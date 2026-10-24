# 调优组（研究组②）· 可续用状态账

> 本文件是**账**，不是报告：每个数字都带出处与 as-of，下一轮直接接着往下写即可。
> 记账人：状态记账员（MiniMax-M3.1-Flash），写作时点 **2026-10-22 03:00 CST**。

## 0. 账本元信息

| 项 | 值 | 出处 |
|---|---|---|
| 工作流 run | `dwfrun-5e3a9b73-f9db-4383-88c6-eee7e8956fdf`（名：研究组②调优组·mcode单点改造） | `~/.zcode/cli/db/db.sqlite` 表 `dwf_run` |
| 流程脚本 | `.zcode/workflow-runs/dwfrun-5e3a9b73-f9db-4383-88c6-eee7e8956fdf.mjs`；方法原文 `.zcode/workflow-drafts/研究组2-调优组.dwf.ts` | 文件本体 |
| 本轮节点账 | `dwf_node` 表 node id 32116–32246（run 内 18 节点，全部 completed；32250=本记账节点） | `sqlite3 db.sqlite` 查询 |
| 方法（运营者钦定） | 每次只采纳一个改进点；题目必须与承诺域匹配；mcode官方 vs mcode改造 **同模型配对**；**≥3pp 才值得考虑**；5题速筛→潜力深测→组合防冲突；工作者 GLM-5.3-Flash / MiniMax，红队审查一律 step-5 | `研究组2-调优组.dwf.ts` 首部注释 |
| 授权来源 | `计划/变更日志.md` 末行（2026-10-22 01:2x 厂长条：fix3 路线终审，启动对齐/调优/可观测/资源管理四组，红队审查一律 step-5） | 文件本体 |
| 官方臂在飞 | 派发器 pid `3711801`（`python3 tools/mcode-dispatch.py run`），heartbeat `2026-10-22 02:59:17` 仍刷新 → **官方臂 results.jsonl 持续追加，任何数字必须带 as-of** | `cat /tmp/mcode-dispatch/heartbeat`、`ps -p 3711801` |
| 官方臂任务池 | `/tmp/swev-s1/` 120 个任务包；`/tmp/mcode-dispatch/state.json` 240 条（120 题 × 2 档案 m31f/m3） | `ls /tmp/swev-s1/*.json \| wc -l` = 120；`python3 -c` 读 state.json |

### 本轮官方臂读数（记账员自测，口径：**last-row + as-of**）

命令：`python3` 解析 `/tmp/bench-official-mcode-{m31f,m3}/results.jsonl`（同一时刻一次性读入，落盘快照另见 §7）

| 臂 | as-of(mtime) | 原始行 | 唯一 task_id | 有重复行任务 | last-row judged | pass | fail | reward=None | status 分布 | 真 reward 翻转任务 | "None+judged" 混合任务 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| m31f | 2026-10-22 02:55:45 | 213 | 120 | 78（最多 3 行） | 111 | 107 | **4** | 9 | completed 111 / judge_error 1 / prepare_failed 8 | **0** | 71 |
| m3 | 2026-10-22 02:58:54 | 216 | 120 | 79 | 110 | 88 | **22** | 10 | completed 110 / judge_error 3 / prepare_failed 7 | **1**（`scikit-learn__scikit-learn-11578` = [False, True]） | 68 |

- m31f 失败集（4，逐题 reward=False）：`django__django-10097`（f2p 431过/7挂）、`django__django-10999`（0/2）、`pytest-dev__pytest-7205`（1/9）、`sphinx-doc__sphinx-10435`（1/0）。
- m3 失败集（22）：`astropy__astropy-13236`、`astropy__astropy-13398`、`django__django-10097`、`django__django-10973`、`django__django-10999`、`django__django-11087`、`django__django-11400`、`django__django-14011`、`django__django-14315`、`django__django-15629`、`psf__requests-2317`、`psf__requests-2931`、`pydata__xarray-2905`、`pylint-dev__pylint-4604`、`pylint-dev__pylint-4661`、`pytest-dev__pytest-10356`、`pytest-dev__pytest-7205`、`sphinx-doc__sphinx-10435`、`sphinx-doc__sphinx-11510`、`sphinx-doc__sphinx-8548`、`sympy__sympy-16597`、`sympy__sympy-17318`。
- **口径要点**：m31f 的 78 个重复行任务里，71 个是"一行 reward=None（prepare_failed/judge_error）+ 一行 judged"，**不是真翻转**；但若取首行或"任一行 None 即算未判"，会把大量已判题误算成未判。m3 有 1 个真翻转 → **必须 last-row**。（终审说"无 reward 翻转"，那是对 m31f 而言；m3 存在 1 例，记账员实测。）

---

## 1. 一屏摘要（下一轮先读这段）

| 环节 | 结论 | 关键数字 | 出处 |
|---|---|---|---|
| 改造面盘点 | **28 个旋钮**，全部"不改安装本体、参数/配置/包装层可改" | 28 条 | node 32117 |
| 改造面红队核验 | **confirmed**（附 8 条引证修正，无虚构、无需改本体、不改判分链） | 8 处引证缺陷 | node 32127 |
| 候选起草 | GLM 3 条 + MiniMax 4 条 → 合并去重 **5 条** | 5 | node 32139/32140/32155 |
| 候选红队逐条审查 | **5 条全部 rejected**（题目-承诺域不匹配＝生死线） | 0 批准 | node 32175/32192/32206/32216/32226 |
| 单点改造与 5 题速筛 | **未开跑**（无批准候选 ⇒ 未进入该 phase） | 0 变体 / 0 速筛 | `ls -d /tmp/mcode-tune-*` → 不存在 |
| 红队终审 | **confirmed**（整轮过程与"0 批准/0 速筛"与独立实测一致，无编造、无越界） | 5 条意见 | node 32246 |
| 20 题深测 / 组合测试 | **未执行**（无速筛通过者；且 m31f 臂域内可配对失败题 ≤1，深测题集当前**造不出来**） | — | 见 §6 |

**本轮的一句话**：改造面是真材（28 旋钮），但**速筛设计对当前数据近乎零功效**——钦定解题模型 m31f 的官方臂 111 道已判题只败 4 道，且 4 道分属 4 个互异域，任何"同承诺域 5 题且官方臂已判"的速筛集都凑不出，**0 批准是数据决定的正确结果**，不是流程偷懒。

---

## 2. 改造面清单（28 旋钮，node 32117；红队 node 32127 confirmed）

红队结论原文要点：**28 个旋钮全部真实存在且可在参数/配置/包装层改造；无虚构、无需改安装本体、不改判分链**；需按 8 条 issues 修正引证（行号/文件/计数/枚举归属），**修正不废旋钮**。

| # | 旋钮 | 怎么改（不改安装本体） | 证据 | 红队修正 |
|---|---|---|---|---|
| 1 | `--prompt-mode tui\|coding\|work`（默认 tui） | 复制 run-one.sh 成 run-one.coding.sh，仅 exec 行加 `--prompt-mode coding` | mcode-dispatch.py exec 行未传 → 默认 tui；anolis `mcode exec --help`；实测 rc=0 | — |
| 2 | `--effort <default\|low\|medium\|high\|xhigh\|max>` | 变体加 `--effort`，**必须与 `--model` 同给** | anolis --help；`wKn=new Set([...])` | 行号：实为 :4874（非清单写的 :4329）。**【第二循环整改④写回·终审 issue 4】`--effort` 在 MiniMax-M3 路由被 CLI 一票拒绝**（原文 `minimax/MiniMax-M3 does not support reasoning effort selection, so --effort high cannot be applied.`，拒绝发生在任何 LLM 调用前、连 llm-call.json 都不生成，证据见 §11.4(1)）→ **m3fail 锚上 effort 类旋钮禁用**（除非路由侧变更）；探针①的 `takes_effect=true` **只在 m31f 路由成立**，不得外推（§7-11、§11.9-12、§11.10-D） |
| 3 | `--max-steps <count>` | 变体加，兼做预算/失控护栏 | --help "maximum assistant steps" | — |
| 4 | `--permission ask\|smart\|full\|off`（官方 full） | 变体改 off/smart（off 会掐断工具调用） | --help；run-exec 第 2 行 `F("--permission",["ask","smart","full","off"])`，默认 smart | 清单把 config 的 `permissionMode` 枚举当 CLI 枚举（双重错误） |
| 5 | `--timeout 25m`（内层）× `SOLVE_TIMEOUT=1800`（外层 OS） | **成对改**，否则外层先杀丢收尾 | 补丁前 mcode-dispatch.py:73/:163 | — |
| 6 | `--mode standard\|lightweight` | 变体加 lightweight 降上下文噪声 | --help | — |
| 7 | `--system-prompt-file <path>` | 整体替换主 Agent 身份提示（**风险最高**） | 处理在 `chunk-G7Q4HUMC.js:23` | 清单称"同列于 run-exec:8"，该文件无此字面量 |
| 8 | `--append-system-prompt-file <path>` | 追加硬约束（最稳的提示注入点） | 同上；探针被候选引用为 TULIP-7781 | 探针工件在工作区与 /tmp 全库 grep **无命中**（见 §3 候选1 issue4） |
| 9 | `--append-system-prompt <text>` | 内联追加，便于逐字节对照 | 同上 | — |
| 10 | `--config <path>` | 复制 `~/.minimax/config.yaml` 成臂级 yaml，exec 加 `--config` | --help "use an explicit Runtime config file"；ENOENT 即拒（先 realpath） | — |
| 11 | config.yaml 可调键白名单 | 配合 `--config` 调键 | `chunk-JIWEZSQY.js:3209` ggr 集 | **15 键，不是清单说的 16 键** |
| 12 | `provider.models.<M>.variants`（none-thinking/thinking） | 臂级 yaml 改 thinking 档 | anolis `~/.minimax/config.yaml:30-39`、`:70-78` | — |
| 13 | `thinking.effortOptions` + `contextWindowOptions`(512000/1000000) | 臂级 yaml 调档位/上下文窗 | config.yaml:86-99 | — |
| 14 | `dataContribution.enabled`（当前 true） | 臂级 yaml 置 false 做去遥测对照 | config.yaml:3-4 | — |
| 15 | 工作区根 `AGENTS.md` | prepare() 写入项目记忆；官方臂不写 | `chunk-2XPMNZVR.js:4902-4904` Tyt/readProjectInstructions | 候选引用的探针 ZEBRAFISH-OK-4242 **无命中** |
| 16 | 工作区根 `CLAUDE.md` | 与 AGENTS.md 二选一（先查 CLAUDE.md，命中即返回） | 同上 | — |
| 17 | 全局 `~/.minimax/AGENTS.md` | 臂级 dataDir 副本家目录落一份 | readGlobalInstructions；`ls ~/.minimax` 确认当前不存在 | — |
| 18 | 工作区根 `.mcp.json` | 挂 MCP 工具 | `chunk-JIWEZSQY.js:3298` | **不在** 2XPMNZVR（机制真、位置错） |
| 19 | `--output-format text\|json\|stream-json` | 改 text→json 填 usage/计费字段 | --help；dispatch 现把 turns/model_calls/tokens 写死 None | — |
| 20 | `-o/--output-last-message <path>` | 归档终稿便于抽检 | --help | — |
| 21 | `--diagnostics-dir <path>` | 每题独立诊断目录（可观测素材） | --help | — |
| 22 | `--file <path>` / `--input -` / `--input-format json` | prompt 走 stdin，issue 原文/失败用例可附 | --help；官方现用 `"$(cat "$PROMPT")"` 塞 argv | — |
| 23 | `--session <id>` / `--continue` | 同 repo 多题挂同 session | --help；`~/.minimax/v2/sessions` | — |
| 24 | `MCODE_LLM_FIRST_EVENT_TIMEOUT_MS` / `MCODE_LLM_STREAM_IDLE_TIMEOUT_MS` | 变体 export 调流容忍度 | `chunk-2XPMNZVR.js:4310`（默认首事件 1200s/流空闲 300s） | — |
| 25 | `MCODE_CONFIG_DIR` / `MINIMAX_DATA_DIR` | 臂级家目录隔离 | `chunk-4Y64C4JT.js:2` + `2XPMNZVR:5268` | 清单把 MCODE_CONFIG_DIR/MCODE_REGION 归错文件 |
| 26 | `MCODE_EXTRA_HEADERS` / `MCODE_PROVIDER_API_KEY` / `MCODE_REGION` | 路由层注入（**密钥只按字段名管道取值，禁明文**） | 4Y64C4JT:2 / 2XPMNZVR:3883 | 清单引的 shared-broker 位置错 |
| 27 | `PROMPT_TMPL`（任务提示模板） | 复制模板只改收尾指令段，题面 `{ps}` 逐字不动 | 补丁前 mcode-dispatch.py:196-204（**现 :246**） | — |
| 28 | Plugin Hooks（PreToolUse/PostToolUse） | 臂级独立 `MINIMAX_PLUGIN_ROOT` 装 hook（**风险最高，排最后**） | `mcode plugin --help`；grep 计数 PostToolUse 32 / PreToolUse 27 | — |

**终审追加意见（node 32246 issue2）**：测绘指令写的是"10-25 条"，实交 28 条，**超上限 3 条**——轻度偏差，会稀释逐条核验强度，登记备复。

---

## 3. 候选红队结论逐条（5 条全部 rejected）

红队 = step-5（`红队·候选审查`），生死线 = **screen_tasks 必须真落在 promised_domain 内**。逐条原始结论在 `dwf_node` 32175/32192/32206/32216/32226；`__host.report` 落表：5 行 status=rejected，official=modified="-"。

### 候选 1「收工对账·验证诚实（--append-system-prompt-file 臂）」【互证 GLM-1 × MiniMax-C2】— **rejected**（node 32175，8 issues）
- **i1 硬性要求不满足**：速筛题 `django__django-10097|m31f` **不在承诺域**，且候选对该题的 motivating 证据与工件相反——候选称"patch.diff 整行删除 userinfo 行"，实盘是上游那一行替换。**记账员复核**：`/tmp/bench-official-mcode-d3-m31f/runs/django__django-10097/patch.diff:9-10` = `- r'(?:\S+(?::\S*)?@)?'` / `+ r'(?:[^\s:@/]+(?::[^\s:@/]*)?@)?'`（上游 cdcf4164be 逐字一致）；红队用官方判分管线复跑得残失败 7 项全是 `auth_tests.test_templates` 的 `TemplateDoesNotExist: registration/password_reset_form.html`（环境性，判分镜像模板缺失）→ 任何"诚实自验"干预都翻不动一个本就上游正确的补丁。
- **i2 连带失实**：域内失败数从"4 败中 3 个"修正为 **2 个**（sphinx-10435 是 P2P 回归型，不在本域）。
- **i3 账本数字漂移**：候选快照（m3 203/98、m31f 201/99）与当时文件（m3 204/99、m31f 203/101）不同——**追加式账本在长**，引用必须带 as-of（记账员 §7 已立此规）。
- **i4 引用材料缺失**：TULIP-7781 / ZEBRAFISH-OK-4242 两个探针工件全库 grep 无命中。
- **i5 策略锚夸大**：S161 的 "+13.8pp 全来自负向约束" 与 `strategies.csv:162`/总表 L74 原文不符（原文是"随机规则与专家精编规则同效 +13.8pp"，另一并列结论才是负向约束）。
- **i6 未复现项**：候选称"64/98 自述环境受限"，红队用关键词代理扫描 104 个 m31f 完成题得 79/104（方向支持，精确值不复现）。
- **i7/i8**：MM-C3 姊妹候选 JSON 不在可达范围；psf-2317 的"已替换"声明属实（m31f 恰 2 条 prepare_failed、无 completed 行）。
- **域内证据成立的部分（记账员复核成立）**：`django-10999|m31f` —— `runs/django__django-10999/mcode.log:27` 自称"`utils_tests.test_dateparse` — 12 tests, OK"，`eval.log:375` 实为 `FAILED (failures=5)`，`judge.json` = `{"resolved": false, "f2p_success": 0, "f2p_failure": 2}`（→ 域内 (a) 类成立、可翻转）。
- 红队收尾："剔除 django-10097 并重筛后本候选**可救**"。

### 候选 2「先测后改·受影响既有用例定向复跑（AGENTS.md 主通道，PROMPT_TMPL 变体作通道对照）」【互证 GLM-2 × MiniMax-C3】— **rejected**（node 32192，8 issues）
- **i1 硬性要求不满足**：`django-django-10097|m31f` 不落在"相邻行为破坏"域；候选定性"纯 P2P 回归型"**错误**——红队复跑得 F2P success=431/failure=7、PASS_TO_PASS success=1427/failure=5（generic_inline_admin 5 条，候选完全未提），逐名核 `/tmp/swev-s1/django__django-10097.json`：那 7 条 `in_f2p=True, in_p2p=False`。
- **i2 筛选题不在发现机制内 + 数字失实**：`pytest-10356|m3` 唯一 f2p 失败是 test_patch 新增的 `test_mark_mro`（模型把 MRO 顺序写反）→ 新测试才暴露，"跑既有测试文件"看不见；候选称"同文件 52 个失败头"实测 anchored `^(FAILED|ERROR)` 仅 13 行、全量出现 23 处。
- **i3 干预盲区**：`pytest-7205|m31f` —— 模型自述本机该文件修复前后均 25 failed（pytest 5.4.1 断言重写器 vs py3.11），判分镜像只挂 9 个 f2p → knob 的"新增失败=未完成"永不触发；"eval 同段 27 个失败头"实测汇总头 11 行。
- **i4 设计缺口**：`django-10973|m3`（f2p 4/1，唯一 FAIL=`test_nopass`）证据较扎实，但模型以"该测试针对旧行为"为由未跑 → 缺"目标测试必须转绿"的硬动作。
- **i5 穷举声明字面失实**："除 2317 外无第二个 f2p 全过+纯 P2P 回归实例"不成立（sphinx-10435|m31f、psf-2931|m3 均符合）；结论方向正确、声明与扫描口径失实。
- **i6 机制新发现（候选未声明）**：prepare() 写的 AGENTS.md 会被 collect() 的 `git add -A && git diff {base}` 扫进 patch.diff（官方 patch.diff 已内含 mcode.log/prompt.txt 为证）→ 改造臂补丁比官方臂多一个 harness 文件，与"只保留修复本身"自相矛盾；走该通道须把注入文件写进 `.git/info/exclude`。
- **i7** ZEBRAFISH-OK-4242 工件不存在；**i8** django-11451 移出属实、django-11400 再分类未核。

### 候选 3「推理档位提升（--effort high 臂）」【GLM-3 独有，无互证】— **rejected**（node 32206，4 issues）
- **i1 硬性要求不满足**：`sympy__sympy-13091` 官方两臂均 resolved=true（m3 1330s f2p 2/0、m31f 1507s f2p 2/0）——它是**通过题**，不属承诺域（深语义推演滑错），却仍在 screen_tasks 里 → 按字面即不匹配。（记账员复核 m31f 侧：`reward=True`，wall 1506886ms；m3 侧 `reward=True`，wall 1329645ms。）
- **i2 弱合域**：`astropy-13398|m3` 未被 motivating 列举、不在候选自己的域枚举里；4 个 f2p 失败同一根因 `TypeError: Coordinate frame ITRS got unexpected keywords: ['location']`（漏做框架属性），并叠加自建 in-place astropy + 数值 harness 自证（候选1 的 (b) 域）。
- **i3 风险备案重大遗漏——内层 25m 才是硬预算**：红队全量扫描 216 个官方 mcode.log，内层超时**恰好 1 例**就是 sympy-13091|m31f（`mcode exec timeout: The run timed out.`、rc=6、wall 1506.9s，靠已落盘改动才判 resolved=true）；而核心合域槽 sympy-16597 已用 1225s、astropy-13398 用 1050s → effort=high 墙钟上涨后会撞内层超时，被记成假阴性。
- **i4 锚点跨模型迁移未证**：S093 数字属实（`strategies.csv:94`，等级A/强度4），但 csv 自述"档位语义由厂商定义、跨模型不可比"、原始证据是 Claude Opus 4.5；`--effort` 对 MiniMax 路由是否生效、方向如何，**本厂无实证** → A/B 前须先做一次档位探针，否则整臂可能是无效对照。

### 候选 4「issue 评论区（hints_text）经 --file 附加给 agent」【MiniMax-C1 独有，无互证】— **rejected**（node 32216，6 issues）
- **i1 硬性要求不满足**：`django-11400` 被列为"规格缺口"实例，但域定义明写缺口"只写在 issue 评论区"；红队读全文：problem_statement 只讲 admin filter ordering 回退，hints_text 全是"是不是回归/发版阻断"口水，**没有任何地方要求 `Field.get_choices` 回退 Meta.ordering**；隐藏期望只在 test_patch → 喂 hints 翻不动。
- **i2 域归属不成立**：`sphinx-8548` —— eval.log:549-600 是模型自己 MRO 文档注释解析选错 namespace 优先级；hints_text 只给方向不给口径。
- **i3 域归属不成立**：`pytest-10356` —— 隐藏期望顺序 `[xfail('c'), xfail('a'), xfail('b')]`（本类优先再按 MRO）只在隐藏测试里，hints_text 无顺序口径。
- **i4 证据缺口**：`sympy-16597` motivating 只有任务名零证据；hints_text 的三个隐藏期望（`oo.is_integer is False` 等，eval.log:417-431）全不在 hints 里，且模型已自证推演过该规则风险 → 弱合域。
- **i5 机制风险未声明**：prepare() 落盘的 hints.txt 在仓库内，会被 `git add -A` 扫进 patch.diff → 改造臂多带一个含 hints 文本的文件（A/B 人工复核 diff 会看到旋钮痕迹）；须写 `.git/info/exclude` 或用仓库外绝对路径。
- **i6 引用工件不存在**：TULIP-7781 / ZEBRAFISH-OK-4242 覆盖声明不成立；候选自承 `--file` 通道未做探针实证（诚实披露，予以确认，但前提陈述失实）。

### 候选 5「工作区根 AGENTS.md 装"补丁最小化"负向约束」【MiniMax-C4 独有，无互证；与候选2 同通道不同内容】— **rejected**（node 32226，5 issues）
- **i1 控制槽判定失实会污染 A/B**：`pylint-4661` 被指定为"判分镜像缺 appdirs…不可救、只作不退化对照"，但 **m31f 官方臂同题 resolved=true（f2p 1/0）**，赢法恰恰是往 setup.cfg 的 install_requires 加 `appdirs>=1.4.0`（`/tmp/bench-official-mcode-d2-m31f/runs/pylint-dev__pylint-4661/patch.diff`；其 eval.log:404-421 显示 pip install -e . 联网装上 appdirs-1.4.4）。而本候选 AGENTS.md 第③条"不要修改 pytest/setup/tox 配置"恰好禁掉这一动作 → 一旦 A/B 跑 m31f 锚点，本旋钮会**制造一个假回归信号**。（记账员复核：m31f `reward=True`、wall 227120ms；m3 `reward=False`、wall 206814ms。）
- **i2 自污 outcome measure 未声明**：AGENTS.md 会进 patch.diff，而本候选的 outcome measure 正是"补丁卫生" → 每条补丁多带一个 AGENTS.md，卫生统计必须先剔除它。
- **i3 引用工件不存在**：ZEBRAFISH-OK-4242 grep 无命中；通道机制本身已独立证实可用（`chunk-2XPMNZVR.js` Tyt 先 CLAUDE.md 后 AGENTS.md、readProjectInstructions 注入、32KB 预算硬截断）。
- **i4 普查数字无法复现**：候选称 195 份 patch.diff、55/99 个任务含 changelog/CHANGES/docs/releases/配置类文件、CHANGES 22 次；红队实跑 6 个批次全部 patch.diff 得 **219 份 / 111 个唯一任务、39 个任务命中该类文件、CHANGES 25 次**（仅 docs/releases/3.0.txt=6 次与候选一致）→ 方向性结论（约三分之一补丁带非源码文件）成立，精确形式不复现（账本在长）。
- **i5 散文与清单不一致**：正文把 sphinx-10435 与 pylint-4661 并列为"不退化对照"，但 screen_tasks 五项里没有 sphinx-10435 → 对照组设计与筛选题清单脱节，计分规则须先统一。

**合并后的候选排序（node 32155 `ranked`）**：①收工对账(--append-system-prompt-file) ②先测后改(AGENTS.md 主通道) ③--effort high ④--file hints_text ⑤AGENTS.md 补丁最小化。

---

## 4. 速筛两侧数字与出处

### 4.1 本轮速筛实况：**0 个速筛，0 条速筛结论**

- 流程上：`approved=[]`（5 条候选全被否）⇒ 脚本的"单点改造与 5 题配对速筛"phase **没有产生任何变体、冒烟或配对跑**。`__host.report` 五行 `official="-"`、`modified="-"`。
- 产物级证据（记账员本轮实查）：
  - `ls -d /tmp/mcode-tune-*` → **不存在**（无变体目录、无变体脚本、无改造臂 results.jsonl）。
  - 派发器 `tools/mcode-dispatch.py` 中无臂选择分支被改（`:547` 仍写死 `run-one.sh`）。
  - 因此**改造侧数字 = 无（未跑）**，不存在"0/5"这种可被误读为"跑过且全败"的数字。
- 结论：本轮**没有任何速筛数字**可记；下一轮若有，第一件事是补这张两侧表。

### 4.2 备用账：五个候选的速筛题在官方臂的**官方侧**数字（记账员自测，as-of 见 §0）

> 出处：`/tmp/bench-official-mcode-m31f/results.jsonl` 与 `.../m3/results.jsonl`（last-row 口径）；逐题轨迹在 `/tmp/bench-official-mcode-d{1,2,3}-{m31f,m3}/runs/<task>/{mcode.log,patch.diff,eval.log,judge.json}`。
> **配对警告**：方法钦定"同模型配对"，m31f 才是钦定解题模型；下表并列两臂只为暴露"候选实际是从 m3 失败集挖的"这一事实。

