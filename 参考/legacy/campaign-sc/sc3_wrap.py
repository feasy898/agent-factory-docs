#!/usr/bin/env python3
"""sc3_wrap.py <wave_root> <job> — SC3 机制级 wrapper：一个 job 的完整生命周期。

job 形式: "<arm>/<task>-rN"（p31 的链式伪 job 为 "p31-skill-library/CHAIN-<fam>-rN"）
所有 zcode 调用统一: timeout -k 60 <s> zcode -p <prompt> --cwd <dir> --mode yolo --model GLM
配额检测: 该次调用日志尾部 20KB 命中 429/限流模式 -> 置 QUOTA_GLM, exit 42（不标 .done, watcher 重试）
       rc=124/137/143（超时杀）豁免配额判定，记 partial 完成（与 SC1/SC2 车道惯例一致）
红线: runner 永远读不到隐藏 pytest；反馈只来自 prompt.txt 里的公开 instruction。
"""
import json, os, re, shutil, subprocess, sys, threading, time

ROOT = sys.argv[1].rstrip("/")
JOB = sys.argv[2]
ARM, J = JOB.split("/", 1)
SC = os.path.dirname(ROOT)
BACKEND = os.environ.get("SC3_BACKEND", "glm")
if BACKEND == "m31":
    QUOTA = os.path.join(SC, "QUOTA_M31")
    MODEL = "minimax/MiniMax-M3.1-Flash-Preview"
    ENGINE = os.path.expanduser("~/.npm-global/bin/mcode")
    QRE = re.compile(r"insufficient_balance|insufficient\s+balance|Token Plan|用量上限|余额不足|error.*2067|2067", re.I)
    def engine_args(prompt, cwd):
        return [ENGINE, "exec", "--cwd", cwd, "--model", MODEL, "--permission", "full", "--timeout", "25m", prompt]
else:
    QUOTA = os.path.join(SC, "QUOTA_GLM")
    MODEL = "account:bigmodel-individual-coding-plan/GLM-5.3-Flash"
    ENGINE = os.path.expanduser("~/.npm-global/bin/zcode")
    QRE = re.compile(r"rate.?limit|http[^ ]*429|responseStatus: 429|Turn execution failed|insufficient|余额|用量上限|Token Plan|too many requests", re.I)
    def engine_args(prompt, cwd):
        return [ENGINE, "-p", prompt, "--cwd", cwd, "--mode", "yolo", "--model", MODEL]
SOLVE_TO = 1500          # 单次解题调用 25min（外层硬超时；mcode 另有内层 --timeout 25m）
AUX_TO = 900             # 验证/选择/QA 调用 15min
MARK = "--- TASK INSTRUCTION (verbatim) ---"
TIMEOUT_RC = (124, 137, 143)

D = os.path.join(ROOT, "runs", ARM, J)
WORK = os.path.join(D, "work")
LOGDIR = os.path.join(ROOT, "logs", ARM)
os.makedirs(LOGDIR, exist_ok=True)
LOG = os.path.join(LOGDIR, J + ".glm.log")

def log(msg):
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("[%s] %s\n" % (time.strftime("%F %T"), msg))

def quota_flag():
    open(QUOTA, "w").write(JOB + "\n")

def tail_quota(path):
    try:
        with open(path, "rb") as f:
            f.seek(0, 2); size = f.tell(); f.seek(max(0, size - 20000))
            return bool(QRE.search(f.read().decode("utf-8", "replace")))
    except Exception:
        return False

def zcode(prompt, cwd, timeout_s, tag, out=None):
    """一次 zcode 调用，输出追加到 out（默认主日志）。返回 rc。rc=127 直接全局中止。"""
    os.makedirs(cwd, exist_ok=True)
    out = out or LOG
    t0 = time.time()
    with open(out, "a", encoding="utf-8") as lf:
        lf.write("\n===== CALL %s cwd=%s =====\n" % (tag, cwd))
        rc = subprocess.run(["timeout", "-k", "60", str(timeout_s)] + engine_args(prompt, cwd),
                            stdout=lf, stderr=subprocess.STDOUT).returncode
    log("call %s rc=%s %.0fs" % (tag, rc, time.time() - t0))
    if rc == 127:
        open(QUOTA + ".infra127", "w").write("zcode missing\n")
        sys.exit(43)
    return rc

