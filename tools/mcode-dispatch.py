#!/usr/bin/env python3
"""mcode-dispatch.py — mcode 官方 harness 对照线派发器（S1 120题 × {m31f, m3}）。

链路：本机(pandev-comp)派发 → anolis(100.64.0.7) 备工作区+跑 mcode 官方 CLI exec →
      收 git diff 补丁 → 本机 tools/cb-judge.sh（sweb.eval 容器 + GNU patch fuzz + 官方
      eval_script + swev-judge）判分 → results.jsonl 落账（字段仿 deepseek-cb 行）。

口径声明（勿混算）：profile="mcode-m31f"/"mcode-m3"，scaffold="mcode-official"。
与 af-harness 口径（af-bench fix1/fix2 各臂）和 codebuddy 口径（deepseek-cb）不混算。

调用方式（cal2 遗产复刻 + 2026-10-21 排障修复，详见 设计/mcode-官方harness对照-设计.md）：
  ssh anolis mcode exec --cwd <work> --model <route> --permission full --timeout 25m "$(cat prompt.txt)"
  外层 OS timeout 1800s。路由名：m31f=minimax/MiniMax-M3.1-Flash（旧 Preview 名已从
  managed 路由目录剔除）；m3=minimax/MiniMax-M3。
  每次 exec 前跑 auth-sync.py：af 主产线 token 门禁每小时轮换 auth.json（generation 递增），
  而 mcode 的 readUsableCredential 要求 auth-state.json.generation == credential.generation，
  不一致即误判 needs-login——auth-sync 在锁内对齐两文件并把 cli-auth identity 指纹对齐当前令牌。

资源纪律：mcode 并发 ≤2 实例（红线 ≤3）；判分串行（cal2 教训：判分须安静防 OOM 假失败，
满足 ≤2 红线）；anolis /data 余量 <4G 熔断等待；配额熔断按 profile 独立（m31f 免费 / m3 套餐）。

资源闸（补丁① R2，2026-10-22；tmpfs 第四探针=R2 同批 D-24 补丁）：worker 循环顶部先
probe 四条件，闸闭则任务不出队。
60s 缓存对齐 factory-sched mem_gate 先例；阈值/时限全部可用环境变量覆盖（调参不改码）：
  a. 本机内存：/proc/meminfo MemAvailable < GATE_MEM_MIN_GB（默认 4GiB，判分容器峰值
     ~889MiB/题、4 倍余量）→ 推迟。本地读取解析（绝不把 awk 程序经 ssh 传远端——
     sched mem_gate 的引号永闭教训）；读数异常属进程环境故障：记日志放行（单题有
     25m/30m 双超时兜底，不因读数故障停产）。
  b. 本机磁盘：docker data root 所在分区可用 < GATE_DISK_MIN_GB（默认 20GiB）→ 推迟
     （判分容器与 judge.json/eval.log 写在本地）；statvfs 判不准 → 推迟（fail-closed）。
  c. anolis REMOTE_ROOT 余量 < GATE_REMOTE_MIN_GB（默认同 DISK_MIN_GB=4G）或不可达/
     判不准 → 推迟（fail-closed，先例=sched 磁盘闸 2026-10-20 22:21 闪断放行教训；
     本条升级原 disk_ok 的「判不准不拦」）。tailnet/ssh 闪断（复发模态）下旧行为=
     prepare_failed 显性爆发并烧 attempts，新行为=进入带升级通道的推迟。
  d. 本机 /tmp（tmpfs）可用 < GATE_TMPFS_MIN_GB（默认 2.2GiB）→ 推迟。statvfs 异常
     =盘点失败=推迟（fail-closed）。校准依据：10-21 晚 /tmp 配额耗尽 EDQUOT（Errno 122）
     实测发生于仅余 ~1.7G 时（mes500-根因报告.md:42 + 对齐组-state.md:252），64M-1G
     金丝雀在 3.07G 余量全过——与 factory-sched tmpfs 闸（patch-tmpfs-gate-sched-R2）
     同阈值。本闸防自反馈死法：results.jsonl/judge.json/state/heartbeat 全落 /tmp，
     /tmp 满时照常取任务=判分账写到一半撞 EDQUOT。
推迟语义（拦新不杀旧）：闸闭期间任务永不出队（无重排队逻辑，在飞 solve 自然收尾）；
不写 phase（不污染 summary）、不调 _note_failure（不烧 attempts）；每 DEFER_HB_S
（600s）刷一次 heartbeat——keepalive 判据是 heartbeat mtime<2400s（factory-keepalive
check_mcode_dispatch），推迟期必须呈现「活的、在推迟的」而非失联误判重启。连续推迟
>DEFER_ESCALATE_S（1800s）→ 升级（同一次连续推迟期只升一次，escalated 旗标，闸解除
复位）：klog(/tmp/mcode-dispatch.log) ALARM + MES kind=mcode_defer_stalled（直 INSERT
af_mes.mes_event，写失败不致命）+ deferred.log 追加摘要。连续推迟 >DEFER_HALT_S
（86400s）→ worker 停取新任务、保持升级态等人工（心跳照刷防 keepalive 误判重启；
资源恢复闸开即自动复位恢复取任务；如需彻底停产由人工 kill 并同步处置 keepalive 侧）。
连续推迟时长跨重启接续：进程内 + /tmp/mcode-dispatch/defer-state.json（重启后新进程
读到旧起始时刻继续计时，escalated 同期不重复升级）。watch 安灯对 mcode 零可见性，
接入为二期可选项；当前靠 klog+MES+deferred.log 三通道可达人工巡检。
残余竞态：取任务之后、prepare 之前闸才闭的窗口内，run_one 既有预检 disk_ok（本补丁
起 fail-closed）等待 300s 后仍未恢复，则走既有失败重试路径（每进程每任务 ≤3 次），
再下一次取任务即被闸拦住。
环境变量：MCODE_GATE_MEM_MIN_GB / MCODE_GATE_DISK_MIN_GB / MCODE_GATE_REMOTE_MIN_GB /
MCODE_GATE_TMPFS_MIN_GB / MCODE_GATE_CACHE_S / MCODE_DEFER_HB_S / MCODE_DEFER_ESCALATE_S /
MCODE_DEFER_HALT_S。
exit 码语义：run 双实例守卫 exit 3（single_instance，保持不动）；gate-check 闸闭 exit 4；
tools/mcode-once-wrapper.sh（无人值守补跑硬闸）闸闭拒绝 exit 4；once 本体不拦人工补跑
（人工知情动作）——闸闭只打横幅警告并写 deferred.log，照常执行。

断点续跑：state.json 记 (task|profile) → phase；daemon 重启后跳过已 judged 行，
未完成态按 phase 续跑。order：D1 全部 → D2 → D3，每题先 m31f 后 m3。

2026-10-22 排障修复（D2 双档案停滞根因，详见 状态观测/巡检日志.md）：
  - ensure_repo 改走 repo-cache.sh：flock 按 repo 串行化。旧逻辑只 test -d .git，
    识别不了"克隆进行中/上次克隆失败留下的半个缓存"，另一 worker clone --shared
    拿到缺对象缓存，checkout 即 fatal: unable to read tree（D2 积压 16 题全部死于此）。
  - clone 自带 1700s 远端超时；超时/失败一律 rm -rf 半个缓存（旧逻辑留毒缓存，
    会反复毒害后续所有用到该 repo 的任务，且 prepare_failed 无重试 → 一次判死）。
  - prepare 的 checkout 失败若报 unable to read tree / does not exist：加锁清理
    毒缓存后返回失败，下一 attempt 自动重 clone（自愈）。
  - prepare_failed/error 不再一次判死：worker 内重排队，每进程每任务最多 3 次，
    间隔 60s；quota 熔断不重试。历史重试机制=重启 daemon（results.jsonl 里
    47/48 行 prepare_failed 多为跨重启累积），本修复把重试下沉到进程内。
  - 运维注意：重启 daemon 前须等在飞任务自然收尾——强杀会遗留远端 mcode 跑到
    25m 内层超时，且与新 run 争用同一 workdir（prepare 会 rm -rf 之）。

用法:
  mcode-dispatch.py run                  # 常驻：跑完 120×2 题后退出
  mcode-dispatch.py once <tid> <profile> # 单题单档案端到端（验收/补跑；闸闭仅横幅放行）
  mcode-dispatch.py summary              # 看板：分档×分档案通过率 + 在途
  mcode-dispatch.py deploy               # 只部署 anolis 侧 helpers（调试用）
  mcode-dispatch.py gate-check           # 只读探测资源闸（0=开 / 4=闭）
  tools/mcode-once-wrapper.sh <tid> <profile>  # 无人值守补跑硬闸：闸闭拒绝 exit 4

密钥纪律：本机不落任何令牌；anolis 侧 auth-sync.py 只写哈希与 ID，不落令牌明文。
"""
import argparse
import base64
import hashlib
import json
import os
import queue
import re
import subprocess
import sys
import threading
import time
import urllib.parse
import urllib.request

