# mcode dispatch 组合补丁 · 交付（①refs 裁剪 flag ②D-34 只重判 ③keepalive 完成态）

> 实施人：组合补丁实施员（子会话）｜as-of 2026-10-22 15:0x（锚点行号以本单落码时盘上版本为准）
> 施工依据：设计/底座重构施工方案.md v3 §8.1–§8.3（T0-5）；技术债登记.md D-34（:42）
> 硬纪律遵守：①改前已备份 ②判分链/超时/判分参数零改动 ③refs 裁剪只做**默认关闭的 flag**
> ④gov/密钥/在飞臂零接触 ⑤卡住升级提问、不编造

---

## 0. 一句话交付

三项单点改动全部落码并各自可独立回滚；**现役行为零变化**（①默认关、②仅在 judge_error 时触发、
③仅在队列已排空时改变拉起决策）；bounce 抖环已止（换血后 dispatch 拉起次数 = 0）。

---

## 1. 改前基线与备份

| 文件 | 现役 sha256（落码后） | 改前备份 |
|---|---|---|
| `tools/mcode-dispatch.py` | `57bf50bf2b9ba7d4ebe915fd490db9fc13fb75b5843ce71428421922a7278406` | `工具状态备份/mcode-dispatch.py.pre-t0-combo-20261022-143448`（`3187896c3fe74c7ea157e37c69b2f1a1c53d3b33ae07c69811c2c98c841597c6`） |
| `tools/factory-keepalive.py` | `8d5617cd521c527c3c6e97a0a9a5011217dcd8bf18958d27c5fdd2a38156b704` | `工具状态备份/factory-keepalive.py.pre-t0-combo-20261022-143448`（`857fb23149d4f76f2a0dc91d3d741b339fad2b579fdf34d7e128453c92aa300b`） |

> ⚠️ **改前备份的 mtime 是 14:34:34**，即 ④资源组同窗改 ch-mes-local 查询级探针**之前**。
> ④组在 14:44:18 另留 `工具状态备份/factory-keepalive.py.pre-mes-query-probe-20261022`（=含本单③的版本）。
> → **整文件回滚会连带回退 ④ 的在役改动**，故本单另出外科式回滚补丁（见 §6）。

**同窗并发事实（须让主会话知悉）**：14:44:25–14:44:26 有第三方重启了 keepalive（新 pid 636996），
它直接加载了本单已落码的 ③ → klog 出现 `14:44:27 queue_drained：state 240 键全终态…`（本单③的
首条现役证据）。两单改动在文件层面**互不覆盖、合并无损**（diff 核对：④ 的 ch-mes-local 段完整保留）。

---

## 2. ① refs 裁剪（--trim-history，默认关）

### 落码位置
- `tools/mcode-dispatch.py:129-134` 常量 `TRIM_HISTORY=False`（默认关，硬纪律③）
- `tools/mcode-dispatch.py:310-...` 远端脚本 `TRIM_HISTORY_SH`（`trim-history.sh`）
- `tools/mcode-dispatch.py:731` 部署：**仅 flag 开启时**才写 anolis `~/mcode-swev/trim-history.sh`
  （默认关 = anolis 侧零新文件）
- `tools/mcode-dispatch.py:785-798` `prepare()` 内裁剪 + 三面校验，**不闭合即 fail-closed**（返回 None → prepare_failed）
- `tools/mcode-dispatch.py:1377/1383` `run`/`once` 子命令的 `--trim-history` 开关

### 裁剪机制（顺序不可换，已实测）
1. **refs 面**：删 base 之后可达的引用；`refs/tags/*` 一律删（tag 是考古通道）。
   必须用 `git update-ref --no-deref -d`——**否则 symref（refs/remotes/origin/HEAD）会被解析到其目标，
   删掉目标后留下悬垂 symref**（首轮演练实测踩中，fsck 报 `invalid sha1 pointer 0000…`）。
2. **gc 面（关键）**：`--shared` 克隆的 `objects/info/alternates` 是考古后门（v3 §8.3-a 记载的残余风险）。
   做法 = **定向 pack**（`git rev-list --objects $BASE | git pack-objects --stdout` + `index-pack`）
   把 base 可达对象搬进本仓 → 删 alternates → 复验 base 对象仍在场（不在场即中止，工作区已废）→ `gc --prune=now`。
   *为什么不用 `repack -a -d`*：它会把整条上游历史搬进工作区（实测 requests 全量 5.8M pack vs 定向 28K 量级差异，
   大仓不可接受）；定向 pack 还必须**在删 refs 之后、拆 alternates 之前**做（顺序错则 gc 报 `bad object`）。
