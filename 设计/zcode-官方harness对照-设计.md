# 设计 · zcode 官方 harness 对照线（step-5）— SWE-V S1 全 120 题

> 本文是"官方 harness 对照"第三条线（zcode 线）的设计与操作手册。
> 运营者指令（2026-10-21）：用 **zcode 工作流**（zcode 官方 agent 脚手架）跑 step-5 档案，重做 S1 全部 D1-D3 120 题，与 af-harness 对照。
> 分工边界：**本线准备子代理只备件不启动**（子代理禁嵌套 CreateWorkflow）；由主代理一键 CreateWorkflow 启动。
> 最后更新：2026-10-21 ｜ 状态：**待主代理启动工作流**

---

## 1. 定位与口径

### 1.1 四方对照格局（同题集 / 同判分链，互不混算）

| 线 | profile | scaffold | 120 题读数 | 判分 |
|---|---|---|---|---|
| af-harness（我方） | glm-cp / kimi-k3 / m31f 等 | af-harness fix1 | 44-47%（fix2 A/B 在跑） | 同下 |
| **本线（zcode 官方）** | **zcode-step5** | **zcode-workflow** | **待跑** | 同下 |
| codebuddy 官方 | deepseek-cb | codebuddy-npc | 69.2%（83/120） | 同下 |
| mcode 官方 | mcode-m31f / mcode-m3 | cal2 蓝图复刻 | 在跑（另一子代理） | 同下 |

判分链全同：本地 sweb.eval 官方镜像容器 + GNU patch -p1 --fuzz=3 应用 + 官方 eval_script + swebench 4.1 swev-judge（含 xarray env-yml 合成兜底）。**resolved 数跨线直比**。

### 1.2 模型与脚手架

- 模型：`new-provider/step-5-preview$high`（运营者指定；经 CreateWorkflow 的 `subagent_model` 传入，**脚本内不钉模型**，留 Amend 换档自由）。
- 脚手架：zcode 官方动态工作流（dynamic-workflows），每题一个独立子代理，1 ask/题。

## 2. 判分衔接：tools/zc-judge-collect.sh

### 2.1 路径约定（全链唯一的交付物接口）

| 件 | 路径 |
|---|---|
| 题目数据源 | `/tmp/swev-s1/<instance_id>.json`（12 字段，problem_statement/test_patch/eval_script 等） |
| 工作区 | `/tmp/zc-ws/<instance_id>/`（**符号链接** → 真身 `/home/pan-ding/zc-ws/`，见 §3.1 磁盘裁决） |
| 子代理交付物 | `/tmp/zc-ws/<instance_id>/model.patch`（`git diff` 产出） |
| 结果账本 | `/tmp/bench-official-zcode-step5/results.jsonl`（profile=zcode-step5 / scaffold=zcode-workflow） |
| 逐题判分产物 | `/tmp/bench-official-zcode-step5/<instance_id>/{apply.log,eval.log,judge.json,collect.log}` |

### 2.2 复用与分工

zc-judge-collect.sh **不重写判分链**，逐题调用 tools/cb-judge.sh（deepseek-cb 120/120 验证过的同一条），只做三件增量事：

1. **收集**：校验 model.patch 存在且非空（缺 → 终态 no_patch 行，不算基础设施错）；
2. **区分失败性质**（这是对 cb-run.py 教训的直接吸收）：
   | gate | status | 语义 | 重跑行为 |
   |---|---|---|---|
   | ok | completed | 官方判分完成（reward=resolved） | 跳过 |
   | no_patch | completed | 模型没交卷（**真实结果，终态**） | 跳过 |
   | apply_failed | completed | 补丁打不上（**模型责任，终态**） | 跳过 |
   | image_missing | **pending** | eval 镜像不在本机 | 自动重判 |
   | judge_error | **pending** | 判分链基础设施错（rc 非 0/2 或 judge.json 空） | 自动重判 |
3. **落账**：results.jsonl 追加一行（flock 防并发互踩），字段仿 deepseek-cb 行（suite/task_id/profile/trial/reward/status/scaffold/gate/attempts/turns/model_calls/tokens/agent_wall_ms/verifier_note）+ solve自报摘要入 verifier_note。**幂等断点续跑**：已有 status=completed 行的题直接 SKIP（与 cb-run.py preseed 口径一致）。

### 2.3 已验证证据（2026-10-21 实测）

