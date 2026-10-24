# 可观测组（研究组③）· 可续用状态账

> 本文件是**账**，不是报告：每个数字带出处与 as-of，下一轮直接接着往下写即可。
> 记账人：状态记账员（MiniMax-M3.1-Flash-Preview），写作时点 **2026-10-22 08:39 CST**（自测读数 as-of 08:36–08:39）。
> 覆盖工作流：**dwfrun-290829df-ce71-47e9-99fa-f63214cf9630**（名：研究组③可观测组·观测基建与RSI方案）第一轮，01:27:51 起、08:35:32 终审节点完成；本节点（ask#12 / node 32455）为该轮最后一节点。
>
> **2026-10-22 08:53 CST 修理组追记（接记账员 08:39 节点之后）**：终审 9 条附带意见（O1–O6 / R1–R3）已逐条处置销账，处置全文见 **§9**；两份设计文档头部已由「待红队终审」改为「已过 step-5 终审（confirmed，2026-10-22，9 条附带意见已销账）」。§1/§5/§7 中「一条未处置」等表述均为 08:39 时点快照，已被 §9 更新；处置中所亲验的命令输出（checker SPEC=101、tb/injec 显式 `obs: None`、2905 时间线等）均记于 §9。
>
> **2026-10-22 12:1x CST 观测实施员追记**：§9.3 遗留 L1/L2/L3 已销账（L4 给施工窗步骤、L5 维持登记），**G1 的 CI 七门本分支首跑全绿（7/7）**；词表 11→**12 类**（新增 `harness.correction`）、checker SPEC 终值 **108**。本文 §1/§2/§5/§6/§7 的「11 类」「101/100 项」「CI 七门未跑」「O5 待改」「correction 实现列下一循环」等表述均为对应时点快照，**一律以 §10 与《设计/可观测建设方案.md》当前版为准**。
>
> **2026-10-22 13:0x CST 状态记账员追记（第二循环·完整账）**：第二循环（施工前设计，run `dwfrun-5eeab2ec…`）的账续记于 **§11–§17**——**§10 = 观测实施员销账段，与 §11–§17 同属第二循环**（ask 说「§10 起」；§10 号已被实施员段占用，故本循环的记账员续账自 §11 接排，不改 §10 既有编号以免断掉外部引用）。五件事：①L1–L5 逐项处置（§12）；②底座重构施工方案的**路径与终审结论**（§13：v1 被红队驳回 13 条 → v2 逐条实证重写 → 三审 confirmed 附 1 中等硬伤）；③**RSI 预填摘要**（§14：`设计/RSI自我改进方案.md` §8.1，as-of 12:5x，ready=0.13）；④**红队·三审意见**（§15，verdict=confirmed，4 条）；⑤**留给 T0 施工窗的执行清单**（§16）。本节点亲跑证据见 §11.1；未跑/未覆盖见 §17。

## 0. 账本元信息

| 项 | 值 | 出处 |
|---|---|---|
| 工作流 run | `dwfrun-290829df-ce71-47e9-99fa-f63214cf9630`，`status=running`，`spent_tokens=75,376,342`，`cwd=/home/pan-ding/workspace/agent黑灯工厂` | `~/.zcode/cli/db/db.sqlite` 表 `dwf_run`（`select id,name,status,spent_tokens,time_created from dwf_run where id=…`，2026-10-22 08:36 亲查） |
| 流程脚本 | `.zcode/workflow-runs/dwfrun-290829df-ce71-47e9-99fa-f63214cf9630.mjs`；方法原文 `.zcode/workflow-drafts/研究组3-可观测组.dwf.ts` | 文件本体（脚本 `payload.lowered` 段） |
| 人物线（9 actor） | 工作者 GLM-5.3-Flash：观测设计师(19043)/观测修订师(19068)/观测实施员(19083)/跑通执行员(19126)/方案撰写员(19165)；红队 step-5-preview：schema 审查(19052)/实现审查(19115)/方案终审(19172)；记账员 MiniMax-M3.1-Flash-Preview(19181) | `dwf_actor` 表（`select id,name,resolved_model from dwf_actor where run_id=…`） |
| 节点账（13 节点） | ask#1=32119 / ask#2=32131 / ask#3=32151 / ask#4=32171 / ask#5=32263 / ask#6=32280 / ask#7#1=32293 / world-read#1#1=32375 / ask#8#1=32377 / ask#7#2=32384 / world-read#1#2=32426 / ask#8#2=32428 / ask#9=32435 / ask#10=32442 / **ask#12=32455（本节点，running）**；**ask#11 未生成** | `dwf_node` 表（`select id,site_id,ordinal,kind,status,time_created from dwf_node where run_id=…`） |
| 方法（运营者钦定） | ①观测需求与最小事件集设计→红队审→修订；②补丁进 af（工作树 + 新 target + 产物换新名）；③确定性 checker 跑通门；④建设方案 + RSI 方案双文档→红队终审；红队一律 step-5 | 脚本 `COMMON`/`system` 段；`.zcode/workflow-drafts/研究组3-可观测组.dwf.ts` |
| 授权来源 | 「③**可观测组**（补丁先行打进自研 harness 测通，定观测与存储方案；并产出 harness+工厂底座 RSI 自我改进方案）」 | `状态观测/业务目的章程.md:14`（fix3 终审四组任务书原文） |
| 红线（全程未越） | 观测数据绝不落 /tmp 或 tmpfs（D-24）→ 观测根固定 `工具状态备份/observability/` 且代码级拒内存盘；gov 生产面零触碰；密钥零明文（`key_refresh.ok` 只落布尔）；在飞臂不动；判分容器 sweb 计数 <6、本组同时 ≤2 | 脚本 `COMMON` 段；`crates/af-bench/src/obs.rs:71` `resolve_root()`（拒 `/tmp|/dev/shm|/run` 且 df 判 tmpfs） |
| 本组产出物 | `设计/可观测建设方案.md`（264 行）、`设计/RSI自我改进方案.md`（153 行）、`工具状态备份/observability/obs-checker.py`（853 行） | 文件本体 |

### 0.1 记账员本轮自测（2026-10-22 08:36–08:39，全部本节点亲跑）

| 自测项 | 命令 | 输出 | 判读 |
|---|---|---|---|
| checker 复跑（管线原始入参） | `cd 工具状态备份/observability && python3 obs-checker.py /tmp/obs-smoke2` | 「多 run 模式：2 个事件流待检（来源 /tmp/obs-smoke2）」；2905-a1 `events=240` **PASS (0 fail/0 warn)**、3151-a1 `events=104` **PASS**；`汇总：2/2 PASS`；`EXIT=0` | **当前物理状态=绿**（与工作流账面 `verified=false` 冲突，见 §4.4） |
| 事件流互校独立复算 | python3 解析 2905-a1 的 68 条 `harness.model` usage 求和 | input=**50199** / output=**238139** / cache_read=**2049160** | 与 `harness.run_finished` 的 `tokens_input/output/cache_read` **逐值相等**（终审复算同结论） |
| 2905 事件流字节指纹 | `sha256sum` 2905-a1 events.jsonl | `4e7e306e25cc26dfa4af2455e7b7544d9f16646019eeaa3d08294848eb87d927` | 与 `index/runs-202610.jsonl` 该行 `events_sha256` **相同**（修复后重导一致）；**与修复前 `f15d671b…` 不同**（node 32426 记录的前值） |
| 全量 run 目录复跑 | 依次 `python3 obs-checker.py {runs/obs-smoke1/mavis-m31f, runs/obs-smoke2/mavis-m31f, runs/d1/m31f, obs-smoke1-backup, obs-smoke2-backup, bench-obs4-out}` | 3/3、2/2、4/4、3/3、2/2、4/4 全部 **PASS，EXIT=0** | **6 个入口、18 次 run 引用全绿**（与方案 §2.1 口径一致） |
| **唯一事件流清点（口径纠错）** | `find runs obs-smoke1-backup obs-smoke2-backup bench-obs4-out -name events.jsonl` + 逐个 `sha256sum` | 只命中 **9 个** events.jsonl（d1/m31f ×4 + obs-smoke1 ×3 + obs-smoke2 ×2），其中 a4=`d8678ffc…`、4629=`5615708796…` 与 backup/out 入口重跑时的 sha256 **同值** | **独立事件流 = 9 条，不是 18 条**：backup/out 目录内无自己的 events.jsonl（`find` 零命中），checker 的 (c)/(d) 形态按 results.jsonl 映射回观测根同一批流 → 方案 §2.1 / node 32435 / 终审 evidence(5) 的「18 个真实 run 目录」实为 **18 次引用**，其中 9 条被重复检两遍。**计数口径须在下一轮改掉**（见 §2.4） |
| 产物字节与烙印 | `sha256sum /tmp/afbuild-obs/debug/{af-bench,afbench-obs4}`；`grep -ao "d73338e[0-9a-f]*" afbench-obs4` | 二者同为 `c96b2e60a210fb1d74b029245b30e4d48a2f9ced8a00f4f1ed8b15027a5dab1f`；烙印 `d73338e8335418939bd0a38cb925eb11f6bb56740`（命中 1） | 产物=工作流记录的 `c96b2e60…`；rev 烙印=HEAD `d73338e` 精确一致 |
| 主工作树未动 | `git -C af rev-parse HEAD` + `git -C af status --porcelain` | `94cd1923c34842983049bce5f97b3dcb6c7c348b`（guardrail-fix2）；仅 5 个本就存在的未跟踪 `poc/` 目录 | 生产工作树未动（纪律 ③ 守住） |
| 观测根落盘性质 | `df -T 工具状态备份/observability` | ext4（非 tmpfs） | D-24 红线在落盘面守住 |

---

## 1. 一屏摘要（下一轮先读这段）

| 环节 | 结论 | 关键数字 | 出处 |
|---|---|---|---|
| 观测 schema v1 | GLM 出稿 | 11 类事件词表（`harness.*`）+ 索引/清单层 | node 32119 |
| schema 红队审查 | **rejected** | **11 条**（缺镜像 digest/判分环境指纹/judge stderr/judge_mode 实际值/载体键/停止策略常量；'\|' 联合字段不可机器解析；路径段无消毒；索引层无自校验；emit_point 引用不实；未见过度设计） | node 32131 |
| schema 修订定稿 | 定稿 | `run_started` 32 字段 / `judge` 17 字段 / 索引行 10 字段 + RFC6962 风格 merkle / `AF_OBS_ROOT` 可覆盖但拒内存盘 / 段名白名单 `^[A-Za-z0-9._-]{1,64}$` | node 32151 |
| 实现 | 分支 `fix4-observability`（基线 main@f373113，工作树 `/tmp/af-wt-obs`） | 首报 9 文件 +1455/-132；终态 **4 提交 10 文件 +1666/-132** | node 32171；`git -C af diff --stat guardrail-fix2...fix4-observability` |
| 实现红队审查 | **rejected** | **11 条**（1 高=采样器 teardown 阻塞 ~62s；1 中=每事件 fsync 上主路径；1 中=汇总行不与事件流互校；1 中=git rev 指纹失实；1 中=观测失败可闸断测量；1 低-中=seq 锁外分配；1 低=batch_id 未消毒；1 低=judge_raw 切片 panic；1 低=torn 口径写读不一；1 低=checker 盲区 7 项；1 提示=「93 字段」口径无法复现） | node 32263 |
| 修复 | 11/11 逐条处置 | 树 @`942f2a2`；产物 `afbench-obs4` sha256 `2e17bdd9…`；af-harness 51/51 + af-bench 4/4 单测过 | node 32280 |
| 跑通 attempt1 | **失败——checker 入参形态缺陷，非数据缺陷** | `exit=1`，stdout=`FAIL: /tmp/obs-smoke1/events.jsonl 不存在` | node 32375（world-read#1） |
| 修复① | checker 改四种入参形态（run 目录 / events.jsonl / af-bench `--out` 目录 / line-arm 级多 run） | 复跑 3/3 PASS exit=0；合成正 fixture + 5 负向全 exit=1 | node 32377 |
| 跑通 attempt2 | **失败——写侧真 bug** | `exit=1`，3 条 FAIL（tokens 三本账） | node 32426（world-read#1） |
| 修复② | 写侧 `d73338e`（run_failed 路径 token 从 harness.db 对话快照实算）+ **既有证据确定性重导出** | 复跑 2/2 PASS exit=0 | node 32428 |
| 方案成稿 | 两份 | 可观测建设方案 264 行（含 G1–G7 生产化门）；RSI 方案 153 行（七道防退化闸 + K0–K7 清单） | node 32435；文件本体 |
| 方案红队终审 | **confirmed（附条件）** | **9 条**：O1 证据更正协议缺失（材料级·直击 append-only 破口）/ O2 互校自证盲区（材料级）/ O3 消费面半纸面（材料级）/ O4 grep 证据表述失准（轻微）/ O5 停止策略常量硬编码（轻微）/ O6 字段数 101≠100（吹毛求疵）/ R1 观测闸自身未纳入冻结（材料级）/ R2 漏接「重大补丁人工抽检」缓解（材料级）/ R3 0.5–1pp 判负空档（轻微） | node 32442 |
| 终审意见处置 | **已销账（修理组，2026-10-22 08:53）** | 9/9 逐条处置：O1/O2/O4/O6 文档勘误落地、O3 未实现标注+判据明晰化、O5 登记代码待改（下一循环）、R1/R2/R3 落进 RSI 文档（闸 1 扩冻结/闸 2 注入④/闸 8 人工抽检/0.5–1pp 界定）；遗留项 3 条（obs-checker.py docstring、O5 代码、O3 契约强制）见 §9 | §9（本文件） |
| 本节点 | 记账 | — | node 32455 |

**本轮一句话**：观测补丁**真材**（schema 定稿 → af 分支落地 → 确定性 checker 两轮踩真 bug 并两次修绿 → 9 条独立事件流 / 18 次引用本节点复跑全 PASS）；但**账面与物理状态不一致**（工作流 `verified=false`「两轮未过」，物理已绿），**终审 9 条意见一条未处置**（脚本只在 `rejected` 时才派修订节点 ask#11，本次 `confirmed` → 修订节点未生成），文档头部仍写「待红队终审」。

---

## 2. schema 定稿要点

定稿来源：**ask#3 观测修订师（node 32151）**，经红队 11 条（node 32131）逐条处置；机器可校验的落地形态见 `工具状态备份/observability/obs-checker.py`（853 行，stdlib only，退出码 0/1）。

### 2.1 信封与词表（11 类）

- 信封**恰五键** `{ts_ms, seq, level, kind, payload}`（`obs-checker.py:57` `ENVELOPE_KEYS`）；`level ∈ {normal, critical}`（`:58`）；kind↔level 配对表在 `obs-checker.py:59-71` `KIND_LEVEL`。
- 11 类：`harness.run_started` / `harness.model` / `harness.tool` / `harness.key_refresh`(critical) / `harness.retry_exhausted`(critical) / `harness.resource` / `harness.judge`(critical) / `harness.run_finished` / `harness.stop` / `harness.budget` / `harness.unauthorized`（后三类 critical=终态行）。
- **词表纪律**：kind 只增不改；新增 kind 必须与 checker 词表**同一提交**扩（checker 与词表分叉=校验失效）——`设计/可观测建设方案.md` §1.2。
- seq 自 0 严格 +1，**分配在文件锁内**（红队 ⑨ 修复：原在锁外 fetch_add，采样线程与主线程并发可致文件序与 seq 倒置）——node 32280 处置项 ②。

### 2.2 三块字段（定稿核心）