def gate_quota(rc, logpath=None):
    """非超时 rc 才做配额判定（超时日志尾部的 turn-failure 不算配额）。"""
    if rc not in TIMEOUT_RC and tail_quota(logpath or LOG):
        log("QUOTA hit -> abort job (no .done)")
        quota_flag()
        sys.exit(42)

def instruction():
    text = open(os.path.join(D, "prompt.txt"), encoding="utf-8", errors="replace").read()
    return text.split(MARK)[-1].strip()

def base_prompt():
    return open(os.path.join(D, "prompt.txt"), encoding="utf-8", errors="replace").read()

def done():
    open(os.path.join(WORK, ".done"), "w").write(time.strftime("%F %T\n"))
    log("DONE " + JOB)

def required_artifacts():
    paths = set()
    for m in re.finditer(r"/app/([A-Za-z0-9_\-][A-Za-z0-9_\-./]*)", instruction()):
        p = m.group(1).rstrip(".,;:)}]")
        if p and not p.endswith("/"):
            paths.add(p)
    return sorted(paths)

def gate_missing():
    return [p for p in required_artifacts() if not os.path.exists(os.path.join(WORK, p))]

def valid_score(wdir):
    score = 0
    for p in required_artifacts():
        fp = os.path.join(wdir, p)
        if not os.path.isfile(fp):
            continue
        try:
            ext = os.path.splitext(fp)[1].lower()
            if ext == ".json":
                json.load(open(fp, encoding="utf-8", errors="replace"))
            elif ext == ".py":
                compile(open(fp, encoding="utf-8", errors="replace").read(), fp, "exec")
            elif os.path.getsize(fp) == 0:
                continue
            score += 1
        except Exception:
            pass
    return score

def artifact_hash_map(wdir):
    import hashlib
    m = {}
    for p in required_artifacts():
        fp = os.path.join(wdir, p)
        if os.path.isfile(fp):
            m[p] = hashlib.sha256(open(fp, "rb").read()).hexdigest()[:16]
    return m

def file_listing(wdir, cap=60):
    out = []
    for dp, dns, fns in os.walk(wdir):
        dns[:] = [x for x in dns if x not in (".git", "__pycache__", "node_modules")]
        for fn in fns:
            out.append(os.path.relpath(os.path.join(dp, fn), wdir))
            if len(out) >= cap:
                return sorted(out)
    return sorted(out)

def artifact_heads(wdir, per=4096, total=30000):
    chunks, used = [], 0
    for p in required_artifacts():
        fp = os.path.join(wdir, p)
        if not os.path.isfile(fp):
            chunks.append("--- %s: MISSING" % p)
            continue
        data = open(fp, "rb").read(per).decode("utf-8", "replace")
        chunks.append("--- %s (%d bytes) ---\n%s" % (p, os.path.getsize(fp), data))
        used += len(data)
        if used > total:
            break
    return "\n".join(chunks)

def vote_winner(roll_dirs):
    """p27 确定性投票：逐产物多数决；无多数 -> 有效性分决胜；再平 -> r1。"""
    maps = [artifact_hash_map(d) for d in roll_dirs]
    best, win = -1, 0
    for i, hm in enumerate(maps):
        agree = 0
        for p in required_artifacts():
            votes = [m.get(p) for m in maps]
            majority = max(set(votes), key=votes.count)
            if votes.count(majority) >= 2 and hm.get(p) == majority:
                agree += 1
        if agree > best:
            best, win = agree, i
    if best <= 0:
        scores = [valid_score(d) for d in roll_dirs]
        win = scores.index(max(scores))
    return win