WS = "/home/pan-ding/workspace/agent黑灯工厂"
PLAN = f"{WS}/计划/s1-swev-120.json"
TASKS_DIR = "/tmp/swev-s1"
JUDGE = f"{WS}/tools/cb-judge.sh"
REMOTE = "anolis"
REMOTE_ROOT = "/data/bench/mcode-swev"
STATE_ROOT = "/tmp/mcode-dispatch"
STATE_FILE = f"{STATE_ROOT}/state.json"
HEARTBEAT = f"{STATE_ROOT}/heartbeat"
PIDFILE = f"{STATE_ROOT}/dispatch.pid"
LOG = "/tmp/mcode-dispatch.log"

PROFILES = {
    "m31f": "minimax/MiniMax-M3.1-Flash",
    "m3": "minimax/MiniMax-M3",
}
TIER_ORDER = {"D1": 0, "D2": 1, "D3": 2}
SOLVE_TIMEOUT = 1800          # OS 级硬超时（cal2 同款；mcode 内层 25m）
SSH_TIMEOUT = SOLVE_TIMEOUT + 420
MCODE_WORKERS = 2             # 红线 ≤3，留 1 余量
DISK_MIN_GB = 4.0
QUOTA_PATTERNS = "insufficient_balance|Token Plan 用量上限|http_code.:402|error code: 2067"
MAX_ATTEMPTS = 3             # 每进程内同一 (task,profile) 最大尝试次数（2026-10-22：失败不再一次判死）
RETRY_DELAY = 60             # 重试间隔（秒）

# ---- 组合补丁①（T0-5 §8.3-a）：--trim-history 默认关的 refs 裁剪 ----
# 硬纪律③：只做默认关闭的 flag，不改现行行为。开启时 prepare() 之后把工作区
# refs 裁剪到 base（删 base 之后可达的 refs + reflog expire + gc --prune=now），
# 杜绝未来提交可达；裁剪后做三面校验（refs/reflog/gc），任一面不闭合即 fail-closed。
TRIM_HISTORY = False         # 由 --trim-history 置 True（默认 False=现行行为）
TRIM_SCRIPT = "trim-history.sh"

# ---- 组合补丁②（T0-5 §8.3-b）：D-34 judge_error 只重判不重跑 ----
REJUDGE_MAX_ATTEMPTS = 2     # §8.3-b：判分锁内重判 ≤2 次
REJUDGE_BACKOFF = 60         # §8.3-b：退避 60s
REJUDGE_TIMEOUT = 1500       # 与 judge() 现行 cb-judge 超时同值
VENV_PY = "/home/pan-ding/swev-venv/bin/python"
# §0.3 冻结表（静态值，重判前逐件对照；漂移=不重判、直接登记安灯）。
# venv 指纹两件为本次实施时实测（as-of 2026-10-22 14:3x，sha256sum 实测），
# 重基线命令见交付文档（改这两个常量即可，判分链本身不动）。
FREEZE_JUDGE_SHA = {
    "tools/cb-judge.sh": "9c8f9c981f91f02dd3aec2706ada4ae3cd05b8e486517a6c0dc531e3f41a4d1e",
    "tools/swev-judge.py": "0338566c2f457496037c70f16504b0cfe9f5286c55ee2d67963428b00e7fc16a",
    "swev-venv/bin/python": "52e0a13e60a981d8c4b6478be2ba5176f69da07948a056bf49cf6f077e30cb41",
    "swev-venv/pip-freeze": "85d4c909ed2229a2434eb5f5406fddf0a385ca157c68f1e955624ad8b7d0bd15",
}

# ---- 补丁① R2：资源闸常量（阈值/时限全部环境变量可覆盖，便于调参不改码）----
GATE_MEM_MIN_GB = float(os.environ.get("MCODE_GATE_MEM_MIN_GB", "4"))
GATE_DISK_MIN_GB = float(os.environ.get("MCODE_GATE_DISK_MIN_GB", "20"))
GATE_REMOTE_MIN_GB = float(os.environ.get("MCODE_GATE_REMOTE_MIN_GB", str(DISK_MIN_GB)))
# tmpfs 第四探针（R2 同批 D-24 补丁）：/tmp 存判分结果+state+heartbeat，满盘=自反馈死法
GATE_TMPFS_MIN_GB = float(os.environ.get("MCODE_GATE_TMPFS_MIN_GB", "2.2"))
GATE_CACHE_S = float(os.environ.get("MCODE_GATE_CACHE_S", "60"))
DEFER_HB_S = float(os.environ.get("MCODE_DEFER_HB_S", "600"))
DEFER_ESCALATE_S = float(os.environ.get("MCODE_DEFER_ESCALATE_S", "1800"))
DEFER_HALT_S = float(os.environ.get("MCODE_DEFER_HALT_S", "86400"))
DEFER_STATE_FILE = f"{STATE_ROOT}/defer-state.json"
DEFERRED_LOG = f"{STATE_ROOT}/deferred.log"


def _mes_conn(url=None):
    """MES ClickHouse 连接 → (base_url, auth_header)。

    2026-10-22 MES 由 pandev-comp 本机迁至 mingda-website（tailnet 100.64.0.2:15221，
    迁移动机/对账/回滚见 计划/研究组/mes迁移mingda-交付.md；本机 127.0.0.1:5221 旧实例
    保留只读 48h 作回滚锚）。解析顺序：入参 url > 环境变量 MES_CH_URL > 0600 凭据文件
    ~/.config/mes-ch/url > 缺省新 MES 地址。凭据可写 user:pass@host 形式（urllib 不
    解析 URL 内嵌凭据，故在此拆出转 Basic 头）；口令明文按密钥纪律只存 0600 文件，
    不进任何文档/回报。缺文件且无 env 落到无凭据地址→401 显性失败，不静默写旧锚点。
    """
    if url is None:
        url = os.environ.get("MES_CH_URL")
    if not url:
        try:
            with open(os.path.expanduser("~/.config/mes-ch/url"), encoding="utf-8") as f:
                url = f.read().strip()
        except OSError:
            url = "http://100.64.0.2:15221"
    auth = None
    if "@" in url:
        scheme, rest = url.split("://", 1)
        userinfo, hostpart = rest.split("@", 1)
        url = f"{scheme}://{hostpart}"
        auth = "Basic " + base64.b64encode(userinfo.encode()).decode()
    return url, auth


CH, CH_AUTH = _mes_conn()   # MES ClickHouse（2026-10-22 迁 mingda；factory-keepalive 同款直 INSERT）
DOCKER_ROOT = "/var/lib/docker"  # docker info 不可用时的兜底 data root

# ---------------- anolis 侧 helpers（每次启动重新部署，幂等） ----------------

AUTH_SYNC = '''#!/usr/bin/env python3
"""auth-sync.py — mcode exec 前的凭证一致性同步（mcode-dispatch 线专用，anolis 侧）。

背景（2026-10-21 排障）：af 主产线的 mcode-token.py 每小时轮换 auth.json（generation 递增），
而 mcode CLI readUsableCredential 要求 auth-state.json.generation == credential.generation，
不一致一律按 needs-login 拒执行。本脚本每次 exec 前：
  1. 令牌余量 <35min 时先经 mcode-token.py refresh（自带 flock，与主产线门禁串行；35min
     覆盖最长 25min 的 exec + 30s minValidity，保证 mcode 全程免刷新、不碰轮换竞态）；
  2. flock(auth.json.lock) 内把 auth-state.json 的 generation/expiresAtMs/status 对齐 credential；
  3. 刷新 cli-auth account-identity.json 的 tokenFingerprint（sha256(当前token)）。
密钥零明文：只写哈希与 ID。
"""
import fcntl
import hashlib
import json
import os
import subprocess
import time

AUTH = os.path.expanduser("~/.minimax/auth/prod/cn/mcode-public/auth.json")
STATE = os.path.expanduser("~/.minimax/auth/prod/cn/mcode-public/auth-state.json")
IDENT = os.path.expanduser("~/.minimax/cli-auth/prod/cn/account-identity.json")
REFRESH_AHEAD = 35 * 60


def read_rec():
    d = json.load(open(AUTH))
    return d["records"][next(iter(d["records"]))]


def atomic(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        f.write(json.dumps(obj, indent=2) + "\\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, path)


def main():
    rec = read_rec()
    left = (int(rec.get("expiresAtMs", 0)) - int(time.time() * 1000)) / 1000
    if left < REFRESH_AHEAD:
        subprocess.run([os.path.expanduser("~/.local/bin/mcode-token.py"), "refresh"],
                       check=False, capture_output=True)
        rec = read_rec()
    lock = open(AUTH + ".lock", "a+")
    fcntl.flock(lock, fcntl.LOCK_EX)
    try:
        rec = read_rec()  # 锁内重读（可能刚被门禁刷新）
        st = json.load(open(STATE))
        st.update(generation=int(rec["generation"]),
                  expiresAtMs=int(rec["expiresAtMs"]),
                  status="authenticated")
        atomic(STATE, st)
        ident = {}
        try:
            ident = json.load(open(IDENT))
        except Exception:
            ident = {}
        ident.update(version=1, buildEnv="prod", region="cn", status="verified",
                     tokenFingerprint="sha256:" + hashlib.sha256(
                         rec["accessToken"].strip().encode()).hexdigest(),
                     updatedAtMs=int(time.time() * 1000))
        os.makedirs(os.path.dirname(IDENT), mode=0o700, exist_ok=True)
        atomic(IDENT, ident)
    finally:
        fcntl.flock(lock, fcntl.LOCK_UN)


if __name__ == "__main__":
    main()
'''