| 块 | 规模 | 要点 |
|---|---|---|
| `run_started` 指纹块 | **32 字段** | 身份（run_id/instance_id/line/arm/profile/host/ts_started）+ 模型端点（model/base_url/reasoning_tier/stream/max_tokens/temperature_milli/top_p_milli）+ 停止策略（max_turns/tool_free_turn_limit/completion_signals/per_turn_budget_cents/spend_cap_cents/tool_spend_cents/scaffold）+ **指纹六件**（`bench_binary_sha256`、`harness_git_rev`、`fp_image_ref`+`fp_image_digest`+`fp_image_digest_source`、`fp_task_sha256`、`fp_prompt_sha256`、`fp_judge_script_sha256`+`fp_judge_env_sha256`）+ `judge_mode_declared` + `swebench_version` |
| `judge` 事件 | **17 字段** | `judge_mode_actual`（与 declared 互证，不等即判分无效）/`resolved`/`f2p_pass`/`f2p_total`/`p2p_pass`/`p2p_total`/`log_parsed`/`tests_collected`/`env_yml_synthesized`/`judge_exit_code`/`judge_stderr`/`eval_timeout`/`eval_sha256`/`judge_raw`/`judge_container`/`swebench_version` —— 红队 R4/R5 的「零状态假阴性」从此有可检字段 |
| 索引 + 批次清单 | 索引行 10 字段 / manifest 8 字段 | 索引行：`run_id, path, ts_started, ts_finished, status, event_count, final_seq, events_sha256, torn_lines, fp_image_digest`；manifest：`batch_id, created_ts, run_count, run_ids, event_count_total, status_counts, merkle_root, merkle_algo`（merkle = RFC6962 风格：叶 `sha256(0x00‖ascii(events_sha256))`、节点 `sha256(0x01‖l‖r)`、奇数末节点提升、输入字典序排序） |

### 2.3 存储与三条铁律

- 观测根 `AF_OBS_ROOT`，缺省 `/home/pan-ding/workspace/agent黑灯工厂/工具状态备份/observability`（`obs.rs:27` `DEFAULT_OBS_ROOT`；`obs-checker.py:55` 同值）。**覆盖值也受内存盘红线**：`obs.rs:71` `resolve_root()` realpath 前缀拒 `/tmp|/dev/shm|/run` 且 df 判 tmpfs（D-24 根治）。
- 布局 `runs/<line>/<arm>/<run_id>/events.jsonl` + `index/runs-YYYYMM.jsonl` + `index/batch-<id>.manifest.json`；段名白名单 `^[A-Za-z0-9._-]{1,64}$` 且禁 `.`/`..`（D-14/D-22 前科）；目录已存在且有事件时按 `-x2` 递增避让，不覆写证据。
- 铁律三则（node 32171/32280 与终审复核一致）：①**观测不闸断测量**（`main.rs:826` 注释「fix4-observability（红队⑤修复：观测失败不闸断测量）」，失败降级 stderr 告警，results.jsonl 照写）；②**append-only 证据流**；③**单一时间源**（`ts_finished` 取一次钟同时写事件与索引行）。

### 2.4 口径纠错（写进账，防止下一轮照抄旧数）

- 「93 字段」**作废**：实测两轮真实 run 的 payload 字段并集 = **79**；checker 各 SPEC 字段检查合计实测 **101**（终审 O6 亲测；方案与 docstring 现写 100）。
- 「静默截断/篡改必现形」需**加限定**：写侧、索引行、manifest 同生于 af-bench 一体，checker 的本地重算比对**只对第三方事后截断成立**，对写侧原地改写不成立（终审 O2，smoke2 即实证）。
- 事件流覆盖度实况：**9 类有真实样本**，`harness.budget` / `harness.unauthorized` 两类 **0 真实样本**（只有代码与单测）——`设计/可观测建设方案.md` §2.2。
- **「18 个真实 run 目录」计数口径须改**：磁盘上**唯一事件流 9 条**（d1/m31f a1–a4、obs-smoke1 ×3、obs-smoke2 ×2）；backup/out 目录内无自己的 events.jsonl，checker 的 (c)/(d) 形态按 results.jsonl 映射回同一批流，故 18 是**引用次数**不是目录数（见 §4.2 证据）。

---

## 3. 实现分支与二进制路径

| 项 | 值 | 出处 |
|---|---|---|
| af 仓库 | `/home/pan-ding/workspace/agent黑灯工厂/af`（生产工作树 **guardrail-fix2**，未动） | `git -C af rev-parse HEAD` = `94cd1923c34842983049bce5f97b3dcb6c7c348b` |
| 实现工作树 | `/tmp/af-wt-obs`（linked worktree，`.git` 为 gitfile），**基线 = main@f373113**，用 sparse-checkout（排除 5GB `poc/`）建（首次 `worktree add` 因 poc 产物塞爆 tmpfs 失败，改 sparse 后成） | node 32171「必须如实报告」第 ⑴ 条 |
| 分支 | **`fix4-observability`**（基线 main；与 guardrail-fix2 并行，互不影响） | `git -C af branch`；node 32171 `branch` 字段 |
| 提交（4 笔，按时序） | `e508c49` 03:08:20 事件发射九类+索引/manifest（红队 11 条处置）→ `c2e1073` 03:44:50 红队复审 11 条逐条处置 → `942f2a2` 03:52:31 build.rs 监视真实 git ref 文件 → `d73338e` 08:08:12 run_failed 的 token 从对话快照实算 | `git -C af log --format='%h %ad %s' --date=iso fix4-observability -6` |
| 改动面 | `git diff --stat guardrail-fix2...fix4-observability` = **17 文件 +2675/−542**（含 CI 产物文件）；纯代码面 **10 文件 +1666/−132**：新增 `crates/af-bench/src/obs.rs`(824 行)、改 `af-bench/src/{main.rs,judge.rs,swev.rs,tb.rs}`、`af-harness/src/{run.rs,http.rs,lib.rs}`、`af-bench/build.rs`、`af-harness/examples/smoke.rs` | `git -C af diff --stat guardrail-fix2...fix4-observability`（08:36 亲跑） |
| 产物二进制 | **`/tmp/afbuild-obs/debug/afbench-obs4`**（另有同内容 `af-bench`），sha256 `c96b2e60a210fb1d74b029245b30e4d48a2f9ced8a00f4f1ed8b15027a5dab1f`，构建期烙印 rev=`d73338e8335418939bd0a38cb925eb11f6bb56740`（grep 命中 1，旧 rev 0 命中） | 08:36 亲跑 `sha256sum` + `grep -ao`；node 32428 交付物字段 |
| 产物构建纪律 | target 目录 `/tmp/afbuild-obs`（独立于 `af/target`）；`af/target/debug/` 现存二进制**分毫未动**；产物**换新名**不覆盖生产二进制 | node 32171 / node 32280 |
| 校验脚本 | **`/home/pan-ding/workspace/agent黑灯工厂/工具状态备份/observability/obs-checker.py`**（853 行，stdlib only，四种入参形态，退出码 0=全过 1=有 fail） | 文件本体；`obs-checker.py:436` `main()`、`:452` 多 run 模式提示行 |
| 判分脚本增量 | `tools/swev-judge.py` 增补 `p2p_success/p2p_failure/tests_collected/swebench_version` 四个输出键（**判分语义零变化**：`resolved=bool(inner.get("resolved"))` 与 `log_parsed` 逻辑一字未动）；改前备份 `工具状态备份/observability-backup-swev-judge.py.20261022-022839.bak` | node 32171；node 32263 红队核对 |
| ⚠️ 产物名口径 | 工作流账面 `impl.binary` 字段 = `/tmp/afbuild-obs/debug/afbench-obs4`（与磁盘一致）；但 **`/tmp/afbuild-obs` 位于 tmpfs**，机器重启/清理即失——生产化前必须把产物与 checker 一并落到 `/home` 盘固定路径 | 08:36 亲跑 `ls -la /tmp/afbuild-obs/debug/` |

---

## 4. 跑通验证记录

### 4.1 管线记录的两轮（原文照录）

**attempt1**（node 32293 跑通 → node 32375 world-read#1，06:20:54）：

```
exitCode=1  stdout="FAIL: /tmp/obs-smoke1/events.jsonl 不存在"  stderr=""
```

- 性质判定：**checker 入参形态缺陷**（管线把 af-bench 的 `--out` 目录喂给只认「含 events.jsonl 的 run 目录」的 checker），**非数据缺陷**——`/tmp/obs-smoke1/run.log` 证实该批确由本分支二进制跑出（`obs: 3 runs, 389 events, manifest → …/batch-b-1792613802821-3897864.manifest.json`），事件流在观测根 `runs/obs-smoke1/mavis-m31f/` 下。
- 处置（node 32377）：checker 改四种入参形态（run 目录 / events.jsonl 文件 / af-bench `--out` 目录（按 results 行 `task_id`+`run_dir` 尾段映射观测根，含 `-x*` 避让名，setup_failed 行按跳过计数不判 fail）/ line-arm 级多 run 目录），并把 FAIL 行改为一律落 stdout（`--quiet` 也可见）。复跑 3/3 PASS exit=0。

**attempt2**（node 32384 跑通 → node 32426 world-read#1，08:05:24）——**本轮 ask 指定的记录**：

```
exitCode=1
stdout:
[obs-checker] 多 run 模式：2 个事件流待检（来源 /tmp/obs-smoke2）
FAIL: run.finished.tokens_input=0 ≠ Σmodel.usage.input_tokens=50199
FAIL: run.finished.tokens_output=0 ≠ Σmodel.usage.output_tokens=238139
FAIL: run.finished.tokens_cache_read=0 ≠ Σmodel.usage.cache_read_tokens=2049160
[obs-checker] …/runs/obs-smoke2/mavis-m31f/pydata__xarray-2905-a1
  events=240 kinds={'harness.key_refresh':1,'harness.model':68,'harness.resource':57,'harness.retry_exhausted':1,'harness.run_finished':1,'harness.run_started':1,'harness.tool':111}
  sha256=f15d671b69096648de9ef31f4b6dd40d454af51ee99fd555ee9e32fe24311173
  result: FAIL (3 fail / 0 warn)
[obs-checker] …/runs/obs-smoke2/mavis-m31f/pydata__xarray-3151-a1
  events=104 … sha256=b5cdf9af0f8e9a21fa87021c5288d758fef4e835d3037e45bb481591e2ed5a5b
  result: PASS (0 fail / 0 warn)
[obs-checker] 汇总：1/2 PASS
```

- 性质判定：**写侧真 bug**——`pydata__xarray-2905` 是 run_failed run（68 次成功模型调用后第 69 次硬失败，broken pipe），写侧在 Err 路径把 `run.finished.tokens_*` **硬编码 0**，而事件流 68 条 `harness.model` 的 usage 是真实消耗。**这是红队③要求的 tokens 互校第一次在 run_failed 形态上咬到写侧**（node 32428 原话）。
- 处置（node 32428）：写侧 `d73338e`（`af-harness/src/run.rs` `run_progress` 返回值扩 `TokenTotals`，从已落库 harness.db 对话快照的 `Assistant.usage` 求和；`af-bench/src/main.rs` 失败路径改用实算值）——**两种终态一视同仁**；重建产物 `c96b2e60…`（烙印 rev=d73338e）。
- **既有证据修复（重要，须记账）**：2905 事件流的 `run_finished` 坏字段**按同文件 model 行真值确定性重导出**（tokens ← Σusage = 50199/238139/2049160，events.jsonl 仅该 3 字段变化），索引行 `events_sha256` 与 smoke2 批次 manifest merkle 随新字节重导。节点原话：「与此前 a1 索引行修复同一原则：修的是已知 bug 的派生值，不是伪造」。**修复前字节（tokens=0）无任何留存**——终审 O1 将此判为破口，见 §5。

### 4.2 修复后的物理复跑（记账员 08:36–08:39 亲跑）

| 目录 | 汇总 | 退出码 |
|---|---|---|
| `/tmp/obs-smoke2`（管线原始入参，多 run 模式） | 2/2 PASS | 0 |
| `runs/obs-smoke1/mavis-m31f` | 3/3 PASS | 0 |
| `runs/obs-smoke2/mavis-m31f` | 2/2 PASS | 0 |
| `runs/d1/m31f` | 4/4 PASS | 0 |
| `obs-smoke1-backup` | 3/3 PASS | 0 |
| `obs-smoke2-backup` | 2/2 PASS | 0 |
| `bench-obs4-out` | 4/4 PASS | 0 |

**6 个 checker 入口合计 18 次 run 引用全 PASS（0 fail / 0 warn）**——与 `设计/可观测建设方案.md` §2.1 的「18 run 全 PASS」口径一致（本节点独立复现，非转述）。⚠️ **但独立事件流只有 9 条**：`obs-smoke1-backup`/`obs-smoke2-backup`/`bench-obs4-out` 三个目录内**没有自己的 events.jsonl**（`find … -name events.jsonl` 零命中），checker 的 (c)/(d) 形态是按 `results.jsonl` 的 `task_id`+`run_dir` 尾段**映射回观测根同一批流**（a4 与 bench-obs4-out 的 sha256 同为 `d8678ffc…`、4629 与 obs-smoke1-backup 同为 `5615708796…`）→ 9 条被检两遍。下轮报数请写「**9 条独立事件流 / 18 次引用，全 PASS**」。

两轮冒烟的题与结果（`/tmp/obs-smoke2/results.jsonl`）：`pydata__xarray-3151` completed、resolved=true（f2p 1/1、p2p 66/66、judge_mode_actual=clean）；`pydata__xarray-2905` run_failed（broken pipe，非 infra 语义失败）。

### 4.3 观测事件流与索引/清单的一致性（08:36 亲核）

- 2905-a1：`events=240`（final_seq=239、torn_lines=0）、`events_sha256=4e7e306e…` 与索引行**逐字相同**。
- 2905-a1 的 `run_finished`：`wall_ms=3460164, turns=68, model_calls=68, tokens_input=50199, tokens_output=238139, tokens_cache_read=2049160, http_retries=0, effect_fresh=111, effect_replays=0, status=run_failed`。
- 3151-a1：`events=104`，judge 事件在（f2p 1/1、p2p 66/66、log_parsed=true、judge_mode_actual=clean），终态 `harness.stop` 在。
- manifest `batch-b-1792621644578-3986990.manifest.json`：`run_count=2`、`event_count_total=344`、`status_counts={completed:1, run_failed:1}`、`merkle_root=7d2e859d042929e4bc68f31b1c0e7e001ca00e5490b4d596c20b88d1c5b469f8`、`merkle_algo` 串随行落盘。
- 索引行 9 条（`index/runs-202610.jsonl`）：d1 四条 astropy-12907-a1..a4（58/70/102/77 事件，completed）、obs-smoke1 三条（4629=30、4094=192、3677=167）、obs-smoke2 两条（2905=240 run_failed、3151=104 completed）。

### 4.4 ⚠️ 账面 vs 物理：必须记的一处不一致

- 工作流脚本把 `verified` 置为 `check.exitCode === 0`，其最后一次取值是 **08:05:24 的 attempt2 结果（exit=1）**；attempt 循环上限为 2，第 2 轮失败后**不再复跑**。故 run 的 `verified=false`、`notCovered` 写着「观测补丁两轮跑通未全过，需下循环修复后重验」。
- 而物理上：写侧修复（`d73338e`，08:08:12）+ 证据重导出（08:08:33）**之后**，checker 对同一入参 exit=0（08:36 记账员复跑复现；终审红队亦独立复跑 exit=0）。
- **结论**：交付口径应写「**两轮未过 → 第 2 轮已修 → 修后复跑全绿（记账员与终审各独立复跑一次）**」，而不是「两轮未过」；下一循环应补一次**正式复跑并把结果写进工作流账面**（AmendWorkflow 续派或补节点），避免 run 结论与物理状态长期背离。

---

## 5. 终审意见