- 全链烟雾测：借 deepseek 已验证补丁（astropy-12907）走 `--one` 全链 → `resolved=true, f2p 2/2, log_parsed=true`，落账行格式正确，rc=0。
- 失败路径：no_patch 终态落行 + 幂等重跑 SKIP；fd 未开致 cb-judge 失败时正确落 judge_error/pending 行 rc=3（顺手修掉的真 bug：cb-judge 输出曾指到未打开的 fd 3）。
- `--status` 分档汇总（终态/resolved/待重判）可用。

## 3. 工作区预置：tools/zc-prep-ws.py

### 3.1 磁盘裁决（df 核对的直接产物）

**/tmp 是 tmpfs（7.5G，当时余 3.2G）**，120 仓浅克隆（实测 4G+）放不下且 tmpfs 吃内存——真身落 `/home/pan-ding/zc-ws`（/ 分区 468G 余 112G），`/tmp/zc-ws` 建符号链接维持运营者指定路径约定。脚本含磁盘闸（真实根余量 <8G 拒开工）。

### 3.2 结构与幂等

```
/home/pan-ding/zc-ws/<instance_id>/
├── repo/       git 浅克隆（init + fetch --depth 1 origin <base_commit> + checkout FETCH_HEAD）
├── problem.md  problem_statement 原样落盘（刻意不带 test_patch/fail_to_pass/hints_text——防作弊面）
├── meta.json   instance_id/repo/base_commit/image/tier
└── .ready      就位标记（重跑脚本：.ready + HEAD==base_commit 即缓存命中跳过）
```

- 浅克隆够用的依据：**判分在 eval 镜像容器做（/testbed 合成检出），本机 clone 只供 agent 读源码写 diff**——agent 只需 base_commit 单棵树，单 commit fetch 即足（每仓 ~15-60MB）。
- 预置证据（2026-10-21 实测）：**120/120 全就位**（D1 60 用时 ~42s；D2/D3 workers=4 随后收齐，零失败），抽样 HEAD==base_commit、工作树干净、problem.md 首行与题目一致。合计占盘 ~4G。

## 4. 工作流脚本：.zcode/workflow-drafts/zc-step5-swev.dwf.ts

### 4.1 拓扑（四相位）

```
逐题收集判分（官方容器判分台）   ← future 先启：channel + 2 工位 for-await 消化
  ↑ 判分队列（每题恰好 send 一次，含失败题）
求解 D1 档 60 题（简单） → 求解 D2 档 40 题（中档） → 求解 D3 档 20 题（困难）
  每档 = Promise.all 扇出，每题一个命名子代理「解题·<instance_id>」
pending.close() → await judging（汇合：需全部题判分才出账）→ return WorkflowReport
```

- 看板：`progress`（board，done/partial/stuck 三列）+ `judged`（table，逐题判分口径）。逐题 report 流出（§10 抢救语义：中途死跑已判的题不丢）。
- 终产物：WorkflowReport（conclusion + findings + verified + notCovered），越界声明/stuck/待重判各自成 findings。

### 4.2 判分选型：逐题流水判分（而非攒批末判分）

**选逐题流水**，理由三条：

1. **资源护栏**：判分容器安静低并发（JUDGE_WORKERS=2）正是 cal2"判分须安静串行防 OOM 假失败"教训与本机判分峰值 889MiB 实测的落地——攒批末一次 world.run 要一次吃下整档时长（60 题 × 最长 21 分钟，单次 world.run 超时不可控且粒度全无）。
2. **断点粒度**：逐题 world.run 逐条入运行日志，resume/Amend 缓存逐题复用；攒批一行日志挂了整批重跑（脚本虽幂等，时间白付）。
3. **抢救**：每题判完即 report，运行中途死跑也保住已判的题与看板进度。

并发的分配：**求解并发不设限**（运营者指令：勿设 max_concurrency，运行时自适应）；**判分并发固定 2**（这是判分容器资源闸，不是子代理并发限——JUDGE_WORKERS 常量在控制流里，Amend 可免缓存改）。

### 4.3 Amend 友好性设计

- 子代理命名 `解题·<instance_id>`（120 个唯一名），ask 文本只含每题事实（iid/repo/路径），**无脚本级可调常量**——改 SYSTEM 或 ask 才会破缓存，改 JUDGE_WORKERS/JUDGE_TIMEOUT_MS 不破。
- 判分调用的 args 数组只含 iid 与 solve 自报摘要（≤200 字符切片），保证重放确定性。