3. **reflog 面**：`reflog expire --expire=now --expire-unreachable=now --all` + 删 `.git/logs` 目录。

### 三面校验（任一不闭合 = fail-closed）
| 面 | 判据 |
|---|---|
| refs | `for-each-ref` 无 tag；残留引用必须全是 base 祖先；`rev-list --all --count` == `rev-list $BASE --count` |
| reflog | `reflog --all` 行数 == 0 且 `.git/logs` 下文件数 == 0 |
| gc | alternates 不在场；**物理 commit 对象数 == base rev-list 数**（未来提交物理不在场，非「仅限已知哈希」） |

### 实测证据（全部在 anolis 真实 git 2.47.3 上跑）
- **演练（合成仓）**：`bash /tmp/trim-rehearsal.sh` → `RESULT: PASS（三面闭合）`；裁剪前 `rev-list --all=5≠base=3`、
  tag 存活、alternates 在场、post-base 对象 `cat-file -t` = commit；裁剪后 refs=0/tags=0/--all=base=3、
  reflog 0/0、alternates=none、物理 commit=3、`cat-file -t <post-base>` = "could not get object info"、fsck 干净。
- **门有效性（5 变体，负向对照）**：`bash /tmp/trim-gate-test.sh` → `门有效性：PASS=5 FAIL=0`
  （变体1 全量→PASS；变体2 漏删 alternates→FAIL[gc(alternates在) gc(物理commit=5≠3)]；
  变体3 漏 reflog→FAIL[reflog(lines=2 files=1) gc(物理commit=5≠3)]；变体4 漏删 refs→FAIL[refs(tag残留1) refs(--all=5≠3) …]；
  变体5 裁剪后仍能出补丁 104B）→ **三面校验是有效的闸，不是装饰**。
- **真仓真代码路径**：`TRIM_HISTORY=True` 调 `prepare('psf__requests-1142','m31f')`（3s）→
  `TRIM_DETAIL … refs_left=0 all=2576 base=2576 tags=0 reflog_lines=0 reflog_files=0 phys=2576 alt=none`；
  不经 dispatch 代码的独立复核：refs=0 tags=0 / `--all=2576`=`base=2576` / reflog 0·0 / alternates=none /
  物理 commit=2576 / HEAD detached 正确 / 工作树 14 项完整 / 模拟解题出补丁 1355B（含 2 个 diff --git）。
  - fsck 有一条 `badTimezone` 报错 → **对照缓存仓同样存在**（上游 requests 历史自身数据形态，非裁剪引入）。
  - 上游缓存仓**未被改动**（171 refs 仍在）：裁剪只作用于模型工作区。
  - 演练工作区已清理（`rm -rf /data/bench/mcode-swev/runs/psf__requests-1142-m31f`）。

### 边界与分歧登记（须主会话裁决）
- **与 v3 §8.3(a) 的分歧**：v3 已把「五命令 refs 裁剪」作废、改为 bundle 机制（clean-prep.sh 单 rev bundle）。
  本单按**本单指令**实现的是 flag 版裁剪（默认关 = 与现行行为并存，不与 bundle 机制冲突）；
  且本单三面校验**闭合了 v3 记录的 tag 存活 / alternates 可枚举两处泄漏**（v3 §8.3-a 残余风险段）。
  若主会话决定走 bundle 路线，本单①的 flag 可整体下架（回滚行见 §6），bundle 与 flag 二者不叠加启用。
  现场佐证（as-of 15:0x）：anolis `~/mcode-swev/` 已有 `clean-prep.sh` + `run-one-clean.sh`（在飞干净重跑线的 bundle 机制），
  本单①的 `trim-history.sh` 已清理下盘（默认关=零足迹；flag 开启时 `deploy()` 会自动重建）。
- ①**不覆盖** v3 §8.3-c（`MCODE_OUT_ROOT` env 化）与 §8.1（MES 轻量查询探针）——本单指令只含三项，
  这两项未实现（§8.1 已由 ④ 组同窗在 keepalive 落地）。

---

## 3. ② D-34：judge_error 只重判不重跑

### 落码位置
- `tools/mcode-dispatch.py:908` `freeze_check()`（§0.3 冻结表四件逐件对照，漂移即不重判、直接安灯）
- `tools/mcode-dispatch.py:939` `eval_log_parsed()`（与 swev-judge.py 同口径：Start/End Test Output 标记齐在）
- `tools/mcode-dispatch.py:947` `already_corrected()`（已有更正行者跳过，防重复落账）
- `tools/mcode-dispatch.py:971` `rejudge()`（支路本体）
- `tools/mcode-dispatch.py:1122` `run_one()` 内挂点：judge 返回 judge_error → **就地**走重判支路（不重跑 solve）
- `tools/mcode-dispatch.py:1262` `cmd_rejudge()` + `rejudge` 子命令（backlog 显式处理，默认只列清单）