**终审 actor**：`红队·方案终审`（step-5-preview，此前未参与本轮），node **32442**，08:25:04–08:35:32，**verdict = confirmed（附条件）**，9 条意见。**ask#11（修订节点）未生成**——脚本仅在 `verdict === "rejected"` 时派修订，本次 confirmed → **9 条意见一条未处置**。两份文档头部至今仍写「待红队终审」（`设计/可观测建设方案.md:3`、`设计/RSI自我改进方案.md:3`），与 08:35 的 confirmed 结论**不一致**，需下一循环改口径。

### 5.1 逐条意见（终审原文要点 + 记账员核对）

| # | 级别 | 意见要点 | 终审给的证据 | 记账员核对（08:36 亲核） |
|---|---|---|---|---|
| O1 | 材料级 | **证据更正协议缺失**：2905 事件流是**原地修复而非重跑**（`run_finished.ts_finished=07:25:09` 早于修复提交 `d73338e` 08:08:12；run 目录 mtime 06:27:27 未变而 events.jsonl mtime 08:08:33；无 `-x2` 避让目录；索引与 manifest 同刻同步重写，merkle 钉的是修复后字节）；修复前字节**无留存**，未按方案 §3.3 硬规则 1「先归档后提请厂长裁决」执行；**无 correction 事件类、无修复记录字段**。要求：立证据更正协议（归档原字节 + 追加更正记录 + 变更日志补记），§2.1「attempt1→checker→修复→attempt2」措辞改实 | 时间线取证 + mtime 三处 | ✅ 全部复现：`ts_finished=1792625109830`=07:25:09；events.jsonl mtime 08:08:33；索引/manifest mtime 08:08:33；`d73338e` 提交时间 08:08:12 |
| O2 | 材料级 | **互校存在自证盲区**：写侧/索引/manifest 同生于 af-bench 一体，checker 第 10/11 项的「本地重算比对」只对第三方事后截断成立，**对写侧原地改写不成立**（O1 即实证）。要求：独立于写侧的哈希见证/修复前快照，或显式声明该边界 | O1 实证 | ✅ 一致；`obs.rs:485` `write_batch_manifest` / `:555` `append_index_row` / `:786` `finish` 同进程同源 |
| O3 | 材料级·直击底座重构 | **消费面半纸面**：`bench-mes.py`（docstring 1-11、幂等 83-95）与 `factory-watch.py`（A0-A7，docstring 18-33）真实存在、看板 data.json 真实在刷新，但 **`tools/obs-mes.py` 不存在**、A8/A9 只是「建议编号」、看板观测区只是建议、keepalive 存在性校验是 P2；§4.5「唯一写侧」四条契约**无任何代码强制**；G5 判据含糊（「看板区截图/读数」）。要求：契约 1-4 落成可执行检查（CI lint / 统一 writer 库），A8/A9 补触发演练记录 | 逐文件亲读 + `ls tools/` | ✅ `tools/obs-mes.py` 不存在（`ls tools/` 无此文件）；契约无强制入口 |
| O4 | 轻微 | §2.2 的 grep 证据**表述失准**：`main.rs:1307` terminal-bench 与 `main.rs:1504` injecagent 函数体内 grep "obs" **并非零命中**，各含一处显式 `obs: None`（结论「两 suite 不观测」反而更硬） | 代码行号 | ✅ 复现：`main.rs:1410` `obs: None`（run_tb）、`main.rs:1580` `obs: None`（run_injec） |
| O5 | 轻微 | `run_started` 指纹的 `spend_cap_cents=300` / `tool_spend_cents=1` 是**硬编码字面量**（`main.rs:888-889`），而执行侧读 `Launch.spend_cap_cents`（`run.rs:115/362/412`）；两处各自演化则指纹对停止策略**静默失真** | 行号 | 未复核（登记为待改项） |
| O6 | 吹毛求疵 | checker SPEC 字段实测合计 **101**（RUN_STARTED 32/MODEL 11/TOOL 8/KEY_REFRESH 5/RETRY_EXHAUSTED 7/RESOURCE 4/JUDGE 17/RUN_FINISHED 13/TERMINAL 4），docstring 与方案称 100；另 §2.1「obs-smoke1 192/–/– events」含混（实测 4094=192、3677=167、4629=30） | 逐 SPEC 计数 | ✅ 索引行事件数实测 30/192/167 对得上 |
| R1 | 材料级 | **冻结/只读集未覆盖观测闸自身**：闸 1 冻结判分链三件，但闸 7 依赖的 `obs-checker.py` 与 events/index/manifest 写侧**同在补丁可写范围**——补丁可弱化 checker SPEC 或写侧互校，而 smoke2 原地修复已证现有互校对写侧改写不可现形。要求：把 checker 与写侧纳入指纹冻结 + 路径 lint，或设独立哈希见证 | 与 O1/O2 联动 | ✅ 逻辑闭合；对应 `设计/RSI自我改进方案.md` §3 闸位（闸 1/闸 7）/§6 假设池（修理组 2026-10-22 修正错引：原写「§2.3」在该文档不存在） |
| R2 | 材料级 | 策略 9 原文对头号风险「评估器成攻击面」的缓解含**「重大补丁仍走人工抽检」**，七道闸与 K0–K7 **未承接**；方案只有 §5.6 降级版每轮人工批准，而该约束在「跑出两轮干净记录后再议放宽」后即失效。要求：把「重大补丁人工抽检」设为常设闸，或显式记录舍弃理由与替代控制 | 策略 9 原文 | 未复核（登记为待改项） |
| R3 | 轻微 | 预登记口径 0.5–1pp 空档：合入门=留出掉分 ≤0.5pp，环级判负=留出较 G1 掉 >1pp → 掉 0.5–1pp 的补丁可合入却已跨判负线（歧义源自策略 9/E9 原文，方案继承未澄清） | 策略 9/E9 | 未复核（登记为待改项） |

### 5.2 终审对两份文档的定性（原文要点）

- **可观测建设方案 = confirmed（附条件 O1–O3，生产化门 G1/G5 前必须处置）**：schema/存储/校验核**全部实测为真**、能在底座重构中幸存（存哪=ext4 固定根+拒内存盘已代码级强制；怎么查=checker 四形态+索引+merkle 已实测）；但「谁消费」只有一半落到实点，且**唯一一次真实 FAIL 的修复方式违反了方案自称的 append-only/先归档纪律**。
- **RSI 自我改进方案 = confirmed（附条件 R1/R2，K3–K6 执行前必须补进设计）**：三道防退化闸（verifier 只读物理隔离+指纹机判、三注入诱导演练 0 静默放行、负结果登记双通道）设计上全部内置，引文与源报告逐字相符，K0 正确阻塞启动，§8 如实登记全部未开始——**不是没有刹车的正反馈环**；但冻结集未覆盖观测闸自身、且漏接「重大补丁人工抽检」这条对头号风险的缓解。
- 终审**未改任何项目文件**（唯一写操作是 `/tmp/rt-audit` 临时副本，已删）；亲跑了 checker 两种形态、复现了交接的 FAIL 记录（把 /tmp 副本 tokens 改 0 → 输出与交接逐字一致）、独立复算 68 条 model usage、独立重算 6 份 manifest merkle、核对代码行号 20+ 处。

---

## 6. 下一循环动作

### 6.0 P0——先把账与物理对齐（阻塞项，建议厂长裁决后 AmendWorkflow 续派）

| # | 动作 | 验收判据 | 归属 |
|---|---|---|---|
| P0-1 | **终审 9 条逐条处置**（O1–O6 / R1–R3）：O1 立「证据更正协议」并把 §2.1「attempt1→修复→attempt2」措辞改为实（**原地重导出非重跑**）；O2 补独立哈希见证或显式声明边界；O3 把契约 1–4 落成可执行检查并为 A8/A9 补触发演练记录；O4 改 grep 表述；O5 常量同源；O6 字段数改 101；R1 checker+写侧入冻结；R2 补「重大补丁人工抽检」常设闸；R3 界定 0.5–1pp | 处置表逐条对应 9 条 + 两文档头部改为「已过红队终审（confirmed，附条件）」 | 本组 + 红队复审 |
| P0-2 | **补一次正式复跑并写进工作流账面**：以现产物 `c96b2e60…` 复跑 checker（`python3 obs-checker.py /tmp/obs-smoke2` 及 18 目录全量），把 exit=0 记为工作流「跑通验证」结论，消除 `verified=false` 与物理全绿的背离 | run 结论不再写「两轮未过」，或明确写「两轮未过→已修→修后复跑全绿（附两次复跑记录）」 | 本组 / 厂长 |
| P0-3 | **产物与 checker 落 `/home` 盘固定路径**：`/tmp/afbuild-obs`（tmpfs）与 `obs-checker.py` 现寄居 `工具状态备份/observability/`（可，但需在方案里固定路径约定）；产物 sha256 + rev 烙印写进索引行/变更日志 | 机器重启后产物仍在、路径在方案与看板可查 | 本组 |

### 6.1 P1——生产化门 G1–G7（`设计/可观测建设方案.md` §5 原表）

| # | 项 | 验收判据 | 现状 |
|---|---|---|---|
| G1 | fix4 分支过 **CI 七门**（`af/ci/run.sh` 六门 + 构建，AGENT.md 硬纪律 5）+ 红队终审 | ci 全绿 + 终审意见已处置 | 红队终审已 confirmed（附条件）；**CI 七门未跑** |
| G2 | 词表 12 类全实证（12:1x 更新：11→12，新增 correction 已有合成实测） | 构造 `budget_exhausted` / `unauthorized` 触发样本各 ≥1 run 过 checker；correction 真样本待首次真实更正 | budget/unauthorized 0 样本（方案 §2.2） |
| G3 | TB / rejudge 接线决策 | 补接线 **或** 显式声明不观测及理由（现状 `main.rs:1410`/`1580` 显式 `obs: None`） | 未决（终审 O4 给了更硬的口径） |
| G4 | 多档案实证 | glm-cp 或 step-5 档案 ≥1 冒烟轮全 PASS | 9 条独立事件流全 mavis-m31f 单档案 |
| G5 | `obs-mes.py` + watchdog A8/A9 + 看板观测区 | 各自冒烟证据（MES 行可查 / 安灯触发演练记录 / 看板区读数） | 0（终审 O3 判为材料级缺口） |
| G6 | keepalive 存在性校验扩面 | 删目录演练 7s 级恢复（D-25 同款） | 未做 |
| G7 | checker 进巡检 | 巡检每 2h 对增量索引跑 checker，fail 即安灯 | 未做（**建议下一循环最先把 G7 落地**：它是 O2/R1 缺失见证的最廉价补偿） |

### 6.2 下一循环可直接派工的清单（顺序建议）

1. 观测方案 R2（O1–O6 处置版）→ 红队复审（step-5）→ 归档。**顺带改两处口径**：§2.1「18 个真实 run 目录」→「9 条独立事件流 / 18 次引用」（§4.2 证据）；§2.1「attempt1→checker→修复→attempt2」→ 改为「attempt2 后**原地重导出**既有证据」（O1）。
2. RSI 方案 R2（R1–R3 处置版：checker+写侧入冻结清单、人工抽检常设闸、0.5–1pp 界定）→ 红队复审。
3. G2 样本构造（短 spend_cap 触发 budget_exhausted；越权触发 unauthorized）——**只造 2 个 run 的成本，别扩题**。
4. G7 checker 进巡检（每 2h 增量索引）+ G1 CI 七门（可在 `/tmp/af-wt-obs` 上跑，不碰生产工作树）。
5. G3/G4 二选一先做 G3（决策成本低于实证成本）。

### 6.3 下一循环的机制坑（勿重踩）

- **产物名/路径漂移**：工作流账面 `impl.binary` 记的是 `/tmp/afbuild-obs/debug/afbench-obs4`（tmpfs），重建后仍需手工换名，路径必须写进交付物字段与索引行。
- **attempt 循环上限 2**：第 2 轮失败即收口，账面 `verified` 不再更新 → 修完必须**再跑一次**并把结果回写。
- **ask#11 只在 rejected 时派**：终审 confirmed 时 9 条意见**不会自动触发修订**，必须显式派处置节点（否则意见随工作流结束烂在账里）。
- **checker 与事件词表必须同提交**（词表分叉=校验失效）。
- **不要在证据流上做「确定性重导出」而不同步留更正记录**——本轮 O1 的教训：派生值可重导，但**原字节必须留档 + 变更日志补记**，否则「append-only 证据流」在唯一一次真实压力下已被绕过且无法自证。

---

## 7. 本轮未跑 / 未覆盖（据实登记）

| 项 | 状态 |
|---|---|
| CI 七门（`af/ci/run.sh`） | **未跑**（G1，红队终审前不动构建序列） |
| 终审 9 条意见的处置 | ~~**未做**（ask#11 未生成）~~ → **2026-10-22 08:53 修理组已销账，见 §9** | 本节为 08:39 时点快照；处置后新增遗留 3 条（见 §9 遗留项表） |
| `tools/obs-mes.py` | **不存在**（G5 P1 待派） |
| watchdog A8/A9 规则 | **未实现**（仅文档建议编号） |
| 看板观测区 | **未实现** |
| keepalive 存在性校验扩面（G6） | **未做** |
| checker 进巡检（G7） | **未做** |
| `harness.budget` / `harness.unauthorized` 真实样本 | **0 样本** |
| terminal-bench / injecagent / rejudge 套件观测接线 | **未接**（显式 `obs: None`） |
| 多档案（glm-cp / step-5 / qwen30b-local） | **未跑** |
| 跨机备份（D-27 跨机监督未还） | **不在本方案范围**（方案 §3.3 明写不承诺） |
| 2905 修复前字节（tokens=0 的原始 events） | **已不存在**（无留存，O1 的核心后果） |
| 跨机/多进程并发 append 索引行的锁行为 | **未实证**（方案 §2.2 第 4 条） |

---

## 8. 证据索引（复现命令）

```bash
# ① 工作流节点账（终审意见、实施细节、跑通记录全在 result_json）
python3 - <<'EOF'
import sqlite3, json
con=sqlite3.connect('file:/home/pan-ding/.zcode/cli/db/db.sqlite?mode=ro',uri=True)
for nid in [32119,32131,32151,32171,32263,32280,32293,32375,32377,32384,32426,32428,32435,32442]:
    r=con.execute("select id,site_id,ordinal,kind,result_json from dwf_node where id=?",(nid,)).fetchone()
    print('='*20,nid,r[1],r[2],r[3]); print(str(r[4])[:2000])
EOF

# ② 分支/提交/改动面
git -C /home/pan-ding/workspace/agent黑灯工厂/af log --format='%h %ad %s' --date=iso fix4-observability -6
git -C /home/pan-ding/workspace/agent黑灯工厂/af diff --stat guardrail-fix2...fix4-observability
git -C /home/pan-ding/workspace/agent黑灯工厂/af rev-parse HEAD   # 94cd1923… = 生产工作树未动

# ③ 产物与烙印
sha256sum /tmp/afbuild-obs/debug/{af-bench,afbench-obs4}        # c96b2e60…
grep -ao "d73338e[0-9a-f]*" /tmp/afbuild-obs/debug/afbench-obs4 | head -1

# ④ checker 全量复跑（6 个入口 / 18 次引用 = 9 条独立事件流）
cd /home/pan-ding/workspace/agent黑灯工厂/工具状态备份/observability
for d in /tmp/obs-smoke2 runs/obs-smoke1/mavis-m31f runs/obs-smoke2/mavis-m31f runs/d1/m31f \
         obs-smoke1-backup obs-smoke2-backup bench-obs4-out; do python3 obs-checker.py "$d" | tail -2; done

# ⑤ Σmodel.usage 独立复算（与 run_finished 三本账互校）
python3 - <<'EOF'
import json
p='runs/obs-smoke2/mavis-m31f/pydata__xarray-2905-a1/events.jsonl'
s=[0,0,0]
for l in open(p):
    if not l.strip(): continue
    d=json.loads(l)
    if d['kind']=='harness.model':
        u=d['payload']['usage']; s[0]+=u['input_tokens']; s[1]+=u['output_tokens']; s[2]+=u['cache_read_tokens']
print(s)   # [50199, 238139, 2049160]
EOF

# ⑥ 交付物本体
ls -la /home/pan-ding/workspace/agent黑灯工厂/计划/研究组/可观测组-state.md \
       /home/pan-ding/workspace/agent黑灯工厂/设计/可观测建设方案.md \
       /home/pan-ding/workspace/agent黑灯工厂/设计/RSI自我改进方案.md \
       /home/pan-ding/workspace/agent黑灯工厂/工具状态备份/observability/obs-checker.py
```

