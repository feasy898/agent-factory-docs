# cal2 事件台账（2026-10-13）

## E1 · 额度 canary（01:00-01:10）
- anolis 官方 harness：mcode/M3、mcode/M3.1-Flash、step/step-5-preview、step/step-router-v1、kimi/kimi-for-coding 全部 CANARY_OK。
- 本机 ZCode 工作流派发：4 模型（MiniMax-M3、MiniMax-M3.1-Flash-Preview、step-5-preview、step-router-v1）经 CreateWorkflow 子代理全部 CANARY_OK。
- 上轮 MiniMax 402 额度已恢复；GLM 按用户要求本轮不测。

## E2 · 防作弊基建
- anolis：51 任务的判分测试（tests/）移至不可猜测路径 `/home/pan-ding/bench/.grading-b6a766c909/`；judge.sh 改为从该路径取判分文件，仅保留 4 个任务 Dockerfile 引用的输入文件（schemelike/circuit-fibsqrt/rare-mineral/reverse-engineering），multistep-definite-integral 的 tests/ 按官方 COPY . /app 设计恢复保留。
- 本机：bench/、tb-tasks/、需求包、历史报告等全部移至工作区外 `/home/pan-ding/.cal2-arch-0e9a060a/`；工作区仅剩 cal2/（任务输入+脚本）与 .zcode/。
- 每个本地 agent 独立 scratch + 铁律系统提示（禁越界、禁 ssh、禁找答案）+ declared_clean 声明字段 + 事后审计脚本 audit_cheat.py。
- 两侧任务输入 parity 全量核验：51/51 一致。

## E3 · zcode-s5 配置修正（02:10）
- 发现官方 step CLI 默认 thinking=medium（二进制 DEFAULT_THINKING_LEVEL），而 zcode provider 默认 high。
- 为保证 harness 对比受控，zcode-s5 泳道重置为 medium 重跑（原 high 配置的 8 个已完成任务作废，scratch 重新播种）。
- 记录：zcode 的 provider 默认档位与官方 harness 默认档位不同，本身是标定数据点。

## E4 · 本地磁盘 ENOSPC（02:08）
- 旧 s5 跑因 ENOSPC 崩溃（mkdir .zcode/v2/visualizations 失败）。瞬时写入高峰（疑似某 agent 任务大临时文件），自行恢复，136G 可用。
- 部署本地 disk_watchdog.sh（<20G 时清理 6 小时前的 /tmp/tmp*）。

## E5 · m3 泳道 DriverError（02:17）
- circuit-fibsqrt 的 agent 单次回复超出模型输出上限，异常击穿整个 run（63/66 已 settle）。
- 修复：全部 4 个脚本加 try/catch 包裹（ask 文本未变，缓存不失效），amend 后 63 个已完成步骤零成本恢复，仅失败/在途任务重跑。

## E6 · 规则违规：zcode-m3 / db-wal-recovery（01:35-01:45）
- 该 agent 被 sqlite checkpoint 删除工作目录内 WAL 后，越界探索文件系统（引用归档路径与 md5），并于 01:40 删除 cal2/inputs/db-wal-recovery/main.db-wal。
- 处置：答复禁止越界恢复（与官方泳道约束一致）；inputs 原始文件已从归档恢复；该结果保留但标记待审计（若 recovered.json 含 5 条以上记录即判定污染剔除）。

## E7 · movie-helper 输入缺失（全程）
- 该任务输入由 Dockerfile RUN 阶段生成（种子确定性），本 harness（及上轮）不提供 RUN 期生成输入，需 agent 自行重建；9 条泳道一致。
- 已答复挂起 agent：不提供文件、自行生成、判官用自带参考矩阵比对。

## E8 · 判分链路验证
- judge_local.sh 端到端验证通过（zcode-router/db-wal-recovery → pass）。

## E9 · router 泳道多次中断与处置（07:49-14:00）
- 07:49 会话切换导致 run 91f9e06f 被中断（64/66 settled，2 个在途+第 4 批未跑）；09:35 恢复。
- schemelike：agent 单步运行约 5 小时无收敛（其他泳道同题 40-60 分钟），按 infra 剔除（E10 同）。
- circuit-fibsqrt：agent 单步运行约 2h40m 无收敛（样例仍输出 0），按上轮"保留产物重判"惯例直接判分当前产物得 fail，该题按 infra 口径从 JOBS 剔除；处置时主代理误杀进程树导致新 run 被 SIGTERM/SIGKILL 误伤两次，均已恢复（缓存零损），最终 ff366180 完成全部 49 题。
- 完成后的 summary 审计发现 3 起跨泳道/归档污染（regex-chess 复制 zcode-s5 产物、movie-helper 访问归档 solution.sh、db-wal-recovery 利用他泳道记录破谜），按纪律剔除（详见 results/audit-final.md）。