### 4.4 防作弊与越权（红线落地）

- 作弊禁区写进 persona：`/tmp/swev-s1/`（内含 test_patch 与 fail_to_pass）任何接触即评测作弊；工作区文档、判分账本、其他题目目录全部禁入。
- 返回 schema 带 `declared_clean` 强制声明（虚假声明按作弊处理），越界声明进最终 findings（severity=high）。
- 禁网（git push/pip/curl）、禁 ssh、禁 docker、禁 git commit/stash、禁改测试文件、禁跑重型测试（判分我方做，agent 期只许 py_compile 级自查）。

### 4.5 已验证证据

- tsc --strict 对着 SKILL.md facade 原文重建的声明全量类型检查：**0 诊断**（/tmp/zc-check.ts 包装函数体口径 + /tmp/zc-facade.d.ts）。
- TASKS 数组与 计划/s1-swev-120.json 程序化比对：**120 项 (instance_id, repo, tier) 完全一致**，60/40/20。
- 判分 RESULT 行解析逻辑与真实烟雾测输出对拍通过。

## 5. 提示模板（全文）

> 风格承 cal2 时代 zcode 线（参考/legacy/cal2/scripts/wf_zcode-m31f-r2.ts）：中文 persona + 编号铁律 + declared_clean 强制声明。persona 全题一致；ask 每题注入自己的路径事实。

### 5.1 system（persona，全题共用）

```
你是一名严谨的工程师，正在参加 SWE-bench 软件修复自动评测（zcode 官方脚手架对照线）。这是你个人独立负责的一道题，其他任何进程不会碰你的题目目录。铁律：
① 只允许在指配给你的题目目录内读写文件（其下 problem.md 是题目原文、meta.json 是元信息、repo/ 是你的工作克隆、model.patch 是你的交付物）；严禁读取、列出或搜索该目录之外的任何路径——特别是 /tmp/swev-s1/（内含测试补丁与判分答案，任何接触即评测作弊）、本评测工作区、其他题目的目录、以及任何判分账本或结果文件；
② 严禁任何网络访问（git push/fetch/pull、pip/curl/wget 一律禁止）；严禁 ssh 到任何机器；严禁运行 docker；
③ 只允许修改 repo/ 里的源码来修复题目问题；严禁改动任何测试文件（tests/ 目录、test_*.py、*_test.*、测试配置与 conftest）；严禁 git commit / git stash——把改动留在工作区，补丁由外部用 git diff 收集；
④ 不要运行重型测试套件、不要安装依赖（判分由外部容器完成）；允许轻量自查（python -m py_compile、通读代码）；
⑤ 题目前提若有缺损（文件缺失、无法复现、定位不到根源），尽力完成能完成的部分，自主决策，不要向用户提问，并把实际情况如实写进最终 summary；
⑥ 如不慎看到了题目说明之外的测试或答案内容，立即停止阅读并在 summary 中如实声明——隐瞒按作弊处理；
⑦ 若判分规则、题目与你的指令矛盾到无法干活，如实声明而不是硬造。收工前逐项核对产物存在后再声明 done。任何查阅测试或答案的作弊行为会使整个对照评测作废。
```

### 5.2 ask（每题注入实例事实）

```
你负责 SWE-bench {tier} 档题目 {instance_id}（仓库 {repo}）。
第一步：完整阅读题目原文 /tmp/zc-ws/{instance_id}/problem.md 与元信息 /tmp/zc-ws/{instance_id}/meta.json。
第二步：你的唯一工作克隆在 /tmp/zc-ws/{instance_id}/repo/（已检出题目基线 commit，工作区干净）。在其中定位问题根源并做最小源码修复；严格遵守系统铁律（只改源码、不碰任何测试文件、不跑重型测试、不联网、不出 /tmp/zc-ws/{instance_id}/）。
第三步：在 /tmp/zc-ws/{instance_id}/repo/ 内把你的完整改动写成补丁文件 /tmp/zc-ws/{instance_id}/model.patch（在 repo/ 内执行：git diff > ../model.patch），并确认该文件已生成且非空。
最后返回 JSON：instance_id 填 "{instance_id}"；tier 填 "{tier}"；patch_written 为布尔值（model.patch 已写出且非空）；summary 用一句话说明修复内容或卡点（越界必声明）；declared_clean 为布尔值——你是否从未读取过 /tmp/zc-ws/{instance_id}/ 之外的任何文件；status 按完成度填 done/partial/stuck。
```