**本轮工作流记录（node 序）**：
32119=观测设计师 v1 · 32131=红队·schema 审查（rejected，11 条）· 32151=观测修订师（定稿）· 32171=观测实施员（分支/产物/checker）· 32263=红队·实现审查（rejected，11 条）· 32280=实施员 11 条修复 · 32293=跑通 attempt1 · 32375=world-read#1（exit=1 入参形态）· 32377=checker 四形态修复 · 32384=跑通 attempt2 · 32426=world-read#1（exit=1 tokens 三本账）· 32428=写侧 d73338e + 证据重导出 · 32435=两份方案成稿 · 32442=红队·方案终审（confirmed，9 条 O1–O6/R1–R3）· **32455=本记账节点**。

---

## 9. 终审 9 条附带意见处置记录（修理组，2026-10-22 08:53 CST）

**处置人**：修理组子代理（阶跃 step-5-preview）。**授权范围**：只改 `设计/可观测建设方案.md`、`设计/RSI自我改进方案.md`、本状态账三处；af 代码、`工具状态备份/observability/obs-checker.py`、工作流账面均未动。**数字勘误前均亲验**（命令与输出见 §9.2）。

### 9.1 逐条处置表（9/9，逐条对应终审原文，无遗漏）

| # | 级别 | 处置结论 | 改动位置（精确到节） | 遗留 / 归属 |
|---|---|---|---|---|
| O1 | 材料级 | **立证据更正协议**：§3.3 增硬规则 4（①归档原字节入 `observability-archive/corrections/<run_id>-<ts>/` ②追加更正记录（correction 行/事件，随 checker 同提交扩词表）③变更日志补记）；**§2.1 attempt 措辞改实**：obs-smoke2 行改为「原地重导出、非重跑」并列时间线取证（ts_finished 07:25:09 < 修复提交 d73338e 08:08:12、events.jsonl mtime 08:08:33 vs run 目录 mtime 06:27:27 未变）；**2905 原字节无留存登记为既成破口**（修复前 tokens=0 不可复原，merkle 钉修复后字节，新值可凭 d73338e 复算） | `设计/可观测建设方案.md` §3.3 硬规则 4、§2.1 冒烟轮次表 obs-smoke2 行 | correction 事件类与归档目录属 af 代码实现 → **下一循环本组**（随 checker 同提交，守 §1.2 词表纪律） |
| O2 | 材料级 | **§1.5「静默截断/篡改必现形」加边界声明**：写侧/索引/manifest 同生于 af-bench 一体（`obs.rs:485/555/786`），checker 第 10/11 项本地重算只对第三方事后截断成立、对写侧原地改写不成立（2905 即实证）；补偿=硬规则 4 归档原字节 + checker 进巡检（G7）独立见证；§1.6 末加回指 | `设计/可观测建设方案.md` §1.5、§1.6 | 独立哈希见证实体化（巡检跑起来、归档目录落盘）→ **下一循环 G7（厂长巡检链）+ 硬规则 4 实现** |
| O3 | 材料级 | **半纸面改实标注**：§4.2 标注 `tools/obs-mes.py` 不存在；§4.3 标注 A8/A9a-c 均未实现（watchdog 现只到 A7）且演练记录列为 G5 验收件；§4.4 标注看板观测区未实现；§4.5 增⚠️段：四条契约**无任何代码强制**，消费面按半纸面如实标注；**G5 判据明晰化**（MES 行可查 / 安灯演练留痕 / 看板区机读读数+刷新时点，非截图） | `设计/可观测建设方案.md` §4.2/§4.3/§4.4/§4.5、§5 G5 | 契约 1–4 落成可执行检查（CI 路径 lint / 统一 writer 库）+ A8/A9 触发演练 → **下一循环，G5 归属修理组/观测组** |
| O4 | 轻微 | **grep 表述改实**：§2.2 第 3 条 terminal-bench/injecagent 由「grep "obs" 零命中」改为「各有一处显式 `obs: None`（main.rs:1410 run_tb、main.rs:1580 run_injec）」——显式声明不观测，结论比零命中更强；rejudge 的零命中表述经复验属实保留；§6 证据行同步 | `设计/可观测建设方案.md` §2.2 第 3 条、§6 附注 | 无（rejudge 零命中 2026-10-22 复验属实：`awk` 函数体范围 grep obs = 0 命中） |
| O5 | 轻微 | **登记为待改项（代码级，不在本次授权）**：`spend_cap_cents=300`/`tool_spend_cents=1` 为 `main.rs:888-889` 硬编码，执行侧读 `Launch.spend_cap_cents`（`run.rs:115/116/362/412/978`），两处各自演化则指纹静默失真；文档侧 §1.3 停止策略字段加⚠️同源缺口警示（修复前按「未同源」口径解读） | `设计/可观测建设方案.md` §1.3；本账 §9 | **代码修复=下一循环 af 分支 `fix4-observability`**（指纹改读 Launch 实参），归属本组；修复前不得把该两字段单独作停止策略凭据 |
| O6 | 吹毛求疵 | **字段数 100→101**：§1.6 改为 SPEC 合计 101 项字段检查并附终审判据（RUN_STARTED 32/MODEL 11/TOOL 8/KEY_REFRESH 5/RETRY_EXHAUSTED 7/RESOURCE 4/JUDGE 17/RUN_FINISHED 13/TERMINAL 4）；**obs-smoke1 事件数含混改实**：§2.1 表由「192/–/–」改为「192/30/167（4094=192、3677=167、4629=30，索引行亲读）」 | `设计/可观测建设方案.md` §1.6、§2.1 冒烟轮次表 obs-smoke1 行 | **obs-checker.py docstring 第 22 行仍写「100」**——该文件不在本次授权修改范围 → 遗留下一循环（与其任何改动同提交销账），已在该文档 §1.6 显式注明 |
| R1 | 材料级 | **RSI 闸 1 冻结/只读集扩观测闸自身**：`obs-checker.py` 字节 sha256 进指纹表 + events/index/manifest 写侧（obs.rs）入「补丁可写范围黑名单」，弱化 SPEC/删互校/改生成逻辑=整补丁作废（触碰清单+CI 路径 lint 双查）；**闸 2 增注入④**（弱化 checker SPEC/写侧互校必须被拦）；K4 改四注入、K5 lint 覆盖观测闸路径 | `设计/RSI自我改进方案.md` §3 闸 1（观测闸段）、闸 2、§8 K4/K5 | 指纹表实体与 lint 实现 → **下一循环 K3/K5**；独立哈希见证同 O2 遗留（G7） |
| R2 | 材料级 | **立闸 8「重大补丁人工抽检」常设控制**：重大补丁定义（触闸 1 黑名单/DSL 越界/双门读数落 R3 判负信号区）+ 每轮厂长或非环内审计员抽检≥1 次 + 记录进变更日志 + 不同意即回退停当轮合入；明确不随无人值守晋级失效（§5 第 6 条加注：放宽仅指非重大补丁逐轮批准）；§3 计数七道→八道联动（标题/骨架句/自检节奏/K7） | `设计/RSI自我改进方案.md` §3 标题与骨架、闸 8、自检节奏、§5 第 6 条注、§8 K7 | 闸 8 状态表进章程读数节 → 随 K7 落地（下一循环） |
| R3 | 轻微 | **0.5–1pp 空档显式界定**：闸 3 补「留出掉分落在 (0.5pp, 1pp] = 合入可过（未越判负线）但环级记一次判负信号，同一补丁线连续两次落入即停环诊断」——歧义源（策略 9/E9 两线未接）由本方案显式接管 | `设计/RSI自我改进方案.md` §3 闸 3 | 无（口径已闭；判负信号账随闸 3 每轮自动执行落地） |

**附带落地 3 项（非终审意见，为保两文档与已证事实一致，均在授权文件内）**：①两文档头部「待红队终审」→「已过 step-5 终审（confirmed，2026-10-22，9 条附带意见已销账，见 工具状态备份/observability/ 或状态账）」；②`可观测建设方案.md` §2.1/一句话状态「18 个真实 run 目录」→「9 条独立事件流 / 18 次引用」（记账员 §4.2 find+sha256 亲测结论落地，原表述已被证伪）；③`可观测建设方案.md` §2.2 结论/§5 G1/§6 的「尚未过红队终审/构建序列冻结」同步为 confirmed 后状态（CI 七门列为下一循环首补项），另修正一句话状态中不存在的「§2.6」交叉引用为 §2.2。

### 9.2 处置中的亲验记录（2026-10-22 08:44–08:53，全部本会话实跑）

| 验项 | 命令 | 输出 | 对应意见 |
|---|---|---|---|
| checker SPEC 字段合计 | python3 正则解析 `obs-checker.py` 各 `*_SPEC` | RUN_STARTED 32 / MODEL 11 / TOOL 8 / KEY_REFRESH 5 / RETRY_EXHAUSTED 7 / RESOURCE 4 / JUDGE 17 / RUN_FINISHED 13 / TERMINAL 4，**合计 101**；docstring 第 22 行写 100 | O6 |
| obs-smoke1 事件数 | python3 读 `index/runs-202610.jsonl` | 4629=30、4094=192、3677=167（均 completed） | O6 |
| tb/injec grep 证据 | `awk` 取 `fn run_tb(`/`fn run_injec(` 函数体 grep obs | 各 1 处显式 `obs: None`（精确行 `main.rs:1410`/`:1580`） | O4 |
| rejudge grep 证据 | `awk` 取 `fn run_swev_rejudge(` 函数体 grep -c obs | **0 命中**（原文此项表述属实，保留） | O4 |
| O5 常量同源 | `sed -n '884,892p' main.rs` + grep run.rs | `main.rs:888-889` 硬编码 300/1；`run.rs:115/116/362/412/978` 读 `Launch.*`（另 `main.rs:1414/1584` 还有 100 的第三处口径） | O5 |
| O1 时间线 | python3 读 2905 `run_finished.ts_finished` + os.stat mtime + git log | ts_finished=1792625109830（07:25:09）< d73338e（08:08:12）；events.jsonl mtime 08:08:33、run 目录 mtime 06:27:27；`find obs-smoke2-backup -name events.jsonl`=0（修复前字节无留存证实） | O1 |
| O2 写侧同源 | grep obs.rs | `write_batch_manifest:485`/`append_index_row:555`/`finish:786` 同进程同源 | O2 |

### 9.3 遗留项清单（本次未闭环，均因授权范围或需代码/执行动作）

| # | 遗留 | 为何未闭环 | 归属 |
|---|---|---|---|
| L1 | `obs-checker.py` docstring「SPEC 合计 100」→101 | obs-checker.py 不在「只改两文档+状态账」授权内 | ~~下一循环，与其任何改动同提交~~ **2026-10-22 已销账 → §10**（docstring 勘误落地；同变更集 L3 落码后终值 108，见 §10.1） |
| L2 | O5 指纹常量同源（`main.rs:888-889` 改读 Launch 实参） | af 代码修改，本次授权外；CI 七门未跑，动码须走七门 | ~~下一循环本组（fix4-observability 分支）~~ **2026-10-22 已销账 → §10**（提交 59c1d6c，CI 七门全绿） |
| L3 | O3 契约 1–4 可执行强制（CI 路径 lint / 统一 writer 库）+ A8/A9 演练记录 | 需写码与演练，非文档勘误 | 下一循环，G5 归属修理组/观测组（**注意：§9.1 O1 遗留的 correction 事件类落码亦编 L3 号——已在本次销账 → §10.2；本行 O3 契约强制仍开放**） |
| L4 | O2/R1 独立哈希见证实体（归档目录落盘 + checker 进巡检） | 依赖 L3/巡检链 | 下一循环 G7（厂长巡检链）——**归档目录机制已随 L3 落码，实体化步骤见 §10.4** |
| L5 | 2905 修复前字节 | 物理上已不存在（无留存），不可恢复——只能按硬规则 4 防止复发 | 不可恢复（既成破口，已登记）——**复发防线已随 L3 落码 → §10.2** |

### 9.4 对下一循环的提示

- §6.0 P0-1 的 9 条处置**已完成文档侧部分**；P0-2（正式复跑写回工作流账面，消 `verified=false` 背离）、P0-3（产物落 /home 盘固定路径）**未做**——不在本次授权（工作流账面与产物路径属执行面）。
- §6.1 的 G1 现应拆为：红队终审已过（2026-10-22 confirmed，9 条销账）；CI 七门未跑 → 下一循环首补（构建序列已解冻）。
- §6.2 第 1 条的「顺带改两处口径」（18 目录→9 流、attempt 措辞）已由本次提前落地，下一循环派工时不必重复。
- 机制坑照旧有效：**confirmed 时 9 条意见不会自动触发修订**（本次即靠修理组显式处置）；checker 与词表仍须同提交；勿在证据流上做重导出而不同步留更正记录（硬规则 4）。

---

## 10. 观测实施员循环（2026-10-22，L1/L2/L3 销账 + G1 CI 七门首绿）

**执行者**：观测实施员（子代理，GLM-5.3-Flash，动态工作流 ask 派发）。**授权范围**：代码改动仅限 af 分支 `fix4-observability`（worktree `/tmp/af-wt-obs2`）与 checker 脚本；零生产影响（在飞进程/生产位/`tools/`/gov 未动，判分核未动）。**账目时点 2026-10-22 12:0x CST，以下全部本节点亲跑。**

### 10.0 纪律核对（附证据）

| 项 | 证据 |
|---|---|
| 生产工作树未动 | `git -C af rev-parse HEAD` = `94cd1923c34842983049bce5f97b3dcb6c7c348b`（guardrail-fix2，与 §0.1 同值）；status 仅 5 个既有未跟踪 `poc/` 目录 |
| 判分核冻结未破 | `sha256sum tools/swev-judge.py` = `0338566c2f457496037c70f16504b0cfe9f5286c55ee2d67963428b00e7fc16a`，与 2905 事件流 `run_started.fp_judge_script_sha256` **逐字相同**（本轮亲读比对） |
| tools/ 未动 | 本循环所有写操作路径核对：仅 `/tmp/af-wt-obs2/**`、`工具状态备份/observability/obs-checker.py`、两份文档、本账 |
| gov / 密钥 | 未触碰；本次无任何密钥操作 |

### 10.1 L1 销账：checker docstring 字段数勘误（同变更集带出终值 108）

