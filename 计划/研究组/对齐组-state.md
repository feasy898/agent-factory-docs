# 对齐组（研究组①）· 可续用状态账

> 本文件是**账**，不是报告：每个数字带出处与 as-of，下一轮直接接着往下写即可。
> 记账人：状态记账员（MiniMax-M3.1-Flash-Preview），写作时点 **2026-10-22 09:27 CST**（本节点自测读数 as-of 09:22–09:27）。
> 覆盖工作流：**dwfrun-fc5da704-f07a-4d32-bb1b-daae1991837b**（名：研究组①对齐组·自研追平商业），01:27:36 起，本节点（ask#14 / node 32481）为该轮最后一节点；run 账面 `status=running`、`spent_tokens=58,429,175`（`~/.zcode/cli/db/db.sqlite` 表 `dwf_run`，2026-10-22 09:26 亲查）。
> 方法原文：`.zcode/workflow-drafts/研究组1-对齐组.dwf.ts`（运营者钦定：功能对齐→轨迹分析找设计差异→纳入改进→5 题快测看差距→差距≤1-2pp 才扩测→直至 D1-D3 旧题全量→再扩 glm5.3f/step5；红队一律 step-5）。
> 授权来源：`计划/变更日志.md:75`（2026-10-22 01:2x 厂长条：fix3 路线终审落地，启动对齐/调优/可观测/资源管理四组研究工作流，红队审查一律 step-5）。

---

## 0. 账本元信息

| 项 | 值 | 出处 |
|---|---|---|
| 工作流 run | `dwfrun-fc5da704-f07a-4d32-bb1b-daae1991837b`（`status=running`，`spent_tokens=58,429,175`，`cwd=/home/pan-ding/workspace/agent黑灯工厂`） | `dwf_run` 表（本节点 09:26 亲查） |
| 流程脚本 | `.zcode/workflow-runs/dwfrun-fc5da704-f07a-4d32-bb1b-daae1991837b.mjs`；方法原文 `.zcode/workflow-drafts/研究组1-对齐组.dwf.ts` | 文件本体 |
| 人物线（11 actor） | 差距测绘员(19034,GLM-5.3-Flash) / 红队·差距核数(19055,step-5) / 轨迹分析师·GLM(19077) / 轨迹分析师·MiniMax(19079) / 候选合并员(19089) / 红队·机理归因(19095,step-5) / 改进实施员(19100) / 快测执行员(19101) / 红队·终审(19187,step-5) / 状态记账员(19193,本节点) | `dwf_actor` 表 |
| 节点账（17 节点） | ask#1=32115 / ask#2=32135 / ask#4=32163 / ask#5=32164 / ask#6=32179 / ask#7×5=32187,32201,32211,32221,32236 / ask#8×2=32241,32359 / ask#9×2=32267,32371 / ask#10×2=32271,32381 / ask#11×2=32354,32465 / ask#13=32472 / **ask#14=32481（本节点，running）** | `dwf_node` 表（按 `time_created` 排序） |
| **未生成的 ask** | **ask#3**（差距画像被驳回后的重算位，本轮 gapCheck=confirmed 未触发）、**ask#12**（脚本无此位）、ask#10 探针后**无 ask#12 复核位** | 同上；脚本 `研究组1-对齐组.dwf.ts:96-101`（gap 重算分支）与节点表逐条比对 |
| 本组产出物 | 分支 `fix4-align-r1`(c9ae50a) / `fix4-align-r2`(936fa48)；二进制 `/home/pan-ding/afbuild-align-r1/af-bench-fix4-align-r1`、`/home/pan-ding/afbuild-align-r2/af-bench-fix4-align-r2`；探针结果 `/tmp/align-probe-r1/results.jsonl`(5 行)、`/tmp/align-probe-r2/results.jsonl`(5 行) | `git -C af log`；`sha256sum`（本节点亲跑，见 §0.2） |
| 红线（全程未越） | gov 生产面零触碰；`/tmp/bench-*`、`/tmp/truth-*` 只读；af 生产工作树 **未动**（HEAD 仍 `94cd1923c34842983049bce5f97b3dcb6c7c348b` = guardrail-fix2，仅 5 个既有未跟踪 `poc/` 目录）；产物二进制换新名、未覆盖 `af/target/debug/af-bench`（mtime 仍 Oct 21 18:16） | 本节点 09:23 亲跑 `git -C af rev-parse HEAD` / `status --porcelain` / `ls -la af/target/debug/af-bench`（见 §0.2） |
| **在飞进程（下一轮必带 as-of）** | `af-bench` PID **3890229**（step-5 臂，out=`/tmp/bench-fix1-d1-step5`）与 PID **3890231**（m31f 臂，out=`/tmp/bench-fix1-d1-m31f`），04:03:48 起跑、09:23 时仍存活（ELAPSED 5h22m）→ **`/tmp/bench-fix1-d1-m31f/results.jsonl` 仍在被追加**（本节点读数 74 行、mtime 08:56:21） | `ps -o pid,lstart,etime -p 3890229,3890231`（本节点亲跑） |
| 官方臂派发器 | `/tmp/mcode-dispatch/heartbeat` = **2026-10-22 04:25:39**（已停跳）；但 mcode d1 文件 mtime 02:55:45、d2 04:25:39、d3 01:39:11 → **mcode 侧数据在 01:32 快照之后被重写过**（见 §1.2） | `cat /tmp/mcode-dispatch/heartbeat`；`stat`（本节点亲跑） |

### 0.1 记账员本节点自测（2026-10-22 09:22–09:27，全部本节点亲跑）

| 自测项 | 命令 | 输出 | 判读 |
|---|---|---|---|
| **当前盘面重算差距主表** | `python3` 遍历 `/tmp/truth-rejudge/bench-fix1-d{1,2,3}-m31f/results.jsonl`（清洁、任务级取末 attempt）+ `/tmp/bench-fix1-d{1,2,3}-m31f/results.jsonl`（arm 末条非 null 兜底）+ `/tmp/bench-official-mcode-d{1,2,3}-m31f/results.jsonl`（status∈{completed,judge_error}） | **D1 n=53 af=40 mcode=51 gap=20.75pp；D2 n=38 af=20 mcode=36 gap=42.11pp；D3 n=20 af=7 mcode=19 gap=60.00pp；合计 n=111 af=67 mcode=106 gap=35.14pp** | **与终审 node 32472 的重算逐位相同**（终审的 20.75/42.11/60.00 成立） |
| **01:32 快照重算** | `python3` 读 `/tmp/pairing-state.pkl`（`TIER/af_val/af_src/mc`），同口径重算 | **d1 n=29 af=20 mcode=27 gap=24.14；d2 n=24 af=12 mcode=23 gap=45.83；d3 n=19 af=7 mcode=18 gap=57.89** | **与 ask#1 差距画像逐位相同** → 测绘员的数字**不是编造**，它对应 `pairing-state.pkl` 这一 01:32 快照；但它把快照当成当前盘面呈现，**呈现口径有罪**（终审 issue 1 成立） |
| 快照候选池 | 同上 pkl：`mcode=T & af=F` | **d1=8、d2=11、d3=11，合计 30**；d1 的 8 题中 3 题为 arm 回退（astropy-14096 / matplotlib-20826 / pytest-10081） | 复现 ask#1 与终审两处「30 候选」的说法 |
| 未探候选数 | 同上 pkl，扣掉已探 5 题 | **25 题未探**（d1 3 + d2 11 + d3 11） | **终审 issue「无剩余候选」是假的**——脚本默认 expandNote 的「或无剩余候选」半句必须删（终审 issue 6 成立） |
| 当前盘面候选池 | 同当前盘面口径重算 `mcode=T & af=F` | D1=12 / D2=16 / D3=12，**合计 40**，扣已探 5 → **35 题未探** | 当前盘面候选比快照多，因 mcode 重写把更多题从「未判」变「判过」 |
| mcode 侧「全 prepare_failed 题」 | `python3` 按 status 分组三档 mcode results.jsonl | d1 行 95（completed 59 / judge_error 1 / prepare_failed 35）、d2 行 87（40/0/47）、d3 行 39（20/0/19）；**三档 `all_prepare_failed_tasks` 均为 0** | 终审「mcode 全 prepare_failed 题由 24 降为 0」**成立**（本节点复现） |
| af arm 无值题 | 同上按 task 聚合 arm | d1 行 74（全 None 任务 9）、d2 行 57（3）、d3 行 20（0）；当前盘面 mcode 已判而 af 无值 = **9** | 终审「af 无值题由 24 降为 9」**成立** |
| af arm 终态 | 同上 status 统计 | 151 行：max_turns **58**（turns 全 = 60）、completed 43、setup_failed 30、tool_free_limit 10、run_failed 10 | 终审「max_turns 58 行且 turns 全为 60」**成立** |
| 配对集内反向不对称案 | 同当前盘面口径 | **恰 1 题**：`matplotlib__matplotlib-13989`（af 清洁判 reward=True；mcode d1 status=judge_error、reward=None、note `judge.json unreadable...rc=1`） | 终审 issue 4「(af=T,mcode 非过)=0」在 null=非过口径下**不成立**，须披露此 1 例 |
| 探针 r1 结果 | `python3` 逐行解析 `/tmp/align-probe-r1/results.jsonl` | 5 行全部 `judge_mode=clean`：`13033 T completed 40轮 870600ms` / `13236 F completed 93轮 1516014ms` / `20859 T completed 67轮 1567467ms` / `4970 F completed 20轮 116929ms` / `10356 F **wall_timeout** 34轮 1807633ms gate=test_edit` | af_pass=**2**、mcode_pass=**5**、judged_rows=5、clean=true —— 与 ask#10 报告逐项属实 |
| 探针 r2 结果 | 同上解析 `/tmp/align-probe-r2/results.jsonl` | 5 行全部 clean：`13033 F completed 27轮 242030ms` / `13236 T completed 147轮 2288534ms` / `20859 F completed 47轮 858127ms` / `4970 T completed 62轮 462714ms` / `10356 F completed 116轮 4997169ms http_retries=2 gate=test_edit` | af_pass=**2**、mcode_pass=**5** —— 与 ask#10 报告逐项属实 |
| **两轮题目级翻转** | 上两表对照 | 5 题中 **4 题在两轮间翻转**（13033 T→F、13236 F→T、20859 T→F、4970 F→T），仅 10356 恒 F | **「af_pass=2」不是稳定值**；「2 vs 5 未追平」的扩测门槛在 n=5、题目级翻转下统计脆弱（终审 issue 5 成立） |
| 探针 r1 结果的 run_dir 指向 | `python3` 打印 r1 每行 `run_dir` | 13033 → `/tmp/align-probe-r1-r2/runs/...`、20859 → `/tmp/align-probe-r1-r4/runs/...`、其余 3 题在 `/tmp/align-probe-r1/runs/` | **r1 的 results.jsonl 是 r1/r2/r4 三批合并产物**；`/tmp/align-probe-r1/runs/` 只有 3 个目录 |
| r1 基建损耗 | `cat /tmp/align-probe-r1.log` | `[1/5] 13033 SETUP_FAILED`、`[2/5] 13236 SETUP_FAILED`、`[3/5] 20859 SETUP_FAILED`、`[4/5] 4970 RUN_FAILED`、`[5/5] 10356 SETUP_FAILED`、末行 `af-bench 完成: 5 题, resolved 0, infra 5` | 首批 **0/5 全灭于基建**（swebench eval 镜像本地缺失） |
| r1 重跑目录 | `cat /tmp/align-probe-r1-r{2,3,4}/results.jsonl` | r2：13033 **T**、20859 setup_failed（note `Unable to find image 'swebench/sweb.eval.x86_64.matplotlib_1776_matplotlib-20859:latest' locally`）；r3：20859 setup_failed（同因）；r4：20859 **T** | 约 **12 次 agent 尝试**才换出 5 个可判 run（node 32354 记述与本节点亲读一致） |
| **r1 负反馈通道**（终审 issue 2 复核） | `python3` 扫 r1 五个判分行 `run_dir/normal.jsonl` 全部 `kind=harness.tool` 事件 | **tool 事件 424 条，is_error=true = 0 条** | 「r1(v4) 无负反馈」在 r1 **全部 5 个判分行**上成立（不止 base 目录那 3 个） |
| **r2 负反馈通道** | 同上扫 r2 五行 | **tool 事件 558 条，is_error=true = 21 条**（`exit:1` × **19**、`exit:124` × **2**）；逐 run：13033 1/40、13236 9/194、20859 3/87、4970 5/73、10356 3/164 | **终审 issue 2 的「14 次（exit:1 ×12、exit:124 ×2）」两个数都不对**（应为 21 / 19+2）；r2 探针复核 node 32465 的「21/558」**正确** |
| r1 轮次/墙钟提醒触发 | `python3` 扫 r1 `harness.db` 的 `transcript_json` | 「Time budget」：13236 1 次、20859 1 次、10356 1 次；「FINAL time warning」：10356 1 次；「turn budget」每 run 1 次 | r1 墙钟提醒**确实注入**（node 32354 的 13236 gentle×1 属实） |
| r2 空响应注记触发 | 同上扫 r2 transcript | 「produced no output」：13033 3、13236 6、20859 1、4970 5、10356 8；**「Network access is unavailable」0 次** | 离线护栏本批**零触发**（node 32465 同结论）；空输出注记为良性高频 |
| 探针 run 的生效策略 | `sqlite3` 读 `harness.db` 的 `run_row.spec_json` | r1：`max_turns=250`、`wall_timeout_secs=1800`、stop=`{completion_signals:['TASK_COMPLETE'], tool_free_turn_limit:3}`；r2：`max_turns=250`、**无 wall_timeout** | 证实 r1/r2 是**两条 divergent 分支**（r2 不含 r1 墙钟），r1/v4、r2/v5 |
| 探针终态 | `sqlite3` 读 `run_row.terminal_json` | r1 10356 = `{"kind":"wall_timeout","elapsed_secs":1806}`；其余 = completed/TASK_COMPLETE；r2 全部 completed | **两轮均无指纹刹车 `stopped` 终态** → 刹车收益证据为零（node 32267/32465 同结论） |
| mcode 对照 | `python3` 读 5 题 `judge.json` | 13033 f2p 1/0、13236 2/0、20859 1/0、4970 1/0、10356 1/0，**全部 resolved=true** | mcode_pass=5 成立 |
| fix1 同题基线 | `python3` 读 arm + 清洁判 | 5 题 fix1 全 F：13033 completed@8、其余 4 题 max_turns@60 | 探针相对 fix1 基线（0/5）为 **净 +2**（两轮各自） |
| fix2 A/B 对照（13236） | `python3` 读 `/tmp/bench-fix2-ab-m31f/results.jsonl` | 13236 = completed **169 轮 / 3154718ms / reward=True** | 与 r1 的 completed@93/**1516s**/F 构成同题对照（node 32354 记述属实） |
| 现树源码引证 | `grep -n` on `af/` | `spec.rs:144 pub max_turns: u32`；`run.rs:419 if live.row.turn_index >= max_turns`；`af-stop/src/lib.rs:65 ToolOk { tool: String }`（现树**无 fingerprint 字段**）、`:250 pub fn feed`、`:259 Event::ToolError`；`af-bench/src/main.rs:748 max_turns: 250`、`:787 spend_cap_cents: 300`、`:558` 已含「NO usable internet access」条款；`af-bench/src/swev.rs:127 let is_test = p.contains("test")` | 终审 issue 5 的源码依据逐条复核成立（含「护栏文案已在现树」「60 轮上限早已提为 250」） |
| 分支与产物 | `git -C af log/diff --stat`；`sha256sum` | r1 `c9ae50a` 9 文件 +425/-21；二进制 sha256 `aeeb35fe…`；r2 `936fa48` 4 文件 +251/-21；二进制 sha256 `4bf41006…` | 两条分支均基于 `main=f373113`，**互不包含对方** |
| 生产工作树未动 | `git -C af rev-parse HEAD`；`git -C af status --porcelain`；`git -C af worktree list` | HEAD `94cd1923…`（guardrail-fix2）；仅 5 个未跟踪 `poc/` 目录；worktree：生产树 + `/home/pan-ding/workspace/af-wt-align-r1` + `/tmp/af-wt-align-r2` + `/tmp/af-wt-obs` | 生产面未动（纪律守住） |
| **未跑**（本节点明确不做） | 未跑 cargo build/test（由红队在其节点自建 target 复验）、未跑任何判分、未跑任何探针题 | — | 本账中「构建/单测全绿」等结论**只署红队节点**，不署记账员 |

---

## 1. 一屏摘要（下一轮先读这段）

| 环节 | 结论 | 关键数字 | 出处 |
|---|---|---|---|
| 基线差距画像 | **数字可复现，但呈现口径有罪** | 快照（01:32 pkl）：D1 24.14pp / D2 45.83pp / D3 57.89pp（n=72）；**当前盘面（09:2x）：D1 20.75pp / D2 42.11pp / D3 60.00pp（n=111，合计 35.14pp）** | ask#1；本节点 §0.1 双向重算；终审 node 32472 |
| 差距画像红队核数 | **confirmed**（1 条实质瑕疵：未配对分解 (b) 少 1 题；1 条重要 caveat：源数据被在飞进程追加，画像为**时点快照**） | 快照重建逐位复现 42/45、31/32、18/19、91/96=94.8% | node 32135（ask#2） |
| 双模型轨迹分析 | GLM 5 条 + MiniMax 5 条 → 合并去重 **5 条**候选 | 5 | node 32163/32164/32179 |
| 候选红队逐条审查 | **5 条：confirmed 3 / rejected 2** | 候选1 confirmed（附 6 条限定）、候选2 **rejected**、候选3 confirmed（附 5 条限定）、候选4 confirmed（附 5 条限定）、候选5 **rejected** | node 32187/32201/32211/32221/32236 |
| 进入实现的候选 | **3 条**（候选1、3、4） | MAX_ROUNDS=2 → 只做了 2 轮 | 脚本 `for round=1..MAX_ROUNDS` + `vetted.shift()` |
| 第 1 轮实现（候选1：墙钟对齐 + 指纹刹车） | 分支 `fix4-align-r1`(c9ae50a)，scaffold **v4** | 9 文件 +425/-21；二进制 `af-bench-fix4-align-r1`（sha256 `aeeb35fe…`） | node 32241（ask#8） |
| 第 1 轮实现红队审查 | **confirmed**（附 6 条限定，最大一条：刹车改的是**共享内核**，TB/InjecAgent 口径也会动，摘要只说「墙钟不动」） | 6 | node 32267（ask#9） |
| 第 1 轮探针 | **af 2/5 vs mcode 5/5，未追平** | 基建先灭 0/5（镜像缺失），约 12 次尝试换 5 个可判 run | node 32271 + node 32354 |
| 第 2 轮实现（候选3：失败负反馈 + 离线三通道声明） | 分支 `fix4-align-r2`(936fa48)，scaffold **v5** | 4 文件 +251/-21；二进制 `af-bench-fix4-align-r2`（sha256 `4bf41006…`） | node 32359（ask#8 ord2） |
| 第 2 轮实现红队审查 | **confirmed**（附 6 条限定，最大一条：is_error 只在 AnthropicMessages 协议上线，**step-5 臂走 OpenAI 路径不生效**） | 6 | node 32371（ask#9 ord2） |
| 第 2 轮探针 | **af 2/5 vs mcode 5/5，未追平** | 5/5 一次跑完（基建干净）；题目级与 r1 交叉翻转 4/5 | node 32381 + node 32465 |
| 扩测判定 | **未达门槛 → 不扩测** | 脚本默认 expandNote 生效；**但「或无剩余候选」半句为假**（25 题未探） | 脚本 `expandNote` 逻辑；终审 issue 6 |
| 红队终审 | **rejected**（未参与环节的 step-5） | **9 条 issue**，给出「达到 confirmed 所需修正」6 项 | node 32472（ask#13） |
| 本节点 | 记账 | — | node 32481 |

**本轮一句话**：材料链完整（差距画像→双模型轨迹→候选红队→两轮实现+两轮探针→终审），**但终审判 rejected**——主表数字是 **01:32 旧快照**被当成当前盘面呈现（当前盘面已重算为 20.75/42.11/60.00pp、n=111），「无剩余候选」是假的（**25 题未探**），两轮探针的「2/5」掩盖了 **5 题中 4 题题目级翻转**；此外终审自身的两条数字（r2 `is_error` 14 次 / r1 238 次 bash）经本节点复核**是错的**（应为 21 次 / 424 次事件）。

---

## 2. 差距画像（含命令）

### 2.1 数据路径与口径（测绘员 node 32115 的口径，本节点已复算）

| 侧 | 路径 | 口径 |
|---|---|---|
| af 清洁判 | `/tmp/truth-rejudge/bench-fix1-d{1,2,3}-m31f/results.jsonl` | 44/24/21 行，全 `judge_mode=clean`；任务级取**末 attempt**（`run_dir` 尾 `-a<N>` 排序） |
| af 回退（arm 原判） | `/tmp/bench-fix1-d{1,2,3}-m31f/results.jsonl` | 无清洁行的题取 arm 末条非 null 行（本轮 14 题进入配对集） |
| mcode 对照 | `/tmp/bench-official-mcode-d{1,2,3}-m31f/results.jsonl` | 有效判分行 = `status ∈ {completed, judge_error}`；`prepare_failed` 无效；`reward=null` 计**非过** |
| 档位 | 任务包目录 `d1/d2/d3`（`/tmp/swev-s1/` 120 包） | 三方 tier 映射零冲突（node 32135 独立复现） |
| 配对定义 | 同 `task_id` 双方均有有效判分行 | 快照 n=72；当前盘面 n=111 |
| gap 公式 | `100 × (mcode_pass − af_pass) / n_paired` | — |

**本节点复算命令（可原样重跑）**：

```bash
# 当前盘面主表（本节点亲跑，输出 D1 20.75 / D2 42.11 / D3 60.00 / 合计 n=111 af=67 mcode=106 gap=35.14）
python3 - <<'EOF'
import json, re
def load(p): return [json.loads(l) for l in open(p) if l.strip()]
def af_clean(d):
    best={}
    for r in load(f'/tmp/truth-rejudge/bench-fix1-d{d}-m31f/results.jsonl'):
        if r.get('judge_mode')!='clean': continue
        m=re.search(r'-a(\d+)$', r.get('run_dir') or ''); a=int(m.group(1)) if m else 0
        t=r['task_id']
        if t not in best or a>best[t][0]: best[t]=(a,bool(r.get('reward')))
    return {t:v[1] for t,v in best.items()}
def af_arm(d):
    last={}
    for r in load(f'/tmp/bench-fix1-d{d}-m31f/results.jsonl'):
        if r.get('reward') is None: continue
        last[r['task_id']]=bool(r['reward'])
    return last
def mcode(d):
    out={}
    for r in load(f'/tmp/bench-official-mcode-d{d}-m31f/results.jsonl'):
        if r.get('status') in ('completed','judge_error'):
            out[r['task_id']]=(r.get('reward') is True, r.get('status'), r.get('reward'))
    return out
T=[0,0,0]
for d in (1,2,3):
    cl=af_clean(d); arm=af_arm(d); mc=mcode(d)
    n=ap=mp=0
    for t,v in mc.items():
        av = cl[t] if t in cl else arm.get(t)
        if av is None: continue
        n+=1; ap+= 1 if av else 0; mp+= 1 if v[0] else 0
    print(f'D{d}: paired={n} af={ap} mcode={mp} gap_pp={round(100*(mp-ap)/n,2)}')
    T[0]+=n; T[1]+=ap; T[2]+=mp
print('TOTAL n=%d af=%d mcode=%d gap=%.2f'%(T[0],T[1],T[2],100*(T[2]-T[1])/T[0]))
EOF

# 01:32 快照主表（本节点亲跑，输出 d1 29/20/27/24.14、d2 24/12/23/45.83、d3 19/7/18/57.89）
python3 - <<'EOF'
import pickle, collections
d=pickle.load(open('/tmp/pairing-state.pkl','rb'))
TIER=d['TIER']; af_val=d['af_val']; mc=d['mc']
tiers=collections.defaultdict(list)
for t,v in TIER.items(): tiers[v].append(t)
for tier in ('d1','d2','d3'):
    n=ap=mp=0
    for t in tiers[tier]:
        av=af_val.get(t); m=mc.get(t)
        if av is None or not m.get('reached'): continue
        n+=1; ap+= 1 if av else 0; mp+= 1 if m.get('reward') else 0
    print(f'{tier}: n={n} af={ap} mcode={mp} gap_pp={round(100*(mp-ap)/n,2)}')
EOF
```

### 2.2 两个口径必须并列写进下一轮（终审 issue 1 的正解）

| 口径 | D1 | D2 | D3 | 合计 | 快照时点 | 何时失效 |
|---|---|---|---|---|---|---|
| **A. 01:32 快照**（`/tmp/pairing-state.pkl`，node 32115 报出、node 32135 与终审均能逐位复现） | n=29 af=20 mc=27 **24.14pp** | n=24 af=12 mc=23 **45.83pp** | n=19 af=7 mc=18 **57.89pp** | n=72 | pkl mtime 2026-10-22 01:32 | mcode d1/d2/d3（02:55/04:25/01:39）与 af arm d1/d2（08:56/07:44）**在其后被原地重写** |
| **B. 当前盘面**（本节点 09:2x 亲算，与终审逐位一致） | n=53 af=40 mc=51 **20.75pp** | n=38 af=20 mc=36 **42.11pp** | n=20 af=7 mc=19 **60.00pp** | n=111 af=67 mc=106 **35.14pp** | 2026-10-22 09:2x | af arm d1 仍被在飞 af-bench（PID 3890231）追加 → **仍会漂移，任何引用必须带 as-of** |

- 漂移事实（终审 issue 1 证据，本节点复核）：mcode d1 现 95 行 / d2 87 / d3 39（旧快照 80/79/38）；arm d1 现 74 行 / d2 57（旧 64/48）；mcode 侧「全 prepare_failed 题」由 24 降为 **0**，af 侧「无值题」由 24 降为 **9**。
- **口径纪律（写进下一轮）**：引用主表时必须写「**快照 A**」还是「**盘面 B**」+ as-of；两者不可混用，**不可把 A 当作当前事实陈述**。

### 2.3 未配对分解（订正终审 issue 3）

- (a) mcode 侧全 `prepare_failed` 的题：快照 **24**（其中 af=T 19 题）→ 当前盘面 **0**。
- (b) af 无值（`reward=None`）而 mcode 判过：快照 **24**（23T + 1F `sphinx-doc__sphinx-10435`）→ 当前盘面 **9**。测绘员原报 23（22T+1F）**少 1**（node 32135 与终审一致指出）→ **下一轮一律写 24（23T+1F）**（快照口径）或 9（盘面口径）。
- 敏感性不对称案：配对集内 `af=T & mcode 非过` 在快照口径为 0，在 null=非过口径下 **1 题**（`matplotlib__matplotlib-13989`，mcode d1 `judge_error`、reward=None）→ 下一轮须披露。

### 2.4 探针集（5 题）与基线

- 探针集（ask#1 选定，node 32135 逐行复核）：`astropy__astropy-13033`、`astropy__astropy-13236`、`matplotlib__matplotlib-20859`、`pylint-dev__pylint-4970`、`pytest-dev__pytest-10356`（全部 D1，全部 mcode=completed+T、af=clean 判 F）。
- fix1 同题基线：**5 题全 F**（13033 completed@8，其余 4 题 max_turns@60）——探针的「2/5」是相对 0/5 的 **净 +2**。
- mcode 同题对照：5 题 `judge.json` 全 `resolved=true`（f2p 1/2/1/1/1）→ **mcode_pass=5 是硬对照，不是估计**。
- 探针集之外的候选池：快照 30（d1 8 / d2 11 / d3 11），当前盘面 40（d1 12 / d2 16 / d3 12）。

---

## 3. 候选红队结论逐条（5 条，一条不落）

### 候选 1 —— 硬 60 次调用上限 + 唯一刹车只认 ToolError（GLM+MiniMax 互证）
**红队裁定：confirmed（附 6 条限定）** — node 32187（ask#7 ord1）

- 成立的核心因果：**60 次调用硬上限 → 成批 max_turns → 清洁判 F 的头号来源**。148 个 fix1 m31f `harness.db` 终态 = max_turns 76 / completed 42 / tool_free_limit 25；89 行清洁判中 27 行 F，终态 max_turns 19 / completed 8（**19/27 = 最大单一桶**）；同模型同题 mcode 以 `os_timeout=1800s` 跑完全流程而 af 被切半路。
- 限定 ①「刹车休眠致打转」**子论断被否**：9583 条 tool 记录 `is_error=true` 共 **0** 条（代码事实成立），但全 bench ≈9500 条命令**精确重复≈0**（重复≥3 次仅 3–4 条），模型是**语义层换方案**（django-13121 死前 "I'm overcomplicating this... take a completely different approach"），指纹级刹车抓不到；且 `Fingerprint={tool,error_code}` 而 `Event::ToolOk` 只带 tool 名（现树 `af-stop/src/lib.rs:65`），天真把 ToolOk 计入连击会在第 3 次成功 bash 就 Stop → **收益≈0、风险>0**。
- 限定 ② 归因档案错位：19/27 属 **m31f 线**；glm-cp 线实为 47 F / 30 max_turns。
- 限定 ③ 「agent.diff 缺失关键改动」不精确：19 个 max_turns-F 的 diff **全部非空**（580–11217 B），准确说法是「补丁存在但关键改动未完成/不正确」。
- 限定 ④ 非全部差距来源：27 个清洁 F 中 8 个是 completed；配对 21 题 af=F&mcode=T 中仅 13 题死于 max_turns；**反向也有 12 题 af=T&mcode=F（D1 5 / D2 7）——harness 差异是双向的**。
- 限定 ⑤ 候选引的 **D2 45.8pp 不可复现**（配对口径 D2 两边都是 16/22=72.7%，0pp）；D3 57.9pp 可复现。墙钟中位 D1 1110s / D3 925s（候选写 1112/992），结论（远小于 1800s）不变。
- 限定 ⑥ **提额部分在现树已落地**：`af-bench/src/main.rs:748 max_turns: 250`、`:787 spend_cap_cents: 300`（fix2 已由 60→250、$1→$3，并加轮次预算提醒/提交式完成协议/重复命令警告/反考古护栏）。fix2 A/B：13236 fix1 max_turns@60 F → fix2 completed@169 T（支持因果），但 seaborn-3069 T→F **反向翻转**，且 fix2 墙钟已达 3424s > mcode 1800s → **超额运行成为新待管项**。
- **下一轮可用结论**：候选的**剩余**可执行价值只有「墙钟上限回撤」这一新决策；「刹车重设计」不建议。

### 候选 2 —— 完成判定 = 模型自证 TASK_COMPLETE 且无验证闸门（fix1 更按叙述文本子串触发）
**红队裁定：rejected** — node 32201（ask#7 ord2）

- 代码事实属实（fix1 `run.rs:543` + `:871` 用 `text.contains` 子串匹配；现树 `:595-601` 已改为工具输出首行精确匹配，提示词 `main.rs:565-566` 同步改为 "PRINTS the token TASK_COMPLETE as its FIRST output line"）。
- 驳回理由 ① **实际命中 1/148 运行（0.7%）**：42 个 completed 逐条扫 transcript，41 例信号词在末条消息结尾干净收尾，**只有 astropy-13033-a1 一例**被掐断（信号词后仍有 "Wait — I shouldn't stop before confirming the tests..." 且还有 1 个工具调用已执行）。
- 驳回理由 ② 13033 的 F 主要由**错误格式补丁**造成（`', '.join` 产出 "'time', 'a'" 式，而隐藏 F2P 要求列表字面量 "['time', 'a']"；P2P `test_empty_initialization_invalid` 真被打坏），错误格式在掐断前已定型，**不算掐断的因果**。
- 驳回理由 ③ **「无验证闸门」不是 af 相对商业线的设计差异，作为改进方向有害**：判分由同一判分核 `tools/swev-judge.py` 裁定（completed 只是 run 状态、reward 仍 False）；mcode 的「跑全量+基线对照」是**模型行为**而非 harness 门；若加「最后一次测试为绿」闸门，mcode 自己日志里的 astropy 全套 "1821 passed, 29 failed"（29 个失败为环境预存）这类题会被全部堵死。
- 驳回理由 ④ 8 例 completed-but-F 中 7 例末条消息即在信号词处干净结束 → 属「改错/近 miss」**模型行为类**失败。
- 驳回理由 ⑤ **纳入价值≈0**：该 bug 已在 fix2 修复；剩余风险方向相反（fix2 语义下若模型只叙述不 echo 令牌，运行会不收尾直至 tool_free/max_turns）→ 登记为**后续观察项**，不作改进候选。

### 候选 3 —— 离线零声明（GLM）× 命令失败被报成 exit=0 成功（MiniMax）
**红队裁定：confirmed（附 5 条限定）** — node 32211（ask#7 ord3）

- 成立：fix1 `tb.rs` 用 `format!("exit={}\\n{text}", …)`（**首行 + 字面 `\n` + 整行 rc**），管道掩蔽 rc（`python -m pytest … 2>&1 | tail -20` 用法错误未跑起来却 exit=0；`pip download … | tail` 同）；现树 `tb.rs:186-222` 仍只回 String，退出码降级为末行装饰文本。
- 限定 ① 候选说「追加末行」**不准确**——那是现树 fix2 形态，fix1 是**首行**；真正机制是「整行 rc + 管道掩蔽 + 首行装饰」。
- 限定 ② 「既无负反馈修正」**被夸大**：失败侧 76 次网络探测中 29 次 exit=0 但体含 ConnectTimeout 等错误文本，模型**看得到**；缺的是（a）事前环境声明、（b）结构化错误通道。预算占比有限：失败侧 23 run 的 1819 条命令中网络探测 76（4.2%）+ pip cache 90（4.9%）≈9%，**主要终结因素仍是 60 轮上限**。
- 限定 ③ **提示词半边已在现树落地**（fix2 `SWEV_INSTANCE_PROTOCOL` 已写 "The container has NO usable internet access… Never retry a failed download"）→ 纳入成本 0。
- 限定 ④ is_error 半边**不可朴素实现**（回归风险已量化）：`af-stop` 指纹连击 limit=3 且 bash 失败时 error_code 为空 → 所有 bash 错误共享同一指纹；实测 fix1 m31f 有 **29 个 run 存在 ≥3 次连续非零退出**，其中有清洁判的 25 个里 **19 个判 T**（astropy-13579、django-10880、xarray-4075、requests-1142 等）→ 朴素实现会**歼灭约 19 个通过用例**；`normal_error_threshold=5` 更早触发。
- 限定 ⑤ 「空 stdout 判别」不稳（exit=0 且静默是重定向/`true`/`touch` 的常态）。
- **本轮据此实施的正是候选 3 的收窄版**（见 §4.2），且实施被限定为「**逐字重复**的失败连击」而非「非零 rc 即计」——**这条限定是红队 ④ 的直接产物**。

### 候选 4 —— 验证经济学错位：af 强制「跑相关测试」但隐藏 F2P 不可达、只能 in-place stash
**红队裁定：confirmed（附 5 条限定）** — node 32221（ask#7 ord4）

- 最锋利实证（20859）：af 探针跑 `l = subfig.legend(); print(l, l.figure is fig)`，而其补丁 `agent.diff:17` 正是把 `self.set_figure(parent)` 改成 `self.set_figure(parent.figure)` → 探针验证的是**错误不变量**（返回 True 给假信心），隐藏断言是 `leg.figure is subfig`（`/tmp/swev-s1/matplotlib__matplotlib-20859.json` test_patch 末行）必 False；mcode 同题日志直接拿上游回归测试当验收点（"Upstream regression test (leg.figure is subfig) | ❌ TypeError | ✅ pass"）。
- 10356：GLM 的「editish=0」是分类器假象（实为 `python - <<'EOF'` Heredoc 改写，真实图景是**测试主导** 43/67）；失败核心是 diff 实现了 MRO 遍历但**没有 `consider_mro` 关键字**（diff 中出现 0 次），隐藏测试调 `get_unpacked_marks(C, consider_mro=False)` → TypeError。
- 4970：隐藏 F2P `test_set_duplicate_lines_to_zero` 是 test_patch **新增**（base 仓库没有）；af 全 run 只有 2 条 `sed -n` **只读**命令碰过该文件、从未执行过任何 similar 测试 → 「读过即将插入的那一段却从未执行」。
- 限定 ① 「af 只能 in-place stash」**言过其实**：harness 不禁 `git worktree add` 基线对照（fix2 反考古护栏只挡翻上游修复，不挡基线对照）——是模型选择而非 harness 限制；但 **af 提示词从未建议基线对照**，mcode 提示词显式封顶自验（`tools/mcode-dispatch.py:202` "不要在自验上耗尽时间"）。
- 限定 ② MiniMax 「唯一 0 字节 agent.diff 是 astropy-14182」**不复现**（fix1 m31f truth-manifest 89 条中 0 字节 0 条，14182 实为 1392B）。
- 限定 ③ 补丁体型差复证：af agent.diff 中位 1537B(n=89) vs mcode patch.diff 中位 8137B(n=109)；同题配对 78 对 1550B vs 7902B。
- 限定 ④ 10356 的 `gate=test_edit` 是**子串误报**（`swev.rs:127 p.contains("test")` 命中 `_pytest`）——**fix2 既有缺陷，非本轮引入**，且使任务包里全部 10 个 pytest 题的正当修复路径 `src/_pytest/**` 被误标。
- 限定 ⑤ 本候选**尚未进现树**（fix2 `SWEV_INSTANCE_PROTOCOL` 第 4 条仍无封顶、无 pristine 基线差分协议）→ **纳入成本低、回归风险可控**。
- **⚠ 本轮状态：confirmed 但未实施**（MAX_ROUNDS=2 用尽，候选 4 仍在 vetted 队列尾）→ **下一循环的第一个候选**。

### 候选 5 —— 任务理解辅助缺位：仓库 git 对象自带上游补丁，af 零槽位 prompt 不引导
**红队裁定：rejected** — node 32236（ask#7 ord5）

- 事实核实（红队做得比候选更多）：泄漏**真实存在**——`/tmp/bench-fix1-d1-m31f/runs/swev-astropy__astropy-13236-mavis-m31f-a2/effects.db` 里 `git fsck --lost-found` → `dangling commit 646909fd…`，`git show --stat 646909f` → `Merge: b8aeddf39 d2e4ca08b | Author: SWE-bench <setup@swebench.com> | WIP`（建镜像时把上游修复并进了对象库）；`git cat-file --batch-all-objects` 33447 commit vs `git rev-list --all` 33437。mcode 侧 `mcode.log:33` 逐字自述补丁与上游 PR #13236 的 merge `034625e982` **byte-equivalent**、first parent 正是本 repo HEAD——不可能凭记忆写出。af 两个 attempt 对该泄漏提交只有 1 次 `git show --stat`、**0 次补丁提取**，最终手写变体 not_resolved。
- 驳回理由 ① **这是基准泄题 exploitation，不是 harness 改进**：测量意图是「从 issue 描述出发修 bug」，取用建镜像残留的 WIP 合并提交属于拿答案。
- 驳回理由 ② **与现树决策直接冲突**：fix2 反考古护栏（`main.rs` `ARCHAEOLOGY_PATTERNS` + 注入文案 "Searching for an upstream fix (git archaeology / full-disk search) is unavailable… the upstream fix is not in this repository…"）正是把「翻上游修复」当浪费压掉（依据 51/148 run 用过 git fsck/lost-found，本轮 m31f 子集复现 51/148）。采纳候选 5 会摧毁 af↔mcode 的比较基础。
- 驳回理由 ③ 「提示词蒸馏差异」**不成立**：mcode dispatch 同样原文透传 problem_statement（`PROMPT_TMPL` 含 `{ps}`），与 af 的 user_message 同源（13033 user_message 6878 B，尾部确为维护者对话噪声）。
- **附带发现（建议单独立项）**：护栏文案「the upstream fix is not in this repository」与对象库里真实存在 WIP 修复提交矛盾——**这是为测量完整性说的白谎**；正当化方式是**建容器时清除不可达对象或明令禁用**，而不是教模型利用。→ **登记为独立待办，优先级高于本组其他项**。

### 3.1 候选台账（下一轮直接续用）

| # | 候选（简称） | 红队裁定 | 是否已实施 | 剩余可执行价值 / 备注 |
|---|---|---|---|---|
| 1 | 60 轮上限 + 刹车只认 ToolError | confirmed（6 限定） | ✅ r1 实施（墙钟 + ToolOk 指纹刹车） | 提额已在现树（250 轮）；刹车历史零命中、收益≈0；**新待管项：fix2 墙钟 3424s > mcode 1800s** |
| 2 | 完成判定子串截断 | **rejected** | ❌（现树已修） | 登记为**观察项**（fix2 语义下模型不 echo 令牌会不收尾） |
| 3 | 离线零声明 × 失败报假成功 | confirmed（5 限定） | ✅ r2 实施（收窄版：逐字重复失败连击 + 三通道离线声明 + 空响应护栏） | 探针上负反馈已上线（21/558 is_error）；离线护栏本批 0 触发 |
| 4 | 验证经济学错位 | confirmed（5 限定） | ❌ **未实施（下一轮首候选）** | 成本低、风险可控；需与反考古护栏划界（只允许 HEAD 旁路） |
| 5 | 任务理解/git 考古 | **rejected** | ❌ | 改为**独立立项**：建容器清除不可达对象（或明令禁用），禁止利用 |

---

## 4. 每轮探针结果

### 4.1 第 1 轮（分支 `fix4-align-r1`，scaffold **v4**）

- **实施内容**（node 32241）：①`Policy.wall_timeout_secs: Option<u64>`（serde default 兼容旧规格、`Some(0)` 拒绝）+ `RunStatus::WallTimeout{elapsed_secs}` + 剩 300s/120s 各注入一次墙钟提醒 + af-bench swe-v 设 `Some(1800)`；②`Event::ToolOk` 增 `fingerprint`（入参 FNV-1a64，同指纹连续 3 次成功调用 → `Stop(NoInfluence)`，不计普通错误阈值）。
  - **偏差（已如实披露）**：ask 给的 `/tmp/af-wt-align-r1` 与 `/tmp/afbuild-align-r1` **被 /tmp 磁盘配额挡死**（dd 写 205MB 即 `Disk quota exceeded`，tmpfs 仅余 1.7G，target 需 2.1G+）→ 实际工作树 `/home/pan-ding/workspace/af-wt-align-r1`、target `/home/pan-ding/afbuild-align-r1`，**语义不变**（新分支/新工作树/新 target/产物改名）。
  - 红队独立复验（自有 target `/home/pan-ding/afbuild-rt-r1`）：`cargo build` 40.33s OK；`cargo test -p af-stop -p af-harness -p af-bench` → af-stop lib 33✓ / properties 7✓ / restart 13✓ / af-harness lib 56✓ / af-bench 4✓ / doc 1✓ **全绿**；`cargo fmt --check` 干净；clippy 无新增告警（node 32267）。
  - **红队限定 ①（最重要）**：刹车改的是**共享内核**（af-stop/af-harness 三套件共用），`Event::ToolOk` 带指纹后**对 TB（max_turns=40）与 InjecAgent（max_turns=16、canned stub、tool_free=1）同样生效** → 摘要「TB/InjecAgent 口径不动（None）」**只对墙钟成立**，对刹车不成立；InjecAgent 的桩工具被同参连调 3 次即停，是该套件上真实的新停止路径。
  - **红队限定 ②**：墙钟 1800s 会把「轮次耗尽」变成「时间耗尽」——fix2 代际 33 个有 turns+墙钟的 run 中位 19.4s/轮 → 1800s 内可达中位 93 轮，**15/33 个 run 墙钟超 1800s**（最长 astropy-13398 222 轮/4812s、seaborn-3069 227 轮/4204s）→ 新预算下约 **45% 的 fix2 代际 run 会在 1800s 处被硬切**。
  - **红队限定 ③**：刹车在历史数据上**零命中**（9584 条命令重复实例 9、≥3 连续逐字相同的 run **0**）→ 回归风险≈0，**预期收益也≈0**，不应作为本轮可测收益来源。
  - 红队限定 ④：properties.rs 的 `arb_event/noise_event` 仍只生成 `fingerprint: None` 的 ToolOk（proptest 未覆盖新分支）；摘要把 restart/properties 计数写反（实测 properties 7 / restart 13）。
  - 红队限定 ⑤：`tools/truth-aggregate.py:110` `AB_FAILED_STATUSES={run_failed,setup_failed}` **不含 wall_timeout** → 墙钟终止且无 diff 的 run 会被标成 `clean_pending` 而非 `run_failed_no_diff`（外观问题，判分链不受影响）。

- **探针结果**（`/tmp/align-probe-r1/results.jsonl`，5 行，**全 `judge_mode=clean`**）：

| 题 | reward | status | 轮数 | 墙钟 | gate | f2p / p2p | 备注 |
|---|---|---|---|---|---|---|---|
| astropy-13033 | **T** | completed | 40 | 870.6s | ok | 1/0、20/20 | 相对 fix1（completed@8 F）**翻转成功**；run_dir 指向 `-r2` 批 |
| astropy-13236 | F | completed | 93 | 1516.0s | ok | 0/2、644/0 | **警钟样本**：墙钟 gentle 提醒在 ~1500s 触发 1 次、**16s 后模型即提交**；死前自述选 FutureWarning 式最小修复。对照 fix2-AB 同题 completed@169/**3155s** = T |
| matplotlib-20859 | **T** | completed | 67 | 1567.5s | ok | 1/0、88/88 | 相对 fix1（max_turns@60 F）**翻转成功**；run_dir 指向 `-r4` 批 |
| pylint-4970 | F | completed | 20 | 116.9s | ok | 0/1、17/17 | 117s 内墙钟提醒不可能触发（300s/120s 门槛未到）→ 属 completed-but-**F** 类，与两机制无关；残留 TOTAL lines=62 |
| pytest-10356 | F | **wall_timeout** | 34 | 1807.6s | test_edit | 0/1、79/79 | `terminal_json={"kind":"wall_timeout","elapsed_secs":1806}`；gentle×1 + FINAL×1 提醒各触发但模型拒绝提交；diff 仍缺 `consider_mro`（**与 fix1-a2 同一失败模式**） |

  **af_pass = 2 / mcode_pass = 5，judged_rows=5，clean=true，未追平。**

- **基建损耗（红队点名的「未报喜亦未报忧」）**：首批 5 题**全灭于基建**（`/tmp/align-probe-r1.log`：4×SETUP_FAILED + 1×RUN_FAILED，末行 `resolved 0, infra 5`），根因 = swebench eval 镜像本地缺失（`Unable to find image 'swebench/sweb.eval.x86_64.matplotlib_1776_matplotlib-20859:latest' locally`）；20859 连败 r2/r3 两次到 r4 才成功；合计约 **12 次 agent 尝试**换 5 个可判 run；**最终 results.jsonl 是 r1/r2/r4 三批合并产物**（run_dir 分指三个目录）→ 复现与审计须知。
- **探针红队复核**（node 32354）**confirmed**，附 6 条：基建损耗被完全省略、13236 警钟样本（只报 2 个翻转不报对照 = 选择性陈述）、10356 的 `gate=test_edit` 是 `_pytest` 子串误报、4970 属 completed-but-F 与两机制无关、n=5 无方差估计、刹车零触发无收益证据。
- **本节点复核**：r1 五行 tool 事件 **424 条、is_error=true 0 条**（v4 零负反馈成立）；「Time budget」提醒在 13236/20859/10356 各 1 次、FINAL 在 10356 1 次（墙钟提醒确实注入）。

### 4.2 第 2 轮（分支 `fix4-align-r2`，scaffold **v5**）

- **实施内容**（node 32359）：①`bash_result()`：bash 非零退出升级为 `ToolFailure`（`is_error=true` 经 anthropic `tool_result.is_error` 上线，`output` 字段原文透传），error_code 带命令 FNV-1a64 指纹；止损规则①**只对「逐字重复的失败连击」**收束，不同命令的正常失败互不打断；规则③累计阈值对 bash 常态失败不升级（`normal_error_threshold` 抬至 1000）；②空响应判别（rc=0 + 命中网络探测模式 + 输出 <16 字符 → 前置离线护栏；rc=0 + 完全无输出 → 附无输出注记）；③**离线声明三通道**（system prompt 每轮重发 / bash 工具描述每次请求重发 / instance 模板扩写「空响应=失败」）。
  - 偏差披露：target 目录同样因 /tmp 配额改到 `/home/pan-ding/afbuild-align-r2`；工作树用**稀疏检出**（`--no-checkout` + `sparse-checkout set crates .cargo`）落在 ask 指定的 `/tmp/af-wt-align-r2`（3.5M；全量检出 4.9G 全在 `poc/` 放不下）。
  - 红队独立复验（自有 target `/home/pan-ding/afbuild-rt-r2`）：build OK；`cargo test` → af-bench 10✓ / af-harness 52✓ / af-stop 29✓ / properties 7✓ / restart 13✓ / doc 1✓ **全绿**；fmt 干净；clippy 无新增（node 32371）。
  - **红队限定 ①（最重要）**：**is_error 负反馈只在 AnthropicMessages 上线**——`endpoint.rs` 的 `anthropic_body` 把 `is_error` 写进 tool_result，但 `openai_body` 的 tool 消息只有 `{role,tool_call_id,content}`，**没有错误标记位**；而 `main.rs:409` 的 **step-5 档案正是 OpenaiChatCompletions** → 该臂上 bash 失败仍退化为「内容里带 exit=N」，**与 fix1 无异**。
  - **红队限定 ②**：失败命令不再计 `effect_fresh`（`Err(ToolFailure)` → `GatewayError::ExternalCall`，意图停在 declared 无回执）→ 跨代际比较 effect_fresh 的仪表会漂移，属**测量记账变更**，须在提交信息注明。
  - **红队限定 ③（合流隐患）**：r1 走 v3→**v4**、r2 走 v3→**v5**，**互不含对方**——v5 运行不含 r1 墙钟、v4 运行不含 r2 反馈通道；合并时必须重新对齐 bump，否则按 scaffold 字符串推断机制集合会错。
  - 红队限定 ④：repeat 警告与反考古护栏都在 `bash_result` 之前往输出插文本 → 第 3 次及以后的逐字重复网络探测**拿不到离线护栏**（只剩重复警告）。
  - 红队限定 ⑤：`NETWORK_PROBE_PATTERNS` 用 `command.contains(p)` 全命令子串匹配，理论误伤面（历史 126 次触发全是真探测：curl 99 / pip download 25 / git clone 1 / ping 2）。
  - 红队限定 ⑥：公共 API 变化——`ToolFailure` 去掉 `Eq` derive（仓内无外部消费者）；rc 解析缺失时 `unwrap_or(124)` 静默映射成超时码（实际不可达）。
- **探针结果**（`/tmp/align-probe-r2/results.jsonl`，5 行，**全 clean、scaffold v5、attempts=1**）：

| 题 | reward | status | 轮数 | 墙钟 | http_retries | gate | f2p / p2p | 备注 |
|---|---|---|---|---|---|---|---|---|
| astropy-13033 | F | completed | 27 | 242.0s | 0 | ok | 0/1、20/20 | **相对 r1 回退**（r1 T@40/870.6s） |
| astropy-13236 | **T** | completed | 147 | 2288.5s | 0 | ok | 2/2、644/644 | **相对 r1 翻转成功**；147 轮（无墙钟机制，故未触发） |
| matplotlib-20859 | F | completed | 47 | 858.1s | 0 | ok | 0/1、88/88 | **相对 r1 回退**（r1 T@67/1567.5s） |
| pylint-4970 | **T** | completed | 62 | 462.7s | 0 | ok | 1/1、17/17 | **相对 r1 翻转成功** |
| pytest-10356 | F | completed | 116 | 4997.2s | **2** | test_edit | 0/1、79/79 | **第三代连续全败**；本轮流烧 4997s；diff 仍只改 `src/_pytest/mark/structures.py`、仍无 `consider_mro`（grep=0）→ 同一 API 不匹配失败模式 |

  **af_pass = 2 / mcode_pass = 5，judged_rows=5，clean=true，未追平。**

- **探针红队复核**（node 32465）**confirmed**，附 6 条：报喜不报忧 ①（同样 2/5 但**构成翻转**——r1 的两个通过项在 r2 回退、r2 的两个通过项在 r1 是 F，5 题中 4 题翻转）；② 10356 连续第三代全败 + 本轮流烧 4997s；③ 机制触发清单（轨迹实证：is_error 21/558 上线、离线护栏 0 次、刹车 0 次、墙钟 0 次符合分支设计）；④ 基建面好消息（r2 单批 5/5 跑完，无 setup_failed/run_failed、无重试目录）；⑤ 口径提醒（两轮是 divergent 分支各 5 题单样本，"r1 vs r2 谁更好"的读法**无效**；有效结论只能是「两分支各自 2/5、mcode 5/5、样本内均无对 fix1 基线 0/5 的净回退」）。
- **本节点复核**：r2 五行 tool 事件 **558 条、is_error=true 21 条**（`exit:1`×19、`exit:124`×2），逐 run 1/9/3/5/3 —— 与 node 32465 一致，**与终审的「14 次（12+2）」不符**（见 §6）；「produced no output」注记 3/6/1/5/8；「Network access is unavailable」**0 次**。

### 4.3 两轮汇总（**下一轮必须带这三条限定，否则会重蹈覆辙**）

1. **两轮都是 2/5，但通过的是不同题目**（4/5 题目级翻转）→ **「af_pass=2」不是稳定值**；n=5 单样本、两条 divergent 分支（v4 含墙钟不含反馈通道 / v5 反之），**任何「r1 vs r2 谁更好」的读法无效**。
2. 相对 **fix1 基线 0/5**，两轮各自都是 **净 +2**（r1：13033、20859；r2：13236、4970）——**回退的 13033/20859 只是回到 F 而非更差**。
3. **两轮合计仍落后 mcode 3 题**（mcode 5/5 为硬对照），**探针未追平 → 未达扩测门槛 → 本轮不扩测**（脚本 `aligned = probe.af_pass >= probe.mcode_pass` 恒假）。

---

## 5. 终审意见（红队·终审 node 32472，step-5，未参与本轮任何环节）

**裁定：`rejected`**，共 **9 条 issue**。终审自述：只读、未运行判分/构建、未写任何文件。

### 5.1 逐条意见

| # | 意见 | 性质 | 本节点复核结论 |
|---|---|---|---|
| 1 | **主表不可复现**：按声明路径在当前盘面实跑得 D1 20.75 / D2 42.11 / D3 60.00（总 n=111 af=67 mcode=106 35.14pp），与声明的 29/20/27-24.14、24/12/23-45.83、19/7/18-57.89 **全面不符**；声明数字实际对应 `/tmp/pairing-state.pkl`（mtime 01:32）的旧快照 | **拒绝主因** | **成立**。本节点双向重算：快照口径 24.14/45.83/57.89 逐位复现；当前盘面 20.75/42.11/60.00 逐位复现 → **数字真、呈现口径有罪** |
| 2 | **快照过期未披露 + 虚假排他性断言**：mcode 三文件于 01:39/02:55/04:25、af arm d1/d2 于 07:44/08:56 在 pkl 之后被原地重写；后果：mcode「全 prepare_failed」题 24→0、af 无值题 24→9；声明在 r2 探针（08:57）之后汇编仍以旧快照呈现，并称 83.6%→84.1% 是「唯一无法核实项」——**该断言为假** | 重大 | **成立**。本节点独立测得 mcode 三档 `all_prepare_failed_tasks` 均为 0、af 无值 9、mcode 行数 95/87/39、arm 行数 74/57/20；「83.6%→84.1%」只是**第三个**差异（不是唯一） |
| 3 | **未配对分解 off-by-one**：pkl 实证 af 无值题为 **24**（mcode 23T+1F，F 者 `sphinx-doc__sphinx-10435`），声明 (b) 写 23（22T+1F），两处少 1 | 轻微 | **成立**（node 32135 早已独立指出同一条） |
| 4 | **口径套用不一致**：「配对集内 (af=T, mcode=F) 为 0」仅在严格 `reward=False` 下成立；按声明自己的 null=非过口径，`matplotlib__matplotlib-13989`（af resolved=True；mcode d1 judge_error reward=None）是 1 题 af 过而 mcode 非过，敏感性陈述未披露 | 轻微 | **成立**。本节点复核：当前盘面恰 1 题（matplotlib-13989） |
| 5 | **归因越界一**：「唯一刹车只认 ToolError」与脚手架源码矛盾——`af-stop/src/lib.rs:60-75` 定义 **ToolError/ToolOk/CheckFailed/GenericError 四类**事件，`:250-310` 实现**三条规则**（指纹连击 Stop、CheckFailed 首败即停、累计阈值 Escalate）；且实测存在 max_turns（arm 58 行、turns 全 60）与 wall_timeout（r1 10356 @1808s）**两种刹车**。可成立表述应是「**实测停机原因仅 max_turns 与 wall_timeout，af-stop 规则未触发**」 | 中等 | **成立**。本节点已核 `lib.rs:65 ToolOk { tool: String }`、`:250 pub fn feed`、`:259 Event::ToolError`、arm max_turns **58 行 turns 全 60**、r1 10356 `wall_timeout elapsed_secs 1806` |
| 6 | **归因越界二**：「命令失败被报成 exit=0 成功（MiniMax）」与本轮工件相反：r2 全部 run 的 normal.jsonl 台账记录 14 次 is_error=True/`exit:1:*` 与 2 次 `exit:124:*`；「bash 恒 Ok」仅对 r1(v4) 的 5 个 run（238 次 bash、零 is_error）观察成立 | 中等 | **半成立**：机制限定成立（r1 零负反馈、r2 已有负反馈，不能推广为路线属性）；但**两个数都错**——本节点实测 r2 = **21 次**（`exit:1`×**19**、`exit:124`×2；r2 探针复核 node 32465 的 21/558 正确），r1 = **424 条 tool 事件**（不是 238；238 是只数 `/tmp/align-probe-r1/runs/` 里那 3 个 run 的和，漏掉 `-r2`/`-r4` 批的 13033 与 20859） |
| 7 | **探针波动未披露**：同样 5 题两轮各 af_pass=2，但通过的是不同题目（r1: 13033+20859；r2: 13236+4970），5 题中 4 题两轮间翻转；「af_pass=2」被当稳定值呈现；n=5 且题目级翻转下「探针 2 vs mcode 5 未追平」的扩测门槛统计脆弱 | 重大 | **成立**（本节点逐行复现 4/5 翻转） |
| 8 | **因果链缺失**：探针 scaffold v4/v5 已放开 60 轮上限（r1 出现 93 轮、r2 出现 147 轮），af 由 0/5 恢复到 2/5 → **主表 24.14/45.83/57.89pp 的差距有一部分是 af 侧 60 轮上限的人为压制**；expandNote 未把这一点与「不扩测」决定挂钩 | 重大 | **成立**。本节点核 r1 `spec_json` `max_turns=250`、r2 同为 250；fix1 基线 5 题 4 题死于 max_turns@60 → **「差距画像」是 fix1（60 轮）代际的数，探针是 fix2+（250 轮）代际的数，两代不可直接归因同一 gap** |
| 9 | **expandNote 假分支**：「或无剩余候选」为假——30 个候选中仅探 5 个，余 **25** 个未探（`/tmp/gaptasks.json` 另列 d2 5 题 + d3 11 题）。有效理由只有「未追平」一支 | 轻微 | **成立**。本节点 pkl 复算：候选 30（d1 8 / d2 11 / d3 11），扣已探 5 → **25 未探**；当前盘面口径为 **35 未探** |

### 5.2 终审给出的「达到 confirmed 所需修正」6 项（下一循环的**硬前置**）

1. 主表按当前盘面重述为 **D1 20.75pp / D2 42.11pp / D3 60.00pp（n=111）**，或把旧数字显式标注为 **01:32 快照**并披露 mcode/arm 重写（mtime 证据）。
2. (b) 改 **24 题（23T+1F `sphinx-doc__sphinx-10435`）**。
3. 敏感性补 **matplotlib-13989（af=T / mcode=null）** 一案。
4. 归因改为「**实测刹车为 max_turns（arm 58 行，turns=60）与 wall_timeout（1808s），af-stop 规则未触发；r1 零负反馈观察仅限 v4，r2 台账已记录 exit:1/124**」。
5. 披露**两轮探针题目级翻转（4/5）**，并把「**放开 60 次上限后 af 0/5→2/5**」与差距的部分 harness 归因写入。
6. **expandNote 删去「无剩余候选」支**。

### 5.3 终审确认成立（为对齐组背书，逐条复现）

配对主表三档数字（快照口径）、mcode attempt 级锚 42/45、31/32、18/19、全线 91/96=94.8%、候选 8/11/11=30 及任务清单、回退 14 题清单与取值、24+19 未配对分解、5 探针题行级事实、两轮探针 af_pass=2 / mcode_pass=5、tier 三方零冲突、120 题全部在 `/tmp/swev-s1` 有包、xarray-3993 为唯一多 attempt 分歧且未配对、83.6%→84.1% 的快照解释。**计算本身无误，问题在记录呈现与归因措辞。**

---

## 6. 本账对终审数字的两处订正（下一循环引用终审时须带上）

| 终审原文 | 本节点实测 | 命令 |
|---|---|---|
| r2「14 次 is_error=True（exit:1 ×12、exit:124 ×2）」 | **21 次**（`exit:1`×19、`exit:124`×2）；node 32465 的 21/558 与本节点一致 | `python3` 扫 r2 五行 `run_dir/normal.jsonl` 的 `kind=harness.tool` 事件、统计 `payload.is_error` 与 `payload.error_code` 前缀 |
| r1「5 个 run 共 238 次 bash、零 is_error」 | **424 条 tool 事件**、零 is_error（238 = 只数 `/tmp/align-probe-r1/runs/` 内 3 个 run：147+32+59，**漏掉 `-r2` 批的 13033 与 `-r4` 批的 20859**） | 同上，遍历 results.jsonl 每行的 `run_dir` |

**结论**：终审的两个计数是**漏数**而非错判方向；但它提出的 9 条 issue **全部成立**，故终审 `rejected` 的裁定维持不变。

---

## 7. 下一循环动作

### 7.1 扩测判定（脚本 expandNote，本轮实际取值）

- 脚本逻辑：`aligned = probe.af_pass >= probe.mcode_pass`；两轮均 2 < 5 → **aligned=false** → expandNote 取默认串 **「本轮未达扩测门槛（探针未追平）或无剩余候选；」**。
- **有效理由只有「未追平」一支**——「无剩余候选」为假（终审 issue 6）：**快照口径 25 题未探、当前盘面口径 35 题未探**。
- **本轮不扩测、不跑 D1–D3 全量、不扩 glm5.3f / step5 档案**（按运营者方法：m31f 对齐后才扩其他档案）。

### 7.2 下一批候选（可直接开跑，25 题 = 快照未探池；括号内为当前盘面是否仍为候选）

**D1 剩 3 题**（af 值来自 arm 原判回退，非清洁认证 → 置信度较低，建议先补清洁重判）：
`astropy__astropy-14096`、`matplotlib__matplotlib-20826`、`pytest-dev__pytest-10081`（均在当前盘面候选池内）

**D2 11 题**：`astropy__astropy-14369`、`django__django-10554`、`matplotlib__matplotlib-14623`、`matplotlib__matplotlib-21568`、`matplotlib__matplotlib-24870`、`matplotlib__matplotlib-25479`、`mwaskom__seaborn-3187`、`pylint-dev__pylint-4661`、`pytest-dev__pytest-5840`、`sphinx-doc__sphinx-10673`、`sphinx-doc__sphinx-7462`

**D3 11 题**：`astropy__astropy-13398`、`astropy__astropy-13977`、`django__django-13121`、`django__django-14011`、`django__django-14315`、`django__django-15629`、`django__django-16263`、`pydata__xarray-6992`、`pylint-dev__pylint-4604`、`pylint-dev__pylint-6386`、`sympy__sympy-16597`

- 补充：测绘员已把 d2 前 5 题 + d3 11 题写成 `/tmp/gaptasks.json`（mtime 01:52）——**该文件里的 `d3` 含 `sympy__sympy-13091`，而它在 01:32 快照中 mcode 为 prepare_failed（未判），故不属候选池**；引用该文件时须按 §7.2 校正。
- 当前盘面口径新增候选（快照池之外、现已 mcode=判过且 af=F）：D1 `scikit-learn__scikit-learn-10844`、`scikit-learn__scikit-learn-10908`、`pydata__xarray-4687`、`pylint-dev__pylint-7080`；D2 `sphinx-doc__sphinx-7590`、`sphinx-doc__sphinx-8548`、`sympy__sympy-13877`、`sympy__sympy-20438`、`pydata__xarray-3993`；D3 `sympy__sympy-13091`。
- 下一循环若做 5 题快测，建议抽 **D2/D3 各 2–3 题 + D1 1 题**（D1 剩 3 题的 af 值是回退值，先用清洁重判确认）。

### 7.3 下一循环必办清单（**按终审修正项排序**）

| 序 | 动作 | 完成判据 | 依据 |
|---|---|---|---|
| ① | **重述主表并锁 as-of**：主表改用当前盘面 20.75/42.11/60.00pp（n=111），或显式标为 01:32 快照 + 披露重写 mtime | 账内两套口径并列、均带 as-of 与 mtime 证据 | 终审 issue 1/2；本账 §2.2 |
| ② | **补齐画像 3 处订正**：(b) 改 24（23T+1F）；敏感性补 matplotlib-13989；归因改为「实测刹车 = max_turns(58 行,turns=60) + wall_timeout(1808s)，af-stop 规则未触发」 | 三处均落进下一轮账 | 终审 issue 3/4/5 |
| ③ | **扩测门槛判定改为可判读**：以「**题目级通过集合**」而非 `af_pass=2` 聚合值做判定（n=5 下聚合值不可用） | 下一轮探针表必须给出每题 reward + 与上轮的对齐差异 | 终审 issue 7；本账 §4.3 |
| ④ | **把「60→250 轮」纳入差距归因**：主表是 fix1（60 轮）代际、探针是 fix2+（250 轮）代际，两代不可直接相减 | 下一轮差距画像须标明**代际**；或补跑 fix1 口径的对照臂 | 终审 issue 8 |
| ⑤ | **expandNote 删「无剩余候选」半句**，改为「未追平（探针 2/5，题目级 4/5 翻转）；仍有 25 题（快照）/35 题（盘面）未探」 | 下一循环的 expandNote 逐字照此写 | 终审 issue 6；本账 §7.1/§7.2 |
| ⑥ | **实现候选 4（验证经济学错位）**：提示词加「自验时间封顶」+「pristine HEAD 基线差分」协议；**必须与反考古护栏划界（只允许 HEAD 旁路、不得翻上游修复）** | 新分支 + 新工作树 + 新 target；红队审通过后再探针 | §3 候选 4（node 32221） |
| ⑦ | **候选 5 改判为独立立项**：建容器时清除不可达 git 对象（或明令禁用），而不是教模型利用；并处置「护栏文案说上游修复不在仓库里、对象库里却真实存在」的**白谎** | 单独工单 + 实施记录 | §3 候选 5（node 32236 附带发现） |
| ⑧ | **修 `swev.rs:127` 的 `p.contains("test")` 子串误报**（改为按路径段 `/tests/`、`test_*.py`、`conftest.py` 判定），否则 10 个 pytest 题的 `src/_pytest/**` 正当修复路径永久被误标 | 单测覆盖 + 记录 | §3 候选 4 限定 ④；§4.1/§4.2 `gate=test_edit` |
| ⑨ | **新待管项：fix2 墙钟 3424s > mcode 1800s**——即 r1 引入的 1800s 墙钟与 fix2 的 250 轮叠加，约 45% 的 fix2 代际 run 会被 1800s 硬切（15/33 超时，最长 4812s）；需定「墙钟回撤上限」决策 | 运营者/下一轮出结论 | §3 候选 1 限定 ⑥；§4.1 红队限定 ② |
| ⑩ | **r1/r2 分支合流纪律**：r1=v3→v4、r2=v3→v5，**互不含对方**；合流须重新对齐 scaffold bump 并在结果行写清机制并集，否则按 scaffold 字符串推断机制集合会错 | 合流提交 + 结果行注释规范 | §4.2 红队限定 ③ |
| ⑪ | **基建前置**：swebench eval 镜像本地缺失导致 r1 首批 0/5；下一轮开跑前先 `docker images | grep sweb.eval` 确认镜像齐备 | 跑前镜像清单 | §4.1 基建损耗 |
| ⑫ | **判分口径纪律**：探针必须 `judge_mode=clean`（两轮 10 行全 clean，已守住）；下一步是把「题级通过集合 + n」写进结果表，并给每轮留 as-of | 结果表 schema 固定 | §4.1/§4.2 |
| ⑬ | **数据 as-of 纪律**：af arm d1 仍被在飞 af-bench（PID 3890231）追加、mcode 侧文件在 01:32 后被重写过；任何主表数字引用必须带 as-of + mtime | 每处数字带 as-of | §0.1、§2.2 |

### 7.4 下一循环可直接复用的命令与路径

```bash
# 差距主表（当前盘面）→ 见 §2.1 的两段 python，输出 D1 20.75 / D2 42.11 / D3 60.00（n=111）
# 快照主表 → python3 读 /tmp/pairing-state.pkl，输出 24.14 / 45.83 / 57.89（n=72）
# 候选池（当前盘面）→ 同口径 mcode=T & af=F，D1 12 / D2 16 / D3 12 = 40，扣已探 5 → 35
# 探针结果逐行 → python3 解析 /tmp/align-probe-r{1,2}/results.jsonl
# 负反馈台账 → python3 扫各 run_dir/normal.jsonl 的 kind=harness.tool 事件
# 生效策略/终态 → sqlite3 读 <run_dir>/harness.db 的 run_row.spec_json / terminal_json
# 生产工作树未动 → git -C af rev-parse HEAD（应恒为 94cd1923…）+ git -C af status --porcelain
```

**关键路径**：`/tmp/truth-rejudge/bench-fix1-d{1,2,3}-m31f/results.jsonl`（af 清洁判）、`/tmp/bench-fix1-d{1,2,3}-m31f/results.jsonl`（af arm 原判）、`/tmp/bench-official-mcode-d{1,2,3}-m31f/results.jsonl`（mcode）、`/tmp/pairing-state.pkl`（01:32 快照）、`/tmp/swev-s1/`（120 任务包）、`/tmp/align-probe-r{1,2}/`（本轮探针）、`/tmp/gaptasks.json`（测绘员的下一批清单，**含 1 题需校正**）、`/home/pan-ding/afbuild-align-r{1,2}/af-bench-fix4-align-r{1,2}`（本轮二进制）。

---

## 8. 纪律与合规记录

| 纪律 | 本轮状态 | 证据 |
|---|---|---|
| gov 生产面零触碰 | **守住** | 本轮全部工件在 `/tmp`、`/home/pan-ding/workspace/af-wt-align-r*`、af 分支上；未碰 bao/higress/caddy/zot/pg、`/opt/company`、`/opt/opch` |
| af 生产工作树不动 | **守住** | `git -C af rev-parse HEAD` = `94cd1923c34842983049bce5f97b3dcb6c7c348b`（guardrail-fix2），仅 5 个既有未跟踪 `poc/` 目录（09:23 亲查） |
| 产物二进制换新名、不覆盖生产位 | **守住** | `af-bench-fix4-align-r1`（sha256 `aeeb35fe…`）、`af-bench-fix4-align-r2`（sha256 `4bf41006…`）；`af/target/debug/af-bench` mtime 仍 Oct 21 18:16 |
| `/tmp/bench-*`、`/tmp/truth-*` 只读 | **守住** | 改动全部落在新工作树/新 target；红队自建副本在 `/tmp/rt-verify-now/`、`/tmp/rt-aggr-m31f.json` |
| 密钥零明文 | **守住** | 本账未记录任何密钥值；端点只写档案名（m31f / step-5 / glm-cp） |
| 结论必须带命令/路径证据；做不到如实说 | **守住并有 1 处显式声明** | §0.1「未跑」行：构建/单测结论只署红队节点，记账员未复跑 cargo |
| 判分口径 | **守住** | 探针 10 行全部 `judge_mode=clean`、attempts=1；判分链 `tools/swev-judge.py` 未被改动（两分支 diff 不含判分路径） |
| 在飞臂不动 | **守住** | PID 3890229 / 3890231 始终在跑，未被本轮干预 |

---

## 9. 本账明确未做的事（供下一轮接手人判断可信边界）

1. **未跑** cargo build / cargo test / cargo fmt / clippy —— 全部构建与单测结论来自红队节点（32267、32371）自建 target 的复验，本节点未复跑。
2. **未跑**任何判分、任何探针题、任何扩测批次 —— 本轮探针由快测执行员（32271、32381）跑完，本节点只读了 `results.jsonl` 与 `harness.db`。
3. **未跑** fix1 口径的对照臂 —— 「放开 60→250 轮」这一归因（终审 issue 8）目前只有 fix2 A/B 侧的旁证（13236 fix1 max_turns@60 F → fix2 completed@169 T），**没有同批同题的 fix1-vs-fix4 配对臂**。
4. **未读** 模型侧 trace.db（工具输出原文）—— 终审亦声明未读；因此「exit=0 谎报」在**模型可见内容**层面本轮无直接证据，只有 `normal.jsonl` 台账与 `effects.db` 侧证。
5. **未处理** `/tmp/gaptasks.json` 的 `sympy__sympy-13091` 归属问题（该题在 01:32 快照中 mcode 未判）—— 已在 §7.2 标注，下一轮取用前须重算候选池。
6. **未合并** r1/r2 分支 —— 两分支 divergent（v4 / v5），合流纪律见 §7.3 ⑩。

---

*账毕（第一循环）。本账由状态记账员（MiniMax-M3.1-Flash-Preview）于 2026-10-22 09:27 CST 写入 `计划/研究组/对齐组-state.md`；下一循环请从 §0.1 的自测表与 §7.3 的必办清单开始，续写时**不要**照抄本账 §2.1 的快照数字而不带 as-of。*

---

# 第二循环（提速版 v2）· 账本增补

> 本节是**追加节**，§0–§9（第一循环账）一字未改。写作时点 **2026-10-22 23:4x CST**；本节所有数字带 as-of，并区分「本节点亲跑」与「节点自报」。
> 工作流 run：**`dwfrun-2926ede2-9dda-42c0-9350-b4b17420c27a`**（名「研究组①对齐组·第二循环·提速版v2」，2026-10-22 17:04:08 起，`status=running`，`spent_tokens=161,347,269`——`dwf_run` 表，**本节点 23:3x 亲查**）。
> 流程脚本：`.zcode/workflow-drafts/研究组1-对齐组.dwf.ts:1-269`，标题行自述「第二循环（提速版 v2：收割在盘产物 + 回归对照并行 + 候选起草并行）」；提速令出处 = 脚本 `:1-8` 注释（运营者提速令 12:4x 杠杆五/六/七；16:5x 修正：第 0 档轮拆三步、**一切 af-bench 跑批必拆 ≥2 路并行**，理由「单进程内任务串行是本轮实测确认的坑：5 题=2.5h」）。
> 红线沿用第一循环（脚本 `:83-85` COMMON「硬性纪律」①—⑦）：任何改进不得引入未来信息读取 / 测量语义零改动 / gov 生产面不碰 / 密钥零明文 / 在飞进程不动 / `/tmp/bench-*`、`/tmp/truth-*` 只读 / 判分容器并发上限 4 且全厂 <12。

## 10. 第二循环节点账与本节点自测

### 10.1 节点账（`dwf_node` + `dwf_actor` 表，本节点 23:3x 亲查）

| site | actor（模型） | 内容 | 节点自报裁定 | 本节点复核 |
|---|---|---|---|---|
| ask#1 | 差距测绘员（GLM-5.3-Flash） | 真实差距池重算（带 as-of，剔 S 档 74） | — | **数字已漂移，见 §11.2** |
| ask#2 | 红队·差距核数（step-5） | 独立复算剔除表/口径/池题 | **confirmed**（3 条轻微 issue） | 裁定与 issues 原文照录 |
| ask#4 | 改进实施员（GLM） | r1/r2 分支合流 | `build_ok=true` | **已亲核**（§14） |
| ask#5 | 改进实施员（GLM） | 第 0 档采纳轮·收割核查 | 17 族 / 6 commits / 回归 2/5 | **已亲核**（§12、§13） |
| ask#6 | 候选起草员（GLM） | 起草 3 个候选（与回归收割**并行**） | — | §15 |
| ask#7 | 回归收割员（GLM） | 对照补测 3 题 + k2 复跑 6 次 + 逐题配对定性 | — | **行级已亲核**（§13） |
| ask#8 | 红队·第0档审查（step-5） | 审第 0 档采纳 + 回归对照配对 | **rejected**（**7 条 issue**） | 裁定与 issues 原文照录 |
| ask#9 ord1/2/3 | 红队·机理归因（step-5） | 候选①②③ 逐条门审 | **confirmed / inconclusive / confirmed** | §15 |
| ask#10 ord1/2 | 改进实施员甲/乙（GLM） | 路 A=候选①、路 B=候选③ | build_ok ×2 | §16 |
| ask#11 ord1/2 | 红队·机理归因（step-5） | 两路实现审查 | **inconclusive / confirmed** | §16 |
| ask#12 | 快测执行员甲（GLM） | 探针（p01 臂） | af 4 / mcode 5 / clean | **已亲核**（§16） |
| ask#13 | 红队·机理归因（step-5） | 探针行级复核 | **confirmed**（0 条 issue） | §16 |
| ask#14 | 红队·三审（step-5，**未参与本循环任何环节**） | 三审 | **confirmed**（6 条 issue） | §17 |
| **ask#15** | **状态记账员（MiniMax-M3.1-Flash-Preview，本节点）** | 落账 | — | — |

- 人物线 13 actor（19320–19390，`dwf_actor`）；**未生成的位**：脚本无「探针扩测」分支位（`aligned=false` 恒不扩测）、`快测执行员乙`（actor 19380）**从未被调用**（`resolved_model=None`、`session_id=None`）——**成对并行只成了一半**：两路**实现**并行，两路**探针**只有一路（p01）；p00 臂的探针由实施员甲自跑（2 题），不是工作流编排的探针节点。
- 脚本 `for (pair=0; pair<2 && vetted.length>0 && !aligned)`：本轮 `vetted` 装入候选①③（候选② inconclusive 未入列）→ pair 0 取满 2 条 → 跑完即 `vetted.length=0` 退出 → **第 2 对从未开始**。

### 10.2 本节点自测（2026-10-22 23:3x–23:4x，**全部本节点亲跑**）

| 自测项 | 命令 | 输出 | 判读 |
|---|---|---|---|
| 第二循环 run/节点/actor 账 | `python3` 读 `~/.zcode/cli/db/db.sqlite`（`mode=ro`）`dwf_run`/`dwf_node`/`dwf_actor` | run `dwfrun-2926ede2-…`（17:04:08 起、running、spent 161,347,269）；18 个 ask 节点（17 完成 + 本节点在飞）；13 actor | 与 §10.1 表逐行一致 |
| **9 个主数据文件行数+mtime（漂移证据）** | `stat -c '%y' …` + `grep -c .` | truth-rejudge d1/d2/d3 = 44/24/21 行（mtime 10-21 19:14/19:12/18:52，**未动**）；af arm d1 **83** 行 @**10-22 15:34**、d2 **59** 行 @**13:48**、d3 20 行（10-21 03:56）；mcode d1 **96** 行 @**10-22 15:51**、d2 87 行 @04:25、d3 39 行 @01:39 | **测绘员 as-of 12:48 的行数（arm 78/57、mcode 95）已全部过期**；漂移源 = 12:48 后另有 af-bench 批写 arm d1/d2 + mcode d1 被重判订正 |
| **剔 S 74 差距 + 真实差距池重算** | `python3` 复刻 §2.1 口径（af 清洁末 attempt + arm 末条非 null 回退；mcode `status∈{completed,judge_error}`、reward=null 计非过），S 集 = 独立解析 `计划/研究组/mcode考古份额-量化.md:70-89` §7「S 档（74）」D1 31 / D2 28 / D3 15 | **全量**：D1 n=59 af=41 mcode=57 **27.12pp** / D2 n=40 af=20 mcode=38 **45.00pp** / D3 n=20 af=7 mcode=19 **60.00pp** / 合计 **n=119 af=68 mcode=114 gap=38.66pp**；**剔 S 74**：D1 n=28 af=20 mcode=26 **21.43pp** / D2 n=12 af=5 mcode=10 **41.67pp** / D3 n=5 af=2 mcode=4 **40.00pp** / 合计 **n=45 af=27 mcode=40 gap=28.89pp** | 与测绘员 12:48 读数（剔 S 合计 15.38pp、n=39）**不同** → 见 §11.2 漂移分解 |
| S 74 清单解析 | `python3` 正则切 `mcode考古份额-量化.md` §7 | D1 31 / D2 28 / D3 15，合计 **74**，短名→包名前缀映射（mpl→matplotlib__、sklearn→scikit-learn__、seaborn→mwaskom__、requests→psf__、flask→pallets__…） | 测绘员与红队核数所述「74 名逐一映射、各恰对应 1 个 `/tmp/swev-s1/*.json`」**可复现** |
| 剔 S 残余分解（23:4x 现算） | 同上 | **双过 27 / 双败 5 / 仅 mcode 过 13 / 仅 af 过 0**；剔 S 配对集内 arm 回退题 **19** | **第一循环 §2.3 的「仅 af 过 1 题 `matplotlib-13989`」已消失**（见 §11.2③） |
| 探针池 5 题 mcode 侧 | `python3` 读 `/tmp/bench-official-mcode-d{1,2}-m31f/results.jsonl` 取末有效行 | 10081/10908（d1）、3187/7462/13877（d2）**全部 status=completed & reward=True** | **mcode_pass=5 是硬对照**（非估计） |
| 探针池 5 题 af 清洁侧 | `python3` 读 `/tmp/truth-rejudge/bench-fix1-d{1,2,3}-m31f/results.jsonl`（全 `judge_mode=clean`） | **仅 seaborn-3187 有清洁行**（reward=False, status=not_resolved）；10081/10908/7462/13877 **无清洁行 → af 值为 arm 原判回退** | 测绘员 caveat 属实：**5 题中 4 题的 af=F 是回退值**，非清洁认证基线 |
| **第二循环 7 个 results.jsonl 逐行解析** | `python3` 解析 arm/ctl/ctl-c2/k2/p00/p01/r1 | arm 5 行、ctl 2 行、ctl-c2 3 行、k2 6 行、p00 2 行、p01 **7 行（5 判定 + 2 setup_failed）**、r1 4 行（3 判定 + 1 run_failed） | 与 §12/§13/§16 各表逐位一致；**p01 的 2 条 setup_failed 行 reward=None、run_dir=None**（基建桶与模型败正确分离） |
| **harness.db 终态 + 生效策略** | `python3 sqlite3 mode=ro` 读各 `run_dir/harness.db` 的 `run_row.terminal_json` / `spec_json` | **臂（tier0）**：5 run `policy={max_turns:250, wall_timeout_secs:1800, observation_window:5}`，终态 2×wall_timeout(elapsed 1800/1824)+3×completed；**对照（v6ctl / v6ctl-c2）**：5 run `wall_timeout_secs=None, observation_window=None`，终态全 completed；**探针 p00/p01**：5+5 run `wall_timeout_secs=1800, observation_window=None`，终态 1×wall_timeout(p01 seaborn elapsed=1935) | **三层机制差被本节点直接证实**（臂 vs 对照差 r1 墙钟 + tier0 折叠/S083；对照为 v3 代）；p01 属 v6 无折叠代（与 tier0 臂**不可直接配对**） |
| tool 事件 / is_error 台账 | `python3` 扫各 `run_dir/normal.jsonl` 的 `kind=harness.tool` 事件 | **p01：tool_events=260、is_error=62**（含 `exit:141`×**12**、`exit:124`×6、`exit:1`×31、`exit:2`×10、`exit:4`×1、`exit:120`×2）；**臂（tier0）：941 事件 / 38 is_error**；**对照 ctl-c2：342 事件 / 0 is_error** | 节点自报「260/62/12」**逐位复现**；对照臂 **0 条 is_error** = v3 代确无负反馈通道（节点结论成立） |
| 分支 / 提交 / 生产树 | `git -C af log --oneline main..<branch>`、`git rev-parse HEAD`、`git status --porcelain` | 生产树 HEAD 仍 **94cd1923c34842983049bce5f97b3dcb6c7c348b**（guardrail-fix2），仅 5 个既有未跟踪 `poc/` 目录；分支：fix4-align-r1(c9ae50a) / -r2(936fa48) / **align2(0dd1a23)** / **align2-tier0(fb7666d)** / **align2-r1(5d9c94d)** / **align2-p00(5d9c94d)** / **align2-p01(588382d)** | **gov 生产面与 af 生产工作树零触碰**（纪律守住） |
| 二进制 sha256 | `sha256sum` 6 个产物 | `af-bench-fix4-align2`=8754b74a… / `-b2`=7974bcc3… / `-tier0`=1a9bf4f0… / `v6ctl-0dd1a23`=97170abe… / `-p00`=e6c3fdf5… / `-p01`=6b81bd45…；**生产位 `af/target/debug/af-bench` mtime 仍 10-21 18:16** | 节点自报 sha 全部对上；**未覆盖生产位** |
| tier0 工作树状态 | `git -C /home/pan-ding/workspace/af-wt-align2 status --porcelain` | **6 个文件 staged 未提交**（main.rs +32/-…、run.rs **-52**、spec.rs **-7**、tests.rs **-138**、smoke.rs -1、docs +12）；`git diff --cached spec.rs` = **删除 `Policy.observation_window` 字段** | **= 实施员自建的「v8 回退（摘除 S002/S118 折叠）」**，**未提交、未计入 6 commits**；回归与 tier0 二进制均跑在 **fb7666d/v7 提交态**（与 ask#5 声明一致） |
| S083 阈值常量（**订正三审 issue ①**） | `git show fix4-align2-tier0:crates/af-bench/src/tb.rs` + `grep -n` | `tb.rs:109 const LARGE_OUTPUT_SAVE_CAP_BYTES: usize = 512 * 1024;`；`tb.rs:237 const CAP: usize = 12_000;`，`tb.rs:243 if text.len() > CAP { … externalize_output … }` | **触发线 = 12_000 字节（12KB，非 12KiB）**；512KiB 是**写回上限**（超限 → `Err` → 退回 `lossy_truncate`），**不是触发阈值** → 三审把 512KiB 当成阈值**不成立**（详见 §18①） |
| 17 族出处核对 | `sed -n '10,45p' 决策简报.md`；`python3 csv.DictReader` 扫 `strategies.csv` | 决策简报 §二 = 12 族（S128/S077/S066/S065/S033/S032/S073+S074+S045/S130/S147+S148+S149/S150+S151/S152+S170/S169）；§三 前 3 项 = S002/S118/S083；csv：`S156` 的**测试设计列**含「直接采纳」，`S160` 的**验证意见列**含「直接采纳」（其**测试设计列是配对 A/B**） | 17 族 = 12+3+2 **集合成立**；但台账 provenance 句「strategies.csv **测试设计列**标注『直接采纳』的 S156/S160」**对 S160 列位归属不实**（见 §18②） |
| 25775 工件枚举 | `find /tmp -maxdepth 5 -type d -name '*matplotlib-25775*'` + 三个 results.jsonl 逐文件 `grep -c` | tier0 臂 = **1（回归批）+ 2（k2）= 3 跑**；对照 c2 = 1 跑（**通过**） | **「25775 臂四跑四败」（`状态观测/业务目的章程.md` 21:0x）计数错误**——臂只有 3 跑且全败，另 1 跑是对照且**过**；三审 issue ⑥ 成立 |
| **未跑**（本节点明确不做） | — | 未跑 `cargo build` / `cargo test` / `cargo fmt` / `clippy`；未跑任何判分、任何探针题、任何对照/复跑批次；未读模型侧 `trace.db` 工具输出原文 | 所有构建/单测结论**只署红队与实施员节点**；本节「全绿/构建通过」等字样均标注来源节点 |

## 11. 真实差距池（as-of）

### 11.1 测绘员（ask#1，node 32748，**as-of 2026-10-22 12:48:41 CST**）与红队核数（ask#2，node 32749，**as-of 12:55–13:00**）

| 口径 | D1 | D2 | D3 | 合计 |
|---|---|---|---|---|
| 全量配对 | n=55 af=41 mcode=52 **20.00pp** | n=38 af=20 mcode=36 **42.11pp** | n=20 af=7 mcode=19 **60.00pp** | n=113 af=68 mcode=107 **34.51pp** |
| **剔 S 74（真实口径）** | n=24 af=20 mcode=21 **4.17pp** | n=10 af=5 mcode=8 **30.00pp** | n=5 af=2 mcode=4 **40.00pp** | n=39 af=27 mcode=33 **15.38pp** |

- 两种口径含义不同（测绘员原文已点明）：**反事实口径**（假设 S 题全部失效）→「af 领先 37.7/31.6/15.0pp」；**配对集剔除口径** → 剔 S 后 mcode **仍领先 15.38pp**，残余差距真实存在但池子只剩 7 题。
- 敏感性（af 只认清洁判、不用 arm 回退）：全量 n=80 af=55 mcode=76 gap=26.25pp；剔 S n=26 af=21 mcode=22 **3.85pp**——**剔 S 后若只认清洁认证值，差距近乎抹平**，因残余池 7 题中 4 题的 af=F 是 arm 回退值（v2 代际，多死于 tool_free_limit / max_turns@60）。
- **真实差距池（测绘员口径，12:48）= 配对集内 `mcode=T & af=F & ∉S74` = 7 题**：D1 `pytest-dev__pytest-10081`、`scikit-learn__scikit-learn-10908`；D2 `mwaskom__seaborn-3187`、`sphinx-doc__sphinx-7462`、`sympy__sympy-13877`；D3 `django__django-14011`、`pylint-dev__pylint-6386`。考古档位 6 M + 1 N（7462 为唯一无上游痕迹）。**已探 5 题全属 S 档 D1 → 与池零重叠、全部未探。**
- **探针集（≤5，优先 D1/D2）= 10081 / 10908 / 3187 / 7462 / 13877**（D1+D2 恰好占满；D3 两题 14011、6386 如实留作备选未取）。
- **红队核数（step-5）裁定 `confirmed`**，3 条 issue：
  ① 措辞瑕疵——「seaborn-3187 是池内**唯一**清洁认证 F」仅在 5 题探针集内成立；**7 题全池内 `django__django-14011`（D3）同样是清洁认证 F**（clean 2 attempts 均 not_resolved/reward=False）。
  ② 盘面变化——`/tmp/align-probe-r1/results.jsonl` 已被清理（09:2x 后），仅存 r2（mtime 10-22 08:57，5 题）；「已探 5 题」改由 r2 文件 + 本账 §0.1 第 38 行 grounding；「零重叠」是**集合论证**（已探 5 题 ⊂ S-D1 ⊂ S，池 7 题 ∉ S ⇒ 交集恒空），不依赖 r1 文件存在。
  ③ 已知无害数据瑕疵复认——d1 arm 第 76 行为交错损坏行（原文含 sphinx-10449 reward=null + 下一行开头，json 解析失败，**跳过**）；该行 reward=null 本就不进配对口径。
  - 红队另复核通过的项：S 74 全部在配对集内且全部 mcode 通过（⇒ §6 减法口径无高估）、mcode 每任务恰 1 条有效行（multi-row=0、reward 分歧=0）、8 行主表逐位复现测绘员读数、**漂移归因亲验**（剔除 d1 arm 12:20 段新增的 sphinx-10449(T) / sphinx-10435(F) 后 D1 精确回到 09:2x 锚点 53/40/51/20.75pp）、`ps -p 3890229,3890231` 两进程**已退出**（盘面趋稳）。

### 11.2 ⚠ 本节点 23:4x 复算：测绘员的 12:48 读数**已过期**（as-of 纪律）

复刻同一口径现算（命令见 §10.2 第 3 行）：

| 口径 | D1 | D2 | D3 | 合计 |
|---|---|---|---|---|
| 全量配对 | n=59 af=41 mcode=57 **27.12pp** | n=40 af=20 mcode=38 **45.00pp** | n=20 af=7 mcode=19 **60.00pp** | **n=119 af=68 mcode=114 gap=38.66pp** |
| **剔 S 74** | n=28 af=20 mcode=26 **21.43pp** | n=12 af=5 mcode=10 **41.67pp** | n=5 af=2 mcode=4 **40.00pp** | **n=45 af=27 mcode=40 gap=28.89pp** |

**漂移分解（逐条本节点亲查）**：

1. **新增 6 个配对题**（12:48 后写入 af arm 与 mcode）：`sphinx-doc__sphinx-10323`/`-10466`/`-10614`/`-11510`（D1）、`sympy__sympy-14248`/`-17318`（D2）——**6 题全部是 af=arm 原判回退值 F**（`max_turns@60` 或 `tool_free_limit`，v2 代际）+ **mcode=completed/T** ⇒ 6 题**全部进入真实差距池**。
2. **`matplotlib__matplotlib-13989` 被重判订正**：mcode d1 第 96 行（末行，mtime 15:51）为 `completed/reward=True`，note 原文 `rejudge-correction: basis=swev-replay`；此前第 15 行为 `judge_error/reward=None`（note `judge.json unreadable…rc=1`）⇒ **第一循环 §2.3 记的「1 题 af 过而 mcode 非过」敏感性一案在 23:4x 盘面已消失**，剔 S 残余分解「仅 af 过」由 1 降为 **0**。
3. **合计效应**：剔 S 残余池 **7 题 → 13 题**；剔 S 差距 **15.38pp → 28.89pp**；全量 **34.51pp → 38.66pp**（n 113→119）。

**结论（写进下一循环）**：

- **本循环全部「真实差距池」引用必须带 as-of**：测绘员口径 = **12:48:41，7 题**；本节点口径 = **23:4x，13 题**。两者不可混用。
- 测绘员的 7 题与本节点的 13 题**前 7 题完全包含**（10081、10908、3187、7462、13877、14011、6386），新增 6 题即上列 D1 四题 + D2 两题 ⇒ **本轮已跑的 5 题探针仍在池内**，但**池子已不是 7 题**。
- 池内 **af 值置信度分层（本节点亲算）**：剔 S 配对集内 **arm 回退题 19 题**；剔 S 池 13 题中 **5 题有清洁认证 F**（`django-10999`、`seaborn-3187`、`requests-2317`、`django-10097`、`django-14011`），其余为回退值 ⇒ **引用池内 af=F 时须逐题标「清洁认证 / arm 回退」**（测绘员与红队核数的同一 caveat 至今未消）。
- **注意**：这 6 个新增题的死因（`max_turns@60` / `tool_free_limit`）与第一循环终审 issue 8 的**代际混淆**同型——它们是 **fix1（60 轮）代际**的失败样本，**不能**直接计为「放开 250 轮可回收的收益」。

## 12. 第 0 档采纳：逐族清单与回归结果

### 12.1 逐族清单（17 族，**本节点亲读** `git show fix4-align2-tier0:docs/tier0-adoption.md` 全文）

落地台账 = af commit `8763e01`「docs: 第0档采纳台账——17 族逐条处置表（代码采纳/已内建/跳过+原因）与评测纪律协议」。

| # | ID | 一句话机制（台账原文锚点） | 处置 | 落点 / 依据 |
|---|---|---|---|---|
| 1 | S128 | runner 从 git 状态导出 patch（19.3%→71.2%） | **已内建** | `crates/af-bench/src/swev.rs` `capture_diff`（`git -c core.fileMode=false diff`） |
| 2 | S077 | SEARCH/REPLACE 多级容错解析+结构化错误反馈 | **跳过（不适用）** | af 无编辑块解析层（模型经 bash 直接改文件） |
| 3 | S066 | 代码正文不用 JSON 承载，用 markdown/文本块 | **已内建** | `crates/af-bench/src/tb.rs` `bash_tool_decl` |
| 4 | S065 | 编辑格式按模型路由（weak=whole/strong=diff） | **跳过（不适用）** | 单一模型档案 + 无编辑格式层 |
| 5 | S033 | 治理/安全约束钉在压缩之外（违规率 30%→0%） | **已内建** | af 无有损压缩器；system prompt 每轮重发（`crates/af-harness/src/run.rs`） |
| 6 | S032 | 压缩摘要必须来源校验（83% 失败含臆测） | **跳过（不适用）** | 现树无 LLM 摘要压缩器；S002/S118 为确定性机制 |
| 7 | S073/S074/S045 | 沙箱底座：任务级容器+断网+白名单；FS/网络双边界；镜像分层复用 | **已内建（容器形态）** | `tb.rs` `TbEnv::setup`（`docker rm -f` → `docker run -d`）、`--memory/--pids-limit`、离线三通道声明 |
| 8 | S130 | harness 版本级回归防护（35 release 波动 23–39%） | **采纳（本轮运营化）** | 固定 5 题回归集协议（台账 §二），本轮首个执行实例 |
| 9 | S147/S148/S149 | 饱和集回归+活水外推；截止时间切片；基准退役机制 | **采纳（协议文档）** | 台账 §三 |
| 10 | S150/S151 | 置信区间+配对差分析；小差距不可排序+溯源 | **采纳（代码+协议）** | S151 = 结果行 `harness_commit` 字段（commit `3a548c1`，五处结果行） |
| 11 | S152/S170 | 成本归一化指标（同等成本解决率）为一等指标 | **采纳（协议文档）** | 结果行已带 `tokens/turns/agent_wall_ms`（台账 §四） |
| 12 | S156 | 三层 evals+失败模式正则分类（pass@k/flakiness） | **采纳（协议文档）** | 台账 §五：L1 cargo test / L2 冒烟 / L3 bench；失败先归因（setup_failed/infra vs not_resolved） |
| 13 | S169 | Batch API 半价跑大批评测 | **采纳（政策记录）** | 台账 §六；**现 endpoint 无 batch 通道**，政策先行不虚报已实现 |
| 14 | S002 | 工具结果清理/上下文编辑（+29%，token −84%） | **代码采纳** | commit `9818633`：`Policy.observation_window` + `run.rs::fold_observations`（只折 Tool 项，保留 call_id/name/is_error；System/User/Assistant **不折**；transcript 不改） |
| 15 | S083 | 大工具输出外置（>20KiB 只回路径+预览） | **代码采纳** | commit `bb018d3`：`tb.rs` 大输出写回容器 `/tmp/.af-outputs/`（base64 分块），上下文只进预览+路径+回读指引；**失败退有损截断** |
| 16 | S118 | 只保留最近 5 条观测全文（+3.0pp，官方默认） | **代码采纳** | commit `9818633`（与 S002 同机制）：swe-v `observation_window=Some(5)`；TB/InjecAgent `None`（口径不动） |
| 17 | S160 | 技能边际收益先证伪（49 技能 39 零提升） | **跳过（不适用）** | af 无技能注入面；该族是「引入技能库前的准入门槛」 |

- **台账自述的两处参数/出处偏差（红队与三审均点出，本节点复核）**：① S083 清单原文阈值为 **20 KiB**（csv「测试设计」列：`超过阈值（20 KiB / 50k token 预算）改为「路径 + 预览 + 截尾 30 行」`；决策简报 §三 亦写「Copilot CLI 20KiB 阈值」），落地触发线为 **12,000 字节**（更早外置，严格替代原有损截断 CAP，**非劣化**）；② 台账 provenance 句把 S160 归到 csv「测试设计列」，实为**验证意见列**（其测试设计列是配对 A/B 协议）——见 §18②。
- **17 族清单与原文一致性**：本节点亲读 `决策简报.md:15-31`（§二 12 族）与 `:36-38`（§三 前 3 项）→ **12+3+2=17 集合逐条对上**；台账「S118 一句话栏 +3.0pp」可溯源至 csv「比保留完整历史高 3.0pp」。
- **代码采纳仅 3 笔**（另 9 族「已内建」、5 族「跳过」）：`bb018d3`(S083) / `9818633`(S002+S118) / `3a548c1`(S151)；加上 `8763e01`(台账)、`b0d3c59`(fmt)、`fb7666d`(style) = **6 commits**（本节点 `git log main..fix4-align2-tier0` 亲核）。
- **测量语义零改动**（红队亲核，本节点核 diff 面）：`git diff 0dd1a23..fb7666d --name-only` 仅 8 文件，**不含判分路径**（`tools/swev-judge.py` mtime 10-22 02:28，早于本轮；`tb.rs` 超时常量 180/600 两代一致；`ARCHAEOLOGY_PATTERNS` 数组 diff 为空；三臂 `eval.sh` md5 同为 `c6c080c6…`）。
- **未来信息红线**：`S083` 只写本 run 自身输出；`S002/S118` 只折本会话旧工具输出；运行时验证折标记**不入库**（`harness.db` 的 `transcript_json` 里 `'folded'` 只出现在模型自述文本，非 harness 注记）。

### 12.2 回归快测结果（S130 门禁：5 题应全过，任一题掉过 = 采纳引入回归）

- 回归集（台账 §二协议）：**「真实差距池之外」的已过题**（`/tmp/truth-rejudge` 清洁判 reward=true）中 5 题 —— 本节点亲核 **5 题在 `/tmp/truth-rejudge/bench-fix1-d{1,2,3}-m31f` 清洁判全部 reward=true**，且**均非差距池题**。
- 结果：**`/tmp/align2-tier0-regress/results.jsonl`（5 行，mtime 10-22 16:55，scaffold=v7，judge_mode 全 clean，attempts=1）**：

| 题 | reward | status | 轮次 | 墙钟 | gate |
|---|---|---|---|---|---|
| `pydata__xarray-4094` | **F** | **wall_timeout** | 215 | 1,801,812ms（terminal elapsed=1800） | no_patch |
| `psf__requests-1766` | F | completed | 160 | 1,720,422ms | — |
| `matplotlib__matplotlib-25775` | **F** | **wall_timeout** | 153 | 1,825,784ms（terminal elapsed=1824） | no_patch |
| `matplotlib__matplotlib-25122` | **T** | completed | 91 | 1,714,836ms | — |
| `pydata__xarray-3677` | **T** | completed | 51 | 1,644,020ms | — |

  **回归 = 2/5 → 门禁未过 → 第 0 档采纳轮不算采纳成功**（与红队裁定一致，见 §13.2）。臂的生效策略本节点亲核：`max_turns=250 / wall_timeout_secs=1800 / observation_window=5`，终态 2×wall_timeout + 3×completed。
- 产物：`~/afbuild-align2/af-bench-fix4-align2-tier0`（sha256 `1a9bf4f0…`，mtime 10-22 13:43），**未覆盖生产位**。

## 13. 回归对照配对表（arm / ctl / k2 逐题）与红队定性

### 13.1 逐题配对表（**行级全部本节点亲核**，as-of 2026-10-22 23:4x）

| 题 | 臂 tier0（v7, fb7666d） | 对照 ctl（v3 代, v6ctl + v6ctl-c2） | k2 复跑（tier0 臂，k=2） | 考古档位 |
|---|---|---|---|---|
| `pydata__xarray-4094` | F wall_timeout 215轮 1,801,812ms | **T** completed 61轮 2,691,454ms | **T** completed 154轮 1,749,229ms（a1）<br>**T** wall_timeout 142轮 1,820,951ms（a2，补丁已解判 T） | N·D1 |
| `psf__requests-1766` | F completed 160轮 1,720,422ms | F completed 32轮 907,867ms | F wall_timeout 179轮 1,880,759ms（a1）<br>F completed 156轮 1,801,183ms（a2） | M·D2 |
| `matplotlib__matplotlib-25775` | **F wall_timeout 153轮 1,825,784ms** | **T** completed 146轮 1,961,021ms | F wall_timeout 172轮 1,830,658ms（a1）<br>F wall_timeout 225轮 1,816,816ms（a2） | S·D2 |
| `matplotlib__matplotlib-25122` | T completed 91轮 1,714,836ms | T completed 61轮 3,089,287ms | —（未复跑） | S·D3 |
| `pydata__xarray-3677` | T completed 51轮 1,644,020ms | T completed 41轮 2,270,287ms | —（未复跑） | S·D1 |

- 批次工件：`/tmp/align2-tier0-regress/results.jsonl`（5 行，16:55）、`/tmp/align2-tier0-regress-v6ctl/results.jsonl`（2 行，16:34）、`/tmp/align2-tier0-regress-v6ctl-c2/results.jsonl`（3 行，19:33）、`/tmp/align2-tier0-regress-k2/results.jsonl`（6 行，20:04）。**共 16 行，全部 `judge_mode=clean`、`attempts=1`、`trial=false`。**
- **臂 vs 对照的机制差 = 三层**（本节点亲核 `spec_json`）：对照 = **v3 代**（`wall_timeout_secs=None`、`observation_window=None`、`is_error` **0 条**）；臂 = **v7**（`wall_timeout_secs=1800`、`observation_window=5`、v2 的 is_error 通道 38 条）。差集 = **r1（墙钟+ToolOk 指纹刹车）+ r2（is_error 负反馈+离线三通道+空响应护栏）+ tier0（S083/S002/S118/S151）** ⇒ **任何「对照过而臂败」都不能单独归到第 0 档**。
- 收割员披露的**对照二进制名实不符**：`~/afbuild-align2/af-bench-v6ctl-0dd1a23` 文件名内嵌合流 rev `0dd1a23`，**实测内容是 v3 代基线**（结果行 scaffold=v3、spec 无墙钟、ctl-c2 is_error=0）——与三审 issue ④ 一致。**对照臂与 tier0 臂的差含 r1+r2+tier0 混合效应**。
- 收割员披露的**基建事故（如实记）**：17:21 首批 4 路 nohup（未 setsid）于 17:39:45 因会话轮询超时被连坐 SIGKILL（日志零字节），留下 4 个无判分行的半截 run 目录；处置 = 删本轮自建半截产物 + 清孤儿容器，17:59 setsid 重起，**最终 8 行新结果全部来自重起后的干净批次（18:28–20:04），与被杀批次零混行**。
- 并行与容器纪律：起跑前与途中多次 `ssh anolis` 查 docker 计数（起跑前 4、峰值 7、全程 <12）；`docker images | grep sweb.eval` 确认 6 题镜像齐备（§7.3⑪ 前置执行）。

### 13.2 红队·第 0 档审查（ask#8，node 32807，step-5，as-of 10-22 20:2x）：**裁定 `rejected`**

7 条 issue（原文要点）：

1. **【回归成立·臂级】** matplotlib-25775 是本轮**唯一**「对照过而 tier0 臂稳定败」的题：对照 completed T@1961s/146 轮，tier0 臂 **0/3 全 wall_timeout**（153/172/225 轮，terminal_json 均为 wall_timeout，agent.diff=0B、gate=no_patch，**切时模型仍在发工具调用**——normal.jsonl 末事件为 turn 152 tool_use）。按本轮自己写入的 S130 协议（「5 题应全过；任一题掉过 = 本次采纳引入回归，须回退定位 git bisect」），**采纳轮未过门，不能签为 confirmed**。
2. **【归因未隔离——不得单独归到第 0 档】** 直接死因是**合流基线 0dd1a23 带入的 r1 1800s 墙钟硬切**（非第 0 档代码；r1 红队限定②早已量化约 45% fix2 代际 run 会被 1800s 硬切 = §7.3⑨）。对照臂与 tier0 臂差三层机制（harness.db 实测对照 `wall_timeout_secs=None/observation_window=None`，臂 = `1800/Some(5)`）。**第 0 档侧可疑族 = S002/S118 观测折叠**：mpl-25775 臂对 `lib/matplotlib/text.py` 重读 **77 次** vs 对照 **26 次**、工具调用 242 vs 194、轮次 153/172/225 vs 146；模型自述适应折叠（transcript 原文「The output gets folded when too long. Let me use small targeted reads.」）；xarray-4094 原败跑有 35 次逐字重复命令（k2 两次通过跑仅 12/7 次）。**折叠同时实测有效**：臂末轮 cache_read 34.8k vs 对照 96.7k（上下文 −64%）、每轮更快（11.9s vs 13.4s）——**「省上下文但付重读税」的相关性证据，未做反事实隔离**。
3. **【bisect/回退建议】** ① 先补关键对照：用**真 v6 二进制** `/home/pan-ding/afbuild-align2/af-bench-fix4-align2`（strings 实测含 5 处 wall_timeout、0 处 observation_window = 0dd1a23 内容）复跑 mpl-25775 k≥2：若 v6 也败 ⇒ 回归属 r1 墙钟（回退点是墙钟上限决策 §7.3⑨，与第 0 档无关）；若 v6 过 ⇒ 折叠有贡献，进 ②。② 分支内 bisect：`0dd1a23(v6)→bb018d3(+S083)→9818633(+S002/S118)→3a548c1(+S151)`，重点复跑 9818633 前后两格；S083 在该题仅触发 1 次（低暴露），S151 纯元数据。③ **最低成本回退 = `main.rs` 一处配置 `observation_window: Some(5)→None`**（保留 S083/S151），无需 revert 整个 commit。④ 硬换位窗维持不开，直至 v6 对照 + bisect 出结论。
4. **【审计缺陷·对照二进制名不副实】** 见 §13.1。
5. **【文档瑕·S160 出处句】** 台账称 17 族来源含「strategies.csv 测试设计列标注『直接采纳』的 S156/S160」——实测 csv 中仅 S156 的**测试设计列**带「直接采纳」字样，S160 的测试设计是配对 A/B 协议。**17 族集合本身一致、S160 处置（跳过：af 无技能注入面）合理，仅出处措辞需订正。**（→ 本节点 §18② 的更精确表述）
6. **【参数偏差·S083 阈值】** 清单原文 20KiB、落地触发线 12KiB（等于既有截断 CAP，外置严格替代原有损截断，非劣化），**应作为参数偏离登记在案**。（→ 本节点 §18① 订正其单位与常量）
7. **【配对结论复核·①措辞偏干净】** 逐条亲读原始行，配对定性 ①–⑤ 与数据全部相符；唯 ① 的「随机波动」表述偏干净——原败跑轨迹带**折叠相关重复签名**（35 次逐字重复），机制风险真实存在，只是 k2 未翻车；建议下轮表述为「**方差主导 + 折叠重读税为潜在助因**」。

## 14. r1/r2 分支合流（ask#4，node 32750）

- 合流分支：**`fix4-align2` = `0dd1a23a09f2558059ddab2e4efaf45070a52b06`**（scaffold **v6**），**未弃任何一支**（r1 `c9ae50a` 全量并入，r2 `936fa48` 全量并入）——本节点 `git log main..fix4-align2` 亲核提交序列：`c9ae50a`(r1, v4) → `afe7793`(merge r1) → `936fa48`(r2, v5) → `0dd1a23`(merge r2, v6)。
- **三处冲突逐处裁决**（实施员复核 + 红队复核一致）：① `SWEV_INSTANCE_PROTOCOL` = 墙钟预算行 **∪** 增强离线行（严格超集替代）；② **scaffold 重对齐 v6 = v3 + {v4: 墙钟1800s + ToolOk 指纹刹车} ∪ {v5: bash is_error 负反馈 + 离线三通道 + 空响应护栏}**，机制清单写入结果行注释（§7.3⑩ 合流纪律）；③ `run.rs` `done_error` = r2 output 透传 **∪** r1 `fingerprint:None` 并存。
- **红线核验**（红队复验）：判分链零改动；`ARCHAEOLOGY_PATTERNS` 与 main 逐字节一致；零未来信息引导；生产树/生产二进制未动。
- **构建亲见**：`/tmp/af-wt-align2 @0dd1a23`，`CARGO_TARGET_DIR=~/afbuild-shared cargo build` 实编+链接 **8.17s Finished**；`cargo test -p af-stop -p af-harness -p af-bench` = **121✓/0✗**（红队自建 target 复验）；产物 `~/afbuild-align2/af-bench-fix4-align2-b2`（sha256 `7974bcc3…`，本节点亲核一致）。
- **工作树位置纪律**：合流分支检出在 **`/tmp/af-wt-align2`**（分流默认根约定 §3「续用不强迁、严禁对已检出分支再 add」），**未在 `~/workspace` 重建**——与 §7.3⑩「工作树落 ~/workspace/」的一般约定有出入，**已如实记录，不静默改址**。

## 15. 候选与红队结论（ask#6 起草 → ask#9 逐条门审）

### 15.1 三个候选（起草员 GLM，与回归收割**并行**执行）

| # | 候选 | 机制摘要 | 红队裁定 | 关键限定（红队原文要点） |
|---|---|---|---|---|
| ① | **双轨预算制**：turn 上限降为后备 + 墙钟对齐 mcode 1800s | 以墙钟为主预算、`max_turns=250` 为后备；`--wall-timeout-secs` 旋钮（0=关=对照臂）；剩 300s/120s 各一次收尾提醒 | **confirmed**（ask#9 ord1，node 32816，**5 条 issue**） | ①**探针设计强制条件**：墙钟硬切已是**实证回归疑点**，必须跑 wall-on(1800) vs wall-off(0) **同二进制配对臂**（含 mpl-25775），单默认臂重蹈「单臂无配对」覆辙；② 与可疑族 S002/S118 **运行级耦合**（折叠→重读税→轮次膨胀→墙钟硬切）；③ **target_failure 增益预期未披露 0 字节交叉核**——`pytest-10081`（a1/a2）与 `sympy-13877`（a1/a2）fix1 全部 attempt `agent.diff = 0B`，兄弟工作流 `dwfrun-80498024`（node 32601/32607，`recompute.py:158` `all(sz==0)` 规则）已把这两题剔出真实差距池（「结构性无 diff，采样也救不了」）→ **3 题「死于预算」中至多 1 题为干净增益样本**；④ 引用瑕疵（`EVAL_TIMEOUT_SEC` 行号差、`Instant::now` 实为 `SystemClock::wall_ms`、墙钟为轮次间检查 → 硬切可超 1800s 至多一个轮次，实测最晚 1879s）；⑤ **流程观察**：`~/afbuild-shared` 陈旧工件 → warm `cargo build` 报「Finished 0.44s」**假新鲜**，而 `cargo test` 编译失败（`Event::ToolOk has no field fingerprint`），须 touch 两 crate 源码强制重编（3.62s）后才全绿 → **下一轮 build_ok 须以 test 编译通过为据** |
| ② | **验证引导收窄**（首循环候选 4 的落地版）：base 时刻已存在测试 + issue 自带复现 + 自验时间封顶 | 纯提示词三句话写进 `SWEV_INSTANCE_PROTOCOL`；(a) 提交前必跑 base 时刻已存在的受影响测试文件；(b) 验证须包含 issue 自带复现段端到端跑通；(c) 自验时间封顶（mcode 同款）；可选 HEAD 基线差分 | **inconclusive**（ask#9 ord2，node 32824，**5 条 issue**） | **实现面全过**（纯提示词、零判分接触、护栏不伤、红线①合规、**确证未实施**、与 §7.3⑥ 规格一致）；**但立论核心被证伪**：① `seaborn-3187` **不是 completed-but-F**，实测 `terminal_json={"kind":"max_turns"}` / `turn_index=60` / `agent_wall_ms=2671244`（**墙钟已超候选①的 1800s**），且 issue 复现**实际端到端跑过**（effects.db seq 15000/16000/17000：`cat > /tmp/repro.py` + `python /tmp/repro.py`，receipt exit=0 输出 `title:sp/labels:['a','c','b']`）；② `sklearn-10908` 的「验证错位」**不成立**——该 run 已跑过既有测试文件（seq 25000 `pytest sklearn/feature_extraction/tests/test_text.py -q`）、全量套件（seq 38000/39000 `timeout 2400 python -m pytest sklearn/ -q`）、基线对照（seq 42000 `git stash && …`）、issue 复现，**仍败于隐藏测试新增的 `assert_false(cv.fixed_vocabulary_)` 断言**（issue 文本从未提及的内部属性）⇒ **隐藏规格缺口，不是验证引导缺口**；③ **首循环实例全部来自 S 档池**（mpl-20859 / pytest-10356 / pylint-4970 均在 S 74 内，已被剔出真实差距池），**池子迁移未披露**；④ 与候选①存在运行级交互（自验鼓励长套件 vs 墙钟/600s 单命令封顶）；⑤ 次要瑕疵（`main.rs` 行号引的是生产树而非目标树；P2P 计数集合正确但列举顺序对不上） |
| ③ | **exit 语义修正**（pipefail）：exec 桥接内层 `bash -lc` 前置 `set -o pipefail;` | 令 `__AF_RC=$?` 反映首个失败环节而非末位 `tail/head` 的 0；exit=N 仍置末行；**纯反馈面、零新增刹车** | **confirmed**（ask#9 ord3，node 32828，**4 条 issue**） | ① **证据⑤「取证边界」declaration 失实**——per-call 工具输出**就在 `effects.db` 的 `effect_intent.receipt_json`**（候选本可引而未引）：据此逐 call 坐实 `sympy-13877-a1` seq 24001 `pytest … | tail -5` → **exit=0 + `No module named pytest`**（pytest 根本没跑，假成功）；`sphinx-7462-a1` seq 27001 → exit=0 + `5 failed, 5 passed`；`pytest-10081-a1` seq 7000/28000 `pip download … | tail -5` → exit=0 + ConnectTimeoutError；② **「3 题 F2P 文件命令被掩蔽」只有 1 题坐实**——`sympy-13877` 坐实，但 `sphinx seq 27000`（`28 passed`）与 `sklearn seq 25000`（`48 passed`）**rc 诚实**；③ 「只改反馈不改判定」须补**记账变更限定**：rc 翻非零会把该调用从 Ok 翻成 `Err(ToolFailure)`（`main.rs` `bash_result`），进 af-stop 规则①输入群（limit=3、error_code 含命令指纹）并改 `effect_fresh` 记账（Err→ExternalCall）——**池内 8 attempt 全扫「≥3 次重复命令」的 run = 0、最大连续逐字重复 = 1 ⇒ 规则①无新触发空间**；④ 计数口径小瑕（管道数按「含 |」朴素计） |

- 红队另有**重叠核**（node 32816 §F、node 32828）：三个候选与第 0 档 17 族**零重叠**（无预算族、无验证引导族、无 exit 语义族；最近的 S077 已在台账列「跳过」）；候选③与候选②**互补但会互相混淆归因**（③使失败可见→模型多迭代→吃①的预算；②③目标类部分重叠）→ **结果表须分列归因**。
- **机制门结果**：`vetted` = **候选①、候选③**（候选② inconclusive 未入列）→ 脚本 `vetted.shift()` 取出 2 条进入 pair 0。

## 16. 成对并行探针（逐轮）

### 16.1 实现两路（ask#10）与实现审查（ask#11）

| 路 | 分支 / 提交 | 内容 | 产物 | 实现审查裁定 |
|---|---|---|---|---|
| **A（候选①）** | `fix4-align2-p00` @ `5d9c94d`（**无新提交**，v6 内容已完整） | 候选①补全（`--wall-timeout-secs` 缺省 1800=mcode `SOLVE_TIMEOUT` 等额、0=关=对照臂开关、结果行自述 `wall_timeout_secs`、双轨优先级矩阵测试） | `/home/pan-ding/afbuild-shared/af-bench-fix4-align2-p00`（sha `e6c3fdf5…`，本节点亲核） | **inconclusive**（node 32840，ask#11 ord1，**6 条 issue**） |
| **B（候选③）** | `fix4-align2-p01` @ `588382d`（`tb.rs` +57/−1、`main.rs` +18/−5，**仅 2 文件**） | `tb.rs` 新增 `bridge_inner()`，exec 桥接内层 `bash -lc` 脚本前缀 `set -o pipefail; `；`main.rs` 两处：profile 别名 `mavis-m31f-p01`（端点/模型/key/提示词全同，仅容器名后缀）+ scaffold `v6→v6-p01`（两处结果行 + 机制并集注释） | `/home/pan-ding/afbuild-shared/af-bench-fix4-align2-p01`（sha `6b81bd45…`，本节点亲核） | **confirmed**（node 32844，ask#11 ord2，**3 条 issue**） |

- **实现审查的硬性要求（被违反的与被满足的）**：
  - 路 A（node 32840）**inconclusive 的核心理由**：我在候选①审查时设定的**强制条件未执行**——**wall-on(1800) vs wall-off(0) 同二进制配对臂未跑**；本路单臂对 fix1 基线的 0/5→4/5 把**墙钟、轮次放宽、r2 反馈三层混在一起**（终审 issue 8 / §7.3④ 的代际混淆同型）；**按本路自己的数据，墙钟对通过集合的边际贡献 = 0**（4 个 run 在 165–452s 自然 TASK_COMPLETE 收尾，唯一被墙钟硬切的 seaborn-3187 切时补丁已就位、判分照过）→「墙钟成主力」**超出单臂数据能支撑的范围**，4/5 应记在 **v6 包（主因 60→250 轮）**账上。附加订正：报告称「两题镜像均在 anolis 本地」**不实**（`pytest-10081` 镜像只在本机 docker 有，p00 批实际跑在**本机** docker 而非 anolis）；**r1 批死因表述不准**（`[4/5] django-14011 RUN_FAILED` 是 infra 行，随后 `sqlite: disk I/O error` 杀死的是**第 5 题**，身份未披露）；续用批与 sample-agg 批有并发窗口（已排查无实害，**须登记为残留风险**）。
  - 路 B（node 32844）**confirmed**：实现/测试/产物/探针数据逐字段亲核属实；失分项仅 4 条订正级：① **管道失败计数 51 应为 56**（其 `summarize.py` 按「前一条 assistant 消息里最后一个 bash 命令」join，对同轮并行双工具调用错配；用 `effects.db` 逐 call 顺序 join 重算 = 56，逐 run 10/6/16/12/12）；② 重试行目录名表述不准（两条重试行 `run_dir` 均为 **`-a1`**，失败行 `run_dir=None`）；③④ 四项声明无工件可核（anolis 四态实测输出未保存、docker 计数无日志、镜像被清理的窗口与归因无法确证），按未核实计；④ `docker images -q` 对缺失镜像**也返回 0**（本节点已复现）→ 跑前镜像检查须用 `docker images | grep`。
- **第 0 档被否后的基线处置**：脚本逻辑 `t0Check.verdict === "confirmed" ? "第0档采纳后分支" : merge.merged_branch` ⇒ **第 0 档 rejected ⇒ 两路实现基线回退为合流分支 `fix4-align2`**，与章程 22:0x 记载的「阶段五回退合流基线（tier0 分支封存待归因复跑）」一致。**候选分支不含 tier0 commits**（`git merge-base --is-ancestor 9818633 5d9c94d` = false，红队亲验）⇒ 第 0 档后续无论回退与否，**都不影响 p00/p01**。

### 16.2 探针（**只跑了 1 路**：p01）

| 批次 | 臂 | 题 | reward / status / 轮次 / 墙钟 | 备注 |
|---|---|---|---|---|
| `/tmp/align2-probe-p01`（ask#12，**工作流编排的探针节点**） | `af-bench-fix4-align2-p01`（候选③ pipefail，scaffold **v6-p01**） | `pytest-dev__pytest-10081` | **T** completed 26轮 397,385ms | |
| | | `scikit-learn__scikit-learn-10908` | **T** completed 19轮 128,253ms | |
| | | `mwaskom__seaborn-3187` | **T** **wall_timeout** 56轮 1,937,335ms（terminal elapsed=1935） | 切时补丁已解，判分照过 |
| | | `sphinx-doc__sphinx-7462` | **F** completed 31轮 609,391ms | 唯一败因：**补丁错误类**（eval.log「2 failed, 65 passed」＝F2P 对；`py39: FAIL code 1 (1.45s)`），与预算机制无关 |
| | | `sympy__sympy-13877` | **T** completed 53轮 363,367ms | |
| | | （+ 2 条 setup_failed 行） | reward=None / run_dir=None | **基建事故行**（anolis sweb.eval 镜像于 21:17–22:05 被非本组进程清理）；同二进制重跑后 a1 行落定，失败行保留在 results.jsonl |

  **p01 汇总：af_pass = 4/5 vs mcode_pass = 5/5，judged_rows = 5，5 判定行全 `judge_mode=clean`/`attempts=1`/`http_retries=0`（本节点逐行复核）。**
- **p00 臂的探针（**非工作流编排**，由实施员甲自跑，2 题）**：`/tmp/align2-probe-p00`（scaffold v6，`wall_timeout_secs=1800`）——`pytest-10081` T completed 24轮 452,133ms、`sympy-13877` T completed 21轮 406,971ms；末行「af-bench 完成: 2 题, resolved 2, infra 0」。**另续用批** `/tmp/align2-probe-r1`（12:21，v6）3 判定行：`sklearn-10908` T completed 13轮 164,686ms、`seaborn-3187` T wall_timeout 59轮 1,819,276ms、`sphinx-7462` F completed 23轮 173,550ms；外加 1 条 `django-14011` **run_failed** 行（`sqlite: disk I/O error`）。**p00 的 5 题合并表 = p00 2 行 + r1 续用 3 行**（实施员自报 4/5，与 p01 逐题一致）。
- **红队·探针审查（ask#13，node 32852，step-5）= `confirmed`，0 条 issue**：本节点亲跑复核 7 行 = 5 判定行 + 2 基建失败行；af_pass=4、clean=true、5 题 probe_tasks 与文件 task_id 逐一对应、**mcode_pass=5 重新亲读 mcode 末有效行全部 completed+reward=True**、attempts=1 全成立。
- **⚠ 归因纪律（两路实现审查共同点出，必须带进下一循环）**：**4/5 不得表述为任何单一机制的增益**。可断言的只有：**①零回退**（p01 与 v6 基线在 3 个可比重题上 10908=T / 3187=T / 7462=F **完全一致**；10081/13877 与 p00 同日亦 T）；**② is_error 通道真实化已生效**（p01 tool_events=260 / is_error=62 / `exit:141`×12，本节点亲核）；**③ 4/5 归在 v6 包（主因 60→250 轮）对 fix1 的代际差上**，不是候选①或③的增量。
- **扩测判定**：`af_pass(4) < mcode_pass(5)` ⇒ **aligned = false ⇒ 不扩测**（方法口径 `aligned = probe.af_pass >= probe.mcode_pass` 恒假）；`vetted` 已空 ⇒ **第 2 对未开始**。**扩测未发生是数据支持的**（不是首循环那种「无剩余候选」假分支——本轮池内 5 题已探、池外仍有题）。
- **n=5 敏感性**：首循环同 5 题两轮间 4/5 题目级翻转的教训（§4.3 / 终审 issue 7）仍然成立；且 4 个通过题中 2 题（`pytest-10081`、`sympy-13877`）的 fix1 全部 attempt `agent.diff = 0B`，**已被邻组工作流 `dwfrun-80498024`（node 32601/32607）按「结构性无 diff」剔出真实差距池** ⇒ 通过集合对这两题高度敏感。

## 17. 三审意见（红队·三审 ask#14，node 32857，step-5，**未参与本循环任何环节**）

**裁定：`confirmed`**（6 条 issue，无一推翻记录本体）——「六项审维度中，5 题配对定性、wall_timeout 轮次证据、归因限定、17 族清单一致性、tier 标注、未来信息红线、探针边界均获工件级证实」。

| # | issue | 性质 | 本节点复核 |
|---|---|---|---|
| ① | **【轻微·台账文档与代码不一致】** 台账 `docs/tier0-adoption.md`（`8763e01`）S083 处置栏写「超 **12KiB** 完整输出写回容器」，但 tier0 分支实际阈值为 `LARGE_OUTPUT_SAVE_CAP_BYTES = 512*1024 = 512KiB`（`tb.rs:109`；预览 2000+600 字节），代码内无任何 12KiB 常量；表格一句话栏「>20KiB」与决策简报原文一致但同样非实现值 | 轻微（文档笔误） | **本节点订正见 §18①：三审读错了常量**——触发线是 `tb.rs:237 const CAP: usize = 12_000`（`text.len() > CAP` → 触发外置），512KiB 是**写回上限**（超限则 `Err` → 退回 `lossy_truncate`）。台账「12KiB」**接近正确**（12,000 字节 ≈ 11.72KiB），三审的「实际阈值 512KiB」**不成立** |
| ② | **【中·既有债·差距池工件与标签不符】** `/tmp/gaptasks.json`（mtime 2026-10-22 01:52，**早于 09:5x 考古量化**）21 题与 `mcode考古份额-量化.md` §7 逐题对档 = **19 题 S 档 + 2 题 M 档 + 0 题 N 档**——「mcode=T&af=F 剔除考古题」的剔除**从未应用到该文件**；且 `计划/空档期批次-规格书-20261022.md:15` 标注其为「真实差距池 21 题（d1 5/d2 4/d3 12）已算好」（文件实为 5/5/11），巡检日志 11:5x 引「真实差距池 20 题（剔除考古）」，**三处数字互不相符** | 中（既有债，非本轮引入） | 成立；本账 §9.5 已登记同源问题。**下一轮引用「真实差距池」不得直接取用该文件** |
| ③ | **【轻微·as-of 缺位】** 受审记录正文不带任何 as-of 时点，其数据分别落于 16:34（v6ctl）、16:55（tier0 原臂）、19:33（v6ctl-c2）、20:04（k2）；且第二循环内容**尚未写进本账**（本账末条 as-of 2026-10-22 09:27） | 轻微（程序性） | **本节已补**：§10–§19 全部带 as-of；**且本节点 23:4x 复算发现测绘员的 12:48 读数本身也已过期**（§11.2） |
| ④ | **【轻微·对照臂目录名与实际二进制代际不符】** `align2-tier0-regress-v6ctl` / `-c2` 目录名易误读为「v6 合流基线对照」，但结果行自述 `scaffold="v3"`（`git show 0dd1a23:…/main.rs` 写 "v6"、guardrail-fix2 产线同文件写 "v3"，已分别核对） | 轻微 | 成立；本节点亲核：ctl-c2 的 `spec_json` = `wall_timeout_secs=None, observation_window=None` 且 `is_error` **0 条** ⇒ **确为 v3 代**。**建议下轮改名或在账上显式登记二进制来源**（本账 §13.1 已登记） |
| ⑤ | **【观察·待测通道】** tier0 臂与对照臂在同 5 题上**轮次系统性膨胀**（tier0 51/91/153/160/215 轮 vs 对照 32/41/61/61/146 轮，4094/1766 上差 2–5 倍），与厂长「观察折叠族致重读→轮次膨胀」预判同向；红队将回归信号修正为「墙钟与对照构造缺陷混杂」**并未排除该通道**（三层机制差下不可归因） | 观察 | 成立。**建议的干净对照复跑（0dd1a23+同款墙钟）除 reward 外必须同报 `turns`/`agent_wall_ms` 与重读行为指标**，否则该通道仍不可分离 |
| ⑥ | **【轻微·外部账目计数不一致】** `状态观测/业务目的章程.md` 21:0x 写「25775 臂**四跑四败**全 wall_timeout」，但盘上工件仅存 **3 次** tier0 臂运行（原臂 a1 + k2 a1/a2）；受审记录「三跑 0/3」与工件一致 | 轻微 | 成立，本节点亲核（`find` + 三个 results.jsonl 逐文件 `grep -c`：臂 1+2=3、ctl 1）⇒ **章程 21:0x 计数错误**；**臂 3 跑全败 + 对照 1 跑通过** |

## 18. 本账对第二循环各节点的订正（引用时须带上）

| # | 对象原文 | 本节点实测 | 依据（本节点亲跑） |
|---|---|---|---|
| ① | 三审 issue ①：「tier0 分支实际阈值为 `LARGE_OUTPUT_SAVE_CAP_BYTES = 512*1024 = 512KiB`，代码内无任何 12KiB 常量」 | **不成立**。S083 外置的**触发线是 `tb.rs:237 const CAP: usize = 12_000`**（`tb.rs:243 if text.len() > CAP { …externalize_output… }`）；`tb.rs:109` 的 512KiB 是**写回上限**（`externalize_output` 内 `if full.len() > LARGE_OUTPUT_SAVE_CAP_BYTES { return Err(...) }` → 退回 `lossy_truncate(text, CAP)`），**不是触发阈值** | `git show fix4-align2-tier0:crates/af-bench/src/tb.rs` + `grep -n`（§10.2 第 14 行）。**台账「12KiB」接近正确（12,000 字节，非 12,288）**；应勘误的是**单位**（12KB ≠ 12KiB），不是阈值本身 |
| ② | 台账 provenance 句「strategies.csv **测试设计列**标注『直接采纳』的 S156/S160」；红队「csv 中仅 S156 命中『直接采纳』」 | **两处均不精确**。`S156` 的「直接采纳」确在**测试设计列**；`S160` 的「直接采纳」在**验证意见列**（`唯一在钉 commit 真实仓库上隔离技能边际收益的公开基准，配对开/关设计天然就是准入门槛 A/B，直接采纳。`），其**测试设计列是配对 A/B 协议** | `python3 csv.DictReader` 逐行扫 `harness策略调研/strategies.csv`（§10.2 第 15 行）。**17 族集合成立、S160「跳过」处置合理**；应勘误的是**列位归属** |
| ③ | 测绘员 ask#1 与红队 ask#2 的「真实差距池 = 7 题」「剔 S 合计 gap 15.38pp」（as-of 12:48） | **已过期**。23:4x 复算：池 **13 题**、剔 S 合计 **n=45 af=27 mcode=40 gap=28.89pp**、全量 **n=119 af=68 mcode=114 gap=38.66pp**。漂移 = 6 个新配对题（sphinx-10323/10466/10614/11510、sympy-14248/17318，全为 af arm 回退 F + mcode T）+ `matplotlib-13989` 被 `rejudge-correction` 订正为 mcode 通过 | §11.2（§10.2 第 3–5 行）。**首循环 §2.3 的「1 题 af 过而 mcode 非过（matplotlib-13989）」在 23:4x 盘面已消失**（剔 S 残余「仅 af 过」= 0） |
| ④ | 回归收割员自报「管道/对照臂与 tier0 臂相差三层机制」 | **完全成立并被本节点以 `spec_json` 独立证实**（对照 `wall=None/obs=None`、臂 `wall=1800/obs=5`、ctl-c2 `is_error=0`） | §10.2 第 8–9 行 |
| ⑤ | 实施员乙自报「管道失败 51 条」 | 红队订正为 **56**（effects.db 逐 call join vs 错配 join）；本节点只复核了「260 事件 / 62 is_error / exit:141×12」三项逐位一致，**未独立复算 51/56 之争** | §10.2 第 9 行（**部分复现**） |
| ⑥ | `状态观测/业务目的章程.md` 22:0x 增量：「候选②（验证引导收窄）被红队以轨迹级铁证**否决**」 | **裁定标签不准**：红队（node 32824）给的是 **`inconclusive`**，不是 `rejected`——其原文裁定理由是「**实现面（纯提示词、零判分接触、护栏不伤、红线①合规、未实施确认、与 §7.3⑥ 规格一致）全部通过**；但候选的立论核心…在两个具题上分别被证伪…故机制归因不能确认为候选所陈述的形态：判 inconclusive」。脚本语义上 `inconclusive` 与 `rejected` 同义于「**不入 vetted**」，故**未实施这一结果无误**，只是「否决」二字与裁定标签不符 | node 32824 `result_json`（本节点亲读） |

## 19. 下一循环动作（第二循环 → 第三循环）

### 19.1 硬前置（按红队/三审纠正令排序）

| 序 | 动作 | 完成判据 | 依据 |
|---|---|---|---|
| ① | **画归因的干净对照：用真 v6 二进制（`~/afbuild-align2/af-bench-fix4-align2`，= 0dd1a23 内容）复跑 `matplotlib-25775` k≥2** | v6 也败 ⇒ 回归属 r1 墙钟（回退点 = 墙钟上限决策 §7.3⑨，与第 0 档无关）；v6 过 ⇒ 折叠有贡献，进 ② | §13.2 issue 3①；三审 issue ⑤（**除 reward 外必须同报 `turns`/`agent_wall_ms` + 重读行为指标**） |
| ② | **候选①的 wall-off 配对臂**：`--wall-timeout-secs 0`（5d9c94d 已提供该开关 = 0→None）**同二进制同 5 题**补跑，与 wall-on 臂配对 | 配对差分离出墙钟的边际贡献；**当前所有 4/5 读数均不可归因到墙钟** | §16.1 路 A 审查强制条件（node 32816 设定、node 32840 认定未执行） |
| ③ | **tier0 分支内 bisect**：`0dd1a23(v6)→bb018d3(+S083)→9818633(+S002/S118)→3a548c1(+S151)`，重点复跑 9818633 前后两格 | 出结论 | §13.2 issue 3② |
| ④ | **最低成本回退预案**：`main.rs` 一处 `observation_window: Some(5)→None`（保留 S083/S151） | 预案就位；**注意 tier0 工作树已有一份 staged 未提交的 v8 回退（`spec.rs` 删 `observation_window` 字段、`run.rs` −52、`tests.rs` −138），须先决定「提交为 v8」还是「丢弃重做」** | §13.2 issue 3③；§10.2 第 12 行（本节点亲核 staged diff） |
| ⑤ | **第 0 档维持「不算采纳成功」**，硬换位窗（观测折叠/容器名换装）**继续不开** | 红队复审后改判 | §13.2 issue 1；章程 22:0x |
| ⑥ | **「真实差距池」一律现算现引，并逐题标「清洁认证 F / arm 回退 F」**；**禁用 `/tmp/gaptasks.json`** | 池清单 + as-of + 逐题来源标注 | §11.2；三审 issue ②（该文件 19/21 为 S 档）；测绘员 caveat |

### 19.2 计量与纪律修正（可立即执行）

| 序 | 动作 | 依据 |
|---|---|---|
| ⑦ | **`build_ok` 一律以 `cargo test` 编译通过为据**，不得只署 warm「Finished」；`~/afbuild-shared` 陈旧工件出现 `Event::ToolOk has no field fingerprint` 时先 `touch` 两 crate 源码重编 | node 32816 issue ⑤；node 32840 复现同一形态 |
| ⑧ | **跑前镜像检查用 `docker images \| grep sweb.eval`，禁用 `docker images -q`**（缺镜像时 `-q` 也返回 0） | node 32844 issue ④（本节点已复现 rc=0） |
| ⑨ | **探针结果表逐行标注出处**（本轮 p00/p01/r1 三批合并，同题多臂须标 arm+行号）；**基建失败行（`setup_failed`/`run_failed`）与模型败行分桶** | §16.2（p01 7 行 = 5 判定 + 2 setup_failed）；§7.3⑫ |
| ⑩ | **引用 pipeline 机制数时用「题目级通过集合」判定**（n=5 单样本），并披露 2/4 通过题（10081、13877）属邻组「结构性无 diff」排除集 | §16.2 归因纪律；node 32840 issue ② |
| ⑪ | **台账勘误**：S083 阈值单位（12KB ≠ 12KiB，触发线 `tb.rs:237 CAP=12_000`）；S160 出处列位（验证意见列，非测试设计列） | §18①② |
| ⑫ | **SIGPIPE 代价登记**：`pipefail` 使 `grep\|head` 类良性截断报 `exit:141`，p01 5 run 共 **12 条**（本节点亲核） | §16.2；node 32844 |
| ⑬ | **候选② 暂不实施**：若要实施，target_failure 须按红队实测改写（seaborn-3187 = max_turns@60 击杀、sklearn-10908 = 隐藏规格缺口、首循环实例属 S 档池外），且探针须与候选①分列归因 | §15.1 候选② 红队裁定 **inconclusive** |
| ⑭ | **扩测仍未达门槛**（af 4 < mcode 5，`aligned=false`）→ **不扩 D1–D3 全量、不扩 glm5.3f/step5 档案**；扩测理由只能是「未追平」，**不得写「无剩余候选」** | §16.2；首循环终审 issue 6 的教训继续适用 |

### 19.3 本节明确未做的事（供下一轮判断可信边界）

1. **未跑** `cargo build` / `cargo test` / `cargo fmt` / `clippy` —— 本节所有「全绿/构建通过」均署红队或实施员节点，本节点未复跑。
2. **未跑**任何判分、任何探针题、任何对照补测或 k2 复跑 —— 本节点只读了 `results.jsonl` 与 `harness.db`（只读）。
3. **未复算** 管道失败 51 vs 56 之争（只复核了 260/62/12 三项）。
4. **未做** 「真 v6 二进制复跑 25775」「wall-off 配对臂」「tier0 内 bisect」——三者都是 §19.1 的**下一循环动作**，本节只登记纠正令。
5. **未读** 模型侧 `trace.db` 工具输出原文；池内 per-call 取证依据是 `effects.db` 的 `effect_intent.receipt_json`（由红队提供路径，本节点未逐 call 复算）。
6. **未处理** `/tmp/gaptasks.json` 的归属问题（已按三审 issue ② 登记为禁用件）。
7. **未裁决** tier0 工作树那 6 个 staged 未提交文件（v8 回退）的去留——属 §19.1④ 的决策项，记账员不代裁。

---

*第二循环账毕。本节由状态记账员（MiniMax-M3.1-Flash-Preview）于 2026-10-22 23:4x CST 追加写入 `计划/研究组/对齐组-state.md`；下一循环请从 §11.2（差距池已漂移，须现算）、§13.2（回归归因三路 bisect）、§19.1（硬前置 6 项）开始，续写时**不要**照抄 §11.1 的 7 题池而不带 as-of。*

# 第三循环（红队纠正令执行 + 候选①配对臂 + v8 决策 + 差距池续测）· 账本增补

> 本节是**追加节**，§0–§19（第一/第二循环账）一字未改。写作时点 **2026-10-23 07:0x CST**；本节所有数字带 as-of，并严格区分「**本节点亲跑/亲读**」与「**节点自报**」。
> 工作流 run：**`dwfrun-0059228c-2e38-4bb7-9b5c-82670bd2eb97`**（名「研究组①对齐组·第三循环」，`time_created`=2026-10-23 04:32:26，`status=running`，`spent_tokens=25,373,420`——`dwf_run` 表，**本节点 07:01 亲查**）。
> 流程脚本：`dwf_run.script_text`（7,671 字符，**本节点亲读**），标题行自述「红队纠正令执行 + 候选①配对臂 + v8 决策 + 差距池续测」；编排自述：净对照/候选①配对/7462 续测三路跑批【并行】、v8 决策+候选起草零容器【并行】、**红队串行**、跑批 >2 题必拆 ≥2 进程。红线不变：未来信息零引入 / 测量语义零改动 / 生产位 `ecd1a1a0` 只读 / 他线在飞进程零接触。
> **本节与 §19 的对账**：§19.1 的 6 项硬前置，本循环**执行了 3 项**（①净对照、②候选① wall-off 配对臂、③探针第 5 题续测）、**裁定了 1 项**（④v8 处置，裁定为「采纳为变体」但**采纳序 3 步一步未执行**）、**未执行 2 项**（v8 五题门禁跑批、tier0 内 9818633 前后 bisect）；§19.2 计量纪律本循环继续适用，并新增 3 条（§27.4 ⑦⑨⑪）。

---

## 20. 第三循环节点账与本节点自测

### 20.1 节点账（`dwf_node` + `dwf_actor` 表，本节点 2026-10-23 07:01 亲查）

| site | node | actor（模型） | 内容 | 节点自报裁定 | 本节点复核 |
|---|---|---|---|---|---|
| ask#1 | 32915 | actor#4 v8决策员（GLM-5.3-Flash） | 候选起草 4 条 + v8 决策 | `v8.adopted=true` | 采纳**裁定**与工作树树态亲核（§24.1）；**采纳序 ③ 构建 / ④ 门禁跑批均未执行**（本节点亲查：无 v8 二进制、无 `scaffold=v8` 结果行） |
| ask#2 | 32916 | actor#1 净对照执行员（GLM-5.3-Flash） | 净对照（`0dd1a23` 内容 + 同面墙钟）复跑 25775 | `verdict_25775`=**tier0 致**（S002/S118 折叠嫌疑成立） | 二进制身份链 + 结果行亲核（§21.2/§21.3）；**机理侧写「text.py 重读 0/0 vs 臂 77」不可复算，本节点独立复算后订正**（§21.4） |
| ask#3 | 32917 | actor#2 配对臂执行员（GLM-5.3-Flash） | 候选① wall-on/off **同二进制**配对臂（同 5 题） | `on_pass=3/5`、`off_pass=3/5`；墙钟**负向边际=1 题** | 10 行结果 + 10 个 `harness.db` policy 亲核（§22.2/§22.3）；红队/三审的措辞与披露订正已并入（§22.5） |
| ask#4 | 32918 | actor#3 末题执行员（GLM-5.3-Flash） | 差距池第 5 题 sphinx-7462 候选③续测（p01 二进制单跑）+ 未翻归因 | `reward=False`（未翻） | 结果行亲核（§23.1）；轨迹级归因为**节点自报**，本节点未逐 call 复算（§28 第 4 条） |
| ask#5 | 32960 | actor#5 红队·三循环（step-5-preview） | 净对照审（构建身份链 + 归因 + 候选红线 + v8 证据） | **confirmed**（5 条 issue） | 5 条原文照录（§25.3）；其第 ① 条订正（重读数）**本节点独立复算成立** |
| ask#6 | 32964 | actor#5 红队·三循环 | 配对臂审（同二进制/同题集/两臂齐全/环境对称） | **confirmed**（5 条 issue） | 原文照录（§25.3） |
| ask#7 ord1 | 32968 | actor#5 红队·三循环 | 候选①门审 = **C2 墙钟压力下补丁先行** | **confirmed**（4 条 issue） | 原文照录（§25.2/§25.3） |
| ask#7 ord2 | 32972 | actor#5 红队·三循环 | 候选②门审 = **C1 失败后转向纪律** | **confirmed**（5 条 issue） | 原文照录（§25.2/§25.3） |
| ask#7 ord3 | 32976 | actor#5 红队·三循环 | 候选③门审 = **C3 交付物=工作树 diff 自包含** | **confirmed**（5 条 issue） | 原文照录（§25.2/§25.3） |
| ask#8 | 32980 | actor#5 红队·三循环 | v8 决策审（树态 + 冒烟 + 判读规则） | **confirmed**（6 条 issue，含 **2 条阻塞级**） | 原文照录（§24.3/§26.2） |
| ask#9 | 32984 | actor#6 红队·三审（step-5-preview，**未参与本循环任何环节**） | 三审（身份链 / 配对口径 / v8 处置 / 候选门 / as-of 纪律） | **confirmed**（6 条 issue） | 原文照录（§26） |
| **ask#10** | 32988 | **actor#7 状态记账员（minimax/Minimax-M3.1-Flash-Preview，本节点）** | 落账 | — | — |

- **人物线 7 actor（19402–19432，`dwf_actor`）**：`actor#1`–`#4` = GLM-5.3-Flash（四个执行员/决策员）；`actor#5` 红队·三循环 = step-5-preview（**1 个 actor 承担 6 次串行门审**）；`actor#6` 红队·三审 = step-5-preview；`actor#7` = 本节点。
- **脚本分支位与实际调用**：脚本 `phase("四路并行")` 起 4 个 agent（净对照 / 配对臂 / 末题 / 起草+v8）→ `phase("红队串行裁决")` 1 个红队 actor 连发 6 次 ask（净对照审、配对臂审、候选×3、v8 审）→ `phase("三审与落账")` 三审 + 记账员。**候选循环的上限是 `vetted.length < 3`**，故第 4 条候选（B2①人格句）**未被红队门审**——它由起草员自驳「明确不立项」，与 B2 移交单 §四一致（§25.1）。
- ⚠ **时间戳一致性观察（本节点亲查）**：红队/三审节点**自报 as-of 最晚到「07:5x CST」**（node 32964/32980/32984 的 `evidence` 首句），而 `dwf_node.time_updated` 上界为 **06:59:10**、本节点读库时刻为 **07:01:10 CST**（`date`）。即**节点自报时间戳超出盘面时钟 30–50 分钟**，自相矛盾。→ 引用本循环时间一律以 **DB `time_created/time_updated` + 工件 mtime** 为准，节点自报 as-of 只作参考（§27.4 新增纪律 ⑮）。

### 20.2 本节点自测（2026-10-23 07:0x CST，**全部本节点亲跑**）

| # | 自测项 | 命令 | 输出 | 判读 |
|---|---|---|---|---|
| 1 | 第三循环 run/节点/actor 账 | `python3` 读 `~/.zcode/cli/db/db.sqlite`（`mode=ro`）`dwf_run`/`dwf_node`/`dwf_actor` | run `dwfrun-0059228c-…`（04:32:26 起、running、spent 25,373,420）；**12 节点 = 11 completed + 1 running（本节点 32988）**；7 actor | 与 §20.1 表逐行一致 |
| 2 | 三个二进制 + 生产位 sha256 | `sha256sum ~/afbuild-shared/af-bench-netctl-0dd1a23 ~/afbuild-shared/af-bench-fix4-align2-p00 ~/afbuild-shared/af-bench-fix4-align2-p01 af/target/debug/af-bench` | `0c37f56d…be9` / `e6c3fdf5…08a` / `6b81bd45…82d7` / **`ecd1a1a0…331`（生产位）** | 与 §10.2 登记的 p00/p01 值**逐位一致**；生产位 `ecd1a1a0` 与第二循环一致、**未被覆盖** |
| 3 | 四个二进制 mtime | `stat -c '%y %n' …` | netctl **10-23 04:42:39**（本循环新建）；p00 10-22 21:13:37、p01 10-22 21:18:34（复用未重建）；生产位 **10-23 00:53:54**（早于本循环起跑） | 生产位未被本循环触碰 |
| 4 | **代际标记 strings** | `strings -a <bin> \| grep -c -- <pat>`（8 个标记） | netctl：`wall_timeout`=5 / `observation_window`=0 / `fold_observations`=0 / `pipefail`=0 / `--wall-timeout-secs`=0 / `fingerprint`=19 / `harness_commit`=0；p00：`wall_timeout`=9 / `--wall-timeout-secs`=**2**（候选①在场）/ 其余 0；p01：`pipefail`=1 / `v6-p01`=1（候选③在场）/ 其余 0 | **三个二进制代际自证成立**：净对照=0dd1a23 内容（无折叠、无候选①③、有 r1 指纹刹车）；p00 只多墙钟旋钮；p01 只多 pipefail |
| 5 | 第三循环 4 份 results.jsonl 逐行 | `python3` 解析 `/tmp/align3-{netctl,pair-on,pair-off,tail}/results.jsonl` | netctl **2 行**（25775 T completed 51轮/504822ms；T wall_timeout 61轮/2037058ms，`http_retries`=1）；pair-on **5 行**（T 10908、T 10081、T 13877、F 7462 completed 21轮/103705ms、F 3187 wall_timeout 54轮/1842999ms）；pair-off **5 行**（**T 3187 completed 116轮/1513385ms**、F 10908、F 7462、T 10081、T 13877）；tail **1 行**（7462 F completed 18轮/76111ms）；**全部 `judge_mode=clean`、`attempts=1`、infra 行 0** | 复现三执行员自报，**on 3/5 vs off 3/5、构成不同**成立 |
| 6 | 生效策略与终态（**harness.db 只读**） | `python3 sqlite3 mode=ro` 读各 `run_dir/harness.db` 的 `run_row.spec_json`/`terminal_json` | netctl 2 run：`max_turns=250`、**`wall_timeout_secs=1800`**、**`observation_window` 键缺席**、终态 completed(TASK_COMPLETE)/wall_timeout(elapsed 2035)；pair-on 5 run：**wall=1800**、obs 缺席、1×wall_timeout(1841)+4×completed；pair-off 5 run：**wall=None**、obs 缺席、5×completed | **配对两臂唯一差 = 墙钟**（本节点亲核）；净对照**带同一面 1800s 墙钟且无折叠** |
| 7 | tier0 臂历史 16 行 | `python3` 解析 `/tmp/align2-tier0-regress{,-k2,-v6ctl,-v6ctl-c2}/results.jsonl` | regress 5 行（4094 F wall@1801812 no_patch 215轮、1766 F completed、25775 F wall@1825784 no_patch 153轮、25122 T、3677 T）；k2 6 行（4094 T completed 154轮、4094 T wall@1820951 gate=ok 142轮、1766 F wall@1880759 gate=ok、1766 F completed、25775 F wall@1830658/1816816 no_patch）；v6ctl 2 行（4094 T completed@2691454、1766 F）；v6ctl-c2 3 行（25775 T completed@1961021、25122 T、3677 T）**scaffold 全 `v3`** | 臂 25775 历史 **0/3 全 wall_timeout + 切时 `agent.diff`=0B**；两条 ctl 获胜轨迹墙钟 2691s/1961s **均超 1800s** |
| 8 | v8 工作树状态 | `git -C ~/workspace/af-wt-align2 status` / `diff --cached --shortstat` / `REVERT_HEAD` / `git grep -n "observation_window\|fold_observations" -- crates/` | 「**您在执行还原提交 9818633 的操作**（所有冲突已解决：执行 `git revert --continue`）」；`6 files changed, 21 insertions(+), 221 deletions(-)`；`REVERT_HEAD=981863395ddce63e7f12e0f3a1193ea5cfc2c2fb`；`git grep` **rc=1（零残留）** | **v8 采纳序第 ② 步（`revert --continue` 提交）尚未执行**——树仍停在 revert 中间态（§24） |
| 9 | 身份链（git） | `git rev-list --count 0dd1a23..fb7666d` / `log --oneline` / `cat-file -t 9818633` / `show --stat 9818633` / `worktree list` | count=**6**（`bb018d3`/`9818633`/`3a548c1`/`8763e01`/`b0d3c59`/`fb7666d`）；`9818633` = commit、**5 files +192/−1**；worktree：`/tmp/af-wt-align2`@**0dd1a23**、`~/workspace/af-wt-align2`@fb7666d、p00@5d9c94d、p01@588382d、生产树 `af`@**94cd192** | 差集 = 6 commits（**S083 + S002/S118 + S151**）；**生产树 HEAD 仍 94cd192**，`status --porcelain` 仅 5 个既有未跟踪 `poc/` 目录 |
| 10 | **v8 门禁是否跑过** | `grep -rl '"scaffold": "v8"' /tmp/*/results.jsonl`；`ls -d /tmp/align2-tier0-v8-regress`；`ls ~/afbuild-align2/` | grep **rc=1（无任何 v8 结果行）**；`/tmp/align2-tier0-v8-regress` **不存在**；`~/afbuild-align2/` 只有 `af-bench-fix4-align2`、`-b2`、`-tier0`、`af-bench-v6ctl-0dd1a23`，**无 `af-bench-fix4-align2-v8`** | **v8 五题 S130 门禁未跑、v8 产物未建**（红队/三审的阻塞级条件成立） |
| 11 | **重读数独立复算（订正项）** | `python3 sqlite3 mode=ro` 逐 run 扫 `effects.db` 的 `effect_intent.payload_json`，计含 `text.py` 的行数 | 净对照 a1/a2 = **26 / 27**（总行 66/71）；tier0 臂三跑 = **93 / 105 / 118**（总行 245/278/314）；v3 代 ctl = **45**（总行 194） | **红队/三审订正成立**：执行员自报的「控 0/0 vs 臂 77」**不可复算**（0/0 源于对不含命令字段的 `normal.jsonl` payload 计数；77 对不上任何单一口径）。方向结论不变，引用须改署可复算口径（§21.4） |
| 12 | `agent.diff` 大小对照 | `stat -c %s <run_dir>/agent.diff` | 净对照 a1=**8199B**、a2=**10143B**；pair-on seaborn=**2724B**、pair-off seaborn=**3757B**；tail 7462=**1010B**；**tier0 臂 25775 三跑 = 0 / 0 / 0** | 两种「补丁形态」不同：臂 25775 = **0B（无产物）**；pair-on seaborn = **补丁在场但未解**（f2p 0/2、p2p 248/0）——**两者不可混称**（§22.5） |
| 13 | 7462 续测结果行 | `python3` 打印 tail 行全字段 | `reward=false`、`status=completed`、`scaffold=v6-p01`、`turns=18`、`model_calls=18`、`agent_wall_ms=76111`、`gate=ok`、`http_retries=0`、`tokens{input 12024, output 5990, cache_read 132391}`、`verifier_note` = `resolved:false, f2p_success:0, f2p_failure:2, p2p_success:49, p2p_failure:0, tests_collected:51, swebench_version:4.1.0` | 复现执行员自报：**判分失败模式=补丁错误类**，与预算/墙钟/pipefail 均无关（§23） |
| 14 | **差距池现算（as-of 07:0x）** | 复刻 §2.1 口径 `python3`（af 清洁末 attempt / arm 末条非 null / mcode `status∈{completed,judge_error}`、`reward=null` 计非过），S74 由 `计划/研究组/mcode考古份额-量化.md` §7 正则独立解析（**74 题**），坏行跳过 1 条（d1 arm 第 76 行交错损坏行，红队第一循环已登记） | 全量：D1 n=59 af=41 mcode=57 **27.12pp** / D2 n=40 af=20 mcode=38 **45.00pp** / D3 n=20 af=7 mcode=19 **60.00pp** / 合计 n=119 af=68 mcode=114 **38.66pp**；**剔 S 74**：D1 n=28 af=20 mcode=26 **21.43pp** / D2 n=12 af=5 mcode=10 **41.67pp** / D3 n=5 af=2 mcode=4 **40.00pp** / 合计 **n=45 af=27 mcode=40 gap=28.89pp**；**池（剔 S ∧ mcode=T ∧ af=F）= 13 题** | **与 §11.2（10-22 23:4x）逐位一致 ⇒ 池自 23:4x 起未漂移**（9 个源文件 mtime 最新为 10-22 15:51:47，本节点亲查）。**新发现**：13 题中仅 **2 题有清洁认证 F**（`seaborn-3187`、`django-14011`），另 **11 题为 arm 回退值**；§11.2 所称「13 题中 5 题有清洁认证 F（另列 `django-10999`/`requests-2317`/`django-10097`）」中**有 3 题不在本口径的 13 题池内** → **§11.2 该句待下一轮核对口径**（§27.4 新增纪律 ⑯） |
| 15 | 代码行核对（引用锚点） | `sed -n` 读生产树与 v8 树 | 生产树 `crates/af-bench/src/main.rs:806-807` = `if diff.trim().is_empty() { gate = "no_patch" }`；生产树 `crates/af-harness/src/run.rs:305` = `TOOL_FREE_FEEDBACK`（只催工具调用、不谈交付物落盘）；生产树 `crates/af-bench/src/swev.rs:57-59` = 容器名 `afbench-swev-{}-{profile}`（**无臂标识**）；生产树 `crates/af-harness/src/spec.rs:121-124` = 完成信号「工具输出首行 trim 全等」；v8 树 `crates/af-bench/src/main.rs:936` = 逐字重复护栏文案（窗口 6 条 / ≥2 前科即注入）；v8 树 `crates/af-harness/src/run.rs:317` = `TOOL_FREE_FEEDBACK`、`:1042` = `fn matched_signal`；v8 树 `crates/af-harness/src/run.rs:323`/`:324` = `WALL_GENTLE_PREFIX`/`WALL_STRONG_PREFIX`、`:326`/`:327` = 阈 300s/120s、`:331` = `fn push_wall_budget_reminders`、`:342` strong 文案「Submit your best current fix NOW」、`:351` gentle 文案「Do not start new lines of work」；v8 树 `crates/af-bench/src/main.rs:729` = `SWEV_INSTANCE_PROTOCOL`、`:990` = `user_message` 拼装点、`:963` = `wall_timeout_secs: Some(1_800)`（**墙钟保留**）、`:1053`/`:1124` = `"scaffold": "v8"`（两处自锚） | 三个候选的挂钩点与红队引用的行号**本节点逐条落到实物**（行号以**本节所标树**为准；红队 §25.3 里 `run.rs:942-954` 是生产树行号，v8 树对应 `:1042`） |
| 16 | staged docs 归因段现状 | `git diff --cached -- docs/tier0-adoption.md`（v8 树） | S002/S118 行已改「采纳→回归回退」；但 §二 仍写「归因：4094=采纳面致归（v6 T→v7 F）→ 回退折叠」与「回退后 scaffold **v8** … 重跑 5 题门禁见 results 行」 | **红队/三审的两条阻塞级订正尚未落到台账**（§24.3/§26.2 ①） |
| 17 | **未跑**（本节点明确不做） | — | 未跑 `cargo build` / `cargo test` / `cargo fmt` / `clippy`；未跑任何判分、任何探针题、任何对照补测或 v8 门禁批次；未逐 call 复算 7462 轨迹归因；未读模型侧 `trace.db` | 所有构建/单测结论**只署红队与执行员节点**（§28 第 1–5 条） |

---

## 21. 净对照实验：二进制身份链与 25775 归因终局

### 21.1 实验设计（红队纠正令，本循环 ask#2）

第二循环三审与红队留下的强制条件：**用 `0dd1a23` 的内容（含 r1 那面同样的 1800s 墙钟）复跑 25775**，与 tier0 臂（`fb7666d`）配对，把「墙钟」与「tier0 层（S083 + S002/S118 折叠 + S151）」两个嫌疑源**分格**。判读规则两支（脚本 ask 原文）：**对照也败 ⇒ 墙钟/题因；对照过而臂败 ⇒ tier0 致**。

### 21.2 二进制身份链（本节点亲核，见 §20.2 第 2/3/4/9 行）

| 环节 | 本节点亲核结果 |
|---|---|
| 产物 | `/home/pan-ding/afbuild-shared/af-bench-netctl-0dd1a23`，sha256 `0c37f56d71cdb9501a64ce08b85d7120c92e61473ccf7542b9ac84c12aa89be9`，mtime **2026-10-23 04:42:39**（本循环新建，**新名未覆盖任何既有产物**；生产位 `ecd1a1a0` 未触碰） |
| 源码基线 | worktree `/tmp/af-wt-align2` @ `0dd1a23a09f2558059ddab2e4efaf45070a52b06`（`git worktree list` 亲见），差集 `0dd1a23..fb7666d` = **6 commits**：`bb018d3`(S083) / `9818633`(S002+S118 折叠) / `3a548c1`(S151) / `8763e01`(docs) / `b0d3c59` / `fb7666d` |
| 代际标记（`strings`） | `observation_window`=**0**、`fold_observations`=**0**（**无折叠**）；`wall_timeout`=**5**（**墙钟在场**）；`pipefail`=0、`--wall-timeout-secs`=0（**候选①③均不在**）；`fingerprint`=19（r1 指纹刹车在场）；`harness_commit`=0（S151 不在） |
| 运行时自证 | 2 个 run 的 `harness.db` `spec_json.policy` = `{max_turns:250, wall_timeout_secs:1800, observation_window 键缺席}`；`results.jsonl` 两行 `scaffold="v6"`、`judge_mode=clean`、`attempts=1` |
| 墙钟面值一致性 | 净对照 `wall_timeout_secs=1800` ≡ 臂 `1800`（§20.2 第 6/7 行）→ **同墙钟、不同折叠**，差集恰为 tier0 层 |

### 21.3 结果与归因终局（本节点亲核行级）

| 侧 | 行 | reward | status | turns | agent_wall_ms | `agent.diff` | 备注 |
|---|---|---|---|---|---|---|---|
| 净对照 a1 | `matplotlib__matplotlib-25775` | **true** | completed | 51 | 504822 | **8199B** | 504s 自然完赛，**墙钟根本未触**；judge f2p 7/0、p2p 89/0（node 32916/32960 自报） |
| 净对照 a2 | 同题 | **true** | **wall_timeout** | 61 | 2037058 | **10143B** | 被墙钟切（终态 elapsed 2035s），但**补丁在位判 T**；`http_retries`=1 |
| tier0 臂（历史 3 跑） | 同题 | false ×3 | wall_timeout ×3 | 153 / 172 / 225 | 1825784 / 1830658 / 1816816 | **0 / 0 / 0 B** | 切时**无补丁**（`gate=no_patch`） |

**归因终局（节点裁定，本节点复核后**维持**，附两条限定）**：
> **tier0 致**：含同一面 1800s 墙钟、但无折叠的对照 2/2 过（其一墙钟切杀仍判过），而 tier0 臂同题 0/3 全 `wall_timeout` 且切时 `agent.diff`=0B ⇒ **若墙钟是死因，含同一面墙钟的对照应同败，实际 2/2 过** ⇒ 臂败归 tier0 层；其中 **S002/S118 观测折叠为头号嫌疑**（对照 51/61 轮 vs 臂 153/172/225 轮，轮次膨胀 2.5–3.7×），S083 在该题暴露仅 1 次、S151 纯元数据。
> —— 该结论**解除**了第二循环 §13.2 issue 2 的「归因未隔离」状态（`对齐组-state.md:599-605`）。

**限定 ①（红队 32960 issue ①，三审 32984 issue ①）**：机理侧写的两个数**不可复算**。「对照 text.py 重读 0/0」源于对 `normal.jsonl` 的 `harness.tool` payload 做子串计数，而该 payload 只含 `run_id/turn/tool/effect/is_error/error_code`（**无命令字段**），属方法性零值；「臂 77 次」对不上任何单一口径。**本节点独立复算**（`effects.db` 的 `effect_intent.payload_json`，含 `text.py` 的行数）：**对照 26/27 vs 臂 93/105/118**（v3 代 ctl 45）；方向结论**更强**而非更弱。**引用一律改署可复算口径**（§27.4 纪律 ①）。

**限定 ②（三审 32984 issue ④）**：「tier0 臂洗清墙钟责任」**须加 25775 限定词**——净对照 a2 仍被墙钟**硬切**（`status=wall_timeout`，仅因补丁 10143B 在场判 T）；4094 上臂自身 **2/3**（T completed@1749s/154轮、T wall_timeout@1821s/142轮 `gate=ok`、F wall_timeout@1801s `no_patch`）属**墙钟边缘竞态**；墙钟作为**一般约束**未被免除。

**仍未隔离的残余**：差集 = 全部 6 个 tier0 commits，**S002/S118 与 S083 尚未分格** → 需 **9818633 前后 bisect**（v7 vs v8 恰好单变量隔离折叠族），本循环**未跑**（§28 第 3 条）。

### 21.4 净对照实验的现场与环境披露（节点自报，本节点未逐条复核）

- 起批前 anolis 容器计数 5（<12），本组峰值 1 agent 容器（≤4）；镜像 `sweb.eval.x86_64.matplotlib_1776_matplotlib-25775:latest(841377bcfa1d)` 双端在册；发现 longcat 线在飞批（pid 1033345，41 题含同题 25775）——profile/容器名/out 全不同，零接触。
- 净对照为**单 lane 串行两迭代**（防同题 `next_attempt_index` 竞态），04:44:25 起跑、05:28:07 收口。
- 红队 32960 复核：**事后不可直核**项（起批前快照 pid 1033345 已退出、构建过程细节未目睹）；**可核**项（终态 2 行、121 测试过、worktree 干净、生产位 sha/mtime 未动）。

---

## 22. 候选① 配对臂终局（墙钟边际复验）

### 22.1 设计（红队上轮强制条件，本循环 ask#3）

候选①（`--wall-timeout-secs` 旋钮，墙钟 1800s vs 0→None）第二循环被否的**强制条件**是「**同二进制 wall-on/off 配对臂**」，本循环照办：同二进制 `af-bench-fix4-align2-p00`（sha256 `e6c3fdf5…08a`，分支 `fix4-align2-p00` @ `5d9c94d`，parent=`0dd1a23`）、同 5 题（探针同题集 10081/10908/3187/7462/13877）、同 `--suite swe-v --data-root /tmp/swev-s1 --profile mavis-m31f --host anolis`、`judge_mode=clean`、attempts=1、零判分参数改动；**唯一差 = 墙钟旋钮**。

### 22.2 数据（本节点逐行亲核，§20.2 第 5/6 行）

| 题 | ON（wall=1800） | OFF（wall=None） | 配对读法 |
|---|---|---|---|
| `mwaskom__seaborn-3187` | **F** wall_timeout 54轮 / 1842999ms（终态 elapsed 1841s；`agent.diff` 2724B**补丁在场**；`http_retries`=1） | **T** completed 116轮 / 1513385ms（`agent.diff` 3757B） | **唯一 wall-attributable 翻转** |
| `scikit-learn__scikit-learn-10908` | **T** completed 13轮 / 63440ms | **F** completed 23轮 / 135101ms | **非墙归因**（两侧远未及墙）＝运行方差 |
| `pytest-dev__pytest-10081` | **T** completed 47轮 / 372449ms | **T** completed 27轮 / 190919ms | 稳定 T |
| `sphinx-doc__sphinx-7462` | **F** completed 21轮 / 103705ms | **F** completed 38轮 / 1321685ms | 稳定 F（补丁错误类） |
| `sympy__sympy-13877` | **T** completed 24轮 / 266337ms | **T** completed 49轮 / 595229ms | 稳定 T |
| **合计** | **on_pass = 3/5** | **off_pass = 3/5** | 聚合相等、**构成不同**（ON 过 {10908,10081,13877}；OFF 过 {3187,10081,13877}） |

10 行全部 `judge_mode=clean`、`attempts=1`、infra 行 0；终态 = **1×wall_timeout + 9×completed(TASK_COMPLETE)**；两臂 `policy` 除 `wall_timeout_secs` 外逐行一致（`max_turns=250`、obs 键均缺席）。

### 22.3 墙钟边际终局（复验红队 node 32840 上轮判定）

> **正向边际 = 0**（复验成立）：**无任何题因墙开而过**——sklearn 的 ON=T/OFF=F 翻转，两臂均自然完成（63s / 135s），**与墙无关**，属运行方差。
> **总判定「墙钟边际=0」被推翻**：**负向边际 = 1 题**——`seaborn-3187` ON 臂 `wall_timeout@1841s` 切杀判 F，OFF 臂同题自然 `TASK_COMPLETE@1513s` 判 T，是本轮**唯一** wall-attributable 翻转。
> **机制注记**：OFF 实例 116 轮/1513s（轮均 13.0s）vs ON 实例 54 轮/1841s（轮均 34.1s）；OFF 侧 5 run 全部 <1800s 收尾 ⇒ **1800s 对正常 pace 实例不构成约束，墙只打击慢实例，惩罚经运行间方差兑现**（与红队「方差主导」框架同向）。
> **敏感性**：n=5、题级翻转 2/5（seaborn、sklearn），**单样本不可过度归因**。

### 22.4 事故登记（配对臂首版编排撞名，节点自报 + 本节点亲读事故单）

`/tmp/align3-pair-on/INCIDENT-container-name-collision.txt`（**本节点亲读全文**）：首版编排 = 两臂 4 路同时起（ON×2 + OFF×2），60–90s 内出现 **2 条 SETUP_FAILED**，anolis 上 4 个 `afbench-swev-*` 容器全部 Up —— 容器名生成式 `crates/af-bench/src/swev.rs:57-59` = `afbench-swev-<task>-<profile>`（**不含臂标识**），同题两臂在同一 docker daemon 同名互踩。处置：90s 内 `kill 1262689-92` + 清 4 个孤儿容器 + 删除本轮全部半截产物（`/tmp/align3-pair-{on,off}` 整目录），改**两臂串行、臂内 2 路并行**重起 ⇒ **被杀批与净数据零混行可证**（10 行 infra=0、半截产物已删）。
- ⚠ **本节点发现**：容器名防撞**已有分支** `fix4-container-names` @ **`daef39c`**（worktree `~/workspace/af-wt-cname`，`计划/研究组/容器名防撞-交付.md`：唯一生成处 `swev.rs:57`，**只做分支不换生产位**）——下一循环若要「多臂同题并行」跑批，**先换用该分支二进制**或**臂间串行**，否则必再撞名（§27.4 纪律 ⑦）。

### 22.5 红队/三审订正（已并入本节口径）

1. **措辞失准**（红队 32964 issue ①、三审 32984 issue ④）：seaborn ON 臂**不得写「补丁未就位」**——其 `agent.diff`=**2724B**、apply 干净、**p2p 248/248 全过**，只是 **f2p 0/2 未解**；**切时 `agent.diff`=0B 是 tier0 臂 25775 三跑的形态**，两者**不可混称**（§20.2 第 12 行）。
2. **披露缺口**（红队 32964 issue ②）：ON seaborn 行 `http_retries`=**1**（10 行唯一一次），须与净对照 a2 一样如实披露（不影响 `attempts=1` 成立）。
3. **历史计数**（红队 32964 issue ③）：seaborn-3187 在墙钟期的历史观察为 **3 次 = 2T+1F**（v6-p01 探针 T wall_timeout 56轮/1,937,335ms、v6 续用批 T wall_timeout 59轮/1,819,276ms、pair-on **F** wall_timeout 54轮/1,842,999ms），**不是「3 次全 pass」**；实质点仍成立——OFF 的 completed-pass 是该题 v6 代**首个非 wall_timeout 观察**。
4. **时间窗与事故录内部矛盾**（红队 32964 issue ④、三审 32984 issue ③）：执行员自报 ON 04:47–05:25 / OFF 05:31–06:10，而 10 个 run 的 `agent.diff` mtime 实为 ON ≈04:45–05:22、OFF ≈05:28–06:00（起点各早 2–4 分钟）；事故单现象段署「04:40:4x 起」vs 处置段署「02:49 前后起」→ **须勘误为 04:49 前后**。
5. **不可事后核**（红队 32964 issue ⑤）：容器峰值的逐时点记录未留档，按**未核**计；只能核设计上限（两臂串行 + 臂内 2 路 ⇒ 组峰值 ≤3，<4）。
6. **环境披露**（两臂逐字节同境）：anolis 8123 出口桥（D-18 gost）**已死**（无监听/无进程/无二进制/unit，无 root 不可修复）；两臂 `effects.db` 网络类命令（curl/wget/pip/apt/git clone/ssh）**各 0 条** ⇒ 配对**内部有效性不受影响**。

### 22.6 对 §19.1② 的结清状态

§19.1②（候选①的 wall-off 配对臂）**就探针 5 题而言已放电**（本节数据）；**回归 5 题**（4094/1766/25775/25122/3677）**是否补配对未裁**——红队 32980 issue ⑤ 已登记该歧义，须随 v8 门禁批设计一并裁定（§27.2）。

---

## 23. 差距池第 5 题 sphinx-7462：候选③续测与未翻归因

### 23.1 结果（本节点亲核，§20.2 第 13 行）

| 字段 | 值 |
|---|---|
| 二进制 | `/home/pan-ding/afbuild-shared/af-bench-fix4-align2-p01`（sha256 `6b81bd45…82d7`，本节点亲算 = §10.2 登记值），工作树 `~/workspace/af-wt-align2-p01` @ `588382d`（**status 干净，本节点亲核**），`strings`：`pipefail`=1、`v6-p01`=1 |
| 命令 | `af-bench-fix4-align2-p01 --suite swe-v --data-root /tmp/swev-s1 --profile mavis-m31f-p01 --tasks sphinx-doc__sphinx-7462 --out /tmp/align3-tail`（judge-mode clean，04:35:43 起，04:37:14 落定；run_dir `swev-sphinx-doc__sphinx-7462-mavis-m31f-p01-a1`） |
| 结果 | **`reward=False`（未翻）**、`status=completed`、`scaffold=v6-p01`、`judge_mode=clean`、`attempts=1`、`http_retries=0`、`gate=ok`、`turns=18`、`model_calls=18`、`agent_wall_ms=76111`、`tokens{input 12024, output 5990, cache_read 132391}` |
| 判分 | `verifier_note`：`resolved=false, f2p_success=0, f2p_failure=2, p2p_success=49, p2p_failure=0, tests_collected=51, swebench_version=4.1.0`；`agent.diff`=**1010B** |

**⇒ 探针 p01 臂仍 4/5，sphinx-7462 为唯一未翻题（不变）。**

### 23.2 未翻归因（**节点自报**，轨迹级；本节点未逐 call 复算，见 §28 第 4 条）

执行员（node 32918）读 `effects.db` 27 calls + `normal.jsonl` + `eval.log` + 任务包原文后的定性：

1. **判分失败模式 = 补丁错误类**，与预算/墙钟无关：恰 2 个 F2P 失败（`tests/test_domain_py.py::test_parse_annotation`、`tests/test_pycode_ast.py::test_unparse[()-()]`），49 P2P 全过；`eval.log` 记「2 failed, 65 passed」「py39: FAIL code 1 (1.58s)」。
2. **根因 = 隐藏规格缺口**（与 sklearn-10908 同型，见 §15.1 候选②红队证伪）：agent 容器 `/testbed` **不含 test patch**；判分侧 test patch 新增 ①`_parse_annotation("Tuple[()]")` 必须渲染字面 `'('` `')'` 括号、②`test_unparse` 新参数 `("()","()")`。本跑 `agent.diff` 仅改 `sphinx/domains/python.py` 两处 `result.pop()` → `if result: result.pop()`（消除 IndexError 崩溃），但 `Tuple[()]` 渲染为 `Tuple[]`，且全程 **0 次触碰** `sphinx/pycode/ast.py`。
3. **预算面零接触**：自然 `TASK_COMPLETE`，18 轮 / 76.1s，距 250 轮差 232、距 1800s 墙钟差 ~1724s；与上跑（31 轮 / 609.4s）同败构成**两条独立轨迹同败型**＝稳定失败而非方差。
4. **候选③（pipefail）本题零显现**：`normal.jsonl` tool_events=27、is_error=0（上跑 42/0 同），模型管道 `pytest|tail` 全部真实 rc=0（`28 passed`），**既无被掩蔽的失败也无 `exit:141`** ⇒ pipefail 的反馈面在本题**无可修正对象**。
5. **模型行为非偷懒**：修崩溃 + 跑受影响测试文件（28 passed）+ 4 轮端到端 `sphinx-build` HTML 复现（文档建成无 IndexError）+ `git stash` 基线对照，按 issue 文本验收标准补丁已达标；**唯一不可见的是 test patch 注入的精确渲染断言**（issue 文本只描述崩溃，不含「空 tuple 须渲染成 ()」规格）。

**⇒ 结论（节点自报，本节点采信其结果行）**：`sphinx-7462` 未翻**不属候选③可及失败面，亦不属预算面**，而是「**隐藏测试规格 + issue 验收标准弱于隐藏断言**」的结构性缺口。翻题须「隐藏规格可见化」类机制，**触碰 test-patch 信息 → 有未来信息红线风险**，须另行立项论证，**本循环不作主张**。

---

## 24. v8 处置：采纳裁定已下，采纳序一步未执行

### 24.1 裁定（node 32915 = v8 决策员；红队 32980 + 三审 32984 均 **confirmed**）

> **`adopted=true`，裁定性质 =「采纳为变体（adopt-as-variant），非确认修复」**。工作树 `~/workspace/af-wt-align2`（分支 `fix4-align2-tier0`）**维持 staged 的 `git revert 9818633` 中间态**（**勿 abort、勿 checkout 丢弃**）。

**采纳序（节点原文的 4 步）与当前真实进度（本节点逐项核对）**：

| 序 | 节点定的动作 | 本节点亲查的进度 |
|---|---|---|
| ① | 先订正同批 staged 的 `docs/tier0-adoption.md` 归因段 | ❌ **未做**——staged 文档仍写「归因：4094=采纳面致归（v6 T→v7 F）→ 回退折叠」与「回退后 scaffold v8 … 重跑 5 题门禁见 results 行」（§20.2 第 16 行） |
| ② | `git revert --continue` 提交为 v8 | ❌ **未做**——`git status` 仍显示「您在执行还原提交 9818633 的操作」，`REVERT_HEAD=9818633…` 在位（§20.2 第 8 行） |
| ③ | 新名构建 `~/afbuild-align2/af-bench-fix4-align2-v8`（绝不覆盖生产位 `ecd1a1a0` 与既有命名产物），`build_ok` 以 `cargo test` 为据（§19.2⑦） | ❌ **未做**——`~/afbuild-align2/` 下**无 v8 产物**（§20.2 第 10 行） |
| ④ | 验证跑批 = 同 5 题 S130 门禁重跑（scaffold=v8 自锚定、judge_mode=clean、attempts=1、新目录、≥2 路并行、起批前 anolis 计数 <12 且本组 ≤4、镜像检查用 `docker images \| grep sweb.eval`），4094+25775 k≥2，同报 turns/agent_wall_ms/重读计数，与 §19.1② wall-off 配对臂并列归因 | ❌ **未做**——**全盘无任何 `scaffold=v8` 结果行**（`grep -rl '"scaffold": "v8"' /tmp/*/results.jsonl` → rc=1），`/tmp/align2-tier0-v8-regress` 不存在 |

**⇒ v8 的「采纳」目前只是**纸面裁定**：树未提交、产物未建、门禁未跑。**下一循环必须从采纳序 ① 开始**（§27.2）。

### 24.2 采纳理由与边界（节点自述，本节点复核要点）

- **staged diff 实况**：6 文件 **+21/−221**（`main.rs` 删 `observation_window: Some(5)` 并 bump scaffold v7→v8、`run.rs` 删 `fold_observations` 与请求侧折叠分支、`spec.rs` 删 `Policy.observation_window` 字段、`tests.rs` −138、`smoke.rs`、`docs/tier0-adoption.md`）；**S083/S151 与 `wall_timeout_secs=Some(1_800)` 保留**；`git grep observation_window\|fold_observations -- crates/` **rc=1（零残留）**；机制完整留档于 `9818633`（5 文件 +192/−1，本节点 `git show --stat` 亲核）。
- **烟测**：节点亲跑 `CARGO_TARGET_DIR=~/afbuild-align2 cargo build --workspace`（Finished 6.72s）+ `cargo test -p af-harness -p af-bench -p af-stop` = **126 passed / 0 failed**（7 target）；红队 32980 在隔离 target `~/afbuild-align2` 复跑**逐位一致**（126✓/0✗，产物 sha `d41519b1…f35a`）。**本节点未复跑**（§28 第 1 条）。
- **为什么值得采纳（而非 abort）**：v7 门禁 2/5 触发分支自设 S130 协议「掉过→回退定位」；回退是 protocol sanctioned 的零损失动作；abort 则把分支头退回已知门禁不及格的 v7、浪费已完成的冲突解决、§19.1④ 悬置。**且 v7 vs v8 恰好单变量隔离折叠族**（墙钟/S083/S151 持恒），是 §19.1③ bisect 的关键格。
- **必须先订正的因果（节点原文）**：「4094=采纳面致归（v6 T→v7 F）」**不成立**——两处 ctl 的 `harness.db` `spec_json` 均为 `wall_timeout_secs=None / observation_window=None`（**对照实为 v3 代，名实不符**，§13.1/三审 issue ④）；配对跨三层机制差；且 k2 显示 4094 在臂上自身 **2/3**，结局只取决于补丁是否在 ~1800s 前落树 ⇒ **墙钟边缘竞态**，折叠最多是**放大器假说（未隔离）**。docs 应改述为「回归成立（2/5）、**归因未隔离**、v8=折叠摘除后的隔离臂」。
- **边界**：v8 **恒为研究分支变体**——不换装生产位、**硬换位窗维持不开**（§19.1⑤）。

### 24.3 ⚠ 两条**阻塞级**意见（红队 32980 issues 1–2，三审 32984 issue ② 复认）——**判读规则必须重写，否则验证批读错牌**

1. **原规则第二支已被净对照实测反驳**：原写「v8 仍败 4094/25775（同型 no_patch 墙钟切断）⇒ 墙钟为约束、折叠罪责未证」。**净对照带着同一面 1800s 墙钟且无折叠，25775 照样 2/2 过** ⇒ **墙钟不是 25775 臂败的充分解释**；v8 与净对照的差集恰 = **S083 + S151**（墙钟/无折叠两侧持恒）⇒ **v8 若在 25775 仍败，嫌疑集应为 {S083（该题暴露仅 1 次）、S151（纯元数据）、运行方差}，而不是墙钟**。
   **新判读规则（须带净对照参照臂）**：
   - **v8 过 25775 ⇒ 折叠致**（与净对照同向）；
   - **v8 败 25775 ⇒ 折叠洗清**，嫌疑转 S083/方差；
   - **混合结局**（25775 过而 4094 败）⇒ **按题分判**（25775=折叠致；4094=墙钟边缘竞态，与臂自身 2/3 相容）；
   - **per-task 聚合口径**：k≥2 时以**多数/全部判 T 为过**（k=2 中 1 次 `no_patch` 切断 ≠ 该题败）。
2. **docs 订正稿不得写入「墙钟单因可解释 25775」**（该论证依据的是 ctl 获胜轨迹墙钟 2691s/1961s >1800s，属**反事实**；净对照已给出**前向**答案 2/2 过）。若不订正，第 ① 步「订正归因段」会把**一个新错误**写进台账。

### 24.4 v8 未做的事（不得记为已完成）

- v8 **未提交**、**未构建**、**未跑门禁**、**未 bisect**；§19.1③（9818633 前后 bisect 把 S002/S118 与 S083 分格）**仍未执行**。
- 红队 32980 issue ④ 另记：**二进制级 scaffold 字面量在 `strings -n 2` 下不可分离判别**（v0–v9 均成百出现）⇒ 代际链只能靠「源码两处 `"scaffold": "v8"` + 构建标记 obs=0/fold=0/wall=5/harness_commit=68 + 待验证批结果行自锚」闭合。

---

## 25. 新候选与红队结论

### 25.1 候选台账（node 32915 起草，4 条；红队门审 3 条，1 条起草员自驳）

| # | 名称 | 机制（要点） | target_failure | 红队裁定 |
|---|---|---|---|---|
| C2（候选①位） | **墙钟压力下补丁先行**（预算收尾行为纪律，af 原生） | 在既有墙钟提醒（v8 树 `run.rs:323` WALL_GENTLE_PREFIX / `:332-348` gentle·strong 注入）或 `SWEV_INSTANCE_PROTOCOL`（`main.rs:729`，拼装点 `:990`）**追加一条提示词行为纪律**：终局提醒触发时若工作树尚无候选修复，立即把当前最优部分修复写入仓库文件（即被判 artifacts=工作树 diff），随即转**验证-only** 模式；终局警告后不开新调查线。**零判分接触、墙钟值 1800s 不动**；落地 = 提示文本级 harness 语义变更（scaffold bump v8→v9）+ 新结果目录 + 独立 A/B 臂 | `wall_timeout & gate=no_patch`（25775 三跑全死于此型、4094 原败跑同型）；次目标 fix1 代 0B-diff 类（10081/13877） | **confirmed**（node 32968，4 条 issue） |
| C1（候选②位） | **失败后转向纪律**（B2 纠错风格可迁移件的 af 原生化） | 向 `SWEV_INSTANCE_PROTOCOL` 追加：命令失败（非零退出/is_error）或即将重跑同一命令时，先用一行写明该失败改变了你对问题的哪点理解，再发出一条**不同的**命令；不逐字重跑失败命令、不长篇道歉/反刍；对 `exit:141`（SIGPIPE）改用写文件再回读而非重管道。system prompt 保持一行（af 分工） | 错误触发型打转（4094 型「215 轮膨胀 + 切断时无补丁」）；附带回收 §19.2⑫ 的 SIGPIPE 代价（12 条/5 run） | **confirmed**（node 32972，5 条 issue） |
| C3（候选③位） | **交付物=工作树 diff 自包含**（B2 收尾自包含可迁移件的 af 原生化） | 向 `SWEV_INSTANCE_PROTOCOL` 追加：唯一步骤被评定的东西是完成时仓库工作树的 diff；发 `TASK_COMPLETE` 前用 `git status/diff` 确认修复所需全部改动已落在仓库工作树内（而非只存在于 `/tmp` 脚本、site-packages 或容器状态） | 「仓库外劳作、diff 内空转」类：改动物质化不完整 → 判分只见空或错 diff（fix1 代 0B-diff 全 F 为既有实证） | **confirmed**（node 32976，5 条 issue） |
| B2① | 人格句 | **明确不立项**（备查）：B2 移交单 §四明令不引入 media/citations/人设条款；§3.3 裁定「本题型真正起作用的差是人格/收尾/纠错风格」的原推断已失去证据支撑（经验腿 19-run mcode.log 不可复现、被 8/25 反例否证）；B2 自身未结账（题集 5/19、base 对照臂 0 跑、sympy-16597 在 m31f T→F），机制定位（B4）未闭合 | — | **未门审**（脚本 `vetted.length<3` 上限；起草员自驳，与 B2 §四一致） |

**候选过门数 = 3**（C2/C1/C3）。三条**均无未来信息红线违反**（红队逐条判过：三审 issue ⑥ 复认「no_future_info 生死线无一违反」）。

### 25.2 三候选的共同设计条件（红队三条各提一遍 → **下一循环硬前置**）

> **必须带同二进制 on/off 旋钮**（B2 §四现成形态：两拼装点按旗标选常量、只改 `user_message` 侧，system 保持一行），使 A/B **同二进制只差该条款**；否则 scaffold bump（v8→v9）会把文案效应与**代际差**混在一起——**这是候选①「单臂未跑 wall-on/off 配对」被否的同构教训**。

### 25.3 红队逐条意见（node 32960 / 32964 / 32968 / 32972 / 32976 / 32980，原文照录）

| 节点 | 裁定 | issue 摘要 |
|---|---|---|
| 32960（净对照审） | **confirmed** | ①**中·证据误述**：「text.py 触碰 0/0（计数法=payload 子串）」不成立——按其自述方法复算，控臂 a1/a2 payload 含 text.py = **26/27**（含 receipt 并集 33/33；精确路径 14/14；sed 区域读 10/6）。唯一能得到 0/0 的指标是「**重复区域重读**」（控 0/0 vs 臂 6/8/24）——方向反而更强。**归因结论（2/2 vs 0/3）不依赖该数，不影响 verdict**。②**中·账面数不可复算**：「臂 77 vs 对照 26」对不上任何单一口径（payload+receipt 也仅 43），账面计数脚本未留档；下轮须改署可复算口径。③**中·v8 决策证据缺决策级隔离**：差集=全部 6 commits、S002/S118 未与 S083 分格；**盘上无任何 scaffold=v8 结果行** ⇒ v8 五题门禁未跑，staged docs 中「回退后重跑 5 题门禁见 results 行」属**前瞻未兑现**；v8 doc 的 4094「v6 对照 T/v7 F」一腿建立在 v3 代误标对照且被 k2 反证（v7 对 4094 实为 2/3），**v8 立论应改挂 25775 腿**。④**轻·不可事后核**：起批前快照（docker 计数 5、longcat pid 1033345）事后不可直验（已核当前态无反证）。⑤**轻·佐证定位**：模型自述折叠适应句仅存于 k2-a2 transcript。 |
| 32964（配对臂审） | **confirmed** | ①ON seaborn 措辞失准（「补丁未就位」应改「**补丁在场但未解**」f2p 0/2、p2p 248/0）。②ON seaborn `http_retries=1` 未披露。③历史计数不精确（墙钟期 3 次观察 **2T+1F**，非全 pass）。④时间窗与事故录内部矛盾（建议勘误）。⑤容器峰值逐时点记录未留档，按**未核**计。 |
| 32968（候选①=C2 门审） | **confirmed** | ①**计数句订正**：16 行内 `gate=ok` 切断为 **1T+1F**（原写「2T+1F」跨批并入未披露）；全盘口径 **4T+2F**；实质不对称（no_patch 切断 4/4 全 F）成立。②**引文订正**：第一循环「8/148 completed-but-F」实为「**清洁判 89 行中 27 行 F，终态 completed 8**」= **8/27**（148 是 fix1 m31f 全部 harness.db 终态数，非该率分母）。③**落地须去重**：`run.rs:351` 已有「Do not start new lines of work」、`:342` 已有「Submit your best current fix NOW」、`main.rs:739/747` 已有「submit immediately with your best current fix」+「A run that ends with no code changes is an automatic failure」——C2 真正增量只有「**尚无修复时落盘**」与「**验证-only 模式**」两点，须与既有三条**合成**（避免同轮双注入互相矛盾）。④**A/B 设计条件**：须给同二进制开关；A/B 题集应含 target_failure 签名题（25775/4094）并按订正后 8/27 基线同表监测 completed-but-F。 |
| 32972（候选②=C1 门审） | **confirmed** | ①**中·与既有护栏的重叠分析缺失**（盲区已实测为真）：候选漏读 af 既有「逐字重复命令」硬护栏（v8 树 `main.rs:936` 附近，近 6 条工具历史窗口内同命令 ≥2 次前科即注入提醒）——实测该护栏在 4094 三跑触发 **0 次**（35/12/7 次逐字重复全落在其结构盲区）⇒ 候选覆盖的通道**确为既有护栏 miss**，不是重复采纳；但定稿**必须补这节重叠分析**。②**引文两处不精确**：B2 件号实为「**③纠错风格**」（非②）；「三审 32898 撤证」落点实为 `计划/研究组/调优组-state.md:1110` + B2 §一 P1。③**r1 424/0 一腿当期不可复算**（源 run 目录已清），须标「ledger 亲验、源目录已清不可复跑」。④**A/B 设计条件**（同候选1）+ 主读数必须含 turns/agent_wall_ms/逐字重复率/tool_free_streak 等**轨迹量**（只比 reward 看不到作用面）。⑤**观察·依赖关系**：exit:141 子句的收益以候选③（pipefail）落地为前提，③不采纳时该子句惰性；两者若同批过门，A/B 应**分列臂或预注册联合读法**。 |
| 32976（候选③=C3 门审） | **confirmed** | ①**中·触发点与自带证据终态错位**：C3 挂在「发 TASK_COMPLETE 前」，但其援引的 fix1 代 0B-diff 两例（`bench-fix1-d1-m31f` row46 = 10081 `tool_free_limit@53`/`gate=no_patch`；`bench-fix1-d2-m31f` row52 = 13877 `tool_free_limit@26`）**均不以 TASK_COMPLETE 收场** ⇒ 预完成审计在这两例**永不触发**；真正会触发的是既有无工具轮教学反馈（`run.rs` TOOL_FREE_FEEDBACK，**只催工具调用、不谈交付物落盘**）。定稿须二选一：并入/扩展到 tool-free 反馈路径，或收窄主张并明记 fix1 两例在射程外。②**中·缺口陈述过宽**：空 diff **已有 harness 门**（生产树 `main.rs:806-807` `diff.trim().is_empty() → gate="no_patch"` 如实落行；既有协议还有 `git diff --stat` 自检段）——C3 的真实增量只剩「**完整性/物质化**」一格，定稿须按此收窄。③**轻**：目标模式在 fix1 批次其实**可见弱形式**（13877 fix1-a1 的 69 条命令中 8 条涉仓库外：`cat > /tmp/dbg{,2,3,4}.py`、`ls site-packages`、`curl -o /tmp/master_matrices.py raw.githubusercontent.com`，仓库 diff 终值 **0B**；**强形式（可用修复存在于仓库外）未证**）⇒ 「未读到实证」应改述为「fix1 批次有弱形式模式、强形式未证」。④B2 件号引文错位（C3=「②收尾自包含」）。⑤**A/B 设计条件** + 「Wilmington 手工环境变更」一词不可解（疑为草稿错字），定稿须改通。 |
| 32980（v8 决策审） | **confirmed** | ①**中·（阻塞级）判读规则缺净对照参照**，第二支按原文会误判 → 规则须重写（见 §24.3）。②**中·reason(6)「墙钟单因即可解释两题回归」对 25775 已被实测反驳**；docs 订正稿必须补入净对照事实，否则第①步会把新错误写进台账。③**轻·分数误述**：「4094 在臂上自身 1/3」与其自列两 T 矛盾，实为 **2/3 过**（2T+1F）。④**轻·判读规则缺混合结局分支与 per-task 聚合口径**。⑤**轻·wall-off 配对臂题集歧义**（探针 5 题 vs 回归 5 题）。⑥**轻·scaffold 字面量在 `strings` 不可分离判别**，代际链改由源码/构建标记/结果行自锚闭合。 |

---

## 26. 三审意见（红队·三审，node 32984，step-5-preview，**未参与本循环任何环节**）

**裁定：`confirmed`（6 条 issue）。**

### 26.1 issue 原文照录（摘要，逐条不失真）

1. **【中·证据误述（须订正后再入账）】** 受审记录与 ask 摘要的「对照 text.py 重读 0/0 次 vs 臂 77 次」两个数均不可复算：0/0 出自对 `normal.jsonl` `harness.tool` payload 的子串计数，而该 payload 只含 `run_id/turn/tool/effect/is_error/error_code`（**无命令字段**），对两臂都会得 0，是**方法性零值**；以 `effects.db` `effect_intent.payload_json` 独立复算：净对照 a1/a2 触 text.py = **26/27**（payload+receipt 并集 33/33、精确路径 14/14、sed 区域读 14/11），tier0 臂三跑 = **93/105/118**（精确路径 73/71/97），v3 代对照 = 45（精确 21）。**臂 77 亦对不上任何单一口径**（三审自算精确路径 73、红队复算 payload 73）。归因结论不依赖该数，且正确口径下「折叠→重读税→轮次膨胀」**方向更强**，但**账本引用前必须改署可复算口径**（如「payload 触 text.py：对照 26/27 vs 臂 93/105/118」）。
2. **【中·v8 判读规则的前瞻条件】** `v8=adopt-as-variant` 本身程序正确（staged revert 中间态保留、REVERT_HEAD 在、6 文件 +21/−221、烟测 126✓），但**盘上无任何 scaffold=v8 结果行 ⇒ v8 五题 S130 门禁未跑**；红队 32980 的阻塞级意见成立：规则须改为「**v8 过 25775⇒折叠致；v8 败⇒折叠洗清、嫌疑转 S083/方差**」并补**混合结局分支与 per-task 聚合口径**；**docs/tier0-adoption.md 归因段订正稿不得写入「墙钟单因可解释 25775」**。
3. **【轻·事故录内部矛盾】** `/tmp/align3-pair-on/INCIDENT-container-name-collision.txt:3` 现象段署「04:40:4x 起」，`:11` 处置段署「02:49 前后起」——应为 **04:49 前后**，不影响零混行结论，勘误后入账。
4. **【轻·措辞失准】** 配对臂记录「seaborn-3187 ON 臂补丁未就位」易与 tier0 臂 25775 的 `agent.diff`=0B 形态混淆：ON seaborn `agent.diff`=**2724B**（补丁在场、p2p 248/248 无回归），实质是**墙钟切杀未完成修复**（f2p 0/2）；应订正为「**补丁在场但未解**」。另 ON seaborn `http_retries`=1（10 行唯一）未在证据摘要披露，两路口径应对齐。
5. **【轻·as-of 与账本状态】** 受审记录的载体**尚未入账**：`计划/研究组/对齐组-state.md` 最新节仍是第二循环账（§19.3 末，as-of 2026-10-22 23:4x，:726），第三循环事实只存在于 run 节点记录（`dwf_node` 32915–32980）与 `/tmp/align3-*` 工件（as-of 04:32–07:3x）；**记账员追加时必须带 as-of 并并入上述订正**。另 ask 摘要「tier0 臂洗清墙钟责任」**应加 25775 限定词**——净对照 a2 仍被墙钟硬切（`status=wall_timeout`，仅因补丁 10143B 在场判 T），4094 上臂自身 2/3 属墙钟边缘竞态，**墙钟作为一般约束未被免除**。
6. **【轻·候选门观察】** 3 个候选过门均附中等级订正（C2 计数 scope 16 行 vs 全盘 4T+2F、与既有三条收尾文案去重；C1 漏读 af 既有逐字重复护栏 `main.rs:928-939` 的重叠分析、B2 件号引文错位；C3 机制挂点与自带证据终态错位——fix1 两例 0B-diff 均 `tool_free_limit` 收场而非 TASK_COMPLETE），且**三者都缺同二进制 on/off 旋钮**（候选①「单臂无配对」教训的同构要求）。**no_future_info 生死线无一违反**；入下一循环实施清单时**订正项为硬前置**。

### 26.2 三审独立复核确认的正面项（原文要点）

- **净对照身份链**：sha256 逐位一致（`0c37f56d…`）、`strings` 代际自洽、`worktree list` 显示 `/tmp/af-wt-align2` 检出在 `0dd1a23`、`rev-list --count 0dd1a23..fb7666d`=6、差集 = S083+S002/S118+S151（+docs/style）、运行时 `spec_json.policy` 两跑 wall=1800 且 **obs 键缺席**、`results.jsonl` 两行 `scaffold=v6`/clean/attempts=1/0 infra。
- **归因链成立**：含同一 1800s 墙钟的对照 **2/2 过** vs 臂同题 **3 跑 0/3** 全 wall_timeout 且 `gate=no_patch` ⇒ 「臂败归 tier0 层、S002/S118 头号嫌疑、S083 待 bisect 分格」的链条成立，**红队 §13.2 issue 2 的未隔离状态就此解除**（`state.md:599-605`）。
- **配对臂口径**：两臂同二进制（`e6c3fdf5…`，= `state.md:638` 登记值）、分支 `5d9c94d` parent=`0dd1a23`、ON/OFF `spec_json` 逐行一致、10 行全 clean/infra=0；**on 3/5 vs off 3/5 核实**；**正向边际=0、负向边际=1 题（seaborn）部分推翻 node 32840「墙钟边际=0」总判定**，n=5 单样本已自限；**§19.1② 对探针 5 题已放电**。
- **7462**：`/tmp/align3-tail/results.jsonl` `reward=False`、completed 18 轮/76.1s（p01 二进制 `588382d`、`scaffold=v6-p01`、f2p 0/2），轨迹级归因 = 补丁错误类 + 隐藏规格缺口，与预算/墙钟/pipefail 均无关，与上跑 31 轮/609s 同败型构成两条独立轨迹同败 ⇒ **7462=False 及其归因核实**（对照 `state.md:653`）。
- **v8 处置**：`git status` 明示 revert 中间态、`REVERT_HEAD=9818633…`、staged 6 文件 +21/−221（main.rs 删 obs 且**保留 wall 1800**、scaffold v7→v8；run.rs/spec.rs/tests.rs 摘折叠；docs 同批待订正）、`git grep` 零命中、红队隔离 target `cargo test` = **126✓/0✗**；**adopt-as-variant + 「v8 五题门禁 + wall-off 配对并列归因、v8 恒为研究分支不换装、硬换位窗维持不开」的处置链程序正确**。
- **as-of 与纪律**：四执行员报告与六份红队审均带 as-of；事故披露如实（4 路撞名 90s 内杀批清场、零混行可证）；**生产位 `ecd1a1a0` 全程只读**（红队核 sha/mtime），**gov/他线零触碰**。

---

## 27. 下一循环动作（第三循环 → 第四循环）

### 27.1 循环级决策：**先「实施」，扩测并行且次级**

- **主轴 = 实施（本循环已把纸面清干净，就差落地）**：① **v8 采纳序 4 步**（§24.1，唯一能把 tier0 归因彻底分格的实验）；② **三条过门候选 C2/C1/C3 的同二进制 on/off A/B**（§25.2）。
- **次轴 = 差距池扩测**：**允许**，但**理由只能是「未追平」**——7462 未翻（p01 仍 4/5，OFF 臂仍 3/5），mcode 侧同题 `completed/True`（硬对照）⇒ 差距仍在；**严禁写「无剩余候选」**（§19.2⑭ 教训继续适用）。
- **不作**：`glm5.3f/step5 档案对齐`（脚本 `notCovered` 登记，本循环未开始，**本节不将其列入动作**，避免与前几轮重复挂账）。
- **不扩 D1–D3 全量**（`aligned=false` 未变：af 侧 4/5–3/5 < mcode 5/5）。

### 27.2 硬前置 ①：执行 v8 采纳序（**最优先**，承 §19.1④ + §24.1）

| 序 | 动作 | 纪律/依据 |
|---|---|---|
| V1 | **先订正 staged `docs/tier0-adoption.md` 归因段**：删/改「归因：4094=采纳面致归（v6 T→v7 F）」→ 改述为「回归成立（2/5）、**归因未隔离**、v8 = 折叠摘除后的隔离臂」；补入**净对照事实**（同墙钟无折叠 25775 2/2 过）；**禁写「墙钟单因可解释 25775」**；「回退后 scaffold v8 … 重跑 5 题门禁见 results 行」在门禁跑完前须标为**未兑现**或删除 | 红队 32980 issues ①②；三审 32984 issue ② |
| V2 | **判读规则按净对照参照重写并写入台账**（§24.3 四条：过⇒折叠致 / 败⇒折叠洗清转 S083·方差 / 混合结局按题分判 / per-task 多数或全 T 为过） | 同上 |
| V3 | `git revert --continue` **提交为 v8**（树在 revert 中间态，**裸 checkout 清不掉 `REVERT_HEAD`**）；若要反悔只能 `git revert --abort` | §24.2 |
| V4 | 新名构建 `~/afbuild-align2/af-bench-fix4-align2-v8`（**绝不覆盖生产位 `ecd1a1a0` 与既有命名产物**）；**`build_ok` 以 `cargo test` 编译+通过为据**（不得只署 warm「Finished」）；`~/afbuild-shared` 出陈旧工件（`Event::ToolOk has no field fingerprint`）时先 `touch`/重编相关 crate | §19.2⑦；v8 决策员采纳序③ |
| V5 | **v8 五题 S130 门禁跑批**：scaffold=v8 自锚定、`judge_mode=clean`、`attempts=1`、新目录（如 `/tmp/align2-tier0-v8-regress/`）、**≥2 路并行**、起批前 `ssh anolis` 查容器计数 **<12** 且本组 **≤4**（与其它路共享）、镜像检查用 **`docker images \| grep sweb.eval`**（**禁用 `docker images -q`**）；**4094 + 25775 各 k≥2**；同报 **turns / agent_wall_ms / 重读计数**；**回归 5 题是否补 wall-off 配对**在此批一并裁定（§22.6） | §19.2⑧⑨⑩；红队 32980 issue ⑤；三审 issue ② |
| V6 | **9818633 前后 bisect**（v7 vs v8 单变量）把 **S002/S118 与 S083 分格**——§19.1③ 至今未执行 | §19.1③；§21.3 残余 |
| V7 | v8 **恒为研究分支变体**：不换装生产位、**硬换位窗维持不开**；第 0 档维持「不算采纳成功」 | §19.1⑤；§13.2 issue 1 |

### 27.3 硬前置 ②：三条过门候选的**同二进制 on/off** 实施

| 候选 | 实施硬前置（红队订正项，逐条落为前置） |
|---|---|
| **C2** 墙钟压力下补丁先行 | ① 文案**与既有三条收尾文案去重合成**（`run.rs:342` strong、`run.rs:351` gentle、`main.rs:739/747` 协议条款），**只保留两点增量**：「尚无修复时把最优部分修复落盘」+「转验证-only 模式」；② 删去冗余括注「被判 artifacts=工作树 diff」（属既有披露复述）；③ **同二进制 on/off 旋钮**；④ A/B 题集含签名题 25775/4094，**同表监测 completed-but-F（基线按订正后 8/27）**；⑤ A/B 题集与 wall-off 配对批的判读须分列 |
| **C1** 失败后转向纪律 | ① **补 af 既有「逐字重复命令」护栏的重叠分析**（v8 树 `main.rs:936` 附近：窗口 6 条、≥2 前科即注入）；实测 4094 三跑触发 **0 次**（35/12/7 次重复落在盲区）⇒ 增量通道为真，须写进实施说明；② **订正 B2 件号**（「③纠错风格」）与撤证落点（`计划/研究组/调优组-state.md:1110` + B2 §一 P1）；③ r1「424 事件/0 is_error」须标「ledger 亲验、源目录已清不可复跑」；④ **A/B 主读数含轨迹量**（turns / agent_wall_ms / 逐字重复率 / tool_free_streak），不只 reward；⑤ **监测必要重试率**（「少反刍」可能压制必要重试：`state.md:209` 载 fix1 m31f 有 25 个清洁判 T run 存在 ≥3 次连续非零退出）；⑥ 与候选③（pipefail）的**依赖关系**须处理：`exit:141` 子句的收益以③落地为前提，同批过门则**分列臂或预注册联合读法** |
| **C3** 交付物=工作树 diff 自包含 | ① **触发点二选一**：并入/扩展到 **tool-free 反馈路径**（v8 树 `run.rs:317` TOOL_FREE_FEEDBACK，当前只催工具调用、不谈交付物落盘；fix1 两例 10081 `tool_free_limit@53`、13877 `tool_free_limit@26` 正落此路径），**或**把主张收窄为「TASK_COMPLETE 路径上的不完整 diff」并明记 fix1 两例在射程外；② **收窄「无任何强制最终 diff 审计」表述**——生产树 `main.rs:806-807` 已有 `diff.trim().is_empty() → gate="no_patch"` 空 diff 门（另有协议 `git diff --stat` 自检段），C3 的真实增量只剩「**完整性/物质化**」一格；③ 目标模式改述为「fix1 批次有**弱形式**（仓库外调试/取料 + 修复未落盘，13877 fix1-a1 69 命令中 8 条涉仓库外、仓库 diff 终值 0B），**强形式（可用修复存在于仓库外）未证**」；④ **订正 B2 件号**（「②收尾自包含」）；⑤ 「Wilmington 手工环境变更」一词改通；⑥ 同二进制 on/off 旋钮 |
| **共同** | 三条候选**均**须：同二进制 on/off 旋钮（B2 §四形态：旗标选常量、只改 `user_message` 侧，system 保持一行）；**scaffold bump 只作结果行锚定，不得代替配对**；零判分路径改动；`build_ok` 以 `cargo test` 为据；A/B 两臂**同题集、同判分、同环境**，结果表**逐行标出处 + 基建/模型败分桶**；题级通过集合判定（n 小须披露） |

### 27.4 计量与纪律修正（可立即执行；含本轮新增 3 条）

| 序 | 动作 | 依据 |
|---|---|---|
| ① | **重读/文本计数一律改署可复算口径**：`effects.db` 的 `effect_intent.payload_json` 触 `text.py` = **对照 26/27 vs 臂 93/105/118**（v3 代 ctl 45）；**作废**「对照 0/0」「臂 77」两数；可复算的重复重读口径为「重复区域重读 臂 6/8/24 vs 控 0/0」 | 红队 32960 issues ①②；三审 32984 issue ①；**本节点已独立复算**（§20.2 第 11 行） |
| ② | **cutting 计数订正**：`gate=ok` 切断在 tier0 16 行 scope 内为 **1T+1F**（原写 2T+1F 跨批并入未披露），**全盘 4T+2F**；`no_patch` 切断 4/4 全 F 不变 | 红队 32968 issue ① |
| ③ | **completed-but-F 基线引文**：改「8/27」（清洁判 89 行中 27 行 F、其中终态 completed 8），**不得写 8/148** | 红队 32968 issue ②；`state.md:183` |
| ④ | **两臂/两形态的「补丁形态」必须分称**：0B（臂 25775 三跑，切时无产物）vs 「补丁在场但未解」（pair-on seaborn 2724B、f2p 0/2、p2p 248/0） | 红队 32964 issue ①；三审 issue ④ |
| ⑤ | **`http_retries` 须逐行披露**（10 行中 ON seaborn 为唯一 1 次；净对照 a2 亦为 1），两路口径对齐 | 红队 32964 issue ②；三审 issue ④ |
| ⑥ | **seaborn 历史观察数**：墙钟期 3 次 = **2T+1F**（非「全 pass」）；OFF 的 completed-pass 是该题 v6 代首个非 wall_timeout 观察 | 红队 32964 issue ③ |
| ⑦ | **容器名无臂标识 ⇒ 多臂同题并行必撞名**（`swev.rs:57-59` = `afbench-swev-<task>-<profile>`）：下一循环若要多臂并行，**先换 `fix4-container-names` @ `daef39c` 分支二进制**，否则**臂间串行**；事故单「04:40:4x vs 02:49」须勘误为 **04:49 前后** | 本节点亲读事故单 + `计划/研究组/容器名防撞-交付.md`；三审 issue ③ |
| ⑧ | **4094 臂自身成绩**一律写 **2/3 过（2T+1F）**，不得写「1/3」 | 红队 32980 issue ③ |
| ⑨ | **差距池现算现引**（本节点 07:0x 已复算，与 10-22 23:4x 逐位一致、**自 23:4x 起未漂移**，9 个源文件 mtime 最新为 10-22 15:51:47）：**剔 S 74 后池 = 13 题**（D1：10081/10908/sphinx-10323/10466/10614/11510；D2：seaborn-3187/7462/sympy-13877/14248/17318；D3：django-14011/pylint-6386），其中**仅 2 题有清洁认证 F**（`seaborn-3187`、`django-14011`），其余 11 题为 **arm 回退值**；**§11.2 所称「13 题中 5 题有清洁认证 F」另列的 `django-10999`/`requests-2317`/`django-10097` 不在本口径的 13 题池内 → 该句须在下一轮核对口径**；扩测题集**必须现算重取**，禁用 `/tmp/gaptasks.json` | 本节点亲算（§20.2 第 14 行）；§11.2；三审 issue ②（账本纪律） |
| ⑩ | **§19.2 全条继续适用**：⑦`build_ok` 以 `cargo test` 为据；⑧镜像检查用 `docker images \| grep sweb.eval`（禁 `-q`）；⑨探针表逐行标出处 + 基建/模型败分桶；⑩题目级通过集合判定 + 披露邻组「结构性无 diff」排除集；⑪台账勘误（S083 阈值单位 12KB、S160 列位）；⑫SIGPIPE 代价登记；⑬**候选② 仍不实施**；⑭扩测理由只能是「未追平」 | §19.2 全表原样延续 |
| ⑪ | **本轮实测的第三方纪律**：两臂逐字节同境（anolis 8123 出口桥已死、无网络命令）须在结论中披露；红队/三审**自报 as-of 与盘面时钟不一致**（自报最晚 07:5x vs DB `time_updated` 06:59:10）⇒ **时间一律以 DB 时刻 + 工件 mtime 为准** | §22.5；§20.1 末条 |
| ⑫ | **扩测规模建议**（本节点建议，非既有裁决）：以现算池中**未探的 8 题**为候选（`sphinx-10323`/`10466`/`10614`/`11510`、`sympy-14248`/`17318`、`django-14011`、`pylint-6386`），优先 D1 的 sphinx 四题与 D3 两题（`django-14011` 为**清洁认证 F**，归因价值最高）；**每题须逐题标「清洁认证 / arm 回退」**；**扩测不得与候选 A/B 同批并行**（判读须分列） | 本节点基于 §20.2 第 14 行的建议；具体题集下一轮现算重取 |

### 27.5 下一循环建议的节点分工（可续用）

沿用本循环的编排优点：**跑批并行、门审串行**：①「v8 执行员」（V1–V5 独占）+ ②「候选实施员×3」（C2/C1/C3 各自同二进制 on/off）**并行**；③「红队·第四循环」（串行门审 v8 判读 + 三候选 A/B 口径 + 账本订正是否落地）；④「红队·三审」（未参与环节）；⑤「状态记账员」（落账）。**纪律**：跑批 >2 题必拆 ≥2 进程；臂间串行或换 `daef39c` 二进制；起批前 anolis 计数 <12、本组 ≤4；gov 与他线零接触。

---

## 28. 本节明确未做的事（供下一轮判断可信边界）

1. **未跑** `cargo build` / `cargo test` / `cargo fmt` / `clippy` —— 本节所有「126✓/0✗」「build_ok」字样**均署红队/实施节点**（32915/32980），本节点未复跑。
2. **未跑**任何判分、任何探针题、任何对照补测、**v8 五题门禁**、任何 k2 复跑 —— 本节点只读了 `results.jsonl` 与 `harness.db`（`mode=ro` 只读）。
3. **未做** 9818633 前后 bisect（§19.1③）、**未做** v8 提交/构建/门禁（§24.1 采纳序 ②③④ 全部未执行）。
4. **未逐 call 复算** 7462 的轨迹级归因（隐藏规格缺口、0 次触碰 `sphinx/pycode/ast.py`、仓库外弱形式）——§23.2 全部为 node 32918 自报；本节点只复核了结果行字段（§20.2 第 13 行）。
5. **未读** 模型侧 `trace.db` 工具输出原文；未复算 4094 三跑的逐字重复计数（35/12/7）、未复算 p01 的 260 事件/62 is_error/12 条 `exit:141` —— 均为节点自报（32972 复算、§19.2⑫ 登记）。
6. **未复核** 净对照/配对臂的**起批前环境快照**（anolis 容器计数、longcat pid 1033345、镜像在册）与**构建过程细节**（cargo clean 五 crate、Finished 3.71s）—— 红队自陈未目睹/事后不可核。
7. **未处理** `/tmp/gaptasks.json` 的归属（仍按三审 issue ② 登记为禁用件）。
8. **未裁决** §19.1② 的「回归 5 题是否补 wall-off 配对」与 v8 验证批的题集设计 —— 属 V5 的设计项，记账员不代裁。
9. **未代裁** 三个候选的**实施优先级排序**（本节只给硬前置，不排期）—— 属红队/运营者裁决。

---

*第三循环账毕。本节由状态记账员（MiniMax-M3.1-Flash-Preview）于 2026-10-23 07:0x CST 追加写入 `计划/研究组/对齐组-state.md`；下一循环请从 §21.3（净对照终局与残余未隔离项）、§24.3（v8 判读规则重写）、§25.3（三候选红队订正）、§27.2/§27.3（v8 采纳序 + 候选同二进制 A/B 硬前置）开始；引用本节任何数字须带 as-of，并**不要**引用「对照 0/0 vs 臂 77」这一已被订正的数对。*

---

# 第四循环（v8 采纳闭环 + 候选实施 + 探针）· 账本增补

> 本节是**追加节**，§0–§28（第一/第二/第三循环账）一字未改。写作时点 **2026-10-23 12:5x CST**；本节所有数字带 as-of，严格区分「**本节点亲跑/亲读**」与「**节点自报**」。
> 工作流 run：**`dwfrun-981b3ebc-b3a2-4019-a436-2390868e1538`**（名「研究组①对齐组·第四循环」，`time_created`=2026-10-23 07:06:08，`time_updated`=2026-10-23 12:54:52，`status=running`，`spent_tokens`=49,336,811——`dwf_run` 表，**本节点 12:5x 亲查**）。
> 流程脚本：`.zcode/workflow-drafts/研究组1-对齐组-四循环.dwf.ts:1-152`（标题行自述「第四循环（v8 采纳闭环 + 新候选实施）」）。编排：`v8 采纳复验 ∥ 新候选实施`（并行）→ `红队串行（v8 采纳审+实现审）` → `探针（过审候选，拆路并行）` → `三审与落账`。脚本 COMMON 纪律（`:41-43`）：未来信息零引入 / 测量语义零改动 / gov 不碰 / 密钥零明文 / 他线在飞不动 / anolis 容器 <12 全厂、本组 ≤4 / **研究二进制无 D-37 前缀 → 同题跨臂并发必用闸门时序或串行隔离** / 结论带证据 + as-of / 卡住升级提问。
> **与 §27 的对账**：§27.2 硬前置①（v8 采纳序 V1–V7）中 **V1/V2/V3/V4/V7 已执行**、**V5 部分执行**（`:1012` 要求「4094 + 25775 各 k≥2」，实跑 25775 k2、4094/25122/3677/1766 各 k=1）、**V6 未执行**（`:1013` 的 9818633 前后 bisect 未跑）；§27.3 硬前置②中 **C2 落地并已跑同二进制 A/B**、**C1 落地但未跑 A/B**、**C3 未实施**（脚本 `const implBatch = cands.items.slice(0, 2)` 只取前 2 条候选）；§27.1 次轴「差距池扩测」**未发生**（探针题集是脚本硬编码的 5 题，未按 §27.4⑨ 现算重取）。
> **红线核查（本节点亲跑）**：生产位 `af/target/debug/af-bench` sha256 `ecd1a1a0caf178240a2d70026a2dc6fe76ae7890678b9d1542fb8f9c75b5d331`、mtime **2026-10-23 00:53:54** 未变（与第三循环账 §20.2 第 2/3 行登记逐位一致）⇒ gov / 生产面零接触成立；三枚新二进制均为**新名**（`~/afbuild-shared/af-bench-fix4-align2-v8` / `-align4-p0` / `-align4-p1`），**未覆盖任何既有产物**（`ls -la ~/afbuild-shared` 亲核：p00 10-22 21:13、p01 10-22 21:18、netctl 10-23 04:42 mtime 全未动）。

## 29. 第四循环节点账与本节点自测

### 29.1 节点账（13 节点 = 12 completed + 1 running〔本节点 33082〕；8 actor）

| 节点 | actor | 角色（脚本 persona） | 产出 | 状态 | DB 起止 |
|---|---|---|---|---|---|
| 32991 | actor#1 v8 采纳执行员（GLM-5.3-Flash） | v8 回退正式采纳与复验：commit 化 staged v8、构建、25775 复验 + 4 题回归抽查、定新基线 | `V8Adoption`：`adopted=true`、`commits=1`、`branch=fix4-align2-v8 @ 50ba8a8`、`baseline=fix4-align2-v8 @ 50ba8a8` | completed | 07:06:08→07:41:11 |
| 32992 | actor#4 候选读取员（M3.1-Flash） | 从本账第三循环节读出过门 3 候选原文（附行号出处） | `items[]`=C2/C1/C3 三条（原文 + 出处 :945–:952/:954–:956/:982） | completed | 07:06:08→07:06:38 |
| 32996 | actor#2 候选实施员甲（GLM-5.3-Flash） | 实施 **C2**（墙钟压力下补丁先行）+ 同二进制 on/off A/B | `Implementation`：`branch=fix4-align4-p0`、`build_ok=true`、`binary=/home/pan-ding/afbuild-shared/af-bench-fix4-align4-p0` | completed | 07:06:38→10:02:00 |
| 32997 | actor#3 候选实施员乙（GLM-5.3-Flash） | 实施 **C1**（失败后转向纪律） | `Implementation`：`branch=fix4-align4-p1`、`build_ok=true`、`binary=…/af-bench-fix4-align4-p1`；**未跑任何批次** | completed | 07:06:38→07:26:09 |
| 33023 | actor#5 红队·四循环（step-5） | v8 采纳审（复验口径 + 代际自证） | **confirmed**，9 条 issue | completed | 10:02:00→10:26:00 |
| 33027 | actor#5（同 actor，seq=1） | C2 实现审（单点差异 + 未来信息红线） | **confirmed**，4 条 issue | completed | 10:26:01→10:33:25 |
| 33031 | actor#5（seq=2） | C1 实现审 | **confirmed**，5 条 issue | completed | 10:33:25→10:41:28 |
| 33035 | actor#6 探针执行员甲（GLM） | 探针轮 1：C2-ON 臂 5 题差距池 | `af_pass=4`、`mcode_pass=5`、`clean=true`、`results_path=/tmp/align4-probe-p0/results.jsonl` | completed | 10:41:28→11:37:50 |
| 33036 | actor#6（seq=1） | 探针轮 2：C1-ON 臂 5 题差距池 | `af_pass=4`、`mcode_pass=5`、`clean=true`、`results_path=/tmp/align4-probe-p1/results.jsonl` | completed | 10:41:28→12:39:05 |
| 33070 | actor#5（seq=3） | 探针轮 1 审（亲读行数/reward/clean） | **confirmed**，4 条 issue | completed | 12:39:05→12:40:59 |
| 33074 | actor#5（seq=4） | 探针轮 2 审 | **confirmed**，4 条 issue | completed | 12:40:59→12:42:32 |
| 33078 | actor#7 红队·三审（step-5，**未参与本循环任何环节**） | 三审：v8 闭环证据链 / 候选实现与探针口径 / as-of 纪律 | **confirmed**，8 条 issue | completed | 12:42:32→12:54:52 |
| 33082 | actor#8 状态记账员（本节点，M3.1-Flash） | 落账 | 本节 | **running** | 12:54:52→ |

- **人物线 8 actor**（`dwf_actor` id 19435/19437/19438/19439/19453/19456/19501/19504）：actor#1–#3 = GLM-5.3-Flash（v8 采纳员、候选实施员甲/乙）；actor#4 = M3.1-Flash（候选读取员）；actor#5 红队·四循环 = step-5（**1 个 actor 承担 5 次串行门审**）；actor#6 探针执行员 = GLM；actor#7 红队·三审 = step-5；actor#8 = 本节点。
- **脚本分支位与实际调用**：脚本 `implBatch = cands.items.slice(0, 2)` ⇒ **C3 结构性未被调用**（第三条候选起草过门但未进入实施批；与第三循环 §25.1「3 条过门」不矛盾，是编排切片所致）。
- ⚠ **节点自报 as-of 与盘面时钟**：本循环节点的 `time_updated` 上界为 12:54:52（DB），三审 33078 自报 as-of「12:4x」、红队 33074 自报「12:4x」，**均与 DB 时刻相容**（第四循环未见第三循环那种自报超钟 30–50 分钟的矛盾，§27.4⑮ 纪律本轮无违例）。

### 29.2 本节点自测（**本节点亲跑/亲读**，全部在本会话执行）

| # | 检查 | 命令 | 结果 | 判读 |
|---|---|---|---|---|
| 1 | 第四循环 run / 节点 / actor 账 | `python3` 读 `~/.zcode/cli/db/db.sqlite`（`mode=ro`）`dwf_run`/`dwf_node`/`dwf_actor` | run `dwfrun-981b3ebc`（07:06:08 起、running、spent 49,336,811）；**13 节点 = 12 completed + 1 running（33082）**；8 actor | 与 §29.1 表逐行一致 |
| 2 | 四枚二进制 sha256 | `sha256sum af/target/debug/af-bench ~/afbuild-shared/{af-bench-fix4-align2-v8,af-bench-fix4-align4-p0,af-bench-fix4-align4-p1}` | `ecd1a1a0…5b331`（生产位）/ `a9aa479d…80e` / `b8dde284…fcd4c` / `73390f93…457a` | 与 32991/32996/32997 自报**逐位一致**；生产位与第三循环登记一致 |
| 3 | 工作树落点 | `git worktree list` | `af @94cd192 [guardrail-fix2]`（生产）、`af-wt-align2 @50ba8a8`、`af-wt-align4-p0 @6dccda5`、`af-wt-align4-p1 @8c670f2` | 生产树未动；无 align4-p2（C3）工作树 |
| 4 | v8 commit 形态 | `git -C ~/workspace/af-wt-align2 show --stat 50ba8a8` | **6 files changed, 30 insertions(+), 221 deletions(-)**（main.rs/run.rs/spec.rs/tests.rs/smoke.rs + docs/tier0-adoption.md） | 与 32991 自报逐位一致 |
| 5 | v8 与净对照差集 | `git diff --stat 0dd1a23 50ba8a8 -- crates/` | **3 files**：main.rs +51、swev.rs +1、tb.rs +211 | **S083（tb.rs）/S151（main.rs）在场、折叠相互抵消**成立 |
| 6 | 折叠残留零命中 | `git grep -n observation_window 50ba8a8 -- crates/`；同 `fold_observations` | 两次 **rc=1**（零残留） | 折叠摘除在源码层成立 |
| 7 | scaffold 自锚 | `git grep -n '"scaffold": "v8"' 50ba8a8` | `main.rs:1053`、`main.rs:1124` | 与账本 §24.4 预期一致 |
| 8 | 候选实施 commit 形态 | `git show --stat 3a8db9a`（p0）/ `6dccda5`（p0）/ `8c670f2`（p1） | 3a8db9a=**5 files +227/−16**（无 judge.rs/swev.rs/tb.rs）；6dccda5=main.rs +6/−1；8c670f2=**2 files +207/−3**（main.rs +119 + docs/c1-redirect-discipline.md +91） | 判分路径零触碰（两 diff 均不含 judge.rs/swev.rs/tb.rs） |
| 9 | 代际自证（strings） | `strings -n 4 <四枚二进制>` 关键词计数 | v8：observation_window **0** / fold_observations **0** / wall_timeout 5 / wall-patch-first 0 / redirect-discipline 0 / wall-timeout-secs 0 / pipefail 0；p0：wall-patch-first **1** / verification-only **2**；p1：redirect-discipline **2**；netctl 对照全 0 | **v8 = 净对照 + S083/S151 − 折叠**；两候选旋钮**互不混入**；四枚均无候选①②机制（wall-timeout-secs / pipefail 皆 0） |
| 10 | 26 行结果逐行解析 | `python3` 解析 `/tmp/align4-v8/results.jsonl`(6) + `/tmp/align4-c2/{ab-on,ab-off}/lane-{sig,probe}/results.jsonl`(10) + `/tmp/align4-probe-p{0,1}/results.jsonl`(5+5) | 逐行 task_id/reward/status/turns/wall_ms/gate 全部还原，见 §30.2 / §31.1 / §32.2 表 | 复现 32991/32996/33035/33036 自报；**并订正三审 1 处 OFF 计数（§34①）** |
| 11 | 运行时 policy（harness.db 只读） | `python3 sqlite3 file:…?mode=ro` 读 `run_row.spec_json` | v8 25775：wall_timeout_secs **1800** / observation_window **缺席** / max_turns **250** / 无候选键；probe-p0 与 c2-on：**wall_patch_first=true**；c2-off 与 probe-p1：该键**缺席**；probe-p1 无 `redirect_discipline` 键 | 折叠已摘除（obs 缺席）成立；**ON/OFF 旋钮在 spec 级可分**；C1 旋钮仅行级自锚（与红队 33074 issue② 一致） |
| 12 | 补丁形态（0B vs 补丁在场未解） | `stat -c %s <run_dir>/agent.diff` | c2-ON 25775=**6926B**、c2-OFF 25775=**8503B**、probe-p0 7462=**1683B**、probe-p1 7462=**1168B** | **本批零「切时 0B」墙杀**；7462 两臂均「补丁在场但未解」（f2p 0/2），形态与 §22.5 纪律④ 一致 |
| 13 | 批时序 / as-of 工件 | `cat /tmp/align4-v8/BATCH-{START,END}-asof.txt`、`/tmp/align4-probe-p{0,1}/BATCH-{START,END}-asof.txt`、`ls /tmp/align4-c2/` | v8 **07:15:55→07:40:07**；probe-p0 **10:53:18→11:37:27**；probe-p1 **11:39:30→12:38:58**；**C2 A/B 批无 BATCH-START/END-asof.txt**（仅 launcher.log） | 三审 issue④「as-of 工件不齐」**本节点复核成立** |
| 14 | 7462 立项文档是否存在 | `find . -name "*立项*"`；`grep -rn "隐藏规格" --include="*.md" .` | `find` **零命中**；`grep` 命中仅 `计划/研究组/对齐组-state.md`（:626/:711/:890/:895/:1037）、`状态观测/巡检日志.md:309`、`状态观测/业务目的章程.md` | **第四循环未产出任何 7462 立项论证文档**（§35.3） |
| 15 | C3 是否留痕 | `git -C ~/workspace/af-wt-align4-p0 branch -a | grep align4` | 仅 `fix4-align4-p0` / `fix4-align4-p1` | **C3 无分支、无二进制、无工件** |

## 30. v8 采纳闭环（commit / 构建 / 复验 / 基线变更）

### 30.1 采纳序 V1–V4 的落地（**本节点亲读工件 + 采信节点自报**）

| 采纳序（§27.2 `:1006-1011`） | 落地形态 | 证据 |
|---|---|---|
| **V1** 先订正 staged `docs/tier0-adoption.md` 归因段 | 与代码回退**同 commit** 落地：删「4094=采纳面致归（v6 T→v7 F）」，改述「4094=墙钟边缘竞态、臂自身 2/3；v6 对照实为 v3 代名实不符」；前瞻句改标「门禁重跑在本 commit 时点尚未兑现」；补净对照事实；写明禁「墙钟单因可解释 25775」+ 四条判读规则 | 32991 evidence；本节点亲核 `git show --stat 50ba8a8` 含 `docs/tier0-adoption.md | 21 ++++--`（§29.2 第 4 行） |
| **V2** 判读规则按净对照参照重写 | 判读按 §24.3（`:928` 起）「**v8 过 25775 ⇒ 折叠致**」执行；**本节点采信该规则在本循环的适用**（v8 = v7 − 单 commit 9818633 = 单变量） | `:928`；32991/33078 均按此判读 |
| **V3** 提交为 v8 | **commit `50ba8a8`**（`fix4-align2-v8: revert 9818633（摘 S002/S118 观测折叠，scaffold v7→v8）`，07:13:51），parent=`fb7666d`；`REVERT_HEAD` 已清、树干净 | 本节点亲核 `git log --oneline -3`（§29.2 第 3 行）+ `git show --stat` |
| **V4** 新名构建、`build_ok` 以 cargo test 为据 | `cargo clean -p af-bench/af-harness/af-stop`（清 ~1.5GB）→ `CARGO_TARGET_DIR=~/afbuild-shared cargo test -p af-harness -p af-bench -p af-stop` = **126 passed / 0 failed**（**32991 自报**）→ `cargo build -p af-bench` → `~/afbuild-shared/af-bench-fix4-align2-v8`（sha256 `a9aa479d…`，mtime 07:14:29） | **⚠ 本节点未复跑 cargo test**（§36 第 1 条）；二进制身份本节点亲验（§29.2 第 2 行） |

### 30.2 复验读数（**本节点逐行亲核**，工件 `/tmp/align4-v8/`，6 行、基建行 0、零 wall_timeout、零 judge 重试行）

| task | 臂/轮次 | status | reward | turns | agent_wall_ms | gate | http_retries | 判分（f2p/p2p/tests） |
|---|---|---|---|---|---|---|---|---|
| `matplotlib__matplotlib-25775` | a1 | completed | **T** | 41 | 458,495 | ok | 0 | 7/0 · 89/0 · 96 |
| `matplotlib__matplotlib-25775` | a2 | completed | **T** | 59 | 604,655 | ok | 0 | 7/0 · 89/0 · 96 |
| `matplotlib__matplotlib-25122` | 抽查 | completed | **T** | 37 | 812,694 | ok | 0 | 12/0 · 2476/0 · 2488 |
| `pydata__xarray-3677` | 抽查 | completed | **T** | 21 | 403,217 | ok | 0 | 1/0 · 21/0 · 22 |
| `pydata__xarray-4094` | 抽查 | completed | **T** | 38 | 197,289 | ok | 0 | 1/0 · 862/0 · 863 |
| `psf__requests-1766` | 抽查 | completed | **F** | 44 | 991,812 | ok | 0 | **0/6** · 45/34 · 85 |

- **25775 复验 = 2/2 过** ⇒ 按 §24.3 规则第一条「v8 过 25775 ⇒ 折叠致」→ **S002/S118 观测折叠罪责成立**，第三循环「25775 归因=tier0 致」**闭环**。形态佐证（33078 evidence ⑨）：v7 臂同题 0/3 全 `wall_timeout` 且切时 `agent.diff`=0B（153/172/225 轮），v8 两跑**自然完赛**（458s/605s，远未触 1800s 墙），turns 41/59 与净对照 51/61 同款。
- **4 题抽查无退步**（比较基线 = tier0 臂自身历史）：25122/3677 持平 T；4094 T@197s 优于臂均值；**1766 F 为预存失败**（v7 臂 0/3 全 F、v3 代无折叠无墙钟对照亦 F completed）⇒ 非 v8 引入。**但按 S130 原始「5 题应全过」严格门槛，1766 单题仍不过**——如实计入（32991 spot_check 自述与 33078 ⑬ 一致）。
- **⚠ V5 未完整执行**（§27.2 `:1012` 要求「4094 + 25775 各 k≥2」）：本批 25775 k2 达成，**4094/25122/3677/1766 均 k=1**。红队 33023 issue① 指出：4094 恰是臂历史 2/3（两次 T 均为墙钟边缘）的题，单次 T@197s 无法把「折叠摘除效应」与「墙钟边缘竞态方差」分开；**须补跑 4094 k2，或由运营者显式裁定口径下调**。
- **本批其余披露项**（红队 33023 issue⑤/⑦）：25122 判分发生 1 次 judge 退出重试（host 侧 urllib3 网络错，5s 后成功；行级 `http_retries=0`、judge note 完整）；`containers-at-launch.txt` mtime 晚于 BATCH-START ~60s，「起批前容器 0」无独立工件直证；批后 xarray-4094/3677 镜像已不在 anolis（anolis GC 及他线活动所致，**红队未触碰任何镜像**）。

### 30.3 基线变更与生产位状态

| 项 | 变更前（第三循环账） | 变更后（第四循环，as-of 12:5x） | 证据 |
|---|---|---|---|
| **研究基线** | 净对照 `0dd1a23`（内容基线） | **`fix4-align2-v8 @ 50ba8a8`**（= fb7666d − 折叠 commit 9818633 + 归因段订正） | 32991 `baseline` 字段；本节点亲核 worktree HEAD |
| **生产位** | `ecd1a1a0`（af @ 94cd192，mtime 10-23 00:53:54） | **不变**（sha256 与 mtime 逐位复核，§29.2 第 2 行） | V7 维持：v8 恒为研究分支变体、硬换位窗维持不开 |
| **scaffold 代际** | v7（tier0 臂） | **v8**（v8 批）/ **v9**（两候选臂，scaffold bump 仅作结果行锚定） | 结果行 `scaffold` 字段（本节点逐行亲核） |
| **候选实施基线** | — | p0 基线 = `b1bd179`（v8 crates/ 内容逐字节一致，docs 归 v8 采纳员）；p1 基线 = **直接继承已提交的 `50ba8a8`**（而非复刻 staged 态） | 32996/32997 自报；红队 33027 亲核 `git diff --stat b1bd179 50ba8a8 -- crates/` 输出空、33031 亲核 `git rev-parse 8c670f2^`=50ba8a8 |

### 30.4 红队 v8 采纳审（node 33023，10:02:00→10:26:00，**confirmed**，9 条 issue）

1. **【中】复验口径对账本 V5 不齐**：4094 仅 1 跑；「k2 + 4 题抽查」本身即对 V5 的下调，未经追认；4094 单次 T@197s 分不开「折叠效应 vs 墙钟边缘方差」⇒ 补 4094 k2 或运营者显式裁定。
2. **【轻】重读计数未报**：V5 要求同报 turns / agent_wall_ms / **重读计数**，record 只报前两项；红队独立复算补上——v8 臂 25775 触 `text.py` = **26/33**（净对照 26/27、折叠态 v7 臂 93/105/118）⇒ **结论获支持但 record 缺项**。
3. **【轻】代际自证映射错误**：record 写「fingerprint=19 = S083 在场」**错**——19 是 r1 指纹刹车标记（净对照同为 19 而无 S083）；S083 在场应由 `.af-outputs=2`/`externalize=8` 佐证（净对照 0/0）。**结论不变，映射须订正**。
4. **【轻】同 commit 内代码注释残留旧归因**：`50ba8a8` 的 `crates/af-bench/src/main.rs` 结果行注释仍写「xarray-4094 在 v6 对照臂 resolved=true 而 v7 resolved=false——采纳面致归成立」＝红队 32980/三审 32984 判定不成立的归因腿；docs 已订正、**代码注释未同步**（注释不进二进制，不影响测量语义）。
5. **【轻】judge 重试事件未披露**：lane-b.log 载 25122 判分第 1/3 次失败后 5s 重试成功（见 §30.2 末条）。
6. **【轻】环境快照时点**：`containers-at-launch.txt` 晚于起批 ~60s，「起批前容器 0」无独立直证。
7. **【观察】镜像现况**：批后 xarray-4094/3677 镜像已不在 anolis（GC + 他线活动；红队未触碰）。
8. **【观察】共享 target 陈旧工件 Hazard**：`~/afbuild-shared` 跨 worktree 共享时，后建 worktree 会误复用前一 worktree 工件——红队在 p0 树跑 `cargo test` 即触遇 **E0560**（af-harness Policy 无 `wall_patch_first`，链到 07:23 p1 构建的 rlib）；按 §27.2 V4 药方 touch 后重编恢复。**预存结构性 Hazard，非本记录引入**。
9. **【观察】C2 A/B 读数**：ON 3/5 vs OFF **4/5**，签名题 25775 在 ON 臂翻 F——候选门审须诚实读数，不得因「单点差异成立」推定候选有效。

## 31. 候选实施与红队结论

### 31.1 C2（候选①位·墙钟压力下补丁先行）→ 分支 `fix4-align4-p0` @ `6dccda5`

- **落地形态**（32996 自报 + 红队 33027 四层复核 + 本节点亲核 commit 形态）：基线 `b1bd179` → C2 实施 `3a8db9a`（5 files +227/−16，**不含 judge.rs/swev.rs/tb.rs**）→ profile 别名 `6dccda5`（`mavis-m31f-c2`，端点全同仅容器名后缀）。
- **同二进制 on/off 旋钮落地**：`--wall-patch-first`（B2 §四形态：拼装点按旗标选常量——`run.rs` 提醒两处 + `main.rs` 协议一处，**只改 user_message 侧，system 一行不动**）；`Policy.wall_patch_first` 穿线，**false 不序列化 ⇒ OFF 臂 spec 与 v8 同形**（本节点亲核：c2-off 的 harness.db 该键缺席、c2-on 为 true，§29.2 第 11 行）。
- **§27.3 C2 五项硬前置逐条照办**：①既有三条收尾文案原句全保留，只织入两点增量（「尚无修复时把最优部分修复写进仓库源文件」+「转 verification-only 模式」）；②冗余括注「被判 artifacts=工作树 diff」未引入；③同二进制 on/off 旋钮 ✓；④A/B 题集含签名题 25775/4094 + completed-but-F 同表监测（基线引 8/27）；⑤A/B 与 wall-off 配对批判读分列（**wall-off 配对批本轮未跑**，该裁决权在 V5，属主，**至今未见裁定记录**）。
- **build_ok**：`cargo test -p af-harness -p af-bench -p af-stop` = **129 passed / 0 failed**（v8 基线 126 + 新增 3：spec 序列化、提醒 OFF=v8 逐字节/ON=恰两点增量、协议旋钮）——**32996 自报，红队 33027 亲跑复现 129/0**（逐包 16+59+33+7+13+0+1）；`cargo fmt --check` rc=0；clippy 全 workspace 仅 `tb.rs:513` 既有告警。**本节点未复跑 cargo test**（§36 第 1 条）。
- **A/B 跑批读数（本节点逐行亲核，10 行全 `judge_mode=clean`/`attempts=1`/基建行 0/`scaffold=v9`/`harness_commit=6dccda5`）**：

| task | ON 臂 | OFF 臂 |
|---|---|---|
| 25775（签名题） | **F** completed 68 轮 / 558,973ms，diff **6926B**，f2p 5/2 · p2p 89/0 | **T** completed 72 轮 / 1,087,050ms，diff **8503B**，f2p 7/0 |
| 4094（签名题） | T completed 60 轮 / 1,089,863ms | T completed 51 轮 / 1,532,784ms |
| 10081 | T completed 27 轮 / 257,268ms（gate=test_edit） | T completed 47 轮 / 244,330ms（gate=test_edit） |
| 13877 | T **wall_timeout** 150 轮 / 1,879,797ms，diff 928B 在场，f2p 1/0 | T completed 22 轮 / 273,637ms |
| 3187 | F completed 60 轮 / 1,519,238ms，f2p 0/2 | F **wall_timeout** 132 轮 / 2,213,120ms，diff 5080B 在场，http_retries=1 |
| **合计** | **ON 3/5** | **OFF 4/5** |

  ⇒ **正向边际 = 0（未证明）；签名题 25775 上 ON=F / OFF=T = 签名题负向**；每格 k=1 无统计力；**零「墙切 + no_patch」**（两次墙切均 gate=ok 且补丁在场）；基建败 0、模型败 3（25775-ON、3187-ON、3187-OFF）。
- **新证据·既有缺口（C2 实施员亲扫，下循环候选材料）**：墙钟提醒**只在 turn 起点检查**（v6 设计）——13877-ON 被墙切却 **0 条提醒**（末条 bash 单跑 501s，整个 [T−300s,T] 提醒窗被单 turn 跳过）；3187-OFF 同型（1229s 空窗）。修正后可见性表：**gentle 3/10 run 触发、strong 0/10，C2 增量文案实际被模型见到的仅 3187-ON 一次**；协议腿（turn-0 条款）全程在场。历史 v6 墙切 run 同样 0 提醒 ⇒ **该缺口为既有设计，C2 的提醒腿被结构性削弱**。
- **红队 33023 issue⑨ / 33027 issue③③**：25775-ON 翻 F 的 run **提醒腿从未触发**，但 turn-0 协议条款在场（ON 559s/F vs OFF 1087s/T）⇒ 「不可归因于机制生效路径」应理解为**提醒腿未激活**，协议腿是否为早提交通道 n=1 无法排除，**k≥2 补跑时应预注册该读数**。

### 31.2 C1（候选②位·失败后转向纪律）→ 分支 `fix4-align4-p1` @ `8c670f2`

- **落地形态**：单 commit `8c670f2`（**2 files +207/−3**：`crates/af-bench/src/main.rs` +119、`docs/c1-redirect-discipline.md` +91；**无 harness crate、无 judge.rs/swev.rs**），parent = `50ba8a8`（直接继承已提交的 v8）。
- **旋钮**：`--redirect-discipline on|off`（缺省 on，off = user_message **逐字节还原 v8**，单测钉死）⇒ 同二进制 on/off 配对成立；但**旋钮只在 af-bench 侧提示词选择层（main.rs-only），不进 af-harness Policy** ⇒ **spec 级无该键，仅结果行 `redirect_discipline` 字段自锚**（红队 33074 issue②；本节点亲核 probe-p1 的 spec_json 无该键）。
- **§27.3 C1 六项硬前置逐条照办**：①重叠分析（effects.db 逐 call 重建 4094 三跑命令序列：全量 219/170/163 条、distinct 184/158/156、**逐字重复 35/12/7**、top 命令 8×/4×/4×、**护栏仿真注入 0 次**、注入文案在 normal.jsonl+transcript 双台账 **0 命中** ⇒ 红队「盲区为真」由自报升级为坐实）；②B2 件号订正为「③纠错风格」、撤证落点改为 `调优组-state.md:1110` + B2 移交单 §一P1/§3.3（红队 33031 逐字亲核）；③r1「424 事件/0 is_error」标注「ledger 亲验、源目录已清不可复跑」（亲查 `/tmp/align-probe-r1/` 已不存在）；④⑤A/B 预注册齐（主判定=题目级通过集合；主读数=turns/agent_wall_ms/逐字重复率/tool_free_streak；completed-but-F 基线 8/27；必要重试签名 + 告警线，引 `state.md:209`）；⑥`exit:141` 子句登记为**本代惰性**（p1 二进制 strings `pipefail`=0，本节点亲验）。
- **build_ok**：`cargo clean -p` 三包（Removed 3313 files/2.5GiB）后 `cargo test` 三包 = **128 passed / 0 failed**（af-bench 17 = v8 基线 15 + 新增 2）——32997 自报，红队 33031 亲跑复现 128/0（17+57+33+7+13+0+1）；非法值冒烟被拒（`--redirect-discipline maybe` → 报错，不静默落缺省）。
- **⚠ C1 的 A/B 批未跑**：本循环 C1 **只有 ON 臂**（探针轮 2 = C1-ON，4/5），**无 OFF 臂配对** ⇒ §25.2/§27.3 的「同二进制 on/off」硬前置**只落地了一半**（实现侧有旋钮，实验侧缺配对读数）。
- **红队 33031 issue①（精度订正）**：「逐字重复的相邻间隔全部 > 6」**订正为 ≥6**（最小相邻间隔 = 6：k2-a1 两对 `sed`/`awk` 实例）；结论不受影响（间隔 6 时滑窗内最多 1 次前科，仍 <2 注入阈）。

### 31.3 C3（候选③位·交付物=工作树 diff 自包含）→ **未实施**

- 脚本 `implBatch = cands.items.slice(0, 2)` 只取前两条 ⇒ **C3 无分支、无二进制、无构建、无跑批**（本节点亲核：`git branch -a | grep align4` 仅 p0/p1；§29.2 第 15 行）。
- C3 的红队订正项（`:1022` 六项，node 32976 confirmed）**仍未消解**，其中触发点二选一（tool-free 反馈路径 vs 收窄为 TASK_COMPLETE 路径）是**未裁**项。

### 31.4 候选门小结（红队 5 次串行门审的合并读数）

| 候选 | 实施 | 同二进制 on/off | 跑批 | 红队 | 本账读数 |
|---|---|---|---|---|---|
| **C2** | ✓ `3a8db9a`+`6dccda5` | ✓（spec 级可分） | ✓ 10 行（5 题 × 2 臂） | **confirmed**（33027，4 issue） | **机制实现成立；效果未证明（ON 3/5 vs OFF 4/5，签名题负向），不得写「C2 有效/增益」** |
| **C1** | ✓ `8c670f2` | ◐（旋钮有，**OFF 臂未跑**） | ◐ 仅 ON 探针 5 行 | **confirmed**（33031，5 issue） | **机制实现成立；效果未知（缺配对臂）** |
| **C3** | ✗ | ✗ | ✗ | confirmed（第三循环 32976） | **未实施** |

## 32. 探针逐轮

### 32.1 轮次账（两轮，各 5 题，均 `judge_mode=clean`/`attempts=1`/基建行 0/零 wall_timeout）

| 轮 | 节点 | 臂 / 二进制 / profile | 批次时区（工件 as-of） | af_pass | mcode_pass |
|---|---|---|---|---|---|
| **轮 1** | 33035 | **C2-ON**（`af-bench-fix4-align4-p0`，`b8dde284…`，`mavis-m31f-c2`，`wall_patch_first=true`） | 10:53:18 → 11:37:27 | **4** | 5 |
| **轮 2** | 33036 | **C1-ON**（`af-bench-fix4-align4-p1`，`73390f93…`，`mavis-m31f`，行级 `redirect_discipline=true`） | 11:39:30 → 12:38:58 | **4** | 5 |

### 32.2 逐行读数（本节点逐行亲核；两批合并件与两 lane 原件**逐行全等**〔红队 33070/33074 python 深比较 identical=True〕）

| task | 轮 1（C2-ON） | 轮 2（C1-ON） |
|---|---|---|
| `mwaskom__seaborn-3187` | **T** completed 81 轮 / 1,562,165ms，f2p 2/0 · p2p 248/0 | **T** completed 116 轮 / 1,536,262ms，f2p 2/0 · p2p 248/0 |
| `sphinx-doc__sphinx-7462` | **F** completed 26 轮 / 284,208ms，f2p **0/2** · p2p 49/0，diff **1683B 在场** | **F** completed 28 轮 / 1,606,341ms，f2p **0/2** · p2p 49/0，diff **1168B 在场**，**http_retries=1**（已披露） |
| `pytest-dev__pytest-10081` | T completed 28 轮 / 425,357ms（gate=test_edit，f2p 1/0） | T completed 31 轮 / 462,378ms（gate=test_edit） |
| `scikit-learn__scikit-learn-10908` | T completed 17 轮 / 268,721ms（f2p 1/0） | T completed 11 轮 / 62,814ms（f2p 1/0） |
| `sympy__sympy-13877` | T completed 44 轮 / 1,692,815ms（f2p 1/0） | T completed 28 轮 / 323,195ms（f2p 1/0） |

- **两轮唯一未过题同为 7462**（隐藏规格型：补丁在场、f2p 0/2）⇒ 与「折叠致归 / 候选均为提示词层机制 / 均不触及隐藏规格可见性」的既定边界一致。
- **`mcode_pass=5` 是外部对照**（账本引述值），两批目录内**无 mcode 侧工件** → 红队 33070/33074 均按「账本引述、未独立复算」计（**本节点同此口径**）。

### 32.3 探针口径裁定（三条硬限制）

1. **⚠ 探针跑在候选 ON 变体上，不是中性基线**（红队 33070 issue① / 33074 issue①）——「af_pass=4」分别是 **C2-ON 4/5** 与 **C1-ON 4/5**；**记账必须署臂别**，不得与历史中性探针 4/5（v6-p01 臂）混比；脚本硬编码的 5 题探针集**未按 §27.4⑨ 现算重取**（13 题池本循环未复算）。
2. **3187 是掷硬币题**（红队 33070 issue②）：轮 1 T / 轮 2 T，但 C2 A/B 两臂 ON=F、OFF=F ⇒ 该题在墙钟期呈 2T+1F + 双臂双 F + 两轮双 T 的高方差形态；**引用 3187 必带臂别与 n**。
3. **aligned 判定仍为 false**：方法口径 `aligned = af_pass ≥ mcode_pass`（4 < 5）⇒ **不扩测**（不扩 D1–D3 全量、不扩 glm5.3f/step5 档案）；扩测理由**只能是「未追平」**，严禁写「无剩余候选」（§19.2⑭ 教训继续适用）。
4. **纪律遵守核**：探针批与 C2 A/B 批**不并行**（A/B OFF lane 09:29 收口 vs 轮 1 10:53 起；轮 2 11:39 起 vs 轮 1 11:37 收口）⇒ §27.4⑫「扩测不得与候选 A/B 同批并行」成立；7462 全程未触碰 test-patch 信息（红线①成立）。

## 33. 三审意见（红队·三审，node 33078，step-5，12:42:32→12:54:52，**未参与本循环任何环节**，**confirmed**，8 条 issue）

| # | 三审 issue（原文要点） | 级别 | 本账采信 |
|---|---|---|---|
| ① | **候选探针结论必须如实入账**：C2 A/B 实测 ON 3/5 vs OFF **3/5**，正向边际=0；签名题 25775 ON=F（f2p 5/2、补丁在场未解、68 轮/559s）vs OFF=T（f2p 7/0、72 轮/1087s）= **签名题负向**；每格 k=1 无统计力；记录只可写「候选 2 过审 + A/B 探针已跑」，**不得写 C2 有效/增益**，须留 k≥2 复跑设计 | 中 | **采信结论，订正数字**：OFF 臂应为 **4/5**（本节点逐行复算，见 §34①） |
| ② | **V5 执行偏差**：V5（`:1008-1010`）规定「4094+25775 各 k≥2」，实际仅 25775 k=2；25775 归因判读不受影响（重写规则只涉 25775 且 v8=v7−折叠单变量成立），但**账本须记 V5 未完整执行，不得写「V5 全项落实」** | 中 | 全盘采信（§35.2 ①） |
| ③ | **判分器重试未入账**：v8 门禁 lane-b.log 载 25122 判分 1 次 judge 退出重试（urllib3 exit 1，5s 后成功）；行级 http_retries=0、judge clean 不受影响，但须披露 | 轻 | 采信（§30.2 末条） |
| ④ | **as-of 工件不齐**：C2 A/B 批无 BATCH-START/END-asof.txt（仅 launcher.log 时间戳），与 v8 批、p0/p1 批形态不一致 | 轻 | **本节点复核成立**（§29.2 第 13 行） |
| ⑤ | **账本未入账**：本账最新节仍止于第三循环账（mtime 10-23 07:04，早于本批 07:15 起跑）；第四循环事实须带 as-of 追加，引用时间一律以 DB 时刻 + 工件 mtime 为准 | 轻 | 本节即为其落实 |
| ⑥ | **文档残句过时**：`docs/tier0-adoption.md:47` 仍写「S083 与折叠的最终分格待 9818633 前后 bisect」——v8 复验已在 25775 上完成该分格，入账时须更新此句，勿留「未分格」旧述 | 轻 | 采信（§35.2 ⑦） |
| ⑦ | **构建证据未寻获**：V4 要求 `build_ok` 以 cargo test 为据；三二进制（07:14/07:21/07:23 构建）的 cargo test 记录在可及工件中**未寻获**；树内确有对应钉死单测、二进制实跑正常，但**测试通过记录本身报告为未核** | 轻 | **部分订正**（§34②：记录存在于 dwf_node 32996/32997/33027/33031 的节点结果中，但**本节点未亲跑**） |
| ⑧ | **路径偏差**：V4 规定新名构建 `~/afbuild-align2/af-bench-fix4-align2-v8`，实际落 `~/afbuild-shared/`；**红线未破**（生产位 `ecd1a1a0`、`~/afbuild-align2` 既有产物 mtime 全 10-22 未动、生产树 af @94cd192） | 轻 | 采信（§29.2 第 2/3 行复核） |

三审 evidence 另载两项**未核项**（如实转录）：`dwf_node` 节点库不可定位（**本节点亲查可定位**，`dwf_node` 表 13 行，§29.2 第 1 行）、§22.6 wall-off 配对裁定未见记录（**本节点复核仍无裁定记录**）。

## 34. 本账对第四循环各节点的订正（引用时须带上）

| # | 订正 | 依据 |
|---|---|---|
| **①** | **C2 A/B 的 OFF 臂计数：三审 33078 issue① 写「ON 3/5 vs OFF 3/5」，正确读数应为 **ON 3/5 vs OFF 4/5**。**本节点逐行复算**：OFF 臂 5 行 reward = [25775 T、4094 T、10081 T、13877 T、3187 F(wall_timeout)] ⇒ **OFF 4/5**（C2 实施员 32996 与红队 33027 均记 4/5，三审为孤例）。**方向不变**：正向边际仍 = 0（实为 **−1**），签名题 25775 仍为负向（ON F / OFF T）；不得据此写「C2 有效」 | 本节点亲跑 `python3` 逐行解析 `/tmp/align4-c2/ab-off/lane-{sig,probe}/results.jsonl`（§29.2 第 10 行）；32996/33027 自报 |
| **②** | **「构建证据未寻获」（三审 issue⑦）订正为「记录存在但本节点未亲跑」**：cargo test 读数 **v8 126/0、p0 129/0、p1 128/0** 见于 `dwf_node` 结果（32991 / 32996 / 32997）并由红队 33027（129/0）、33031（128/0）**亲跑复现**；**本节点未复跑任何 cargo test**（§36 第 1 条） | `dwf_node` 32991/32996/32997/33027/33031 |
| **③** | **「fingerprint=19 = S083 在场」的映射错误成立**（红队 33023 issue③）：19 是 r1 指纹刹车标记；S083 在场应署 `.af-outputs=2`/`externalize=8`（净对照 0/0）。**本节点复核**：四枚二进制 `observation_window`/`fold_observations` 计数全 0、`wall_timeout` 5 一致，**代际结论不受影响** | 红队 33023 issue③；本节点 strings 计数（§29.2 第 9 行） |
| **④** | **v8 与净对照的差集只有 3 个文件**（`main.rs` +51 / `swev.rs` +1 / `tb.rs` +211）⇒ **S083、S151 在场、折叠相互抵消**；「v8 = 净对照内容 − 折叠」成立，**这使 25775 的 2/2 复验构成单变量隔离** | 本节点 `git diff --stat 0dd1a23 50ba8a8 -- crates/`（§29.2 第 5 行） |
| **⑤** | **探针两轮均非中性基线**（红队 33070/33074 issue①）：**C2-ON 4/5** 与 **C1-ON 4/5** 与历史 v6-p01 臂 4/5 **跨臂不可直接比**；本账一律按臂别署名 | 红队 33070 issue① / 33074 issue① |
| **⑥** | **C1 的 OFF 臂从未跑过**（红队 33078 issue⑧ 末条亦指出「C1 仅 ON 单臂探针」）：C1 的效果**完全未知**，不得与 C2 同表并列比较 | 本节点工件清单（`/tmp/align4-c2` 仅 p0 的 ON/OFF；无 p1 的 A/B 目录） |
| **⑦** | **共享 target 陈旧工件病为双向实证**（红队 33031 issue③）：p1 首次 `cargo test` 静默复用了 **p0 的缓存测试二进制**（输出 16/59/total 129，含 p0 的测试而非 p1 的）；强制刷新后撞 **E0063**；早前 p0 树撞 **E0560**（红队 33023 issue⑧）⇒ **下一循环构建必须 touch/clean 相关 crate**（§35.2 ⑤） | 红队 33031 issue③ + 33023 issue⑧ |
| **⑧** | **闸门条件缺一项**（红队 33027 issue①）：C2 ON 臂 07:38:52 起批，而 v8 批的簿记 wrapper 到 07:40:07 才写 BATCH-END-asof.txt；闸门等的是**进程退场 + 容器排干 + 工厂计数**，**未等他批 wrapper 退出**。本轮无污染（profile 异名、无并发容器），但**下一循环闸门须把「他批 wrapper 退出 / BATCH-END 落盘」纳入条件** | 红队 33027 issue①；`launcher.log` + `/tmp/align4-v8` mtime |

## 35. 下一循环动作（第四循环 → 第五循环）

### 35.1 循环级判断

- **已收口**：v8 采纳闭环（commit 50ba8a8 → 构建 → 25775 k2 复验 2/2 → 4 题抽查无退步）⇒ **第三循环「25775 归因 = tier0 致」结案**；研究基线正式从 `0dd1a23` 移到 **`fix4-align2-v8 @ 50ba8a8`**（**生产位不动、硬换位窗维持不开**，V7 维持）。
- **未收口**：C2 效果未证明（ON 3/5 vs OFF 4/5，签名题负向）；C1 效果未知（无 OFF 臂）；C3 未实施；V5 口径未补齐；V6 bisect 未跑；§22.6 wall-off 配对未裁；差距池未扩测且未现算重取。
- **⚠ 外部语境（写作时点在场，影响下一循环排序）**：运营者 11:05 最高令「**对齐冲刺**」——6h 内把 af 对齐 mcode 至 ≤5pp、24 题非 S 档分层集、clean 判分、af ≥ mcode−5pp 即达成；三组建制：**1 组 = 在飞①第四循环（原策略不动）**、2 组 = 激进移植、3 组 = **直觉组合（v8 底 + pipefail + 仅 thinking high）**（工作流 `dwfrun-15a7f4e4`，running）。⇒ **本账的 v8 结论正是 3 组「v8 底」的单变量地基**（v8 = v7 − 折叠，是当前唯一经 k2 复验的基线）；而 **C2/C1 两轮 ON 探针 4/5 与「隐藏规格不可见」的边界，是 2 组「人格式提示词全抄」路线的对照面**。下一循环的排期须与冲刺班对齐，**不得与冲刺跑批争 anolis 槽位**（本组 ≤4、全厂 <12 纪律继续）。

### 35.2 下一循环必办清单（**按红队/三审订正项排序**）

| 序 | 动作 | 依据 |
|---|---|---|
| ① | **补齐 V5 口径**：4094 **k≥2**（+ 25122/3677/1766 各 k≥2 若成本允许），或由运营者**显式裁定下调 V5** 并在账本登记（红队 33023 issue①；三审 issue②） | §27.2 V5（`:1012`） |
| ② | **C2 复跑设计化**：k≥2（每题每臂 ≥2），并**预注册**读数：①签名题 25775 的 ON/OFF 成对；②「提醒腿是否触发」作为**分层因子**（ON 臂中提醒腿激活 vs 未激活分开读）；③「协议腿（turn-0 条款）是否为早提交通道」单列 | 红队 33027 issue③；三审 issue①；§34① |
| ③ | **C1 补同二进制 OFF 臂配对批**（`--redirect-discipline off`），题集与 C2 A/B 分列（否则两候选的效应不可分），主读数按预注册（turns / agent_wall_ms / 逐字重复率 / tool_free_streak / completed-but-F 同表） | §25.2（`:956`）；§27.3 C1④⑤；§34⑥ |
| ④ | **C3 立项与否须裁**：若立项，先按 §27.3 六项（触发点二选一：tool-free 反馈路径 vs 收窄为 TASK_COMPLETE 路径）落地再进实施批；本轮脚本 `slice(0,2)` 的编排切片须在下轮脚本里显式包含第 3 条 | 脚本 `implBatch` 切片；§27.3 C3（`:1022`） |
| ⑤ | **构建卫生**：`~/afbuild-shared` 共享 target 的陈旧工件病已**双向实证**（E0560 / E0063 / 静默复用缓存测试二进制）⇒ 下一循环**每个 worktree 构建前必须 `touch` 相关源文件或 `cargo clean -p` 对应三包**，并**禁止把「cargo test 输出行数」当绿信号而不看测试名** | 红队 33023 issue⑧、33031 issue③（§34⑦） |
| ⑥ | **闸门条件补项**：起批闸门须同时满足「无他批 af-bench 进程在飞 + 他批容器排干 + **他批 wrapper 已退出 / BATCH-END 已落盘** + 工厂容器 <12 + 本组 ≤4」 | 红队 33027 issue①（§34⑧） |
| ⑦ | **文档残句订正**：`docs/tier0-adoption.md:47` 的「S083 与折叠的最终分格待 9818633 前后 bisect」已过时（25775 上分格已完成）⇒ 下一循环提交时改写；同时**同步 `crates/af-bench/src/main.rs` 结果行注释**（50ba8a8 内残留的 4094「采纳面致归」旧归因，red队 33023 issue④） | 三审 issue⑥；红队 33023 issue④ |
| ⑧ | **V6（9818633 前后 bisect）**：正式 bisect 仍未跑。**判定**：v8 复验已在 25775 上完成「折叠 vs 其余」的分格（S083/S151/墙钟持恒），**bisect 的边际价值已从「唯一分格手段」降为「可选加深」** → **须由运营者裁定是否仍做**（做则登记为加强证据，不做则**明确销案**并写明理由，禁止悬空挂账） | §27.2 V6（`:1013`）；§21.3 残余；32991 判读⑤ |
| ⑨ | **§22.6「回归 5 题是否补 wall-off 配对」**：**至今无裁定记录**（三审 evidence 亦载）→ 下一循环**须显式裁**（补 / 不补 + 理由） | §22.6；§27.2 V5 末句 |
| ⑩ | **差距池现算重取**：下一循环若扩测，题集须**现算**（剔 S 74 后 13 题池口径，§27.4⑨），**禁用 `/tmp/gaptasks.json`**；每题逐题标「清洁认证 / arm 回退」；扩测理由**只能是「未追平」** | §27.4⑨⑫；§19.2⑭ |
| ⑪ | **记账纪律（本轮新增）**：①探针分数**必须署臂别**（C2-ON 4/5、C1-ON 4/5），不得与历史中性探针 4/5 混比；②`mcode_pass=5` 一律署「账本引述、未独立复算」；③C2 A/B 引用写 **ON 3/5 vs OFF 4/5**（**不写 OFF 3/5**）；④**不得写「C2 有效/增益」**；⑤ASOF 工件形态统一（BATCH-START/END 三批齐、第四批缺）；⑥重读/轨迹计数一律署可复算口径（`effects.db` 的 `effect_intent.payload_json`） | 红队 33070/33074 issue③；§34①⑤；三审 issue①④ |
| ⑫ | **既有缺陷转候选材料**：**墙钟提醒只在 turn 起点检查**（13877-ON 被墙切却 0 提醒，3187-OFF 1229s 空窗；gentle 3/10 触发、strong 0/10；历史 v6 墙切 run 同型）⇒ 「提醒在 turn 内触发」可作**新候选**立项（属 harness 语义变更，须过未来信息/测量语义双红线审） | 32996 summary「新证据·既有缺口」；红队 33027 evidence 四 |
| ⑬ | **红线与纪律现状继承**：生产位 `ecd1a1a0` 只读（**本轮已复核未变**）；研究二进制**无 D-37 前缀**（本轮以 profile 别名 `mavis-m31f-c2` + 臂间串行 + 闸门时序规避撞名，**未换 `fix4-container-names` @ `daef39c`**）⇒ 下一循环多臂并行仍须**臂间串行或换该分支二进制**；`/tmp/bench-*`、`/tmp/truth-*` 只读；本组容器 ≤4、全厂 <12 | §27.4⑦；AGENT.md 硬纪律 3/7 |

### 35.3 7462 隐藏规格类题：**立项论证未推进**（结论 + 依据 + 建议）

- **结论：第四循环未推进 7462 的立项论证**。三条依据：
  1. **工件层**：本循环对 7462 只做了**两次探针跑批各 1 跑**（轮 1 = C2-ON：F completed 26 轮/284,208ms；轮 2 = C1-ON：F completed 28 轮/1,606,341ms），**两跑都把 7462 写作「预期 F、不计入门槛」**（BATCH-END-asof 原文「7462 F expected, not counted」）⇒ **是当已知未翻题跑，不是立项论证**。
  2. **文档层**：`find . -name "*立项*"` **零命中**；`grep -rn "隐藏规格" --include="*.md"` 命中仅本账与巡检日志/章程 ⇒ **无 7462 专项立项文档**。第三循环 §23.2（`:895`）的「翻题须『隐藏规格可见化』类机制，触碰 test-patch 信息 → 有未来信息红线风险，**须另行立项论证，本循环不作主张**」——**该待办在本循环原样挂账未启动**。
  3. **流程层**：第四循环脚本的 `notCovered` 明列「7462 隐藏规格类翻题机制（另立项论证）」⇒ **编排上即把它排除在本循环之外**，与「未推进」一致。
- **本循环对 7462 的新增事实（可作立项输入）**：两臂**补丁都在场但未解**（diff 1683B / 1168B，f2p 0/2、p2p 49/0，与第三循环「补丁错误类」同型）；两轮 **hidden-spec 断言仍是唯一缺口**；**两个提示词层候选（C2/C1）都推不动它** ⇒ 再次坐实「**7462 的失败面不在提示词/预算/墙钟层**」。
- **下一循环建议（**待运营者/红队裁决，本账不代裁**）**：若要立项，第一步**不是**碰 test-patch，而是先做**红线可行性论证**——「隐藏规格可见化」是否必然引入未来信息（若必然 ⇒ 该类题在现有红线下**不可解**，应转为**题集分层/判据口径**问题而非机制问题）；可先出一页**可行性备忘**（含「必然引入未来信息」与「可不引入」两条路径的判别标准），再决定是否进实施。
- **口径提醒**：扩测理由**只能写「未追平」**（7462 仍是唯一未过题、mcode 侧同题 completed/True 为硬对照），**严禁写「无剩余候选」**（§19.2⑭）。

### 35.4 下一循环建议的节点分工（沿用第四循环编排优点）

①「v8/基线维护员」（守 `50ba8a8` 基线 + 补 4094 k2 + 裁定 V6/§22.6）+ ②「候选实施/复跑员」（C2 k≥2 复跑、C1 OFF 臂、C3 若立项）**并行**；③「红队·第五循环」（串行门审：v8 口径完整性、C2/C1 配对读数、账本订正落地）；④「红队·三审」（未参与环节）；⑤「状态记账员」（落账）。**纪律**：跑批 >2 题必拆 ≥2 进程；臂间串行或换 `daef39c` 二进制；起批前 anolis 计数 <12、本组 ≤4；**与「对齐冲刺」班错峰**（冲刺 8 lane 自管 ≤8 容器，本组不得与之争槽）。

## 36. 本节明确未做的事（供下一轮判断可信边界）

1. **未跑** `cargo build` / `cargo test` / `cargo fmt` / `clippy` —— 本节所有「126/129/128 passed」字样**均署节点**（32991 / 32996 / 32997 / 33027 / 33031），**本节点未复跑**（§34②）。
2. **未跑**任何判分、任何新跑批、任何 k≥2 复跑 —— 本节点只读了 `results.jsonl`（26 行）、`harness.db`（`mode=ro`）、`agent.diff` 大小与 git 状态。
3. **未做** 9818633 前后 bisect（V6）、**未跑** 4094 k2、**未裁** §22.6 wall-off 配对、**未跑** C1 的 OFF 臂、**未实施** C3 —— 均登记在 §35.2。
4. **未逐 call 复算** 任何轨迹级指标（重读计数 26/33、逐字重复 35/12/7、提醒可见性 3/10·0/10）—— **均为节点自报**（33023 / 33031 / 32996），本节点只复核了行级结果字段与工件存在性。
5. **未读** 模型侧 `trace.db` 工具输出原文；**未复核** 起批前 anolis 容器快照与镜像在册的逐题状态（仅见 `containers-at-launch.txt` 3 行与三审转述）；**未核** 判分器重试的原始 log 全文（仅采信 lane-b.log 的转述与三审登记）。
6. **未动** 任何代码、文档、分支、容器与生产位（本节点只读 + 追加本节）；**未改** `docs/tier0-adoption.md`（残句订正属下一循环提交者，§35.2 ⑦）。
7. **未代裁**：C2 是否继续复跑/放弃、C3 是否立项、C1 与 C2 的优先级、V6 是否执行、7462 立项是否启动 —— **均属红队/运营者裁决**。

---

*第四循环账毕。本节由状态记账员（MiniMax-M3.1-Flash-Preview）于 2026-10-23 12:5x CST 追加写入 `计划/研究组/对齐组-state.md`；下一循环请从 §30.2（v8 复验读数与 V5 口径缺口）、§31.4（候选门合并读数）、§32.3（探针臂别口径）、§34（本账订正，**尤其 ① OFF 臂 4/5**）、§35.2/§35.3（必办清单 + 7462 立项未推进）开始；引用本节任何数字须带 as-of 与臂别，并**不要**引用「OFF 3/5」这一已被订正的数对，也不要把 C2 的 A/B 读数写成「C2 有效」。*

---

# 第五循环（对齐冲刺·三组决战）· 账本增补

> 本节是**追加节**，§0–§36（第一至第四循环账）一字未改。写作时点 **2026-10-23 15:3x CST**；本节所有数字带 as-of，并区分「**本节点亲跑/亲读**」与「**节点自报**」。
> 工作流 run：**`dwfrun-15a7f4e4-ae6d-4f08-960c-6ed89144774a`**（名「对齐冲刺·三组决战（限流回退版）」，2026-10-23 11:10:39 起；`status=running`、`spent_tokens=27,378,679`、`time_updated=2026-10-23 15:28:33`——`dwf_run` 表，**本节点 15:3x 亲查**；`resumed_from=dwfrun-668b72e7-2cdd-44a0-9bba-cccd3f1c9ea3`，后者 11:05:19 起、11:10:39 `cancelled`/`stopReason=superseded`）。
> 流程脚本：`.zcode/workflow-drafts/对齐冲刺-三组.dwf.ts`（14,875 B，11:10 mtime）；run 内嵌 `script_hash=3bff10e304e9ec04891622cce07c983eb65a67e522ae3a7340cb54a06f05c9c9`。
> 军令状出处：`状态观测/巡检日志.md:325`（11:1x 运营者最高令）、`:326`（11:4x profile 配对口径修订）、`:327`（11:5x 测集方案 B 裁决）。
> 硬时限 **17:05**（脚本 `:8`「硬时限 17:05——各步超时即弃该步如实报」）；本节点写作时点余量 ≈ 1h30m。

## 37. 冲刺节点账与本节点自测

### 37.1 节点账（`dwf_node` 表，**本节点 15:3x 亲查**）

| site | node | actor（模型） | 内容 | 节点自报 | 本节点复核 |
|---|---|---|---|---|---|
| artifact#1 | 33109 | — | metrics 制品「对齐冲刺·读数（6h 时限）」 | `af_best=15 / mcode=21 / gap_pp=25` | **数字须更正**，见 §43.2 |
| ask#1 | 33044 | thinking 探针员（GLM-5.3-Flash$max） | af 可否开 thinking | `probe_ok=true` | **已亲核**（§40） |
| ask#2 | 33045 | 标定员（GLM-5.3-Flash$max） | 24 题测集 + mcode 侧数字 | 冻结 D1×8/D2×11/D3×5，m31f 21/24 | **已亲核**（§39） |
| ask#3 | 33049 | 移植实施员（GLM） | **2 组·激进移植** | `build_ok=true / smoke_ok=true` | **已亲核**（§41.1） |
| ask#4 | 33050 | 组合实施员（GLM） | **3 组·直觉组合** | `build_ok=true / smoke_ok=true` | **已亲核**（§41.2） |
| ask#5 ord1–8 | 33059–33066 | 跑批员 G2甲/乙/丙/丁、G3甲/乙/丙/丁（GLM） | 8 lane × 6 题 | 见 §42.1 | **8 lane 逐行亲核**（48 行） |
| ask#6 | 33110 | 红队·冲刺审（step-5-preview$high） | 三件快审 | **`rejected`（3 条 issue）** | 裁定与 issues 原文照录（§44） |
| **ask#7** | **33114** | **状态记账员（MiniMax-M3.1-Flash-Preview，本节点）** | 落账 | — | — |

- **18 节点 = 17 completed + 本节点 running**（`dwf_node` 按 `time_created` 排序；ask#1–ask#4 在 11:10–12:1x 陆续完成，8 条 lane 在 12:1x–15:1x 完成，红队 15:1x 后完成）。
- **未触发的分支**：脚本 `:125-126` 的 `ready` 门槛（`build_ok && smoke_ok`）**两臂都满足** → 8 lane 全起跑，无降级。脚本 `:167` 的「最优臂」选择逻辑与 `agg()` 有缺陷，**其产出数字不可直接引用**（§43.2）。
- **无 m3 回退发生**：8 条 lane 的结果行 profile 全在 m31f 通道（§42.1），脚本 `:138` 的「429/限流持续 2 分钟以上整 lane 回退 mavis-m3」分支**一次都没走到** → profile 配对口径全程对 mcode-m31f 清单。

### 37.2 本节点自测（2026-10-23 15:30–15:33，**全部本节点亲跑/亲读**）

| 自测项 | 命令 | 输出 | 判读 |
|---|---|---|---|
| run/节点账 | `python3` 读 `~/.zcode/cli/db/db.sqlite`（`mode=ro`）`dwf_run`/`dwf_node`/`dwf_event` | run 11:10:39 起 / running / 27,378,679 tokens；18 节点；事件 seq 92 = 脚本自报终判 | 与 §37.1 逐行一致 |
| 8 lane 逐行解析 | `python3` 解析 `/tmp/sprint-g{2,3}-lane{0..3}/results.jsonl` | **8 × 6 = 48 行**，`judge_mode=clean` / `attempts=1` 全命中；scaffold 24×`v8-g2` + 24×`v8-g3`；`reasoning_tier=high` 48/48；`harness_commit` 24×`bd4e2799…` + 24×`4a0a902e…` | **变体指纹全部在场**（§41、§42） |
| lane 基建面 | `tail -1 /tmp/sprint-g{2,3}-lane{0..3}.log` | 8 条末行全部 `infra 0`（resolved 依次 3/6/3/3、3/5/4/4） | **零基建损耗**（与第一循环 r1 的 0/5 全灭对照） |
| 臂间聚合 | `python3` 聚合 48 行 | **G2 = 15/24 = 62.50%；G3 = 16/24 = 66.67%** | 与红队订正后读数逐位一致 |
| **脚本 `agg()` 复现** | 用 `dwf_node` 的 lane 自报 `group`/`passes`/`rows` 逐条喂回脚本 `:146-160` 的 `expectedOf`/`agg` 逻辑 | `agg('G2')` = 15/24 对 21（4 lane 全中）；**`agg('G3')` = 9/12 对 11（只中 g3-lane1 + g3-lane2）** | **脚本终判数字的根因已定位**（§43.2） |
| 题目级通过矩阵 | 同上脚本按 `task_id` 出 24×(mcode/G2/G3) | 24 题中 **仅 3 题两臂分歧**（6528 G2-T/G3-F、14248 G2-F/G3-T、6386 G2-F/G3-T）；「mcode 过而两臂都不过」= 4 题（1766、7462、14011、4551）；「af 过而 mcode 不过」= **0 题** | 不对称**单向**（全在 mcode 一侧）；G3 的净 +1 建立在 3 题分歧的 2:1 上（§42.2） |
| 测集抽样复现 | `python3` 按 `sampling_rule` 重跑（层内 instance_id 升序、stride=池/取数、`floor(i*stride)`），与 `/tmp/calib-frozen-set-24.json` 比对 | D1 命中序号 `[0,3,7,10,14,18,21,25]`、D2 `[0..10]`、D3 `[0..4]`；**三层选中集与冻结件逐位相同**；D2 唯一跳过 = `sympy__sympy-17318` | 冻结清单**可复现**；红队 issue ③ 正确（§39.2、§44） |
| mcode 侧 as-of 现读 | `python3` 对 6 个 live mcode 目录重取 last-row（每 task 取末行 `reward==true`），与冻结清单 `diff` | **m31f 21/24（diff=∅）、m3 20/24（diff=∅）**；live 目录 mtime 全部 ≤ **2026-10-22 15:51:47** | 数字**今日仍可复现**；但「快照」是 symlink 不是副本（§39.3） |
| 二进制 sha256 | `sha256sum` | g2 = `12638d0c1ede18d332d2c7c8964c60629d5627e375aec8a3bc42cb8ab47ce404`；g3 = `7a87876c0a5541c0e709af74e453a745a1a962abb4c254b8519bd07eca3f8b76` | 与实施员自报**逐位一致**（§41） |
| 变体指纹（源码侧） | `git -C af-wt-sprint-g{2,3} grep/show` + `sed -n` | g2：`main.rs:185/188` 人格三条逐字断言、`tb.rs:79` `set -o pipefail; cd {} && {}`、`main.rs:1053` `max_turns: 250`；g3：`main.rs:731` 仍是 af 标准 SWEV_SYSTEM_PROMPT（无 MCode 字样）、`tb.rs:78` pipefail、`main.rs:964` `max_turns: 250` | **人格只在 G2、pipefail/250 轮两臂都有**（单因子差成立，§41.3） |
| 生产工作树 | `git -C af rev-parse HEAD` + `status --porcelain \| wc -l` | HEAD **94cd1923c34842983049bce5f97b3dcb6c7c348b**（guardrail-fix2）、5 个既有未跟踪 `poc/` 目录 | **生产面零触碰**（纪律守住） |
| 1 组（四循环）读数 | `python3` 读 `/tmp/align4-probe-p{0,1}/results.jsonl`、`/tmp/align4-v8/lane-25775/results.jsonl` | p0/p1 各 5 行 4/5、scaffold=v9、`reasoning_tier=off`、commit 6dccda5/8c670f2；25775 复验 2/2 过、scaffold=v8 | 与 run 结论一致；**并入方式见 §45** |
| **未跑**（本节点明确不做） | — | 未跑 `cargo build`/`cargo test`/`cargo fmt`/`clippy`；未跑任何判分、任何新题、任何复跑；未核网关侧 thinking 穿透 | 所有构建/单测结论**只署实施员节点**（33049/33050）；本节「全过」字样均标注来源 |

## 38. 军令状判据（判据先于结果）

| 项 | 内容 | 出处 |
|---|---|---|
| 总令 | **6 小时内（至 17:05）af 对齐 mcode 至 ≤5pp**，三组建制，动用全部资源 | `巡检日志.md:325`；脚本 `:1-8` |
| **测集** | **24 题非 S 档分层集**（D1/D2/D3 各 8），剔除考古 74 题 | `:325`；脚本 `:2-3` |
| **判分口径** | **clean 判分** | `:325`；脚本 `:2` |
| **对照侧** | af 最优变体 **vs mcode 官方 last-row** | `:325`；脚本 `:2-3` |
| **达成线** | **af 通过率 ≥ mcode − 5pp 即达成**；同时报全池 headline 与差距画像 | `:325`；脚本 `:3` |
| **限流回退（11:4x 并入）** | profile 优先 mavis-m31f；遇 429/限流持续 2 分钟以上则**整 lane 回退 mavis-m3**（同 lane 不混 profile，profile 字段如实记） | `:326`；脚本 `:138` |
| **口径修订（11:4x）** | **profile 配对口径**：m31f lane 对 mcode-m31f 官方过题清单、m3 lane 对 mcode-m3 | `:326`；脚本 `:145-152` |
| **测集裁决（11:5x）** | **D3 非 S 池仅 5 题**（20 题中 15 题是考古 S 档）→「8/8/8 不可满足」→ 冻结**方案 B = 24 题（D1×8 / D2×11 / D3×5，同步长规则）**；**m31f 基线 21/24 = 87.5% 入军令状** | `:327`；脚本 `:83`；标定员 node 33045 `exclusion_note` |
| **建制** | 1 组 = 在飞①四循环（原策略不动，不在本流内）；2 组 = 激进移植（mcode 人格提示词全抄 + thinking high + 250 轮 + pipefail 一把上）；3 组 = 直觉组合（v8 底 + pipefail + **仅** thinking high，无线性迭代） | `:325`；脚本 `:4-6` |
| **红线** | 未来信息零引入；**测量语义零改动**（thinking/轮次/提示=请求与编排层参数）；生产位只读 | 脚本 `:9`、`:62` ①—⑦ |

**达标线的算术（本节点亲算，**订正标定员 node 33045 证据串自相矛盾处**）**：

- mcode 配对期望 = 21/24 = **87.50%**；
- 达标线 = 87.50% − 5pp = 82.50% → ×24 = **19.8 题** → **af 须 ≥ 20/24（至多落后 1 题）**；
- 标定员证据串里「af 对 m31f 配对达标=过题≥**16/24**」与同句「af 须 ≥ 19.8/24 即 20 题」**冲突**，**16/24 是误写**，operative 的 20 题正确（红队 issue ② 同指，见 §44）。

## 39. 测集（冻结清单 + 抽样规则 + mcode 侧 as-of）

### 39.1 冻结件与抽样规则（本节点逐位复现）

- **机器可读终稿**：`/tmp/calib-frozen-set-24.json`（2,909 B，mtime 2026-10-23 11:22），内含 `as_of = "2026-10-23 11:17:13 +0800"`、`frozen_by = 标定员 (subagent)`。
- **抽样规则（无随机种子、可复现）**：层内池 = 任务包 `/tmp/swev-s1/`（120 题）剔除 S 档 74 题后的余集 → 层内按 `instance_id` 升序排序 → `stride = 池大小 / 取样数` → 取 `floor(i*stride)`，`i = 0..take−1`。

| 层 | 池（剔 S 后） | 取数 | stride | 命中序号 | 冻结清单 |
|---|---|---|---|---|---|
| D1 | 29 | 8 | 3.625 | 0/3/7/10/14/18/21/25 | `astropy-12907`、`django-11066`、`matplotlib-22719`、`pydata__xarray-4075`、`pylint-7277`、`scikit-learn-10297`、`scikit-learn-11578`、`sphinx-10466` |
| D2 | 12 | 11 | 1.0909 | 0..10 | `astropy-8707`、`django-11451`、`mwaskom__seaborn-3187`、`psf__requests-1766`、`psf__requests-2317`、`pylint-6528`、`pytest-7205`、`pytest-8399`、`sphinx-7462`、`sympy-13877`、`sympy-14248` |
| D3 | 5 | 5 | 1.0 | 0..4 | `django-10097`、`django-14011`、`django-14672`、`pylint-4551`、`pylint-6386` |

- **本节点独立复现**：按上述规则重跑抽样器（`/tmp/calib-candidates.json` 的 pools + `floor(i*stride)`），**三层选中集与冻结件逐位相同**；D2 唯一跳过 = `sympy__sympy-17318`（**不是** `psf__requests-2317`——后者序号 4 被选中，见 §44 issue ③）。
- **S 档剔除核对**（红队亲跑 + 本节点读工件）：S 档 74 = D1 31 / D2 28 / D3 15，名单出自 `计划/研究组/mcode考古份额-量化.md:70-77`，经 repo-slug 映射（`requests→psf__`、`seaborn→mwaskom__`、`xarray→pydata__` 等 12 前缀）与 120 题包求交 **74/74 唯一命中、0 遗漏**；**冻结 24 题 ∩ S74 = ∅**。
- **判据偏差已登记（非静默降级）**：军令状「D1/D2/D3 各 8」在 D3 不可满足，标定员 escalate、主代理裁决方案 B（`巡检日志.md:327` 与 `:329`）→ **D3 只取 5 题**，此为**经裁决的偏差**，非本组自行缩题集。

### 39.2 mcode 侧双 profile 过题清单（判据配对用）

- **m31f_passed = 21 题**（24 题中过 21）；**m3_passed = 20 题**（24 题中过 20）。
- 24 题中 **m31f 未过** = `django-10097`、`psf__requests-2317`、`pytest-7205`（3 题）；**m3 未过** = 上述 3 题 + `django-14011`（4 题）。
- **全池 headline**（判据要求同时报）：m31f **115/120**（d1 58 / d2 38 / d3 19）、m3 **94/120**（d1 50 / d2 31 / d3 13）。

### 39.3 ⚠ mcode 侧 as-of：**「快照」名不副实，但数字今日仍可复现**

- 标定员 `exclusion_note` 与冻结件的 `mcode_lastrow_source.snapshot` 均写「`cp -a` 快照 `/tmp/calib-asof-20261023-111713`（8 目录）」。
- **本节点核查**：该目录内 8 个条目**全部是 symlink**（指向 `/home/pan-ding/bench-data/results/bench-official-mcode-*`），**不是内容副本** → `cp -a` 保留了原 symlink，**「冻结」在形式上不成立**（读经它拿到的是 live 目录）。
- **但冻结保证实际成立，理由是源侧未再变**：live 六个 mcode 目录的 `results.jsonl` mtime 全部 **≤ 2026-10-22 15:51:47**，**早于** 11:17:13 的标定 as-of → 11:17 之后无人重写。
- **本节点 15:3x 现读复核**：对 6 个 live 目录重取 last-row → **m31f 21/24（与冻结清单 diff=∅）、m3 20/24（diff=∅）** → **冻结清单与 mcode 侧数字今日仍逐位可复现**。
- **登记为口径瑕疵（低危）**：下一轮若沿用此模式，须**改用真副本**（`cp -aL` 解引用或 `tar` 实拷）并核 `md5`，否则「快照」二字不可写进呈报。

## 40. thinking 探针结论

- **节点**：ask#1 / node 33044，thinking 探针员（GLM-5.3-Flash），**as-of 2026-10-23 11:2x**。
- **结论：`probe_ok = true`** —— **af 开 thinking 可行**，且是**请求层参数**（军令状②允许，非判分链）。

| 项 | 内容 |
|---|---|
| **af_config_shape（最小 diff = 1 行）** | `crates/af-bench/src/main.rs:350`（mavis-m31f profile 的 `EndpointSpec`）把 `reasoning_tier: ReasoningTier::Off` → `ReasoningTier::High`（可选 `:365` mavis-m3 同改） |
| 下游链路（零新增） | `spec.rs:28-34/78` 枚举 `off\|low\|medium\|high`；`endpoint.rs:296-297` 对非 Off 组装 `body["thinking"]={type:enabled,budget_tokens:N}`；`endpoint.rs:17-19` `HIGH=4096`；`endpoint.rs:385-391` 预算叠加进 `max_tokens`；`endpoint.rs:886-915` 既有单测断言该请求体 |
| **指纹（3 次最小 curl POST mavis `/v1/messages`）** | ①`thinking={type:enabled,budget_tokens:1024}` → **HTTP 200**，`usage.output_tokens_details.thinking_tokens=24`，`content=[thinking,text]`；②**对照**（无 thinking 字段 = af 当前 tier:Off 形态）→ HTTP 200，`content=[text]`、**无** `thinking_tokens`（证明网关默认关、thinking 块显式生效）；③af tier=high 逐字段（`budget_tokens:4096, max_tokens:8192`）→ HTTP 200，`thinking_tokens=56`、`stop_reason=end_turn` |
| 响应存档 | `/tmp/probe-thinking-resp.json`、`/tmp/probe-ctrl-resp.json`、`/tmp/probe-high-resp.json` |
| **探针员自述边界** | 探针用 curl **复刻** `endpoint.rs:296-297` 的请求体，**未跑 af 二进制端到端**（那需改已提交代码，本单红线禁止）；未动任何已提交代码、未动判分链、密钥照旧（密钥走既定 `key_cmd mcode-token.py`，未落明文） |

**本节点独立复核（跑批侧）**：48/48 冲刺结果行 `reasoning_tier = high`（scaffold `v8-g2` 24 行 + `v8-g3` 24 行）—— 探针结论在**真实跑批**上被兑现，不止 curl 层。

**未核项（如实登记）**：网关侧档位**穿透**（mavis `llm-call.json` 回显 `thinkingLevel=high`）**本节点未核**（实施员亦把此列为 caveat）——af 侧只证「请求层已武装 + 全调用被接受」。

## 41. 两组变体（分支 / 指纹 / 冒烟）

### 41.1 2 组·激进移植（G2）

| 项 | 值 | 出处 / 本节点复核 |
|---|---|---|
| 分支 | **`fix4-sprint-g2` @ `bd4e279`**（worktree `~/workspace/af-wt-sprint-g2`） | node 33049；本节点 `git worktree list` 亲见 |
| 基线 | `fix4-align2-v8@50ba8a8`（= 0dd1a23 合流 + fb7666d + v8 回退，**折叠族未入**） | node 33049；本节点 `git log` 亲见 |
| 提交 | `ef474ee`（四件移植）/ `a8129ae`（wire 合同测试）/ `bd4e279`（产物出库） | 本节点 `git log --oneline` |
| 二进制 | `/home/pan-ding/workspace/af-wt-sprint-g2/af-bench-fix4-sprint-g2`，sha256 **`12638d0c…ce404`**（12,767,336 B，mtime 11:43） | **本节点 `sha256sum` 亲算**，与自报逐位一致 |
| **①人格提示** | `SWEV_SYSTEM_PROMPT` **整体替换**为 mcode coding 移植版（人格句 / 纠错风格 / 收尾自包含三条按 `计划/研究组/B2提示风格-移交对齐组.md` 原文逐字）；`SWEV_INSTANCE_PROTOCOL` 与题面**零改动** | node 33049；红队逐字节核 = 活体 `spec_json` 的 1194 字符 system，sha16 `5faf5e4334bc9072`；**本节点核源码 `main.rs:185/188`** 两条断言逐字在位 |
| **②thinking** | mavis-m31f 与 mavis-m3 `reasoning_tier` Off→High | node 33049（引 `main.rs:429`）；48/48 结果行 `high` |
| **③250 轮** | `main.rs:1053` `max_turns: 250`（v3 起已有，本臂零改动） | **本节点 `git show bd4e279:…/main.rs` 亲见** |
| **④pipefail** | `tb.rs:79` `format!("set -o pipefail; cd {} && {}", workdir, command)`（588382d p01 同型） | **本节点亲见**；活体 24/24 run 携 `harness_commit=bd4e2799…` |
| 结果行锚 | `scaffold = v8-g2`（24/24）、`reasoning_tier = high`（24/24）、`judge_mode = clean`（24/24）、`attempts = 1`（24/24） | **本节点逐行亲核** |
| **冒烟** | 题 `psf__requests-6028`、profile `mavis-m31f-g2`、out `/tmp/swev-g2-smoke`（D-37 隔离）、host anolis（峰值自占 1 容器）→ **resolved=true**、`judge clean` f2p 2/0 / p2p 185/0、turns 63、agent 墙钟 1,108,737ms、http_retries 0；`systemPrompt` 三条锚点逐字命中；`body[thinking]={enabled,4096}` 且 `max_tokens=36096`（=32000+4096） | node 33049（含 wire 合同测试 `sprint_g2_wire_carries_persona_system_and_thinking_high` 经 StubServer 真实装配链断言） |
| 构建 | `cargo clean -p af-bench -p af-harness` 报 **Removed 0 files**（无陈旧 rlib 在场）→ af-bench 全新编译；**单测 af-bench 18/18 + af-harness 57/57 全过**（含 2 枚 pipefail 测试 + 1 枚 wire 合同测试） | **署实施员节点 33049；本节点未复跑** |
| **已知偏离（如实登记）** | ①`from Environment` 悬空引用（B2 §三 R-A）、②preamble 折叠前提 af 不存在（R-C）——按「全抄」军令**保留原文**；③冒烟执行的是 `ef474ee` 版二进制（其后只加 `#[cfg(test)]` 与 gitignore，运行时语义零差） | node 33049 |

### 41.2 3 组·直觉组合（G3）

| 项 | 值 | 出处 / 本节点复核 |
|---|---|---|
| 分支 | **`fix4-sprint-g3` @ `4a0a902`**（worktree `~/workspace/af-wt-sprint-g3`） | node 33050；本节点 `git worktree list` 亲见 |
| 基线 | **同 G2**：`fix4-align2-v8@50ba8a8` | node 33050；本节点 `git log` 亲见 |
| 提交 | **单 commit `4a0a902`**（`main.rs` +31/−…、`tb.rs` +55/−…） | 本节点 `git show --stat` |
| 二进制 | `/home/pan-ding/workspace/af-wt-sprint-g3/af-bench-fix4-sprint-g3`，sha256 **`7a87876c…8b76`**（12,764,512 B，mtime 11:33） | **本节点 `sha256sum` 亲算**，与自报逐位一致 |
| **组合（恰两因子，与 G2 单因子差 = 人格提示零引入）** | ①**pipefail**（`tb.rs:78`，588382d 同型；is_error 通道 / 指纹刹车 / 止损阈值 / 判分链零触碰）；②**thinking High**（`main.rs:350`） | **本节点亲见 `main.rs:731` 仍是 af 标准 `SWEV_SYSTEM_PROMPT`（"You are an autonomous software engineer…"），全树无 MCode 字样** → 人格零引入成立 |
| 250 轮 | `main.rs:964` `max_turns: 250` | **本节点亲见** |
| 结果行锚 | `scaffold = v8-g3`（24/24）、`reasoning_tier = high`（24/24）、`judge_mode = clean`（24/24）、`attempts = 1`（24/24）、`harness_commit = 4a0a902e…`（24/24） | **本节点逐行亲核** |
| **冒烟** | 题 `django__django-11087`、profile `mavis-m31f-g3`、out `/tmp/sprint-g3-smoke`（log `/tmp/sprint-g3-smoke.log`）→ **status=wall_timeout / resolved=**false** / infra=0 / agent 墙钟 1,824,179ms（≈1800s 满额）/ 34 轮调用全成功 / tokens in 36,791 out 189,914**；五锚齐全（scaffold=v8-g3、reasoning_tier=high、harness_commit=4a0a902e…、judge_mode=clean、gate=ok） | node 33050；**本节点亲读 `/tmp/sprint-g3-smoke.log` 末行「af-bench 完成: 1 题, resolved 0, infra 0」→ resolved 0 如实** |
| **冒烟判定口径** | 判的是**管线通**（-g3 容器后缀实证 / reasoning_tier 入 spec_json / 34-34 调用被网关接受 / pipefail 桥接在位 / clean 判分链走通 / 结果行如实记账），**非通过率**（n=1） | node 33050；**本节点复核后认可该口径**：未解出本题 = 墙钟满额的正当测量读数 |
| 构建 | `cargo clean -p af-bench -p af-harness` 清 **2211 文件 / 2.2 GiB** → release 重建 1m16s 零警告错误；**单测 3 枚亲跑过**（pipefail 构造合同 + 真 bash 四态语义合同 + Anthropic 请求体 thinking 断言） | **署实施员节点 33050；本节点未复跑** |
| **caveats（自述）** | ①网关侧 `thinkingLevel=high` 回显 af 侧不可直接观测；②结果行 `reasoning_tier` 为单字面量 `high`，本 binary 仅供 mavis 通道 lane 使用；③冒烟墙钟 ~34 min 的主因是题目 agent 阶段本身，未危及 17:05 | node 33050 |

### 41.3 变体可比性判定（本节点判定，**下一轮读数的前提**）

| 维度 | G2 | G3 | 可比？ |
|---|---|---|---|
| 底（基线） | `50ba8a8`（v8） | `50ba8a8`（v8） | ✅ 同底 |
| pipefail | 有 | 有 | ✅ 同 |
| 250 轮 | 有 | 有 | ✅ 同 |
| thinking High | 有 | 有 | ✅ 同 |
| **人格提示** | **有** | **无** | ❌ **单因子差**（这正是设计意图） |
| profile 别名 | `-g2`（防 docker 撞名） | `-g3`（防 docker 撞名） | ✅ 端点/模型/key/提示/thinking 全同，**非测量语义变更**（红队逐 run 核 24 个 G3 run 的 `spec_json` 证实） |

⇒ **G2 vs G3 是干净的「人格提示」单因子对比**（这是 3 组「不加人格提示、与 2 组形成单因子差」的设计兑现）；但 **G2/G3 vs 第四循环 1 组不可直接比**（scaffold 与 reasoning_tier 双因子不同，见 §45）。

## 42. 8 lane 终值

### 42.1 逐 lane 读数（**本节点逐行亲核**，48 行 = 8 lane × 6 题，as-of 2026-10-23 15:3x）

| lane | 臂 | 节点自报 group | 结果行 profile（实测） | rows | passes | 题级明细（T/F） | lane.log 末行 |
|---|---|---|---|---|---|---|---|
| `sprint-g2-lane0` | G2 | `G2` | `mavis-m31f` | 6 | **3** | 12907 T、7277 T、8707 T、requests-2317 **F**(wall_timeout)、sphinx-7462 F、django-14011 **F**(wall_timeout) | `resolved 3, infra 0` |
| `sprint-g2-lane1` | G2 | `G2` | `mavis-m31f-g2` | 6 | **6** | 11066 T、sklearn-10297 T、django-11451 T、pylint-6528 T(wall_timeout)、sympy-13877 T、django-14672 T | `resolved 6, infra 0` |
| `sprint-g2-lane2` | G2 | `G2` | `mavis-m31f` | 6 | **3** | 22719 T、sklearn-11578 T、seaborn-3187 T(wall_timeout)、pytest-7205 **F**(gate=test_edit)、sympy-14248 **F**(gate=no_patch)、pylint-4551 **F**(wall_timeout) | `resolved 3, infra 0` |
| `sprint-g2-lane3` | G2 | `G2` | `mavis-m31f-g2` | 6 | **3** | xarray-4075 T、sphinx-10466 T、pytest-8399 T(gate=test_edit)、requests-1766 **F**、django-10097 **F**、pylint-6386 **F**(wall_timeout) | `resolved 3, infra 0` |
| `sprint-g3-lane0` | G3 | **`G3（3组=直觉组合：…）`** | `mavis-m31f-g3` | 6 | **3** | 12907 T、7277 T、8707 T、requests-2317 **F**、sphinx-7462 **F**(wall_timeout)、django-14011 **F** | `resolved 3, infra 0` |
| `sprint-g3-lane1` | G3 | `G3` | `mavis-m31f` | 6 | **5** | 11066 T、sklearn-10297 T、django-11451 T、pylint-6528 **F**(wall_timeout)、sympy-13877 T、django-14672 T | `resolved 5, infra 0` |
| `sprint-g3-lane2` | G3 | `G3` | `mavis-m31f-g3` | 6 | **4** | 22719 T(wall_timeout)、sklearn-11578 T、seaborn-3187 T(wall_timeout)、pytest-7205 **F**(gate=test_edit)、sympy-14248 T、pylint-4551 **F** | `resolved 4, infra 0` |
| `sprint-g3-lane3` | G3 | **`g3`** | `mavis-m31f` | 6 | **4** | xarray-4075 T、sphinx-10466 T(wall_timeout)、requests-1766 **F**、pytest-8399 T(wall_timeout)、django-10097 **F**(wall_timeout)、pylint-6386 T(wall_timeout) | `resolved 4, infra 0` |

**臂级合计（本节点亲算）**：**G2 = 15/24 = 62.50%**；**G3 = 16/24 = 66.67%**。

- **基建面全清**：8 条 lane 末行 `infra 0`（第一循环 r1 的 0/5 全灭于镜像缺失 → 本轮**零基建损耗**，镜像前置检查已生效）。
- **判分口径全清**：48 行 **全部 `judge_mode=clean`、`attempts=1`**，零重试行、零 `judge_error` 行（第一/二循环的 `judge_mode` 纪律在本轮守住）。
- **profile 配对成立**：**8 lane 全在 m31f 通道，零 m3 回退** → 全部对 mcode-m31f 清单，无跨 profile 混比。
- **两臂的 `-g2`/`-g3` 别名 = docker 容器名防撞**（`afbench-swev-<task>-<profile>`），端点/模型/key/提示/thinking 全同 —— **非测量语义变更**（红队逐 run 核 24 个 G3 run 的 `harness.db` `spec_json` 证实；本节点核结果行 `harness_commit` 24+24 分布）。
- **本节点自报与工件不一致一处**：node 33059 自报 `lane = "g2-lane0"`（缺 `sprint-` 前缀）、33066 自报 `lane = "g3-lane3"`（缺前缀且与 `sprint-g3-lane3` 路径不符）—— **属节点自报的字符串笔误，工件路径与读数无误**（`results_path` 全对）。

### 42.2 题目级通过矩阵（**本节点亲算**，24 题 × (mcode / G2 / G3)）

| 题 | mcode-m31f | G2 | G3 |
|---|---|---|---|
| astropy-12907 / django-11066 / matplotlib-22719 / xarray-4075 / pylint-7277 / sklearn-10297 / sklearn-11578 / sphinx-10466 | T | T | T |
| astropy-8707 / django-11451 / seaborn-3187 / requests-1766 | T | T | T |
| **pylint-6528** | T | **T** | **F** ← 分歧 |
| pytest-8399 | T | T | T |
| sphinx-7462 | T | **F** | **F** |
| sympy-13877 / sympy-14248 | T | T | T |
| **sympy-14248** | T | **F** | **T** ← 分歧 |
| django-14672 | T | T | T |
| **pylint-6386** | T | **F** | **T** ← 分歧 |
| psf-requests-2317 / pytest-7205 / django-10097 | F | F | F |
| psf-requests-1766 | T | **F** | **F** |
| django-14011 | T | **F** | **F** |
| pylint-4551 | T | **F** | **F** |

**三条账本级结论（须与聚合值一起引用）**：

1. **24 题中仅 3 题两臂分歧**（6528、14248、6386）→ **G3 的净 +1 建立在 3 题分歧的 2:1 上**（G3 多赢 14248、6386，少赢 6528）。按 §19.1③ 的既定纪律（**扩测门槛以「题目级通过集合」判定，n 小处不用聚合值**），**「G3 16/24 优于 G2 15/24」在 3 题分歧的样本上不构成统计结论** —— 本节只登记读数，不代裁优劣。
2. **不对称单向**：**「af 过而 mcode 不过」= 0 题**；「mcode 过而两臂都不过」= 4 题（requests-1766、sphinx-7462、django-14011、pylint-4551）→ **本测集上剩余差距全部在 mcode 一侧**，无反向不对称案（与第一循环 §2.3 的 matplotlib-13989 案已不同）。
3. **4 道共同失守题的形态跨臂不一致**（本节点逐题读结果行 `status`/`turns`）：

   | 题 | mcode-m31f | G2 | G3 |
   |---|---|---|---|
   | `psf__requests-1766` | T | F / **completed** / 59 轮 | F / **completed** / 57 轮 |
   | `sphinx-doc__sphinx-7462` | T | F / **completed** / 51 轮 | F / **wall_timeout** / 36 轮 |
   | `django__django-14011` | T | F / **wall_timeout** / 29 轮 | F / **completed** / 66 轮 |
   | `pylint-dev__pylint-4551` | T | F / **wall_timeout** / 67 轮 | F / **completed** / 57 轮 |

   ⇒ **4 题中 3 题两臂形态不同（7462 / 14011 / 4551），只有 1766 是两臂同型的 completed-but-F**；**「补丁质量面 vs 预算/墙钟面」不能按臂一刀切**——14011 与 4551 是「G2 墙钟切、G3 自然完赛仍未解」，7462 是「G2 自然完赛未解、G3 墙钟切」。**唯一跨臂稳定的失败面是 7462 与 1766 的 completed-but-F（补丁质量面）**，下一轮归因须按此四象限写，**不得合并成单一原因**。

4. **⚠ 弱通过口径会翻转「最优臂」标识（本节点亲算，下一轮必须先定判读规则）**：把 `status=wall_timeout` 但判过的题单列为**弱通过**后：

   | 口径 | G2 | G3 |
   |---|---|---|
   | 全部通过计入（§43.1 口径） | **15/24 = 62.50%** | **16/24 = 66.67%** |
   | **仅自然完赛（completed）计入** | **13/24 = 54.17%**（弱通过 2 题：6528、3187） | **11/24 = 45.83%**（弱通过 5 题：22719、3187、10466、8399、6386） |
   | **最优臂** | 全部计入时 **G3** 领先；仅自然完赛时 **G2** 领先 | ← **排序翻转** |

   ⇒ **「最优 = G3 直觉组合」这一标识是在「wall_timeout 判过也计入」口径下成立的**；G3 的净 +1 伴随**多 3 个墙钟绑定的通过**。**两种口径下两臂都远未达成 ≤5pp（差距 21.67pp 与 33.33pp）→ 终判「未达成」不受影响，但「最优臂」必须随口径标注**（与 §24.3「判读规则必须重写，否则验证批读错牌」同类）。**本账不代裁采哪一档**，登记为红队/运营者的判读规则待决项。

## 43. 终判（达成与否 + 差距）

### 43.1 正确读数（本节点亲算，与红队订正后逐位一致）

| 口径 | af 通过 | 行数 | af 通过率 | mcode 配对期望 | mcode 通过率 | **差距** | **判定** |
|---|---|---|---|---|---|---|---|
| **G2 激进移植**（人格+thinking+250 轮+pipefail） | 15 | 24 | 62.50% | 21 | 87.50% | **25.00pp** | **未达成** |
| **G3 直觉组合**（v8 底+pipefail+thinking high，**无人格**） | **16** | 24 | **66.67%** | 21 | 87.50% | **20.83pp** | **未达成** |

- **判据**：af 通过率 ≥ mcode − 5pp ⇔ **af ≥ 20/24**。G2 = 15、G3 = 16，**两臂都差 ≥ 4 题** → **终判：军令状未达成**。
- **最优变体（订正后）= G3 直觉组合**，**差距 20.83pp（> 5pp）**。
- **⚠ 最优臂标识的判读依赖（必读）**：上表按「`wall_timeout` 判过也计入」计。**若只计自然完赛，则 G2 13/24 = 54.17% > G3 11/24 = 45.83%（排序翻转）**，但**两臂差距分别为 21.67pp 与 33.33pp，均 > 5pp → 「未达成」这一终判在两种口径下都不变**（详见 §42.2 结论 4）。
- **全池 headline（判据要求同时报）**：mcode m31f **115/120（95.83%）**、m3 **94/120（78.33%）**；本轮 af 读数只在 24 题测集上（62.50% / 66.67%），**不可与全池 headline 直接相减**。

### 43.2 ⚠ 脚本自报终判**不可引用**（本节点已定位根因并复现）

- **脚本自报**（`dwf_event` seq 92）：「终判：G2 15/24（对 21），**G3 9/12**（对 11）；**最优=G2 激进移植**，差距=**25.0pp**」；metrics 制品 `report#1`（node 33109）= `af_best=15 / mcode=21 / gap_pp=25`。
- **根因（本节点复现定位）**：脚本 `.zcode/workflow-drafts/对齐冲刺-三组.dwf.ts:154` 的 `agg(g)` 用**精确相等**筛选 lane：`idxs = settled.map((x,k) => (x.group === g ? k : -1))`。
  - 8 条 lane 节点的自报 `group` 字段**并非全为 `"G2"`/`"G3"`**：node **33063**（g3-lane0）自报 `"G3（3组=直觉组合：v8 底+pipefail+thinking high，scaffold v8-g3）"`、node **33066**（g3-lane3）自报 `"g3"`（小写）。
  - ⇒ `agg("G3")` 只命中 **settled[5]（node 33064, g3-lane1）** 与 **settled[6]（node 33065, g3-lane2）** → **passes 5+4=9、rows 6+6=12、mcode 期望 6+5=11**，即 **9/12 对 11**。
  - ⇒ `best = g2agg.pass(15) >= g3agg.pass(9) ? g2agg : g3agg` → **误选 G2 为「最优」**，并把 **G3 的 9/12 当成 G3 的臂级读数**。
- **订正后（本节点亲算 + 红队独立复现，双向一致）**：**G2 = 15/24（−25.00pp）、G3 = 16/24（−20.83pp）、最优 = G3、差距 20.83pp**。
- **偏差方向**：脚本自报**高估 G3**（75% vs 全臂 66.67%）**且误判最优臂**（G2 而非 G3）。
- **终判方向不变**：两臂均未达成 ≤5pp → **「未达成」这一结论不受该缺陷影响**；但**呈报数字与「最优臂」标识必须更正后方可对外**。
- **与红队 issue ① 的一处差异（本节点为准）**：红队把 9/12 的来源记作「**lane1 + lane3**」；**本节点按 `settled` 下标复现为「g3-lane1 + g3-lane2」**（node 33064 + node 33065，`group` 恰为 `"G3"` 的两条）。**数字 9/12、方向（高估 G3）与结论红队正确；被纳入的两条 lane 归属以本节点为准。**

### 43.3 终判一句话（订正后）

> **对齐冲刺终判：未达成。** 24 题非 S 档分层测集上，**G3 直觉组合 16/24 = 66.67%**（最优，**按「wall_timeout 判过也计入」口径；若只计自然完赛则 G2 13/24 反超，排序翻转，但两臂差距 21.67pp / 33.33pp 均 > 5pp，未达成的终判不变**）、**G2 激进移植 15/24 = 62.50%**，**mcode 官方 m31f 配对期望 21/24 = 87.50%** → **差距 20.83pp（> 5pp）**，达标线 **≥20/24** 未及；thinking **可开**（请求层 1 行改动，48/48 行实证 `reasoning_tier=high`）；**红队 `rejected`**（3 条 issue，1 条实质为聚合缺陷）；脚本自报的「G3 9/12 / 最优=G2 / 25.0pp」**须更正**。

## 44. 红队审（红队·冲刺审，ask#6 / node 33110，step-5-preview$high）

**裁定：`rejected`（3 条 issue）**。红队自述：三件快审全部亲跑，**未改任何文件、未触碰 af 工作树与在飞工作流**。

### 44.1 三条 issue 原文照录（不失真）

| # | 性质 | 原文要点 |
|---|---|---|
| **①** | **判据计算缺陷·实质** | 「**G3 行数/过题数不可从 lane 原始数据复现**：ask 载 G3={pass:9, rows:12}，但 `/tmp/sprint-g3-lane{0,1,2,3}/results.jsonl` 实为 4 lane×6 行=24 行、last-row 复算 **16/24=66.7%**（lane 分布 3/5/4/4，与各 lane.log 末行 'resolved 3/5/4/4' 一致）。stated 9/12 只能由两条 lane 复现；另两条（profile 别名 'mavis-m31f-g3'）被无说明剔除。该别名在 `~/workspace/af-wt-sprint-g3/crates/af-bench/src/main.rs:344-350` 自证为**容器防撞基建**（端点/模型/key/提示词/thinking 与 mavis-m31f 完全一致，'非测量语义变更'），且逐 run 亲验 24 个 G3 run 的 `harness.db` `spec_json`：system 提示词、`reasoning_tier=high`、`harness_commit=4a0a902e` 全部相同。**不存在能同时推出 G2=15/24（含 -g2 别名 lane）与 G3=9/12（剔 -g3 别名 lane）的一致计数规则**。偏差方向为**高估 G3**（75% vs 全臂 66.7%）；因两臂均未达 af≥mcode−5pp（G2 −25pp、G3 全臂 −20.8pp），**终判方向不变，但读数须更正后方可呈报**。」 |
| **②** | **判据计算缺陷·文档** | 「ask 证据串自相矛盾：'af 对 m31f 配对达标=过题≥16/24' 与同句 'af 须 ≥ 19.8/24 即 20 题' 冲突——87.5%−5pp=82.5%×24=19.8，正确达标线为 **≥20/24（至多落后 1 题）**，'≥16/24' 为误写（operative 的 20 题正确）。」 |
| **③** | **文档小瑕·不影响数据** | 「`exclusion_note` 对 D2 跳题的描述串行：'跳过序号 11 的 psf__requests-2317 之外仅此一跳'不准确——实际按序**仅跳过序号 11 的 `sympy__sympy-17318`**，`psf__requests-2317` 在序号 4 且被选中；按 stride=12/11、`floor(i*stride)` 复现命中序号 0..10，与冻结集逐位一致，**选中集合本身无误**。」 |

### 44.2 红队亲跑的通过项（原文要点，本节点复核认可）

- **①测集剔除口径 = PASS**：120 题包与 `bench-official-mcode-{d1,d2,d3}-m31f/runs` 双向 **bijection**（runs-only=0, pkg-only=0，60+40+20=120 唯一）；S 档 74 条正则解析自 `计划/研究组/mcode考古份额-量化.md:70-77`，唯一映射 74/74（S in d1/d2/d3 = 31/28/15）；非 S 池 D1=29 / D2=12 / D3=5；复现选中集与冻结件逐位相同；**frozen24 ∩ S74 = ∅**。
- **②last-row = PASS**：`diff -rq` 验证快照与六个 live 官方目录逐一 identical；`md5sum d3-m31f/results.jsonl = cd6a74c36416a16204847f55925983d3` 与源一致；24 题上 m31f 21/24=87.5%、m3 20/24=83.3%，与冻结件列表 **diff=∅**；全池 m31f 58/38/19=115/120、m3 50/31/13=94/120。
- **③lane 亲读抽验**：G2 各 lane 3/6/3/3=15/24=62.5%（与 stated 15 一致）；24 题与冻结集**双向相等**（tasks−frozen=∅、frozen−tasks=∅）；mcode m31f 同 24 题=21/24（gap 25pp 属实）；**48 行全部 `judge_mode=clean`、`reasoning_tier=high`**；判分脚本 `eval.sh` 为标准金测集判分（checkout base + apply 测试补丁 + pytest），**判分链未混入变体参数**；**全部 lane 为 m31f 通道（无 m3 回退）**，profile 配对成立。
- **④变体指纹 = PASS**：**G2 人格真在场**——`runs/harness.db` `spec_json` 的 system（1194 字符）与 `af-wt-sprint-g2/crates/af-bench/src/main.rs:816` 的 `SWEV_SYSTEM_PROMPT` **逐字节相同**（`prompt==actual` True），含 B2 移交件三条指纹句，24/24 G2 run 全携该提示；**G3 无人格**——其 system 与 v8 基线逐字相同（`af-wt-sprint-g3/main.rs:731` == `af-wt-align2/main.rs:724`），24/24 G3 run 无 MCode 串；**thinking high**：48/48 行 `reasoning_tier=high`，profile 映射 g2 `main.rs:429` / g3 `main.rs:350` → `ReasoningTier::High`，装配层 `endpoint.rs:296-297` `thinking enabled/budget=4096`、`max_tokens 32000+4096=36096`；**pipefail 真在场**：`git show` 亲验实际运行的 `harness_commit`（G2 `bd4e2799`、G3 `4a0a902e`）的 `tb.rs` 均含 `set -o pipefail; ` 桥接前缀（各 9 处，移植自 588382d p01）；**250 轮**：`main.rs:1053`（G2）/ `:964`（G3）`max_turns:250`；提交信息自证变体定义（`ef474ee` / `4a0a902`）。
- **红队给出的 corrected 读数（供终判更正）**：「G2=15/24=62.5%（mcode 87.5%，−25pp）、G3=16/24=66.7%（mcode 87.5%，−20.8pp），达标线 **≥20/24**——**两臂均未达成，冲刺终判方向（未达成）不变**。」

### 44.3 本节点对红队意见的复核与订正

- **issue ① 成立**，根因已由本节点定位到脚本 `.dwf.ts:154` 的 `x.group === g` 精确匹配（**红队只描述现象，本节点给出机制**）；**「被纳入的两条 lane」以本节点复现为准：g3-lane1 + g3-lane2**（红队记作 lane1+lane3，见 §43.2）。
- **issue ② 成立**：达标线 **≥20/24**（本节点独立算得 87.50% − 5pp = 82.50% × 24 = 19.8 → 20 题）。
- **issue ③ 成立**：本节点独立复现 —— D2 stride=12/11 命中序号 `[0..10]`，唯一跳过 `sympy__sympy-17318`；`psf__requests-2317` 序号 4 被选中。**标定员 `exclusion_note` 的描述须改为「仅跳过 sympy-17318」**（选中集合本身无误）。
- **红队未发现、本节点补充的一条**：标定员把 mcode 侧 as-of 目录记作「`cp -a` 快照」，**实为 symlink 目录**（§39.3）——**数字今日仍可复现**（live 目录 mtime ≤ 10-22 15:51，本节点现读 diff=∅），但「快照」措辞须订正。

## 45. 遗留（1 组四循环并行结果并入方式）

### 45.1 1 组的结果（**本节点亲读工件**）

- **run**：`dwfrun-981b3ebc-b3a2-4019-a436-2390868e1538`（名「研究组①对齐组·第四循环」，2026-10-23 07:06:08 起、13:02:35 `completed`、`spent_tokens=51,929,649`；**三审 `confirmed`**）。
- **①v8 采纳成立**：25775 复验 **2/2 过**（`/tmp/align4-v8/lane-25775/results.jsonl`，scaffold=v8、judge_mode=clean、attempts=1、gate=ok、http_retries=0、status=completed、reward=true；a1=41 轮/458,495ms/agent.diff 7641B、a2=59 轮/604,655ms/10052B，f2p 7/0 p2p 89/0）⇒ **S002/S118 观测折叠罪责成立，三循环归因闭环**；另 4 题抽查无退步（严格 5/5 门槛下 1766 仍不过，已如实计入）。**新研究基线 = `fix4-align2-v8@50ba8a8`**（**正是冲刺 3 组的「v8 底」**）。
- **②双候选探针各 4/5**（**本节点逐行亲核**）：`/tmp/align4-probe-p0/results.jsonl`（C2「墙钟压力下补丁先行」，commit `6dccda5`）与 `/tmp/align4-probe-p1/results.jsonl`（C1「失败后转向纪律」，commit `8c670f2`），**两臂题集相同、各 5 行、各 4/5、未过题同为 `sphinx-7462`**；**scaffold 均为 `v9`、`reasoning_tier` 均为 `off`**。

### 45.2 为什么 1 组结果**不能直接并入** 24 题主表（三条，本节点亲核）

| # | 障碍 | 证据 |
|---|---|---|
| ① | **题集不同**：1 组探针 5 题 ≠ 冲刺冻结 24 题，**交集仅 3 题**（seaborn-3187、sphinx-7462、sympy-13877） | 本节点算：p0/p1 的 task_id 集合 ∩ 冻结 24 = {3187, 7462, 13877}；另 2 题（pytest-10081、sklearn-10908）在 D1 非 S 池内但**未被 stride 采样选中**（本节点复现的 D1 跳过清单含此 2 题） |
| ② | **判据基线不同**：1 组的「4/5」是 **5 题中 4 题**口径，其分母与 mcode 期望都不是 24 题制的 21/24 | 1 组 5 题上 mcode-m31f 的期望过题数与 21/24 不可直接换算；「4/5 = 80%」与「16/24 = 66.67%」**是两个不同题集上的通过率，不是同一把尺** |
| ③ | **臂别因子不齐**：1 组 = scaffold **v9** + `reasoning_tier=off`；冲刺两臂 = scaffold **v8-g2 / v8-g3** + `reasoning_tier=high` → **scaffold 与 thinking 双因子同时不同**，交集比较是**混淆对比** | 本节点逐行读 `scaffold`/`reasoning_tier`/`harness_commit` 字段 |

### 45.3 交集 3 题子集配对（**本节点已算好，可立即引用**）

| 题 | mcode-m31f | 1 组 p0（6dccda5, v9, off） | 1 组 p1（8c670f2, v9, off） | G2（v8-g2, high） | G3（v8-g3, high） |
|---|---|---|---|---|---|
| `mwaskom__seaborn-3187` | T | T | T | T | T |
| `sphinx-doc__sphinx-7462` | T | **F** | **F** | **F** | **F** |
| `sympy__sympy-13877` | T | T | T | T | T |
| **小计** | 3/3 | **2/3** | **2/3** | **2/3** | **2/3** |

⇒ **交集上四臂全等 2/3，零区分度**：1 组的「双候选各 4/5」**既未证明优于、也未证明劣于**冲刺两臂；而唯一共同失守题 `sphinx-7462` 在四臂上**全部不过** ⇒ **再次坐实 §35.3 的登记「7462 的失败面不在提示词/预算/墙钟层」**（本次是四臂、四种因子组合的第三次独立复现）。

### 45.4 并入方式（三选一，**本账不代裁，属红队/运营者裁决**）

| 方案 | 做法 | 代价 / 收益 |
|---|---|---|
| **(A) 不并入，另立口径** | 1 组结果留在 §30–§35（第四循环账）内，冲刺节只记「并行旁证」，**不进 24 题主表** | 军令状 headline 仍只有 2/3 组；但口径最干净、零混淆 |
| **(B) 交集子集表（已算好）** | 引用 §45.3 的 3 题表，**只作否定性证据**（「1 组结论在交集上不能支持冲刺两臂」） | 零额外成本；但样本 n=3、无区分度，信息量有限 |
| **(C) 重跑 1 组最优臂到冻结 24 题** | 在 `fix4-align2-v8@50ba8a8`（或 1 组最优 commit）上用**同 24 题集、同 m31f、同 clean 判分、同 8 lane 同口径**跑一遍 | **唯一能得到「同题同判据可比」结论的路径**；成本 ≈ 一次冲刺跑批（本轮 8 lane 实耗 ≈ 2h45m，12:13 起批 → 15:10 收口），须在 **17:05 时限外另立窗口**；走此路须**冻结「底 = 50ba8a8」并把因子差异（1 组叠 C2/C1 行为纪律、冲刺叠 pipefail+thinking）显式列为协变量**，否则仍是混淆对比 |

**并入时必须遵守的三条纪律**：

1. **口径纪律**：1 组的任何数字写进冲刺节时，**必须标明题集（5 题 vs 24 题）、scaffold（v9 vs v8-g2/v8-g3）、`reasoning_tier`（off vs high）** 三项，缺一不可混引。
2. **不得写「1 组 4/5 = 80% > 冲刺 G2 62.5%」这类跨题集相减**（第一循环 §19.1③ 的既定纪律：跨代际/跨题集不可直接相减）。
3. **扩测理由只能写「未追平」**（§19.2⑭）：本轮**仍有未探候选** —— 冻结 24 题之外，非 S 池 D1 还剩 21 题未被采样（本节点复现的 D1 跳过清单）、D2 还剩 1 题（`sympy-17318`）；**严禁写「无剩余候选」**。

### 45.5 其他遗留（据本节读数新增，须下一轮接手）

1. **呈报口径必须先更正再对外**：脚本 `report#1` 制品（`af_best=15/mcode=21/gap_pp=25`）与 `dwf_event` seq 92 的「最优=G2」**须改为「af_best=16（G3）、mcode=21、gap_pp=20.8」**（§43.2）。**本账不代改制品**（未写任何 run 工件）。
2. **脚本聚合缺陷须修**（`.zcode/workflow-drafts/对齐冲刺-三组.dwf.ts:154`）：`x.group === g` 应改为**按 lane 名/臂前缀归组**（如 `x.lane.startsWith("sprint-g3")`），或**在 lane prompt 中强制 `group` 字段取固定枚举**。**同类缺陷在第四循环/第三循环脚本中未检出，但本轮证明「节点自报的分组字段」不可信** → 下一轮任何按自报字段聚合的脚本都须改为按**路径/臂前缀**聚合。
3. **共同失守 4 题需二分归因**（§42.2 结论 3）：`sphinx-7462`（补丁质量面，四臂全败，第三次复现）、`requests-1766`（补丁质量面，两臂同型 completed-but-F）、`django-14011`（预算/墙钟面，G2 wall_timeout）、`pylint-4551`（两臂形态不同）。**这 4 题正是下一轮「差距画像」的靶子**。
4. **1 组未探的 2 题**（`pytest-10081`、`sklearn-10908`）在冲刺 D1 非 S 池内但未被 stride 选中 —— 若走 §45.4 的方案 (C)，这两题会被自然覆盖。
5. **`swev.rs:127` 的 `p.contains("test")` 子串误报仍未修**：本轮 `pytest-7205` 两臂均 `gate=test_edit`（而 7205 是 mcode 也不过的一题）、`pytest-8399` 两臂均判 **T** 却带 `gate=test_edit` → **该误报在本轮被 48 行读数再次实证**（第四循环 §35.2 ⑧ 仍未办）。
6. **墙钟与轮次双预算的余量 —— 弱通过须单列（与 §24.3「判读规则必须重写」同类）**：**G3 的 16 个通过题中有 5 个是 `status=wall_timeout` 判过**（22719、3187、10466、8399、6386），**G2 的 15 个通过题中只有 2 个**（6528、3187）→ **G3 的净 +1 伴随多 3 个墙钟绑定的通过**；**仅计自然完赛则排序翻转（G2 13/24 > G3 11/24，§42.2 结论 4）**。另 `sympy-14248` 的 G3 通过是**自然完赛 176 轮**（G2 同题 wall_timeout 59 轮）——**G3 的长跑余量与墙钟余量都在被消耗**。下一轮须先定「T 且 wall_timeout 是否计过」的判读规则，再谈最优臂。

## 46. 本节明确未做的事（供下一轮判断可信边界）

1. **未跑** `cargo build` / `cargo test` / `cargo fmt` / `clippy` —— 本节所有「af-bench 18/18 + af-harness 57/57 全过」「3 枚单测亲跑过」「release 重建 1m16s 零警告」字样**均署实施员节点**（33049 / 33050），**本节点未复跑**。
2. **未跑**任何判分、任何新题、任何复跑、任何扩测 —— 本节点只读了 8 个 `results.jsonl`（48 行）、8 个 lane `.log`、2 个 smoke `.log`、冻结件与候选件 JSON、源码与 git 历史。
3. **未核**网关侧 thinking **穿透**（mavis `llm-call.json` 回显 `thinkingLevel=high`）—— 本节点只核了 af 侧结果行 `reasoning_tier=high` 字段与源码映射。
4. **未逐 run 亲验** 48 个 `harness.db` 的 `spec_json` 全字段 —— 红队亲验了 24 个 G3 run；本节点验的是**结果行**的 `scaffold`/`reasoning_tier`/`harness_commit`/`judge_mode`/`attempts` 字段分布（48/48），未打开 run 目录。
5. **未做** 1 组最优臂在冻结 24 题上的重跑（§45.4 方案 C）、**未做** m3 档案复跑、**未做** glm5.3f / step-5 档案对齐（第四循环 `notCovered` 亦明列「glm5.3f/step5 档案对齐未开始」）。
6. **未改**判分链、**未动**任何 af 工作树（生产树 HEAD 仍 `94cd1923c34842983049bce5f97b3dcb6c7c348b`、仅 5 个既有未跟踪 `poc/` 目录）、**未改**任何分支、**未改** `report#1` 制品、**未改**任何 run 工件（§45.5 ① 的制品更正是给下一轮/红队的工作项，不是本节点的动作）。
7. **未代裁**：1 组并入方式三选一、「最优臂」的对外呈报口径、「T 且 wall_timeout」的弱通过是否单列、7462 是否立项、军令状 headline 的最终呈报 —— **均属红队/运营者裁决**。

---

*第五循环（对齐冲刺）账毕。本节由状态记账员（MiniMax-M3.1-Flash-Preview）于 2026-10-23 15:3x CST 追加写入 `计划/研究组/对齐组-state.md`；下一轮请从 §43.2（脚本终判数字不可引用、根因已定位）、§43.1（订正后读数 G2 15/24 / G3 16/24 / 差距 20.83pp / 达标线 ≥20/24）、§42.2（题目级矩阵与 3 题分歧的脆弱性）、§44.3（红队三条 issue + 本节点补充的 as-of symlink 一条）、§45.4（1 组并入三方案）开始；引用本节任何数字须带 as-of 与臂别，且**不要**引用脚本自报的「G3 9/12 / 最优=G2 / 25.0pp」。*

## 第五循环·冲锋令二次冲刺（2026-10-23 23:37 → 10-24 04:0x，厂长主导快闪编队）

**变体周期记档（g3c，不采纳）**
- 假设：G3 之上的败题受三重工程件拖累——墙钟帽 1800s 截断（7462）、改测试踩门（7205）、考古膨胀（6528/7462/7205 三题诊断 40-95% 预算烧在 git fsck/pip cache 考古）。
- 干预：g3b（墙钟 1800→3600 @main.rs:970-972 + 测试禁改句 @main.rs:731）→ g3c（+反考古句 @main.rs:747，SWEV_INSTANCE_PROTOCOL 无网条目尾部）。二进制 sha：g3=7a87876c/g3b=7a2d5814/g3c=d001f0fb（均在 /home/pan-ding/workspace/af-wt-sprint-g3/）。
- 四靶单题诊断复跑：6528 ✓复现（非稳定题，f2p 4/4）；4551 ✗三振（**fix1 之"过"=容器网络可达 GitHub curl 拉上游补丁，effects.db seq 42000-46000 直证——"fix1 证无未来信息可解"前提作废**，亦为 af 侧网络泄漏首例）；7462 ✗（**墙钟假设被 g3b 实测证伪**：3600s 结果逐位同 1800s，真因=隐藏规格两处：`(`+`)` 两节点渲染+pycode/ast.py::unparse 漏改）；7205 ✗（**"改测试踩门"前提作废**：三 run 均未改测试，gate=test_edit 系门子串误报（swev.rs:128 contains("test") 误杀 src/_pytest/*，登记 D-41），真因=条件 repr vs 上游无条件 saferepr 语义错）。
- confirm（g3c×冻结 24 题 k=1×8 shard，/tmp/align2-confirm/，00:57-04:0x）：**16/24=66.7%**。相对 G3：6528/6386 守住、**14248 回归（wall_timeout 撞 3600s 帽）**、净 Δ=0。
- 判定：**不采纳 g3c**（Δ0+回归+墙钟成本×2）。G3（v8 底+pipefail+thinking high，sha 7a87876c）仍为最优=16/24。
- **行为层重要副产物**：反考古句实证有效（考古占比 40-95%→~10%，harness.db user_message 直证句子进提示词）但分数不动——**"考古膨胀"不是 confirm 期瓶颈，"首编辑过晚"才是**（14248 首源码编辑 t69@96% 墙钟=分析瘫痪：grep 39% 命令墙钟+纯文本思考轮；对照 3187 首编辑@20% 墙钟→patch 早落盘→长题能过）。ARCHAEOLOGY_PATTERNS 现状=软警告不拦+漏网严重（git show/git log --all/pip cache/-maxdepth 拆词全逃逸）。
- **下一循环主件（已裁）**：①预算整形——40% 墙钟仍无 /testbed 源码写入→harness 强插"立即落最小补丁"系统指令（直接打首编辑过晚）；②D-41 门误报修复（路径分量精确匹配）；③30min 文本 vs 3600s 代码不一致清理。7462/4551 类隐藏规格题的"agent 可否见 gold 断言"边界问题→运营者裁决，不自行放宽。
- 数据面：/tmp/align2-{4551,6528,7462,7205}/（四靶）+ /tmp/align2-confirm/（confirm 8 shard）；清场待终报归档后执行。

### 第五循环附章·g4 变体周期（字节对齐包装，10-24 04:4x-07:1x，不采纳）

- **假设**：mcode 首条消息形态（issue 原文直开+中文短指令尾，原文占比 74-94%）是"回忆触发器"；af 的包装（Repository 头+2.7KB 英文协议）打断回忆。
- **干预**：g4（sha e5736bb9）=swev.rs prompt() 直返 problem_statement + SWEV_INSTANCE_PROTOCOL 整体替换为 mcode 中文件逐字件（脚本断言 byte-identical）+TASK_COMPLETE 紧凑尾；反考古句/禁 changelog 句/英文长协议全删。首条消息形态经 harness.db 验证=对齐生效（issue 直开、全文 1702B、无英文残留）。
- **探针**：4551 false（19.1min/168 turns，无快过签名）/ 7205 false（42.2min/86 turns）/ 7462 run_failed（本地磁盘配额瞬态杀 gateway，非任务判定）。**0/3，不采纳。**
- **判决与综合（v4）**：包装假设不是"被证伪"而是**被净化审计釜底抽薪**——审计证明 4551/7462/7205 的 mcode 净化过题全走宿主工件通道（pr4551.tar.gz/宿主 pytest 9.1.1/Sphinx-3.1.0 wheel），**本不存在"格式触发的权重回忆"可供移植**；"快过签名"实为"盘上抄答案签名"。**昨夜 16.7pp"引出效率份额"整体改判为环境泄漏**（宿主影子三通道）。真权重回忆=双侧对称小份额（af S4 无通道纯权重；mcode 干净桶 14672 亦有记忆自述）。**干净题上两 harness 判决逐题全同（v3 n=13/10 双口径）**——运行时循环层（tool call/呈现）假说失去待解释对象，降级为非必要。副产品：被删"禁 changelog"句显净正价值（4551 解禁后去改 ChangeLog/whatsnew 烧轮次），G3 纪律栈维持不动。**G3（sha 7a87876c）仍为最优配置。**