RUN_ONE = '''#!/bin/bash
# run-one.sh <workdir> <model> <promptfile> <logfile> <timeout_s> — mcode 官方 exec（cal2 复刻）
set -uo pipefail
W="$1"; MODEL="$2"; PROMPT="$3"; LOG="$4"; TMO="${5:-1800}"
export PATH="$HOME/.npm-global/bin:$PATH"
python3 "$HOME/mcode-swev/auth-sync.py" || echo "[run-one] auth-sync 失败（继续，用现有凭证）"
cd "$W"
timeout -k 60 "$TMO" mcode exec --cwd "$W" --model "$MODEL" --permission full --timeout 25m "$(cat "$PROMPT")" > "$LOG" 2>&1
rc=$?
if grep -qi "insufficient_balance\\|Token Plan 用量上限\\|http_code.:402\\|error code: 2067" "$LOG"; then
  echo QUOTA_HIT; exit 42
fi
exit $rc
'''

REPO_CACHE = '''#!/bin/bash
# repo-cache.sh <slug> <url> — 确保 repos/<slug> 仓库缓存完整可用（2026-10-22 修 D2 停滞）。
# 背景：旧 ensure_repo 只 test -d .git，识别不了"克隆进行中/上次克隆失败留下的半个缓存"，
# 另一 worker clone --shared 会拿到缺对象缓存，checkout 报 fatal: unable to read tree。
# 现：flock 按 repo 串行化（消除并发克隆竞态）；HEAD 不可解析视为毒缓存，清理后重 clone；
# clone 自带 1700s 超时，超时/失败即清理，绝不留半个缓存毒害后续任务。
# 输出：OK（缓存完好）/ CLONED（重建完成）/ CLONE_FAIL（重建失败，已清理）。
set -uo pipefail
ROOT="${MCODE_REPOS:-/data/bench/mcode-swev/repos}"
SLUG="$1"; URL="$2"
D="$ROOT/$SLUG"
mkdir -p "$ROOT"
exec 9>"$ROOT/.$SLUG.lock"
flock 9 || exit 1
if [ -d "$D/.git" ] && git -C "$D" rev-parse --verify HEAD >/dev/null 2>&1; then
  echo OK; exit 0
fi
[ -e "$D" ] && rm -rf "$D"
if timeout 1700 git clone --quiet "$URL" "$D"; then
  echo CLONED; exit 0
fi
rm -rf "$D"
echo CLONE_FAIL; exit 1
'''

TRIM_HISTORY_SH = '''#!/bin/bash
# trim-history.sh <workdir> <base_sha> [probe_sha] — 裁剪工作区 refs 到 base + 三面校验
# 2026-10-22 组合补丁①（dispatch --trim-history；默认关，本脚本仅在 flag 开启时部署到 anolis）。
# 步骤顺序不可换（2026-10-22 anolis 实测）：
#   1) 删 base 之后可达的 refs（tag 一律删——tag 是考古通道）——必须在 alternates 仍在时做，
#      此时对象可读，update-ref -d 才干净；
#   2) 定向 pack：只把 base 可达对象搬进本仓（不搬整条上游历史，repack -a 会把全量搬进来）；
#   3) 拆 alternates（--shared 克隆的考古后门）——拆后 base 对象必须仍在场，否则工作区已废；
#   4) reflog expire + 清 logs（reflog 面）；
#   5) gc --prune=now（gc 面）。
# 输出：TRIM_DETAIL <k=v...> + TRIM_RESULT OK|FAIL <原因>（Python 侧 fail-closed 判读）。
set -uo pipefail
W="${1:?workdir}"; BASE="${2:?base}"; PROBE="${3:-}"
G="git -C $W"
det=""
fatal() { echo "TRIM_DETAIL$det"; echo "TRIM_RESULT FAIL $1"; exit 1; }

# 1) refs 面
for r in $($G for-each-ref --format='%(refname)'); do
  tip=$($G rev-parse --verify -q "$r^{commit}" 2>/dev/null || true)
  case "$r" in
    refs/tags/*) $G update-ref --no-deref -d "$r" && det="$det tag_deleted=1" ;;
    *)
      if [ -n "$tip" ] && $G merge-base --is-ancestor "$tip" "$BASE" 2>/dev/null; then
        det="$det kept=$r"
      else
        $G update-ref --no-deref -d "$r" && det="$det deleted=$r"
      fi ;;
  esac
done
rm -f "$W/.git/FETCH_HEAD" "$W/.git/ORIG_HEAD"

# 2) 定向 pack（base 可达对象）
PKG="$W/.git/objects/pack/base-reachable.$$.pack"
$G rev-list --objects "$BASE" | awk '{print $1}' | $G pack-objects --stdout > "$PKG" 2>/dev/null \
  || { rm -f "$PKG"; fatal "pack-objects失败"; }
$G index-pack "$PKG" >/dev/null 2>&1 || { rm -f "$PKG" "${PKG%.pack}.idx"; fatal "index-pack失败"; }

# 3) 拆 alternates
rm -f "$W/.git/objects/info/alternates"
$G cat-file -e "$BASE^{commit}" 2>/dev/null || fatal "base对象丢失(工作区已废,须重clone)"

# 4) reflog 面
$G reflog expire --expire=now --expire-unreachable=now --all 2>/dev/null
rm -rf "$W/.git/logs"

# 5) gc 面
$G gc --prune=now -q 2>/dev/null || fatal "gc失败"

# ---- 三面校验（refs / reflog / gc）----
tags=$($G for-each-ref refs/tags | wc -l)
allc=$($G rev-list --all --count)
basec=$($G rev-list "$BASE" --count)
lr=$($G reflog --all 2>/dev/null | wc -l)
lf=$(find "$W/.git/logs" -type f 2>/dev/null | wc -l)
phys=$($G cat-file --batch-all-objects --batch-check | awk '$2=="commit"' | wc -l)
if [ -s "$W/.git/objects/info/alternates" ]; then alt=present; else alt=none; fi
bad=""
[ "$tags" -eq 0 ] || bad="$bad refs:tag残留=$tags"
[ "$allc" = "$basec" ] || bad="$bad refs:rev-list--all=$allc≠base=$basec"
for r in $($G for-each-ref --format='%(refname)'); do
  tip=$($G rev-parse --verify -q "$r^{commit}" 2>/dev/null || true)
  if ! { [ -n "$tip" ] && $G merge-base --is-ancestor "$tip" "$BASE" 2>/dev/null; }; then
    bad="$bad refs:$r非base祖先"
  fi
done
{ [ "$lr" -eq 0 ] && [ "$lf" -eq 0 ]; } || bad="$bad reflog:lines=$lr,files=$lf"
[ "$alt" = none ] || bad="$bad gc:alternates=$alt"
[ "$phys" = "$basec" ] || bad="$bad gc:物理commit=$phys≠base=$basec"
if [ -n "$PROBE" ]; then
  pt=$($G cat-file -t "$PROBE" 2>&1)
  case "$pt" in [0-9a-f]*) bad="$bad gc:post-base对象在场($PROBE)";; esac
fi
det="$det refs_left=$($G for-each-ref | wc -l) all=$allc base=$basec tags=$tags reflog_lines=$lr reflog_files=$lf phys=$phys alt=$alt"
if [ -n "$bad" ]; then
  echo "TRIM_DETAIL$det"
  echo "TRIM_RESULT FAIL 三面不闭合:$bad"
  exit 1
fi
echo "TRIM_DETAIL$det"
echo "TRIM_RESULT OK"
'''

PROMPT_TMPL = """{ps}

--- TASK INSTRUCTION (verbatim) ---
请修复上述 issue 描述的 bug：
1. 当前目录即上游源码仓库（已切到目标提交），直接在此定位并修复。
2. 只改必要的非测试源码文件；严禁改动任何测试文件（tests/ 目录、test_*.py、conftest.py 等）。
3. 尽量自验（能装环境就装；装不上就静态推理保证正确性），不要在自验上耗尽时间。
4. 完成后直接结束。不要 git commit、不要 stash——把改动保留在工作区即可，补丁由外部用 git diff 收集。
"""

# ---------------- 基础设施 ----------------

_log_lock = threading.Lock()


def log(msg):
    line = f"[{time.strftime('%F %T')}] {msg}"
    with _log_lock:
        print(line, flush=True)


def sh(cmd, timeout=None, input_text=None):
    return subprocess.run(cmd, capture_output=True, text=True,
                          timeout=timeout, input=input_text)


def ssh(cmd, timeout=60, input_text=None, check=False):
    r = sh(["ssh", "-o", "ConnectTimeout=15", REMOTE, cmd],
           timeout=timeout, input_text=input_text)
    if check and r.returncode != 0:
        raise RuntimeError(f"ssh 失败 rc={r.returncode}: {cmd[:120]} err={r.stderr[-300:]}")
    return r