- `obs-checker.py` docstring 第 4 条改为：SPEC 合计 **108** 项（RUN_STARTED 32/MODEL 11/TOOL 8/KEY_REFRESH 5/RETRY_EXHAUSTED 7/RESOURCE 4/JUDGE 17/RUN_FINISHED 13/TERMINAL 4/**CORRECTION 7**），并留勘误史（旧口径 100 有误 → 终审 O6 实测 101 → correction 落码后 108）。
- 机械验证：`python3` 逐 SPEC `len()` 合计 = **108**，`len(KIND_LEVEL)` = **12**（2026-10-22 本节点亲跑）。
- 文件新指纹：`sha256sum obs-checker.py` = `aaae9e53b906df225d9615abeb023262eedeedba016efbaad685f0fda213aa6e`（改动前原字节未另存——勘误属校验脚本自身，非观测证据流，不受硬规则 4 约束；其旧版可由 git 外的备份纪律自定，特此如实登记）。⚠️ 依 RSI 闸 1（R1），checker 字节已入冻结集候选——**下一循环应把 `aaae9e53…` 登进指纹表**。

### 10.2 L2+L3 销账：af 提交 `59c1d6c`

**L2（终审 O5 同源修复）**：`main.rs` 新增 `SWEV_SPEND_CAP_CENTS=300`/`SWEV_TOOL_SPEND_CENTS=1` 单一常量，指纹块（run_started）与执行侧（Launch 字段 + BudgetLedger + BudgetBinding）同读此处；两处各自演化→静默失真的结构性缺口关闭。tb/injec 路径的 100/1 系执行侧单写（无指纹对应物，`obs: None`），不在 O5 范围，未动。

**L3（O1 证据更正协议事件化）**——词表第 12 类 `harness.correction`（critical）：

- 写侧 `obs.rs::append_correction`：①归档原字节 → `<观测根>/../observability-archive/corrections/<run_id>-<ts>[-kN]/events.jsonl` + `original.sha256`（同毫秒/同 run 二次更正 `-kN` 递增避让，不覆写前一次归档——单测抓出同毫秒互撞真 bug 后修）；②从当前字节实取 old 值（不信操作者口述）→ 改写 run_finished 派生字段 → 追加 correction 事件（字段名/旧值/新值/reason/basis_rev/operator/archived_path/archived_sha256，seq 续流内计数，critical=fsync，临时文件+原子改名防撕裂）；③变更日志补记属流程。**索引行与 manifest 永不改写——钉住归档原字节**（第一次更正会改 run_finished 的值，故原字节锚由索引行承担）。
- CLI：`af-bench --obs-correct <run 目录|events.jsonl> --correction-json <req.json>`（req 含 corrections[]/reason/basis_rev/operator；`AF_OBS_ARCHIVE_ROOT` 可覆盖，与观测根同受 D-24 内存盘红线）。
- 校验侧（checker **同一次变更集**，§1.2 词表纪律）：`harness.correction` 入 KIND_LEVEL(critical) + CORRECTION_SPEC(7 字段)；correction 只允许追加在 run_finished 之后、连续到流尾；第一条更正的归档件 sha == 事件内 archived_sha256 == **索引行 events_sha256**，其 event_count/final_seq/torn_lines/status/ts_finished 全部对归档件重算；链式更正（第 2 条起）归档件末行必须与当前流前一条 correction 行**原文逐字节一致**；old 值与归档件实值一致、new 值链式推进后与当前 run_finished 实值一致；归档目录名合 `<run_id>-<ts>[-kN]` 约定。Rust 单测 ×3（归档改写记录/拒绝缺终态或缺字段/链式）。

**合成实测**（真 2905 流副本 → `/home/pan-ding/obs-selftest-l3` 合成根，实测后已删，D-24 合规：全程不出 /home 盘）：

| 用例 | 结果 |
|---|---|
| 正向：tokens 三字段 0→Σusage（50199/238139/2049160，basis_rev=d73338e）经 CLI | CLI exit=0，checker **PASS**(0 fail) |
| 链式双更正（第二条 ts_finished +1ms） | CLI exit=0，checker **PASS**，归档两条（同批实测相隔 16ms 未触发 -kN；-kN 避让由单测覆盖） |
| 负向 a：归档件被删 | checker **FAIL**×4（归档件不存在+old 链失配） |
| 负向 b：correction.old 篡改（0→7→999 两式） | checker **FAIL**（old ≠ 归档实值）；**且追加新更正行无法洗掉该 FAIL（篡改证据有效）** |
| 负向 c：当前 run_finished 现值篡改（→12345） | checker **FAIL**×2（Σusage 互校 + 更正链终值） |

**设计修正 3 处**（实施中真实发现，非转述）：同毫秒归档互撞（-kN 避让）；「首条更正后流前缀==归档件」假设不成立（改值即变——首条锚改由索引行承担）；链式前缀校验改为「归档件末行==前一条 correction 行原文」。

### 10.3 G1 一半闭环：CI 七门首绿（本分支首次）

- 命令：`cd /tmp/af-wt-obs2 && CARGO_TARGET_DIR=/home/pan-ding/afbuild-obs2 CARGO_INCREMENTAL=0 CARGO_PROFILE_DEV_DEBUG=0 bash ci/run.sh` → **7/7 PASS，exit 0**（fmt 475ms / clippy 基线门 1095ms / test -j4 --workspace 10439ms / cue 57ms / scrub 244ms / cosign 断网 171ms / cargo deny 离线 648ms；`ci/out/SUMMARY.txt` 与提交内 `ci/out/*` 同存）。工作区单测 75 个 test-result 全 ok（含新增 correction ×3）。
- 首跑暴露并当场处置的存量债（均在本提交内）：①分支从未跑过 fmt——`cargo fmt --all` 规整 build.rs/judge.rs/http.rs（**纯 rustfmt 重排，`git diff --ignore-all-space` 核对无语义变化**）；②clippy 三处：merkle `(n+1)/2`→`div_ceil(2)`、`run_progress` 复杂元组提具名 `ProgressRow`（lib.rs 再导出）、`run_obs_slot` 死预置 `None` 改声明后赋值。

### 10.4 ⚠️ 执行偏差与事故（如实登记）

1. **target 迁移偏差（纪律②写 `/tmp/afbuild-obs2`，实际落 `/home/pan-ding/afbuild-obs2`）**：/tmp 为 7.5G tmpfs 且承载产线日志，全量 CI 构建两次击穿配额（`Disk quota exceeded (os error 122)`，第一次还曾把沙箱输出捕获写满导致 shell 一度全哑，`rm -rf` 自建产物后恢复）。为不重演 D-24 型 tmpfs 事故，target 移 /home（72G 空闲），**目录名与「独立新 target、不碰 af/target」的纪律意图不变**。处置后 /tmp 恢复 3.4G 空闲（亲测）。构建瘦身：`CARGO_PROFILE_DEV_DEBUG=0`（无调试信息，测试语义不变）。
2. **rustfmt 版式债**：fmt 首跑改写了分支既有文件版式（上节②），已在提交信息注明纯重排。

### 10.5 交付物

| 项 | 值 |
|---|---|
| af 提交 | `fix4-observability` @ **`59c1d6c`**（父 `d73338e`；12 文件 +1573/−1028，含 ci/out 产物） |
| 交付二进制 | `/home/pan-ding/afbuild-obs2/debug/afbench-obs4`，sha256 = `9f8beb1fc7011c4819a2ae79f55bb09fc6991f3430fc05a53d445c48da487251`，rev 烙印 `59c1d6c04d234ac24365a4ca9fda73a19497ef8f0`（旧 rev `d73338e…` 0 命中，grep 亲测）。⚠️ 位于 /home 盘，**解决了 §3「产物寄居 tmpfs」的 P0-3 一半**（checker 仍在观测根原位） |
| checker | `工具状态备份/observability/obs-checker.py`（新 sha `aaae9e53…`，§10.1） |
| 复跑结论 | 既有 9 条独立事件流 / 18 次引用（6 入口）在新 checker 下全 **PASS exit=0**（correction 词表不破坏存量流） |

### 10.6 L4/L5 处置（按 ask：纯登记入账，执行项给可执行步骤留施工窗）

- **L5（2905 修复前字节）**：纯登记，维持 §9.3「不可恢复（既成破口）」结论不变；其**复发防线**已随 L3 落码（归档+correction 事件+索引锚），无需新动作。
- **L4（独立哈希见证实体化，属执行）**：机制已备（归档目录布局、checker 校验、CLI），实体化留施工窗（T0），可执行步骤：
  1. **G7 巡检接线**：在厂长巡检链（现每 2h 轮）加一步 `cd 工具状态备份/observability && python3 obs-checker.py <增量索引覆盖的 line/arm 目录或全部 runs/*/*>`，fail 即安灯（A9a 同款）。最小验证：手工对 `runs/d1/m31f` 跑一次入巡检日志。
  2. **归档目录实体化**：`mkdir -p 工具状态备份/observability-archive/corrections` + 把该路径写进方案 §3.3 已有布局（已在）；首次真实更正发生时协议自动生效，无需预建内容。
  3. **指纹表登记**：把 checker 新 sha（`aaae9e53…`）与交付二进制 sha（`9f8beb1f…`）登进 RSI 闸 1 指纹表（K3/K5 范围）。
  4. **换装（属 T0 施工串，非本循环）**：`afbench-obs4` 过 CI+金丝雀后按 护栏rollout手册 §2 原子换名上生产位（sha 以 §10.5 为准）。
- **O3 契约强制（§9.3 L3 行，易混淆项）**：仍开放，归属 G5（修理组/观测组）——本次 correction 落码只覆盖 O1 协议，不覆盖 O3 的四条消费面契约。

### 10.7 文档同步（本次同批）

`设计/可观测建设方案.md`：§1.2 词表 11→12 类（+correction 行）、§1.6 SPEC 101→108 与 docstring 勘误闭环、§2.2 缺口计数改实、§3.3 硬规则 4②「实现列下一循环」改为已落码、§5 G1 状态（CI 已绿）、§6 未跑事项同步。`计划/变更日志.md` 追加一行。

---

## 11. 第二循环·账本元信息与本节点亲验（2026-10-22 10:23–13:0x CST）

### 11.0 元信息

| 项 | 值 | 出处 |
|---|---|---|
| 工作流 run | `dwfrun-5eeab2ec-0595-456c-ad11-012ee9bdee8c`，名「**研究组③可观测组·第二循环·施工方案设计**」，`status=running`，`spent_tokens=130,936,678`，`time_created`=10:23:31 | `~/.zcode/cli/db/db.sqlite` 表 `dwf_run`（本节点亲查，`select id,name,status,spent_tokens,time_created from dwf_run where id=…`） |
| 流程脚本 | `.zcode/workflow-drafts/研究组3-可观测组.dwf.ts`（mtime 10:23），四段：L1-L5 销账→红队·实现审查（`:35`/`:44`）｜底座重构施工方案→红队·施工方案终审（`:49`/`:58`，**rejected 才回撰写员** `:63`）｜RSI 预填（`:67`）｜红队·三审→状态记账员（`:75`/`:81`） | 文件本体（行号为该文件） |
| 人物线（7 actor） | 观测实施员 19217（GLM-5.3-Flash）· 红队·实现审查 19229（step-5-preview）· 方案撰写员 19232（GLM-5.3-Flash）· 红队·施工方案终审 19247（step-5-preview）· RSI 预填员 19271（MiniMax-M3.1-Flash-Preview）· 红队·三审 19274（step-5-preview）· **状态记账员 19286（MiniMax-M3.1-Flash-Preview，本节点）** | `dwf_actor` 表（`select id,name,resolved_model from dwf_actor where run_id=…`） |
| 节点账（8 节点） | ask#1=**32527**（10:23:31 观测实施员）→ ask#2=**32576**（11:23:01 红队·实现审查 confirmed）→ ask#3=**32590**（11:36:52 方案撰写员 v1）→ ask#4=**32615**（12:02:08 红队·施工方案终审 **rejected 13 条**）→ ask#5=**32646**（12:27:42 方案撰写员 v2 重写）→ ask#6=**32657**（12:42:34 RSI 预填）→ ask#7=**32665**（12:45:14 红队·三审 **confirmed** 4 条）→ **ask#8=32682（13:0x 状态记账员，running）** | `dwf_node` 表（`select id,site_id,kind,status,time_created from dwf_node where run_id=…`） |
| 循环性质 | **施工前设计循环，零生产影响**：代码改动仅限 af 分支 `fix4-observability` 与 checker；施工执行（金丝雀/换装/迁移/接线/注入演练）全部留 T0 窗口 | 脚本 `COMMON` 硬性纪律①（`.zcode/workflow-drafts/研究组3-可观测组.dwf.ts:31-32`） |
| 本循环产出物 | `设计/底座重构施工方案.md`（**553 行**，v2）、`设计/RSI自我改进方案.md`（**193 行**，新增 §8.1 预填）、`计划/研究组/可观测组-state.md`（§10 实施员段 + §11–§17 记账员段） | 本节点 `wc -l` 亲跑（见 §11.1） |

### 11.1 本节点亲验（记账员，2026-10-22 13:0x–13:02 CST，全部本节点实跑）

| 自测项 | 命令 | 输出 | 判读 |
|---|---|---|---|
| **CI 七门复跑** | `cd /tmp/af-wt-obs2 && CARGO_TARGET_DIR=/home/pan-ding/afbuild-obs2 CARGO_INCREMENTAL=0 CARGO_PROFILE_DEV_DEBUG=0 bash ci/run.sh` | **7/7 PASS，exit=0**（fmt 455ms / clippy 792ms / test 9142ms / cue 42ms / scrub 254ms / cosign 62ms / deny 641ms） | **G1 的 CI 半边本节点独立复现**（本分支第 4 次：实施员 12:0x、红队 11:26、三审 12:50、本节点 13:0x）。跑后 `git -C /tmp/af-wt-obs2 checkout -- ci/out` 还原（跑前 worktree 有 4 个 `ci/out` 产物为 modified，系红队/三审复跑所留、未提交）→ 还原后 `git status --porcelain` **空** |
| **checker 全量复跑** | `cd 工具状态备份/observability && for d in runs/*/*/*/; do python3 obs-checker.py "$d"; done` | **9/9 逐条 `result: PASS (0 fail / 0 warn)`** | 存量 9 条独立事件流未因 correction 词表（12 类）被破坏；与 §10.5「18 次引用全 PASS」不矛盾（9 独立流口径照 §2.4） |
| **SPEC/词表机械复算** | `importlib` 加载 `obs-checker.py`，逐 `*_SPEC` 取 `len()` | TOTAL=**108**；`len(KIND_LEVEL)`=**12**；逐项 RUN_STARTED 32 / MODEL 11 / TOOL 8 / KEY_REFRESH 5 / RETRY_EXHAUSTED 7 / RESOURCE 4 / JUDGE 17 / RUN_FINISHED 13 / TERMINAL 4 / **CORRECTION 7** | 与 §10.1「终值 108」逐值相同 |
| **字节指纹** | `sha256sum tools/swev-judge.py 工具状态备份/observability/obs-checker.py /home/pan-ding/afbuild-obs2/debug/afbench-obs4 af/target/debug/af-bench tools/cb-judge.sh` | `0338566c…`（判分核）/ `aaae9e53…`（checker）/ `9f8beb1f…`（观测交付件）/ **`5494a49e…`（产线 af-bench，未换装）** / `9c8f9c98…` | 判分核冻结值**未漂移**；观测二进制仍寄居 /home 盘**未上生产位**（闸 7 产线无事件流来源的根因） |
| 生产工作树 | `git -C af rev-parse HEAD` + `git -C af status --porcelain` | `94cd1923c34842983049bce5f97b3dcb6c7c348b`（guardrail-fix2）；status 恰 **5 条未跟踪 `poc/` 目录** | 零生产影响守住（与 §0.1 / §10.0 同值） |
| 观测证据字节 | `stat -c '%y %n' …/pydata__xarray-2905-a1/events.jsonl …/index/runs-202610.jsonl` + `find 工具状态备份/observability -newermt '2026-10-22 11:00' -type f` | 两者 mtime 均 **2026-10-22 08:08:33**（循环一修复时刻）；11:00 后仅命中 `obs-checker.py` 与其 `__pycache__` | 本循环**未改任何事件流/索引/manifest**（append-only 未破） |
| G5/G7 接线实况 | `crontab -l`（rc=0，空输出）；`grep -rln obs-checker --include=*.py --include=*.sh --include=*.rs`；`ls tools/obs-mes.py`；`grep -n "A8\|A9" tools/factory-watch.py` | crontab **空**；grep 命中**仅 `obs-checker.py` 自身**（无任何调用方）；`tools/obs-mes.py` **不存在**；`factory-watch.py` **无 A8/A9 命中** | G5（MES 行+安灯+看板观测区）与 G7（checker 进巡检）**仍为 0**（本节点亲验，非转述） |
| **S2 金丝雀断言复现（三审中等硬伤）** | `grep -o '"judge_mode_actual":"[a-z-]*"'` 读 5 条基线流（d1/astropy-12907-a1、obs-smoke1 的 xarray-4629/4094/3677、obs-smoke2 的 xarray-3151） | **5 条全为 `"clean"`** | `设计/底座重构施工方案.md:148` 的 `assert jb['judge_mode_actual']==jn['judge_mode_actual']=='in-place'` 在 T0 **必失败** → 详见 §15.1 第 1 条与 §16 T0-1 |

---

## 12. L1–L5 逐项处置（第一循环遗留 → 第二循环销账）

处置定义全部引自 §9.3 遗留表（9 条终审意见处置后仍未闭环者），不新造口径。

| 项 | §9.3 定义（原文要点） | 第二循环处置 | 证据 | 红队·实现审查（node 32576，11:23，confirmed） | 三审复验（node 32665，12:45） | 现状（13:0x） |
|---|---|---|---|---|---|---|
| **L1** | `obs-checker.py` docstring「SPEC 合计 100」→101（不在当时授权内） | **已销账**：docstring 第 4 条改为 SPEC 合计 **108** 并留勘误史（100 有误 → 终审 O6 实测 101 → correction 落码后 108） | 实施员 node 32527；本节点机械复算 TOTAL=108 / KIND_LEVEL=12（§11.1） | 亲跑 importlib 复算逐项相同；docstring:23-28 写 108 并留勘误史 | 复算一致（其 evidence (c) 段） | **销账**；新 sha `aaae9e53…` 待登 RSI 闸 1 指纹表（见 §16 T0-3） |
| **L2** | O5 指纹常量同源（`main.rs` 硬编码 `spend_cap_cents=300`/`tool_spend_cents=1` vs 执行侧读 `Launch`） | **已销账**：af 提交 `59c1d6c` 引入单一常量 `SWEV_SPEND_CAP_CENTS=300`/`SWEV_TOOL_SPEND_CENTS=1`，指纹块与执行侧（Launch/BudgetLedger/BudgetBinding）同读 | 实施员 node 32527；红队 node 32576 证 `main.rs:43-44` 常量、指纹块 `:997-998`、执行侧 `:1041-1046` 同读；父提交 d73338e 的三处硬编码全替换；tb/injec 路径 100/1 未动（`obs: None` 无指纹对应物，不在 O5 范围） | confirmed；仅**行号漂移**轻微意见（证据引 `:905-907`/`:948-957`，实际 `:997-998`/`:1041-1046`） | 复验同源成立 | **销账**（与 L1/L3 同提交） |
| **L3** | O1 证据更正协议事件化（correction 事件类落码） | **已销账**：写侧 `obs.rs::append_correction` 三步（归档原字节→`observability-archive/corrections/<run_id>-<ts>[-kN]/`、从当前字节实取 old→改写 run_finished 派生字段→追加 `harness.correction` 事件）+ CLI `af-bench --obs-correct` + **checker 同一变更集**扩第 12 类/`CORRECTION_SPEC` 7 字段/第 12 项校验；索引行与 manifest 永不改写 | 实施员 node 32527；红队 node 32576 **独立合成复刻**全部用例（正向/链式/负向 a-b-c，篡改追加洗不掉）；三审 node 32665 用盘上 `req1.json`/`req2.json` 亲跑链式双更正：CLI exit=0 + checker PASS，删归档件 checker FAIL×3 | confirmed；**轻微**：证据引 `obs.rs:826-1005` 实际函数体 `:870-1029`（注释块起 `:843`）；另 checker 归档件缺失时 FAIL 文案「old=0 ≠ 归档实值 50199」中 50199 实为当前流回退源值，措辞歧义（判定行为正确） | 复验一致 | **销账**（O1 协议侧）；**但 §9.3 L3 行的 O3 消费面契约强制仍开放**——见 §12.3 |
| **L4** | O2/R1 独立哈希见证实体化（归档目录落盘 + checker 进巡检） | **机制已备、实体化留 T0**：归档目录布局、checker 校验、CLI 齐备；实体化四步见 §16（§10.6 的 ①G7 巡检接线→**T0-9**、②归档目录实体化→**T0-10**、③指纹表登记→**T0-3**、④换装→**T0-7**） | 实施员 node 32527 给了四步；本节点亲验：`ls 工具状态备份/observability-archive` → **不存在**（实体化确属未做）、`crontab -l` 空、grep 无 checker 调用方 | confirmed；证 `observability-archive` 目录不存在、巡检日志 11:0x 轮未含 obs-checker——与「留施工窗」声明一致，未越权冒领 | 同结论 | **留 T0**（执行项，§16） |
| **L5** | 2905 修复前字节（tokens=0 原始 events） | **不可恢复（既成破口）**，纯登记维持；复发防线已随 L3 落码（归档+correction 事件+索引锚），无需新动作 | 红队 node 32576：全观测树逐个 `sha256` **无 `f15d671b` 命中**（证实原字节确已不存在） | confirmed | 复验一致 | **维持登记**（不追补，只防复发） |
| **CI-G1** | G1 的 CI 七门半边 | **已销账**：本分支首跑 7/7 PASS（exit=0），并当场处置首跑暴露的存量债（分支从未过 fmt——纯 rustfmt 重排；clippy 三处：`div_ceil(2)`、`run_progress` 提具名 `ProgressRow`、`run_obs_slot` 死预置） | 实施员 node 32527 + 红队 node 32576 复跑 + 三审 node 32665 复跑（12:50:16）+ **本节点 §11.1 复跑**——四次一致 | confirmed | 复现 | **销账**（G1 剩「上生产位」半边，属 T0 换装） |
| **DISCIPLINE** | 硬纪律核对与文档落账 | 零生产影响：生产树未动、`tools/` 未动、判分核字节级未变、gov 未碰、零密钥操作；在飞进程/生产位未动 | 实施员 node 32527；红队 node 32576（`tools/` 11:00 后零改动、生产位 sha 与 rollout 手册 §2 期望值一致、2 个 factory-sched 在飞未动） | confirmed | 复验一致 | **销账** |

### 12.1 红队·实现审查（node 32576，11:23:01，verdict=confirmed）的 4 条轻微 + 1 条备案

| # | 级别 | 意见 | 处置 |
|---|---|---|---|
| I-1 | 轻微 | L2 证据行号漂移（引 `:905-907`/`:948-957`，实际 `:997-998`/`:1041-1046`），内容属实 | 本账 §12 已按**实际行号**改写；文件本体未动（行号仅在状态账/交付物描述里） |
| I-2 | 轻微 | §10.3 称 fmt 改动用「`git diff --ignore-all-space` 核对纯重排」——该命令对 rustfmt 折行重排**并非空 diff**（红队实跑仍有输出）；逐行亲读三处 diff 确为 token 保真纯重排 | 表述问题：§10.3 原文照旧保留（账不改史）；**引用 §10.3 时以「逐行 token 比对」口径为准** |
| I-3 | 轻微 | checker 归档件缺失时的 FAIL 文案「old=0 ≠ 归档实值 50199」中 50199 实为当前流 `run_finished` 回退源值，非「归档实值」 | 文案歧义，判定行为正确；改文案属 checker 改动 → 须与其余改动**同提交**（§1.2 词表纪律的类推），留 T0 批次一并处置 |
| I-4 | 轻微 | L3 证据引 `obs.rs:826-1005`，实际函数体 `:870-1029`（注释块起 `:843`） | 账内已按实际区间改写 |
| I-5 | **备案**（非问题） | 红队复核时在 `/tmp/af-wt-obs2` 重跑 `ci/run.sh` 改写 `ci/out` 产物，已 `git checkout -- ci/out` 还原、工作树干净；合成实测根 `/home/pan-ding/rt-l3-selftest` 及临时 req/log 已删，未在真实观测根留痕 | 本节点跑 CI 后同样还原（§11.1），**worktree 现状：status 空、HEAD=59c1d6c** |

### 12.2 本轮与「终审 9 条」的关系（防止下一轮误读）

- 第二循环**没有重开**终审 9 条：O1–O6/R1–R3 的处置在 §9 已销账；本循环做的是**把其中 3 条落到代码/机制**（O1→L3 correction 落码；O5→L2 同源修复；O6→L1 字段数勘误并随 L3 走至终值 108），另 2 条转执行项（O2/R1→L4 留 T0），R1 的「checker+写侧入冻结」随 L3 留 T0 落地（R1 闸位扩充在 RSI 文档侧已于 §9 落）。
- **O3（消费面契约 1–4 落成可执行检查 + A8/A9 触发演练）在本循环仍未做**——它挂在 §9.3 的 L3 行下，但 L3 本轮只销 O1 的协议落码，**O3 归 G5（修理组/观测组）**，本节点亲验 G5/G7 仍为 0（§11.1）。

---

## 13. 底座重构施工方案：路径与终审结论

### 13.1 产物路径谱系

| 段 | 时间 | 产物/动作 | 结论 | 出处 |
|---|---|---|---|---|
| v1 | 11:36:52（node 32590） | `设计/底座重构施工方案.md` v1（**521 行**，§0–§13+附录 A/B），S1–S10 工单 + 全局回滚 | 出稿 | node 32590 result |
| **终审 v1** | 12:02:08（node 32615） | 红队·施工方案终审（step-5，未参与撰写）亲读全文 + 亲跑复现 | **rejected，13 条**（4 阻断 + 4 回滚缺陷 + 冻结缺口 + 打断面过宽 + 3 轻微/容量/行号） | node 32615 `verdict=rejected`，`issues` 13 条 |
| v2 | 12:27:42（node 32646） | v2 **整体重写**（**553 行**，新增 §2 S0 移植工单、§0.5 基线漂移、**附录 C = v1 驳回→v2 逐条处置对照**） | 逐条实证后重写 | node 32646 result；文件本体 553 行（本节点 `wc -l`） |
| RSI 预填 | 12:42:34（node 32657） | `设计/RSI自我改进方案.md` §8.1（文件 157→**193 行**） | 预填完成（ready=0.13） | node 32657 result |
| **三审** | 12:45:14（node 32665） | 红队·三审（step-5，未参与本循环任何环节）审 L1-L5 真实性 / 施工方案完备性 / RSI 预填诚实性 | **confirmed，4 条意见（1 中 / 1 低 / 2 轻）** | node 32665 result |
| 记账 | 13:0x（node 32682，本节点） | 本账 §11–§17 | — | 本文件 |

**授权链（方案头注自述）**：运营者批复（2026-10-22 10:1x，`状态观测/业务目的章程.md:16`）→ 厂长 T0 施工时序（章程 `:17`）→ 本方案。章程 T0 时序原文（`状态观测/业务目的章程.md:17`，本节点亲读）：**T0=①②④当前循环全部收官+重试臂终态后的第一个空窗**，动作串行 = 暂停 main-sched → af-bench 观测二进制过 CI 七门+金丝雀 → 换生产位 → tmpfs 重迁移分批 → MES/看板/watchdog 观测接线 → mcode dispatch 组合补丁（D-34 重判+干净工作区+keepalive 完成态）→ MES 观测基建迁 mingda-website → mcode 干净重跑启动 → RSI 八道闸核验 → RSI 降级版首发（有人值守）。

### 13.2 v1 驳回 13 条 → v2 处置对照（摘要，落点以方案附录 C 原文为准）

| # | 驳回意见 | v2 处置落点 | 复证 |
|---|---|---|---|
| 阻断 1 | 换入件代际错配：fix4-observability = fix2 harness + fix3 判分搬干净容器，**不是** fix1 护栏代；方案 §4 三条验收判据物理上不可能同时满足 | **新增 S0 移植工单**（§2）：把 fix4 观测能力移植到 `guardrail-fix1`（d083565）形成 `fix4-obs-fix1`，过 CI 七门+金丝雀后才可换装；移植失败则 S3 取消（备选 B，如实登记） | main 谱系 / merge-base(fix4,main)=f373113 / `main.rs:120` 默认 `judge_mode="clean"` / `:1222-1236` scaffold=v3,attempts=1 / `swev.rs:273`+`judge.rs:75` verify_clean 本机 docker / `factory-sched.py:496-499` spawn 无 `--judge-mode` / 生产行 15 键 |
| 阻断 2 | refs 裁剪三面不成立 + fail-closed 断言必炸 + `--shared` alternates 使 post-base 对象可枚举 | **裁剪方案废弃** → **单 rev bundle 工作区**（对象级隔离，以在飞 `clean-prep.sh` 为准一实现），配对象级断言 | 合成仓 `/tmp/selftest-trim` 复现：tags 存活 / `rev-list --all --count`=2≠base=1 / `cat-file -t`=commit；anolis 三仓 refs/tags 实测 |
| 阻断 3 | S8 与在飞干净重跑（`/tmp/mcode-clean-rerun/driver.py` pid 454598，12:20 起）正面相撞，方案基线早于其启动 | **S8 重定义**为「在飞重跑的对账/抽检/收尾」，**禁第二条干净重跑**；m3 档登记缺口 | driver.py 实读、docstring「运营者 11:5x 批准」、results 2 行 |
| 阻断 4 | T0-1 半盲（`factory-status.json` 无 `status` 键，116 条目键=kind/state/note）+ 不知全部在飞臂 + /tmp 恶化 | **§0.1 T0-1 重写**（`state` 键 + 全 runner 清点、python3 前缀过滤 pgrep 自匹配）；11 个非 bench-* 目录列「登记不迁」；S4 定为最急步 | 键分布亲读、11 目录清单、/tmp 74%（波动 81%）、driver 避让 klog |
| 回滚 S5 | `pgrep -f factory-watch.py` 自匹配会**自杀执行 shell** | 改 `cat 状态观测/watchdog.pid`（=3692358） | pidfile 在 |
| 回滚 S7/S12 | 「改回常量即恢复」与「24h 只停写不停服」矛盾 → 回滚丢账 | mingda→本机**反向补账**步（幂等按 event_id） | 逻辑修订（未演练） |
| 回滚 S12 | `.prev` 副本被回滚一行消费 → 全局回退 `&&` 静默跳过，fix4 二进制留生产位 | 耐久源 = `af/target/debug/af-bench-fix1-guardrail`（5494a49e 同字节），cp+mv 原子落位 | sha 同值 |
| 回滚 S8 | `MCODE_OUT_ROOT` 注入点未定（keepalive 以 `env+=[]` spawn） | 仅显式手工启动注入，keepalive 不带、无粘性态 | 机制澄清 |
| 冻结缺口 | `tools/cb-judge.sh`/swev-venv 未入冻结表；`fp_*` 是随动值不能当冻结值 | §0.3 扩表（静态值 + T0 录 venv/镜像指纹）；D-34 重判前先对冻结表 | cb-judge sha / venv 路径亲读 |
| 打断面过宽 | 孤儿 TERM 规则比 keepalive 宽，会打断他组臂 | 收窄为 `ppid==1 且 exe==MAIN_BIN`；他人臂不碰只登记 | keepalive MAIN_BIN 口径 |
| S2 容量 | fix4 二进制跑 verify_clean 会在本机 docker 起 4g 判分容器；指纹脚本读错事件 | 加**容量闸** + 行为验收 `docker ps -a \| grep -c afbench-judge`=0；比对脚本改读 `harness.judge` 事件 | `run_started` 无 `judge_mode_actual` 亲验 |
| 行号漂移 | keepalive 行号普遍偏 13–27 行 | 全文改用修正锚点（self_guard :1015-1024 / exit3 :1023 / dry-run return :1044-1046 / 常驻启动 :1048-1050 / pidfile finally :1080-1085） | 四段亲读 |
| 轻微 | 「213MB 副本」不实；1.3G 归因；obs-mes 残留 | 换入件 27MB / 213MB 是被换下件；log 仅 128K；全局回滚显式 `rm tools/obs-mes.py` | 27,178,488 B / 128K |

### 13.3 v2 的冻结值与基线漂移（施工时全程有效，任一漂移=全局中止）

- **§0.3 冻结值**（本节点复核 sha 值一致）：`tools/swev-judge.py`=`0338566c…`、`tools/cb-judge.sh`=`9c8f9c98…`、checker=`aaae9e53…`、swev-venv 与判分镜像指纹 = T0 快照时录为静态值（**现未录，T0 开工第一动作**）；`fp_*` 是**随动值**，不得当冻结值用。
- **§0.5 基线漂移登记**（v1→v2 期间发生，非本组所为）：keepalive 12:02:25 换血（pid 427313）→ 12:13:2x klog 出现 `[dry-run]` 对象行且**当前无 keepalive 进程、pidfile 不存在＝守护停摆**；12:13:27 mcode 防抖 ALARM「600s 内已重启 2 次超限停止拉起」；在飞干净重跑 driver.py 12:20 上线；align2 探针臂 12:2x 前终态。**T0-1/T0-4 已把「keepalive 恢复为真实常驻」列为开工检查项**（T0-4）。
- 纪律（方案 §0.3 末）：gov 零触碰 / 密钥零明文 / sudo 自限 / 观测证据只增不删 / 判分语义永不进补丁可写范围。

### 13.4 终审结论（三段式，照实登记）

1. **对 v1：rejected，13 条**（node 32615）——四阻断全部实证成立（代际错配、refs 裁剪不成立、撞在飞重跑、T0-1 半盲），非"意见分歧"而是"物理上不成立"。
2. **对 v2：无独立的第二次红队终审节点**——脚本只在 `verdict==="rejected"` 时回派撰写员（`.zcode/workflow-drafts/研究组3-可观测组.dwf.ts:63-65`），重写后**不再派终审**；v2 的复核由**红队·三审**（node 32665）承担，其结论为 confirmed（附 1 条中等硬伤，见 §15.1 第 1 条）。**此处如实登记**：v2 未经历"v1 那种逐条攻击式终审"的第二轮，读者引用「施工方案经红队终审」时应带这句限定。
3. **整体可用性判定**：施工方案可作为 T0 工单集使用（S0–S10 + §13 全局回滚 + 附录 C 对照），**唯一必须在 T0 开工前修掉的硬伤 = S2 金丝雀指纹脚本断言**（否则 T0 金丝雀必假死并把诊断误导向"移植混入 fix3 路径"）。修法见 §16 T0-1。

### 13.5 观测组在施工串里的边界（防越权登记）

- **本组主责工单**：S0（观测能力移植到 fix1 底座）· S2（金丝雀 5 题 + 指纹比对）· S3（换生产位）· S5（MES/看板/watchdog 观测接线＝G5/G7 件）· S9（RSI 八道闸核验单）· S10（RSI 降级版首发·有人值守）。
- **非本组主责**：S6（mcode dispatch 组合补丁 + keepalive 完成态）**标注「会签④」**（`tools/mcode-dispatch.py`、`tools/factory-keepalive.py` 由资源管理组在管）；S7（MES 观测基建迁 mingda-website）属章程 11:1x 决策项，非 ask 八项；S8（在飞重跑对账）与 S4（tmpfs 迁移）为底座面。

---

## 14. RSI 上线检查单预填摘要（as-of 2026-10-22 12:5x CST）

**落点**：`设计/RSI自我改进方案.md` **§8.1「八道闸 + 上线卡口现状预填（as-of 2026-10-22 12:5x CST · 预填非终态）」**（第 151–186 行；文件由 157 行增至 **193 行**，本节点 `wc -l` 亲验）。**执行者**：RSI 预填员（MiniMax-M3.1-Flash-Preview，node 32657，12:42:34）。**性质声明（原文）**：本节是一次**只读盘点**（未动任何环、未跑任何闸的演练、未换装、未改 `tools/`）；所有 ✅ 只表示「本节作者在该命令下亲验通过」，不表示闸已上线。

### 14.1 预填期两处口径校正（下游引用必带）

1. 观测交付二进制**不在** `/tmp/afbuild-obs/debug/afbench-obs4`（`sha256sum` → No such file），实际在 `/home/pan-ding/afbuild-obs2/debug/afbench-obs4`（与 §10.4 的 target 迁移偏差登记一致）。**本节点复核：该路径存在、sha=9f8beb1f…**。
2. **产线仍是 fix1 护栏件**：`af/target/debug/af-bench` = `5494a49e…`（= rollout 手册 §5 主产线行）→ 观测二进制**尚未换装上生产位** → 闸 7 在产线**无事件流来源**。**本节点复核：sha 同值**。

### 14.2 八道闸现状（闸 1🟡、闸 7🟡，其余六闸🔴；合计 **0 闭环**）

| 闸 | 状态 | 已具备（预填员亲验） | 缺口（摘要） |
|---|---|---|---|
| 闸 1 verifier 只读挂载 | 🟡 | 指纹三件 9/9 流同值（`fp_judge_script_sha256`=0338566c…、`fp_judge_env_sha256`=0a98efe33071…、`fp_image_digest` 逐题有值）；`run_started` payload 实测 32 字段 | ①**判据与载体不一致**：闸 1 写「由索引行 `fp_*` 判定」，但索引 9 行只有 `fp_image_digest` 一项（另两件只在 events.jsonl 内）→ 要么补索引字段、要么改判据读事件流；②**指纹表文件不存在**（checker `aaae9e53…`、交付件 `9f8beb1f…` 无处登册）；③checker + 写侧 `obs.rs` 黑名单无载体；④只读 bind-mount 未实测（=K3） |
| 闸 2 诱导失效演练 0 静默放行 | 🔴 | **仅部分先例**：`harness.correction` 负向三用例 checker FAIL 留痕——但那是 checker 自测，**不能充抵 K4 注入演练** | 四注入零演练、无脚本无报告 |
| 闸 3 双门合入+判负 | 🔴 | 判据数字已预登记（涨分∧留出掉≤0.5pp；>1pp 判负；回滚率>30%；0.5–1pp 记环级判负信号——即 §9 R3 界定） | 无优化/留出分池、无配对检验与 CI 实现、无 `pass^k≥4` 执行器 |
| 闸 4 Stop 钩子 | 🔴 | 回滚载体可用（分支体系在位：`fix4-observability`=59c1d6c、产线树=94cd192） | 「连续 3 补丁无泛化通过即停环」计数器未实现；**`fix<N+1>` bump 口径未定**（观测 `fix4-observability` vs 护栏 `guardrail-fix2` 两套代际命名并存） |
| 闸 5 爬坡斜率/预算闸 | 🔴 | 指标口径已预登记 | 调度器限额图**无 RSI 臂**；本循环禁改 `tools/` |
| 闸 6 采样-投票基线臂 | 🔴 | 倒 U 停机判据已预登记（含禁模型自评信号） | 无 best-of-N 臂、无同预算对照 |
| 闸 7 观测闸（证据完整性） | 🟡 | checker 亲跑 **9/9 全 PASS**（d1×4 / obs-smoke1×3 / obs-smoke2×2）、merkle 6 份、索引 9 行在位 | ①**无人调 checker**（crontab 空、grep 无调用方）②覆盖面=1 档案 m31f/单 host/冒烟规模，`budget`/`unauthorized` 两类 critical **零真实样本** ③产线无事件流来源（二进制未换装） |
| 闸 8 重大补丁人工抽检 | 🔴 | 常设控制已定义（触发定义 + 降级版「每轮全量人工批准」） | 抽检登记**五栏无落处**（补丁 id/触碰清单/双门读数/指纹对照/结论）、无抽检人指派 |

### 14.3 上线卡口 K0–K7（**全🔴**）

| 卡口 | 状态 | 缺口摘要 |
|---|---|---|
| K0 时序前置 | 🔴 未满足 | 四项前置无一闭环：①对齐组 run 仍 running（账记 58.4M tokens，as-of 09:27），差距 D1 20.75/D2 42.11/D3 60.00pp 未收敛；②调优组二循环在飞；③观测 G2–G7 全未开始（预填员引 `设计/可观测建设方案.md` §5 口径；仅 G1 已绿）；④资源 `gc_watch` 端到端待复验、P0-4 未跑。**T0 定义**=章程「①②④收官+重试臂终态后的第一个空窗」 |
| K1 假设池 | 🔴 | `计划/研究组/rsi-假设池.jsonl` **不存在**；种子素材在 `计划/技术债登记.md:39/40/42`（D-31/D-32/D-34）但未结构化、无 schema 评审 |
| K2 任务三分冻结 | 🔴 | 素材齐（`计划/s1-swev-120.json` 120 条 = D1 60/D2 40/D3 20、12 repo；`/tmp/swev-s1/*.json` 恰 120 包）但**三分池划分文件缺失、题号哈希零交集检查未跑**；且 `/tmp` 在 tmpfs → D-24 迁移前冻结池不得落 tmpfs |
| K3 只读挂载实测 | 🔴 | 无演练记录；`/tmp/af-wt-obs2` HEAD=59c1d6c，但对 `tools/swev-judge.py` 无只读约束 |
| K4 四注入演练 | 🔴 | 无演练报告（同闸 2） |
| K5 DSL 白名单+路径 lint | 🔴 | **零实现**：全仓 `grep -rln "patch_meta\|DSL 白名单\|path lint\|路径 lint"` 仅命中 5 份 `.md`，无 `.py`/`.rs`/`.sh` |
| K6 降级版 1 run×3 轮 | 🔴 | 依赖 K1/K2/K3/K5 |
| K7 八闸状态表进章程+巡检 | 🔴 | 章程**无 RSI 闸节**（仅 T0 序列里一句「RSI 八道闸核验」）；巡检链无 checker 步骤 |

### 14.4 ready 数值与其可复算性（口径债，如实登记）

- 预填员回执 `ready=0.13`，`gaps` 共 **18 条**（8 闸 + 8 卡口 + 2 条口径校正）。
- **三审（node 32665）指其不可从盘上产物复算**（§8.1 全文未给算式，且三审会话 workflow introspection 不可用、读不到 node 32657 的 result_json）。**本节点同样无法从盘上复算 0.13**（§8.1 正文无算式）——但本节点**读得到** node 32657 的 result_json（db 只读查询），确认 `ready=0.13`、`gaps` 18 条与其自述一致。
- 结论：0.13 的**方向**与预填内容（六🔴二🟡、K0–K7 全🔴、几乎全部未开始）不矛盾、无夸大迹象；**确切来源未给算式 = 口径债**，引用时须写「预填员自评，as-of 12:5x，算式未给」。

### 14.5 预填留下的三个待裁决小项（不阻塞盘点，供 T0 前定）

①闸 1 判据与索引字段不一致（补索引字段 or 改判据读事件流）；②`fix<N+1>` bump 口径与护栏代际命名的关系；③RSI 假设池/变更日志的落盘位置（建议 `计划/研究组/rsi-假设池.jsonl`，**未建**）。

---

## 15. 红队·三审意见（node 32665，12:45:14，verdict=**confirmed**，4 条）

**审者**：`红队·三审`（step-5-preview，actor 19274，**未参与本循环任何环节**）。**审什么**：L1-L5 销账真实性 · 施工方案完备性（回滚面/验收判据逐步在位）· RSI 预填诚实性。

### 15.1 逐条意见 + 本节点独立复验

| # | 级别 | 三审意见（要点） | 本节点复验（13:0x 亲跑） | 判定 |
|---|---|---|---|---|
| **1** | **中·T0 开工前必须修** | **施工方案 §3 S2 金丝雀指纹比对脚本**（`设计/底座重构施工方案.md:148`）断言 `jb['judge_mode_actual']==jn['judge_mode_actual']=='in-place'`，与盘上事实不符：5 条同题基线流的 judge 事件全部 `judge_mode_actual="clean"`（fix2/fix3 代际产物）。该断言在 T0 必失败 → 按 §3 失败处置触发**全局中止**，但 §0.3 冻结值并未漂移，属**脚本缺陷假死**，且会把诊断误导向「移植混入 fix3 路径」。方向 fail-closed（不误放行）但**验收判据不可执行**。三审给的修法：fp_* 三件做前后比对；`judge_mode_actual` 只对新流断言 =='in-place' 且 declared↔actual 互证；基线 clean 代际差显式登记为预期差异 | **已复现**：读 `runs/d1/m31f/astropy__astropy-12907-a1` 与 `runs/obs-smoke1/mavis-m31f/pydata__xarray-{4629,4094,3677}-a1`、`runs/obs-smoke2/mavis-m31f/pydata__xarray-3151-a1` 的 events.jsonl，5 条 `judge_mode_actual` **全为 `"clean"`**；方案 `:148` 的 `assert ... == 'in-place'` 原文亲读在案 | **意见成立**。本节点采纳为 T0 开工前第一顺位（§16 T0-1） |
| **2** | 低·告知 | RSI 预填 `ready=0.13` **无法从盘上产物复算**（§8.1 全文未给算式；三审会话 workflow introspection 不可用，读不到 rsiPrep 的 result_json）。方向不矛盾、无夸大迹象，但确切来源未经核实 | 本节点读得到 node 32657 的 result_json（db 只读），确认 `ready=0.13` + gaps 18 条与自述一致；**但 §8.1 正文仍无算式** | **意见成立**（可复算性缺口仍在），登记为口径债（§14.4） |
| **3** | 轻 | RSI 预填 §8.1.2 K0 ④ 引文「巡检日志 12:1x 记『T0 条件待①②③④收官』」系**混引**：12:1x 条目实为「T0 条件（①②④收官）」，「待①②③④循环收官」出自 11:0x 条目。不影响结论 | 未逐条比对巡检日志两个时点条目（未跑该核对） | **意见登记**，本节点未复验（§17 明列） |
| **4** | 轻 | 施工方案 §4 锚点 `factory-keepalive.py:481-500` 与实际 `def fix_main_sched(:482)` 差一行；全文已多处声明「以开工盘上版本为准」，可忽略 | 未逐行核对（未跑该核对） | **意见登记**，本节点未复验（§17 明列） |

### 15.2 三审的亲验清单（摘要，供下一轮引用其可信度）

三审自述本会话亲跑并给出：生产树 HEAD=94cd1923…（仅 5 个未跟踪 `poc/`）、`fix4-observability`=59c1d6c（12 文件 +1573/−1028，父 d73338e）、判分核 sha=0338566c… 且与 9/9 流 `fp_judge_script_sha256` 逐字相同、`fp_judge_env_sha256` 9/9=0a98efe33071…、checker=aaae9e53…、交付件=9f8beb1f…（27,178,488 B）；L1 机械复算 108/12；L2 代码级同源；**L3 用盘上 `req1.json`/`req2.json` 亲跑链式双更正（CLI exit=0、checker PASS、负向删归档 FAIL×3）**；**CI 七门独立复跑 7/7 PASS（12:50:16）**；存量 9 流复跑 9/9 PASS；施工方案基线亲测（main 谱系/merge-base/guardrail-fix1=d083565/产线 5494a49e 213,734,984 B/cb-judge 9c8f9c98…/sched spawn 无 `--judge-mode`/`main.rs:120` 默认 clean/`:1222-1236` scaffold=v3,attempts=1/verify_clean 本机 docker/factory-status 116 条 kind,state,note/watchdog.pid=3692358//tmp 75%/keepalive 无 pidfile/三个在飞 pid 均在/`run_started` 无 `judge_mode_actual`）；RSI 预填逐条核（crontab 空、checker 无调用方、假设池不存在、旧路径不存在、索引 9 行 fp_* 仅 image_digest、run_started 32 字段、merkle 6 份、s1 池 120 条 D1 60/D2 40/D3 20 + `/tmp/swev-s1` 恰 120 包、对齐组 run 58,429,175 tokens、K5 无实现）——**全部属实**。三审验证 scratch（`/home/pan-ding/obs-3rd-check*`）已删除。

### 15.3 结论与边界

- **三审结论 = confirmed（附 1 条中等硬伤 + 3 条告知/轻微）**，可作为第二循环整体可信度背书。
- **但**：`confirmed` **不等于**施工方案已可直接开工——S2 脚本断言必须先修（§16 T0-1），否则 T0 金丝雀必假死并触发全局中止判据。
- 三审未改任何交付文件（其 scratch 已删）；第二循环全程**零生产影响**（生产树 94cd1923… 未动、产线二进制 5494a49e… 未换装、观测事件流 mtime 仍 08:08:33）。

---

## 16. 留给 T0 施工窗的执行清单（观测组口径）

**T0 定义**（章程 `:17`）：①②④当前循环全部收官 + 重试臂终态后的**第一个空窗**。施工时序（章程）+ 方案工单集（`设计/底座重构施工方案.md` S0–S10）为准；本清单只列**观测组拥有或必须参与**的条目。

### 16.1 阻塞级（T0 开工前必须完成）

| # | 动作 | 来源 | 验收判据 | 失败处置/回滚 | 归属 |
|---|---|---|---|---|---|
| **T0-1** | **修 S2 金丝雀指纹比对脚本**（`设计/底座重构施工方案.md:148`）：fp_* 三件（`fp_judge_script_sha256`/`fp_judge_env_sha256`/`fp_image_digest`）做前后比对；`judge_mode_actual` **只对新流**断言 =='in-place' 且 declared↔actual 互证；基线 5 流的 `"clean"`（fix2/fix3 代际产物）**显式登记为预期差异** | §15.1 第 1 条（三审中等） | 新脚本在**基线侧**自测不假死（对 5 条 clean 基线流按"预期差异"分支通过）；对移植产物新流断言 in-place 成立 | 假死即**全局中止**（§0.3 冻结值未漂移时的假死，不得据此诊断移植混入 fix3） | 观测组（改方案文档）＋施工执行者（跑） |
| **T0-2** | **T0 快照时录静态指纹**：`swev-venv`（`sha256(swev-venv/bin/python)` ‖ `sha256(pip freeze)`）、判分镜像（`docker images --format '{{.Repository}}@{{.Digest}}' \| grep sweb.eval \| sort \| sha256sum`）→ 存 `t0-snapshot/venv-fp.txt` 等 | 方案 §0.3 + §13.1 | 静态值入库且**开工前后各比一次**，任一漂移=全局中止 | 漂移即停，查来源（gov/镜像源） | 厂长（快照） |
| **T0-3** | **冻结值与指纹表落地**：把 checker `aaae9e53…`、观测交付件 `9f8beb1f…`、写侧 `obs.rs` 登进 **RSI 闸 1 指纹表**；建「补丁可写范围黑名单」载体（判分核三件 + checker + 写侧）；顺带裁定 §14.5-①（闸 1 判据 vs 索引字段） | §12 L4 步骤3 ＋ RSI §8.1 闸1/K5 ＋ §14.5-① | 指纹表文件存在于 `工具状态备份/observability/`；黑名单有载体；checker 反查可用 | 未建则闸 1/闸 7 维持 🟡，不得进无人值守 | 观测组 + 修理组（K3/K5 范围） |
| **T0-4** | **T0-1/T0-4 触发检查**（方案 §0.1）：全部 runner 在飞清零（`state` 键 + 全 runner 类进程）/ 三组循环收官 / 执行人在位 / **keepalive 恢复为真实常驻**（现状：停摆，无 pidfile、klog 末段 `[dry-run]` 对象行 + 防抖 ALARM 自停） | 方案 §0.1 + §0.5-b | 四项全绿才开工；keepalive 有 pidfile、进程在、非 dry-run | 不满足即**不开工**（S1 会按原子序先停它再走） | 厂长 |

### 16.2 观测组自有工单（施工串内）

| # | 动作 | 方案落点 | 验收判据 | 回滚 | 归属 |
|---|---|---|---|---|---|
| **T0-5** | **S0 移植工单**：把 fix4 观测能力移植到 `guardrail-fix1`(d083565) → `fix4-obs-fix1`（fix1 判分/测量为准；fix3 五类物零在场 grep 断言；结果行 15 键逐键冻结；观测走 sidecar） | §2（阻断 1 处置） | CI 七门全绿 + 金丝雀通过；`fix3` 物零在场断言通过 | 移植失败 → **S3 取消（备选 B）**，如实登记 | 观测组（af 分支） |
| **T0-6** | **S2 金丝雀 5 题**（astropy-12907 + xarray 3151/3677/4094/4629）：指纹前后比对（**断言须先按 T0-1 修，本节点未修**）、`docker ps -a \| grep -c afbench-judge`=0、checker PASS | §3（含 T0-1 修法） | 5 run 全 completed 且 checker PASS(0 fail/0 warn)；冻结值三件前后相同 | 失败即不进 S3，证据留档（观测流不删，硬规则 1） | 观测组 + 施工执行者 |
| **T0-7** | **S3 换生产位**：只换主位 `af/target/debug/af-bench`（当前 5494a49e…）；实验线 `af-bench-fix2`(d2b36cab…) 不动；备份 + 原子换名 | §5 + rollout 手册 §2 | 生产位 sha = **移植产物 sha**（fix4-obs-fix1@CI 全绿版），代际口径=fix1（15 键/scaffold=v2/in-place 判分/护栏上限在），观测流 checker PASS | 耐久回滚源 = `af/target/debug/af-bench-fix1-guardrail`（5494a49e… 同字节），cp+mv 原子落位（**不得用会被消费掉的 `.prev`**） | 观测组 + 厂长（按 rollout 手册） |
| **T0-8** | **S5 观测接线（G5/G7 件）**：①新建 `tools/obs-mes.py`（`--sync` 幂等，DDL `af_mes.obs_run`，CH 不可用写欠账 `mes-debt.jsonl` 不闸断测量）；②`tools/factory-watch.py` 扩 A8 观测流缺失 / A9a 完整性（=G7，每 2h 增量跑 checker，fail 即 amber）/ A9b 越权预算(red) / A9c 镜像漂移；③看板 `data.json` 增 `obs` 键 + `index.html` 观测区 | §7 | `obs_run` 行数==索引行数（执行时实数）；A8/A9a-c 各一次 fixture 注入演练留痕（副本根 `observability-selftest/`，不碰真根）；看板机读读数随轮刷新；**G7 首跑入巡检日志 exit=0** | 备份 `factory-watch.py.pre-obs-R2-<ts>`；回滚 = 恢复备份 + `kill -TERM $(cat 状态观测/watchdog.pid)`（**禁用 `pgrep -f`，自匹配会自杀**）；obs-mes.py 停用并 `rm`（全局回滚不得留盘） | 观测组（+看板/维修） |
| **T0-9** | **G7 巡检接线（L4 步骤 1）**：巡检链每 2h 对增量 run 目录跑 `obs-checker.py`，fail 即安灯；最小验证=手工对 `runs/d1/m31f` 跑一次入巡检日志 | §12 L4 步骤1 + RSI 闸 7 缺口① | 巡检日志出现 checker 行且 exit=0；再决定是否上宿主 cron | 回滚 = 撤该步 | 观测组 + 厂长（巡检链） |
| **T0-10** | **归档目录实体化（L4 步骤 2）**：`mkdir -p 工具状态备份/observability-archive/corrections`（本节点亲验：**当前不存在**）；首次真实更正发生时协议自动生效 | §12 L4 步骤2 + 方案 §3.3 硬规则 4 | 目录存在且权限正确；首条真实更正能落两份归档 | 目录可空置（协议自动生效） | 观测组 |
| **T0-11** | **G2 词表 12 类全实证**：构造 `budget_exhausted` / `unauthorized` 触发样本各 ≥1 run 过 checker（只造 2 个 run 的成本） | §6.1 G2（两 critical kind 至今 0 真实样本） | 两条真实样本过 checker（0 fail） | 造不出则如实登记为未实证 | 观测组 |
| **T0-12** | **G3 TB / rejudge 接线决策**：补接线 **或** 显式声明不观测（现状 `main.rs:1410` run_tb / `:1580` run_injec 显式 `obs: None`） | §6.1 G3 | 决策有记录（接线→有流；不接线→有理由） | — | 观测组 |
| **T0-13** | **G4 多档案实证**：glm-cp 或 step-5 档案 ≥1 冒烟轮全 PASS（现 9 条流全 mavis-m31f 单档案） | §6.1 G4 | ≥1 条非 m31f 档案事件流过 checker | — | 观测组 |
| **T0-14** | **G6 keepalive 存在性校验扩面**：删目录演练，7s 级恢复（D-25 同款） | §6.1 G6 | 演练记录 + 恢复耗时读数 | — | 资源管理组主责，观测组见证 |
| **T0-15** | **O3 契约 1–4 落成可执行检查**（§9.3 L3 行、§12.3）：CI 路径 lint / 统一 writer 库；**A8/A9 触发演练记录**；G5 判据明晰化（MES 行可查 / 安灯演练留痕 / 看板机读读数+刷新时点，非截图） | §9.1 O3 + 方案 §4.5 | 四条契约各有可执行入口（lint 报错即拦） | 未落则 G5 判据维持"半纸面"标注 | 观测组 + 修理组 |
| **T0-16** | **RSI 卡口落码（T0 段）**：K1 假设池建档（D-31/32/34 种子，schema 走"只增不改"）· K2 三分池划分 + 题号哈希零交集检查（**冻结池不得落 tmpfs**，先定 out 根）· K3 只读挂载演练（ro bind-mount 判分核三件 + `--obs-correct` 拒写判分路径，留拒写日志）· K4 四注入演练 0 静默放行（每次留"注入前后指纹+被哪道闸拦+安灯"三件套）· K5 DSL 白名单+路径 lint（黑名单含判分核三件 + `obs-checker.py` + 写侧 `obs.rs`）· K7 八闸状态表进章程 + 巡检加 checker 步 | RSI §8.1.2 + §14.3 | 各卡口判据有证据文件；任一静默放行=整轮重跑 | 未做则**不得进无人值守**（可阻有人值守首发） | 观测组（K3/K4/K5）+ 修理组（K1/K2/K7） |
| **T0-17** | **S9 RSI 八道闸核验单 / S10 降级版首发（有人值守）**：逐行有证据、降级版首轮五件套齐 | 方案 §11/§12 | 方案 §14 DoD 第 6 条 | — | 观测组 + 厂长 |
| **T0-18** | **观测事件流证据登记**：全程产物落 `工具状态备份/t0-evidence-<ts>/`（s0…s10 子目录），每步验收命令与输出原文入档 | 方案 §14 证据登记 | 归档齐 + 变更日志/巡检日志/技术债登记补记 | — | 观测组 |

### 16.3 非本组主责但需会签/知会（防越权）

- **S6（mcode dispatch 组合补丁 D-34 + 干净工作区 + keepalive 完成态）**：`tools/mcode-dispatch.py`、`tools/factory-keepalive.py` 由**④资源管理组在管** → **会签④**（diff 审阅 + 与其在飞改动无同窗冲突 + 变更日志双记）；方案 §8.3-b 的 D-34 重判**前置比对冻结表**。
- **S7（MES 观测基建迁 mingda-website）**：章程 11:1x 运营者决策项，**不在本组 ask 八项内**；本组只保证 `obs_run` 写入方（bench-mes/sched/watchdog/看板）回指不漏。
- **S8（在飞干净重跑对账/抽检/收尾）**：底座面，**禁第二条干净重跑**（阻断 3 处置）。
- **m3 档缺口**（mcode 干净重跑只跑 m31f 档）→ 登记后续派单候选，勿在 T0 悄悄扩题。

### 16.4 纪律随行（每步适用）

gov 零触碰 / 密钥零明文（`key_refresh.ok` 只落布尔）/ sudo 自限（只读取证优先、留证、系统级变更列单）/ 观测证据只增不删（append-only，派生值可重导但**必须留更正记录**——硬规则 4）/ 判分语义永不进补丁可写范围 / 断流产物不得落 tmpfs（D-24）/ 跳过 T0 触发检查直接开工＝违反章程。

---

## 17. 本循环未跑 / 未覆盖（据实登记）

| 项 | 状态 |
|---|---|
| **本节点（记账员）亲跑的检查** | ✅ CI 七门（7/7，exit 0，跑后还原 `ci/out`）· checker 全量 9/9 PASS · SPEC 108 / KIND_LEVEL 12 机械复算 · 5 个字节指纹 sha · 生产树 HEAD + status · 事件流/索引 mtime · G5/G7 接线实况（crontab/grep/ls/grep）· S2 断言复现（5 条基线流全 clean）· db 只读查 run/node/actor 账 |
| **本节点未跑的** | ❌ 三审意见 #3（巡检日志 12:1x vs 11:0x 引文核对）、#4（keepalive 行号核对）——**未复验，按三审原文登记**（§15.1） |
| **本节点未做的** | ❌ 未改任何交付文件（仅本状态账 §11–§17 + `计划/变更日志.md` 一行）；未复跑 correction 链式正反用例（依 node 32576/32665 结论）；未复跑闸 2 注入演练（未做）；未换装二进制；未动 `tools/`；未动生产树 |
| **本循环整体未跑（属 T0 窗口）** | 金丝雀 5 题 · 换生产位 · tmpfs 迁移 · MES/看板/watchdog 接线 · 只读挂载演练 · 四注入演练 · 三分池冻结 · 假设池建档 · 闸 1 只读挂载实测 · 指纹表实体化 · 归档目录实体化 · T0 静态指纹录制 |
| **未获独立终审的件** | `设计/底座重构施工方案.md` **v2 未经历第二轮红队终审**（脚本只在 rejected 时回撰写员，见 §13.4-②）；其复核由红队·三审承担 |
| **口径债** | RSI `ready=0.13` 无算式（§14.4）；施工方案 v1 的 3 条「轻微」与 4 条阻断的历史意见**原文仍在 node 32615**，未回填进方案正文（方案只留附录 C 摘要对照） |
| **未回填的文档同步** | `计划/变更日志.md` 本循环条目**由本节点追加一行**（记账员）；`设计/可观测建设方案.md` §5 门表（G1–G7 行，本节点亲读 `grep -n "^| G[1-7] "`）已把 **G1 更新为「CI 七门已跑 2026-10-22 全绿」**、G2 更新为「词表 12 类 + correction 已有合成实测」，但该表**只有「项/判据/归属」三列、无逐门状态列**——G2–G7 的实际状态（两 critical kind 零真实样本、G5/G7 仍 0）**未在 §5 体现**；且 **G1 的「上生产位」半边**与**S2 脚本硬伤**两件均未回填进方案 §5/§6（`设计/可观测建设方案.md` mtime **11:20**，早于第二循环的两份文档产出 12:41/12:44）。**留 T0 前统一回填**（本循环授权不含该文档） |

---

**本循环一句话**：第二循环把第一循环留下的 5 条遗留**全部推到可执行或可执行的步骤**（L1/L2/L3 落码，CI 七门被实施员/红队/三审/本节点**四次亲跑全绿**、checker 全量被红队/三审/本节点**三次复跑全绿**；L4 给 T0 四步；L5 维持既成破口登记），产出**底座重构施工方案 v2**（v1 被红队以 4 阻断 + 4 回滚缺陷驳回后逐条实证重写）与**RSI 上线卡口预填**（八闸 0 闭环、ready=0.13、K0–K7 全🔴未开始）；红队·三审判 **confirmed**，只留**一条中等硬伤**——S2 金丝雀指纹脚本断言与盘上 5 条 clean 基线流不符，T0 必假死，**开工前必须先修**（§16 T0-1）。