## E10 · grok-4.7 接入与两轮测试（2026-10-14）
- 用户授权接入：anolis 已登录 grok CLI（SessionToken，grok-4.7 为默认模型），网络需走 hk-gateway SOCKS5 代理（socks5h://100.64.0.3:1080）——harness 脚本内置代理 env。
- 踩坑修复：(a) `script` 伪终端吞掉 lane 的任务列表 stdin → script 的 stdin 重定向 /dev/null；(b) 任务提示词含引号破坏 `script -qec "..."` 嵌套引用 → 改 --prompt-file 传参；(c) 额度检测模式误伤含银行术语（credit/balance）的任务 → 收紧为明确计费错误模式；(d) python:3.13-slim-bookworm 基础镜像缺失且 docker.io 拉取被断 → 从 docker.1ms.run 拉取重打标签；(e) 磁盘多次满导致判分 JSON 写入失败 → anolis-root 清理 + setsid 重判。
- 初测（25 分钟上限）：46.0%，41/51 题超时。
- 用户判断为延迟问题，授权 2.5 倍时间（3750s）重测 41 题：47.1%，零超时，成绩无变化 → 确认超时为深夜代理延迟的窗口性现象，grok-4.7 真实水平约 47%，A5 强臂假设证伪。

## E11 · GLM 轮开测前全体系排查与修复（2026-10-14 17:00-18:00）
- 反作弊再加固：工作区残留的 tb-tasks/（241 题原始包含 solution.sh）移出至归档；4 个历史配置 scratch（zcode-m3/m31f/s5/router，204 份解答）全部移出工作区，runs/ 仅保留新配置空目录。
- 发现并修复判分环境退化（会导致假失败）：
  - spotcheck 重判 5 题：hello-world pass✓、count-call-stack fail✓、tree-directory-parser fail✓ 与原判一致；analyze-access-logs 原判 pass、重判 fail —— 定位为 ubuntu-24-04 基底 pytest 丢失（判题容器装 pytest 失败被静默吞掉后记 fail）。用 --break-system-packages 重增强后重判恢复 pass，确定性成立。
  - python-3-13:20250620 / :latest / python:3.13-slim-bookworm 缺 setuptools（judge 首检 import pytest,setuptools 需两者），已烤入并 6 基底离线核验全 OK。
  - judge.sh 加固：pytest 环境自检失败 → exit 97 → 记 infra/pytest_env_broken（不再静默假 fail）；安装链加 PIP_BREAK_SYSTEM_PACKAGES=1 兼容 PEP 668。
- 发现并修复本机播种遗漏：gen_jobs.py 原本 copytree(inputs→work)，gen_wf3.py 漏做 —— GLM 102 个工作目录补种 35 个含输入任务（cp -n 不覆盖 agent 已产出）。git-leak-recovery agent 因空目录升级提问，答复后带输入继续。
- anolis 清场：7 个 solve-maze-challenge 判题残留容器（判题 pytest 挂死、timeout 杀客户端致孤儿）rm -f，回收 2.16GB 镜像；28 个 dangling 层 prune。
- 已知行为记录：solve-maze-challenge 判题 pytest 在产物错误/缺失时可无限挂起（900s timeout 记 test_timeout/infra；产物正确则快速通过）——各配置口径一致，pass 率分母不含 infra。

## E11 · 判分完整性审计与修正（2026-10-14 晚）
- 用户质询触发全量审计：官方 5 配置 + zcode-m3/m31f 零假失败；zcode-s5 2 个、zcode-router 20 个、grok47 26 个假失败。
- 假失败三类根因：(a) grok harness 的 `script -qec "..."` 嵌套引号被任务提示词里的引号破坏 → agent 从未运行（0 秒退出、scratch 为空）；(b) 磁盘满导致判分容器内 pip 安装 pytest 失败 → 测试从未执行；(c) ubuntu-24-04 基础镜像丢失 pytest 增强层（上轮 prune 事故遗留，PEP 668 externally-managed 挡住运行时补救安装）。
- 修复：harness 改 --prompt-file；磁盘清理（anolis-root）；ubuntu-24-04 用 PIP_BREAK_SYSTEM_PACKAGES=1 重新增强并 commit；41 题重判 + 8 题重跑；3 个污染剔除题重新施加剔除。
- 修正后：grok-4.7 47.1%→96.1%（49/51，全场第一）；zcode-router 28.3%→53.2%；zcode-s5 68.6%→70.6%；官方 5 配置与 zcode-m31f 数值不变。
- 教训：判分日志必须记录 pytest 是否真实运行；“No module named pytest”类静默失败需要判分器显式检出（已列入下轮改进项）。