### 5.3 返回 schema（JSDoc 即字段说明，见脚本 SolveOutcome）

instance_id / tier / patch_written / summary / declared_clean / status。

## 6. 启动手册（主代理操作）

### 6.1 一键启动

```
CreateWorkflow(
  path: ".zcode/workflow-drafts/zc-step5-swev.dwf.ts",
  name: "SWE-V S1 120题·zcode官方线（step-5）",
  subagent_model: "new-provider/step-5-preview$high",
)
```

- **勿传 max_concurrency**（运营者指令：默认并发）。
- subagent_model 的 id 本线准备代理的会话无模型目录（ListModels 能力缺口），未能本地核验——**启动若报模型 id 不可解析，先 ListModels 核对 new-provider 下的准确 id 再重提**（改参数不改脚本）。

### 6.2 启动前核对（全部已就绪，此处供复核）

1. `python3 tools/zc-prep-ws.py --status` → all: 120/120 就位；
2. `bash tools/zc-judge-collect.sh --status` → 合计 终态 0/120（干净账本；烟雾测只写了 /tmp/zc-judge-test 测试账本，未碰真实账本）；
3. 120 张 sweb.eval 镜像本机全齐（2026-10-21 核对 missing=0）；
4. 工厂臂并发在跑时判分容器会叠加——本线判分工位 2 是按"工厂本地臂先例上限 3 - 裕量"取的，若工厂仍重载可先收工几条臂再启。

### 6.3 运行中/收尾

- 进度：工作流 progress 看板（求解）+ judged 表（判分）；`bash tools/zc-judge-collect.sh --status` 随时可查账。
- **中途死跑**：patch 在盘上、账本只记终态——直接重跑 `tools/zc-judge-collect.sh --batch all` 补判，或主代理按 §13 用 AmendWorkflow 修脚本续跑（命名子代理可缓存复用）。
- image_missing/judge_error 的 pending 行：镜像/链路修复后 `--batch all` 自动重判。
- 对照分析：resolved 率与 deepseek-cb 69.2%、af-harness fix1 线 44-47% 同口径直比。

## 7. 口径差异与风险（如实登记）

| 项 | 差异/风险 | 处置 |
|---|---|---|
| tokens/turns | zcode 线拿不到子代理平台侧计量，results.jsonl 该三字段恒 null（deepseek-cb 行有值） | 已写进行内 verifier_note 与脚本 notCovered；对照只看 resolved |
| agent_wall_ms | 工作流脚本无时钟（replay 纪律禁 Date.now），恒 null | 同上 |
| 判分容器共厂 | 本机 docker 同时在跑工厂臂判分，判分突发内存/CPU 叠加 | JUDGE_WORKERS=2 护栏；启动前核对工厂负载（§6.2-4） |
| /tmp tmpfs | results.jsonl 与逐题判分日志在 tmpfs（进程重启即失） | 与 deepseek-cb 线同惯例；终局读数出来后主代理择时归档 |
| step-5 行为未知量 | 该档案对本任务集的通过率无先验 | 无预判，数据说话 |
| 模型 id | 本会话无模型目录未能核验 `new-provider/step-5-preview$high` | 启动报错即按 §6.1 核对重提 |

## 8. 交付清单

| 件 | 路径 | 状态 |
|---|---|---|
| 判分收集脚本 | `tools/zc-judge-collect.sh` | ✅ 全链烟雾测过（resolved=true）+ 幂等/失败路径实测 |
| 工作区预置脚本 | `tools/zc-prep-ws.py` | ✅ 120/120 预置完成 |
| 工作流脚本 | `.zcode/workflow-drafts/zc-step5-swev.dwf.ts` | ✅ 120 题嵌入 + tsc --strict 0 诊断 |
| 烟雾测证据 | `/tmp/zc-judge-test/`（隔离账本，未碰真实账本） | ✅ |
| 本文 | `设计/zcode-官方harness对照-设计.md` | ✅ |

## 更新记录

| 日期 | 变化 |
|---|---|
| 2026-10-21 | 准备子代理建本文：判分衔接/预置/工作流脚本/提示模板/启动手册全套备齐，**待主代理启动工作流** |