### 支路语义
- **log_parsed 可解析 → 重放 swev-judge**（读既有 `{rd}/eval.log`，**不碰容器**）；
  **截断型（log_parsed=false）→ 完整重判**（`bash tools/cb-judge.sh`，容器内重跑 eval_script + 官方判分）。
- 判分锁内重试 ≤2 次、退避 60s；rc=1 命中 `QUOTA_PATTERNS`（`mcode-dispatch.py:123`）→ **推迟不烧重试**（写 `deferred.log`）。
- **账法（修理组 3 例先例）**：原 judge_error 行**保留不改写**；只**追加**更正行——
  `attempts=2`、`verifier_note` 前缀 `rejudge-correction:`、新增 `correction` 字段（basis / evidence / frozen_chain / ts）。
- 重放路径的证据另存 `{rd}/judge.rejudge.json`（**不覆盖**原 0 字节的 judge.json）；完整重判沿用 cb-judge.sh 自写 judge.json。
- **测量语义零改动**：判分链脚本、参数、超时、判分内容一律未动（只多调一次同一条链）。

### 实测证据（真实判分链；生产 state.json / results.jsonl 全程零写）
自测脚本 `/tmp/t0d34-selftest.py` → **共 26 项，失败 0 项**：

| 用例 | 结果 |
|---|---|
| A 冻结表四件全同 | OK（四件全同） |
| B 可解析型→重放 swev-judge（django__django-16263\|m3，真跑） | OK 38s，产出更正行，basis=swev-replay，attempts=2，correction 字段带 evidence；**原 judge_error 行零改写**（1→2 行，只追加）；**原 judge.json 未被覆盖（0 字节仍在）**；判定 resolved=**True**（找回一个真阳性） |
| C 已有更正行者跳过 | OK（返回 None，0 行追加） |
| D 冻结漂移 | OK（拒绝重判，0 行追加，日志「安灯」） |
| E 配额形态 rc=1 | OK（推迟，0 行追加，写 deferred.log） |
| F 无补丁 | OK（不重跑，0 行追加） |
| G 截断型→完整重判（pydata__xarray-4687\|m3，真跑容器） | OK 67s，basis=full-rejudge，evidence=judge.json，只追加 1 行，resolved=**False**（与修理组手工改账结论一致） |

- **生产零写核对**：`/tmp/mcode-dispatch/state.json` sha256 前后同为 `3d37af8929106bf6c902a4a19802d13b0f7439aa7bff7b87fe43f6add1117614`；
  生产 results.jsonl mtime/行数未变（d3-m3 38 行、d1-m31f 95 行、m3 聚合 226 行）；自测容器由 cb-judge.sh 的 trap 清除。
- **现役 backlog（`python3 tools/mcode-dispatch.py rejudge` 只列清单）**：

  | task\|profile | tier | 补丁 | log_parsed | 路径 | 已有更正行 |
  |---|---|---|---|---|---|
  | django__django-16263\|m3 | D3 | 有 | True | 重放 swev-judge | 否 |
  | matplotlib__matplotlib-13989\|m31f | D1 | 有 | True | 重放 swev-judge | 否 |
  | pallets__flask-5014\|m3 | D1 | 有 | True | 重放 swev-judge | 是（修理组手工改账） |
  | pydata__xarray-3095\|m3 | D2 | 有 | True | 重放 swev-judge | 是 |
  | pydata__xarray-4687\|m3 | D1 | 有 | **False** | 完整重判（容器） | 是 |

  → **真未更正 2 条**（16263\|m3、13989\|m31f），均为 log_parsed=True → 走廉价重放路径。
  自测已用 16263\|m3 实跑出 resolved=True（沙箱内），**生产账本未动**。
  **是否对这两条正式落账属主会话/运营者决策**（会改官方 results 行数与通过率），本单只交路径不擅自落账。

### 设计取舍（须知悉）
- **backlog 不自动重放**：worker 对 `phase=judged` 仍跳过（`mcode-dispatch.py` worker 分支未改），
  历史 judge_error 不会在守护进程重启时自动弹重判（避免在已排空队列上突然起容器潮）。
  自动路径只覆盖**本次 solve 当场发生的 judge_error**（`run_one` 内就地重判）。