| 候选 | 速筛题（5） | m31f 侧（钦定锚点） | m3 侧 | m31f 侧失败题数 / 域内可配对失败题数 |
|---|---|---|---|---|
| C1 收工对账 | django-10999 / django-10097 / pytest-7205 / pylint-4604 / django-14011 | 败/败/败/**过**/**过** = 2 过 3 败 | 全败（5/5） | 3 个失败，分属 3 个互异域 |
| C2 先测后改 | pytest-7205 / django-10097 / pytest-10356 / django-11087 / django-10973 | 败/败/**过**/**过**/**过** = 3 过 2 败 | 全败（5/5） | 2 个失败（都是环境性，见红队 i1/i3） |
| C3 --effort high | django-10999 / sympy-16597 / sympy-13091 / astropy-13398 / sphinx-11510 | 败/过/过/过/过 = 4 过 1 败 | 败/败/过/败/败 = 1 过 4 败 | 1 个失败（1 题） |
| C4 --file hints | django-10999 / sympy-16597 / sphinx-8548 / django-11400 / pytest-10356 | 败/过/过/过/过 = 4 过 1 败 | 全败（5/5） | 1 个失败（1 题） |
| C5 补丁最小化 | astropy-13236 / pylint-4661 / pytest-10356 / sphinx-11510 / astropy-13398 | 全过 = 5 过 0 败 | 全败（5/5） | **0 个失败（0 题）** |

**这张表就是本轮 0 批准的量化根因**：在钦定锚点 m31f 上，五组速筛题的官方失败数分别是 3 / 2 / 1 / 1 / **0**，且那 4 个失败分属 4 个互异域（自验失真 / 环境性模板缺失 / 断言重写器不兼容 / 无网 LaTeX 资源）——**同域凑 5 题在 m31f 上不可能**；而把"官方已过"的题塞进速筛题集以凑数，又正好撞红队的生死线（域外即否）。

---

## 5. 终审意见（node 32246，红队·终审 step-5，全程未参与其它环节）

**verdict = confirmed**。终审结论原文要点：整轮过程、门闸与"0 批准 / 0 速筛"结果**与独立实测数据一致，无编造、无越界**；所列问题为**记录缺口与下一循环设计风险，不构成否决**。

| # | 意见 | 记账员补注（as-of 已更新） |
|---|---|---|
| 1 | **记录缺口·旋钮清单未落盘**：`/tmp/mcode-tune-*` 不存在、`计划/研究组/` 不存在（记账员在终审之后才落账）→ 旋钮真实性无法从工件验证，只能依赖流程内 step-5 闸。终审独立验证量级：`mcode exec --help` 暴露 22 个包装层可达选项 + config.yaml 键面 + PROMPT_TMPL/OS 超时 → 真实旋钮面 ≥28，计数无虚胖。**要求：状态账必须落盘完整清单+证据指针** | 本文件 §2 即为该要求的兑现（28 条全量带证据与红队修正） |
| 2 | **指令偏差**：测绘指令"10-25 条"（draft:76），实交 28 条，超上限 3 条 | 登记备复，下轮把上限改回 25 并优先保 §2 表中的 1/2/3/4/8/10/19/27 |
| 3 | **结构性·速筛对当前数据近乎零功效（最重要）**：m31f 官方臂 judged 110 题仅 4 败（106 过=96.4%），四败分属四个互异域、每域仅 1 例 → 任何候选都凑不出"同承诺域 5 题且官方臂有配对判分"的速筛集（pad 已过题=域不匹配生死线；借 m3 臂 22 失败=模型不配对；或编造）。"这完全解释 approved_count=0 是数据决定的正确结果"，并预示"不升级任务池或改换目标档案，后续每循环仍将 0 批准"。**建议向厂长上报：要么换更难任务池/换目标档案，要么把 motivating 证据改到轨迹级（轮次/空转/越权），并优先测 --effort/--prompt-mode/--max-steps 等高价值真旋钮（须先解决速筛功效问题）** | 记账员实测 as-of 02:55/02:58：m31f judged 111 / pass 107 / fail 4（96.4% 过率，数字随臂在飞微增，4 败集合不变）；§4.2 表把"域内可配对失败题数"逐候选量化 |
| 4 | **下一循环必须·配对基线钉定**：官方线仍在飞（pid 3711801 存活），results.jsonl 中 78+ 任务有重复行（最多 3 行），collect() 按固定路径 `runs/<tid>` 覆写轨迹（mcode-dispatch.py:628）。取官方侧数字必须：**last-row 口径 + as-of 时间戳 + 筛前快照拷贝 results.jsonl 与 runs/**；**不得把 101 行 prepare_failed（基建流失、reward=None、无轨迹）当失败 mining** | 记账员实测：m31f 78 个重复行任务中 71 个是"None+judged"混合，m3 有 1 个真翻转（scikit-learn-11578）；`runs/<tid>` 覆写风险 → 快照必须整目录 copy（`cp -a`） |
| 5 | **速筛越界检查**：screens=[]/survivors=[] → 本轮零速筛结论，无越界可言；唯一结论是过程性陈述；notCovered 亦正确声明 n=5 仅 20pp/题分辨率只能定向。**≥3pp→n=20 净题数换算属下一循环设计项，未执行、如实列为未覆盖** | 换算方案见 §6.3（本轮由记账员给出设计，**未执行任何深测**） |

---

## 6. 下一循环动作

### 6.0 阻塞项（必须先由厂长/运营者裁决，否则下一循环仍将是 0 批准）

| 选项 | 做法 | 好处 | 代价/风险 | 本账的证据 |
|---|---|---|---|---|
| **A. 换目标档案** | 把"解题模型"从 m31f 改钉到 m3 | m3 臂有 22 个失败、可按域聚类凑 5 题速筛、20 题深测 | 偏离 draft 的"解题一律 m3.1f"；m3 臂更慢更贵（sympy-16597 已 1225s、m31f sympy-13091 已 1506.9s 撞内层 25m） | §0 m3 fail=22；§3 候选3 i3 |
| **B. 扩任务池** | 引入更难任务，使 m31f 臂的失败数 ≥20 | 保持 m31f 锚点与免费额度 | 需新任务包（当前 `/tmp/swev-s1` 仅 120 题） | §0 任务池 120 |
| **C. 改 outcome measure**（终审建议） | 承诺域从"失败类别"改为**轨迹级行为特征**（自证失真/空转轮次/越权改测试/重复读同一文件），题不必全是官方失败题，考察"改造臂是否减少该行为" | 可从 111 个已完成题里凑 20 题同域 | outcome 不再是通过率，判分口径需另定（建议：行为特征计数 + 通过率双报，不互相替代） | 终审 issue3 |
| **D. 只做旋钮探针**（并行可做） | 在速筛功效修复前，先把 --effort / --prompt-mode / --max-steps 三旋钮做成"探针级"实证（档位是否真改变 MiniMax 行为、coding 模式差异、步数上限截断效应） | 产出"旋钮真实有效"的新证据，为下一轮候选提供骨架 | 只证明旋钮有效，不产生分数结论 | §3 候选3 i4 |

**记账员建议**：A 与 C 并行上报，D 立即开工（不依赖裁决），B 由运营者定（工程量最大）。

### 6.1 机制准备（可立即做，解除下一轮的两个机制坑）

1. **臂选择能力**：当前派发器写死 `run-one.sh`（`tools/mcode-dispatch.py:547` 写死，exec 行 `:213`）。改造臂需要"复制 run-one.sh 成变体 + 派发器按臂选脚本"的**参数层**能力（官方臂逐字不动，纪律①允许）。建议在派发器加 `--run-one <path>` 形参，默认仍是 `run-one.sh`。
2. **注入文件排除**（红队候选2 i6 / 候选4 i5 / 候选5 i2 一致指出）：改造臂写入工作区的 `AGENTS.md` / `hints.txt` 会被 `git add -A && git diff {base}`（当前 `:619`，补丁前 `:359`）扫进 patch.diff → ① 改造臂补丁比官方臂多一个 harness 文件；② 以"补丁卫生"为 outcome 的候选**自污**；③ 人工复核 diff 会看到旋钮痕迹。**做法**：prepare() 写注入文件后立刻写 `.git/info/exclude`（或写到仓库外绝对路径 + `--file` 绝对路径），并把"patch.diff 内不含注入文件"列为变体冒烟的必检项。
3. **官方侧快照器**：速筛/深测开跑前，先 `cp -a` 官方臂 `results.jsonl` 与 `runs/` 到 `/tmp/mcode-tune-<候选>/official-snapshot-<as-of>/`，并在快照目录写 `as-of.txt`（时间戳 + 文件 sha256）。**理由**：官方臂在飞、重复行多、`runs/<tid>` 覆写（终审 issue4）。
4. **行号漂移登记**：本轮引用的 dispatch 行号是补丁前口径（649 行版本，备份 `工具状态备份/mcode-dispatch.py.pre-patch1-R2`）；当前工作区版本 949 行（02:37 被 补丁1-R2 资源闸 改写，存档 `补丁/补丁1-mcode-dispatch-资源闸-R2.patch`）。**下轮引用前必须确认版本**，当前行号对照：SOLVE_TIMEOUT `:110`（前 `:73`）、exec 行 `:213`（前 `:163`）、PROMPT_TMPL `:246`（前 `:196`）、git add -A `:619`（前 `:359`）、`turns/model_calls/tokens=None` `:682`/`:719`（前 `:422`/`:459`）、`runs/<tid>` `:628`（终审引用的仍是补丁前口径）。

### 6.2 5 题速筛（下一循环，条件触发）

- **触发**：某候选经红队 **confirmed**（题目-承诺域逐条落域、配对同参同判分、无更简单解释）→ 进速筛。
- **配对规则**：改造臂与官方臂 **同模型**（钦定 m31f）、同判分链（`tools/cb-judge.sh` → `tools/swev-judge.py`，口径 resolved = F2P+P2P 全过，`tools/swev-judge.py:94-96`）、除唯一旋钮外参数全同；官方臂数字取自 as-of 快照并逐题标注出处路径。
- **题集硬规则**：①每题必须落在 promised_domain 内（域判据须写成可核的判据，不接受散文）；②官方臂同题有判分结果；③同模型；④**禁用** prepare_failed / judge_error 题（无判分无轨迹）；⑤官方臂已过的题只能作"不退化对照槽"，**单列且不计净分**（防"题目本来就会过"）。
- **判读**：net = 改造过数 − 官方过数；net ≥ 1 → 进深测；n=5 的分辨率是 **20pp/题**，结论只能写"信号方向"，不得写"提升 X pp"。

### 6.3 速筛通过者的 20 题深测设计（**本轮未执行**，此处只出设计）

**(a) 触发与题集构成**：速筛 net ≥ 1 且红队复核 confirmed 的候选 → 深测集 = 速筛 5 题（同域）+ 同域扩展 15 题 = 20 题。**20 题必须全部落在该候选的 promised_domain 内**（逐题写明"为什么这题属于该域"的判据 + 证据行号，red-team 逐条核；域外题一律剔除，宁可缩到 12 题也不 padding）。

**(b) 题集从哪来（当前可行性核对）**：
- m31f 臂 120 题里 judged 111、**fail 仅 4**（4 个互异域）⇒ **在 m31f 锚点上，任何单一失败类承诺域内的官方失败题 ≤ 1**，凑不出 5 题速筛，更凑不出 20 题同域深测。**这正是本轮 0 批准的根因，深测同样会被同一根因卡死。**
- 因此 20 题题集只有三条合法来路（对应 §6.0 的 A/B/C）：A 换锚点到 m3（22 败可聚类）；B 扩池使 m31f 失败数足够；C 改 outcome 为轨迹级行为域（题从 111 个已完成题里按行为特征聚类取，判分口径改为行为计数 + 通过率双报）。
- **本轮不给具体 20 题名单**——因为按当前数据，名单只能是"凑数"（域外/已过题），那会重复本轮被否的同一错误。

**(c) ≥3pp 门槛 → 净题数换算**（记账员算，供下轮直接用）：
- 全池口径：官方 m31f 臂任务池 **120 题**（judged 111）→ 3pp × 120 = 3.6 → **采纳门槛 = 净 ≥ 4 题**；若按 240 条 state 条目（120 题 × 2 档案）口径 = 7.2 → **净 ≥ 8 题**。两种口径都要在结论里写明用哪个。
- 20 题深测子集上的**局部**门槛：3pp × 20 = 0.6 → 门槛 = **净 ≥ 1 题**（局部 5pp）。**但 1 题在 n=20 上不具统计意义**，只能作"是否值得继续"的方向性门槛。
- 统计显著性（McNemar 精确检验，discordant 全部同向时）：净 1 → p=1.0；2 → 0.5；3 → 0.25；4 → 0.125；5 → 0.0625；**6 → 0.031（p<0.05 最小值）**；7 → 0.0156；8 → 0.0078。
  - **深测通过线（建议）**：方向性线 = 净 ≥ 1（且 discordant 反向 ≤ 1）；**统计线** = 净 ≥ 6 且 discordant 总数 = 6（即 6 题由错变对、0 题反向）；discordant 更多时净数须更高（如 discordant=10 需净 ≥ 8 才 p<0.05）。
- **结论口径**：20 题深测**不能直接兑现 3pp**（20 题是 120 题池的子集，1 净题 ≈ 全池 0.83pp）。深测通过只意味着"值得在全池上验证"；正式采纳须在全池（120 题 m31f 臂）复跑该旋钮并达到净 ≥ 4 题（3pp）。

**(d) 执行纪律**：改造臂与官方臂同参同判分；改造臂产物落 `/tmp/mcode-tune-<候选>/`（含 mcode.log、patch.diff、eval.log、judge.json、results.jsonl、official-snapshot 引用）；judge 容器前查 `ssh anolis 'docker ps -q | wc -l'`，本工作流同时 ≤2；长跑 nohup + 轮询；所有结论带命令/路径证据；**改造臂与官方臂的官方侧数字必须取自同一 as-of 快照**。

**(e) 深测必查的三个陷阱**：①内层 25m 超时（红队已实测 sympy-13091|m31f 为唯一内层超时例，rc=6、wall 1506.9s）→ **先排超时再谈分数**；②`git add -A` 把 harness 注入文件带进 patch（须 exclude）；③判分链与判分超参（对照 `设计/最终真相-红队挑战-裁决.md` R11a）不得在两臂间漂移。

### 6.4 两候选都过时（都过筛/都过深测）时的组合测试与轨迹冲突观察方案

> 口径说明：本节把 ask 中的"两候选都过时"按上下文读作"**两个候选都过了速筛/深测**"（可进入组合），非"候选已过时"。若运营者本意是"候选已过时（应淘汰）"，则本节应改为淘汰清单模板——请在下轮开工时向运营者确认一次。

**(a) 组合测试（4 臂设计）**
- 臂：官方 O / 单点 A / 单点 B / 组合 AB。四臂同题集（20 题）、同模型、同判分链、其余参数全同；AB 臂 = A、B 两个旋钮同时开（**必须是两个旋钮各自独立生效的组合**，如 A=--append-system-prompt-file、B=AGENTS.md；AB 时注入文件仍须 exclude 规则一致）。
- 判定规则：
  - 组合净 ≥ max(单点净) 且组合 − 次优单点 的 discordant 反向 ≤ 1 → **采纳组合**（两旋钮不冲突）。
  - 组合净 < 任一单点净（且差 ≥ 2 净题）→ **判冲突，禁止组合**；此时以"更强单点 + 把弱旋钮降级为提示层"（换通道不叠加）收场。
  - 组合 ≈ 单点（差 ≤ 1 净题）→ **不叠加收益**，按"取更简单者"（单点）收场，避免两条提示互相稀释。
- 统计：同样报 McNemar 精确 p 与 discordant 明细；n=20 只出方向性结论。
- 冲突判定必须**先排干扰项**：内层超时、判分污染、注入文件进 diff、官方臂数字漂移（as-of 不一致）——**任一存在则该臂结果作废重跑**，不得直接判"冲突"。

**(b) 轨迹冲突观察方案（逐题四臂对照）**
- 采集：每题四臂各留 `mcode.log`（原始轨迹）、`patch.diff`、`eval.log`、`judge.json`；统一落 `/tmp/mcode-tune-<组合名>/combo-<task>/<臂>/`。
- 观察特征（从轨迹与补丁各抽，可脚本化）：
  1. 步数/工具调用序列长度、是否有空转轮次（连续重复读同一文件、无编辑的轮次占比）；
  2. 是否触碰测试文件（`tests/`、`test_*.py`、`conftest.py`）——两臂触及面差异；
  3. 自证行为：是否执行了仓库原生测试入口、是否用 PYTHONPATH/换解释器/自制夹具/`setup.py build_ext` 自证（自证失真域的可观测锚点）；
  4. 最终消息自述 vs `git diff` 的一致性（声称改了什么 vs 实际 diff 的文件/行差异条数）——候选1 的域内铁证正是这一条（django-10999|m31f：自述 "12 tests, OK" vs eval.log `FAILED (failures=5)`）；
  5. 收敛时间与内层超时余量（`agent_wall_ms` vs 25m 内层上限；官方已有 1506.9s 的超时先例）。
- 冲突清单（每条必须带：题号、臂对、轨迹行号/补丁行、观测量、判定）：
  - C1 **补丁语义冲突**：两臂改同一文件但结论不同（交集文件 × 补丁行差异）；
  - C2 **提示张力冲突**：A 的追加约束与官方 PROMPT_TMPL 第 3 条"不要在自验上耗尽时间"直接对撞（候选1 已被红队确认张力真实存在，候选用时间盒化解 → 组合时须复查是否被 B 稀释）；
  - C3 **注入文件互斥**：A 的追加文本与 B 的 AGENTS.md 内容在同题给出**互相矛盾的动作指令**（如"只跑目标测试" vs "不要改 setup/tox 配置" vs "跑完既有测试再收工"）→ 观察模型是否选择其一、是否出现折中行为（跑了测试但改测试、既不跑也不说未验证）；
  - C4 **资源/截断冲突**：AB 臂步数与墙钟同时抬升 → 触发 `--max-steps` 截断或内层 25m 超时的题数（与单点臂对照，判"冲突"还是"预算问题"）；
  - C5 **假冲突排查**：A/B 两臂在同题上"一个过一个不过"但证据显示是**判分链/环境性**（如 django-10097 的模板缺失、sphinx-10435 的无网 LaTeX）→ 此类不计冲突，改列"环境性失败"，需从冲突计数中剔除。
- 输出：一张 20 题 × 4 臂的行为特征对照表 + 冲突清单（含 C1–C5 分类计数）+ 明确"可组合 / 不可组合 / 需改通道"的裁决行。

### 6.5 下一循环动作清单（可直接派工）

| # | 动作 | 角色/模型 | 前置 | 产出落点 |
|---|---|---|---|---|
| 1 | 裁决 §6.0 的 A/B/C（目标档案 / 任务池 / outcome measure） | 厂长·运营者 | — | 决定后写回本文件 §6.0 |
| 2 | 派发器加臂选择参数 + 注入文件 exclude + 官方侧快照器 | 改造实施员 GLM-5.3-Flash | 1 | `tools/mcode-dispatch.py`（官方臂默认行为不变） |
| 3 | 旋钮探针：--effort（MiniMax 侧是否真生效/方向）、--prompt-mode coding、--max-steps | 改造实施员 + 速筛执行员 | 2 | `/tmp/mcode-tune-probe-*/` |
| 4 | 按裁决结果重起草候选（域判据写成可核条目 + 官方臂配对基线 + as-of） | 候选起草 GLM / MiniMax（双模型互证） | 1,2 | 送红队 |
| 5 | 红队逐条审候选（域匹配生死线 + 引证复核 + 探针工件必须真存在） | 红队 step-5 | 4 | 批准列表 |
| 6 | 5 题配对速筛（一次一个变体） | 改造实施员 + 速筛执行员 GLM | 5 | 变体目录 + 两侧数字表（写回 §4） |
| 7 | 20 题深测（触发后） | 同上 | 6 且 net ≥ 1 | 深测读数（写回 §4） |
| 8 | 组合测试 + 轨迹冲突观察（两候选都过筛后） | 同上 + 红队 | 7 且 ≥2 个深测通过 | 组合表 + 冲突清单 |
| 9 | 更新本状态账（沿用本文件结构，追加 as-of 与新行号） | 状态记账员 MiniMax | 每轮末 | 本文件 |

---

## 7. 口径与防错清单（下一轮直接照抄）

1. **官方侧数字**：last-row + as-of + 筛前快照（results.jsonl 与 runs/ 一起 `cp -a`）。理由：m31f 78 个任务多行（71 个是"None+judged"混合），m3 有 1 个真翻转（scikit-learn-11578 [False, True]）。
2. **不把 prepare_failed / judge_error 当失败样本**（reward=None、无轨迹）：results.jsonl 口径 m31f 8 个 prepare_failed + 1 个 judge_error、m3 7 + 3；派发器 state.json 口径（240 条，as-of 2026-10-22 03:0x）= phase: judged 227 / solving 2 / prepare_failed 10 / error 1，reward: True 197 / False 26 / None 17。**终审所写"101 行 prepare_failed"在上述任一口径下均未复现**（疑为另一快照/另一文件的计数），引用时勿直接沿用。
3. **官方臂在飞**：pid 3711801，heartbeat 每分钟刷新；引用任何数字须写 as-of + 文件路径 + 行/任务定位。
4. **行号漂移**：本轮候选/红队引用的 dispatch 行号是**补丁前**口径（649 行，备份 `工具状态备份/mcode-dispatch.py.pre-patch1-R2`）；当前 949 行版本对应：SOLVE_TIMEOUT `:110`、exec `:213`、PROMPT_TMPL `:246`、git add -A `:619`、`runs/<tid>` `:628`、tokens 三件 `:682`/`:719`。
5. **判分口径**：resolved = F2P+P2P 全过（`tools/swev-judge.py:94-96` → swebench `get_eval_report`）；超参见 `设计/最终真相-红队挑战-裁决.md` R11a。
6. **补丁自污**：`collect()` 的 `git add -A` 会把 mcode.log、prompt.txt（已实测在 django-10999、django-10097 的 patch.diff 里）与改造臂注入文件一起收进 patch.diff → 卫生类指标须剔除 harness 文件。
7. **探针工件必须真存在**：本轮 5 个候选里有 3 个引用了全库 grep 无命中的探针（TULIP-7781、ZEBRAFISH-OK-4242、AGENTS.md 复述标记），被红队逐条点名为"引用材料缺失"；**引用前先 grep 一次**。
8. **策略锚引用不得夸大**：strategies.csv:94（S093）、:162（S161）原文与总表 L74/L12 的措辞要逐条对齐（S161 的 +13.8pp 来自"随机规则 vs 专家精编规则同效"，不是"负向约束专属"）。
9. **域外即否**：速筛题凑数（用官方已过题 padding）是本轮 5 条候选全被否的共同根因之一，不得重犯。
10. **样本量诚实性**：n=5 → 20pp/题；n=20 → 5pp/题且需净 ≥ 6（discordant 全同向）才 p<0.05；3pp 是**全池**门槛（120 题池 = 净 ≥ 4 题），子集结果不得冒充全池结论。
11. **【第二循环整改④写回·终审 issue 4】effort 类旋钮 × m3fail 锚 = 硬禁止**：`--effort` 在 MiniMax-M3 路由被 CLI 一票拒绝（`minimax/MiniMax-M3 does not support reasoning effort selection`，发生在任何 LLM 调用前，M1 冒烟硬失败实证 §11.4(1)）；探针①的 `thinkingLevel=high` / `takes_effect=true` 判定**只在 m31f 路由成立**，不得外推到 m3 锚。M1 谱系在 m3 锚上重开须先换通道（config 级 thinking 档位另立候选）或换锚回 m31f（§11.7 动作 6）。（与 §11.9 条 12 同源；§11.9 批量并入本清单时该条并入此处，勿重复编号。）

---

## 8. 本轮未覆盖 / 未跑（据实登记）

- **未跑**：20 题深测（≥3pp 门槛换算只出设计、未执行）；组合测试与轨迹冲突观察（无深测通过者，按流程"待 ≥2 个深测通过者后进行"）；任何改造臂实跑（0 变体、0 冒烟、0 配对速筛）；旋钮探针（--effort 在 MiniMax 侧是否真生效未验）。
- **能力缺口**：本轮中间产物（knobCheck 逐条结论、候选审查逐条结论、终审意见）**不在工作区文件系统**，记账员是从 `~/.zcode/cli/db/db.sqlite` 的 `dwf_node` 表（run `dwfrun-5e3a9b73…`，node 32116–32246）读出并落盘到本文件的；该读取方式对本轮可行，但**下一轮若 run 记录不可读，账就断了** → 建议每轮要求关键结论同时落工作区文件。
- **不可达/未复核项**：MM-C3 姊妹候选 JSON（红队声明不在可达范围）、"64/98 自述环境受限"精确值（红队复现为 79/104）、TULIP-7781 / ZEBRAFISH-OK-4242 探针工件（全库无命中）、候选4/5 所引 patch.diff 全量普查的精确形式（红队复现为 219 份/111 唯一任务/39 命中/CHANGES 25 次）。
- **错配登记**：候选3 的 sympy-13091 与候选4/5 的若干题在 m31f 锚点上官方是**通过题**（见 §4.2），把它们当失败题填入速筛题集是本轮被否的直接原因之一。

---

## 9. 证据索引（复现命令）

```bash
# 本轮工作流记录（改造面/候选/红队/终审 逐条）
sqlite3 ~/.zcode/cli/db/db.sqlite \
 "select id,kind,status,time_created from dwf_node where run_id='dwfrun-5e3a9b73-f9db-4383-88c6-eee7e8956fdf' order by id;"
# node 32117=改造面28旋钮 32127=旋钮红队 32139/32140=双模型候选 32155=合并 32175/32192/32206/32216/32226=候选红队 32246=终审

# 官方臂两侧数字（last-row）
python3 - <<'PY'
import json,collections
for a,p in [('m31f','/tmp/bench-official-mcode-m31f/results.jsonl'),('m3','/tmp/bench-official-mcode-m3/results.jsonl')]:
    rows=[json.loads(l) for l in open(p) if l.strip()]
    by=collections.defaultdict(list)
    for x in rows: by[x['task_id']].append(x)
    last={k:v[-1] for k,v in by.items()}
    j=[x for x in last.values() if x.get('reward') is not None]
    print(a,'rows',len(rows),'judged',len(j),'pass',sum(1 for x in j if x['reward'] is True),
          'fail',sum(1 for x in j if x['reward'] is False),
          sorted(x['task_id'] for x in j if x['reward'] is False))
PY

# 派发器状态（phase/reward 分布，防把基建流失当失败）
python3 -c "
import json,collections
d=json.load(open('/tmp/mcode-dispatch/state.json'))
print('entries',len(d))
print('phase',dict(collections.Counter(v.get('phase') for v in d.values())))
print('reward',dict(collections.Counter(str(v.get('reward')) for v in d.values())))"

# 逐题工件（轨迹/补丁/判分）
ls /tmp/bench-official-mcode-d{1,2,3}-{m31f,m3}/runs/<task>/{mcode.log,patch.diff,eval.log,judge.json}

# 关键铁证
grep -n "12 tests, OK" /tmp/bench-official-mcode-d1-m31f/runs/django__django-10999/mcode.log
grep -n "FAILED (failures=5)" /tmp/bench-official-mcode-d1-m31f/runs/django__django-10999/eval.log
sed -n '9,10p' /tmp/bench-official-mcode-d3-m31f/runs/django__django-10097/patch.diff
grep -n "27 passed" /tmp/bench-official-mcode-d3-m3/runs/pylint-dev__pylint-4604/mcode.log
grep -n "collected 0 items / 1 error" /tmp/bench-official-mcode-d3-m3/runs/pylint-dev__pylint-4604/eval.log

# 本轮无改造臂产物（0 速筛的产物级证据）
ls -d /tmp/mcode-tune-*            # → 不存在
ls 计划/研究组/                    # → 本文件所在目录（记账前不存在）
```

---

## 10. 第二循环·候选起草（候选起草·GLM，写作时点 2026-10-22 05:50 CST）

> 在 §0–§9 之上接着写。取数全部来自筛前快照 `/tmp/mcode-tune-draft-glm/official-snapshot-20261021T214505Z/`（含 m31f/m3 results.jsonl + d{1,2,3} 双臂 runs/ 全量 cp -a，`sha256.txt` + `as-of.txt` 在内；源 mtime：m31f 04:25:39、m3 04:17:49 +0800；heartbeat 04:25:39 官方臂仍在飞）。本节所有"官方臂数字"= 该快照 last-row。

### 10.1 m3 失败集更新：22 → 24（重试波新增已判行）

快照口径 m3 臂：rows 226 / unique 120 / last-row judged 119 / pass 95 / **fail 24** / status completed 119 + judge_error 1。相对 §0（02:58 口径 22 败）新增：`pydata__xarray-3993`（f2p 0/2, p2p 2398/0, wall 51s）、`pydata__xarray-4687`（**judge.json 为 0 字节但 results.jsonl last-row reward=False**——判分管线工件疑在重试中被覆写/未落全，引用该题判分细节前必须重取；wall 205s）。m31f 臂同快照：judged 119 / pass 114 / fail 5（新增 `psf__requests-2317`）。**24 败名单**：astropy 13236/13398，django 10097/10973/10999/11087/11400/14011/14315/15629，requests 2317/2931，xarray 2905/3993/4687，pylint 4604/4661，pytest 10356/7205，sphinx 10435/11510/8548，sympy 16597/17318。

### 10.2 24 败逐题 mcode.log 归因（本循环逐题读完终稿+judge.json+eval.log）

| 题 (d=批次) | judge f2p | wall | 归因（一句话，出处=快照 runs-dN-m3/<t>/） |
|---|---|---|---|
| astropy-13236 (d1) | 0/2 | 281s | 警告措辞无网上游不可对拍+setup.cfg 放行；自述"83 项两边一致"把 f2p 失败归为 numpy 环境漂移 |
| astropy-13398 (d3) | 0/4 | 862s | 明示 by design 留 5 参失败（上游会改该测试）+IERS 失效环境；口径冲突 |
| django-10097 (d3) | 431/7 | 126s | 红队已证：补丁上游正确，7 f2p=判分镜像模板缺失（环境性，不可翻） |
| django-10973 (d2) | 4/1 | 76s | 自选 PGPASSWORD 契约，明知旧 test_nopass 口径会挂（"needs the accompanying test update"） |
| django-10999 (d1) | 0/2 | 361s | **自证失真铁证**：终稿"18 tests, OK"+"287 tests, OK" vs eval `FAILED (failures=5)` |
| django-11087 (d1) | 0/1 | 103s | 零自验静态推理收工（终稿自述"No environment installation performed"），.only() 引入 DeletionTests 全 ERROR |
| django-11400 (d2) | 4/2 | 128s | 只修 admin filter 路径；隐藏期望=Field.get_choices 回退 Meta.ordering（首循环候选4 i1 已证只在 test_patch） |
| django-14011 (d3) | 0/17 | 164s | **补丁自破**：close_request 重写弄坏 connections_override 传参，eval `TypeError: __init__() got an unexpected keyword argument 'connections_override'`，17 f2p 全 setUpClass ERROR；模型自验跑的是旧 servers 测试 |
| django-14315 (d3) | 9/2 | 56s | 明示 test_nopass 断言 {} 而本修返回 None（"intended behavior change"）→ 契约口径 |
| django-15629 (d3) | 1/1 | 662s | 自述"1838 项全部通过"；无 mysqlclient，模板层断言代真连 DB |
| requests-2317 (d2) | **8/0** | 105s | **纯 P2P 回归**：f2p 全过，终稿"9 checks passed"，但 test_auth_is_stripped…/test_conflicting_post_params(TypeError) 挂=补丁引入 |
| requests-2931 (d1) | **1/0** | 45s | 修 data= 误伤 params= 编码（_encode_params 双路径），`test_params_bytes_are_encoded` TypeError；另 81 ERROR=判分镜像 httpbin fixture 递归（环境性） |
| xarray-2905 (d1) | 0/1 | 334s | **终稿未完成承诺**："regression comparison is still running … I'll report"——后台基线对比没等完就收工 |
| xarray-3993 (d2) | 0/2 | 51s | 弃用策略选错：硬移除 dim 不留 shim（"I did not add a dim shim"），隐藏测试期望弃用兼容 |
| xarray-4687 (d1) | judge空 | 205s | 刻意不修算术路径（"deliberately did not change"），范围窄于隐藏期望；判分工件损坏见 §10.1 |
| pylint-4604 (d3) | 0/21 | 351s | 终稿"27 passed" vs 隐藏测试整文件收集 ERROR（接口不匹配），21 f2p 全来自 collected 0/1 error |
| pylint-4661 (d2) | 0/1 | 207s | 终稿"82 passed, 1 failed(旧断言)" vs 隐藏 unittest_lint.py 收集 ERROR |
| pytest-10356 (d1) | 0/1 | 561s | 标记顺序实现 base-first，隐藏期望本类优先再 MRO（首循环候选4 i3 口径） |
| pytest-7205 (d2) | 1/9 | 146s | 目标测试文件本机不可运行（断言重写器 vs py3.11），只验证 issue repro，9 f2p 无法本地校准 |
| sphinx-10435 (d1) | 0/1 | 93s | 终稿"109 passed"；隐藏测试断言修后精确标记，模型只能猜措辞（Pygments 版本伪差异干扰） |
| sphinx-11510 (d1) | 0/2 | 512s | 事件语义自定（source-read 不再对 include 触发）；自述"byte-identical to upstream"仍 2 f2p 挂 |
| sphinx-8548 (d2) | 0/1 | 544s | MRO 文档注释 namespace 优先级选错（首循环候选4 i2），重 shim 环境 |
| sympy-16597 (d3) | 0/3 | 1226s | 窄假设规则 vs 上游 complex→finite 大改（oo.is_integer 期望 False）；自述"wider sweep not completed"；wall 已 1226s |
| sympy-17318 (d2) | 0/1 | 227s | 空 surd 列表浅 guard（`return S.One,[],[]`）vs 更深 split_surds 修；终稿"51 passed" |

### 10.3 行为域扫描（预注册正则冻结版，官方 m3 臂 120 run 全量实测）

正则（已冻结，勿再漂移；出处：本循环扫描脚本，快照 runs）：
- `PASS_CLAIM`（终稿验证通过自述）=`\b\d+ (tests?|items?|cases?|checks?|scenarios?)\b[,\.]?\s*(all\s*)?(passed|OK)\b|\b\d+ passed\b|\bpassed: ?\d+\b|exit(ed)? (with )?(code )?0\b|全部通过`（-i）→ 命中 **69/120**，其中官方败题 **15**。
- `SAMEFAIL`（基线对比声明）=`identical failure|fail(s|ed)? (set[s]? )?identically|(failure|failure list|failure set)s? [^.]{0,60}identical|无(新增)?失败|零新增失败|no new failures` → 命中 25/120（败题 8）。
- `PENDING`（未完成承诺）=收紧版（`I'll (report|finish|follow up|complete)|will report|still running|background (comparison|run|job)|not yet (complete|finished)|尚未(完成|跑完)|待(续|完成|报告)…`）→ 命中 **1/120**（xarray-2905）。**首版宽正则（含裸 `as soon as`/`not complete`）有假阳性（django-14011 的普通连接词、sympy-13877），已弃用——该行为域 m3 臂仅 1 题，不可作候选域，登记为死路防重试。**
- `越权改测试`（patch.diff 触测试文件）→ **0/120**（官方 prompt 已禁且模型全守规）；`patch 触 setup.cfg` → 1/120（astropy-13236）。两域均无杠杆空间，登记死路。
- 环境受限自述（cannot run/not installed/无网等）→ 73/120（61%；败题 17/24）——覆盖面大但与旋钮无机制通道，仅作背景。

### 10.4 本循环候选（3 条，双轨；已随 submit_result 上送）

| # | 锚 | 旋钮（已证） | 承诺域（机械判据+成员数） | 速筛 5 题（全域内，官方 m3 侧全败，wall 均 ≤561s 远离内层 25m） |
|---|---|---|---|---|
| G1 | m3fail | `--effort high`（变体 `/tmp/mcode-tune-implementer/variants/effort-high` 复用；**切 m3 锚前必须先做 m3 通道穿透冒烟**：探针只在 m31f 通道证得 thinkingLevel=high，M3 的 default 解析为 medium——判据=anolis llm-call.json 出现 model=MiniMax-M3 ∧ thinkingLevel=high） | 「验证信号在场的口径/推演型失败」：①last-row False ②judge f2p_failure≥1 ③patch 无测试文件 ④eval 无收集级 ERROR ⑤终稿含 PASS/SAMEFAIL/口径声明信号 → **17 题**；速筛 5 题逐题人工归因为口径选择错（11400 隐藏期望路径/10356 标记顺序/8548 namespace 优先级/17318 修的深浅/3993 弃用策略） | django-11400, pytest-10356, sphinx-8548, sympy-17318, xarray-3993 |
| G2 | m3fail | `--prompt-mode coding`（变体 `…/variants/prompt-mode-coding` 复用；m3 冒烟判据=llm-call.json systemPrompt 开头语 `You run inside MiniMax Code…` 且 ≈17.2KB） | 「自证失真」：last-row False ∧ 终稿 PASS_CLAIM → **15 题**；机制引证 S089（strategies.csv:90，裁决 A：自评置信度与证据强度脱钩） | django-10999, pylint-4661, pytest-7205, sphinx-10435, sympy-17318 |
| G3 | behavior | 同 G2 旋钮（共享变体，分别报 outcome） | 预注册行为「终稿验证通过自述」（PASS_CLAIM）：120 run 命中 69（败 15/过 54）；outcome=行为计数+通过率**双报**（终审 issue3 C 路线）；官方过题命中者只作不退化对照槽单列不计净分（§6.2 规则⑤） | django-10999, pylint-4604, pytest-7205, sphinx-10435, xarray-2905 |

**主动排除与理由（防红队"域外/不可翻"否决）**：django-10097（判分镜像模板缺失，首循环已证不可翻）；sympy-16597（官方 1226s，effort-high 墙钟上浮即撞内层 25m=红队候选3 i3，且其"更广 sweep 未完成"归因需更深修非档位可保翻）；pylint-4604/4661 不入 G1（收集级错误，判据④排除；4604 保留在 G3——其自证失真行为成立）；xarray-4687（判分工件 0 字节，数据质量存疑不入任何速筛）。**机制引证已核原文**：S093=strategies.csv:94（Opus 4.5 最高档 +4.3pp/token−48%；csv 自注"档位语义由厂商定义、跨模型不可比"——与本循环探针 m31f 侧三层证据并用，不外推）；S095=csv:95（overthinking 反向风险，B 级，G1 备案）。

### 10.5 本循环未跑/登记

- 未跑：任何变体实跑（本阶段只起草；变体与 driver 已由探针轮建好且冒烟过 m31f 通道）；m3 通道两旋钮穿透冒烟（已写为候选前置必检）。
- 死路登记（下轮勿重试）：PENDING 行为域（m3 臂 n=1）、越权改测试域（n=0）、纯 P2P 回归判据域（f2p_failure=0 ∧ resolved=false 仅 2 题：requests-2317/2931，凑不出 5）、环境受限自述域（n=73 但无旋钮机制通道）。
- 数据质量：xarray-4687 judge.json 0 字节（results.jsonl 仍记 reward=False）——判分管线在飞覆写风险的实例，官方侧取数纪律（§7.1）再加一条：**引用 judge.json 前先 `wc -c`**。
- 假阳性教训：行为正则禁止收录裸 `as soon as`/`not complete` 等普通语段（本轮实测误命中 django-14011/sympy-13877），冻结版已在 §10.3。

## 11. 第二循环·完整账（状态记账员，写入时点 **2026-10-22 08:08 CST**）

> 本节接在 §10 之后，**不改写 §0–§9 首循环内容**。本循环工作流 run = `dwfrun-1eedf1ee-7c26-4831-be01-87ccd91ef47f`（脚本 `.zcode/workflow-drafts/研究组2-调优组.dwf.ts`，6 相位：机制准备 → 旋钮探针 → 双轨候选起草 → 红队逐条审候选 → 单点改造与5题配对速筛 → 红队终审与落账）。记账员本次的中间产物来源同 §8：**不在工作区文件系统**，从 `~/.zcode/cli/db/db.sqlite` 的 `dwf_node`（node 32258–32432）读出；另对文件系统与 anolis 做了独立复算，逐条注明。

### 11.0 元信息与 as-of

| 项 | 值 | 出处 |
|---|---|---|
| 本循环官方臂**速筛快照** | `/tmp/mcode-tune-B2 重复读同一文件（轨迹级行为域）/official-snapshot-20261021T230753Z/`；`as-of.txt:1` = `snapshot_as_of: 2026-10-22 07:07:53 +0800 / UTC 2026-10-21 23:07:53Z`；`as-of.txt` 共 1214 行（1 行表头 + 1208 条 per-file size+sha256） | 本记账员 `head -3` / `wc -l` 实跑 |
| 官方 m3 臂 last-row（该快照） | rows 226 / unique 120 / judged 119 / **pass 95 / fail 24**（24 败名单与 §10.1 逐题一致） | 本记账员 python3 解析实跑 |
| 官方 m31f 臂 last-row（该快照） | rows 221 / unique 120 / judged 119 / **pass 114 / fail 5**（django-10097/10999、psf-requests-2317、pytest-7205、sphinx-10435） | 同上 |
| 探针三快照 | `official-snapshot-20261021T201106Z`（effort）/ `…204232Z`（prompt-mode）/ `…210543Z`（max-steps），均在 `/tmp/mcode-tune-probe-effort/` | node 32302 / 32320 / 32337 evidence |
| **官方臂「在飞」前提已作废** | `/tmp/mcode-dispatch.log` 末行 `05:33:26 mcode-dispatch 队列跑完退出`；巡检日志 05:1x 记 120/120 双档案满判收官（m31f 95.0% / m3 77.5%） | node 32342 issue4；`状态观测/巡检日志.md:171` |
| 本账 §7.3 的「官方臂在飞 pid 3711801」 | **已过期**，下轮一律改用终局账本 + as-of（见 §11.9 新增口径 11） | node 32342 issue4 |

### 11.1 机制件路径

| 件 | 路径 | 状态（`ls -la /tmp/mcode-tune-implementer/` 本记账员实跑） |
|---|---|---|
| 独立变体驱动 | `/tmp/mcode-tune-implementer/mcode-tune-driver.py` | 31294 B，mtime 03:37:51 |
| 官方臂快照器 | `/tmp/mcode-tune-implementer/snapshot-official.sh` | 4189 B，03:11:52 |
| 变体目录 | `/tmp/mcode-tune-implementer/variants/{base,effort-high,prompt-mode-coding,max-steps-120,max-steps-15,m1-effort-high,b2-prompt-mode-coding}/` | 7 个变体，均含 `run-one.sh` + `knobs.json` |
| 部署清单 | `deploy-manifest.{base,effort-high,prompt-mode-coding}.json` + `deploy-manifest.json`（06:56） | sha256 登记远端部署件 |
| 行为计数器 | `/tmp/mcode-tune-candidates/behave_count.py` → anolis `/tmp/behave_count.py` | **本记账员亲验** `ssh anolis 'sha256sum /tmp/behave_count.py'` = `e667c13e983cbbd88d6b2234d26e6a177971a5d0e77c5b547c8402aa7a1028ec`（与 knobs.json 声明一致） |
| 改造臂产物根 | `/tmp/mcode-tune-implementer/out/<arm>-<profile>/results.jsonl` + `runs/<task>/{mcode.log,patch.diff,eval.log,judge.json}` | 8 个 arm-profile 目录 |
| 候选侧目录 | `/tmp/mcode-tune-M1【G1+A1 互证合并】/`、`/tmp/mcode-tune-B2 重复读同一文件（轨迹级行为域）/`、`/tmp/mcode-tune-candidates/`、`/tmp/mcode-tune-draft-glm/`、`/tmp/mcode-tune-redteam/` | 本记账员 `ls -d /tmp/mcode-tune-*` 实跑 |
| 日志 | `logs/{smoke-031852, smoke-retry-033758, probe-effort-high-0412, probe-promptmode-0442, probe-maxsteps-0506, b2-screen-m3-070828}.log` | 6 份 |

**机制件红队结论（node 32289，verdict=`confirmed`，5 issues 逐条登记）**

1. **【minor·文案过实】** driver docstring `:67-68` 称官方 repo 缓存「只读复用」，实测 `prepare()`（`mcode-tune-driver.py:381-398`）以 `MCODE_REPOS=/data/bench/mcode-swev/repos` 走共享 `repo-cache.sh`，会在官方目录建 `.<slug>.lock`、毒缓存自愈路径 `flock` 下 `rm -rf` 后重 clone；该脚本与官方派发器内嵌 REPO_CACHE 功能行 **16/16 逐行相同**（difflib `FUNC_IDENTICAL: True`），anolis `/data/bench/mcode-swev/repos` 目录 mtime=03:18（冒烟期被写）。不违反纪律①②，但「只读」言过其实。
2. **【观测·A/B 设计风险】** 冒烟题 `django-10999|m31f` 两侧结果不一致：官方臂 `resolved=false`（f2p 0/2，`eval.log` 尾 `FAILED (failures=5)`），改造 base 臂 `resolved=true`（f2p 2/0、p2p 10/10，`Ran 12 tests ... OK`）。两侧 run-one 语义逐字一致 → 只能归因模型采样噪声。**单轨单次 A/B 的「净题数」判读会被噪声淹没**，速筛/深测须先定噪声控制。另：官方补丁结构性含 `prompt.txt`/`mcode.log` 两个 harness 文件，两臂补丁非字节同构，配对审计须写明。
3. **【cosmetic】** 快照 agg 两目录（`bench-official-mcode-m31f/m3`）在快照内为 `mkdir` 新建（目录 mtime=快照时刻），仅 `results.jsonl` 文件本身 `cp -a` 保真；tier 六目录为整目录 `cp -a`（目录 mtime 与源一致，6/6 match）。`as-of.txt` 登记文件级 sha256+mtime，数字引用不受影响。
4. **【informational·披露完整性】** 冒烟实为 **2 跑 1 崩**：首跑 `logs/smoke-031852.log` 于 03:29 `/tmp` EDQUOT 窗口崩溃（`OSError [Errno 122]`，traceback 行号 675/670/608/495 对应旧版驱动；现行版 `:504-518` 已加 10 次退避重试，driver mtime 03:37:51 即该修复时点）；重跑 `logs/smoke-retry-033758.log`（03:37:58–03:50:32）通过。**`smoke_ok=true` 指重跑**，不得只写「通过」。
5. **【transparency】** 红队在 `/tmp/mcode-tune-implementer/__pycache__/` 重新生成了 `.pyc`（04:01），所有机制件源文件 mtime 未变；快照器自跑留目录 `/tmp/mcode-tune-redteam/snap-verify`，未写实现员目录、未写 `/tmp/bench-official-*` 与 `/tmp/mcode-dispatch/*`（`SOURCES_UNCHANGED: true`）。