def llm_select(roll_dirs, mode):
    """p26 按产物选 / p28 按轨迹+产物选。返回 0..2，解析失败回退投票。"""
    parts = ["你是一名严格的评审。下面是同一道终端任务的 3 次独立解题尝试。", "",
             "--- 任务要求（原文） ---", instruction(), ""]
    for i, d in enumerate(roll_dirs):
        parts.append("=== 尝试 %d ===" % (i + 1))
        parts.append("文件清单: " + ", ".join(file_listing(d)))
        parts.append(artifact_heads(d))
        if mode == "traj":
            tlog = os.path.join(D, "roll%d.log" % (i + 1))
            tail = ""
            if os.path.exists(tlog):
                with open(tlog, "rb") as f:
                    f.seek(0, 2); sz = f.tell(); f.seek(max(0, sz - 6000))
                    tail = f.read().decode("utf-8", "replace")
            parts.append("轨迹尾部:\n" + tail)
        parts.append("")
    parts.append("请判断哪次尝试最可能通过任务的自动测试。只输出一行：WINNER: <1|2|3>")
    rc = zcode("\n".join(parts), os.path.join(D, "work.select"), AUX_TO, "select-" + mode)
    if rc in TIMEOUT_RC:
        log("select-%s 超时 -> 回退投票" % mode)
        return vote_winner(roll_dirs)
    gate_quota(rc)
    try:
        with open(LOG, "rb") as f:
            f.seek(0, 2); sz = f.tell(); f.seek(max(0, sz - 20000))
            tail = f.read().decode("utf-8", "replace")
        m = list(re.finditer(r"WINNER:\s*([123])", tail))
        if m:
            w = int(m[-1].group(1)) - 1
            if 0 <= w < len(roll_dirs):
                log("select-%s -> r%d" % (mode, w + 1))
                return w
    except Exception:
        pass
    log("select-%s 解析失败 -> 回退投票" % mode)
    return vote_winner(roll_dirs)

def _switch(eng):
    global BACKEND, QUOTA, MODEL, ENGINE, engine_args
    BACKEND = eng
    if eng == "m31":
        QUOTA = os.path.join(SC, "QUOTA_M31")
        MODEL = "minimax/MiniMax-M3.1-Flash-Preview"
        ENGINE = os.path.expanduser("~/.npm-global/bin/mcode")
        def engine_args(prompt, cwd, _e=ENGINE, _m=MODEL):
            return [_e, "exec", "--cwd", cwd, "--model", _m, "--permission", "full", "--timeout", "25m", prompt]
    else:
        QUOTA = os.path.join(SC, "QUOTA_GLM")
        MODEL = "account:bigmodel-individual-coding-plan/GLM-5.3-Flash"
        ENGINE = os.path.expanduser("~/.npm-global/bin/zcode")
        def engine_args(prompt, cwd, _e=ENGINE, _m=MODEL):
            return [_e, "-p", prompt, "--cwd", cwd, "--mode", "yolo", "--model", _m]

def run_rollout(i, prompt, results):
    rd = os.path.join(D, "work.r%d" % i)
    rlog = os.path.join(D, "roll%d.log" % i)
    if os.path.exists(os.path.join(rd, ".done")):
        results[i] = rd  # 断点续跑：已完成的 rollout 跳过
        return
    if os.path.exists(rd):
        shutil.rmtree(rd)
    shutil.copytree(WORK, rd, symlinks=True)
    t0 = time.time()
    rc = zcode(prompt, rd, SOLVE_TO, "roll%d" % i, out=rlog)
    open(os.path.join(rd, ".done"), "w").write("rc=%s %.0fs\n" % (rc, time.time() - t0))
    results[i] = rd

def roll_rc(rd):
    try:
        return int(re.search(r"rc=(\d+)", open(os.path.join(rd, ".done")).read()).group(1))
    except Exception:
        return 0

def arm_verifier(kind):
    roll_dirs = [os.path.join(D, "work.r%d" % i) for i in (1, 2, 3)]
    if not all(os.path.exists(os.path.join(d, ".done")) for d in roll_dirs):
        prompt = base_prompt()
        results, threads = {}, []
        for i in (1, 2, 3):
            t = threading.Thread(target=run_rollout, args=(i, prompt, results))
            t.start(); threads.append(t); time.sleep(20)  # 错峰防突发限流
        for t in threads:
            t.join()
    for i in (1, 2, 3):
        rc = roll_rc(roll_dirs[i - 1])
        if rc not in TIMEOUT_RC and tail_quota(os.path.join(D, "roll%d.log" % i)):
            log("QUOTA hit in rollout r%d -> abort" % i)
            quota_flag(); sys.exit(42)
    if kind == "p27-artifact-vote":
        w = vote_winner(roll_dirs)
        log("vote -> r%d" % (w + 1))
    elif kind == "p26-rubric-select":
        w = llm_select(roll_dirs, "artifact")
    else:
        w = llm_select(roll_dirs, "traj")
    winner = roll_dirs[w]
    for item in os.listdir(WORK):
        p = os.path.join(WORK, item)
        shutil.rmtree(p) if os.path.isdir(p) and not os.path.islink(p) else os.remove(p)
    for item in os.listdir(winner):
        if item == ".done":
            continue
        src = os.path.join(winner, item)
        dst = os.path.join(WORK, item)
        if os.path.isdir(src) and not os.path.islink(src):
            shutil.copytree(src, dst, symlinks=True)
        else:
            shutil.copy2(src, dst)
    done()