def out_dir(profile, tier):
    return f"/tmp/bench-official-mcode-{tier.lower()}-{profile}"


def agg_file(profile):
    return f"/tmp/bench-official-mcode-{profile}/results.jsonl"


def load_state():
    try:
        return json.load(open(STATE_FILE))
    except Exception:
        return {}


def save_state(st):
    os.makedirs(STATE_ROOT, exist_ok=True)
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)
    os.replace(tmp, STATE_FILE)


class ResourceGate:
    """资源闸（补丁① R2；tmpfs 第四探针=R2 同批）：四条件探测 + 推迟簿记 + 升级通道。
    进程级单例（GATE），两个 worker 共用 60s 缓存。fail-closed 口径：内存读数异常放行
    （双超时兜底），本地磁盘/anolis/本机 /tmp 判不准或不可达一律闭闸（先例见模块
    docstring 与 factory-sched disk_gate 2026-10-20 22:21 闪断放行教训）。"""

    def __init__(self):
        self._lock = threading.Lock()
        self._at = 0.0            # 上次探测时刻（GATE_CACHE_S 缓存）
        self._ok = True
        self._why = []
        self.defer_since = None   # 连续推迟起点（epoch），闸开复位
        self.escalated = False    # 本次推迟期已升级旗标（同期只升一次）
        self.halted = False       # 连续推迟 >DEFER_HALT_S：停取新任务保持升级态
        self._last_hb = 0.0
        self._load_defer_state()  # 重启接续：读到旧起始时刻继续计时

    # ---- 三探针（独立可 mock，供单测）----
    @staticmethod
    def probe_mem():
        """本机 MemAvailable（GiB）。本地读取解析；异常不拦（放行，返回 err 供日志）。"""
        try:
            with open("/proc/meminfo", encoding="ascii") as f:
                for line in f:
                    if line.startswith("MemAvailable:"):
                        return float(line.split()[1]) / 1048576.0, None
        except Exception as e:
            return -1.0, f"本机 MemAvailable 读数异常（放行，双超时兜底）: {e}"
        return -1.0, "本机 MemAvailable 字段缺失（放行，双超时兜底）"

    @staticmethod
    def probe_disk():
        """本机 docker data root 所在分区可用（GiB）。statvfs 判不准=闸闭（fail-closed）。"""
        root = DOCKER_ROOT
        try:
            r = subprocess.run(["docker", "info", "-f", "{{.DockerRootDir}}"],
                               capture_output=True, text=True, timeout=10,
                               stdin=subprocess.DEVNULL)
            d = (r.stdout or "").strip()
            if r.returncode == 0 and d:
                root = d
        except Exception:
            pass  # docker CLI 不可用 → 退回默认路径 statvfs
        try:
            st = os.statvfs(root)
            return st.f_bavail * st.f_frsize / 1073741824.0, None, root
        except Exception as e:
            return -1.0, f"本机磁盘 {root} statvfs 失败（fail-closed）: {e}", root

    @staticmethod
    def probe_remote():
        """anolis REMOTE_ROOT 可用（GiB）与可达性。不可达/判不准=闸闭（fail-closed）。"""
        try:
            r = ssh(f"df -BG --output=avail {REMOTE_ROOT} | tail -1", timeout=60)
            return float(r.stdout.strip().rstrip("G")), None
        except Exception as e:
            return -1.0, (f"anolis {REMOTE_ROOT} 不可达/判不准（fail-closed，"
                          f"tailnet/ssh 闪断按推迟处理）: {type(e).__name__}")

    @staticmethod
    def probe_tmpfs():
        """本机 /tmp（tmpfs）可用（GiB）。D-24 第四探针：results/judge/state/heartbeat
        全落 /tmp，满盘即取任务=判分账写一半撞 EDQUOT。statvfs 异常=盘点失败=闸闭
        （fail-closed，同 probe_disk/probe_remote 口径）。"""
        try:
            st = os.statvfs("/tmp")
            return st.f_bavail * st.f_frsize / 1073741824.0, None
        except Exception as e:
            return -1.0, f"本机 /tmp statvfs 失败（fail-closed）: {e}"

    def probe(self):
        """四条件合并探测，GATE_CACHE_S 缓存。返回 (ok, reasons)。

        探测在锁内串行（双 worker 共享一次结果，防缓存过期瞬间的并发 ssh 风暴，
        同 mem_gate/disk_gate 缓存防风暴意图）。"""
        now = time.time()
        with self._lock:
            if now - self._at < GATE_CACHE_S:
                return self._ok, list(self._why)
            ok, why = True, []
            avail, err = self.probe_mem()
            if err:
                log(f"[gate] {err}")
            elif avail < GATE_MEM_MIN_GB:
                ok = False
                why.append(f"本机 MemAvailable {avail:.1f}G < {GATE_MEM_MIN_GB}G")
            free, err, root = self.probe_disk()
            if err:
                ok = False
                why.append(err)
            elif free < GATE_DISK_MIN_GB:
                ok = False
                why.append(f"本机 docker 分区({root}) {free:.0f}G < {GATE_DISK_MIN_GB}G")
            free_r, err_r = self.probe_remote()
            if err_r:
                ok = False
                why.append(err_r)
            elif free_r < GATE_REMOTE_MIN_GB:
                ok = False
                why.append(f"anolis {REMOTE_ROOT} {free_r:.0f}G < {GATE_REMOTE_MIN_GB}G")
            free_t, err_t = self.probe_tmpfs()
            if err_t:
                ok = False
                why.append(err_t)
            elif free_t < GATE_TMPFS_MIN_GB:
                ok = False
                why.append(f"本机 /tmp {free_t:.1f}G < {GATE_TMPFS_MIN_GB}G")
            self._at, self._ok, self._why = now, ok, why
            return ok, list(why)

    # ---- 推迟簿记（闸闭期间由 worker 周期调用）----
    def _load_defer_state(self):
        try:
            d = json.load(open(DEFER_STATE_FILE))
            self.defer_since = float(d["since"])
            self.escalated = bool(d.get("escalated", False))
            self.halted = bool(d.get("halted", False))
        except Exception:
            pass  # 无文件/坏文件=新推迟期处理

    def _save_defer_state(self):
        try:
            os.makedirs(STATE_ROOT, exist_ok=True)
            tmp = DEFER_STATE_FILE + ".tmp"
            with open(tmp, "w") as f:
                json.dump({"since": self.defer_since, "escalated": self.escalated,
                           "halted": self.halted,
                           "updated": time.strftime("%F %T")}, f)
            os.replace(tmp, DEFER_STATE_FILE)
        except Exception as e:
            log(f"[gate] defer-state.json 写失败（不致命）: {e}")

    def defer_tick(self):
        """闸闭期间维护连续推迟时长、DEFER_HB_S 心跳、升级与停取。

        返回 "run"（继续等）或 "halt"（停取新任务保持升级态等人工）。
        不写 phase、不调 _note_failure——推迟不烧 attempts、不污染 summary。"""
        with self._lock:
            now = time.time()
            if self.defer_since is None:
                self.defer_since = now
                self.escalated = self.halted = False
                self._save_defer_state()
                log(f"[gate] 进入推迟：{'；'.join(self._why) or '原因未记录'}；任务留在队列，"
                    f"每 {DEFER_HB_S:.0f}s 刷心跳，>{DEFER_ESCALATE_S/60:.0f}min 升级")
            defer_s = now - self.defer_since
            if now - self._last_hb >= DEFER_HB_S:
                self._last_hb = now
                # 自反馈坑加固（tmpfs 第四探针同批）：闸闭常因 /tmp 满，而心跳恰写
                # /tmp——ENOSPC/EDQUOT 不得炸掉 defer 路径。沿 _save_defer_state
                # （:405-413）口径：写失败不致命只记日志；_last_hb 照常推进，下个
                # HB 周期自然重试，不热循环捶满盘。worker 闸段外另有兜底 try。
                try:
                    os.makedirs(STATE_ROOT, exist_ok=True)
                    with open(HEARTBEAT, "w") as f:
                        f.write(time.strftime("%F %T") + "\n")
                except Exception as e:
                    log(f"[gate] heartbeat 写失败（不致命，下个 HB 周期重试）: {e}")
                log(f"deferring(since={time.strftime('%F %T', time.localtime(self.defer_since))}, "
                    f"连续 {defer_s/60:.0f}min)")
            if not self.escalated and defer_s > DEFER_ESCALATE_S:
                self.escalated = True
                self._save_defer_state()
                self._escalate(defer_s)
            if not self.halted and defer_s > DEFER_HALT_S:
                self.halted = True
                self._save_defer_state()
                log(f"ALARM 连续推迟 {defer_s/3600:.1f}h > {DEFER_HALT_S/3600:.0f}h："
                    f"worker 停取新任务、保持升级态等人工（心跳照刷，资源恢复即自动复位）")
            return "halt" if self.halted else "run"

    def _escalate(self, defer_s):
        """升级三通道：klog ALARM + MES kind=mcode_defer_stalled + deferred.log。"""
        reasons = "；".join(self._why) or "原因未记录"
        log(f"ALARM mcode-dispatch 连续推迟 {defer_s/60:.0f}min > {DEFER_ESCALATE_S/60:.0f}min"
            f"（同期仅此一次），闸闭原因：{reasons}；请人工介入，摘要见 {DEFERRED_LOG}")
        try:
            os.makedirs(STATE_ROOT, exist_ok=True)
            with open(DEFERRED_LOG, "a") as f:
                f.write(f"{time.strftime('%F %T')} ESCALATED 连续推迟 {defer_s/60:.0f}min "
                        f"原因: {reasons}\n")
        except Exception as e:
            log(f"[gate] deferred.log 写失败（不致命）: {e}")
        self.mes_event("mcode_defer_stalled")

    @staticmethod
    def mes_event(kind):
        """直 INSERT af_mes.mes_event（复用 factory-keepalive mes_event 模式）；
        CH 写失败不致命——不阻塞闸逻辑。"""
        body = json.dumps({
            "work_order_id": "mcode-dispatch",
            "occurred_at": time.strftime("%F %T"),
            "event_id": f"mcode-dispatch-{kind}-{int(time.time())}-{os.getpid()}",
            "line_id": "mcode-dispatch",
            "station_id": "mcode-dispatch",
            "kind": kind,
            "quantity": 1,
        }, ensure_ascii=False) + "\n"
        req = urllib.request.Request(
            CH + "/?query=" + urllib.parse.quote(
                "INSERT INTO af_mes.mes_event (work_order_id, occurred_at, event_id, "
                "line_id, station_id, kind, quantity) FORMAT JSONEachRow"),
            data=body.encode(), method="POST")
        if CH_AUTH:
            req.add_header("Authorization", CH_AUTH)
        try:
            with urllib.request.urlopen(req, timeout=15) as r:
                r.read()
        except Exception as e:
            log(f"[gate] MES 写入失败（不致命）: {e}")

    def opened(self):
        """闸由闭转开：复位推迟期（escalated/halted 复位、defer-state.json 清除）。"""
        with self._lock:
            if self.defer_since is None:
                return
            dur = time.time() - self.defer_since
            log(f"[gate] 推迟解除（连续 {dur/60:.0f}min），escalated/halted 复位，恢复取任务")
            self.defer_since = None
            self.escalated = self.halted = False
            self._last_hb = 0.0
            try:
                os.remove(DEFER_STATE_FILE)
            except FileNotFoundError:
                pass
            except Exception as e:
                log(f"[gate] defer-state.json 清除失败（不致命）: {e}")