### 11.2 三探针结论（node 32302 / 32320 / 32337；复核 node 32342 = `confirmed`）

| 旋钮 | 探针题（profile） | 判定 | 决定性证据（anolis `~/.minimax/v2/sessions/2026/10/21/*/llm-call.json`） | 产物 |
|---|---|---|---|---|
| `--effort high` | `pylint-dev__pylint-4604\|m31f` | **`takes_effect=true`** | `thinkingLevel` 三臂：effort-high 臂 `20-17-54-754`=**high**；base 对照 `20-25-45-086`=default；官方臂 `17-02-49-384`=default。session 归属按 `messages.jsonl` 内 work 路径 grep（54/43/27 行）判定，不以时间戳猜 | `out/effort-high-m31f` + `base-m31f`、`logs/probe-effort-high-0412.log`、快照 `…201106Z` |
| `--prompt-mode coding` | `psf__requests-6028\|m31f` | **`true`** | `systemPrompt` 被换：coding 臂 `20-43-00-962` sha256 `2dd03a811f43834c` **17219 B**，开头 `You run inside MiniMax Code, a workspace developed by MiniMax.`；base 臂 `20-49-43-738` `17e3b1e32ccd9bc5` **15655 B**，开头 `You are a coding agent running in the MiniMax Code terminal…`。同 model / 同 thinkingLevel=default / 同 18 tools | `out/prompt-mode-coding-m31f`、`logs/probe-promptmode-0442.log`、快照 `…204232Z` |
| `--max-steps 120` | `django__django-11532\|m31f` | **`false`**（真旋钮、**条件生效**、120 档对中位题是惰性护栏） | 120 档臂 assistant=**37** ≪ 120、rc=0、llm-call.json **无 maxSteps 字段**（键面实测）；机制由 **15 档演示臂**实证：assistant=**16** 即切、`rc=7`、mcode.log 恰 1 行 `mcode exec limit_exceeded: The run reached its step limit. Increase --max-steps or narrow the task.`；官方 m31f rc 集合 `{0×118,1,4,6}` 无 7 → rc=7 ↔ limit_exceeded 1:1 | `out/max-steps-120-m31f`、`max-steps-15-m31f`、`logs/probe-maxsteps-0506.log`、快照 `…210543Z` |

**探针附带发现（三例全中，node 32342 evidence 复算）**：官方 **m3** 臂同题 session 的 `thinkingLevel=medium`（`pylint-4604` 17-02-56-785 / `requests-6028` 17-54-08-684 / `django-11532` 15-38-27-496，model=MiniMax-M3）——**`default` 档随模型解析不同**，未来 m3 锚点引用档位须注意。

**输出面发现**：终稿语言随 run 漂移（max-steps 探针 base 臂中文、official 臂英文）→ **语言不可作旋钮签名**（探针已自行降级）。coding 模式终稿整篇中文、节标题 `## 根因 / ## 修复 / ## 自验结果` vs base/官方英文 `Root cause / The change / Verification` → **该旋钮直接改变 PASS_CLAIM 正则的命中面**（G2/G3 否决意见已据此立「计数下降须抽样人工核对」纪律）。

**探针红队（node 32342，verdict=`confirmed`）4 条非否决事项**

1. **行为层噪声主导**：两个**无旋钮**臂同题噪声 `turns 58 vs 32(+81%)`、`thinking 73255 vs 46932(+56%)`、`toolResult 80 vs 39(+105%)`，**均大于 effort-high 的偏离**；仅 wall 在 ±9%（498206 vs 456883）。「high 档收敛更快 / 墙钟不涨反降」是 n=1 单观测 → 账本须标「行为层仅佐证、噪声主导，方向结论不立」。**决定性证据是请求层**。同条另指出 M1 候选把 base 混指两臂——457s 是**官方臂** wall，base 变体臂实为 498206ms。
2. **可复现性**：探针的 work 路径 grep 计数是「**含路径的行数**」而非出现次数（出现次数 76/66/117 等）→ 下轮探针须写明「按行计」。
3. **审计登记**：判分管线包装层 `tools/swev-judge.py` 在官方三题判分后、探针判分前被改过（mtime 2026-10-22 02:28，备份 `工具状态备份/observability-backup-swev-judge.py.20261022-022839.bak`），diff 实测**仅增量上报** `p2p_success/p2p_failure/tests_collected/swebench_version` 四字段，**resolved 计算路径逐字未动**；swebench 4.1.0 自 10-20 03:04 未变 → 语义零漂移，但须入账。
4. **上下文**：§7.3「官方臂在飞」前提过期（见 §11.0）。

### 11.3 候选红队结论逐条（4 条，双轨）

红队逐条节点：32367（M1）/ 32389（G2）/ 32394（G3）/ 32399（B2）。**批准 2、否决 2**。

#### 候选 M1「深口径推演/残差半修复（`--effort high` × m3 失败域 G1，screen_tasks 9 题）」→ **confirmed**（带 5 条整改）

1. **【计数口径·域大小差 1】** G1 五判据按字面规则复算实得 **18 题**（含 `django-10097`：f2p_failure=7 过②、patch 无测试文件过③、eval.log 不匹配④、mcode.log L27 `it fails identically before my change` 命中冻结 SAMEFAIL 过⑤），而 promised_domain 写「17 题」——17 = 18 **隐式**剔除 10097（其 eval.log 命中 `TemplateDoesNotExist`，属 A1 式环境过滤，但未写进五条判据）。9 道速筛题在 18/17 两种口径下均落域、无凑数，但**判据文本与域计数不一致**。
   > **本记账员独立复算**（07:07:53 快照，逐题判据位表见 §11.8-A）：五判据全过 = **18 题**（与红队一致），其中 `eval.log` 命中环境阻断正则者 **5 题**（django-10097、xarray-3993、pylint-4604、pylint-4661、pytest-10356）→ 若把「环境剔除」写成明文判据⑥，域 = **13 题**。**三个数（17 / 18 / 13）必须在下轮开工前定死一个并写进判据。**
2. **【判据⑤精度】** STANCE 备选 `deliberately` 过宽：`sphinx-8548` 的⑤命中是 `The name deliberately avoids collision with the mixin's unrelated get_attribute_comment`（代码命名理由，非隐藏测试口径声明）。该题域归属有独立实质证据，但**机械判据存在过纳入口**；复用⑤筛题应收紧为「口径声明须与验证/通过自述同句或同段共现」。
3. **【探针数字标注混用】** 见 §11.2 探针红队 i1。
4. **【风险登记】** 合并 9 题中 `django-15629` 官方 wall=661702ms（662s），超出原 5 题的 ≤561s 包线；S095（`strategies.csv:95`，overthinking，B 级）备案下 effort-high 若推高墙钟，距内层 1500s 上限余量收窄（探针 n=1 反向显示 high 更快，不构成否决，但该题应盯内层超时假阴性，首循环候选3 i3 先例）。
5. **【双报纪律·须写进结论】** M1 的 outcome 为单指标通过率（方向安全），但域定义⑤使用行为信号，且探针复核已登记**无旋钮两臂行为噪声 56–105%** → 「行为层仅佐证、方向结论不立」。**速筛/深测报告必须双报：通过率下跌或持平时，行为改善不得单独作为成功证据。**

#### 候选 G2「自证失真对账（`--prompt-mode coding` × m3 失败域「自证失真」15 题）」→ **rejected**（4 issues）

1. **【生死线·screen_task 不在承诺域】** `pytest-7205` 列入 screen_tasks，但在候选自己的 counting_rule 下**不在域内**：用候选原话命令复算两次均 =0；其终稿唯一验证陈述是 L18 `all 25 tests fail identically before and after my change`（SAMEFAIL 型**主动披露**环境受限，恰是非失真的反例）。且候选 promised_domain 自列的 15 题名单也不含 7205 → **screen_tasks 与域名单自相矛盾**（与首循环 5 条候选全否的共同死因「域外即否」同型，§7.9）。其余 4 题（10999 / 4661 / 10435 / 17318）真在域内。
2. **【引用选择性截断】** `sphinx-10435` 的「终稿『109 passed』」与实文不符：`runs-d1-m3/sphinx-doc__sphinx-10435/mcode.log:40` 原文为 **`109 passed, 8 skipped, 2 failed`**。PASS_CLAIM 命中本身合法，但**引文须逐字**。
3. **【域归属牵强·机制通道不匹配】** `pylint-4661` 按规则机械入域（PASS_CLAIM=1 ∧ reward=False），但其失败是隐藏测试整文件收集 ERROR（判分镜像依赖缺失），模型终稿明示只跑旧测试并解释了 1 个旧断言失败——**并非「自述通过而被在案证据反驳」的失真**；首循环候选5 i1 已证同题在 m31f 臂靠 `setup.cfg` 加 appdirs 翻面（配置动作 ≠ 自验结构动作，与 `--prompt-mode coding` 弱耦合）。留题即留一个「旋钮无机制着力点」的槽位。
4. **【双报纪律·须写进结论】** G2 outcome 为单指标通过率（方向安全），域定义用的 PASS_CLAIM 行为信号取自官方臂、稳定。**但**：①探针复核已登记无旋钮两臂行为噪声 56–105%，行为层仅佐证；②`--prompt-mode coding` 改变终稿结构（探针 n=1：coding 臂 `## 根因/## 修复/## 自验结果` vs base 臂 `## Root cause/## The change/## Verification`）**会直接改变 PASS_CLAIM 正则的命中面**。故速筛/深测报告必须双报，且行为计数的升降须抽样人工核对。

#### 候选 G3「终稿验证自述行为域（`--prompt-mode coding` × behavior 预注册计数+通过率双报）」→ **rejected**（4 issues）

1. **【生死线·screen_task 不在承诺域】** `pytest-7205` 同样问题（复算 =0，终稿是主动披露 `all 25 tests fail identically…`）。其余 4 题（10999 / 4604 / 10435 / 2905）行为=1 ∧ last-row reward=False ∧ status=completed ∧ route=minimax/MiniMax-M3，落域且配对 false 行在场。
2. **【三数计数差 1·对照槽含禁入题】** 候选称「败员 15 / 过题命中 54 / 120 个已完成 run 实测命中 69」。复算：快照 `runs-d{1,2,3}-m3` 恰 120 个 run 目录（60+40+20，无重复题），PASS_CLAIM 命中 69 = **败 15 + 过 53 + judge_error 1**（`django-16263`，last-row reward=None / status=judge_error，其 mcode.log 亦命中正则）。即「过题命中」实为 **53**，第 54 个是 §6.2 规则④**明令禁入**速筛/对照槽的 judge_error 题；「120 个已完成 run」表述亦不准确（**119 completed + 1 judge_error**）。**对照槽池须剔除 16263 后才可用。**
3. **【主指标可被「抑制宣称」刷分·双报未覆盖】** 主指标 = Σ题(改造臂行为=1 ∧ reward≠True) 只计坏例：改造臂若靠空终稿/截断/不再写验证自述把行为计数压到 0，主指标净差全绿而 resolved 崩塌。副指标（两侧 resolved 率单独报告、互不替代）能暴露通过率下跌 → 「藏报」洞在设计层已闭合，但「行为下降=改善」仍缺护栏。**须写进结论**：判为行为改善必须同时满足 (a) 改造臂终稿非空且结构完整（空转/内层超时/无终稿题单列，不计入行为改善）、(b) 两侧 resolved 率不降。另：`mcode.log` 在 text 输出模式下只含终稿消息；`--prompt-mode coding` 改变终稿结构 → 行为计数对表面形式敏感，**计数下降须抽样人工核对是「真的不再虚报」而非「换措辞/换结构逃过正则」**。
4. **【风险登记】** wall 93–361s 复算属实（10999=361s、4604=351s、2905=334s、7205=146s、10435=93s），远离内层 25m；与 G2 共享同一变体（已核与 base 仅 1 处 hunk），若双轨均过须按 §6.4 组合测试处理；m3 档案穿透冒烟本轮未跑（候选已披露为前置必检，准入判据：llm-call.json systemPrompt 开头语 `You run inside MiniMax Code…` 且 ≈17.2KB）。

#### 候选 B2「重复读同一文件（轨迹级行为域，`--prompt-mode coding`）」→ **confirmed**（带 4 条整改）— **本循环唯一 survivor**

1. **【审计留存·基线未落盘】** 官方臂行为基线（reread 三元组）没有持久化工件：`/tmp/mcode-tune-candidates/featcount-20261022T0544Z.json` 字段集实为 `{arm,task,reward,claim_verified,env_deflect,ran_target_test,claims_no_test_change,touch_test,touch_doc,resolved}`（已核），**不含** reread 三字段；B2 的 5 题基线数值只存在于候选散文与 anolis 临时 session（`~/.minimax/v2/sessions` 属易失资产）。速筛开跑前必须把逐题 `behave_count` 输出 JSON + as-of 落盘。
   > **本记账员已在 §11.8-B 落盘**：全量复算结果写入本机 `/tmp/recompute_behave_official_m3.json` 与 anolis 同名文件，域成员名单可复算。
2. **【行为层噪声纪律】** reread 计数量级小（5 题 `reread_paths` 全为 1，`max_rereads` 2–9），而无旋钮两臂行为噪声达 56–105% → **±1 的 reread 差不具旋钮可归性**。候选自限为「观测通道」而非宣称改善方向，方向正确；结论须保留该自限（行为层只作佐证，主口径仍是 resolved，n=5 仅 20pp/题只能写方向）。
3. **【方向性预注册须冻结】** reread 减少既可解读为收敛效率提升、也可解读为放弃深挖/早停。**必须在速筛前预注册**：`reread 下降 ∧ resolved 不降` → 记「效率改善」；`reread 下降 ∧ resolved 降` → 记「早停风险」单列。防事后择优叙事。
4. **【冒烟前置·同 G2/G3】** m3 档案穿透冒烟在候选轮未跑（候选已披露）；变体纯净性已核（与 base 仅 1 处 hunk），`mcode-tune-driver.py:74-75` 映射 m3 → `minimax/MiniMax-M3`。
   > 该前置在**速筛执行阶段已实跑并通过**（node 32409 `smoke_ok=true`），见 §11.4。

**Survivor caveats（第二循环整改③销账，对应终审 issue 3；销账时点 2026-10-22 08:2x CST，本条与 §11.10-C 同源）**

1. **样本量 n=1**：每臂每题 **n=1**，net=+1 只是单次采样差；且改造臂 5 个数据点中 `django-10999` 是 06:57 冒烟 run 而非正式速筛跑（§11.4(2) 已披露，同变体/同驱动/同判分链但非正式槽位）。
2. **同参噪声同级**：无旋钮两臂同题实测 `turns 58 vs 32（+81%）`、`thinking +56%`、`toolResult +105%`（§11.2 探针红队 i1）→ ±1 的 reread 差与 ±1 的净题差**均不具旋钮可归性**，行为层只作佐证、主判读仍是 resolved（§11.3 B2 整改2 自限继续有效）。
3. **通过率增益与承诺机制无因果链**：唯一净胜题 `sympy-16597` 的承诺行为（重复读）**原样未动（reread 1→1、max_rereads 2→2、consec 1→1；本记账员 08:2x 亲跑冻结计数器复算，§11.10-B）** → 1/5 的通过率增益并非由承诺行为介导；且该题在 m31f 官方臂本就可解（快照 last-row `reward=True, wall=700033ms` vs m3 官方 wall 1225634ms，本记账员 08:2x 从同一 07:07:53 快照亲算），属「另一个模型已会做」的题。深测若无法定位非行为机制路径，结论只能写「存在与 `--prompt-mode coding` 相关的非行为机制路径（待定位）」，**不得写成行为域被改善**（§11.8-B 净分口径警告）。
4. **结论边界**：n=5 → 20pp/题，只能写方向，不得写「提升 X pp」；沿用 G2/G3 否决意见所立规矩——「通过率下跌或持平时，行为改善不得单独作为成功证据」「判为行为改善须同时满足终稿非空结构完整 + 两侧 resolved 率不降」（§11.3 G3 整改3、§11.8-B 护栏 a/b）；**B2 深测开跑前必须先过 m31f 回归抽查准入门**（§11.10-A 登记、§11.9-19），未过门则本 survivor 结论不予采信。

### 11.4 速筛执行：两侧数字与快照目录

**M1 速筛：未进入**（前置穿透冒烟硬失败）。**B2 速筛：已跑，产生 1 条 survivor 候选。**

#### (1) M1 冒烟硬失败（本记账员亲验原文）

```
$ cat /tmp/mcode-tune-implementer/out/m1-effort-high-m3/runs/pydata__xarray-3993/mcode.log
mcode exec failed: minimax/MiniMax-M3 does not support reasoning effort selection, so --effort high cannot be applied.
```

`out/m1-effort-high-m3/results.jsonl` 该行 `status=completed`、**`reward=None`**（无补丁、无判分）。同题 base 对照臂 `out/base-m3/results.jsonl` `reward=True`（wall 175040ms，judge `resolved=true` f2p 2/0 p2p 2398/0）→ **失败纯系旋钮与 M3 不兼容，非驱动/通道问题**。代码级根因：拒绝文案在 anolis `~/.npm-global/lib/node_modules/@minimax-ai/code/chunks/chunk-G7Q4HUMC.js`，门槛逻辑按模型 effort 档位表，**M3 档位列表为空**（`s.length===0` 即抛该错），m31f 列表非空；失败跑连 `llm-call.json` 都未产生（22-42-22-442 会话无该文件 = 拒绝发生在任何 LLM 调用前）。

> **硬约束（须写回 §11.9）**：`--effort high` 类旋钮在 **m3 锚上是死路**（除非路由侧变更）。这实质限定 §11.2 探针①的 `takes_effect=true` —— 该判定**只在 m31f 路由成立**。

#### (2) B2 速筛两侧数字

题集 5 题（node 32413 记）：`django-10999`、`django-15629`、`sphinx-8548`、`sympy-16597`、`astropy-13398`（全为官方 m3 臂败题，即题集 100% 满足 m3fail 锚）。

| 侧 | 产物路径 | 通过率 | 逐题 |
|---|---|---|---|
| 官方（as-of 2026-10-22 07:07:53） | `…/official-snapshot-20261021T230753Z/bench-official-mcode-m3/results.jsonl` + `bench-official-mcode-d{1,2,3}-m3/runs/<t>/` | **0 / 5** | 10999 f2p 0/2、15629 1/1、8548 0/1、16597 0/3、13398 0/4，全 `reward=False ∧ status=completed` |
| 改造臂 `b2-prompt-mode-coding-m3` | `/tmp/mcode-tune-implementer/out/b2-prompt-mode-coding-m3/results.jsonl` | **1 / 5** | 仅 `sympy-16597` reward=true（`judge.json`：`resolved=true, f2p_success=3, f2p_failure=0, p2p_success=74, p2p_failure=0, tests_collected=77, swebench_version=4.1.0`，wall 1105507ms < 1500s 内层上限）；其余 4 题 reward=false，全 `completed / attempts=1` |
| **net** | — | **+1** | 唯一翻面题 = sympy-16597 |

**双报（本记账员本轮亲复算，逐题三元组见 §11.8-B）**

| 读法 | 官方 | 改造 | 备注 |
|---|---|---|---|
| resolved（通过率，主判读） | 0/5 | **1/5** | net=+1，n=5 → 20pp/题，**仅方向性** |
| Σ `reread_paths` | 5 | 5 | 「5←5」记录值只在此读法下成立 |
| 逐题在场（`reread_paths≥1`，= B2 域定义） | 5 | **3** | 与记录值 5 不符 |
| Σ `max_rereads` | 22 | 17 | |
| Σ `consecutive_dup_read_turns` | 7 | 3 | |

> 【第二循环整改②销账·终审 issue 2】上表聚合行**不得单独引用**：行为指标的**定义、逐题 `reread_paths`/`max_rereads` 明细、求和/在场两种读法并列与禁裸标量纪律**统一落在 §11.10-B（本记账员 08:2x 用冻结 `behave_count.py` 亲跑复算，与红队复算 `官方 [1,1,1,1,1] / 改造 [0,1,3,1,0]` 逐位一致）。

**逐题方向是混合的（记账员复算）**：`django-10999` 1→0、`astropy-13398` 1→0（行为消失）；`sphinx-8548` 1→3（行为三倍化，`max_rereads` 9→13）；`django-15629`、`sympy-16597` 持平 1→1。**唯一翻面题 sympy-16597 的行为无改善（1→1）** → **通过率增益并非由承诺行为介导**；且该题在 m31f 官方臂本就可解（wall 700033ms vs m3 官方 1225634ms），属「另一个模型已会做」的题。

**数据点来源披露（红队 issue 2，补记）**：5 个改造臂数据点中 **`django-10999` 是 06:57 的 m3 通道冒烟 run**（driver 日志 `logs/b2-screen-m3-070828.log:1` =「跳过 django__django-10999（本账本已有终判行）」，其行来自冒烟日志 `smoke-m3-0657.log`，wall 59.8s）。同变体/同驱动/同判分链、`attempts=1`、completed、卫生检 clean，**数据有效但非正式速筛跑**。

**补丁卫生（5 题全过）**：`out/b2-prompt-mode-coding-m3/runs/<t>/patch.diff` 仅含仓库源码文件（16597 = 6 个 sympy 源文件；13398 = 2 源文件 + 1 changelog rst），`grep -cE '^diff --git a/(prompt.txt|mcode.log|AGENTS.md|hints.txt|.meta/)'` = **0 命中**。`13398` 无新增回归：官方与改造 `eval.log` 的 FAILED/ERROR 行集合 diff 为空（各 10 行、逐一相同）→ 改造 judge 的 `p2p_failure=5` 为官方同款既有失败。（以上为红队 node 32417 的原复算，记账员未逐题重跑该 grep。）

**快照目录**：速筛用快照 = `/tmp/mcode-tune-B2 重复读同一文件（轨迹级行为域）/official-snapshot-20261021T230753Z/`（as-of 2026-10-22 07:07:53 +0800；`as-of.txt` 1214 行 = 表头 + 1208 条 per-file sha256；红队复算 `1208 OK / 0 FAIL`，其中 `bench-official-mcode-m3/results.jsonl` sha256 `8aa08fec…` 与 GLM 起草快照逐字节相同）。**快照 07:07:53 早于速筛首跑 07:08:29，筛前冻结成立。**

#### (3) m31f 回归抽查锚：速筛阶段**完全未执行**（终审 issue 1 的实证）

- **本记账员亲验**：`ssh anolis 'ls /data/bench/mcode-tune/runs/'` → 7 个变体目录，**逐个 `ls` 均为空**（跑后清理），**无任何 `*-m31f` 工作目录**；`ls /tmp/mcode-tune-implementer/out/` → 无 b2/m1 的 m31f 账本（`base-m31f` 仅存探针轮 4 题）；`logs/` 无 m31f 速筛日志。
- **官方 m31f 侧同一 5 题（记账员从同一快照 last-row 亲算）**：**4 过 1 败** —— django-10999=**False**、django-15629=True、sphinx-8548=True、sympy-16597=True、astropy-13398=True。**即该「m3 失败域」大部分是 m3 特有病**，钦定模型 m31f 对 `--prompt-mode coding` 的回归暴露面完全未测。

### 11.5 终审意见（node 32422，红队 step-5，全程未参与其它环节）— **verdict = `rejected`，5 issues**

1. **【口径·回归抽查 = 未执行且未登记】** 裁决口径三要素之一（m31f 留回归抽查锚）无任何执行证据（证据见 §11.4(3)，与记账员亲验一致）。5 个速筛题在 m31f 官方臂 4 过 1 败 → 偏离钦定 m31f 后最需要的一环完全未测。
2. **【口径·双报 = 行为数不是自明量，且按域定义不可复现】** 记录只给 `official_behavior=5 / modified_behavior=5` 两个裸标量，无定义、无逐题明细。红队用冻结计数器（两端 sha256 均 `e667c13e…`）复算：官方 `reread_paths=[1,1,1,1,1]`、改造 `[0,1,3,1,0]`。**只有按「求和」读才得 5 vs 5**；按候选自己 promised_domain 的逐 session 在场定义则 **5 vs 3**。该标量同时掩盖逐题分裂（2 题改善 / 1 题恶化 / 2 题不变）。
3. **【结论边界·survivor 的唯一依据不成立于其承诺机制上】** 唯一净胜分 sympy-16597 恰是「承诺行为毫无改善」的一题（1→1），且该题在 m31f 官方臂本就可解；改造臂每臂每题 **n=1**，而同参噪声同级已实测（`turns 58 vs 32`、`thinking +56%`、`toolResult +105%`）。`screens/survivors` 条目**零 caveats**，与每条 probeFact 都带显式 caveats 形成反差。红队自己在 G2/G3 否决意见中立有规矩（「通过率下跌或持平时行为改善不得单独作为成功证据」「判为行为改善必须同时满足 (a) 终稿非空且结构完整 (b) 两侧 resolved 率不降」），survivor 声明未体现。
4. **【记录完整性·approved_count=2 只记 1 个速筛，另一已批候选的硬失败被略去】** M1（node 32388 confirmed）与 B2（node 32403 confirmed）为两个批准候选，记录只含 B2 一次速筛。M1 冒烟硬失败虽已在 DB node 32408 登记（非隐瞒），但交给终审的「全部记录」未含此事，而它**实质限定 probeFact[0] 的 `takes_effect=true`**：m3fail 锚的 effort-high 候选在当前路由下是死路（原文见 §11.4(1)）。
5. **【未发现编造，可复现部分全部对账】** 官方侧 0 过/改造侧 1 过、两侧 wall、judge.json 逐字段、session 归属、变体单点 diff、补丁卫生、快照哈希**全部独立复现通过**。**否决针对的是口径执行缺口与结论边界，不是诚实性。**

**终审整改建议 4 条（列而未擅动，下轮须逐条销账）**

1. 速筛/深测前补 m31f 回归抽查（改造臂在 m31f 上跑同题单，判据：resolved 不跌 + 行为不恶化），并在记录中**显式登记为待执行项**；
2. behavior 指标改写为「**定义 + 逐题 reread_paths/max_rereads 明细 + 求和/在场两种读法并列**」，禁止只报聚合标量；
3. survivor 结论补 n=1 / 噪声 / 单题翻盘 caveats，并说明通过率增益与承诺行为**无因果链**；
4. 把 `--effort` 在 MiniMax-M3 路由被拒一事写回记录，作为 **m3fail 锚选旋钮的硬约束**（effort 类旋钮在 m3 锚上禁用，除非路由侧变更）。

### 11.6 本循环未跑 / 未复核 / 记账员未独立复算（据实登记）

- **未跑**：M1 速筛（冒烟即失败）；**B2 的 m31f 回归抽查（零执行）**；20 题深测（未触发）；组合测试与轨迹冲突观察（§6.4：无第二个通过者）；任何全池复跑；`--max-steps` 数值退出码的 JS 映射函数在压缩包内未能定位（改用 rc=7 的 1:1 实证对应）。
- **记账员本次亲自复算并通过的检查**：`ls -la /tmp/mcode-tune-implementer/`、`ls -d /tmp/mcode-tune-*`、B2 快照 m3/m31f last-row 统计与 5 题逐题 reward、改造臂 `results.jsonl` 5 行、`as-of.txt` 表头与行数、`sympy-16597` 改造臂 `judge.json`、M1 失败 `mcode.log` 全文与 `results.jsonl`、`ssh anolis 'sha256sum /tmp/behave_count.py'`、`ssh anolis 'ls /data/bench/mcode-tune/runs/*/'`（回归抽查缺失的实证）、**两侧 10 个 session 的 `behave_count.py` 逐题复算**、**官方 m3 全量 119 session 的行为基线复算并落盘**、**G1 五判据在 24 败上的逐题复算**。
- **记账员未复算、仅转录红队/终审记录的数字**：三探针的 `thinkingLevel` / `systemPrompt` 哈希与长度、turns/thinking/toolResult 计数、mcode.log 字节数、探针臂 wall、M1 9 道 screen_tasks 的域内性与官方侧逐题 judge 字段、G2/G3 的 15 题 / 69 题域成员名单、终审的「1208 OK / 0 FAIL」与「补丁卫生 0 命中」原复算、机制件红队的 `FUNC_IDENTICAL: True` 与 `SOURCES_UNCHANGED: true`。
- **已知会随时间失效的资产**：anolis `~/.minimax/v2/sessions/` 的具体 session 目录（易失）。本轮已把**官方 m3 全量行为基线**落盘（§11.8-B），但**改造臂 session 的原始 JSON 未落盘** → 深测前须补。（→ 2026-10-22 10:07 已补：改造臂全部 20 session 落盘 `/tmp/mcode-tune-B2-behavior-baseline/`，见 §11.10-F。）
- **能力缺口（同 §8）**：本循环中间产物同样只在 `dwf_node.result_json`，不在工作区文件系统；本记账员以 `python3` 的 `sqlite3` 模块只读连接读出（本机 `sqlite3` CLI 未安装，`which sqlite3` 空）。

### 11.7 下一循环动作（可直接派工）

| # | 动作 | 角色/模型 | 前置 | 产出落点 |
|---|---|---|---|---|
| 1 | **销账终审 4 条整改**（§11.5 末四条） | 红队 step-5 复核 | — | 本文件 §11 |
| 2 | **重过终审门**（B2 未销账不得开深测） | 红队 step-5（须为未参与本轮修订的新实例） | 1 | 终审 verdict |
| 3 | **m31f 回归抽查锚开跑**（设计见 §11.8-C） | 改造实施员 + 速筛执行员 | 2 | `/tmp/mcode-tune-B2…/regress-m31f/` |
| 4 | **行为基线全量落盘**（改造臂逐题 `behave_count` JSON + as-of） | 改造实施员 | 2 | `/tmp/mcode-tune-B2…/behavior-baseline-<as-of>.json` → **已落盘（2026-10-22 10:07 CST）**：`/tmp/mcode-tune-B2-behavior-baseline/`（改造臂全部 20 session + as-of + sha256，§11.10-F） |
| 5 | **20 题深测**（设计见 §11.8-B/C；准入：终审 confirmed + 回归抽查不恶化） | 同上 + 红队 | 2,3,4 | 深测读数写回 §11 |
| 6 | **M1 谱系换通道**：`--effort high` 在 m3 被 CLI 一票拒绝 → 或改 config 级 thinking 档位（须另立候选 + 独立冒烟）、或改锚回 m31f（须先解 m31f 败仅 5 题的结构约束） | 候选起草 | — | 新候选送红队 |
| 7 | **G1 域计数定死**（17 / 18 / 13 三选一写进判据文本） | 候选起草 + 红队核 | — | 候选 `counting_rule` |
| 8 | 更新本状态账 | 状态记账员 | 每轮末 | 本文件 |

**M1/G2/G3/B2 之外的新候选空间（据本轮证据，可直接起草）**：`--max-steps` 虽判 `takes_effect=false`（条件生效），但 **rc=7 / `limit_exceeded` 是本厂唯一被 1:1 实证的截断信号**，可作「失控护栏」型候选（考察装护栏是否减少长题空转/超时假阴性，outcome = 内层超时题数 + resolved；须避开 sympy-16597 类 1226s 长题或先算自然步数余量）。

### 11.8 通过者的 20 题深测设计（**本循环未执行**，此处只出设计 + 可复算题集）

> 准入提醒：本循环唯一 survivor 是 **B2**；但终审判定 `rejected`（口径执行缺口），**B2 未销账前不得开跑**。以下设计以 B2 为对象，另按 M1/G1 谱系给出 m3fail 锚补题设计（§11.8-A）。

#### A. m3fail 锚按域补题（G1 谱系）— **结论：在本任务池上不可行**

**本记账员亲跑的判据位表**（as-of 07:07:53 快照，官方 m3 last-row 24 败逐题；`Y`=过该判据，`n`=不过，`env=YES`=另命中环境阻断正则）：

| 题 | 批次 | ①②③④⑤ | env | f2p_failure |
|---|---|---|---|---|
| astropy-13236 | d1 | YYYYY | – | 2 |
| astropy-13398 | d3 | YYYYY | – | 4 |
| django-10097 | d3 | YYYYY | **YES** | 7 |
| django-10973 | d2 | YYYYY | – | 1 |
| django-10999 | d1 | YYYYY | – | 2 |
| django-11087 | d1 | YYY**n** | – | 1 |
| django-11400 | d2 | YYYYY | – | 2 |
| django-14011 | d3 | YYYYY | – | 17 |
| django-14315 | d3 | YYYYY | – | 2 |
| django-15629 | d3 | YYYYY | – | 1 |
| psf-requests-2317 | d2 | Y**n**YYY | – | 0 |
| psf-requests-2931 | d1 | Y**n**YYY | – | 0 |
| xarray-2905 | d1 | YYYYY | – | 1 |
| xarray-3993 | d2 | YYYYY | **YES** | 2 |
| xarray-4687 | d1 | Y**n**YYY | – | **judge.json 0 字节** |
| pylint-4604 | d3 | YYY**n**Y | **YES** | 21 |
| pylint-4661 | d2 | YYY**n**Y | **YES** | 1 |
| pytest-10356 | d1 | YYYYY | **YES** | 1 |
| pytest-7205 | d2 | YYYYY | – | 9 |
| sphinx-10435 | d1 | YYYYY | – | 1 |
| sphinx-11510 | d1 | YYYYY | – | 2 |
| sphinx-8548 | d2 | YYYYY | – | 1 |
| sympy-16597 | d3 | YYYYY | – | 3 |
| sympy-17318 | d2 | YYYYY | – | 1 |

→ **五判据全过 = 18 题**（复现红队 32367 i1）；**加环境剔除判据⑥ = 13 题**；候选自写的 17 = 18 − 10097。

**补题设计的硬结论**：官方 m3 臂**败题总数只有 24**，五判据域最多 **18 < 20**。即使放宽到全部 24 败，仍 < 20 且 6 题落在域外（11087 ⑤不命中、2317/2931 f2p=0、4687 判分工件损坏、4604/4661 判据④）。**→ m3fail 锚的「单域 20 题深测」在当前 120 题任务池上不可行**，只有三条出路：①扩任务池（§6.0-B，工程量最大，运营者定）；②放宽判据（但放宽 = 过纳入口，红队 i2 已点名判据⑤ `deliberately` 过宽）；③**按 §6.3 缩到 13 或 18 题并如实写明 n**（局部门槛与 McNemar 换算须按实际 n 重算，不得套用 20 题的「净 ≥ 6」）。**另**：即使题集凑齐，M1 谱系在 m3 锚上**当前是死路**（§11.4(1) 的 CLI 一票拒绝），补题设计在换通道前无法执行。

#### B. behavior 锚双报口径 + 20 题题集（**本记账员亲算，可直接用**）