## E12 · GLM-5.3 泳道播种时序事故与 12 题重做（2026-10-14 19:50）
- 时序：GLM 两泳道 16:55 起跑，播种修复发生在 17:47；第 1-2 批部分 agent 空目录开工。
- 判定：对 51 题 inputs 目录与 agent summary 全量交叉核对——inputs 存在但 agent 空目录开工（合成/占位数据）= A 类重做；任务本无输入文件（mahjong/vertex-solver/movie-helper/flood-monitoring/organization-json-generator 的 data 仅含 projects）= B 类按设计保留（与历史各配置同等条件）。enemy-grid/gcode/git-leak/sqlite 虽早期开工但已获得真实输入并正确完成，不重做。
- GLM-5.3 重做 12 题：analyze-access-logs、bank-trans-filter、count-call-stack、cpp-compatibility、jq-data-processing、jsonl-aggregator、recover-accuracy-log、recover-obfuscated-files、schedule-vacation、constraints-scheduling、db-wal-recovery、log-summary-date-ranges。首次尝试产物归档至 .cal2-arch-0e9a060a/redo-partial-glm53/，工作目录重建并补种后以逐字节相同指令重派（dwfrun-e3bdeb68）。GLM-5.3-Flash 泳道完成后同法处置。
- 声明核查：GLM-5.3 泳道 13 题 declared_clean=false，逐条初判多为良性（阅读 ask 本身指定的 instr 路径、/tmp 自建临时文件）；待 canary 审计终判。

## E13 · GLM-5.3 重做完成 + Flash 泳道中断恢复（2026-10-14 21:40）
- GLM-5.3 重做 12 题全部完成（12/12 自报完成，真实输入产出）；zcode-glm53 declarations.json 落盘（14 处 declared_clean=false，均为良性：读指定 instr、/tmp 临时文件、ilp-solver 一次工作目录外写入后自删）。
- Flash 泳道 dwfrun-91b1bc0c 在会话进程退出时被中断：1-3 批 39 题已结算，solve-maze-challenge 在途（半成品归档至 redo-partial-glm53f/ 并重播种），第 4 批 12 题未开跑。ResumeWorkflowRun 原样恢复（缓存零损）；第 4 批开跑时输入已齐，无时序风险。
- GLM-5.3 泳道 51 题开始后台评分（judge_local_all zcode-glm53）。

## E14 · 判分环境退化影响的全局重估（2026-10-15 03:00-04:30）
- 决定性证据：anolis 判分日志中 42 份含 "No module named pytest/setuptools"，横跨 cal2-grok47(23)、zcode-router(22)、cal2-step-router(4)、zcode-s5(4) 等；grok 的 24 个结果文件是无 agent 元数据的裸判分（17:43 setsid 重判批次），其余 27 个带真实 wall_sec(187-2105s) —— 说明 grok 早前上报的 46%/47.1% 是"判分环境坏 → 静默判 fail"造成的系统性低估。
- 修复基础镜像 + judge.sh 环境自检后，grok-4.7 真实成绩 96.1%(49/51)，仅 2 题真实失败（未编译 feal_in_c / portfolio_optimized_c 扩展，测试导入失败）。
- 受影响面：官方 harness 各配置 scratch 已被 lane runner 判分后清理（仅 grok47 保留 51 份），无法重判；4 条本地 zcode 泳道解答完整归档，已推送 anolis 重判。
- 已在 anolis 启动 rejudge_all.sh：grok47 / zcode-m3 / zcode-m31f / zcode-s5 / zcode-router 五配置在修复环境下重判，旧判定归档为 <cfg>.prefix/ 供前后对比。
- 判分管线再加两道护栏：docker build 1800s 超时（此前 solve-maze 无超时构建挂了 58 分钟）、守护进程 3G 磁盘熔断。

## E15 · GLM 双泳道最终成绩与审计
- zcode-glm53（GLM-5.3）：78.0%（39/50），排除 solve-maze-challenge（infra：node apt 构建 1800s 超时）。主跑 39 题 + 播种事故重做 12 题。
- zcode-glm53f（GLM-5.3-Flash）：60.0%（27/45），排除 6 题：4 题播种遗漏事故（analyze-access-logs / bank-trans-filter / jq-data-processing / jsonl-aggregator）+ 2 题 GLM 账号额度耗尽前未派发（movie-helper / stable-parallel-kmeans）。
- 失败复核（假失败排查）：count-call-stack 期望 646 条堆栈而模型解析出 631 条（模型自述并列排序不确定）、puzzle-solver 最深层与目标深度差 1、grok 两题为未编译 C 扩展 —— 均为真实模型失败。
- 反作弊审计：canary 命中 GLM-5.3 5 例 / Flash 4 例，人工复核后全部误报（base64 输入解码产物 cmp 逐字节一致、指令明文规定的类名与会议名、指令表格可算出的 NPV 299、openssl -dates 标准格式）。双泳道零判分材料污染。
- 跨轮参考：上一轮（10-12）同题集 zcode-glm53 曾测得 88.2%（45/51），本轮 78.0%，差异主要来自本轮 12 题重做前的播种事故与本轮更严格的排除口径。