GATE = ResourceGate()  # 进程级单例：worker 共用缓存；once/gate-check 复用同一逻辑


class Dispatcher:
    def __init__(self):
        self.plan = json.load(open(PLAN))
        # 名单只带 {instance_id, repo, tier}；题目详情（base_commit/problem_statement）在 /tmp/swev-s1/
        for t in self.plan:
            detail = json.load(open(f"{TASKS_DIR}/{t['instance_id']}.json"))
            t.setdefault("base_commit", detail["base_commit"])
            t.setdefault("problem_statement", detail["problem_statement"])
        self.tasks = {t["instance_id"]: t for t in self.plan}
        self.state = load_state()
        self.quota = {p: os.path.exists(f"{STATE_ROOT}/QUOTA-{p}") for p in PROFILES}
        self.attempts = {}          # (tid, prof) -> 本进程已尝试次数（2026-10-22 重试上限）
        self.attempts_lock = threading.Lock()
        self.judge_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.gate = GATE            # 补丁① R2：进程级单例资源闸（worker 共用 60s 缓存）
        self.stop = threading.Event()

    # ---- state helpers ----
    def key(self, tid, prof):
        return f"{tid}|{prof}"

    def set_phase(self, tid, prof, **kv):
        with self.state_lock:
            e = self.state.setdefault(self.key(tid, prof), {})
            e.update(kv)
            e["ts"] = time.strftime("%F %T")
            save_state(self.state)
        # 自反馈坑加固（tmpfs 第四探针同批）：phase 已落账后心跳写失败不得外抛——
        # 原样抛出会穿透 worker 的 except 处理器（处理器内 set_phase 再写心跳再炸）
        # 直至炸掉 worker 线程。沿 :405-413 不致命口径。
        try:
            os.makedirs(STATE_ROOT, exist_ok=True)
            with open(HEARTBEAT, "w") as f:
                f.write(time.strftime("%F %T") + "\n")
        except Exception as e:
            log(f"heartbeat 写失败（不致命，phase 已落账）: {e}")

    def phase(self, tid, prof):
        return self.state.get(self.key(tid, prof), {}).get("phase")

    # ---- remote env ----
    def deploy(self):
        ssh(f"mkdir -p {REMOTE_ROOT}/repos {REMOTE_ROOT}/runs $HOME/mcode-swev", check=True)
        ssh("cat > $HOME/mcode-swev/auth-sync.py", input_text=AUTH_SYNC, check=True)
        ssh("cat > $HOME/mcode-swev/run-one.sh", input_text=RUN_ONE, check=True)
        ssh("cat > $HOME/mcode-swev/repo-cache.sh", input_text=REPO_CACHE, check=True)
        ssh("chmod 700 $HOME/mcode-swev/auth-sync.py && chmod 755 $HOME/mcode-swev/run-one.sh "
            "&& chmod 755 $HOME/mcode-swev/repo-cache.sh", check=True)
        # 组合补丁①：trim 脚本只在 --trim-history 开启时部署（默认关=anolis 侧零新文件）
        if TRIM_HISTORY:
            ssh(f"cat > $HOME/mcode-swev/{TRIM_SCRIPT}", input_text=TRIM_HISTORY_SH, check=True)
            ssh(f"chmod 755 $HOME/mcode-swev/{TRIM_SCRIPT}", check=True)

    def disk_ok(self):
        """anolis /data 余量预检（run_one 内、prepare rm -rf 之前的既有位置，保持不动）。
        补丁① R2 升级语义：判不准/不可达=不足（fail-closed），不再「判不准不拦」——
        先例=factory-sched 磁盘闸 2026-10-20 22:21 闪断放行教训。worker 循环顶部的
        资源闸已把不可达期间的取任务拦在队外，此处兜住取任务后才闪断的残余窗口。"""
        try:
            r = ssh(f"df -BG --output=avail {REMOTE_ROOT} | tail -1")
            return float(r.stdout.strip().rstrip("G")) >= DISK_MIN_GB
        except Exception:
            return False  # 补丁① R2：判不准不拦 → 判不准按不足处理（fail-closed）

    def ensure_repo(self, repo):
        """确保 anolis 侧仓库缓存完整可用（repo-cache.sh：flock 串行 + 毒缓存自清理）。"""
        slug = repo.replace("/", "__")
        r = ssh(f"MCODE_REPOS={REMOTE_ROOT}/repos $HOME/mcode-swev/repo-cache.sh "
                f"{slug} https://github.com/{repo}.git", timeout=1800)
        lines = [x for x in (r.stdout or "").strip().splitlines() if x.strip()]
        tag = lines[-1] if lines else ""
        if tag == "OK":
            return True
        if tag == "CLONED":
            log(f"clone 缓存 {repo} 完成")
            return True
        log(f"clone 失败 {repo}: {(r.stderr or r.stdout or '')[-200:]}")
        return False

    def prepare(self, tid, prof):
        t = self.tasks[tid]
        repo, base = t["repo"], t["base_commit"]
        slug = repo.replace("/", "__")
        work = f"{REMOTE_ROOT}/runs/{tid}-{prof}"
        if not self.ensure_repo(repo):
            return None
        r = ssh(
            f"rm -rf {work} && git clone --quiet --shared {REMOTE_ROOT}/repos/{slug} {work} && "
            f"cd {work} && git checkout --quiet --detach {base} && git rev-parse HEAD",
            timeout=900)
        if r.returncode != 0:
            err_tail = (r.stderr or "")[-200:]
            log(f"prepare 失败 {tid}|{prof}: {err_tail}")
            if ("unable to read tree" in (r.stderr or "")
                    or "does not exist" in (r.stderr or "")):
                # 缓存毒化（refs 在、对象缺）或缓存被外力删除：加锁清理，
                # 下一 attempt 的 ensure_repo 会重 clone 自愈（2026-10-22）
                ssh(f"flock {REMOTE_ROOT}/repos/.{slug}.lock rm -rf "
                    f"{REMOTE_ROOT}/repos/{slug}", timeout=300)
                log(f"缓存毒化清理 repos/{slug}（下次 attempt 将重新 clone）")
            return None
        base_hash = r.stdout.strip()
        # 组合补丁①：--trim-history（默认关）。开启时 prepare 之后把工作区 refs 裁剪到 base
        # （删 base 之后可达 refs + reflog expire + gc --prune=now），三面校验不闭合即
        # fail-closed（本任务判 prepare_failed，绝不在未闭合工作区上解题）。
        if TRIM_HISTORY:
            tr = ssh(f"$HOME/mcode-swev/{TRIM_SCRIPT} {work} {base_hash}", timeout=1800)
            out = (tr.stdout or "") + (tr.stderr or "")
            detail = ""
            for line in out.splitlines():
                if line.startswith("TRIM_DETAIL"):
                    detail = line.strip()
            if "TRIM_RESULT OK" not in out:
                log(f"trim-history 三面不闭合 {tid}|{prof}（fail-closed）: {detail or out[-300:]}")
                return None
            log(f"trim-history 完成 {tid}|{prof}: {detail}")
        ssh(f"cat > {work}/prompt.txt", timeout=60,
            input_text=PROMPT_TMPL.format(ps=t["problem_statement"]), check=True)
        return {"work": work, "base": base_hash}

    def solve(self, tid, prof, prep):
        model = PROFILES[prof]
        t0 = time.time()
        r = ssh(
            f'$HOME/mcode-swev/run-one.sh {prep["work"]} {model} {prep["work"]}/prompt.txt '
            f'{prep["work"]}/mcode.log {SOLVE_TIMEOUT}',
            timeout=SSH_TIMEOUT)
        wall_ms = int((time.time() - t0) * 1000)
        rc = r.returncode
        quota_hit = rc == 42 or "QUOTA_HIT" in r.stdout
        return rc, wall_ms, quota_hit

    def collect(self, tid, prof, prep):
        work, base = prep["work"], prep["base"]
        r = ssh(f"cd {work} && git add -A && git diff {base} --binary > patch.diff 2>/dev/null; "
                f"wc -c < patch.diff", timeout=300)
        size = -1
        try:
            size = int(r.stdout.strip().splitlines()[-1])
        except Exception:
            pass
        runs = out_dir(prof, self.tasks[tid]["tier"])
        os.makedirs(runs + "/runs", exist_ok=True)
        rd = f"{runs}/runs/{tid}"
        os.makedirs(rd, exist_ok=True)
        patch = None
        if size and size > 0:
            p = ssh(f"cat {work}/patch.diff", timeout=300)
            if "diff --git" in p.stdout:
                with open(f"{rd}/patch.diff", "w") as f:
                    f.write(p.stdout)
                patch = f"{rd}/patch.diff"
        lg = ssh(f"cat {work}/mcode.log 2>/dev/null", timeout=120)
        if lg.stdout:
            with open(f"{rd}/mcode.log", "w") as f:
                f.write(lg.stdout)
        ssh(f"rm -rf {work}", timeout=300)
        return patch, rd

    # ---- judge ----
    def judge(self, tid, prof, patch, rd, rc, wall_ms):
        t = self.tasks[tid]
        task_json = f"{TASKS_DIR}/{tid}.json"
        note_extra = f"mcode exec route={PROFILES[prof]} os_timeout={SOLVE_TIMEOUT}s rc={rc}"
        if rc == 124:
            status = "timeout"
        else:
            status = "completed"
        reward = None
        verifier_note = f"no model patch produced (rc={rc}, {note_extra})"
        if patch:
            with self.judge_lock:  # 串行判分（cal2 教训：安静判分防 OOM 假失败）
                jr = sh(["bash", JUDGE, task_json, patch, rd], timeout=1500)
            if jr.returncode == 2:
                status = "apply_failed"
                reward = False
                verifier_note = f"patch apply failed; {note_extra}"
            else:
                try:
                    jj = json.load(open(f"{rd}/judge.json"))
                    reward = bool(jj.get("resolved"))
                    status = "completed"
                    verifier_note = f"judge: {json.dumps(jj, ensure_ascii=False)}; {note_extra}"
                except Exception as e:
                    status = "judge_error"
                    reward = None
                    verifier_note = f"judge.json unreadable ({e}); rc={jr.returncode}; {note_extra}"
        row = {
            "suite": "swe-v",
            "task_id": tid,
            "profile": f"mcode-{prof}",
            "trial": False,
            "reward": reward,
            "status": status,
            "scaffold": "mcode-official",
            "gate": "ok",
            "attempts": 1,
            "turns": None,
            "model_calls": None,
            "tokens": None,
            "agent_wall_ms": wall_ms,
            "verifier_note": verifier_note,
        }
        self.append_row(row, t["tier"])
        return row

    def append_row(self, row, tier):
        line = json.dumps(row, ensure_ascii=False) + "\n"
        prof = row["profile"].replace("mcode-", "")
        for path in (f"{out_dir(prof, tier)}/results.jsonl", agg_file(prof)):
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with _log_lock:
                with open(path, "a") as f:
                    f.write(line)

    def append_row_paths(self, row, paths):
        """按指定路径追加记账行（自测用：写真实判分链的结果，但不碰生产 results.jsonl）。"""
        line = json.dumps(row, ensure_ascii=False) + "\n"
        for path in paths:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with _log_lock:
                with open(path, "a") as f:
                    f.write(line)

    # ---- D-34：judge_error 只重判不重跑（不重跑 solve）----
    def freeze_check(self):
        """对照 §0.3 冻结表（判分链静态指纹）。任一漂移 → 不重判、直接登记安灯。"""
        items = [
            ("tools/cb-judge.sh", f"{WS}/tools/cb-judge.sh"),
            ("tools/swev-judge.py", f"{WS}/tools/swev-judge.py"),
            ("swev-venv/bin/python", VENV_PY),
        ]
        bad = []
        for name, path in items:
            want = FREEZE_JUDGE_SHA.get(name)
            if not want:
                continue
            try:
                h = hashlib.sha256(open(path, "rb").read()).hexdigest()
            except OSError as e:
                bad.append(f"{name}:读不到({e})")
                continue
            if h != want:
                bad.append(f"{name}:{h[:12]}≠{want[:12]}")
        try:
            r = subprocess.run([VENV_PY, "-m", "pip", "freeze"], capture_output=True,
                               text=True, timeout=120)
            h = hashlib.sha256(r.stdout.encode()).hexdigest()
        except Exception as e:
            h = f"ERR:{type(e).__name__}"
        want = FREEZE_JUDGE_SHA.get("swev-venv/pip-freeze")
        if want and h != want:
            bad.append(f"swev-venv/pip-freeze:{str(h)[:12]}≠{want[:12]}")
        return (not bad), ("; ".join(bad) if bad else "四件冻结值全同")

    @staticmethod
    def eval_log_parsed(path):
        """与 tools/swev-judge.py 的 log_parsed 同口径（Start/End Test Output 标记齐在=日志完整）。"""
        try:
            text = open(path, encoding="utf-8", errors="replace").read()
        except OSError:
            return False
        return "Start Test Output" in text and "End Test Output" in text

    def already_corrected(self, tid, prof, tier):
        """该 (task,profile) 是否已有 judge_error 之后的更正行（修理组 3 例手工改账先例）。
        有 → 不重复落账（除非 --force）。"""
        paths = [f"{out_dir(prof, tier)}/results.jsonl", agg_file(prof)]
        seen_err = False
        for p in paths:
            try:
                lines = open(p, encoding="utf-8").read().splitlines()
            except OSError:
                continue
            for line in lines:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("task_id") != tid or r.get("profile") != f"mcode-{prof}":
                    continue
                if r.get("status") == "judge_error":
                    seen_err = True
                    continue
                if seen_err and r.get("reward") is not None:
                    return True
        return False

    def rejudge(self, tid, prof, rd, tier, results_paths=None, force=False):
        """D-34：judge_error 只重判不重跑。
        路径：log_parsed 可解析 → 重放 swev-judge（不碰容器）；截断型 → 完整重判（cb-judge.sh 容器）。
        账法（修理组 3 例先例）：原 judge_error 行保留，本函数只追加更正行——attempts=2、
        verifier_note 前缀 rejudge-correction:、correction 字段带 basis 与 evidence 路径。
        返回更正行 dict；不可重判时返回 None（原因已入日志）。"""
        t = self.tasks[tid]
        task_json = f"{TASKS_DIR}/{tid}.json"
        patch = f"{rd}/patch.diff"
        if not os.path.exists(patch):
            log(f"rejudge 放弃 {tid}|{prof}：无补丁 {patch}（只重判不重跑→需人工 once 补跑）")
            return None
        if not force and self.already_corrected(tid, prof, tier):
            log(f"rejudge 跳过 {tid}|{prof}：已有 judge_error 之后的更正行（不重复落账；--force 可覆盖）")
            return None
        ok, why = self.freeze_check()
        if not ok:
            log(f"rejudge 安灯 {tid}|{prof}：判分链冻结值漂移，不重判（{why}）")
            return None
        parsed = self.eval_log_parsed(f"{rd}/eval.log")
        basis = "swev-replay" if parsed else "full-rejudge"
        last = None
        for attempt in range(1, REJUDGE_MAX_ATTEMPTS + 1):
            with self.judge_lock:  # 判分锁：与 judge() 同款串行，防并发判分压垮机器
                if parsed:
                    # 可解析 → 只重放 swev-judge（读既有 eval.log，不重跑容器）
                    r = sh([VENV_PY, f"{WS}/tools/swev-judge.py", task_json,
                            f"{rd}/eval.log", patch], timeout=REJUDGE_TIMEOUT)
                else:
                    # 截断型 → 完整重判（容器内重跑 eval_script + 官方判分）
                    r = sh(["bash", JUDGE, task_json, patch, rd], timeout=REJUDGE_TIMEOUT)
            blob = f"{r.stdout or ''}\n{r.stderr or ''}"
            last = r
            if r.returncode == 0:
                break
            if re.search(QUOTA_PATTERNS, blob, re.I):
                log(f"rejudge 推迟 {tid}|{prof}（attempt {attempt}）：命中配额形态，不烧重试")
                try:
                    os.makedirs(STATE_ROOT, exist_ok=True)
                    with open(DEFERRED_LOG, "a") as f:
                        f.write(f"{time.strftime('%F %T')} rejudge-quota {tid}|{prof}\n")
                except Exception:
                    pass
                return None
            if attempt < REJUDGE_MAX_ATTEMPTS:
                log(f"rejudge {tid}|{prof} attempt {attempt} 失败 rc={r.returncode}，"
                    f"{REJUDGE_BACKOFF}s 后重试")
                time.sleep(REJUDGE_BACKOFF)
        # 解析判定结果
        resolved = None
        evidence = ""
        status = "completed"
        if last.returncode == 2:
            status = "apply_failed"
            resolved = False
            evidence = f"{rd}/apply.log"
        else:
            payload = None
            if parsed:
                try:
                    payload = json.loads((last.stdout or "").strip().splitlines()[-1])
                except Exception:
                    payload = None
                if payload is not None:
                    ev = f"{rd}/judge.rejudge.json"
                    with open(ev, "w") as f:
                        json.dump(payload, f, ensure_ascii=False)
                    evidence = ev
            else:
                try:
                    payload = json.load(open(f"{rd}/judge.json"))
                except Exception:
                    payload = None
                if payload is not None:
                    evidence = f"{rd}/judge.json"
            if payload is None:
                log(f"rejudge 失败 {tid}|{prof}：重判后仍无判定（rc={last.returncode}）")
                return None
            resolved = bool(payload.get("resolved"))
        corr = {
            "suite": "swe-v",
            "task_id": tid,
            "profile": f"mcode-{prof}",
            "trial": False,
            "reward": resolved,
            "status": status,
            "scaffold": "mcode-official",
            "gate": "ok",
            "attempts": 2,
            "turns": None,
            "model_calls": None,
            "tokens": None,
            "agent_wall_ms": None,
            "verifier_note": (f"rejudge-correction: basis={basis}; evidence={evidence}; "
                              f"原 judge_error 行保留不改写; profile={prof}; tid={tid}"),
            "correction": {
                "of_status": "judge_error",
                "basis": basis,
                "evidence": evidence,
                "frozen_chain": why,
                "ts": time.strftime("%F %T"),
            },
        }
        if results_paths:
            self.append_row_paths(corr, results_paths)
        else:
            self.append_row(corr, tier)
        self.set_phase(tid, prof, phase="judged", reward=resolved, status=status,
                       rejudged=1, correction_basis=basis)
        log(f"rejudge 更正落账 {tid}|{prof}: status={status} reward={resolved} basis={basis}")
        return corr

    # ---- pipeline ----
    def run_one(self, tid, prof):
        t = self.tasks[tid]
        if not self.disk_ok():
            log(f"磁盘余量不足 {DISK_MIN_GB}G，等待 300s 后重试 {tid}|{prof}")
            for _ in range(30):
                if self.stop.is_set():
                    return
                time.sleep(10)
                if self.disk_ok():
                    break
        ph = self.phase(tid, prof)
        log(f"开始 {tid}|{prof} (phase={ph})")
        prep = self.prepare(tid, prof)
        if prep is None:
            self.set_phase(tid, prof, phase="prepare_failed")
            row = {"suite": "swe-v", "task_id": tid, "profile": f"mcode-{prof}",
                   "trial": False, "reward": None, "status": "prepare_failed",
                   "scaffold": "mcode-official", "gate": "ok", "attempts": 1,
                   "turns": None, "model_calls": None, "tokens": None,
                   "agent_wall_ms": None,
                   "verifier_note": "workspace prepare failed on anolis (clone/checkout)"}
            self.append_row(row, t["tier"])
            return
        self.set_phase(tid, prof, phase="solving", base=prep["base"])
        rc, wall_ms, quota_hit = self.solve(tid, prof, prep)
        if quota_hit:
            self.quota[prof] = True
            open(f"{STATE_ROOT}/QUOTA-{prof}", "w").write(time.strftime("%F %T") + "\n")
            log(f"QUOTA 熔断：{prof} 通道（{tid} 触发），剩余该档案任务跳过")
            self.set_phase(tid, prof, phase="quota")
            return
        patch, rd = self.collect(tid, prof, prep)
        self.set_phase(tid, prof, phase="collected", rc=rc, wall_ms=wall_ms,
                       patch=bool(patch))
        row = self.judge(tid, prof, patch, rd, rc, wall_ms)
        # D-34（组合补丁②）：judge_error 只重判不重跑——不重跑 solve，就地走重判支路。
        # 原 judge_error 行已由 judge() 落账且保留不改写；更正行由 rejudge() 追加。
        if row["status"] == "judge_error":
            log(f"judge_error → D-34 只重判不重跑支路 {tid}|{prof}")
            corr = self.rejudge(tid, prof, rd, t["tier"])
            if corr is not None:
                row = corr
        self.set_phase(tid, prof, phase="judged", reward=row["reward"], status=row["status"])
        log(f"完成 {tid}|{prof}: status={row['status']} reward={row['reward']} "
            f"wall={wall_ms/1000:.0f}s")

    def _note_failure(self, tid, prof, ph, q):
        """失败计次并按需重排队（2026-10-22：prepare_failed/error 不再一次判死）。"""
        with self.attempts_lock:
            n = self.attempts.get((tid, prof), 0) + 1
            self.attempts[(tid, prof)] = n
        if n < MAX_ATTEMPTS:
            log(f"重排队 {tid}|{prof}（phase={ph}，第 {n} 次失败，{RETRY_DELAY}s 后重试，"
                f"每进程上限 {MAX_ATTEMPTS} 次）")
            time.sleep(RETRY_DELAY)
            q.put((tid, prof))
        else:
            log(f"放弃 {tid}|{prof}（phase={ph}，已达每进程 {MAX_ATTEMPTS} 次尝试上限，"
                f"可人工 once 补跑）")

    def worker(self, q):
        while not self.stop.is_set():
            # 补丁① R2：取任务前先过资源闸——闸闭则任务永不出队（无重排队逻辑），
            # 在飞 solve 不经预检、自然收尾后资源回落自动解除。推迟不写 phase、
            # 不调 _note_failure（不烧 attempts）。defer_tick 返回 "halt"（连续推迟
            # >DEFER_HALT_S）时同样不取：停取新任务保持升级态等人工，心跳照刷。
            # tmpfs 第四探针同批加固：闸段任何异常（ENOSPC 撞 log/心跳/簿记路径等）
            # 只本轮跳过取任务，绝不炸 worker 线程（线程死=无人刷心跳+队列无人消费，
            # keepalive 2400s 后误判重启，正中自反馈死法）。
            try:
                ok, _why = self.gate.probe()
                if not ok:
                    self.gate.defer_tick()
                    time.sleep(60)
                    continue
                self.gate.opened()
            except Exception as e:
                log(f"[gate] 闸段异常（不致命，本轮跳过取任务）: {type(e).__name__} {e}")
                time.sleep(60)
                continue
            try:
                tid, prof = q.get(timeout=5)
            except Exception:
                return
            try:
                ph = self.phase(tid, prof)
                if ph == "judged":
                    continue
                if self.quota[prof]:
                    continue
                self.run_one(tid, prof)
                ph = self.phase(tid, prof)
                if ph in ("prepare_failed", "error"):
                    self._note_failure(tid, prof, ph, q)
            except Exception as e:
                log(f"异常 {tid}|{prof}: {type(e).__name__} {e}")
                self.set_phase(tid, prof, phase="error", err=str(e)[:300])
                self._note_failure(tid, prof, "error", q)
            finally:
                q.task_done()

    def build_queue(self, tiers=None, limit=None):
        items = []
        for t in sorted(self.plan, key=lambda x: (TIER_ORDER.get(x["tier"], 9), x["instance_id"])):
            if tiers and t["tier"] not in tiers:
                continue
            for prof in PROFILES:
                items.append((t["instance_id"], prof))
        if limit:
            items = items[:limit]
        q = queue.Queue()
        for it in items:
            q.put(it)
        return q