**域规模实测（记账员本轮全量复算，已落盘）**：`ssh anolis` 遍历 `~/.minimax/v2/sessions/2026/10/21/` 下官方 m3 run 的 session，逐个 `python3 /tmp/behave_count.py <session_dir>`，输出 JSON 落 `/tmp/recompute_behave_official_m3.json`（本机与 anolis 各一份）。
→ **SCANNED 119（= 官方 m3 的 119 个 completed 题）；`reread_paths≥1` 命中 85 题**；其中 **官方 m3 败 22 题 / 过 63 题 / 非判分 0**。

**速筛 5 题的双报明细（复算表，此格式即下一轮强制格式）**

| 题 | 官方 reread/max/consec | 改造 reread/max/consec | 通过率 官→改 | 备注 |
|---|---|---|---|---|
| django-10999 | 1 / 2 / 1 | **0 / 0 / 0** | F→F | 数据点来自冒烟 run（§11.4 披露） |
| django-15629 | 1 / 7 / 1 | 1 / 2 / 0 | F→F | |
| sphinx-8548 | 1 / 9 / 3 | **3 / 13 / 2** | F→F | 行为三倍化 |
| sympy-16597 | 1 / 2 / 1 | 1 / 2 / 1 | **F→T** | 唯一翻面；**行为无改善** |
| astropy-13398 | 1 / 2 / 1 | **0 / 0 / 0** | F→F | |
| **合计** | 5 / 22 / 7 | 5 / 17 / 3 | **0/5 → 1/5** | |

**净分题集（域内 m3 败 22 题 → 可用 19 题）**：剔除 `psf-requests-2317`、`psf-requests-2931`（`f2p_failure=0`，纯 P2P 回归，§10.5 死路登记）与 `xarray-4687`（`judge.json` 0 字节）后剩 **19 题**：

`astropy-13236, astropy-13398, django-10999, django-11087, django-11400, django-14011, django-14315, django-15629, xarray-2905, xarray-3993, pylint-4604, pylint-4661, pytest-10356, pytest-7205, sphinx-10435, sphinx-11510, sphinx-8548, sympy-16597, sympy-17318`

（19 题的官方 `reread / max_rereads / consecutive_dup_read_turns / asst_turns` 逐题值已在 `/tmp/recompute_behave_official_m3.json` 内，可直接用作题集基线表。）

**第 20 题的三个合法选项（须下一轮裁决，不 padding）**：①放行 `psf-requests-2317`（官方 f2p 8/0，翻面机制 = 修回归，与其它题「补对」不同类，须在结论中分列）；②从 63 道**域内过题**借 1 题作不退化对照槽（§6.2 规则⑤，单列不计净分，则净分题仍是 19）；③**缩到 19 题**并如实写明 n=19。**默认建议 ③**（§6.3 明文「宁可缩到 12 题也不 padding」）。

**不退化对照槽**：域内 63 道官方 m3 过题中抽 20（同 m3 档案，官方侧数字取同一 as-of 快照），**只作「改造臂不得把已过题弄坏」的对照，单列不计净分**。

**双报口径（下一轮强制，逐条对应终审整改 2、3）**

- **主判读**：`net = 改造过数 − 官方过数`（§6.2）。n=19 → 5.3pp/题；**统计线**按 McNemar 精确检验在 n=19 重算（discordant 全同向时 净 6 → p=0.031 仍成立）。
- **副判读（互不替代）**：①两侧 resolved 率并列；②行为**逐题明细**（`reread_paths` / `max_rereads` / `consecutive_dup_read_turns`）+ **两种聚合读法并列**（求和 / 逐题在场 ≥1）；③`asst_turns`（收敛效率代理）单列。
- **护栏（缺一不可）**：判为「行为改善」必须同时满足 **(a)** 改造臂终稿非空且结构完整（空转 / 内层超时 / 无终稿题**单列，不计入行为改善**）；**(b)** 两侧 resolved 率不降；**(c)** 方向按预注册解释（`reread 降 ∧ resolved 不降` = 效率改善；`reread 降 ∧ resolved 降` = **早停风险**，单列）；**(d)** 因 `--prompt-mode coding` 改变终稿结构，**行为计数下降须抽样人工核对 ≥3 题**，确认是「不再重复读」而非「换措辞 / 换结构逃过计数器」。
- **禁止写法**：只报 `official_behavior=5 / modified_behavior=5` 这样的聚合标量；把 20pp/题写成「提升 X pp」。
- **净分口径警告（须写进结论）**：本旋钮在速筛中已显「唯一翻面题 sympy-16597 行为 1→1 无改善」→ 深测须显式检验「通过率增益是否由承诺行为介导」，若否，结论只能写「存在与 `--prompt-mode coding` 相关的非行为机制路径（待定位）」，**不得写成行为域被改善**。

#### C. m31f 回归抽查锚设计（终审整改 1，速筛/深测前必须实跑）

**为什么必须**：速筛 5 题在 m31f 官方臂 **4 过 1 败**（§11.4(3)，记账员亲算）——钦定模型 m31f 上这批题基本都会做，`--prompt-mode coding` 在 m31f 的**回归暴露面完全未测**，而这是偏离钦定 m31f 后最关键的一环。

**设计**

- **题集**：与深测同一集合（19 题净分题 + 对照槽），profile = **m31f**（`mcode-tune-driver.py` 的档案参数；`:74-75` 为 m3 → `minimax/MiniMax-M3` 的映射行，m31f 为 `minimax/MiniMax-M3.1-Flash`）。
- **配对**：改造臂 `b2-prompt-mode-coding@m31f` vs **同题 base 变体臂** `@m31f`（**不能用官方臂数字当对照**：官方臂含已知自污染 `prompt.txt`/`mcode.log` 进 patch.diff，node 32289 i2；且机制件红队已实测同题两侧不一致的采样噪声）。两侧均 n=1 时结论只能写方向。
- **判据（三条同时满足才算通过）**：①**resolved 不跌**：`net_m31f ≥ 0`；②**行为不恶化**：Σ`reread_paths` 与 Σ`max_rereads` 相对同题 base 对照臂不显著上升（阈值须预注册，建议「求和读法涨幅 ≤ 25%」，因行为噪声实测 56–105%，±1 不可归）；③**终稿非空**：无终稿 / 内层 25m 超时 / `rc=7` 截断题单列，**不计入「通过」**（`rc=7` ↔ `limit_exceeded` 已 1:1 实证）。
- **官方侧数字**：从**同一 as-of 快照**取 m31f last-row（当前终局：221 行 / 120 唯一 / 119 判 / 114 过 / 5 败）。
- **成本预警**：m31f 臂单题 wall 中位约 453.7s（探针三题 453697 / 456883 / 460889ms），19 题 + 20 对照槽 × 2 臂 ≈ 78 次解题，按并发 2 计约 **5 小时**；开跑前先算容器配额（本工作流各臂 ≤2，§6.3(e)）。
- **若回归抽查判不通过**：B2 的深测**不得开跑**（`--prompt-mode coding` 在钦定模型上弄坏已过题 → 违反 §6.2 规则⑤ 的不退化要求）。

### 11.9 写回 §7 的口径新增条目（下一轮直接照抄）

11. **官方臂已终局**：§7.3 的「在飞 pid 3711801」作废；引用一律用终局账本 + as-of（m31f 119 判 / 114 过 / 5 败，m3 119 判 / 95 过 / 24 败，快照 as-of 2026-10-22 07:07:53）。
12. **effort 类旋钮 × m3 锚 = 硬禁止**：`minimax/MiniMax-M3 does not support reasoning effort selection` 是 CLI 一票拒绝（发生在任何 LLM 调用前，连 `llm-call.json` 都不生成）；探针的 `thinkingLevel=high` 证据**只在 m31f 路由成立**，不得外推。
13. **判分包装层版本**：引用 `judge.json` 的 `p2p_*` / `tests_collected` / `swebench_version` 字段时须核对 `tools/swev-judge.py` mtime（当前 2026-10-22 02:28:59）——该版本只增量上报四字段，resolved 计算路径未动；但**官方侧 judge.json 无新字段、改造臂有**，比对时须声明。
14. **行为计数必须先落盘再解读**：`behave_count.py`（sha256 `e667c13e…`）依赖 anolis `~/.minimax/v2/sessions/` 的易失 session；任何行为结论开跑前先把逐题 JSON + as-of 落盘（官方 m3 全量基线已落 `/tmp/recompute_behave_official_m3.json`）。
15. **行为量必须双读法并列**：求和 vs 逐题在场，二者结论可不同（速筛即出现 5←5 与 5→3 之差）；只报聚合标量 = 违反终审整改 2。
16. **探针计数须声明方法**：work 路径 grep 是「含路径的行数」不是出现次数（§11.2 探针红队 i2）。
17. **`--prompt-mode coding` 会改变终稿结构** → 一切基于终稿正则的行为计数（含 §10.3 冻结的 PASS_CLAIM、B2 的 reread 派生指标）在该旋钮下**对表面形式敏感**，下降须人工抽样核对。
18. **快照 as-of 模板文案已过期**：`as-of.txt` 仍写「官方臂在飞」，而 07:07:53 时官方臂已于 05:33:26 退出；下一版快照器应改文案为终局口径。
19. **回归抽查是准入门**：m3fail 锚候选（偏离钦定 m31f）若未实跑 m31f 回归抽查，**其速筛/深测结论一律不予采信**（终审 issue 1）。
20. **引用 judge.json 前先 `wc -c`**（§10.5 已有；本轮 xarray-4687 0 字节实例再次生效——它在 G1 判据②上因 `f2p_failure=None` 被正确排除）。

### 11.10 第二循环整改销账（改造实施员，执行时点 **2026-10-22 08:26 CST**）

> 对应 §11.5 末四条整改（终审 node 32422，issue 1–4），**逐条标注 issue 号**。本轮只做**文档面**销账；整改①（m31f 回归抽查）的**执行面在后续 phase**。凡数字均为本轮亲跑复算，命令与 as-of 见各条及 E。

#### 0. 销账总览

| 整改 | 终审 issue | 销账动作 | 落点 | 状态 |
|---|---|---|---|---|
| ① m31f 回归抽查 | issue 1 | §A 显式登记为**本循环待执行准入项** | 本节 A、§11.7 动作 3 | 文档面已销；**执行面未做（0 跑）** |
| ② 行为指标双读法 | issue 2 | §B 定义表 + 逐题明细 + 求和/在场两种读法并列（亲跑复算）；§11.4(2) 加禁裸标量指针 | 本节 B、§11.4(2) | 已销 |
| ③ survivor caveats | issue 3 | §11.3 B2 条目尾部追加 **Survivor caveats** 块（4 条） | §11.3、本节 C | 已销 |
| ④ --effort×m3 硬约束 | issue 4 | §2 旋钮表行 2 补注 + §7 新增条 11 | §2 行 2、§7-11 | 已销 |

#### A. 整改①（终审 issue 1）：「m31f 回归抽查」= 本循环**待执行准入项**（显式登记）

- **状态：未执行（0 跑）**。销账时点再次核验：`ssh anolis 'ls /data/bench/mcode-tune/runs/'`（08:2x）→ 仍为 7 个变体目录（b2-prompt-mode-coding / base / effort-high / m1-effort-high / max-steps-120 / max-steps-15 / prompt-mode-coding），**逐目录 0 项**（跑后清理口径同 §11.4(3)）；`/tmp/mcode-tune-implementer/out/` 8 个 arm-profile 目录（08:21 亲读）无任何 regress / m31f 速筛产物。
- **准入门效力（§11.9-19，即终审 issue 1 的要求）**：m3fail 锚候选（含唯一 survivor B2）**未实跑 m31f 回归抽查前，其速筛/深测结论一律不予采信**；B2 深测开跑被本项阻塞（§11.7 动作 2 → 3 → 5 前置链）。
- 执行设计：§11.8-C（题集 = 19 净分题 + 对照槽、profile=m31f、对照臂 = 同题 base 变体臂而非官方臂、三条判据：resolved 不跌 / 行为不恶化 / 终稿非空）；产出落点 `/tmp/mcode-tune-B2 重复读同一文件（轨迹级行为域）/regress-m31f/`；执行角色 = 改造实施员 + 速筛执行员（§11.7 动作 3）。

#### B. 整改②（终审 issue 2）：behavior 指标 = 定义 + 逐题明细 + 求和/在场两种读法并列

**指标定义**（出处：冻结计数器本机副本 `/tmp/mcode-tune-candidates/behave_count.py`，`sha256sum` = `e667c13e983cbbd88d6b2234d26e6a177971a5d0e77c5b547c8402aa7a1028ec`；anolis `/tmp/behave_count.py` 同指纹 08:1x 亲验，与 §11.1 声明一致；行号为本机副本实读）：

| 字段 | 定义 | 计数器出处 |
|---|---|---|
| `reread_paths` | 经 read/view 工具读取 **>1 次**的**不同路径数**（重复读路径的个数，不是重复次数） | behave_count.py:11（docstring）、:69-72（`len(rep)`，`rep=[v for k,v in reads.items() if v>1]`） |
| `max_rereads` | 单一路径被读次数的最大值；无重复读时 = 0 | behave_count.py:12、:73（`max(rep) if rep else 0`） |
| `consecutive_dup_read_turns` | 连续「该轮全部工具调用都是 read 且均在读已读过的路径」的最长轮数 | behave_count.py:15、:64-68 |
| `asst_turns` | assistant 消息数（收敛效率代理，按 §11.8-B 副判读③单列，**不入行为判定**） | behave_count.py:6、:70 |

**逐题明细（B2 速筛 5 题；本记账员 08:1x 亲跑复算）**
命令：`ssh anolis 'cd ~/.minimax/v2/sessions/2026/10/21 && python3 /tmp/behave_count.py <session_dir>'`。session 归属按 `messages.jsonl` 内 work 路径 grep 判定（官方臂 pattern `mcode-swev/runs/<tid>-m3/`、改造臂 pattern `mcode-tune/runs/b2-prompt-mode-coding/<tid>-m3/`，两臂各恰命中 1 session，无误配）；官方侧数值另对照 `/tmp/recompute_behave_official_m3.json` 记录值**逐位一致**。

| 题 | 官方 reread/max/consec/asst | 改造 reread/max/consec/asst | 通过率 官→改 | 行为判定 |
|---|---|---|---|---|
| django-10999 | 1 / 2 / 1 / 30 | **0 / 0 / 0 / 13** | F→F | 行为消失（改造数据点来自 06:57 冒烟 run，§11.4(2)） |
| django-15629 | 1 / 7 / 1 / 47 | 1 / 2 / 0 / 20 | F→F | 单径重复深度下降 |
| sphinx-8548 | 1 / 9 / 3 / 65 | **3 / 13 / 2 / 69** | F→F | **行为三倍化** |
| sympy-16597 | 1 / 2 / 1 / 57 | **1 / 2 / 1 / 64** | **F→T** | **原样未动**（唯一翻面题） |
| astropy-13398 | 1 / 2 / 1 / 65 | **0 / 0 / 0 / 39** | F→F | 行为消失 |
| **合计** | 5 / 22 / 7 / 264 | 5 / 17 / 3 / 205 | **0/5 → 1/5** | 2 改善 / 1 恶化 / 2 持平 |

**两种聚合读法并列（终审 issue 2 的核心要求；禁裸标量）**

| 读法 | 官方 | 改造 | 判读 |
|---|---|---|---|
| 求和 Σ `reread_paths` | 5 | 5 | 「行为持平 5←5」只在此读法成立 |
| 在场（`reread_paths≥1` 的题数，= B2 promised_domain 逐 session 定义） | 5 | **3** | 同一数据按域定义读法 = **5→3** |
| Σ `max_rereads` | 22 | 17 | |
| Σ `consecutive_dup_read_turns` | 7 | 3 | |

**写法纪律**：复算与红队独立结果互相印证（红队 `官方 [1,1,1,1,1] / 改造 [0,1,3,1,0]`，issue 2 原文）→ 逐题方向混合，任何只报聚合标量的写法都掩盖分裂；下一轮速筛/深测报告一律用本 B 表格式（定义 + 逐题 + 双读法），聚合值只能作为逐题表的合计行出现（§11.8-B 已立强制格式，本节补定义与禁裸标量依据，并回填 §11.4(2) 指针）。

#### C. 整改③（终审 issue 3）：survivor B2 结论 caveats（正文落 §11.3）

已作为 **Survivor caveats** 块直接写入 §11.3 B2 条目尾部（4 条：每臂每题 n=1 且含冒烟数据点 / 同参噪声同级 turns 58vs32・thinking +56%・toolResult +105% / 唯一净胜 sympy-16597 承诺行为未动 1→1 故通过率增益与承诺机制**无因果链** / 结论边界 + 回归抽查准入门绑定），此处只登记销账依据：
- caveats 第 3 条复算 = 本轮亲跑（§B 表：16597 改造 reread/max/consec = 1/2/1，与官方逐位相同）；
- 「m31f 官方臂本就可解」为本轮从**同一 07:07:53 快照**亲算：`sympy-16597 | reward=True | wall=700033`（m3 官方 wall=1225634ms，§11.4(2)），顺带核得其余 4 题 m31f last-row：15629/8548/13398 = True、10999 = False（即 §11.4(3) 的 4 过 1 败复现）；
- 终审指出的「survivor 零 caveats、与 probeFact 均带显式 caveats 的反差」由本块补齐。

#### D. 整改④（终审 issue 4）：`--effort` × MiniMax-M3 = CLI 硬拒绝，写回完成

- **§2 旋钮表行 2**（`--effort` 行）红队修正列补注：m3 路由 CLI 一票拒绝、m3fail 锚 effort 类禁用、探针 `takes_effect=true` 只在 m31f 路由成立（含 issue 4 标注）。
- **§7 口径清单新增条 11**：effort 类旋钮 × m3fail 锚 = 硬禁止 + M1 谱系重开的两条出路（config 级 thinking 档位另立候选 / 换锚回 m31f，即 §11.7 动作 6）；与 §11.9 条 12 同源，§11.9 批量并入 §7 时条 12 并入条 11、勿重复编号。
- **证据（本轮亲验）**：`cat /tmp/mcode-tune-implementer/out/m1-effort-high-m3/runs/pydata__xarray-3993/mcode.log`（08:2x）→ `mcode exec failed: minimax/MiniMax-M3 does not support reasoning effort selection, so --effort high cannot be applied.`（与 §11.4(1) 一致）；`out/m1-effort-high-m3/results.jsonl` 同题行 `reward=None / status=completed`（08:21 亲读）。

#### E. 销账复现命令

```bash
# ②③ 亲跑复算（10 session；先验冻结指纹）
ssh anolis 'sha256sum /tmp/behave_count.py'   # = e667c13e983c…（与 §11.1 一致）
ssh anolis 'cd ~/.minimax/v2/sessions/2026/10/21 && python3 /tmp/behave_count.py <session_dir>'
#   session 归属：grep -l -F "mcode-swev/runs/<tid>-m3/" */messages.jsonl      （官方臂）
#                grep -l -F "mcode-tune/runs/b2-prompt-mode-coding/" */messages.jsonl （改造臂）

# ① 登记项核验（仍零执行）
ssh anolis 'ls /data/bench/mcode-tune/runs/'  # 7 变体目录均空（08:2x）

# ④ 硬约束证据
cat /tmp/mcode-tune-implementer/out/m1-effort-high-m3/runs/pydata__xarray-3993/mcode.log

# ③ 引用的 m31f 侧数字（同一 07:07:53 快照 last-row）
python3 - <<'PY'
import json,collections
p='/tmp/mcode-tune-B2 重复读同一文件（轨迹级行为域）/official-snapshot-20261021T230753Z/bench-official-mcode-m31f/results.jsonl'
rows=[json.loads(l) for l in open(p) if l.strip()]
by=collections.defaultdict(list)
for x in rows: by[x['task_id']].append(x)
for t in ['sympy__sympy-16597']: print(t, by[t][-1]['reward'], by[t][-1]['agent_wall_ms'])
PY
```

#### F. 行为基线全量落盘（§11.7 动作 4；改造实施员，落盘时点 **2026-10-22 10:07 CST**）