- 显式命令：`python3 tools/mcode-dispatch.py rejudge`（只列清单）→ `rejudge --apply`（真跑落账）→ `--force`（覆盖"已有更正行"跳过规则）。
- **冻结值重基线**：venv 指纹两件是本次实施时实测（as-of 2026-10-22 14:3x）。
  重基线命令：`sha256sum /home/pan-ding/swev-venv/bin/python` 与
  `/home/pan-ding/swev-venv/bin/python -m pip freeze | sha256sum` → 改 `mcode-dispatch.py:144` 的 `FREEZE_JUDGE_SHA` 两行。
  （cb-judge.sh / swev-judge.py 两件与 §0.3 冻结表逐字一致：9c8f9c98… / 0338566c…）

---

## 4. ③ keepalive 完成态判断（止 bounce）

### 落码位置
- `tools/factory-keepalive.py:155` `MCODE_STATE`（可用 `MCODE_DISPATCH_STATE` 环境变量指路 → 供验收②副本演练，不污染真 state）
- `tools/factory-keepalive.py:782` `mcode_dispatch_drained()`：读 state.json，
  `pending=[k for k,v in state.items() if v.get('phase') in (None,'solving','collected')]`
- `tools/factory-keepalive.py:809` `DRAIN_PROBES` 登记表
- `tools/factory-keepalive.py:812-825` `fix_mcode_dispatch()` 完成态分支先行
- `tools/factory-keepalive.py:1130-1140` `one_round()`：防抖超限态下**完成态分支仍放行**（queue_drained 不计入 deb）
- `tools/factory-keepalive.py:1238` 心跳口径：完成态报 `done(queue_drained,…)` 而**不是** `DOWN`（防误读为失联）

### 判读口径（fail-closed 方向 = 不漏拉）
| state 情形 | 判定 | 处置 |
|---|---|---|
| 读不到 / 非法 JSON / 非 dict | 判不准 | 走**现行**判活/拉起 |
| 空表 | 全 pending（新队列） | 走现行拉起 |
| pending 非空（有 solving/collected/无 phase） | 有未完成 | 走现行判活/拉起 |
| pending 空（judged/quota/prepare_failed/error 全终态） | **drained** | **不拉起**；1h 一条 klog `queue_drained` + MES `mes_event('mcode-dispatch','queue_drained')` |

### 换血与验收（§8.2 三条判据）
- **换血前预检**：`/tmp/mcode-dispatch.log` 尾部只有空队列 start/exit，**无进行中的 solve**；
  `ps` 无 `mcode exec`/`run-one.sh` 进程；state.json 240 键全 `judged` → 允许换血。
  换血序：P0-1 干跑（`--dry-run` 输出 8 对象 + 新分支行）→ `kill -TERM $(cat /tmp/factory-keepalive.pid)`
  → 轮询等 pidfile 消失（实测 3×0.5s 内退）→ `setsid nohup python3 tools/factory-keepalive.py >> /tmp/factory-keepalive.out 2>&1 < /dev/null &`
  → 确认落位的是**非 dry-run 实例**（klog「常驻启动 pid=… 周期 30s 看护 8 对象」）。
- **演练脚本** `/tmp/t0-keepalive-rehearsal.py` → **共 9 项，失败 0 项**：
  ① klog 出现显式 `queue_drained` 行（正面证据，非「没看到拉起」）；
  ② 副本 state 注入 `phase='solving'` 假键 → 仍走**拉起**路径（klog「拉起 pid=638706」），真 state 未被污染；
  ③ queue_drained 轮**不计入 deb**（deb 计数 1→1 不变），拉起轮则正常记 deb。
- **换血后现役**：新实例 pid **641328**（14:48:56 起）；换血后 dispatch **拉起次数 = 0**；
  klog 持续出 `queue_drained：state 240 键全终态…——正常完成退出，不拉起（止抖环）`。
  换血后首个心跳（14:57:58 第 19 轮）已如实改口径：
  `mcode-dispatch:done(queue_drained,正常完成退出,不拉起)`（改前口径是 `mcode-dispatch:DOWN(...)`，属误读为失联）。
  （换血前 14:26–14:44 期间是 30s 一轮的 bounce + `ALARM 600s 内已重启 2 次` 防抖报警。）

### 与 v3 §8.2 的差异（据实登记）
- v3 §8.2 的 pending 判据未含 `prepare_failed/error` 之外的终态枚举，本单把 pending 定义为
  `phase ∈ {None, solving, collected}`（与 v3 原文逐字一致），其余 phase（judged/quota/prepare_failed/error）视为终态。