def single_instance():
    os.makedirs(STATE_ROOT, exist_ok=True)
    try:
        old = open(PIDFILE).read().strip()
        if old and os.path.exists(f"/proc/{old}"):
            with open(f"/proc/{old}/cmdline", "rb") as f:
                if b"mcode-dispatch" in f.read():
                    print(f"mcode-dispatch 已在跑 pid={old}，拒绝双实例", file=sys.stderr)
                    sys.exit(3)
    except FileNotFoundError:
        pass
    with open(PIDFILE, "w") as f:
        f.write(str(os.getpid()))


def cmd_run(args):
    single_instance()
    d = Dispatcher()
    d.deploy()
    log(f"mcode-dispatch 常驻启动 pid={os.getpid()} workers={MCODE_WORKERS} "
        f"quota0={d.quota}")
    log(f"[gate] 资源闸生效: mem≥{GATE_MEM_MIN_GB}G disk≥{GATE_DISK_MIN_GB}G "
        f"remote≥{GATE_REMOTE_MIN_GB}G tmpfs≥{GATE_TMPFS_MIN_GB}G cache={GATE_CACHE_S:.0f}s "
        f"hb={DEFER_HB_S:.0f}s escalate>{DEFER_ESCALATE_S:.0f}s halt>{DEFER_HALT_S:.0f}s")
    tiers = set(args.tiers.split(",")) if args.tiers else None
    q = d.build_queue(tiers=tiers)
    threads = [threading.Thread(target=d.worker, args=(q,), daemon=True,
                                name=f"w{i}") for i in range(MCODE_WORKERS)]
    for th in threads:
        th.start()
    try:
        q.join()
    except KeyboardInterrupt:
        d.stop.set()
    # 等在途任务收尾（队列已空，worker 会自然退出）
    for th in threads:
        th.join(timeout=SSH_TIMEOUT)
    log("mcode-dispatch 队列跑完退出")