- **产物目录 `/tmp/mcode-tune-B2-behavior-baseline/`**（4 件，`ls -la` + `sha256sum` 本机实跑）：
  - `reform-arm-behavior-baseline.json`（sha256 `017e2b70…`）——**改造臂全部 session 的 behave_count 逐题 JSON**：**20 条**（10-21 UTC 15 条 = 探针轮 9 + B2 冒烟/速筛 6；**10-22 UTC 5 条 = `b2-prompt-mode-coding @m31f` × 速筛同 5 题**，08:33–09:25 CST，系本账 08:08 写作时点之后后续 phase 的新跑，`out/b2-prompt-mode-coding-m31f/` 已在盘上——其 reward/status 仅作 last-row 关联参考，结论权在该 phase）。每条含 session_dir、messages.jsonl 的 size/mtime_utc/**sha256**、解析出的 work 路径（variant/task/profile，正则 `/data/bench/mcode-tune/runs/<variant>/<tid>-(m31f|m3)/`）、behave_count 输出对象、与本机 `out/<arm>/results.jsonl` last-row（§7.1 口径）的逐题关联。
  - `raw-from-anolis.json`（sha256 `f290db42…`）——anolis 原始提取件（含 behave_count_stdout/stderr 原文与 rc）。
  - `official-m3-full-baseline.json`（sha256 `e586b2cc…`）——`/tmp/recompute_behave_official_m3.json`（§11.8-B，119 records）**逐字节副本**（本轮回灌 `sha256sum` 双侧一致），使目录自包含；canonical 仍为原路径。
  - `as-of.txt`——generated_at 10:07:00 +0800 + 口径 + 上述三件 sha256。
- **口径**：anolis sessions 全树遍历（`2026/10/17…10/22` 六个日目录全查），凡 messages.jsonl 含 `/data/bench/mcode-tune/runs/`（改造臂命名空间）即收入，**不筛变体** → 覆盖 8 个 arm 目录；`m1-effort-high-m3` 臂 **0 session**（`--effort` 在 M3 路由被 CLI 于任何 LLM 调用前拒绝，§11.4(1)，无轨迹可计）。计数器冻结指纹双侧亲验一致（`e667c13e…`），anolis subprocess 亲跑 **20/20 rc=0**。
- **B2 深测可直接用的两侧基线**：官方 m3 119 题（official-m3-full-baseline.json）+ 改造臂 20 session（reform-arm-behavior-baseline.json）；其中 B2 速筛 5 题改造侧三元组与 §B 表**逐位一致**（10999=0/0/0、15629=1/2/0、8548=3/13/2、16597=1/2/1、13398=0/0/0），交互校验通过。
- **可复算性边界（如实登记）**：session 是易失资产（§11.6），本落盘以 messages.jsonl 的 sha256/mtime/size**钉指纹**；messages.jsonl **原件未归档**——session 被清理后，逐字节仲裁不可行，届时以本 JSON 的逐题计数为准（其生成过程有 raw 件与指纹链背书）。若需字节级仲裁，须在 session 清理前另行归档原始 messages.jsonl。

## 12. 第三循环·完整账（状态记账员，写入时点 **2026-10-22 13:2x CST**）

> 本节记录第三循环（run `dwfrun-1c3d5ebc-c038-43b4-8cac-117d79acd16a`，名 **研究组②调优组·第三循环**）的销账与重审、m31f 回归抽查、行为基线落盘、19 题深测、新候选起草与红队、三审，及其对下一循环的约束。**§12.7 是本记账员本轮亲跑复算**（命令与输出逐条在案）；§12.1–§12.6 的数字凡未标「记账员亲跑」者，取自对应节点的 result_json 与 /tmp 工件，两者一致处已在 §12.7 逐条点明。**本节不采信任何未复算的推论**；凡三审/红队提出的裁决项，本节只登记「待裁决」，不代替运行所有者下结论。

### 12.0 元信息与 as-of

| 项 | 值 | 取数 |
|---|---|---|
| run | `dwfrun-1c3d5ebc-c038-43b4-8cac-117d79acd16a` / `研究组②调优组·第三循环`，status=`running`（记账时未终），spent_tokens=104,798,507 | `~/.zcode/cli/db/db.sqlite` 表 `dwf_run`（`select id,name,status,spent_tokens from dwf_run where id like 'dwfrun-1c3d5ebc%'`），本轮只读打开（`mode=ro`） |
| 脚本 | 第三循环脚本全文 214 行，含 5 phase + 准入门分支 | `dwf_run.script_text`（10,023 字节），本节点导出后逐行实读 |
| 节点序（ask → actor → 模型 → 时段 CST） | 32439 改造实施员(GLM-5.3-Flash) 08:18:43→08:27:40 → 32446 红队·重审(step-5) 08:27:40→08:30:00 → 32451 速筛执行员(GLM) 08:30:00→09:52:48 → 32495 红队·候选审查(step-5) 09:52:48→10:01:01 → 32501 改造实施员 10:01:01→10:08:54 → 32513 速筛执行员 10:08:54→12:09:09 → 32627 红队·候选审查 12:09:09→12:15:52 → 32636 候选起草·GLM 12:15:52→12:43:42 → 32661 红队·候选审查 12:43:43→12:52:44 → 32674 红队·三审(step-5) 12:52:44→13:02:48 → **32690 状态记账员（本节点）** 13:02:48→ | `dwf_node` × `dwf_actor`（`left join` on `site_id`），time_created/time_updated 本地化 +0800 |
| report 节点 | 32445 / 32450 / 32512 / 32635 / 32673（5 个） | 同上 |
| 模型 | 工作者 `account:bigmodel-individual-coding-plan/GLM-5.3-Flash`；红队（三审/重审/候选审查）全部 `new-provider/step-5-preview`；记账 `minimax/Minimax-M3.1-Flash-Preview`。脚本侧声明档位：GLM_F `$max`、S5 `$high`、MM_F `$enabled` | `dwf_actor.resolved_model` + 脚本 L43-45 |
| 准入门实际触发 | 脚本 L129 `if (regress.ok && regressCheck.verdict !== "rejected")` → 32451 `ok=true` 且 32495 `confirmed` → **深测开跑**。门只判这两位，未判「门 scope 是否完整」（见 §12.6 issue 1） | 脚本 L129 实读 |
| 关键 as-of | 回归：官方 m31f 快照 `2026-10-22 08:31:58 +0800`，改造臂新跑 08:33–09:41，行为计数 09:49:20；深测：官方 m3 快照 `10:10:46`，改造臂新跑 10:11:31–11:57:12，官方行为计数 10:19、改造侧 12:0x，护栏(d) 12:1x | `/tmp/mcode-tune-B2-regress-m31f/{behavior-as-of.txt,official-snapshot-run/as-of.txt}`、`/tmp/mcode-tune-B2-deep-m3/{behavior-official-as-of.txt,deep-m3-results.json}` |

### 12.1 销账与重审结论

| 环节 | 节点 | 结论 | 要点 |
|---|---|---|---|
| 四条整改文档面销账 | 32439（改造实施员） | 完成 | §11.10 整改销账小节已落（687→790 行），逐条标注终审 issue 号；②的前置由该节点亲跑复算：冻结 `behave_count.py` 双侧 sha256 `e667c13e…`，官方 reread `[1,1,1,1,1]`、max `[2,7,9,2,2]`、consec `[1,1,3,1,1]`；改造 `[0,1,3,1,0]`、`[0,2,13,2,0]`、`[0,0,2,1,0]`，双读法 求和 5←5 / 在场 5→**3** |
| **重审门** | 32446（红队·重审，未参与修订的 step-5 新实例） | **`confirmed`，issues=[]** | 逐条亲跑：10 session 行为复算与 §11.10-B 表逐位一致；`ssh anolis 'ls /data/bench/mcode-tune/runs/'` 7 变体目录**逐目录 0 项**（①零执行的实证）；`cat out/m1-effort-high-m3/runs/pydata__xarray-3993/mcode.log` = `mcode exec failed: minimax/MiniMax-M3 does not support reasoning effort selection, so --effort high cannot be applied.`；caveat 四条数字从同一 07:07:53 快照亲算（16597=True wall=700033）。**门一次过，深测获准开跑** |

**时序纪律**：重审门 08:30:00 完成 → 回归抽查 08:30:00 才派发（`dwf_node.time_updated/time_created` 相等），重审结论先于其放行的跑批，符合脚本 phase 序。

### 12.2 B2 m31f 回归抽查（node 32451，红队复核 node 32495）——**准入门仅部分放电**

产物 `/tmp/mcode-tune-B2-regress-m31f/`（`regress-m31f-results.json`、`behavior-{official,modified}-m31f-raw.txt`、`behavior-as-of.txt`、`logs/regress-m31f-b2-083321.log`、`modified-runs/`、`official-snapshot-run/`）。题单 = B2 速筛 5 题；profile=m31f；改造臂 `b2-prompt-mode-coding@m31f` 新跑 5 题。

**逐题明细（resolved + 行为四元组，官方 ← 改造；行为 = reread_paths / max_rereads / consecutive_dup_read_turns / asst_turns）**

| 题 | 官方 resolved / wall(ms) | 官方 行为 | 改造 resolved / wall(ms) | 改造 行为 | 翻转 |
|---|---|---|---|---|---|
| django-10999 | False / 54,964 | 1/2/1/11 | **True** / 300,923 | 0/0/0/15 | **F→T** |
| django-15629 | True / 696,415 | 4/6/1/48 | True / 279,745 | 2/3/1/33 | T→T |
| sphinx-8548 | True / 651,673 | 2/15/3/60 | True / 1,090,791 | 3/11/1/100 | T→T |
| sympy-16597 | True / 700,033 | 0/0/0/81 | **False** / 1,331,326 | 0/0/0/92 | **T→F** |
| astropy-13398 | True / 1,049,849 | 0/0/0/85 | True / 915,163 | 2/3/1/69 | T→T |

**两种聚合读法并列（禁裸标量）**：Σ`reread_paths` **7 → 7**；Σ`max_rereads` **23 → 17**；Σ`consecutive_dup_read_turns` **5 → 3**；**在场（reread_paths≥1 的题数）3 → 3**，但**构成位移**：官方在场集 `{10999,15629,8548}` → 改造 `{15629,8548,13398}`（10999 行为消失 1→0；13398 行为新增 0→2；8548 reread_paths 升 2→3 而 max 15→11 / consec 3→1 降；15629 4→2 降）。按「逐题 0→1 即恶化」的更严口径，13398 构成**单题恶化信号**——两口径已并列，判读按 ask 指定的在场读法。
**判据**：ok = resolved 不跌（4→4）且 在场行为不恶化（3→3）→ **`ok=true`**；node 32451 payload 同时写明 n=5、net=0 只能写方向。

**红队结论 32495 = `confirmed`，6 issues（1 材料性读法依赖 + 1 scope 偏差 + 1 阻塞场景 + 1 噪声 + 1 文案 + 1 informational）**，本账采纳并转写为约束：
1. **【材料性】ok=true 只在登记读法下成立**，不得被下游消费为「无回归信号」（13398 行为 0→2、16597 T→F）。
2. **【scope 偏差】§11.8-C 设计的完整门未执行**：①配对 `base` 变体臂 **0 跑**——`out/base-m31f/results.jsonl` 仅 4 行（django-10999 / pylint-4604 / psf-requests-6028 / django-11532，全为 03:29–05:21 探针轮旧行，与本轮非同时配对）；②题集 **5/19 净分题**；③不退化对照槽 **0/20**。对照臂用的是官方 m31f 快照而非 base 变体臂（node 32289 i2 明确禁止）。
3. **【阻塞场景】sympy-16597 T→F 正是 §11.8-C 点名的「`--prompt-mode coding` 在钦定模型上弄坏已过题」**：官方 m31f 该题 judge `resolved=true f2p 3/0`，改造臂 `f2p 1/2` 败；判据①靠 10999 F→T 以 net=0 抵掉。
4. **【噪声】10999 F→T 与已知无旋钮分歧重合**（同题 `base@m31f` reward=True 而官方臂 False，§11.2 / node 32289 i2 在案）→ 不得读作旋钮增益。
5. 【minor】快照 `as-of.txt` 仍写「官方臂在飞」（§11.9-18 过期模板复发），**数据无损**：1208 条 per-file sha256、FAIL=0，快照与 live `results.jsonl` 逐字节相同。
6. 【informational】判分字段两臂不对称（官方 4 字段 / 改造 8 字段），`tools/swev-judge.py` 对 02:28 备份 diff 仅增量 4 字段、resolved 计算路径未动。

### 12.3 行为基线落盘（node 32501，终审整改①的资产项；§11.7 动作 4）

产物 `/tmp/mcode-tune-B2-behavior-baseline/`（10:07 CST，4 件）——本记账员 13:1x `sha256sum` **四件指纹与 `as-of.txt` 登记逐位一致**：

| 文件 | sha256（记账员亲跑） | 内容 |
|---|---|---|
| `reform-arm-behavior-baseline.json` | `017e2b705466fc0101598acb1c47ff30609e55f7be8a058b514afcddf14cf126` | 改造臂**全部 20 session** 的 behave_count 逐题 JSON（session_dir + messages.jsonl 的 size/mtime_utc/sha256 + work 路径 + 计数 + 与本机 `out/<arm>/results.jsonl` last-row 逐题关联） |
| `raw-from-anolis.json` | `f290db426d81d62c1ebb6c939d7765ce28e48bfb4d4b823f5f129300c060ed88` | anolis 原始提取件（stdout/stderr 原文 + rc） |
| `official-m3-full-baseline.json` | `e586b2cc5fc76abc214d6edf77c814b4384aee5b4854dbb4e9f5298c7307d073` | 官方 m3 全量 119 题基线的逐字节副本；**canonical** `/tmp/recompute_behave_official_m3.json` 本轮 `sha256sum` = **同值**（记账员亲验） |
| `as-of.txt` | — | generated_at 10:07:00 +0800 + 口径 + 上述三件 sha256 |

口径：anolis `~/.minimax/v2/sessions/` 全树，凡 messages.jsonl 含 `/data/bench/mcode-tune/runs/` 即收入、**不筛变体** → 覆盖 8 个 arm；`m1-effort-high-m3` **0 session**（`--effort` 在 M3 路由被 CLI 于任何 LLM 调用前拒绝）；冻结计数器双侧指纹一致，anolis subprocess 亲跑 **20/20 rc=0**。可复算性边界（§11.10-F 继续有效）：**messages.jsonl 原件未归档**，session 清理后逐字节仲裁不可行。

### 12.4 B2 19 题深测（node 32513，红队复核 node 32627）——**跑了，净 +9，但结论只到「值得全池验证」**

题集 = §11.8-B behavior 锚 **19 题净分集**（第 20 题三选项未经裁决 → 默认建议③缩到 19 并如实写明；**不退化对照槽 20 题未跑**，ask 题集未含）。profile=m3；对照 = 官方 m3 臂快照 10:10:46（`cp -a` 冻结，1208 sha256、FAIL=0）。产物 `/tmp/mcode-tune-B2-deep-m3/`：`deep-m3-results.json`、`deep-m3-detail.json`（逐题）、`behavior-{official,modified}-m3-raw.txt`、`recount.py`、`guardrail-d-recount.txt`、`logs/deep-m3-b2.log`。

**逐题明细（官方 ← 改造；行为三元组 reread/max/consec）**

| 题 | 官方 resolved/wall(ms) | 官方 reread/max/consec | 改造 resolved/wall(ms) | 改造 reread/max/consec | 翻面 | 改造侧数据出处 |
|---|---|---|---|---|---|---|
| astropy-13236 | False / 281,044 | 1/2/0 | **True** / 587,252 | 0/0/0 | F→T | deep-run 10:11–11:57 |
| astropy-13398 | False / 862,461 | 1/2/1 | False / 498,835 | 0/0/0 | — | 速筛行 07:0x |
| django-10999 | False / 361,147 | 1/2/1 | False / 59,767 | 0/0/0 | — | **06:57 冒烟 run**（§11.4(2) 披露） |
| django-11087 | False / 102,856 | 1/3/1 | False / 434,862 | 0/0/0 | — | deep-run |
| django-11400 | False / 127,636 | 1/4/1 | False / 505,008 | 2/2/0 | — | deep-run |
| django-14011 | False / 164,103 | 2/2/1 | **True** / 348,721 | 1/2/1 | F→T | deep-run |
| django-14315 | False / 55,575 | 1/2/0 | **True** / 199,142 | 0/0/0 | F→T | deep-run |
| django-15629 | False / 661,702 | 1/7/1 | False / 85,416 | 1/2/0 | — | 速筛行 07:0x |
| pydata-xarray-2905 | False / 333,690 | 1/2/0 | **True** / 515,067 | 1/4/1 | F→T | deep-run |
| pydata-xarray-3993 | False / 50,627 | 1/2/1 | False / 385,640 | 2/2/1 | — | deep-run |
| pylint-4604 | False / 351,313 | 1/5/1 | False / 429,391 | 1/3/1 | — | deep-run |
| pylint-4661 | False / 206,814 | 1/2/0 | **True** / 254,875 | 0/0/0 | F→T | deep-run |
| pytest-10356 | False / 560,781 | 3/2/2 | False / 789,562 | 0/0/0 | — | deep-run |
| pytest-7205 | False / 145,558 | 1/2/0 | **True** / 232,897 | 0/0/0 | F→T | deep-run |
| sphinx-10435 | False / 93,340 | 3/2/1 | False / 355,270 | 0/0/0 | — | deep-run |
| sphinx-11510 | False / 512,029 | 2/2/1 | **True** / 455,218 | 1/3/1 | F→T | deep-run |
| sphinx-8548 | False / 544,063 | 1/9/3 | False / 506,440 | 3/13/2 | — | 速筛行 07:0x（**唯一行为恶化题**） |
| sympy-16597 | False / 1,225,634 | 1/2/1 | **True** / 1,105,507 | 1/2/1 | F→T | 速筛行 07:0x（**行为 1→1 原样未动**） |
| sympy-17318 | False / 227,499 | 2/3/1 | **True** / 217,553 | 2/2/1 | F→T | deep-run |
| **合计** | **0/19 过** | Σ 26 / 57 / 17 | **9/19 过** | Σ 15 / 35 / 9 | **净 +9** | 14 新跑 + 5 复用 |

**两种聚合读法**：Σ`reread_paths` **26 → 15**；Σ`max_rereads` **57 → 35**；Σ`consecutive_dup_read_turns` **17 → 9**；**在场（≥1 题数）19 → 10**（题集 100% 落在 B2 承诺域）。
**统计与门槛换算**：discordant 全同向 9（official-pass-only=0），McNemar 精确双尾 p = 2×2⁻⁹ = **0.00390625**（<0.05 过）；≥3pp 换算：3pp×19 = 0.57 → **局部门槛净 ≥ 1**，实测净 9 过。**§6.3(c) 的正式采纳线（全池 120 题 m31f 复跑净 ≥ 4 = 3pp）未测**。
**机制拆分（§11.8-B 净分口径警告的强制项）**：9 翻面题中 **6 题行为改善**（13236/14011/14315/4661/7205/11510 reread 降）、**3 题行为未改善**（xarray-2905 1→1、16597 1→1、17318 2→2）→ 如实登记「**存在与 `--prompt-mode coding` 相关的非行为机制路径（待定位）**」；`regressed_tasks=[]`（官方 19 题全败，m3 臂上平凡为真，**不能替代 m31f 不退化验证**）；无零读逃逸题（9 翻面题改造侧 distinct_reads 全 ≥1）。
**护栏(d)**：独立重解析器（非 behave_count）抽 3 题双向核对 → 均为**真实少读**（10356 8→1 次读取 / 10435 8→2 / 10999 3→1）；bash/grep 通道两臂同量级，改造臂 read 仍被使用 1–2 次，计数器覆盖面无失效证据。

**红队结论 32627 = `confirmed`，6 issues**：①【结论边界·材料性】net=9/19 是 **47.4% 子集**读数，**不得读作「提升 47pp」或已达采纳线**（§6.3(c) 边界句执行员 payload 原文没有，由红队补做）；②【准入门状态被高估·材料性】`deep-m3-results.json` caveat 3 写「m31f 回归抽查准入门已过」**表述过强**，按 32495 口径应为「仅 5/19 子集部分放电」，须交运行所有者就 scope 与 16597 单题回归裁决；③【provenance·已披露】19 点中 5 点复用速筛/冒烟账本行（10999 为 06:57 冒烟），引用须保留「非深测正式槽位」标注；④【minor】护栏(d) 方法行引用的 `/tmp/recount-guardrail.py` **不存在**，实际脚本是 `/tmp/mcode-tune-B2-deep-m3/recount.py`（抽样数字无误，路径须更正）；⑤【minor】快照 `as-of.txt` 过期模板复发（数据无损：m3 results.jsonl 在 07:07:53 / 10:10:46 / live 三处 sha256 同为 `8aa08fec…`）；⑥【informational】判分字段两臂不对称。

### 12.5 新候选与红队结论（起草 node 32636，红队 node 32661 = `confirmed`）

| 候选 | 旋钮 / 换通道 | 锚 | 承诺域（定死） | 速筛 5 题 | 红队结论 |
|---|---|---|---|---|---|
| **M1B**「config 级 thinking 档位 high × G1 口径/推演域」 | **臂级 yaml + `--config`**（§2 旋钮 10/12/13），**不传 `--effort` 禁旗**；根因=MiniMax-M3 条目在 config.yaml 里**没有 `thinking.effortOptions` 块**（M3.1-Flash 条目有），即 §11.4(1) CLI 一票拒绝的键面根因；yaml 2 hunk（M3 补 effortOptions+defaultEffort: high；M3.1-Flash defaultEffort→high 供 m31f 臂） | m3fail | **G1 域判据 V4「紧⑤ + 显式环境剔除⑥」= 13 题**（`g1_recount_v3.py` + 位表 `g1_v3_bits.json`）：13236、13398、django-10973/10999/11400/14011/15629、xarray-2905、pytest-7205、sphinx-10435/11510、sympy-16597/17318 | 11400、17318、10435、10999、10973（全 ∈ 域，备用第 1 = 11510） | confirmed（可进冒烟前置阶段） |
| **MX**「--max-steps 120 失控护栏 × 失控型失败域」 | `--max-steps 120`（条件生效；`rc=7 ↔ limit_exceeded` 是本厂唯一 1:1 实证截断信号） | m3fail | **asst_turns≥40 ∩ m3 completed 失败 = 7 题**：13398(65)、8548(65)、16597(57)、15629(47)、11510(42)、13236(41)、4604(40) | 8548、13398、15629、11510、13236（16597 按 1226s 长题规则剔出速筛、保留域内；4604 备用） | confirmed |

两候选**均只起草未跑**（`variants/` 无 `m1b-config-thinking`、无 `max-steps-tiny`）。MX 最前置诚实披露：**不承诺通过率增益**——官方 m3 全池 119 判步数 median=26 / p90=45 / max=65，wall≥1000s 仅 3 题、≥1400s 为 0 → **N=120 恒不咬合**，价值主张是非退化保险实证 + rc=7 截断记账路径打通。

**红队 32661 = `confirmed`，5 issues（无否决，全部为执行前修订项）**：
1. **【材料性】G1 域的 n=13 可机械复现（V4=13，成员逐题一致），但与账本 §11.8-A 的「13」不是同一集合**——账本 18−5=13 的算术本身不成立（18 成员中命中环境阻断的只有 10097/3993/10356，按其自己的 18 与环境名单应得 15），且 V4 因紧⑤ 剔除了 **sphinx-8548 与 django-14315**（账本 18 含此二题）。**n 相同不等于成员相同**，引用时须写「V4-13 ≠ 账本-13」。
2. 【minor】M1B 冒烟判据⑥**锚点错位**：冒烟题是 django-11087（官方 wall=102,856ms），却引 `base-m3` 的 xarray-3993=175,040ms 作 10× 界（base-m3 账本无 11087 行），界过松。
3. 【minor】M1B 速筛双报三项**未明确要求逐题明细落盘**（禁裸标量纪律：聚合值只能作合计行）。
4. 【informational】两候选引用的「官方 m31f rc 集 {0×118,…}」**off-by-one**——从冻结快照按 last-row 重算 = `{0×117, 1, 4, 6}`；承重结论「全表无 rc=7」成立。
5. 【登记·非否决】两候选 m31f 准入门**均未跑**（base@m31f 现仅 4 个探针题，门需改造+base 各 5 run）；M1B 的档位穿透未证（冒烟一票前置，预注册死亡路径：②惰性=旋钮死 / ①被拒=M1 谱系终局），MX 的 **rc=7 → judge reward 记账路径未实测**（max-steps-15 探针为 no-judge 先例）。

### 12.6 三审意见（node 32674，红队·三审 step-5 新实例，未参与本循环任何环节，12:52:44–13:02:48）

**verdict = `confirmed`，5 issues。** 三审总判原文要点：四项指定审查项（**销账是否被重审门如实核过 / 回归与深测口径是否合规（逐题明细、两种读法、caveats、n 换算）/ 新候选是否带入历轮教训**）**全部通过，未发现编造**——所有抽复算数字与登记逐位一致；material issues 属**结论消费边界条件**，须落 §12 并交所有者裁决，不构成对记录真实性或口径格式合规性的否决。

| # | 等级 | 三审意见（转写） | 本账处置 |
|---|---|---|---|
| 1 | 材料性 | **准入门状态被高估，须限定消费**：「回归过」仅对 5 题子集、按 ask 指定在场读法（3→3）与官方快照对照成立；§11.8-C 完整门未执行（base 配对臂 0 跑、题集 5/19、对照槽 0/20）。**sympy-16597 在 m31f 上 T→F 正是 §11.8-C 点名的「弄坏已过题」阻塞场景**，仅被 10999 F→T 以 net=0 抵掉，而该翻面与 node 32289 i2 登记的无旋钮分歧重合（噪声疑似）。**§12 落账时不得把 B2 写成准入完整的 survivor** | 已按此写入 §12.2/§12.4/§12.9；**B2 状态 = 准入门部分放电，待裁决** |
| 2 | 材料性 | **结论边界**：深测 net=9/19 是 47.4% 子集读数，**不得读作「提升 47pp」或已达采纳线**；§6.3(c) 正式采纳线（全池 120 题 m31f 复跑净 ≥ 4 = 3pp）未测 | 已写入 §12.4 与 §12.9 动作 2 |
| 3 | minor·文档 | 护栏(d) 方法行引 `/tmp/recount-guardrail.py`（**不存在**），实际为 `/tmp/mcode-tune-B2-deep-m3/recount.py`；新快照 `as-of.txt` 仍写「官方臂在飞」（§11.9-18 复发，数据无损） | 转入 §12.9 动作 6（文档更正清单） |
| 4 | minor·候选 | M1B 冒烟判据⑥锚点错位；M1B 速筛双报未要求逐题明细落盘；两候选 m31f rc 集 off-by-one（118→117） | 与 32661 issue 2/3/4 同向，并入 §12.9 动作 4 |
| 5 | informational | 沿用披露：19 点中 5 点复用速筛/冒烟账本行；判分字段两臂不对称 | 保留标注，见 §12.4 表末列与 §12.8 |

三审对时序的独立确认：重审门（ask#2，actor#3 独立 step-5 实例，与执行修订的 actor#2 分离）**08:30:00 完成 → 回归 08:30:00 才派发**，时序正确。

### 12.7 记账员本轮亲跑复算（node 32690，13:0x–13:2x CST）

**声明**：以下全部由本节点在本次 ask 内实跑；凡与 §12.1–§12.6 登记值一致处，逐条点明「一致」。

| # | 检查 | 命令（摘要） | 结果 | 对账 |
|---|---|---|---|---|
| ① | run/节点元信息 | `sqlite3`（CLI 不可用，改用 `python3 sqlite3` 以 `file:…/db.sqlite?mode=ro` 只读打开）查 `dwf_run` / `dwf_node` / `dwf_actor` | run 1 行、ask 节点 11 行（32690 running）、report 5 行；角色与时段见 §12.0 | 与本节所引一致 |
| ② | **回归两侧 resolved 复算** | `python3` 对 `official-snapshot-run/bench-official-mcode-m31f/results.jsonl` 与 `modified-runs/results.jsonl` 取 last-row | 逐题 reward 与 wall **5/5 与登记逐位一致**（54964/696415/651673/700033/1049849 ← 300923/279745/1090791/1331326/915163）；**official 4 → modified 4，net=0**；官方全量 unique=120 judged=119 pass=114 fail=5，失败题 = {10097,10999,2317,7205,10435} | **与 §12.2 表一致**；官方 m3 全量（同一复算脚本）unique=120 judged=119 pass=95 fail=24，与 §11.0 终局账一致 |
| ③ | `modified-runs` 与本机臂账本一致性 | 同脚本比 `modified-runs/results.jsonl` vs `/tmp/mcode-tune-implementer/out/b2-prompt-mode-coding-m31f/results.jsonl` | 5 题 reward + wall **全部一致** | 一致 |
| ④ | **回归行为逐题复算（官方侧，5 题）** | `ssh anolis` python3：按 `mcode-swev/runs/<tid>-m31f/` grep 定位 session（各恰 1）→ 跑冻结 `behave_count.py`（`sha256sum` 双侧 = `e667c13e…`，本轮复验） | 10999 1/2/1/11、15629 4/6/1/48、8548 2/15/3/60、16597 0/0/0/81、13398 0/0/0/85；Σ 7/23/5，在场 3 | **与 §12.2 官方列逐位一致** |
| ⑤ | **回归行为逐题复算（改造侧，5 题）** | 同上，pattern `mcode-tune/runs/b2-prompt-mode-coding/<tid>-m31f/` | 10999 0/0/0/15、15629 2/3/1/33、8548 3/11/1/100、16597 0/0/0/92、13398 2/3/1/69；Σ **7/17/3**，在场 3 | **与 §12.2 改造列逐位一致** |
| ⑥ | **深测两侧逐题复算** | `python3` 对官方 m3 快照与 `out/b2-prompt-mode-coding-m3/results.jsonl` 取 last-row，逐题比对 `deep-m3-detail.json` 的 resolved / wall / 行为三元组 | **19 题 resolved + wall 与 detail 零处不符**；官方 0/19、改造 9/19、净 +9；Σreread 26→15、Σmax 57→35、Σconsec 17→9、在场 19→10 | **与 §12.4 表及合计逐位一致** |
| ⑦ | **深测改造侧行为独立重跑** | `ssh anolis` 对 19 个 work 路径各定位 1 session 后跑冻结计数器 | 19/19 与 `deep-m3-detail.json` 的 (reread,max,consec,asst) **逐位一致**；Σ=15/35/9、在场 10 | **一致** |
| ⑧ | 统计线与 n 换算 | `python3`：`2×2⁻⁹`；`0.03×19` | p=**0.00390625**；3pp×19=0.57 → 局部门槛净≥1，实测净 9 | 与 §12.4 一致 |
| ⑨ | **G1 域 V4=13 复跑** | `cd /tmp/mcode-tune-draft-glm-r3 && python3 g1_recount_v3.py` | V1 宽⑤=17 / V2 紧⑤=15 / V3 宽⑤+env=15 / **V4 紧⑤+env=13**；V4 成员 = 13236、13398、django-10973/10999/11400/14011/15629、xarray-2905、pytest-7205、sphinx-10435/11510、sympy-16597/17318 | **与 §12.5 M1B 域名单逐题一致** |
| ⑩ | **MX 域 7 复算** | `python3` 读 canonical 基线 `/tmp/recompute_behave_official_m3.json`（119 records）取 `asst_turns`，与 m3 快照 last-row `reward=False ∧ status=completed` 求交 | asst_turns median=26 / p90=45 / max=65；m3 completed 失败 24 题；步数≥40 交集**恰 7 题**（13398 65、8548 65、16597 57、15629 47、11510 42、13236 41、4604 40）；screen 5 题全 ∈ 域；wall≥1000s 恰 3 题（25102/13091/16597）、≥1400s **0 题** | **与 §12.5 MX 域表、screen 题、余量与「恒不咬合」算术逐位一致** |
| ⑪ | 行为基线四件指纹 | `sha256sum /tmp/mcode-tune-B2-behavior-baseline/*`；`sha256sum /tmp/recompute_behave_official_m3.json` | 四件 sha256 与 `as-of.txt` 登记**逐位一致**；canonical 官方基线 = `e586b2cc…` = 目录内副本 | **一致** |
| ⑫ | 红队 minor 取证 | `ls /tmp/recount-guardrail.py`；`python3` 读 `out/base-m31f/results.jsonl`；`wc -l` 两条 B2 臂账本 | `/tmp/recount-guardrail.py` **不存在**；`recount.py` 存在（1,036 B）；`base-m31f` **仅 4 行**（10999/4604/6028/11532）；`b2-…-m3` **19 行**、`b2-…-m31f` **5 行** | **证实 32495 issue 2、32627 issue 4、三审 issue 3/4** |
| ⑬ | 脚本实读 | `dwf_run.script_text` 导出后逐行读 | 准入门分支 = L129 `regress.ok && regressCheck.verdict !== "rejected"`；三审节点为新 step-5 实例；ask#15 = 本节写作指令原文 | 一致 |

**记账员对 scope 争议的独立判定**（不代替裁决）：三审与 32495 在「准入门是否放行深测」上并无事实分歧——脚本的门只判 `ok` 与 `verdict`，而两者皆真；**争议点是门本身的覆盖面小于 §11.8-C 设计**（base 配对臂 0 跑、题集 5/19、对照槽 0/20）。按 §11.9-19「未实跑 m31f 回归抽查则结论不予采信」的字面，本跑**满足字面**；按 §11.8-C 的设计意图，**只部分放电**。两种读法并存，本账按「部分放电 + 待裁决」登记，不做单方认定。

### 12.8 本循环未跑 / 未复核 / 本节点未独立复算（如实登记）

1. **不退化对照槽 20 题**：未跑（ask 题集未含，§11.8-B 三选项未裁决）。
2. **§11.8-C 完整回归门**：base 变体臂配对 0 跑；剩余 **14 净分题 + 20 对照槽 + base 配对臂**全部敞开。
3. **§6.3(c) 正式采纳线**（全池 120 题 m31f 复跑净 ≥ 4 = 3pp）：未测；**全池复跑需运营者批题池/窗口**。
4. **非行为机制路径定位**（xarray-2905 / sympy-16597 / sympy-17318 三条非行为路径）：只登记，未定位。
5. **M1B 与 MX**：仅起草，**冒烟 / m31f 门 / 速筛全部 0 跑**；M1B 的 thinking 档位穿透未证（config 通道对 M3 请求层是否生效未知）；MX 的 **rc=7 → judge reward 记账路径未实测**。
6. **19 点中 5 点非深测正式槽位**（10999 = 06:57 冒烟；13398/15629/8548/16597 = 07:0x 速筛行）：已逐题标注，但计入深测集合本身是一项披露而非验证。
7. **本节点未独立复算的项**：①19 题**官方侧**行为三元组本轮未在 anolis 重跑（沿用 canonical 基线 + detail 登记 + 红队/三审两方独立复算；官方 m3 19 题的基线记录与记账员 08:09 落盘件逐位一致系**引自**红队 32627 的复算，非本节点亲跑）；②`messages.jsonl` **原件未归档**，本轮 ④⑤⑦ 的复算依赖 session 尚存（§11.10-F 边界）；③MX 机制代码位 `chunk-WROGTDVD.js` 与 `mcode-tune-driver.py:625` 本节点未亲读（引自红队 32661）；④`as-of.txt` 1208 条 sha256/FAIL=0 本节点未逐条核（红队 32495/32627 已核并报）。
8. **本节未做的事**：未改任何产物与 /tmp 工件，未跑任何变体、冒烟或速筛，未动在飞进程与生产面，未对「scope 与 16597 单题回归」下裁决结论。

### 12.9 下一循环动作（可直接派工）

**A. 阻塞项（须先由运行所有者/厂长裁决，否则下一循环仍带着未结账的 B2 结论开跑）**

| # | 事项 | 依据 |
|---|---|---|
| A1 | **B2 m31f 门的 scope 裁决**：以 5 题子集结案，还是补跑 base@m31f 配对臂 + 剩余 14 净分题 + 20 不退化对照槽。同时裁决 **sympy-16597 单题 T→F** 是否构成阻塞 | 三审 issue 1、32495 issue 2/3、32627 issue 2、§11.8-C、§11.9-19 |
| A2 | **B2 是否升级为「全池复跑」**（正式采纳线：120 题 m31f、净 ≥ 4 = 3pp）；若跑，需运营者批题池与窗口 | §6.3(c)、三审 issue 2 |
| A3 | **扩题池（第二循环 §6.0-B）** 仍留运营者裁决（不扩池则 m31f 锚回方案已由 32636 亲算关闭：可翻净分池 ≤2，无统计线） | §11.7-6(b)、32636 候选设计段 |

**B. 可立即做（不需裁决）**

| # | 事项 | 落点 / 判据 |
|---|---|---|
| B1 | **M1B 冒烟（一票前置）**：m3 通道 django-11087（域外，官方 wall=102,856ms）+ m31f 通道穿透冒烟。**先修红队 issue 2**：判据⑥改锚 11087 自身官方 wall（<10×102.9s=1029s）或先补 `base@m3` 11087 对照跑 | 产物 `/tmp/mcode-tune-M1B-config-thinking/`；预注册死亡路径：②惰性=旋钮死 / ①被拒=M1 谱系终局；A2 形态回退**仅一次** |
| B2 | **MX 前置冒烟**：①m3 通道穿透（11087）；②**rc=7 → judge 记账路径验证**（tiny-N 变体 N=10 带 judge，判据：patch.diff 落盘 + judge 产 reward 行 + driver 记 status=completed） | 未过则不送速筛（候选自陈价值主张非通过率） |
| B3 | **两候选的 m31f 准入门**（若 A1 裁决为「继续」）：改造臂 + **base 变体臂@m31f** 同 5 题（**禁用官方臂当对照**，node 32289 i2）；base 臂须重跑，不得复用 4 条探针旧行 | 三判据：resolved 不跌（net≥0）/ 行为不恶化（wall+asst_turns 求和涨幅 ≤25%，阈值预注册）/ 终稿非空（rc=7 截断与内层超时单列） |
| B4 | **非行为机制路径定位**（3 题：xarray-2905 / sympy-16597 / sympy-17318）：先做产物级对照（终稿结构 / 工具面 / 判分链输入），产出「与 `--prompt-mode coding` 相关的非行为路径」假设与证伪条件 | 直接关系 B2 的采纳理由（承诺行为与通过率增益的因果链） |
| B5 | **全池采纳线若获批**：按 §6.2-6.3 执行，快照先行、双报（通过率 + 逐题行为两读法）、禁裸标量 | — |

**C. 文档更正清单（随下一次写作一并改）**

| # | 更正 | 落点 |
|---|---|---|
| C1 | 护栏(d) 方法行 `/tmp/recount-guardrail.py` → `/tmp/mcode-tune-B2-deep-m3/recount.py` | §12.4 护栏(d) 段 |
| C2 | 快照 `as-of.txt` 过期模板（「官方臂在飞」→ 终局口径）复发两次 | §11.9-18；下一版快照器改文案 |
| C3 | 「官方 m31f rc 集 {0×118,…}」off-by-one → `{0×117,1,4,6}`（承重结论「无 rc=7」不变） | §11.2 / §12.5 引用处 |
| C4 | 账本 §11.8-A 的「18−5=13」算术错误回账；**V4-13 ≠ 账本-13**（成员差 sphinx-8548、django-14315） | §11.8-A、§12.5 |
| C5 | §11.3 B2 条目「唯一 survivor」表述须加注：**准入门仅部分放电**（第三循环 A1 未结） | §11.3 |
| C6 | 归档 anolis `messages.jsonl` **原件**（不只是指纹），否则 session 清理后逐字节仲裁永久失效 | §11.10-F 边界 |

## 13. 第四循环·完整账（状态记账员，写入时点 **2026-10-23 03:0x CST**）

> 本节记录第四循环（run `dwfrun-26c949a2-df21-46af-a61d-69035842cf04`，名 **研究组②调优组·第四循环·提速版**）的候选回读、双候选并行冒烟、双路速筛、双路深测、B2 回灌 af 的只读评估、红队逐条复核与三审，并对下一循环给出动作与移交件。**§13.7 是本记账员本轮亲跑复算**（命令与输出逐条在案）；§13.1–§13.6 的数字凡未标「记账员亲跑」者，取自对应节点的 `result_json` 与盘上工件。**本节不采信任何未复算的推论**；凡三审/红队提出的裁决项，本节只登记「待裁决」，不代替运行所有者下结论。
> **口径提示**：§0「本轮官方臂读数」与 §1「一屏摘要」均为**第一循环**口径，已过时；第四循环的最新读数以本节为准。

### 13.0 元信息与 as-of

| 项 | 值 | 取数 |
|---|---|---|
| run | `dwfrun-26c949a2-df21-46af-a61d-69035842cf04` / `研究组②调优组·第四循环·提速版`，status=`running`（记账时未终），spent_tokens=185,897,362，script_hash=`f24b611efab2…`，caps_max_concurrency=14 | `~/.zcode/cli/db/db.sqlite` 表 `dwf_run`（本轮只读打开 `mode=ro`） |
| 前身 run | `dwfrun-dc7a836d-3268-4580-9a03-09b4f16e47ab` / `研究组②调优组·第四循环`，status=`cancelled`（2026-10-22 13:13:32→17:04:29，spent_tokens=108,851,459），其 `resumed_from`=第三循环 `dwfrun-1c3d5ebc…`；提速版 `resumed_from`=本前身 run | 同上 |
| 前身 run 状态 | 仅 3 节点：`ask#1` 候选起草 completed（13:13→13:16）、`ask#2` 改造实施**未终**（13:16 起，cancelled 时仍 running）、`artifact#1` | `dwf_node` |
| 脚本 | 第四循环提速版脚本全文 **218 行**，4 个 phase（新候选实施与冒烟 / 双候选速筛 / 深测 / 三审与落账） | `dwf_run.script_text` 本节点导出后逐行实读 |
| 提速修正（脚本自述） | ①双候选由 甲/乙 两实施员**并行**实施+冒烟 ②B2 af 回灌评估**提前**到第 1 phase、与实施并行（零 anolis 槽位）③速筛/深测按候选**并行**（甲/乙执行员），红队审查保持串行 ④mcode 跑批一律 nohup 后台化、等待期做零槽位独立件、深测题集必拆 ≥2 路 | 脚本 L4-9 |
| 节点序（ask → actor → 模型 → 时段 CST） | 32753 候选起草员(GLM) 17:04:29 → 32754 回灌评估员(MM) 17:04:30→17:31:47 → 32755 改造实施员**甲**(GLM) 17:04:30→17:45:17 → 32756 改造实施员**乙**(GLM) 17:04:30→18:58:35 → 32795 红队·候选审查(回灌复核,S5) 18:58:36→19:13:26 → 32799 速筛执行员**甲**(GLM) 19:13:26→23:53:34 → 32800 速筛执行员**乙**(GLM) 19:13:26→00:18:43 → 32870 红队(M1B 速筛审,S5) 00:18:43→00:28:10 → 32875 红队(MX 速筛审,S5) 00:28:11→00:33:38 → 32880 速筛执行员甲(深测,GLM) 00:33:38→02:33:40 → 32881 速筛执行员乙(深测,GLM) 00:33:38→00:59:18 → 32888 红队(M1B 深测审,S5) 02:33:40→02:41:32 → 32893 红队(MX 深测审,S5) 02:41:32→02:44:51 → 32898 红队·**三审**(S5) 02:44:51→03:02:35 → **32902 状态记账员（本节点）** 03:02:35→ | `dwf_node` × `dwf_actor`（`left join` on `site_id`），time_created/time_updated 本地化 +0800 |
| report 节点（6 个，进度表「调优组·第四循环进度」） | 32793(M1B 冒烟在飞) / 32794(MX 冒烟过) 18:58:36；32874(M1B 速筛通过) 00:28:11 / 32879(MX 速筛通过) 00:33:38；32892(M1B 确证候选) 02:41:32 / 32897(MX 确证候选) 02:44:51 | 同上 |
| 模型 | 候选起草员/改造实施员甲乙/速筛执行员甲乙 = `account:bigmodel-individual-coding-plan/GLM-5.3-Flash`（脚本 `GLM_F`=…`$max`）；回灌评估员/记账员 = `minimax/Minimax-M3.1-Flash-Preview`（`MM_F`=`$enabled`）；红队（回灌复核 + 4 次审查 + 三审）全部 `new-provider/step-5-preview`（`S5`=`$high`） | `dwf_actor.resolved_model` + 脚本 L44-46 |

### 13.1 候选来源（node 32753 候选起草员）

本轮**不起草新候选**，只回读第三循环已红队 `confirmed` 的 2 条（§12.5），并附 §12 出处行号：

| 候选 | 锚 / 承诺域（定死） | 速筛 5 题 | §12 出处 |
|---|---|---|---|
| **M1B**「config 级 thinking 档位 high × G1 口径/推演域」 | 锚=m3fail；承诺域=G1「紧⑤+显式环境剔除⑥」= **V4-13**（`g1_recount_v3.py` + 位表 `g1_v3_bits.json`） | 11400、17318、10435、10999、10973（备用 11510） | §12.5 表第 1 数据行（L897）；红队 32661 `confirmed` 5 issues（L902-903） |
| **MX**「--max-steps 120 失控护栏 × 失控型失败域」 | 锚=m3fail；承诺域=**asst_turns≥40 ∩ m3 completed 失败 = 7 题**（8548/13398/16597/15629/11510/13236/4604） | 8548、13398、15629、11510、13236（16597 按长题规则剔出速筛、保留域内） | §12.5 表第 2 数据行（L898）；最前置诚实披露（L900）：**不承诺通过率增益**，价值主张=非退化保险实证 + rc=7 记账路径 |

### 13.2 冒烟（甲 node 32755 / 乙 node 32756）— 变体单点差异 + 注入排除 + 补丁卫生三项必检

#### (1) M1B（`m1b-config-thinking`）

| 项 | 读数 | 出处 |
|---|---|---|
| 变体路径 | `/tmp/mcode-tune-implementer/variants/m1b-config-thinking` | node 32755 |
| 单点差异 | exec 行 `--model` 后插入 `--config "$HOME/mcode-tune-implementer/config-m1b-thinking.yaml"`；全文**无 `--effort`** 禁旗 | node 32755；**记账员亲跑 `diff`**（§13.7-③） |
| 臂级 yaml 差异 | 官方 `~/.minimax/config.yaml` 逐字 + **恰 2 hunk**：①MiniMax-M3 条目补 `thinking.effortOptions[default..max]`+`defaultEffort: high`（M3 原缺该块=§11.4(1) CLI 一票拒绝的键面根因）②M3.1-Flash `defaultEffort: default→high`（供 m31f 臂） | node 32755；**记账员亲跑 `diff`**（§13.7-④） |
| 注入排除 / 补丁卫生 | `knobs.json inject=[]`；`patch.diff` files=[`django/db/models/deletion.py`] 唯一源码文件；forbidden{prompt.txt,mcode.log}=0、`.meta/` 泄漏 0、`--effort` 0；patch sha256 `37b5c0a8…` 3043B | node 32755 |
| 冒烟 m3 通道 | django-11087：completed、reward=True、wall=371,595ms（<10×官方 102,856ms=1,028,560ms）；judge resolved=true f2p 1/0 p2p 41/0；`llm-call.json` `"MiniMax-M3"×1 ∧ "thinkingLevel":"high"×1`（档位穿透）；0 死亡路径触发 | node 32755 + `/tmp/mcode-tune-M1B-config/smoke-report.md` |
| 冒烟 m31f 通道 | **交付时仍在飞**：`smoke_ok=false`+`smoke_pending=true`，环日志 `/tmp/mcode-tune-implementer/logs/smoke-m1b-m31f-4604-loop.log`（pid 650975，有界 ≤20 轮，第 5 轮 17:39:36 fail-closed、第 6 轮 17:41:36 起；账本 7 行全 `preflight_failed`，非判分终态；阻断原因=anolis 他产线 mcode exec 3-4 >2） | node 32755 |
| m31f 终态（补证） | **17:58:52 到终态**：pylint-4604 `completed` / reward=False / wall=221,173ms（<界 4,568,830ms），无 CLI 拒绝死亡路径；账本共 8 行=completed×1 + preflight_failed×7 | **记账员亲查** `/tmp/mcode-tune-implementer/out/m1b-config-thinking-m31f/results.jsonl`（§13.7-⑬）；三审 node 32898 同载 |
| 进度表行 | `candidate=**M1B**…／status=冒烟在飞／official=-／modified=-` | report node 32793 |

#### (2) MX（`mx-max-steps-120`）

| 项 | 读数 | 出处 |
|---|---|---|
| 变体路径 | `/tmp/mcode-tune-mx-b/variants/mx-max-steps-120`（B 路产物独立，零互踩） | node 32756 |
| 单点差异 | exec 行 `--model` 后插入 `--max-steps 120`（恰 1 行） | node 32756；**记账员亲跑 `diff`**（§13.7-③） |
| 注入排除 / 补丁卫生 | 两 `knobs.json inject=[]`；3 份 patch 的 forbidden 前缀命中 0（11087→仅 deletion.py、10999→仅 dateparse.py、3993→仅 dataarray/dataset.py） | node 32756 |
| 冒烟①（m3 穿透） | django-11087：rc=0、completed、reward=True、wall=290,624ms、judge f2p 1/0 p2p 41/0；`llm-call.json` model=MiniMax-M3、thinkingLevel=medium（对照 M1 effort 拒绝时**无** llm-call.json）→ `--max-steps` 在 m3 路由无 CLI 一票拒绝 | node 32756 |
| 冒烟②（rc=7 记账路径，§12.9-B2②） | tiny-N 变体 `mx-max-steps-10` × xarray-3993：`mcode.log` 恰 1 行 `mcode exec limit_exceeded: The run reached its step limit…`、`patch.diff` 落盘 3,692B、judge 产 reward 行（resolved=false f2p 0/2 p2p 2398/0）、driver 记 status=completed；**反面对照** 13398 同为 rc=7 但零改动 → 空 patch → reward=None「no model patch produced」不丢行 | node 32756；**记账员亲验本地工件**（§13.7-⑫） |
| 进度表行 | `candidate=**MX**…／status=冒烟过／official=-／modified=-` | report node 32794 |

### 13.3 速筛（甲 node 32799 / 乙 node 32800，红队 32870 / 32875）

| 候选 | 快照（官方侧，cp -a 先于起批） | 官方侧 | 改造侧 | 结果路径 | 红队 |
|---|---|---|---|---|---|
| **M1B** | `/tmp/mcode-tune-M1B-config/official-snapshot-screen`，**as-of 2026-10-22 19:20:04 +0800**（`bench-official-mcode-m3/results.jsonl` sha256 `43d7b1a0…`） | **0/5**（11400、17318、10435、10999、10973 全 reward=False ∧ completed，m3fail 锚 5/5 成立） | **2/5**（翻面 17318、10973；**无 T→F**；5 题全 completed∧attempts=1∧rc=0） | `/tmp/mcode-tune-implementer/out/m1b-config-thinking-m3/results.jsonl`（sha256 `0d2e087e…`）；报告 `/tmp/mcode-tune-M1B-config/screen-report.md` | node 32870 `confirmed`，4 issues |
| **MX** | `/tmp/mcode-tune-mx-b/official-snapshot-screen-20261022T192136Z`，**as-of 2026-10-22 19:21:54 +0800**（`results-m3.jsonl` sha256 `43d7b1a0…`，227 rows/unique 120/pass 96/fail 24；终局口径文案） | **0/5**（8548、13398、15629、11510、13236 全 False ∧ completed） | **2/5**（翻面 11510、13236；**无 T→F**；5 题 rc 全 0） | `/tmp/mcode-tune-mx-b/mx-screen-results.json`（sha256 `19abc…`）+ 账本 `/tmp/mcode-tune-mx-b/out/mx-max-steps-120-m3/results.jsonl` | node 32875 `confirmed`，4 issues |

**行为双报（两读法并列，禁裸标量）**

| 候选 | 读法 | 官方 | 改造 | 备注 |
|---|---|---|---|---|
| M1B | Σ`reread_paths` | 7 | **3** | 逐题 11400 1→1、17318 2→1、10435 3→0、10999 1→1、10973 0→0 |
| M1B | 在场（reread≥1 题数） | 4 | **3** | 构成位移 {11400,17318,10435,10999}→{11400,17318,10999}（10435 行为消失），**无单题恶化** |
| M1B | Σ`max_rereads` / Σ`consec` / Σ`asst_turns` | 11 / 4 / 98 | 6 / 1 / 96 | 三审 node 32898 在 10 session 上独立重跑逐位一致 |
| MX | Σ`reread_paths` | 6 | **3** | 逐题 8548 1→1、13398 1→0、15629 1→0、11510 2→1、13236 1→1 |
| MX | 在场（reread≥1 题数） | 5 | **3** | **无单题恶化** |
| MX | Σ`max_rereads` / Σ`consec` / Σ`asst_turns` | 22 / 6 / 260 | **11** / 5 / 190 | ⚠ 文件聚合行写 `modified=13`，逐题求和为 11（**算术错**，见 §13.7-⑨、§13.9-C8） |

**速筛层 caveats（红队确认，非否决）**：①M1B 的 django-10973 翻面**两侧行为均 0/0/0**（官方 distinct_reads=2、改造=2）→ 翻面**不可能由 reread 行为介导**，与 B2 的 sympy-16597 同型「非行为机制路径」caveat（红队 32870 材料性 issue 2）；②MX 旋钮**全程未参与约束**（5 题改造侧 rc=0、asst_turns 17-74 全 <120、无 limit_exceeded；官方池 asst max=65、≥100 者 0 → N=120 恒不咬合）→ 2/5 翻面**不得归因** `--max-steps 120`，只作方向性读数（红队 32875 材料性 issue 2）；③两候选 n=5 → 20pp/题，McNemar 精确双尾 p=2×2⁻²=0.5 不显著；④两候选 **m31f 回归抽查准入门均未跑**；⑤**无旋钮对照缺失**（`base` m3 臂在册仅 1 行 xarray-3993，§13.7-⑮）。

**进度表**：32874 `M1B／速筛通过／0过／2过`；32879 `MX／速筛通过／0过／2过`。

### 13.4 深测（甲 node 32880 / 乙 node 32881，红队 32888 / 32893）

| 候选 | 题集 | 快照（官方侧） | 官方侧 | 改造侧 | 统计 | 结果路径 | 红队 |
|---|---|---|---|---|---|---|---|
| **M1B** | 20 = 官方 m3 24 败 − 4 排除；**双路不重叠**（A 路 8 + B 路 7）+ 5 题速筛行复用（`lane=screen-reuse`） | `/tmp/mcode-tune-M1B-config/official-snapshot-deep`，**as-of 2026-10-23 00:38:09 +0800**（`results.jsonl` sha256 `43d7b1a0…`） | **0/20**（20 题全 False ∧ completed） | **11/20** + 1 题 non-judged（13398，rc=70 无补丁，按 §7-2 单列），**净 +11，无 T→F** | discordant 11 全同向 → McNemar 精确双尾 p=2×2⁻¹¹=**0.0009765625**；3pp×20=0.6→局部门槛净≥1 过；§7-10「discordant 全同向净≥6」过 | `results_path`=`/tmp/mcode-tune-M1B-config/deep-m3-results.jsonl`（sha256 `1690650f…`）；`detail_path`=`/tmp/mcode-tune-M1B-config/deep-m3-detail.json`（sha256 `516dfef2…`） | node 32888 `confirmed`，6 issues |
| **MX** | **7 = 全域**（域内仅 7 题，按 §6.3/§7.9「宁缩勿凑」不 padding）；双路 lane1/b=16597 + lane2/b2=4604 + 5 题复用 | `/tmp/mcode-tune-mx-b/official-snapshot-deep-20261023T003821Z`，**as-of 2026-10-23 00:38:21 +0800**（`results-m3.jsonl` sha256 `43d7b1a0…`，与速筛快照逐字节一致） | **0/7** | **2/7**（11510、13236；**无 T→F**），净 +2 | discordant 2 全同向 → p=2×2⁻²=**0.5 不显著**；n=7 需净≥6 才 p<0.05；3pp×7=0.21→局部门槛净≥1 过 | `results_path`=`/tmp/mcode-tune-mx-b/mx-deep-results.json`（sha256 `b05969b2…`）；`detail_path`=`/tmp/mcode-tune-mx-b/mx-deep-detail.json`（sha256 `e888a7a2…`） | node 32893 `confirmed`，4 issues |

**行为双报（深测层）**

| 候选 | 口径 | 官方（Σreread/Σmax/Σconsec/Σasst；在场） | 改造（同） |
|---|---|---|---|
| M1B | 19 对已判配对 | 25 / 55 / 16 / 529；在场 18 | 18 / 40 / 8 / 505；在场 14 |
| M1B | 全 20 题 | 26 / 57 / 17 / 594；在场 19 | 18 / 40 / 8 / 586；在场 14 |
| MX | 全 7 题（逐题行重算，无口径混用） | 8 / 29 / 8 / 357；在场 7 | 5 / 19 / 7 / 274；在场 5；`rc7_truncations=0` |

> ⚠ M1B 深测报告 `deep-m3-report.md` §2 在「同口径（19 对已判配对）」标题下写 Σmax 57→40、Σconsec 17→8 —— 该两格**实为全 20 题口径值**（19 对应为 55/16）。记账员亲算复现（§13.7-⑧）；三审 node 32898 minor 1 同判。见 §13.9-C7。

**M1B 深测的域偏离（材料性，三审 issue 1，本账必须分账消费）**

- §12.5 把 M1B 承诺域**定死**为 G1 V4-13；§6.3(a) 明令「20 题必须全部落在该候选 promised_domain 内；域外题一律剔除，宁可缩到 12 题也不 padding」。
- 实际深测 20 题 = 24 败 − 4 排除，其中 **7 道「域缘」题**（11087/14315/8548/10356/4604/4661/3993）**经位表 `g1_v3_bits.json` 逐题复核均不在 V4-13**（执行员以「同锚同判据②③④、⑤域从紧放宽并逐题登记」重新框架化）。
- **记账员亲算分账（§13.7-⑦）**：**V4-13 净 +8**（13 题中 12 题已判、8 题通过；13398 non-judged）+ **域缘扩测净 +3**（11087、14315、3993 三题翻面）。
- **结论表述纪律**：不得笼统写「承诺域 20 题净 +11」；须写「V4-13 净 +8 ＋ 域缘扩测净 +3」。**域重定义是否接受 = 待运行所有者裁决**（§13.9-A1）。

**深测层 caveats**：①M1B 11 翻面中 **reread 改善仅 5、行为不变 5、反升 1（16597）** → **6/11 翻面非 reread 介导**，与 B2 同题的「非行为机制路径」caveat 同型且更强；②M1B 14315/7205/10973 改造侧 reread 三元组归 0（无重复读），行为指标对其只能记「无恶化」；③MX 旋钮恒不咬合 → **2/7 翻面不得归因**；④M1B 20 题中 5 题为速筛行复用（provenance 已逐题标注）；⑤两候选 **§6.3(c) 全池 120 题 m31f 采纳线（净≥4）均未测**，**m31f 回归抽查准入门均未跑** → 本节结论**不含 m31f 不退化证据，不得消费为「可回灌/已采纳」**。

**进度表**：32892 `M1B／确证候选／0/20／11/20`；32897 `MX／确证候选／0/7／2/7`。

### 13.5 B2 回灌 af 的只读评估（node 32754 评估员 + node 32795 红队复核）

**结论（红队 32795 `confirmed` 复核通过）**

| 字段 | 结论 |
|---|---|
| `af_equivalent` | **部分（partial）**——af 侧**有「装配层」对应物**（提示构造层 `ContextTemplate{system,slots}`），**无「旋钮」对应物**；且旋钮语义在 af 判分链下**基本惰性** |
| `port_shape` | 若真要移植，最小改动层=**af-bench 的提示构造层单文件**（`main.rs:543` 加第二份变体常量、`:738-741` 按变体注入、`:78-89` Args 加旗标），**af-harness 零改动**；但真正成本在「代号线 bump + 对照臂 + af 侧行为计数器新建」，不在代码 diff |
| `risks` | 机制未定位就跨 harness 搬运=搬噪声；B2 自身未结账（准入门仅部分放电、16597 T→F、采纳线未测）；跨档位可迁移性未测（+9 全在 m3，af 默认 m31f）；交付格式条款在 af 下惰性甚至有害；af 侧基线会被自身改动污染；治理与并发冲突（af 管辖权在①） |
| `recommendation` | **B2 不应被当成「可回灌 af 的旋钮」**；产物应是「不要这样搬」的判定 + 两条正确去向：①af 侧动作**只能由①对齐组以「af 原生候选」形式在①自己的变体周期里做**，②调优组只交出「语义差 + 惰性条款 + 计数口径」三件事实；**B2 结账前不得把任何 af 侧动作记为「回灌 B2 收益」** |

**机制语义要点（可复算事实）**

- mcode 侧 `--prompt-mode` 是**人格/系统提示资产选择开关**（choices tui/coding/work，default tui），装配链 `chunk-2XPMNZVR.js:4783/4785/4793`；资产 tui 9861B / coding 11969B / work 13535B。
- 实证「只换提示、不换工具/模型/档位」：coding vs tui 两个 session 的 `llm-call.json` 中 model/thinkingLevel/maxTokens/api/provider 全同，**tools 数组 JSON sha256 两侧同为 `1133800324e0e6…`（18 工具逐名同）**，唯一差异 = systemPrompt（coding 17219 字符/17327B vs tui 15655/15763B；账本 §11.2:447 记的「B」实为字符数，此处为字节数更正）。
- af 侧：af **全程不经 mcode**（`grep -rn "mcode exec" af/crates` 0 命中），af-bench 直连 mavis（`main.rs:165-195`）；装配链 `spec.rs:100` → `render.rs:10`（纯字面替换）→ `run.rs:462-464` → `endpoint.rs:291`；system 本体 = `SWEV_SYSTEM_PROMPT`（`main.rs:543`，**一行**），纪律进每题 instance 消息（`main.rs:548` / 拼装 `:775`）。
- **惰性是结构性的（代码证实）**：完成判定 = 工具输出首行等于信号词（`spec.rs:121-124` + `run.rs:942-954` `matched_signal`），判分只吃 `(task_json, eval.log, agent.diff)`（`swev.rs:102` / `:205-210`）→ 助手末条文本（=coding 交付格式条款的作用面）**不进判分**。

**红队 32795 的 5 条 issue（1 材料性）**

- **【材料性】评估的经验腿不可复现且被反例否证**：原文称「19 个 B2 臂 run 的 `mcode.log` 里 `deliver-assets`/`Media Output` 均 0 命中（17/19 命中 `## Verification`）」——`/tmp/mcode-tune-B2-deep-m3/` 已不在盘（`ssh anolis 'ls …'` → No such file or directory），盘上幸存 `mcode.log` 全 0 字节（11 个 `find` 命中逐一 `wc -c` 均 0）；反例：coding 探针 session `2026/10/21/20-43-00-962` 的末条 assistant 消息**确实产出** `<deliver-assets><media type="file" src=".../requests/utils.py" caption="…"/></deliver-assets>`。**⇒ 「0 触发/惰性」为假，「本题型真正起作用的差是人格/收尾/纠错风格而非交付格式」这句推断失去证据支撑**（三审 node 32898 issue 2 独立复现：幸存 25 个 coding 臂 session 中 **8 个**末条含 `<deliver-assets>`）。**正确表述改写为**：交付格式条款在 mcode 侧**确实触发（约 1/3 run）**、在 af 判分链下**结构性惰性** → 这**强化而非削弱**「不可搬」的底结论，但推断句须删。
- 另 4 条 minor：账本引用错位（0/20 的支撑在 `:838`/`:948`，`:906` 实为「官方 m31f rc 集 off-by-one」）；「af 全仓关键词 0 命中」措辞范围过宽（vendored `ci/advisory-db/**/*.md` 含 persona 子串）；`## Citations` 标签错误（两侧 systemPrompt 均无该节，实为 References 两侧皆有）；「巡检日志 :203」未点名文件（是 `状态观测/巡检日志.md:203`，非 `对齐组-state.md:203`）。