def arm_t2():
    if not os.path.exists(os.path.join(WORK, ".solve-done")):
        rc = zcode(base_prompt(), WORK, SOLVE_TO, "solve")
        gate_quota(rc)
        open(os.path.join(WORK, ".solve-done"), "w").write("rc=%s\n" % rc)
    gate = ("你刚刚完成了一道终端任务（要求附后）。现在做产物门禁："
            "逐条核对任务要求中明确列出的每一个输出文件/路径在你当前工作目录下是否存在、格式是否正确、内容是否完整。"
            "若有缺失或损坏，立即修复补齐。全部确认无误后结束。\n\n--- 任务要求（原文） ---\n" + instruction())
    rc = zcode(gate, WORK, AUX_TO, "gate")
    gate_quota(rc)
    done()

def arm_p2mech():
    if not os.path.exists(os.path.join(WORK, ".plan-done")):
        plan = (base_prompt() + "\n\n【两阶段之规划阶段】本轮只做规划，不要动手改任何文件："
                "把解题步骤、要创建/修改的文件、验证方法写成 PLAN.md 存到当前工作目录。")
        rc = zcode(plan, WORK, AUX_TO, "plan")
        gate_quota(rc)
        open(os.path.join(WORK, ".plan-done"), "w").write("rc=%s\n" % rc)
    if not os.path.exists(os.path.join(WORK, ".exec-done")):
        exe = (base_prompt() + "\n\n【两阶段之执行阶段】当前目录已有 PLAN.md，按它实施；"
               "实施中若发现计划有误可偏离，但要在 PLAN.md 里注明。")
        rc = zcode(exe, WORK, SOLVE_TO, "exec")
        gate_quota(rc)
        open(os.path.join(WORK, ".exec-done"), "w").write("rc=%s\n" % rc)
    ver = ("核对当前工作目录的产物是否完整满足任务要求（附后），有缺漏立即补齐。"
           "\n\n--- 任务要求（原文） ---\n" + instruction())
    rc = zcode(ver, WORK, AUX_TO, "verify")
    gate_quota(rc)
    done()

def arm_retry(with_feedback):
    rc = zcode(base_prompt(), WORK, SOLVE_TO, "solve1")
    gate_quota(rc)
    miss = gate_missing()
    if not miss:
        log("gate pass round1"); done(); return
    log("gate missing: %s" % ",".join(miss))
    if with_feedback:
        p2 = (base_prompt() + "\n\n【修复轮】上一次尝试结束后检查发现以下任务要求的产物缺失：\n" +
              "\n".join("- " + m for m in miss) + "\n请补齐这些产物并复核其余要求。")
    else:
        p2 = base_prompt()
    rc = zcode(p2, WORK, SOLVE_TO, "solve2")
    gate_quota(rc)
    done()

def arm_qa():
    rc = zcode(base_prompt(), WORK, SOLVE_TO, "solve1")
    gate_quota(rc)
    qa = ("你是 QA 评审。检查当前工作目录的产物是否满足任务要求（附后）。"
          "只输出结论：全部满足输出 QA_PASS；有任何缺漏输出 QA_FAIL，然后用不超过 10 行列出具体问题。"
          "\n\n--- 任务要求（原文） ---\n" + instruction())
    rc = zcode(qa, WORK, AUX_TO, "qa")
    gate_quota(rc)
    qa_pass = False
    try:
        with open(LOG, "rb") as f:
            f.seek(0, 2); sz = f.tell(); f.seek(max(0, sz - 20000))
            qa_pass = "QA_PASS" in f.read().decode("utf-8", "replace")
    except Exception:
        pass
    if qa_pass:
        log("QA_PASS gen1"); done(); return
    log("QA_FAIL -> gen2 with report")
    redo = base_prompt() + "\n\n【代际修复】前一代产物未通过 QA 评审，请全面复核任务要求并修复所有缺漏。"
    rc = zcode(redo, WORK, SOLVE_TO, "solve2")
    gate_quota(rc)
    done()