def cmd_once(args):
    # 补丁① R2：once 本体不拦人工补跑（人工知情动作）——闸闭只横幅警告 + deferred.log。
    # 硬拒绝（exit 4）在 tools/mcode-once-wrapper.sh（无人值守调用方应走 wrapper）。
    ok, why = GATE.probe()
    if not ok:
        reasons = "；".join(why)
        print(f"⚠ 资源闸闭，once 照跑（人工知情放行）：{reasons}", file=sys.stderr)
        log(f"once {args.tid}|{args.profile} 闸闭照跑（人工知情）: {reasons}")
        try:
            os.makedirs(STATE_ROOT, exist_ok=True)
            with open(DEFERRED_LOG, "a") as f:
                f.write(f"{time.strftime('%F %T')} once-manual 闸闭照跑 "
                        f"{args.tid}|{args.profile}: {reasons}\n")
        except Exception:
            pass
    d = Dispatcher()
    d.deploy()
    if args.tid not in d.tasks:
        sys.exit(f"未知任务 {args.tid}")
    d.run_one(args.tid, args.profile)


def cmd_rejudge(args):
    """D-34 backlog：judge_error 只重判不重跑。默认只列清单（不落账），--apply 才真跑。
    跑前逐件过 §0.3 冻结表；冻结漂移 → 不重判。已有更正行者跳过（--force 覆盖）。"""
    d = Dispatcher()
    items = []
    for key, v in d.state.items():
        if v.get("phase") == "judged" and v.get("status") == "judge_error":
            tid, _, prof = key.partition("|")
            items.append((tid, prof))
    items.sort()
    if not items:
        print("无 judge_error 终态条目（state.json 全 judged 且无 judge_error）")
        return
    plan = []
    for tid, prof in items:
        tier = d.tasks[tid]["tier"]
        rd = f"{out_dir(prof, tier)}/runs/{tid}"
        has_patch = os.path.exists(f"{rd}/patch.diff")
        parsed = d.eval_log_parsed(f"{rd}/eval.log")
        done = d.already_corrected(tid, prof, tier)
        path = "重放 swev-judge" if parsed else "完整重判(cb-judge.sh 容器)"
        plan.append((tid, prof, tier, rd, has_patch, parsed, done, path))
        print(f"{tid}|{prof}  tier={tier} 补丁={'有' if has_patch else '无'} "
              f"log_parsed={parsed} 路径={path} 已有更正行={done}")
    if not args.apply:
        print("\n（默认只列清单，未落账；要真跑加 --apply）")
        return
    ok, why = d.freeze_check()
    print(f"冻结表对照：{why}")
    if not ok:
        print("冻结值漂移——不重判（安灯）")
        return
    for tid, prof, tier, rd, has_patch, parsed, done, path in plan:
        if not has_patch:
            print(f"跳过 {tid}|{prof}：无补丁（需人工 once 补跑）")
            continue
        if done and not args.force:
            print(f"跳过 {tid}|{prof}：已有更正行（--force 可覆盖）")
            continue
        corr = d.rejudge(tid, prof, rd, tier, force=args.force)
        print(f"{tid}|{prof} → " + ("已落更正行" if corr else "未落账（见日志）"))