**⇒ 移交件已出**：`计划/研究组/B2回灌-移交①对齐组-20261023.md`（§13.9-D）。

### 13.6 三审意见（node 32898，红队·三审 step-5，02:44:51–03:02:35，**未参与本循环任何环节**）

**verdict = `confirmed`**，2 条材料性 + 9 条 minor/informational。核心：

1. **【材料性 1｜M1B 深测题集偏离 §12.5 定死的承诺域，违反 §6.3(a) 字面】**：三审亲算敏感性——限定回 V4-13 则官方 0/13、改造 8/12 已判 → 净 **+8**；7 道域缘 → 净 **+3**。**处置**：结论必须分账为「V4-13 净 +8」+「域缘扩测净 +3」，不得笼统写「承诺域 20 题净 +11」；该域重定义须**作为显式修订写回组账**（§12.5 的「定死」被更改），**不得静默沿用**；**是否接受此重定义由运行所有者裁决**，不接受则按净 +8 重述或重跑。
2. **【材料性 2｜B2 回灌评估的经验腿不成立（不可复现 + 被反例量化否证）】**：见 §13.5；结构性主张为真、经验腿为假 ⇒ 底结论不变但**机制叙事须改写**，B4 待定位项由「交付格式是否参与」改为「交付格式/收尾自包含条款贡献多少」。
3. minor 1–7：M1B 深测 §2 口径混用；MX 速筛 JSON `sum_max_rereads.modified=13`（实为 11）；M1B 速筛报告「8 条 preflight_failed」（实为 7）；M1B 深测「20/20 session 各恰 1 归属」对 11087 不成立（冒烟 + 深测双 session，按深测时间窗取值，采用值正确）；M1B 深测快照 `as-of.txt` 仍写「官方臂在飞」（过期模板复发，数据无损）；MX 深测 meta「35-39 近域带为空」须加「失败池内」限定；MX 15629 的 wall 取自 `judge_error` 行、late-judge 行 `agent_wall_ms=None` 的拆分未在 JSON 展示。
4. minor 8–9：M1B 深测 15 份 patch 卫生因 anolis 跑后清理**不可复验**（建议逐题落盘）；§6.2-④「禁用 prepare_failed/judge_error 题」按**结局**适用成立，但引用须保留该题 `judge_error→late-judge` 标注。
5. informational：**其他 worktree 的非本组改动**——`af-wt-align2`（fix4-align2-tier0）带 staged 修改（`crates/af-bench/src/main.rs` 等 5 文件），属①对齐组在飞工作树，**不可归因于②调优组**；但它构成回灌评估 risk 5/6「af 侧基线会被自身改动污染」的实证，下一轮差距表须注明对照臂与代号线。

**三审总判**：记录**无编造** —— 三审独立复算的两侧数字、聚合、域成员、指纹、快照与统计线**零处不符**（仅上述 minor 聚合/表述错）；**并行双路未破坏口径**：题集零重叠、快照先行、账本隔离、判分锁共享、官方臂零改动、资源红线未破。两处材料性问题均为「结论消费边界 + 一处真实纪律违背（M1B 深测域重定义）」，**不构成对记录真实性或口径格式合规性的否决**。

### 13.7 记账员本轮亲跑复算（node 32902，2026-10-23 03:0x CST）

> 以下 15 项全部为本记账员本轮**亲自执行**的命令与其输出（命令可照抄复现）；凡未列于此的数字一律注明出处节点。

| # | 复算项 | 命令 | 结果 |
|---|---|---|---|
| ① | 四份官方快照 as-of | `cat` 四个 `as-of.txt` | M1B 筛 **2026-10-22 19:20:04**、M1B 深 **2026-10-23 00:38:09**、MX 筛 **2026-10-22 19:21:54**、MX 深 **2026-10-23 00:38:21**（MX 两份为终局口径，M1B 两份仍写「官方臂在飞」= 过期模板复发） |
| ② | 官方件指纹一致性 | `sha256sum` 三件官方 results + 深/筛产物 | 官方 m3 = `43d7b1a0f49d70b50eeed7b99512057b1ea478a14453b4efa6e26f895bb7d9b8` **三处逐字节相同**（M1B 深快照 / MX 深快照 / live `/home/pan-ding/bench-data/results/bench-official-mcode-m3/results.jsonl`）；`deep-m3-results.jsonl`=`1690650f793a3134…`、`deep-m3-detail.json`=`516dfef2…`、`mx-deep-results.json`=`b05969b2…`、`mx-deep-detail.json`=`e888a7a2…`、`mx-screen-results.json`=`19abc…` |
| ③ | 变体单点差异 | `diff variants/base/run-one.sh variants/m1b-config-thinking/run-one.sh`；`diff …/base/run-one.sh …/mx-max-steps-120/run-one.sh` | M1B = 恰 2 hunk（注释块 + exec 行插入 `--config`），全文**无 `--effort`**；MX = 恰 1 行（插入 `--max-steps 120`） |
| ④ | M1B 臂级 yaml 差异 | `diff evidence/config-official-asof.yaml evidence/config-m1b-thinking.yaml` | 恰 2 hunk：M3 条目新增 `thinking.effortOptions[default..max]`+`defaultEffort: high`；M3.1-Flash `defaultEffort: default→high` |
| ⑤ | G1 域复算 | `cd /tmp/mcode-tune-draft-glm-r3 && python3 g1_recount_v3.py` | V1=17 / V2=15 / V3=15 / **V4=13**，V4 成员（13236、13398、10973、10999、11400、14011、15629、xarray-2905、pytest-7205、sphinx-10435/11510、sympy-16597/17318）与 §12.5/§12.7⑨ **逐题一致** |
| ⑥ | M1B 深测两侧复算 | python 解析 `deep-m3-results.jsonl` + 深测快照 last-row | 20 行 / 20 unique；**官方 0/20、改造 11/20**（另 13398 `reward=None`=non-judged）；**T→F = 0**；翻面 11 题 = 13236/10973/11087/14011/14315/2905/3993/7205/11510/16597/17318（与红队 32888 名单逐题一致） |
| ⑦ | **V4-13 分账复算**（三审 issue 1 的敏感性） | 位表规则 `c2∧c3∧c4∧c5t∧¬env` 逐题判定 + 改造侧 reward | V4∩深测 **13 题**（已判 12 / 通过 **8** → **净 +8**；13398 non-judged）；非 V4 **7 题**（11087、14315 c5t=False；8548 c5t=False；3993 env=True；4604、4661 c4=False&env=True；**10356 c4=False&env=False**）→ 域缘翻面 **3**（11087/14315/3993）→ **净 +3**。**与三审/红队的口径逐位一致** |
| ⑧ | 行为聚合复算（口径混用核） | 解析 `deep-m3-detail.json` 20 条 | 19 对已判配对：official (reread,max,consec,asst)=(25,55,16,529)、在场 18 → modified (18,40,8,505)、在场 14；全 20：official (26,57,17,594)、在场 19 → modified (18,40,8,586)、在场 14。⇒ 报告 §2 标题「19 对」下的 Σmax 57 / Σconsec 17 **确为全 20 口径值**（minor 1 复现） |
| ⑨ | MX 速筛聚合算术复算 | 解析 `mx-screen-results.json` 的 `behavior.per_task` 重算 | modified 逐题求和 Σmax=**11**（7+0+0+2+2）、Σreread=3、在场=3、Σconsec=5、Σasst=190；文件 `two_readings.sum_max_rereads.modified` 写 **13** ⇒ **聚合行算术错（其余各格无误）**，与红队 32875/三审 minor 2 一致 |
| ⑩ | M1B 速筛账本行数复算 | `collections.Counter` 解析 `m1b-config-thinking-m3/results.jsonl` | **21 行 = completed 14 + preflight_failed 7** ⇒ 报告「8 条 preflight_failed」**差一**（实质主张成立） |
| ⑪ | MX 深测两侧复算 | 解析 lane1 15 行 + lane2 1 行账本 last-row | 深测 7 题改造侧 last-row：11510 True、13236 True，其余 5 题 False ⇒ **2/7**（官方侧 7 题全 False，净 +2），与 `mx-deep-results.json` 的 `official_pass=0 / modified_pass=2 / net_pass=2` 一致 |
| ⑫ | MX 冒烟 rc=7 路径本地复验 | `grep -c limit_exceeded` / `cat judge.json` / `wc -c patch.diff` / `ls` run 目录 | 3993：`mcode.log` limit_exceeded **1 行**、judge `resolved=false f2p 0/2 p2p 2398/0 tests 2400`、`patch.diff` **3692B**；13398：run 目录**仅 mcode.log（100B）**、无 patch → reward=None。**rc=7→judge→reward 记账路径两腿均复现** |
| ⑬ | M1B 冒烟 m31f 终态复验 | 解析 `out/m1b-config-thinking-m31f/results.jsonl` | 8 行 = `completed`×1（pylint-4604，reward=False，wall=**221,173ms**，<界 4,568,830ms）+ `preflight_failed`×7 ⇒ 冒烟在飞状态**已闭合**，无 CLI 拒绝死亡路径 |
| ⑭ | af 零改动复验 | `git -C af status --porcelain` / `rev-parse HEAD` / `branch --show-current` / `worktree list` | 仅 5 行未跟踪 `poc/poc-kernelrun/*`；HEAD=`94cd1923c34842983049bce5f97b3dcb6c7c348b`；分支 `guardrail-fix2`；12 个 worktree（`af-wt-align2` 等属①组在飞）⇒ **本组 af 零改动成立** |
| ⑮ | 无旋钮对照缺失复验 | 解析 `out/base-m3/results.jsonl` | **仅 1 行**（`pydata__xarray-3993`）⇒ 20 题/7 题**均无同参无旋钮对照臂**，采样噪声不可剥离（与两候选 caveats 一致） |

### 13.8 本轮未跑 / 未复核 / 本节点未独立复算（如实登记）

| # | 项 | 说明 |
|---|---|---|
| 1 | **m31f 回归抽查准入门** | **两候选均未跑**（out/ 下无 m31f 深测产物）→ 本轮结论**不含 m31f 不退化证据** |
| 2 | **全池 120 题 m31f 采纳线**（§6.3(c) 净≥4） | 未测 |
| 3 | **base 变体臂@m3 / @m31f** | 0 跑（`base-m3` 仅 1 行 xarray-3993，§13.7-⑮） |
| 4 | **轨迹人工抽样核对** | 未做（19/20 题仅计数器双读法 + 判分字段核对） |
| 5 | **M1B 深测 15 份 patch 卫生 + 13398 run 目录** | anolis 跑后清理致**不可复验**（三审 minor 8 同判） |
| 6 | **rc=70 的 mcode 退出码语义** | 未独立验证（仅轨迹一致性核对：81 轮 noedit 78、49 条 bash、零写入）；按 §7-2 单列 non-judged，最坏计 0 净分不变 |
| 7 | **B2 两侧通过率/行为三元组** | 本轮**未复算**（引用 §12.2/§12.4 已复算值；回灌评估员与红队 32795 均为对照原文复核，未重新解析 results.jsonl/session） |
| 8 | **回灌评估的 19 臂 `mcode.log` grep** | 不可复现（产物已清，幸存件 0 字节）—— 已按红队/三审意见改写机制叙事 |
| 9 | **af 侧** | 未跑任何变体/冒烟/回归；未 `cargo build/test`；未在 af 侧构造行为计数器；未验 mcode `work` 第三档 |
| 10 | **组合测试** | 未跑（见 §13.9-B6 前置条件） |
| 11 | **官方侧逐题 judge 的 p2p / tests_collected** | 不可得（官方旧 4 字段格式；官方 tier runs/ 快照时已空，引自 §10.2） |
| 12 | **messages.jsonl 原件归档** | 仍未归档（§11.10-F 边界沿用：session 清理后逐字节仲裁永久失效） |
| 13 | **官方臂 live 漂移** | 官方 m3 `results.jsonl` sha256 自 `8aa08fec…` 变为 `43d7b1a0…`（clean-rerun 产线 15:51 回灌 +1 行 astropy-12907，不在本轮任一域内、不改 24 败）—— 本轮四份快照**统一锁在 `43d7b1a0…`**，与 live 逐字节一致（§13.7-②） |

### 13.9 下一循环动作（可直接派工）

#### A. 阻塞项（须先由运行所有者/厂长裁决，否则下一循环仍带着未结账结论开跑）

| # | 事项 | 依据 |
|---|---|---|
| **A1** | **M1B 深测域重定义裁决**（三审 issue 1，本循环新增最高优先）：接受「V4-13 净 +8 + 域缘扩测净 +3」的分账表述，还是按 V4-13 净 +8 重述或重跑。**裁决前 §12.5「承诺域定死」的措辞不得被静默沿用** | 三审 32898 issue 1；红队 32888 issue 1；§6.3(a) |
| **A2** | **M1B 结论的消费口径固化**：本账及任何下游引用一律写「V4-13 净 +8 ＋ 域缘扩测净 +3」，**禁**写「承诺域 20 题净 +11」 | 三审 32898 issue 1；§13.7-⑦ |
| **A3** | **MX 的候选定性**：旋钮**恒不咬合**（N=120 全池 asst max=65）、n=7、p=0.5 不显著、5/7 为速筛复用行 ⇒ 现行「确证候选」标签是否降级为「**非退化保险 + rc=7 记账路径证据**」（候选自陈的价值主张），须裁决 | §12.5 L900 前置披露；红队 32893 issue ②；§13.4 |
| **A4** | **B2 m31f 门的 scope 裁决**（承接 §12.9-A1）+ **sympy-16597 单题 T→F** 是否阻塞 | §12.9-A1；三审 32898 issue 2 |
| **A5** | **B2 是否升级为全池复跑**（120 题 m31f、净≥4=3pp；需运营者批题池与窗口） | §6.3(c)；§12.9-A2 |
| **A6** | **扩题池（第二循环 §6.0-B）** | §11.7-6(b)；§12.9-A3 |
| **A7** | **组合测试准入裁决**（见 B6 前置）：谁进组合、组合题集怎么定 | 本节 B6 |

#### B. 可立即做（不需裁决；B6 需 A1/A3 先落）

| # | 事项 | 落点 / 判据 |
|---|---|---|
| **B6** | **组合测试协议（第二个确证者出现 → 触发 §6.4）**：本循环出现两个过筛+过深测的候选（M1B、MX），加上第三循环的 B2，**§6.4 的组合测试协议正式具备触发条件**。**但组合臂开跑前必须先满足 4 项前置**：①**A1/A3 落定**（否则组合四臂的题集与「单点净」基线都无定义）②**题集统一**：组合四臂必须同题集、同模型、同判分链、其余参数全同；建议统一取 **V4-13**（M1B 域内；B2 域内交集另算），MX 侧只有 7 题域，**不得把 M1B 的 20 题与 MX 的 7 题拼成组合题集** ③**补 base 变体臂@m3**（禁官方臂当对照；base@m3 现仅 1 行）④**补 m31f 回归抽查准入门**。<br>**臂设计（§6.4(a)）**：O 官方 / 单点 A（=M1B）/ 单点 B（=B2）/ 组合 AB；AB 臂两个旋钮各自独立生效（M1B=臂级 yaml `--config` 通道 + B2=`--prompt-mode coding`，注入文件 exclude 规则一致）。<br>**判定规则**：组合净 ≥ max(单点净) 且「组合−次优单点」的 discordant 反向 ≤1 → **采纳组合**；组合净 < 任一单点净且差 ≥2 净题 → **判冲突、禁止组合**，收场=「更强单点 + 弱旋钮降级为提示层（换通道不叠加）」；组合 ≈ 单点（差 ≤1）→ **不叠加收益**，取更简单者。统计报 McNemar 精确 p + discordant 明细；n=20 只出方向性结论。<br>**冲突观察（§6.4(b)）**：四臂各留 `mcode.log`/`patch.diff`/`eval.log`/`judge.json`，统一落 `/tmp/mcode-tune-combo-M1B-B2/combo-<task>/<臂>/`；按 C1 补丁语义冲突 / C2 提示张力 / C3 注入文件互斥 / C4 资源-截断冲突 / C5 假冲突（环境性失败须剔除）分类出清单。<br>**干扰项先排**（任一存在则该臂作废重跑，不得直接判「冲突」）：内层超时、判分污染、注入文件进 diff、官方臂数字漂移（as-of 不一致）。<br>**落点**：`/tmp/mcode-tune-combo-M1B-B2/` + 本文件 §14 | §6.4(a)(b)；§13.6；A1/A3 |
| **B7** | **m31f 回归抽查准入门**（两候选 0 跑）：改造臂 + **base 变体臂@m31f** 同题（禁官方臂当对照）；三判据：resolved 不跌（net≥0）/ 行为不恶化（wall+asst_turns 求和涨幅 ≤25%，阈值预注册）/ 终稿非空（rc=7 截断与内层超时单列） | §12.9-B3；§7-19 |
| **B8** | **base@m3 同参配对臂**（无旋钮对照）：补 base 变体臂同 20/7 题，剥离采样噪声 | §13.7-⑮；§11.2 探针红队 i1 |
| **B9** | **B4 非行为机制路径定位扩到 M1B 侧**：M1B 11 翻面中 6 题非 reread 介导（16597 翻面但 reread 1→2；14315/7205/10973 reread 归 0）——先做产物级对照（终稿结构/工具面/判分链输入），产出机制假设与证伪条件 | §12.9-B4；§13.4 |
| **B10** | **证据落盘整改**（三审 minor 8 建议）：深测 patch 卫生逐题落盘（与 behavior raw 同级）；快照器 `as-of.txt` 文案改终局口径（M1B 两份快照复发） | 三审 32898 minor 5/8；§11.9-18/C2 |
| **B11** | **M1B 候选再登记**：在 §12.5 条目追加**显式修订留痕**——承诺域「定死」已被本轮深测放宽为 V4-13 + 7 道域缘（待 A1 裁决后定稿），不得静默沿用 | 三审 32898 issue 1；A1 |

#### C. 文档更正清单（随下一次写作一并改）

| # | 更正 | 落点 |
|---|---|---|
| C7 | M1B 深测报告 §2 口径混用：标题「19 对已判配对」下的 Σmax 57 / Σconsec 17 **改为 55 / 16**（全 20 口径值另注） | `deep-m3-report.md` §2 |
| C8 | MX 速筛 JSON 聚合行 `two_readings.sum_max_rereads.modified` **13 → 11**（或删该行只留逐题） | `/tmp/mcode-tune-mx-b/mx-screen-results.json` |
| C9 | M1B 速筛报告「8 条 preflight_failed」**→ 7 条**（账本 21 行 = completed 14 + preflight_failed 7） | `screen-report.md` §1 |
| C10 | M1B 深测「20/20 session 各恰 1 归属」对 django-11087 **不成立**（冒烟 + 深测双 session）→ 改为「11087 双 session 按深测时间窗取值」（采用值正确） | `deep-m3-report.md` §3 |
| C11 | 快照 `as-of.txt` 过期模板（「官方臂在飞」）**本轮第三次复发**（M1B 屏/深两份；MX 两份已修）→ 快照器改文案 | §11.9-18/C2；B10 |
| C12 | MX 深测 meta「35-39 近域带为空」**须加「失败池内」限定**（全池口径有 7 题落在该带，但全为官方 pass） | `mx-deep-detail.json` meta |
| C13 | MX 15629 的 wall 取自 `judge_error` 行（late-judge 行 `agent_wall_ms=None`）→ 逐题条目展示该拆分 | `mx-deep-detail.json` |
| C14 | §12.5 M1B「承诺域定死」**须写明本轮深测放宽**（待 A1 裁决） | §12.5；B11 |
| C15 | 回灌评估的机制叙事**改写**：「0 触发/惰性」为假 → 「交付格式条款在 mcode 侧约 1/3 run 触发、在 af 判分链下结构性惰性」；删「本题型真正起作用的差是人格/收尾/纠错风格」推断句 | `B2回灌-移交①对齐组-20261023.md` §3.3；§13.5 |
| C16 | 账本 §11.2:447 的「17219 B / 15655 B」**是字符数**，字节数为 17327 / 15763 | §11.2；本节 §13.5 |

#### D. 移交件（回灌 → ①对齐组）

- **已出**：`计划/研究组/B2回灌-移交①对齐组-20261023.md`（触发：§13.5 的 `recommendation` 明确「af 侧动作只能由①对齐组以 af 原生候选形式走变体周期」；ask 要求「回灌若建议走①则写明移交件」）。
- **移交内容**：①mcode 侧机制语义事实（CLI/资产尺寸/装配链/双 session 对照 + tools 数组 sha256 一致）②af 侧对应物与**结构性惰性**的代码依据 ③**不可移植的理由**与风险 7 条 ④**若①组立项的正确候选形态**（af 原生「重复读同一文件」域 + af 侧新建计数器（`harness.db` 的 `run_row.transcript_json`）+ 提示增量走 af 既定分工 + 自建 base 对照臂 + 代号线 bump）⑤**前置条件**（②组先闭合 A1 scope / A2 全池采纳线 / B4 机制定位；B4 若落在 mcode 特有机制则结论升级为「无需移植」）⑥边界（②组 af 零改动、未跑任何 af 变体）。
- **接收方**：①对齐组（af 改动管辖权在①）；**触发条件**：①组自认为可立项时按其变体周期流程取用；**②组不催办、不代改 af**。

### 13.10 本节与第四循环进度表对照（供快速核对）

| 候选 | 冒烟 | 速筛（官方→改造） | 深测（官方→改造） | 进度表终值 |
|---|---|---|---|---|
| **M1B**「config 级 thinking 档位 high × G1 口径/推演域」 | 冒烟在飞 → **已闭合**（m3 11087 过；m31f 4604 17:58:52 终态 completed/False/221,173ms） | 0/5 → **2/5**（红队 confirmed） | 0/20 → **11/20**（净 +11；**分账 = V4-13 净 +8 + 域缘净 +3**；红队 confirmed） | `确证候选 / 0过 → 2过 → 0/20 → 11/20` |
| **MX**「--max-steps 120 失控护栏 × 失控型失败域」 | **冒烟过**（m3 穿透 + rc=7→judge→reward 记账路径两腿兑现） | 0/5 → **2/5**（红队 confirmed） | 0/7 → **2/7**（净 +2，p=0.5，旋钮恒不咬合；红队 confirmed） | `确证候选 / 0过 → 2过 → 0/7 → 2/7` |
| **B2**（第三循环，`--prompt-mode coding`） | — | — | 19 题 9/19 vs 0/19（第三循环，本轮**未复算**） | 准入门仅部分放电；**本轮回灌评估只做只读评估，未新增证据** |

---

## 14. 第五循环·完整账（状态记账员，写入时点 **2026-10-23 08:3x CST**）

> 本节记录第五循环（run `dwfrun-0fe55ff6-f057-4a7d-bfb8-2d1321e1274b`，名 **研究组②调优组·第五循环（组合）**）的组合变体实施与冒烟、组合深测、三项消融、B2 提示风格移交件整理、红队三审，并对下一循环给出动作与移交件。**§14.6 是本记账员本轮亲跑复算**（命令与输出逐条在案）；§14.1–§14.5 的数字凡未标「记账员亲跑」者，取自对应节点的 `result_json` 与盘上工件。**本节不采信任何未复算的推论**；凡三审/红队提出的裁决项，本节只登记「待裁决」，不代替运行所有者下结论。
> **本节最高优先事项**：三审 `verdict=rejected`，3 条材料性；其中 issue 1 指认**流程内深测数被记成 1/20（错数）**。**本节一律按记账员亲跑复算的 11/20 落账**，并在 §14.2.3 完整登记错数污染链。**任何下游引用 §14 时禁引用 1/20。**
> **口径提示**：§0 与 §1 为第一循环口径、§13 为第四循环口径，均已过时；第五循环的最新读数以本节为准。