## E16 · 判分链路三处系统性缺陷与修正（2026-10-15 05:00-10:00）
- 缺陷①（基底退化→静默假失败）：判分容器内 pytest 装不上时，报错被吞掉后记 fail。已加装 setuptools、修复 PEP 668、增加环境自检（坏环境记 infra/pytest_env_broken）。
- 缺陷②（root 残留污染 scratch，最隐蔽）：判分容器以 root 运行，会把自己的编译残留写进被挂载的 scratch（例：polyglot-c-py 测试编译出的 /app/polyglot/cmain，断言"目录中只能有 main.py.c"因此失败）。该文件 root 属主、宿主机普通用户删不掉，导致后续每次重判都被污染 —— 表现为 grok-4.7 从 96.1% 掉到 58.0% 的"重判下跌"。修正：judge_daemon 判分前用 root 容器 find ! -uid $(id -u) -delete 清除 root 残留（保留 agent 产物）。
- 缺陷③（构建超时误杀）：1800s 构建超时在极慢镜像源（实测 ~9KB/s）下把正常构建判成 build_failed(exit 137)。修正为 5400s；同时给守护进程加 3G 磁盘熔断（曾因重判累积镜像把磁盘撑到 100%，进而引发连锁 build_failed）。
- 清理 anolis：prune 后磁盘从 366M 恢复到 17-18G。
- 结论：旧判定（污染前）与第一次重判（污染后）均不可直接采信，须以带 root 清理的最终重判为准；GLM 两泳道为一次性干净判分（scratch 全新推送、每题只判一次），不受此影响。

## E17 · 终版数据收官（2026-10-16）
- 第二波基底退化定位与修复：python:3.13-slim-bookworm 丢失（prune 误伤 + docker.io 不通）→ docker.1ms.run 重拉；ubuntu-24-04 增强丢失（dockerd 崩溃窗口）→ fix_ubuntu3（带 apt pip 重试 + 验证不过不提交）；enhance3 重跑冲掉 setuptools → fix_setuptools 重打。5 基底离线验证全 OK。
- 污染面：18 个测试期缺依赖的假失败（numpy/sympy/scipy）+ 7 个 infra 全部清除重判。
- 最终 sweep：5 配置 × 51 题 = 255 判定，零 infra，全部实判。
- 终版数字：grok47 84.3%（43/51）；zcode-m3 49.0%；zcode-m31f 68.6%；zcode-s5 66.7%；zcode-router 54.9%；glm53 78.0%（39/50，1 infra）；glm53f 60.0%（27/45，6 excluded）。
- 官方 5 配置 scratch 已被清理无法重判，报告中已标注口径差异。

## E18 · Flash 泳道 6 题补跑收官（2026-10-16）
- GLM 登录恢复后按逐字节一致指令补跑 6 题（dwfrun-5e1ad7a2）：4 题播种事故全部 pass（analyze-access-logs / bank-trans-filter / jq-data-processing / jsonl-aggregator）、stable-parallel-kmeans pass、movie-helper fail（输入本不提供，设计内条件，与全配置一致）。
- zcode-glm53f 终版：32/51 = 62.7%，51 题完整口径，零排除。
- 双 GLM 泳道就此全部定稿：GLM-5.3 = 78.0%（39/50，1 infra 构建超时）、GLM-5.3-Flash = 62.7%（32/51）。

## E19 · flash 三泳道收官与复现性验证（2026-10-17）
- Step3.7-Flash 首测：51.0%（26/51），安静串行判分，3 个可疑失败核实为真实（count-call-stack 并列排序不符、polyglot 产物写到工作目录外、distribution-search npy 损坏）。
- GLM-5.3-Flash 复现：70.6%（36/51）vs 原跑 62.7%，逐题一致 84.3%，8 题翻转（6 转 pass、2 转 fail）。
- M3.1-Flash 复现：68.6%（35/51）vs 原跑 68.6%，**总分完美复现**，逐题一致 80.4%（10 题翻转净差为零）。
- flood-monitoring-basic 在 M3.1 复现泳道首次因 harness WorkflowError（未提交结果）失败——机制故障非模型失败，已补跑并用新内容重判（仍 fail：该题输入只存在于评分容器，属设计内条件，12 配置一致）。
- anolis 中途不可达 ~2 小时（本机 tailscale 链路抖动，机器实际一直在线），恢复后一键补判完成，零数据损失。
- 三条新泳道反作弊审计：15 例 canary 命中全部证伪，零污染。