def cmd_gatecheck(_args):
    """只读探测资源闸（供 mcode-once-wrapper.sh 与人工巡检）。exit 0=开，4=闭。"""
    ok, why = GATE.probe()
    if ok:
        print("GATE OPEN（四条件全过：本机内存/本机docker分区/anolis /data/本机 /tmp）")
        return
    for w in why:
        print(f"GATE CLOSED: {w}", file=sys.stderr)
    sys.exit(4)


def cmd_deploy(_args):
    Dispatcher().deploy()
    print("helpers 已部署到 anolis:~/mcode-swev/")


def cmd_summary(_args):
    st = load_state()
    plan = json.load(open(PLAN))
    tiers = ["D1", "D2", "D3"]
    print(f"{'档':4s} {'档案':16s} {'判分':>4s} {'pass':>5s} {'fail':>5s} {'未判/在途':>6s} 通过率")
    tot = {}
    for tier in tiers:
        ids = {t["instance_id"] for t in plan if t["tier"] == tier}
        for prof in PROFILES:
            judged = passed = 0
            inflight = 0
            for tid in ids:
                e = st.get(f"{tid}|{prof}")
                if not e:
                    continue
                ph = e.get("phase")
                if ph == "judged":
                    judged += 1
                    passed += 1 if e.get("reward") else 0
                else:
                    inflight += 1
            tot[(tier, prof)] = (judged, passed, inflight)
            rate = f"{passed/judged*100:.1f}%" if judged else "-"
            print(f"{tier:4s} {'mcode-'+prof:16s} {judged:4d} {passed:5d} {judged-passed:5d} "
                  f"{inflight:6d} {rate}")
    for prof in PROFILES:
        j = sum(tot[(t, prof)][0] for t in tiers)
        p = sum(tot[(t, prof)][1] for t in tiers)
        f_ = sum(tot[(t, prof)][2] for t in tiers)
        rate = f"{p/j*100:.1f}%" if j else "-"
        print(f"ALL  {'mcode-'+prof:16s} {j:4d} {p:5d} {j-p:5d} {f_:6d} {rate}")
    for prof in PROFILES:
        qf = f"{STATE_ROOT}/QUOTA-{prof}"
        if os.path.exists(qf):
            print(f"QUOTA 熔断: {prof} (自 {open(qf).read().strip()})")
    # 2026-10-22：非 judged 明细——区分"真在飞(solving)"与"失败态(prepare_failed/error)"，
    # 避免把积压失败误读成在飞活锁（D2 停滞误判源）
    for tier in tiers:
        ids = {t["instance_id"] for t in plan if t["tier"] == tier}
        for prof in PROFILES:
            cnt = {}
            for tid in ids:
                e = st.get(f"{tid}|{prof}") or {}
                ph = e.get("phase")
                if ph and ph != "judged":
                    cnt[ph] = cnt.get(ph, 0) + 1
            if cnt:
                detail = " ".join(f"{k}={v}" for k, v in sorted(cnt.items()))
                print(f"     {tier} mcode-{prof} 非判分态明细: {detail}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run")
    r.add_argument("--tiers", help="逗号分隔 D1,D2,D3（默认全部）")
    r.add_argument("--trim-history", action="store_true",
                   help="组合补丁①：prepare 后把工作区 refs 裁剪到 base（默认关；删 base 之后可达 "
                        "refs + reflog expire + gc --prune=now，三面校验不闭合即 fail-closed）")
    o = sub.add_parser("once")
    o.add_argument("tid")
    o.add_argument("profile", choices=list(PROFILES))
    o.add_argument("--trim-history", action="store_true",
                   help="组合补丁①：同上（默认关）")
    sub.add_parser("summary")
    sub.add_parser("deploy")
    j = sub.add_parser("rejudge", help="D-34：judge_error 只重判不重跑（默认只列清单）")
    j.add_argument("--apply", action="store_true", help="真跑重判并落更正行（默认不落账）")
    j.add_argument("--force", action="store_true", help="已有更正行也重跑（默认跳过，防重复落账）")
    sub.add_parser("gate-check",
                   help="只读探测资源闸：exit 0=开 / 4=闭（wrapper 与人工巡检用）")
    a = ap.parse_args()
    if getattr(a, "trim_history", False):
        global TRIM_HISTORY
        TRIM_HISTORY = True
    {"run": cmd_run, "once": cmd_once, "summary": cmd_summary,
     "deploy": cmd_deploy, "rejudge": cmd_rejudge,
     "gate-check": cmd_gatecheck}[a.cmd](a)


if __name__ == "__main__":
    main()