### 14.0 元信息与 as-of

| 项 | 值 | 取数 |
|---|---|---|
| run | `dwfrun-0fe55ff6-f057-4a7d-bfb8-2d1321e1274b` / `研究组②调优组·第五循环（组合）`，status=`running`（记账时未终），spent_tokens=46,866,871，script_hash=`0a5555ec273ada83…`，caps_max_concurrency=14 | `~/.zcode/cli/db/db.sqlite` 表 `dwf_run`（本轮只读打开 `mode=ro`） |
| 前身关系 | `resumed_from=None`（**第五循环不从第四循环续跑**，独立发起）；承接 §13.9-B6 的组合协议触发条件 | 同上 |
| 脚本 | 全文 **169 行**，4 个 phase（组合实施+冒烟 ∥ 移交件整理 / 组合深测 / 防冲突消融 / 三审与落账） | `dwf_run.script_text` 本节点导出后逐行实读（导出件 `/tmp/fifthloop/script.mjs`） |
| 协议触发条件（脚本原文） | 消融段 **「仅当组合 < 最佳单旋钮」**：`const bestSingle = 11`（L103）、判据 `deep.combo_pass < bestSingle`（L104）；组合深测数取 `combo_pass`（L95/L120） | 脚本 L101-104 |
| 节点序（ask → actor → 模型 → 时段 CST） | 32920 移交整理员(MM) 04:32:31→04:35:36 → 32921 组合实施员(GLM) 04:32:31→04:51:11 → 32935 红队·**组合审查**(S5) 04:51:11→05:00:55 → 32939 深测执行员(GLM) 05:00:56→05:14:07 → 32944 红队·**深测审查**(S5) 05:14:07→05:22:15 → 32948 深测执行员·消融①(GLM) 05:22:16→05:32:38 → 32953 深测执行员·消融②(GLM) 05:32:38→07:26:23 → 33005 深测执行员·消融③(GLM) 07:26:23→08:07:56 → 33013 红队·**三审**(S5) 08:07:56→08:30:55 → **33017 状态记账员（本节点）** 08:30:55→ | `dwf_node` × `dwf_actor`（`left join` on `site_id`），time_created/time_updated 本地化 +0800 |
| report 节点（5 个，进度表「调优组·第五循环（组合）进度」） | 32934 组合变体「冒烟过」04:51:11 / 32943 组合深测「组合有效 0/20 → 1/20」05:14:07 / 32952 消融-knob①「无冲突 0/5」05:32:38 / 33004 消融-knob②「无冲突 3/5」07:26:23 / 33012 消融-knob③「无冲突 3/5」08:07:56 | 同上 |
| 模型 | 组合实施员/深测执行员（含三次消融）= `account:bigmodel-individual-coding-plan/GLM-5.3-Flash`（脚本 `GLM_F`=…`$max`）；移交整理员/记账员 = `minimax/Minimax-M3.1-Flash-Preview`（`MM_F`=`$enabled`）；红队（组合审查 + 深测审查 + 三审）全部 `new-provider/step-5-preview`（`S5`=`$high`） | `dwf_actor.resolved_model` + 脚本 L36-38 |
| escalate 记录 | `dwfq-0fe55ff6-1`（深测执行员 05:26:01 提问 → 运行所有者裁决） | `dwf_event` sequence 48/49 |

### 14.1 组合变体（node 32921 组合实施员；红队 32935 `confirmed`）

| 项 | 读数 | 出处 |
|---|---|---|
| 变体路径 | `/tmp/mcode-tune-combo/variants/combo-b2-m1b-mx`（`run-one.sh` sha256 `b5bcb568…`） | node 32921；**记账员亲跑 `sha256sum` + `diff`**（§14.6-④） |
| 三旋钮叠加 | knob①[B2] `--prompt-mode coding` ＋ knob②[M1B] `--config "$HOME/mcode-tune-combo/config-combo-m1b.yaml"` ＋ knob③[MX] `--max-steps 120`，按固定顺序插在 exec 行 `--model` 之后 | node 32921；**记账员亲跑 `diff`**（§14.6-④，base→combo 仅 exec 行一处旋钮插入 + auth-sync 路径） |
| 单点源可溯 | SOURCES.sha256 六件源：base `9e2f06c3…` / b2 `30c39784…` / m1b-run `6c903c52…` / m1b-yaml `f76cc622…` / mx `e25a1720…` / driver `167bc913…` | node 32921；**记账员亲跑复算 yaml 三方同源**（§14.6-⑤） |
| 臂级 yaml | `config-combo-m1b.yaml` sha256 `f76cc62262b3944…`，与 M1B 件**逐字节同源**；对官方 `config-official-asof.yaml` **恰 2 hunk**（M3 补 `thinking.effortOptions[default..max]`+`defaultEffort: high`；M3.1-Flash `defaultEffort: default→high`）；全文无 `--effort` 禁旗（§7-11） | node 32921；**记账员亲跑 `diff` + `sha256sum`**（§14.6-⑤，输出逐字在案） |
| 注入排除 / 补丁卫生 | `knobs.json inject=[]`；`.git/info/exclude` 组合标记块落位（`git check-ignore -v` 解析 exclude:8/9）；冒烟 `git status` 仅 ` M django/db/models/deletion.py` | node 32921 + `/tmp/mcode-tune-combo/evidence-inject-exclude.txt`；红队 32935 独立复验 |
| 冒烟（django-11087@m3） | nohup 04:42:06–04:47:14，wall=**301,954ms**（<界 1,028,560ms）；completed ∧ reward=**true**；judge resolved=true f2p 1/0 p2p 41/0 tests 42；`patch.diff` 3,913B 唯一 deletion.py；**首判 judge.json 0 字节 → 账本 judge_error 行不掩盖 → late-judge 恢复 completed/True**（§7-20 模式），账本 2 行 last-row=completed/True | node 32921；红队 32935 |
| 冒烟三指纹 | ①`systemPrompt` 头 `You run inside MiniMax Code…` 17208 字符/17316 字节 sha16 `1ce99738ecbcc82c`，对照 tui 头 `You are a coding agent running in the MiniMax Code terminal,` 15,659 字符；②`thinkingLevel=high`（官方 m3 缺省 medium）；③`--max-steps 120` **请求层无指纹**（llm-call.json 键集实测无 `maxSteps`）→ 改用运行中 cmdline（pid 3351171 三旗标同进程）+ CLI 接受（llm-call.json 已生成、无 `does not support reasoning effort selection`）+ 机制族 `rc=7↔limit_exceeded` 1:1 三层举证 | node 32921；红队 32935 四项亲跑 |
| 截断层 | 同 session `roles={'user':1,'assistant':52,'toolResult':51}`，52<120；`mcode.log` grep `limit_exceeded`=**0** → **knob③ 本轮全程未咬合**（§12.5「N=120 恒不咬合」披露如期兑现） | 红队 32935 |
| 资源纪律 | 本臂 0 容器（anolis 4-6 容器全 `afbench-*` 他产线，WARN 让行未动）；预检 `mcode_exec≤2`、`disk_ok=True`；判分走 `judge.lock`+cbj 清零等待 | node 32921；红队 32935 |
| af 零改动 | HEAD `94cd1923c348…`、分支 `guardrail-fix2`、`git status --porcelain` 仅 5 行未跟踪 `poc/poc-kernelrun/*` | node 32921；**记账员亲跑**（§14.6-⑩）；三审 33013 亦复跑 |
| 进度表行 | `组合变体 / 冒烟过 / official=- / combo=knob①+knob②+knob③` | report node 32934 |

**组合实施员自陈的结论边界（记账员照录，不改写）**：`smoke-report.md` §5 与 `knobs.json promised_disclosure` 均明示 n=1 域外题单次采样，**只证三旋钮叠加生效 + 无 CLI 拒绝 + 卫生 clean + 判分链走通，不得读作组合收益**；组合四臂对比（§13.9-B6）须待 A1/A3 裁决 + 题集统一 + base@m3 对照 + m31f 准入门，**本轮均未跑**。

**红队 32935（组合审查）= `confirmed`，4 条（1 informational + 3 minor），无材料性**

1. 【informational·前瞻】knob③「恒不咬合」只是相对**官方臂 asst 分布**的性质（官方 m3 全池 max=65）；**本 combo run asst=52 已达 120 上限的 43%**，且改造臂 turns 可超官方池范围（官方同题 11087 仅 asst=6，combo=52，单点 25-31）→ 四臂对比时 **C4「资源-截断冲突」必须作为活观察项**，不得凭本次冒烟豁免。
2. 【minor】systemPrompt 资产**非跨 run 字节稳定**：combo run 17208 字符/`1ce99738…`，B2 单点同题 session 为 17214 字符/`5ae8d7ce…`，tui 缺省两 session 亦互差 3 字符 → **跨 run 比 systemPrompt sha 不成立**；身份判据应取「头语+尺寸带+tools 数组 sha」。
3. 【minor·披露口径】冒烟报告「预检 /data 16G」的具体数值**不可从落盘工件独立复算**（`results.jsonl verifier_note` 仅记 `disk_ok=True`）。
4. 【informational】run 级轨迹入 MX 域带（asst=52≥40）与题级「域外」不矛盾但**勿混用**：11087 按官方臂成员（官方 asst=6）不属 MX 7 题域，「域外题」按任务成员成立。

### 14.2 组合深测（node 32939 深测执行员；红队 32944 `confirmed`）

#### 14.2.1 题集与快照

| 项 | 读数 | 出处 |
|---|---|---|
| 题集 | 20 题 = M1B 深测 20 题 ∪ MX 失控域 7 题；**MX7 ⊂ M1B20 亲算成立 ⇒ union 为恒等运算 = 20**（未发生 §13.9-B6 禁令的「20+7 拼接」）；名单落 `/tmp/mcode-tune-combo/combo-question-set.json` | node 32939；红队 32944 ①；**记账员亲跑**（§14.6-②，MX7⊂题集 True） |
| 官方快照（深测） | `/tmp/mcode-tune-combo/official-snapshot-deep-20261023T050541Z`，as-of **2026-10-23 05:05:41 +0800**，先于 lane1 起批 05:08:19 | `as-of.txt`；**记账员亲读**（§14.6-①） |
| 快照 m3 sha256 | `43d7b1a0f49d70b50eeed7b99512057b1ea478a14453b4efa6e26f895bb7d9b8`，与 043840Z 冒烟快照、live `/tmp/bench-official-mcode-m3` 、`/home/pan-ding/bench-data/…` **四处逐字节相同 = 零漂移** | **记账员亲跑 `sha256sum`**（§14.6-③）；红队 32944 ② |
| 快照 m31f sha256 | `5758019809bfc057…`（同四处一致） | 同上 |
| ⚠ 快照机制缺陷 | **五个快照目录内的 `bench-official-mcode-m3` 全是符号链接**（→ `/home/pan-ding/bench-data/…`，symlink mtime 10-22 13:03），`cp -a` 对 symlink 源只复制链接本身 → **不构成冻结拷贝**，对复飞的官方臂无保护、会静默漂移。官方臂已终局（末改 10-22 15:51:45）故本次零漂移结论仍成立 | **记账员亲跑 `ls -la`**（§14.6-①，输出逐条在案）；红队 32944 issue 1；三审 33013 同判 |
| 跑批拆分 | 3 路 nohup（lane1 pid1283542=7 题 / lane2 pid1283543=6 题 / lane3 pid1283544=6 题，19 新题两两不交 + 11087 冒烟复用行）；三份 driver 拷贝 sha256 `764d70a1…` 逐位同；`judge.lock` 符号链接回共享件判分串行 | node 32939；红队 32944 ④ |
| 让行纪律 | 他线 `mcode_exec` 3-7 在飞时 60s 轮询等待，**本组全程 0 容器贡献** | node 32939；红队 32944 ⑥ |

#### 14.2.2 两侧读数（双报；**记账员亲跑 last-row 复算**）

| 读法 | 官方侧 | 组合侧 | 差 |
|---|---|---|---|
| 通过数（主口径） | **0/20**（20 题全 reward=False ∧ completed，m3fail 锚成立） | **11/20** | **净 +11** |
| T→F | — | **0** | 无退化 |
| F→T | — | **11**（13236、10973、11087、14011、14315、2905、3993、11510、8548、16597、17318） | 全部同向 |
| McNemar 精确双尾 | discordant 11 全同向 → **p=2×2⁻¹¹=0.0009765625**；n=20 → 5pp/题，只出方向性结论；3pp×20=0.6 → 局部门槛净≥1 | | |

**行为双报（冻结计数器 `behave_count.py` sha256 `e667c13e…`，双侧亲验；**记账员亲跑逐题重算**，§14.6-⑦）**

| 口径 | 官方（Σreread/Σmax/Σconsec/Σasst） | 组合（同） | 在场（reread≥1 题数） |
|---|---|---|---|
| 全 20 题 | 26 / 57 / 17 / 594 | **18 / 44 / 14 / 596** | 19 → **13**（consec 在场 14 → **10**） |

**域分账（组合臂按 `subdomain_ledger`，**记账员亲跑重算**）**

| 子集 | n | 官方过 | 组合过 | 净 | 与 §13.4（M1B 单点）对照 |
|---|---|---|---|---|---|
| **V4-13** | 13 | 0 | **7** | **净 +7** | §13.4 = V4-13 净 **+8**（彼时 13398 为 non-judged，本轮已判 False；另本轮 7205 未翻、8548 翻） |
| **MX7** | 7 | 0 | 4 | 净 +4 | MX 单点 §13.4 = 2/7 |
| 域缘（非 V4-13） | 7 | 0 | **4** | **净 +4** | §13.4 = 域缘净 +3（11087、14315、3993）→ 本轮 +8548 |

> ⇒ **组合分账口径 = 「V4-13 净 +7 ＋ 域缘扩测净 +4」**（合计 +11）。**禁**写「承诺域 20 题净 +11」（沿用 §13.9-A2 的分账纪律；域重定义是否接受仍待 A1 裁决）。

**翻面集与 M1B 单点的差（记账员亲跑比对）**：组合 11/20 与 M1B 单点 11/20 **同数但不同集**——组合多翻 `sphinx-8548`、M1B 多翻 `pytest-7205`，其余 10 题重合。按 §6.4(a)「组合 ≈ 单点（差 ≤1）→ 不叠加收益、取更简单者」：**本轮组合未相对 M1B 单点产生可归因增益**。

**深测层 caveats（登记自 `combo-deep-detail.json` `caveats`，五条）**：①单臂单次采样 n=1/题，**无 base@m3 无旋钮对照臂**（§13.8-3 沿用）→ 采样噪声不可剥离；②**m31f 回归抽查准入门本臂未跑**（§13.9-B7 敞开）→ 本结论**不含 m31f 不退化证据**；③MX knob 恒不咬合披露沿用，`rc7_truncations=0` 以实测覆写；④django-11087 = 冒烟行复用（late-judge，last-row completed/True，wall 取首行 301,954ms）；⑤§13.9-B6 四臂判定规则（O/A/B/AB + 判冲突/采纳）不在本跑范围，**A1/A3 未裁决**。

**进度表行**：32943 `组合深测 / 组合有效 / official=0/20 / combo=1/20` —— ⚠ **该行组合侧为错数，见 §14.2.3**。

#### 14.2.3 ⚠ 错数污染链登记（本节最高优先，**禁引用 1/20**）

| 环节 | 记录值 | 实况 | 出处 |
|---|---|---|---|
| node 32939 返回值 | `combo_pass=1`、`net_pass=1`，`domain_note` 自标「**中间态** as-of 05:13:21，跑批仍在飞，非终版读数」 | 提交时点仅 04:47 冒烟一行终判；**19 新题尚未终判** | node 32939 |
| 时序证据 | 消融路 ab1/ab2 **05:27 已起批**（`official-snapshot-ablation-20261023T052704Z` as-of + ab1 脚本头） | 深测三路 **06:58:09 / 07:02:47 / 07:03:39 才退出**（`logs/combo-deep-lane*.log`）⇒ **深测 ask 在批次未终态即返回** | 三审 33013 实跑日志 |
| report 32943 | `组合有效 / 0/20 → 1/20` | 终版应为 `0/20 → 11/20` | 同上 |
| 红队 deepCheck 32944 | `confirmed`（审的是中间态，本身已如实标注） | 其 issues 中「横向对比预载」已载 B2 9/19、M1B 11/20、MX 2/7 与 §12.4/§13.4 逐位一致 | node 32944 |
| run 结论模板 | L130 渲染「深测 ${combo_pass}/${n} vs 官方 …」⇒ **错数 1/20 会进最终结论串** | — | 脚本 L95/L120/L130 |
| **三审** | **`verdict = rejected`**，issue 1 即此事：**「绝不可按 1/20 入账」** | **记账员亲跑复算三路账本 last-row = 11 pass / 9 fail / 20 题 / 0 T→F / 11 F→T**（§14.6-①） | 三审 33013 issue 1 + **记账员独立复现** |

**⇒ 本账 §14 的深测数一律取 11/20**；1/20 只作为**流程缺陷证据**留档，不得被任何下游引用为组合收益读数。

### 14.3 消融（node 32948 / 32953 / 33005，红队 33013 判定「未按协议触发」）

**触发条件复算**：脚本 L103 `bestSingle = 11`、L104 `deep.combo_pass < bestSingle`。**终版真实数 11 ⇒ 11 < 11 为假 ⇒ 按协议三项消融本不应跑**；它们跑起来只因 §14.2.3 的部分错数 1 满足了 `1 < 11`。运营者在 escalate 答复中亦重申「**消融段触发条件不变（组合深测 < 最佳单旋钮 11 才跑）**」（`dwf_event` sequence 49）。⇒ **本节把消融整体登记为「未按协议触发」，结果只作 n=5 单次采样方向性读数。**

**消融题集（`dwfq-0fe55ff6-1` 运营者裁决，三变体统一）**：V4-13 ∩ MX-7 = {astropy-13236, astropy-13398, django-15629, sphinx-11510, sympy-16597}（恰 5 题），落 `/tmp/mcode-tune-combo/ablation-question-set.json`。**记账员亲跑核**：5 题 ⊂ 20 题集 True（§14.6-②）。⚠ 该裁决**只覆盖题集，不覆盖触发条件**——三审 33013 明判，账本须如实区分。

**四臂同题集对照（官方 0/5；**记账员亲跑三本消融账本 last-row 复算**，§14.6-⑧）**

| 臂 | 变体 sha256 | 逐题（13236 / 13398 / 15629 / 11510 / 16597） | pass | 节点 `conflict` 字段 |
|---|---|---|---|---|
| 官方 | — | F / F / F / F / F | **0/5** | — |
| **组合三旋钮** combo-b2-m1b-mx | `b5bcb568…` | T / F / F / T / T | **3/5** | — |
| drop-B2 = M1B+MX | `d8013a53…` | T / **T** / **T** / F / T | **4/5** | `false`（问句写「去掉 knob①」，脚本按轮次逐项推进） |
| drop-M1B = B2+MX | `0207467096…` | T / F / T / F / T | **3/5** | `false` |
| drop-MX = B2+M1B | `24ca776db…` | T / F / T / T / F | **3/5** | `false` |
| （旁证）M1B 单点同 5 题 | — | T / non-judged / F / T / T | **3/5（1 题 non-judged）** | — |

**消融结论（按三审要求降级表述）**

- 唯一过 4 的臂恰为**去掉 knob①[B2]** 的臂（4/5 vs 组合同 5 题 3/5），**方向上**与「组合 11/20 = M1B 单点 11/20」的同值现象同向，二者均指向 knob①[B2] 在叠加中无正贡献。
- **但差值仅 +1 净题**，discordant 为 13398 T/F、15629 T/F、11510 F/T 三对。账本自有归因标准不支持「负交互」定性：§6.4(a) 判冲突须 **差 ≥2 净题**；§11.3 整改「±1 净题差不具旋钮可归性」；§11.2 探针红队 i1 无旋钮两臂行为噪声 **56–105%**。且对 knob③[MX] 的 discordant 2 题（15629 F/T、16597 T/F）恰以这套噪声逻辑豁免，对 knob① 的 2:1 却亮 `conflict=true` → **双重标准**。
- ⇒ **本账不写「knob①[B2] 负交互」**，只写「**n=5 单次采样下 drop-B2 恰高 1 净题，落在噪声带内，不足以定性；与组合≈M1B 单点的观察同向**」。

**消融层其他口径边界**：每题 n=1 单次采样；**base@m3 对照臂仍缺**；**m31f 准入门三臂均未跑**；消融臂补丁卫生由执行员复检（**记账员亲跑复检 35 份 `patch.diff` 禁前缀 0 命中**，§14.6-⑨）。

### 14.4 移交件（node 32920 移交整理员，零槽位并行）

| 项 | 读数 |
|---|---|
| **路径** | `计划/研究组/B2提示风格-移交对齐组.md`（21,386B，mtime 10-23 04:35）；上位件 `计划/研究组/B2回灌-移交①对齐组-20261023.md` |
| 触发 | §13.5 `recommendation` = af 侧动作只能由①对齐组以 af 原生候选形式走其变体周期；本件把「人格句 / 收尾自包含 / 纠错风格」三件逐条落到 af 提示装配层 |
| 零改动声明 | 「零代码改动、零 anolis 容器（对 anolis 只做 4 次只读 ssh）」 |
| 三件逐条结论 | ①**人格句 → af `main.rs:543 SWEV_SYSTEM_PROMPT`（一行）：无可搬语义，不建议立项**（mcode 那句引用 MiniMax Code 产品面/MCode 名/Environment 段，而 af 无 Environment 段；`main.rs:539-542` 注释把「system 保持一行」记为有实证的设计决策）②**收尾自包含 → af instance 协议 `main.rs:548-566`：作用面不存在，不建议立项**（af 在 `echo TASK_COMPLETE` 后立即终止，`run.rs:601-604` 立即 Terminal(Completed)，无「preamble 被折叠」面）③**纠错风格 → 同一 instance 协议：唯一可立项候选、证据等级最弱**，须与 af 既有两条硬反馈护栏（反考古 `main.rs:713-721`、逐字重复命令 `:722-733`）分臂归因 |
| 建议变体形态 | 只加纠错一条为 `SWEV_INSTANCE_PROTOCOL_V1` + `--protocol-variant base\|v1` + `main.rs:775` 按旗标选中；配 af 原生 base 对照臂、代号线 bump（`计划/50-bench实测方案.md` §9.3）、af 侧新建计数器（冻结指纹+求和/在场双读法）、与①组候选②「验证引导收窄」分臂分账 |
| ⚠ **已知缺陷（三审 material issue 3）** | 移交件 §二「对账订正」（文件 L43-44、L151）称账本 tools sha256 `1133800324e0e6…`「以两种常见序列化都算不出（均得 `fce0c88a…`）」并令①组「用本件的值…**不要直接抄** `1133800324e0e6…`」—— **该订正为假**。**记账员亲跑复算（§14.6-⑪）**：两个 session 的 `json.dumps(tools)` 与 `json.dumps(tools, sort_keys=True)` 双双给出 `1133800324e0e644…`，`fce0c88a96eeece4…` **仅由 `ensure_ascii=False` 产生**。⇒ 移交件须订正（见 §14.8-C），否则会误导接收组怀疑一个正确的已登记指纹 |
| 接收方 | ①对齐组（af 改动管辖权在①）；②组不催办、不代改 af |

### 14.5 三审意见（node 33013，红队·三审 step-5，08:07:56–08:30:55，**未参与本循环任何环节**）

**`verdict = rejected`，3 条材料性 + 1 条已披露偏离。**（与前四循环的 `confirmed` 不同，本轮三审**否决**）

| # | 等级 | 意见摘要 | 记账员复核 |
|---|---|---|---|
| **I-1** | **材料性** | **深测数被记成 1/20，与最终产物 11/20 矛盾，且整个消融阶段跑在这个错数上**；错数来源 = 工作流模板 `${deep.combo_pass}/${deep.n}` 的渲染（脚本 L120）。后果：report#2、红队 deepCheck、run 结论模板与待写的 §14 全部携带错数，「**绝不可按 1/20 入账**」 | **独立复现**：三路账本 last-row = 11 过 / 9 败 / 20 题 / 0 T→F / 11 F→T；聚合与子域分账逐位一致（§14.6-①⑦） |
| **I-2** | **材料性** | **消融逻辑未按协议触发 + 冲突结论越级**：①`11 < 11` 为假 ⇒ 三项消融本不应跑，跑起来只因错数 1；工件中唯一被引的「运行所有者裁决」只覆盖题集，无工件证明存在覆盖触发条件的裁决；⇒ 工作流 `verified` 清单里「消融按协议触发条件执行」为假。②drop-B2 4/5 vs 组合 3/5 只是 n=5 单次采样的**净 +1**（discordant 13398 T/F、15629 T/F、11510 F/T）；§6.4(a) 判冲突须差 ≥2 净题、§11.3「±1 净题差不具旋钮可归性」、§11.2 噪声 56–105% 都不支持「负交互」；对 MX 的双向互抵恰用这套噪声逻辑豁免、对 B2 的 2:1 却亮 `conflict=true` = **双重标准** | **独立复现**：消融三账本 4/5、3/5、3/5（§14.6-⑧）；`dwf_event` sequence 49 运营者答复原文含「触发条件不变（组合深测 < 最佳单旋钮 11 才跑）」，**不仅未覆盖触发，反而重申了触发条件** |
| **I-3** | **材料性** | **移交件忠实性**：§二「对账订正」被实测否证——在 anolis 对其引用的两个 session 只读复算，两种常见序列化均得 `1133800324e0e644…`（=账本/上位移交件值），`fce0c88a…` 仅由 `ensure_ascii=False` 产生；该订正为假且主动误导接收组。另 minor：「af 默认 profile 是 mavis-m31f」措辞不严（`--profile` 必填无代码缺省，`main.rs:144`），实质（af 规范档位在 m31f 层）成立 | **独立复现**（§14.6-⑪，输出逐位在案）：`sha default = 1133800324e0e644`、`sha sort_keys = 1133800324e0e644`、`sha ascii_off = fce0c88a96eeece4` |
| **I-4** | 已披露偏离（限定消费，非诚实性违规） | §13.9-B6/§6.4 四臂 O/A/B/AB **未跑**（只产三旋钮组合臂×官方臂；统一题集上的**单点 B2 臂本轮从未跑**）；四项前置（A1/A3 落定、题集统一、base@m3、m31f 门）均未满足——已由 `knobs.json promised_disclosure` 与 `combo-deep-detail.json caveats` 如实披露；题集取 M1B20 ∪ MX7 = 20（MX7⊂M1B20 成立，避开禁令的 20+7 拼接，但**非协议建议的 V4-13**，且含 7 道域缘题）；**落点 `/tmp/mcode-tune-combo/` 而非协议指定的 `/tmp/mcode-tune-combo-M1B-B2/`**；**C1–C5 冲突观察工件未产** | **独立复现**：目录存在性（§14.6-④⑨）；`/tmp/mcode-tune-combo-M1B-B2/` 不存在（§14.6-⑨）；题集⊂关系（§14.6-②） |

**三审给出的入账前必改四条**（本账已全部照办，§14.2.3 / §14.3 / §14.4 / §14.8-C）：①深测按 11/20 入账并注明流程内曾被部分数 1/20 污染；②消融登记为「未按协议触发」，三项结果仅作 n=5 方向性读数，删除或降级「B2 负交互」标签；③订正移交件 §二 tools 指纹段；④如实区分「运行所有者裁决只覆盖题集、不覆盖触发条件」。

**三审对记录真实性的总判**：三审实测的全部数字（11/20、聚合值、子域分账、无 T→F、消融 4/5·3/5·3/5、SOURCES.sha256 十件、yaml 2 hunk、af 零改动、移交件 af 落点行号）**与本账亲跑复算逐位一致**，未发现编造。**否决的是流程纪律与消费边界（错数入账、未按协议触发的消融、移交件不实订正），不是数据真实性。**

### 14.6 记账员本轮亲跑复算（node 33017，2026-10-23 08:3x CST）

> 以下 11 项全部为本记账员本轮**亲自执行**的命令与其输出（命令可照抄复现）；凡未列于此的数字一律注明出处节点。

| # | 复算项 | 命令 | 结果 |
|---|---|---|---|
| ① | **组合深测两侧 last-row 复算（对三审 issue 1 的独立验证）** | python 解析 `/tmp/mcode-tune-combo/out|lane2|lane3/combo-b2-m1b-mx-m3/results.jsonl`（主 10 行 + lane2 8 行 + lane3 6 行）合并取 last-row | **20 题 / status 全 completed / pass 11 / fail 9 / T→F 0 / F→T 11**（13236、10973、11087、14011、14315、2905、3993、11510、8548、16597、17318）⇒ **流程内记录的 1/20 为错数，确认三审 issue 1** |
| ② | 官方侧与题集 | 同法解析 `official-snapshot-deep-20261023T050541Z/bench-official-mcode-m3/results.jsonl`（经符号链接） | 20 题**官方全 False ∧ completed**（pass=0/fail=20/缺 0）；`MX7 ⊂ 题集 = True`；题集 == M1B 深测 20 题集合 |
| ③ | 官方件指纹零漂移 | `sha256sum` 快照路径 / `/tmp/bench-official-mcode-{m3,m31f}` / `/home/pan-ding/bench-data/…` | m3 **四处同为 `43d7b1a0f49d70b…`**、m31f 同为 `5758019809bfc057…` ⇒ 零漂移 |
| ④ | 快照机制缺陷 | `ls -la official-snapshot-*/` | **五份快照内的 `bench-official-mcode-m3` 全是 symlink**（→ `/home/pan-ding/bench-data/…`，mtime 10-22 13:03）⇒ 「cp -a 冻结」表述不成立（官方臂已终局故本次无损）；确认红队 32944 issue 1 |
| ⑤ | 变体单点差异 | `diff base/run-one.sh combo-b2-m1b-mx/run-one.sh`；`diff` 三个消融变体 vs 组合 | base→combo：exec 行一处插入 `--prompt-mode coding --config …/config-combo-m1b.yaml --max-steps 120` + auth-sync 路径行；drop-B2 恰删 `--prompt-mode coding `、drop-M1B 恰删 `--config … `、drop-MX 恰删 `--max-steps 120` ⇒ **三个消融变体各恰摘一旋钮** |
| ⑥ | yaml 与源同源性 | `diff config-official-asof.yaml config-combo-m1b.yaml`；`sha256sum` 三方 | **恰 2 hunk**（51a52,60 补 thinking 块；99c108 `defaultEffort: default→high`）；官方件 / M1B 件 / combo 件 **三方同为 `f76cc62262b3944…`** |
| ⑦ | 行为双报 + 子域分账 | python 重算 `combo-deep-detail.json` 的 20 条 `per_task` | 官方 Σ(26/57/17/594) 在场 19/14、组合 Σ(**18/44/14/596**) 在场 **13/10**（与文件 `behavior_sum`/`behavior_presence` **逐位一致**）；**V4-13 n=13 净 +7、MX7 n=7 净 +4、域缘 n=7 净 +4** |
| ⑧ | 消融三臂 last-row 复算 | python 解析 ab1/ab2、ab3/ab4、ab5/ab6 六本账本 | drop-B2(M1B+MX) **4/5**（13236 T、13398 T、15629 T、11510 F、16597 T）；drop-M1B(B2+MX) **3/5**；drop-MX(B2+M1B) **3/5**；组合同 5 题 **3/5**（13236 T、13398 F、15629 F、11510 T、16597 T）⇒ 与三份 detail 一致；M1B 单点同 5 题 3/5（13398 non-judged）为噪声带旁证 |
| ⑨ | 补丁卫生全量复检 + 落点核查 | `find` 35 份 `patch.diff` + `grep -cE '^diff --git a/(prompt\.txt\|mcode\.log\|AGENTS\.md\|hints\.txt\|\.meta/)'` | **35 份（组合 20 + 三消融 15）禁前缀命中 0**；`ls /tmp/mcode-tune-combo-M1B-B2` → **不存在** ⇒ 确认三审 issue 4 的落点偏离；`out/` 下**仅 `combo-b2-m1b-mx-m3` 一个臂目录，无 m31f 组合臂** |
| ⑩ | af 零改动 | `git -C af status --porcelain` / `rev-parse HEAD` / `branch --show-current` | 仅 5 行未跟踪 `poc/poc-kernelrun/*`；HEAD `94cd1923c348…`；分支 `guardrail-fix2` ⇒ **本组 af 零改动成立** |
| ⑪ | **移交件 tools 指纹独立复算（对三审 issue 3 的独立验证）** | `ssh anolis` 只读 python 解析 `2026/10/21/20-43-00-962`(coding) 与 `20-49-43-738`(tui) 的 `llm-call.json`，对 `tools` 分别取 `json.dumps` / `sort_keys=True` / `ensure_ascii=False` 三种序列化 | 两侧 **默认与 sort_keys 双双 = `1133800324e0e644…`、`ensure_ascii=False` = `fce0c88a96eeece4…`**；tools 均 18 个；coding systemPrompt 17219 字符/17327 字节 sha16 `2dd03a811f43834c`、tui 15655/15763 `17e3b1e32ccd9bc5`；model/thinkingLevel/maxTokens/api/provider/outputRevisionInstruction 全同 ⇒ **移交件「对账订正」为假，确认三审 issue 3** |

### 14.7 本轮未跑 / 未复核 / 本节点未独立复算（如实登记）

| # | 项 | 说明 |
|---|---|---|
| 1 | **m31f 回归抽查准入门** | **组合臂与三消融臂均 0 跑**（`/tmp/mcode-tune-combo/**/out/` 下只有 `*-m3` 臂目录）→ **本节结论不含 m31f 不退化证据，不得消费为「可回灌/已采纳」** |
| 2 | **base 变体臂@m3（无旋钮对照）** | 仍未补：`/tmp/mcode-tune-implementer/out/base-m3/results.jsonl` **仍仅 1 行**（`wc -l` 亲验）→ 20 题/5 题的采样噪声不可剥离 |
| 3 | **§13.9-B6 四臂对比（O / M1B / B2 / AB）** | 未跑；**统一题集上的单点 B2 臂本轮从未跑过** → 「组合是否优于任一单点」只有对 M1B 的横向对照（§14.2.2 末段），**对 B2 无同题集对照** |
| 4 | **C1–C5 冲突观察工件** | 未产（四臂 `mcode.log`/`patch.diff`/`eval.log`/`judge.json` 分类清单） |
| 5 | **全池 120 题 m31f 采纳线**（§6.3(c) 净≥4） | 未测（承接 §13.8-2） |
| 6 | **B2 两侧通过率/行为三元组** | 本轮**未复算**（引用 §12.2/§12.4 已复算值） |
| 7 | **轨迹人工抽样核对** | 未做（20 题仅计数器双读法 + 判分字段核对） |
| 8 | **judge.json 0 字节首判的两处（11087 冒烟、4604 深测）的字节级取证** | 未做（登记自 `combo-deep-detail.json caveats` 与节点 32953 evidence） |
| 9 | **`/data 16G` 预检数值** | 不可从落盘工件复算（红队 32944 issue 3 同判；`verifier_note` 仅记 `disk_ok=True`） |
| 10 | **mcode `work` 第三档 / af 侧任何变体** | 未跑；af 零改动 |
| 11 | **run 最终结论串与 artifact 表的更正** | **未做**：report 32943 的 `1/20` 与脚本 L130 渲染的结论串**仍是错数**；artifact「调优组·第五循环（组合）进度」表内 `组合深测` 行亦为 `1/20`。**本账不代改运行中 run 的产物**，更正方式见 §14.8-B14 |

### 14.8 下一循环动作（可直接派工）

#### A. 阻塞项（须先由运行所有者/厂长裁决）