- v3 §8.2 写「副本经环境变量指路」→ 本单以 `MCODE_DISPATCH_STATE` 实现（缺省=真 state，行为不变）。

---

## 5. 未做 / 越界声明

- v3 §8.3-c（`MCODE_OUT_ROOT` env 化）、v3 §8.1（MES 轻量查询探针）**未实现**（不在本单三项内；
  §8.1 已由 ④ 组同窗在 keepalive 落地）。v3 §8.3-a 的 bundle 机制（clean-prep.sh）**未实现**（见 §2 分歧登记）。
- ①的 flag **未在任何生产解题中启用**（默认关）；真实解题路径未被裁剪行为影响。
- ②未对生产账本落任何更正行（自测全程沙箱）。
- 既有服务/gov 容器/在飞臂零接触；fork 的 af-bench-guardrail 采样批零改动（本单只碰 dispatch/keepalive 两文件）。
- 本机 anolis 仓 `psf__requests` 缓存、`/data/bench/mcode-swev/repos/*` 全未改动。

---

## 6. 回滚三行（每项独立可回滚）

```bash
# 回滚①（refs 裁剪 flag）：从 dispatch 摘掉 ① 与 ②（两处同文件，一次摘净）
cp 工具状态备份/mcode-dispatch.py.pre-t0-combo-20261022-143448 tools/mcode-dispatch.py && python3 -m py_compile tools/mcode-dispatch.py

# 回滚②（D-34 只重判）已含在上一行（①②同文件）；若只想单独关②而不动①：把 tools/mcode-dispatch.py 的 run_one() 里
# 「judge_error → D-34 只重判不重跑支路」那段调用删掉（judge() 与 rejudge() 保留即无副作用）

# 回滚③（keepalive 完成态）：外科式——只摘本单③的六处块，保留 ④ 组同窗 ch-mes-local 改动
patch -p0 tools/factory-keepalive.py < 工具状态备份/factory-keepalive.py.revert-t0combo3.patch && python3 -m py_compile tools/factory-keepalive.py
```

回滚后均须按 P0-3 同序换血：`kill -TERM $(cat /tmp/factory-keepalive.pid)` → 等 pidfile 消失 → `setsid nohup python3 tools/factory-keepalive.py >> /tmp/factory-keepalive.out 2>&1 < /dev/null &`。

**整文件回滚 keepalive 的警告**：`cp 工具状态备份/factory-keepalive.py.pre-t0-combo-20261022-143448 tools/factory-keepalive.py`
会把 ④ 组 14:4x 的 ch-mes-local 查询级探针一并回退（该备份早于其改动）→ 须与 ④ 协调，优先用上面的外科式补丁。

---

## 7. 证据索引（本单实跑的命令）

| 用途 | 命令 / 位置 |
|---|---|
| ① 裁剪演练 | `ssh anolis 'bash /tmp/trim-rehearsal.sh /tmp/trim-rehearsal-1'` → `RESULT: PASS（三面闭合）` |
| ① 三面门有效性 | `ssh anolis 'bash /tmp/trim-gate-test.sh'` → `门有效性：PASS=5 FAIL=0` |
| ① 真仓真代码路径 | `python3 -c "…TRIM_HISTORY=True; d.prepare('psf__requests-1142','m31f')"` → `TRIM_DETAIL … refs_left=0 all=2576 base=2576 …phys=2576 alt=none` |
| ② 自测 | `python3 /tmp/t0d34-selftest.py` → `共 26 项，失败 0 项` |
| ② backlog 清单 | `python3 tools/mcode-dispatch.py rejudge` → 5 行（含「默认只列清单，未落账」） |
| ③ 判定表 | `python3 -c` 直调 `mcode_dispatch_drained()`（假键/真 state/空表/非法 JSON/缺文件 5 态全测） |
| ③ 验收演练 | `python3 /tmp/t0-keepalive-rehearsal.py` → `共 9 项，失败 0 项` |
| ③ 换血后现役 | `awk '/常驻启动 pid=641328/,0' /tmp/factory-keepalive.log \| grep -c "拉起 pid="` → `0` |
| 干跑预检 | `python3 tools/factory-keepalive.py --dry-run` → 8 对象全列 + `queue_drained` 分支行 |
| 生产零写核对 | `sha256sum /tmp/mcode-dispatch/state.json`（前后同值 `3d37af89…`） |
| 备份链 | `工具状态备份/mcode-dispatch.py.pre-t0-combo-20261022-143448`、`工具状态备份/factory-keepalive.py.pre-t0-combo-20261022-143448`、`工具状态备份/factory-keepalive.py.revert-t0combo3.patch` |