M31_TASKS = set(['feal-linear-cryptanalysis', 'feal-differential-cryptanalysis', 'regex-log', 'jq-data-processing', 'countdown-game', 'huarong-dao-solver', 'puzzle-solver'])

def p31_chain(fam, rep):
    wave = json.load(open(os.path.join(SC, "sc3.json"), encoding="utf-8"))
    tasks = wave["p31_families"][fam]
    skills = os.path.join(ROOT, "chains", "%s_r%s" % (fam, rep), "skills")
    os.makedirs(skills, exist_ok=True)
    for t in tasks:
        jd = os.path.join(ROOT, "runs", ARM, "%s-r%s" % (t, rep))
        w = os.path.join(jd, "work")
        if os.path.exists(os.path.join(w, ".done")):
            continue
        prompt = open(os.path.join(jd, "prompt.txt"), encoding="utf-8", errors="replace").read()
        prompt = prompt.replace("{SKILLS_DIR}", skills)
        jlog = os.path.join(ROOT, "logs", ARM, "%s-r%s.glm.log" % (t, rep))
        os.makedirs(os.path.dirname(jlog), exist_ok=True)
        t0 = time.time()
        with open(jlog, "a", encoding="utf-8") as lf:
            lf.write("\n===== p31 chain %s r%s task %s skills=%s =====\n" % (fam, rep, t, skills))
            if t in M31_TASKS:
                if BACKEND != "m31":
                    old = BACKEND; _switch("m31")
                args = engine_args(prompt, w)
                if BACKEND != "m31":
                    _switch(old)
            else:
                if BACKEND != "glm":
                    old = BACKEND; _switch("glm")
                args = engine_args(prompt, w)
                if BACKEND != "glm":
                    _switch(old)
            rc = subprocess.run(["timeout", "-k", "60", str(SOLVE_TO)] + args,
                                stdout=lf, stderr=subprocess.STDOUT).returncode
        if rc == 127:
            open(QUOTA + ".infra127", "w").write("zcode missing\n"); sys.exit(43)
        if rc not in TIMEOUT_RC and tail_quota(jlog):
            quota_flag(); sys.exit(42)
        open(os.path.join(w, ".done"), "w").write("rc=%s %.0fs\n" % (rc, time.time() - t0))
    log("p31 chain %s r%s done" % (fam, rep))

def m31_owned():
    f = os.path.join(ROOT, "jobs-m31.txt")
    if not os.path.exists(f):
        return False
    return JOB in {l.strip() for l in open(f, encoding="utf-8") if l.strip()}

def main():
    if BACKEND == "glm" and m31_owned():
        return  # m3.1 车道负责（块一致性分流）
    if J.startswith("CHAIN-"):
        if os.path.exists(QUOTA):
            sys.exit(42)
        fam = J[len("CHAIN-"):].rsplit("-r", 1)[0]
        rep = J.rsplit("-r", 1)[1]
        p31_chain(fam, rep)
        return
    if os.path.exists(os.path.join(WORK, ".done")):
        return
    if os.path.exists(QUOTA):
        sys.exit(42)
    if ARM == "base":
        rc = zcode(base_prompt(), WORK, SOLVE_TO, "solve")
        gate_quota(rc)
        done()
    elif ARM in ("p26-rubric-select", "p27-artifact-vote", "p28-supervisor-select"):
        arm_verifier(ARM)
    elif ARM == "t2-artifact-gate":
        arm_t2()
    elif ARM == "p2-mech-chain":
        arm_p2mech()
    elif ARM == "p5-mech-blind-retry":
        arm_retry(False)
    elif ARM == "p37-feedback-retry":
        arm_retry(True)
    elif ARM == "p43-qa-gate":
        arm_qa()
    else:
        log("UNKNOWN ARM/JOB " + JOB)
        sys.exit(2)

main()