| # | 事项 | 依据 |
|---|---|---|
| **A8** | **组合采纳 or 回退的裁决**（本轮新增最高优先）：终版读数 **组合 11/20 = M1B 单点 11/20（翻面集仅差 1 题：组合多 8548、少 7205）**，按 §6.4(a)「组合 ≈ 单点（差 ≤1）→ 不叠加收益，取更简单者」⇒ **当前证据不支持采纳组合**，倾向「**回退到 M1B 单点**」。但此裁决须与 A1（域重定义）一并落定，因为组合的分账是「V4-13 净 +7 ＋ 域缘 +4」，与 M1B 单点的「V4-13 净 +8 ＋ 域缘 +3」在承诺域内**单点更优** | §14.2.2；§6.4(a)；A1 |
| **A9** | **干净官方线重跑是否携带组合 —— 裁决权留给运营者**（本节点不代决）：第四/五循环的全部改造臂结论都建立在 `m3 results.jsonl sha256 43d7b1a0…` 这一份官方侧读数上（快照=live=`/home/pan-ding/bench-data/…`）。若干净官方线重跑，**须先裁决：重跑后的官方基线是否携带组合旋钮**（携带 ⇒ 现有全部「官方 0/N」锚点作废、单点与组合读数须整体重算；不携带 ⇒ 现有锚点可沿用，但重跑差异本身会污染对照）。**本项必须由运营者拍板**，记账员只登记两条路各自的后果 | §14.6-③；§13.8-13；本节点 ask 原文「裁决留给运营者」 |
| **A10** | **A1 承接**：M1B 域重定义仍未裁决（§13.9-A1），**本轮组合臂同题集再触同一条**（题集含 7 道域缘题），裁决前 §12.5「承诺域定死」不得静默沿用 | 三审 33013 issue 4；§13.9-A1 |
| **A11** | **A3 承接**：MX 是否降级为「非退化保险 + rc=7 记账路径证据」仍未裁决；本轮 `rc7_truncations=0` 与红队 32935 前瞻（combo run asst=52 已达 120 上限 43%）说明**该旋钮在改造臂高 turns 区仍可能真实咬合** | §13.9-A3；§14.1 红队 issue 1 |
| **A12** | **「运行所有者裁决」的效力边界登记**：本轮唯一一次裁决（`dwfq-0fe55ff6-1`）**只覆盖消融题集**，未覆盖触发条件；账本与后续节点引用时**禁**把它当「消融已获授权」的依据 | `dwf_event` seq 48/49；三审 33013 issue 2 |

#### B. 可立即做（不需裁决）

| # | 事项 | 落点 / 判据 |
|---|---|---|
| **B12** | **补 base 变体臂@m3（同 20 题 + 消融 5 题）**：剥离采样噪声，这是 A8 裁决「组合≈单点」是噪声还是真同值的**唯一解法** | §14.7-2；§13.9-B8 |
| **B13** | **补 §6.4 四臂对比（O / M1B / B2 / AB）**，统一取 **V4-13**（A1 落定后），补齐 A8 缺的「B2 同题集对照」；C1–C5 冲突观察工件按 §6.4(b) 产出 | §13.9-B6；§14.7-3/4 |
| **B14** | **更正运行中 run 的错数产物**：report 32943「组合深测 0/20→1/20」与 artifact 表同行、以及脚本 L130 渲染的结论串，须以 11/20 覆盖；**本节点不代改运行中 run 的产物**（不可写回已完成节点），由运行所有者以 amend 或下一循环声明方式更正 | §14.2.3；§14.7-11 |
| **B15** | **组合臂 m31f 回归抽查准入门**（组合 + base@m31f 同题）：三判据同 §13.9-B7（resolved 不跌 / 行为不恶化（wall+asst_turns 求和涨幅 ≤25%，阈值预注册）/ 终稿非空） | §13.9-B7；§14.7-1 |
| **B16** | **快照器整改**：①`cp -a` 前先 `readlink -f` 解析源路径，否则复制的是链接不是数据（或改 `cp -aL`）；②`as-of.txt` 增加 `snapshot_kind: real-copy\|symlink` 字段。**本轮五份快照全是 symlink**，官方臂已终局故未造成损失，但复飞时会静默漂移 | §14.6-④；红队 32944 issue 1 |
| **B17** | **工作流模板整改**：深测 ask 必须**等批次终态**再返回 `combo_pass`（本轮 19/20 新题未判即返回，直接污染 report/红队/结论串/消融触发）；建议在脚本里加终态闸（账本行数 == 题集大小 ∧ 每行 last-row 已判） | §14.2.3；三审 33013 issue 1 |
| **B18** | **消融触发判据整改**：把 `bestSingle` 从脚本硬编码 `11` 改为**读单点实测值**；并明确「消融只在 `组合 < 最佳单点` 且差 ≥2 净题时才有解释力」，±1 只登记为方向性读数 | §14.3；三审 33013 issue 2 |
| **B19** | **消融臂去噪**：若 A8 裁决要求保留消融，须在**同题集**上补 base@m3 臂与每个单点臂（drop-B2 之外还需 B2 单点、M1B 单点、MX 单点在同 5 题的读数），否则「4/5 vs 3/5」不可归因 | §14.3；§14.7-3 |
| **B20** | **非咬合证据登记**：`rc7_truncations=0`（组合 20 题）＋ 官方池 asst max=65<120 ＋ 消融 drop-MX 与组合 pass 相同（3/5）→ 记入 `knobs.json promised_disclosure` 作为 MX「恒不咬合」的**本轮实测证据**；同时按红队 32935 前瞻标注「改造臂高 turns 区（asst=52 已见）可能真实咬合」 | §14.2.2 caveats③；§14.3 |

#### C. 文档更正清单（随下一次写作一并改）

| # | 更正 | 落点 |
|---|---|---|
| C17 | **移交件 §二「对账订正」为假**：tools sha256 **恢复 `1133800324e0e644…` 为已登记值**，删「两种序列化都算不出」与「①组不要直接抄 `1133800324e0e6…`」两句；`fce0c88a…` 标注为「仅 `ensure_ascii=False` 序列化下的值」。L43、L151 两处同改 | `计划/研究组/B2提示风格-移交对齐组.md` §二 L43-44、§六 L151 |
| C18 | 移交件「af 默认 profile 是 mavis-m31f（`main.rs:165`）」→ 改为「`--profile` 为必填无代码缺省（`main.rs:144`）；`mavis-m31f` 是文档首列/首个 match 臂」，实质（af 规范档位在 m31f 层）不变 | 同上；三审 33013 issue 3 minor |
| C19 | 五份 `as-of.txt` 的「cp -a 先于起批」表述 → 改为「**sha 复验锁定**」（快照内为 symlink，非冻结拷贝） | `/tmp/mcode-tune-combo/official-snapshot-*/as-of.txt` |
| C20 | §13.9-A2 的分账口径**续用到组合臂**：写作一律「V4-13 净 +7 ＋ 域缘扩测净 +4」，**禁**写「承诺域 20 题净 +11」 | 本节 §14.2.2 |
| C21 | 第四循环 §13.9-B6 的组合落点 `/tmp/mcode-tune-combo-M1B-B2/` 与本轮实际落点 `/tmp/mcode-tune-combo/` 的差异登记在案（后者为准，前者作废） | §13.9-B6；本节 §14.5 issue 4 |
| C22 | 「消融题集」在 §12/§13 全文 **grep 0 命中**（本轮 escalate 已证）→ §14.3 已给出唯一定义（V4-13 ∩ MX-7 = 5 题）；下一循环引用时须引本节，不得再引「§12 消融题集」 | §14.3；`dwf_event` seq 48 |

#### D. 移交件（回灌 → ①对齐组）

- **本轮新增已出**：`计划/研究组/B2提示风格-移交对齐组.md`（21,386B，04:35 落盘）—— 把 B2 的「人格句 / 收尾自包含 / 纠错风格」三件逐条对应到 af 提示装配层落点，含每条机制证据指针、建议变体形态、风险 6+7 条、纪律前提 P1-P3。**三件里只有「纠错风格」值得①组考虑立项**（证据等级最弱），另两件**不建议立项**（无可搬语义 / 作用面不存在）。
- **⚠ 移交前须先落 C17**：该件 §二含一处**不实「对账订正」**（见 §14.4），若原样交给①组会误导其怀疑一个正确的已登记指纹。
- **上位件**：`计划/研究组/B2回灌-移交①对齐组-20261023.md`（§13.9-D）。
- **接收方**：①对齐组（af 改动管辖权在①）；**②组不催办、不代改 af**。

### 14.9 本节与第五循环进度表对照（供快速核对）

| 行 | 进度表登记 | 本账订正 | 依据 |
|---|---|---|---|
| 组合变体 | 冒烟过 | **维持** | §14.1 |
| **组合深测** | **组合有效 · official=0/20 · combo=1/20** | **❌ 订正为 official=0/20 · combo=11/20（净 +11，0 T→F，p=0.0009765625）** | §14.6-① 亲跑复算；三审 issue 1 |
| 消融-knob①[B2] | 无冲突 · 0/5（中间态） | **订正 4/5**（drop-B2）；且整体登记为「**未按协议触发**」，只作 n=5 方向性读数 | §14.6-⑧；脚本 L103-104；三审 issue 2 |
| 消融-knob②[M1B] | 无冲突 · 3/5 | **维持 3/5**（同降级） | §14.6-⑧ |
| 消融-knob③[MX] | 无冲突 · 3/5 | **维持 3/5**（同降级） | §14.6-⑧ |
| 三审 | — | **rejected（3 材料性）** | §14.5 |

---

### 变更记录

| 时间 | 记账人 | 动作 |
|---|---|---|
| 2026-10-22 03:00 CST | 状态记账员（MiniMax-M3.1-Flash） | 首建本账：写入改造面 28 旋钮、红队 8 条引证修正、5 条候选红队逐条结论、0 速筛实况与官方侧逐题数字、终审 5 条意见、下一循环动作（20 题深测设计 + ≥3pp→净题数换算 + 组合/冲突观察方案）、口径防错清单、未覆盖项登记 |
| 2026-10-22 05:50 CST | 候选起草·GLM | 新增 §10：筛前快照（20261021T214505Z）、m3 失败集 22→24、24 败逐题 mcode.log 归因表、行为域预注册正则冻结版与全臂实测计数、3 条双轨候选（G1 effort-high×口径域 17 题 / G2 prompt-mode-coding×自证失真域 15 题 / G3 behavior×PASS_CLAIM 行为域 69 题）与主动排除清单、死路登记（PENDING n=1、越权改测试 n=0、纯 P2P n=2）、judge.json 空文件数据质量旗标 |
| 2026-10-22 08:08 CST | 状态记账员（MiniMax-M3.1-Flash） | 新增 §11 第二循环完整账（run dwfrun-1eedf1ee）：机制件 8 条路径 + 机制件红队 5 issues；三探针结论（--effort high / --prompt-mode coding = true，--max-steps 120 = false 但真旋钮条件生效）+ 探针红队 4 非否决；候选红队逐条（M1 confirmed 5 issues / G2 rejected 4 / G3 rejected 4 / B2 confirmed 4 = 唯一 survivor）；速筛两侧 0/5→1/5（net +1，唯一翻面 sympy-16597）+ 双报四读法逐题表 + 快照 as-of 07:07:53；终审 rejected 5 issues + 4 条整改；下一循环动作 8 项 + 20 题深测设计（m3fail 锚判据位表实测 18/13 题、behavior 锚域 85 题实测与 19 题净分集、m31f 回归抽查锚设计）；写回 §7 口径新增 11–20。**本次亲跑复算**：B2 快照 m3/m31f last-row、改造臂 5 行 results、sympy-16597 judge.json、M1 失败 mcode.log、behave_count.py sha256、anolis runs 目录（回归抽查零执行的实证）、两侧 10 session 行为三元组、官方 m3 全量 119 session 行为基线（落盘 /tmp/recompute_behave_official_m3.json）、G1 五判据 24 败逐题位表。 |
| 2026-10-22 08:26 CST | 改造实施员（GLM-5.3-Flash） | **新增 §11.10 整改销账**（§11.5 末四条整改的文档面，逐条标注终审 issue 1–4）：①（issue 1）m31f 回归抽查显式登记为本循环**待执行准入项**（0 跑，anolis runs/ 7 变体目录均空 08:2x 亲验，B2 深测被其阻塞）；②（issue 2）§11.10-B 行为指标**定义表**（reread_paths/max_rereads/consec/asst_turns 带 behave_count.py 行号）+ B2 速筛 5 题**逐题明细**（含 asst_turns）+ **求和/在场两种读法并列**，§11.4(2) 加禁裸标量指针；③（issue 3）§11.3 B2 条目追加 **Survivor caveats** 4 条（n=1 / 噪声同级 / 16597 行为 1→1 无因果链 / 准入门绑定）；④（issue 4）§2 旋钮表行 2 补注 + §7 新增条 11（effort×m3fail=硬禁止）。**本次亲跑复算**：冻结 behave_count.py（本机+anolis 双侧 sha256=e667c13e… 一致）在 10 个 session（官方 m3 5 + 改造 b2 5，work 路径 grep 定位各恰 1 session）重算，与红队复算官方 [1,1,1,1,1]/改造 [0,1,3,1,0] 及 §11.8-B 记录值逐位一致；m1 拒绝原文 cat 亲验；m31f 快照 5 题 last-row（16597=True wall=700033）亲算。整改①执行面未做，留后续 phase。 |
| 2026-10-22 10:07 CST | 改造实施员（GLM-5.3-Flash） | **行为基线全量落盘（§11.7 动作 4 销账，新增 §11.10-F）**：anolis sessions 全树扫出改造臂（命名空间 `/data/bench/mcode-tune/runs/`）**全部 20 个 session**，冻结 `behave_count.py`（双侧 sha256 `e667c13e…` 一致）anolis 亲跑 **20/20 rc=0**，逐题 JSON + as-of + sha256 落 `/tmp/mcode-tune-B2-behavior-baseline/`（4 件：reform-arm-behavior-baseline.json `017e2b70…` / raw-from-anolis.json `f290db42…` / official-m3-full-baseline.json `e586b2cc…` = 官方 119 题基线逐字节副本 / as-of.txt）。**发现并如实登记**：①10-22 UTC 5 条 = `b2-prompt-mode-coding @m31f` × 速筛同 5 题（08:33–09:25 CST）为本账 08:08 后后续 phase 新跑（`out/b2-prompt-mode-coding-m31f/` 已在盘），本落盘仅作 last-row 关联参考；②`m1-effort-high-m3` 臂 0 session（CLI 拒绝先于任何 LLM 调用）；③messages.jsonl 原件未归档（钉指纹非字节，§11.10-F 披露边界）。B2 速筛 5 题改造侧三元组与 §11.10-B 表逐位一致（交互校验）。 |
| 2026-10-22 13:2x CST | 状态记账员（MiniMax-M3.1-Flash-Preview，node 32690） | **新增 §12 第三循环完整账**（run dwfrun-1c3d5ebc，11 个 ask 节点 32439→32690 + 5 个 report 的角色/模型/时段表）；销账与重审（32439 文档面销账 → **32446 红队·重审 confirmed / 0 issues**，时序 08:30:00 完成后才派发回归）；**B2 m31f 回归抽查**（32451 `ok=true`：resolved 4→4、在场行为 3→3 持平但构成位移、Σreread 7→7 / Σmax 23→17 / Σconsec 5→3，含 5 题逐题明细；32495 红队 confirmed 6 issues = ok=true 读法依赖 + **base 配对臂 0 跑/题集 5/19/对照槽 0/20 的 scope 偏差** + sympy-16597 T→F 阻塞场景 + 10999 F→T 噪声疑似）；**行为基线落盘**（32501，4 件 sha256 已复验，官方基线 canonical 与目录副本同为 e586b2cc…）；**19 题深测**（32513：官方 0/19 vs 改造 9/19 净 +9、McNemar 精确 p=0.00390625、3pp×19=0.57→局部门槛净≥1、Σreread 26→15 / Σmax 57→35 / Σconsec 17→9 / 在场 19→10、19 题逐题明细含 data_provenance、机制拆分 6 改善 + **3 题非行为路径待定位**、护栏(d) 3 题真实少读；32627 红队 confirmed 6 issues = 47.4% 子集不得读作 47pp + 门状态高估 + recount-guardrail.py 路径不存在）；**新候选 2 条**（32636 起草 M1B config 级 thinking×G1 V4 域 13 / MX --max-steps 120 护栏×失控域 7；32661 红队 confirmed 5 issues，含 **V4-13 ≠ 账本-13** 与冒烟判据⑥锚点错位）；**三审**（32674 **confirmed 5 issues**：门仅部分放电须限定消费、不得把 B2 写成准入完整的 survivor、采纳线未测 + 4 条 minor/info）；下一循环动作 A 阻塞 3 项（scope 与 16597 回归裁决 / 全池采纳线 / 扩题池）+ B 可做 5 项 + C 文档更正 6 项。**本次亲跑复算（13 项，§12.7）**：run/节点元信息（db.sqlite 只读）；回归两侧 last-row 5 题 resolved+wall 与官方全量 119 判 114/5 账；回归**两侧 10 session 行为三元组在 anolis 重跑**（官方 1/2/1/11·4/6/1/48·2/15/3/60·0/0/0/81·0/0/0/85；改造 0/0/0/15·2/3/1/33·3/11/1/100·0/0/0/92·2/3/1/69，逐位一致）；深测 19 题 resolved/wall/行为对快照与账本**零处不符**，改造侧 19 session 行为**独立重跑 19/19 逐位一致**；`g1_recount_v3.py` 复跑 V4=13 成员逐题一致；MX 域 7 由 canonical 基线 asst_turns 与 m3 completed 失败集求交复算一致（median 26/p90 45/max 65、wall≥1400s 为 0）；行为基线四件 sha256 与 as-of.txt 登记一致；红队 minor 取证（recount-guardrail.py 不存在、base-m31f 仅 4 行、B2 两臂账本 19/5 行）。**未做/未跑据实登记（§12.8）**：不退化对照槽 20 题 0 跑、§11.8-C 完整门剩余 14 净分题 + base 配对臂敞开、§6.3(c) 全池采纳线未测、非行为机制路径未定位、两新候选冒烟/门/速筛全部 0 跑、19 点中 5 点复用速筛/冒烟行。 |
| 2026-10-23 03:0x CST | 状态记账员（MiniMax-M3.1-Flash-Preview，node 32902） | **新增 §13 第四循环完整账**（run `dwfrun-26c949a2-df21-46af-a61d-69035842cf04`「研究组②调优组·第四循环·提速版」，`resumed_from`=被 cancelled 的 `dwfrun-dc7a836d`；22 节点，ask 序列 32753 候选起草 → 32754 回灌评估 → 32755/32756 实施员甲乙 → 32795 回灌红队复核 → 32799/32800 速筛执行员甲乙 → 32870/32875 速筛红队 → 32880/32881 深测甲乙 → 32888/32893 深测红队 → 32898 三审 → 32902 本节点；6 个 report 进度行）。**冒烟**：M1B（甲，32755）单点差异=`--config` 臂级 yaml（全文无 `--effort`）、yaml 恰 2 hunk、inject=[]、m3 11087 过（371,595ms，thinkingLevel=high 穿透）、**m31f 4604 交付时仍在飞**（第 5 轮 17:39:36 fail-closed，7 行 preflight_failed）→ 17:58:52 到终态（completed/False/221,173ms，记账员亲查账本 8 行）；MX（乙，32756）单点差异=`--max-steps 120`、m3 11087 过（290,624ms）、**rc=7→judge→reward 记账路径两腿兑现**（3993：limit_exceeded 1 行 + patch 3692B + judge f2p 0/2 p2p 2398/0；13398 无 patch → reward=None）。**速筛（双报 + 快照路径）**：M1B 官方 0/5→改造 2/5（快照 `official-snapshot-screen` as-of 19:20:04；Σreread 7→3、在场 4→3，10973 翻面非行为介导），MX 官方 0/5→改造 2/5（快照 `official-snapshot-screen-20261022T192136Z` as-of 19:21:54；Σreread 6→3、在场 5→3、Σmax 22→**11**）。**深测**：M1B 官方 0/20→改造 11/20（+1 non-judged 13398，净 +11 无 T→F，p=2×2⁻¹¹=0.0009765625；快照 `official-snapshot-deep` as-of 00:38:09；**分账 = V4-13 净 +8 + 域缘扩测净 +3**，三审 issue 1 要求），MX 官方 0/7→改造 2/7（净 +2，p=0.5，旋钮恒不咬合；快照 `official-snapshot-deep-20261023T003821Z` as-of 00:38:21）。**B2 回灌评估**（32754，红队 32795 `confirmed`）：`af_equivalent=部分（partial）`——af 有装配层对应物、无旋钮对应物，旋钮语义在 af 判分链下**结构性惰性**（完成判定只认工具输出首行，判分只吃 task_json/eval.log/agent.diff）；**结论=B2 不是可回灌 af 的旋钮，af 动作只能由①对齐组以 af 原生候选走变体周期**；红队材料性更正：评估的「19 臂 deliver-assets 0 命中」腿**不可复现且被反例否证**（coding 臂 8/25 末条含 `<deliver-assets>`）→ 机制叙事须改写为「mcode 侧约 1/3 run 触发、af 侧结构性惰性」，底结论不变且更强。**三审**（32898 `confirmed`，2 材料性 + 9 minor/info）：①M1B 深测题集偏离 §12.5 定死承诺域、违反 §6.3(a) 字面，须分账并由运行所有者裁决是否接受域重定义 ②回灌经验腿不成立 ③8 条 minor（口径混用、Σmax 13→11、preflight 8→7、11087 双 session、as-of 模板复发、近域带措辞、wall provenance、patch 卫生不可复验）+ 1 条 informational（`af-wt-align2` 属①组在飞，非本组改动）。**下一循环动作**：A 阻塞 7 项（**A1 M1B 域重定义裁决**、A2 结论分账口径固化、A3 MX 是否降级为「非退化保险+rc=7 记账路径」、A4–A6 承接 B2 scope/全池采纳线/扩题池、A7 组合准入）+ B 可做 6 项（**B6 组合测试协议触发但须先过 4 项前置**：A1/A3 落定、题集统一（不得把 M1B 20 题与 MX 7 题拼接）、补 base@m3、补 m31f 门；臂=官方/M1B/B2/M1B×B2，判定与 C1–C5 冲突观察按 §6.4(a)(b)，落点 `/tmp/mcode-tune-combo-M1B-B2/`）+ C 文档更正 10 项（C7–C16）+ **D 移交件已出**：`计划/研究组/B2回灌-移交①对齐组-20261023.md`（回灌建议走①，移交件含机制语义事实、af 对应物与惰性代码依据、不可移植理由 7 条、①组立项的正确候选形态、前置条件 A1/A2/B4、边界声明）。**本次亲跑复算（15 项，§13.7）**：四份快照 as-of 亲读；官方 m3 sha256 `43d7b1a0…` 三处逐字节一致 + 深/筛产物 6 个 sha256；两变体 `run-one.sh` diff（M1B 恰 2 hunk 无 `--effort`、MX 恰 1 行）；M1B yaml diff 恰 2 hunk；`g1_recount_v3.py` 复跑 V1=17/V2=15/V3=15/V4=13 成员逐题一致；M1B 深测 20 行 last-row 两侧复算（0/20→11/20、无 T→F、翻面 11 题名单）；**V4-13 分账复算（V4∩深测 13 题已判 12 通过 8 → 净 +8；域缘 7 题翻面 3 → 净 +3）**；行为聚合 19 对/全 20 两口径复算（复现 §2 口径混用）；MX 速筛聚合算术复算（Σmax 13→11）；M1B 速筛账本 21 行=14 completed+7 preflight_failed；MX 深测双账本 last-row 复算 2/7；MX rc=7 两腿本地工件复验；M1B m31f 冒烟终态复验（8 行=1 completed+7 preflight_failed）；af 零改动复验（5 行未跟踪 poc/、HEAD 94cd1923、12 worktree）；`base-m3` 仅 1 行（无旋钮对照缺失）。**未做/未跑据实登记（§13.8）**：两候选 m31f 回归抽查 0 跑、全池 120 题 m31f 采纳线未测、base 变体臂 0 跑、轨迹人工抽样未做、M1B 深测 15 份 patch 卫生与 13398 run 目录不可复验、rc=70 语义未独立验证、**B2 两侧通过率/行为三元组本轮未复算**（引用 §12.2/§12.4）、回灌 19 臂 mcode.log 不可复现、af 侧零执行、组合测试未跑、官方侧 judge p2p/tests_collected 不可得、messages.jsonl 原件仍未归档。 |
| 2026-10-23 08:3x CST | 状态记账员（MiniMax-M3.1-Flash-Preview，node 33017） | **新增 §14 第五循环完整账**（run `dwfrun-0fe55ff6-f057-4a7d-bfb8-2d1321e1274b`「研究组②调优组·第五循环（组合）」，`resumed_from=None`，status=`running`，spent_tokens=46,866,871，script_hash `0a5555ec273ada83…`，169 行 4 phase；11 ask 节点 32920→33017 + 5 report：32920 移交整理员(MM) 04:32:31→04:35:36、32921 组合实施员(GLM) 04:32:31→04:51:11、32935 红队·组合审查(S5) 04:51:11→05:00:55、32939 深测执行员 05:00:56→05:14:07、32944 红队·深测审查(S5) 05:14:07→05:22:15、32948 消融① 05:22:16→05:32:38、32953 消融② 05:32:38→07:26:23、33005 消融③ 07:26:23→08:07:56、33013 红队·三审(S5) 08:07:56→08:30:55、33017 本节点 08:30:55→；escalate `dwfq-0fe55ff6-1`）。**组合变体**（32921）：`/tmp/mcode-tune-combo/variants/combo-b2-m1b-mx`（run-one sha256 `b5bcb568…`）= knob①[B2] `--prompt-mode coding` + knob②[M1B] `--config config-combo-m1b.yaml`（yaml sha `f76cc622…`，与 M1B 件逐字节同源，对官方 config 恰 2 hunk，全文无 `--effort`）+ knob③[MX] `--max-steps 120`；inject=[]、exclude 标记块 exclude:8/9、git status 仅 deletion.py；冒烟 django-11087@m3 wall=301,954ms completed/True（judge f2p 1/0 p2p 41/0，patch 3,913B，**首判 judge.json 0 字节→judge_error→late-judge 恢复**，账本 2 行 last-row=True）；三指纹齐全（coding 头 17208 字符/17316B sha16 `1ce99738…`；thinkingLevel=high；max-steps 请求层无指纹→改用 cmdline pid3351171+CLI 接受+rc=7 机制族三层举证）；**截断层 assistant=52<120、limit_exceeded=0 → knob③ 本轮全程未咬合**；0 容器贡献（他线 4-6 afbench 让行）；af 零改动（HEAD 94cd1923、guardrail-fix2、5 行未跟踪 poc/）。红队 32935 **`confirmed` 4 条**（1 info 前瞻：combo run asst=52 已达 120 上限 43%、「恒不咬合」只是相对官方池分布的性质，C4 截断冲突须作活观察项；3 minor：systemPrompt 非跨 run 字节稳定、`/data 16G` 不可复算、题域 vs run 轨迹勿混用）。**组合深测**（32939，红队 32944 `confirmed` 4 issues）：题集 20 = M1B20 ∪ MX7（**MX7⊂M1B20 亲算成立、union 恒等**，未犯 §13.9-B6 拼接禁令）；官方快照 `/tmp/mcode-tune-combo/official-snapshot-deep-20261023T050541Z` as-of 05:05:41 先于起批 05:08，m3 sha `43d7b1a0…`/m31f `57580198…` 零漂移；3 路 nohup（lane1 7 题 pid1283542 / lane2 6 / lane3 6 + 11087 冒烟复用）。**双报（记账员亲跑复算）**：**官方 0/20 → 组合 11/20、净 +11、T→F=0、F→T 11、McNemar 精确双尾 p=2×2⁻¹¹=0.0009765625**；行为官方 Σ(26/57/17/594) 在场 19/14 → 组合 Σ(**18/44/14/596**) 在场 **13/10**；**域分账 = V4-13 净 +7 ＋ 域缘扩测净 +4**（MX7 净 +4），**禁写「承诺域 20 题净 +11」**；**翻面集与 M1B 单点同数不同集**（组合多 sphinx-8548、M1B 多 pytest-7205，其余 10 题重合）⇒ 按 §6.4(a)「组合≈单点→不叠加收益、取更简单者」本轮组合未产生可归因增益。**⚠ 错数污染链（§14.2.3）**：深测 ask 在 19/20 新题未终态时即返回 `combo_pass=1`（消融 05:27 起批 vs 深测三路 06:58/07:02/07:03 才退出），致 report 32943「1/20」、脚本 L130 结论串、以及**整个消融阶段跑在错数上**；**本账一律按 11/20 落账，1/20 只作流程缺陷证据留档**。**消融**（32948/32953/33005）：题集 = V4-13 ∩ MX-7 = {13236,13398,15629,11510,16597}（运营者 2026-10-23 裁决，`dwf_event` seq 48/49；**该裁决只覆盖题集、并重申「组合深测 < 最佳单旋钮 11 才跑」的触发条件**）；四臂同题集（**记账员亲跑 last-row**）官方 0/5、组合 3/5、drop-B2(M1B+MX) **4/5**、drop-M1B(B2+MX) 3/5、drop-MX(B2+M1B) 3/5、M1B 单点同 5 题 3/5（13398 non-judged）；**但脚本 L103 `bestSingle=11`、L104 `deep.combo_pass < bestSingle` ⇒ 真实 11<11 为假、三项消融未按协议触发**；且 drop-B2 仅高 +1 净题（discordant 13398 T/F、15629 T/F、11510 F/T），**低于 §6.4(a)「判冲突须差≥2 净题」门槛、落在 §11.3「±1 无旋钮可归性」与 §11.2 噪声 56–105% 带内**，对 MX 的 2:1 豁免而对 B2 的 2:1 亮 conflict=双重标准 ⇒ **本账不写「knob①[B2] 负交互」**，只记「n=5 方向性读数、与组合≈M1B 单点同向」。**移交件**（32920）：`计划/研究组/B2提示风格-移交对齐组.md`（21,386B，04:35，零代码改动/零容器）——人格句→af `main.rs:543 SWEV_SYSTEM_PROMPT` **无可搬语义不建议立项**、收尾自包含→instance 协议 `main.rs:548-566` **作用面不存在不建议立项**、纠错风格→同一协议 **唯一可立项但证据等级最弱**（须与 af 反考古 `main.rs:713-721`、逐字重复命令 `:722-733` 分臂归因）；建议形态 `SWEV_INSTANCE_PROTOCOL_V1` + `--protocol-variant base|v1` + `main.rs:775` 按旗标选中。**三审**（33013 step-5，**`verdict = rejected`**，3 材料性 + 1 已披露偏离）：①**深测数 1/20 与最终 11/20 矛盾且消融跑在错数上**，「绝不可按 1/20 入账」 ②**消融未按协议触发 + 冲突结论越级**（`11<11` 为假；唯一裁决只覆盖题集；±1 净题不具旋钮可归性）③**移交件忠实性**：「对账订正」称 tools sha `1133800324e0e6…` 算不出为假——实为 `json.dumps` 默认/sort_keys 均得该值、`fce0c88a…` 仅 `ensure_ascii=False` ④**已披露协议偏离**：四臂 O/A/B/AB 未跑（统一题集上单点 B2 臂从未跑）、四项前置均未满足、题集非协议建议的 V4-13 且含 7 道域缘题、**落点 `/tmp/mcode-tune-combo/` 而非协议指定 `/tmp/mcode-tune-combo-M1B-B2/`**、C1–C5 冲突观察工件未产。三审的**全部数字与本账亲跑逐位一致**（未发现编造），否决的是流程纪律与消费边界，非数据真实性。**下一循环动作**：A 阻塞 5 项（**A8 组合采纳 or 回退裁决——组合 11/20 = M1B 单点 11/20、同数不同集，按 §6.4(a) 当前证据不支持采纳、倾向回退到 M1B 单点，须与 A1 一并落定**；**A9 干净官方线重跑是否携带组合旋钮——裁决权留给运营者**，本节点只登记两条路各自后果：携带则现有全部「官方 0/N」锚点作废、单点与组合读数须整体重算；不携带则锚点可沿用但重跑差异本身污染对照；A10 A1 承接域重定义；A11 A3 承接 MX 定性 + 高 turns 区可能真实咬合；A12 「运行所有者裁决只覆盖题集、不覆盖触发条件」的效力边界登记）+ B 可做 9 项（B12 补 base@m3、B13 补 §6.4 四臂、B14 更正运行中 run 的错数产物 report/artifact/结论串、B15 组合臂 m31f 门、B16 快照器整改（`readlink -f`/`cp -aL` + `as-of.txt` 加 `snapshot_kind` 字段）、**B17 工作流模板整改：深测 ask 必须等批次终态再返回 `combo_pass`（加终态闸）**、B18 消融触发判据改为读单点实测值且差≥2 才有解释力、B19 消融臂去噪补同题集 base 与单点臂、B20 非咬合证据登记 `rc7_truncations=0`）+ C 文档更正 6 项（**C17 移交件 §二「对账订正」为假须恢复 `1133800324e0e6…` 为已登记值、删「算不出」与「不要直接抄」两句**、C18 `--profile` 必填无缺省措辞、C19 五份 `as-of.txt`「cp -a 冻结」改「sha 复验锁定」、C20 分账口径续用组合臂、C21 落点差异登记、C22 「消融题集」唯一定义引 §14.3）+ **D 移交件已出**（`B2提示风格-移交对齐组.md`，**移交前须先落 C17**；上位件 `B2回灌-移交①对齐组-20261023.md`；②组不催办不代改 af）。**本次亲跑复算（11 项，§14.6）**：**组合深测三路账本 last-row 复算（主 10+lane2 8+lane3 6 → 20 题 / status 全 completed / pass 11 / fail 9 / T→F 0 / F→T 11，独立确认三审 issue 1 的 1/20 为错数）**；官方侧快照 last-row 20 题全 False∧completed + MX7⊂题集 + 题集==M1B20；官方件 sha256 四处逐字节同（零漂移）；**五份快照内的 `bench-official-mcode-m3` 全是 symlink**（`cp -a` 只复制链接本身、不构成冻结拷贝；官方臂已终局故本次无损）；base→combo 与三个消融变体的 `run-one.sh` diff（各恰摘一旋钮）；yaml 恰 2 hunk + 官方/M1B/combo 三方同为 `f76cc62262b3944…`；行为双报与子域分账逐题重算（V4-13 +7 / MX7 +4 / 域缘 +4）；消融六本账本 last-row（4/5、3/5、3/5 与三份 detail 一致）；**35 份 patch.diff 禁前缀 0 命中**（组合 20 + 三消融 15）+ `/tmp/mcode-tune-combo-M1B-B2/` 不存在 + `out/` 下仅 `*-m3` 臂目录（无 m31f 组合臂）；af 零改动（HEAD 94cd1923、5 行未跟踪 poc/）；**移交件 tools 指纹在 anolis 只读独立复算（默认=1133800324e0e644、sort_keys=1133800324e0e644、ensure_ascii=False=fce0c88a96eeece4，两 session 均 18 工具，systemPrompt coding 17219/17327 sha16 2dd03a81、tui 15655/15763 sha16 17e3b1e3，控制变量全同）→ 独立确认三审 issue 3**。**未做/未跑据实登记（§14.7）**：组合臂与三消融臂 **m31f 准入门 0 跑**（本节结论不含 m31f 不退化证据）、base@m3 对照臂仍仅 1 行、§6.4 四臂未跑（**同题集单点 B2 臂从未跑**）、C1–C5 工件未产、全池 120 题 m31f 采纳线未测、B2 两侧数字本轮未复算、轨迹人工抽样未做、judge.json 0 字节两处未做字节级取证、`/data 16G` 不可复算、mcode `work` 第三档与 af 侧零执行、**运行中 run 的 report/artifact/结论串错数未代改**。 |
