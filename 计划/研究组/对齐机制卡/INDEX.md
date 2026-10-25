# 对齐机制卡 · INDEX（第二阶段对齐资料批产）

> 生成：2026-10-24，anolis-gpu-01 上经 mcode CLI headless 批产（模型 `minimax/MiniMax-M3.1-Flash`，免费窗口 2026-10-26 截止前）。
> 用途：Agent 定义 DSL 的对齐输入**草稿**——论文/框架机制的忠实提炼 + DSL 映射预判；最终通过与与否由我们的编译器裁定，卡片本身不构成验收标准。
> 制作方式：15 张提示词卡（固定六节：①核心机制 ②组件清单 ③数据与上下文流 ④失败处理与停止条件 ⑤预算与评估方式 ⑥DSL 表达点清单）→ `auth-sync.py` + `mcode exec --permission full` 逐个跑，并发≤2，单卡 15 分钟硬超时。
> 运行现场：anolis `~/m31f-mechcards/`（prompts/cards/logs/脚本 + status.tsv 批跑台账）；本机管线副本在 `pipeline/`。

## 验收结论

**15/15 全部落地，六节齐全**（≥13 达标，超额）。每张卡均含逐字六节标题、`<!-- TARGET: … -->` 头；正文 2854~5918 字。

| # | 本机文件 | 目标 | 成败 | 字数 | 耗时(s) | 置信 | 备注 |
|---|---|---|---|---|---|---|---|
| 1 | ReAct.md | ReAct | 成 | 3069 | 55 | 正常 | 映射预判「单节点循环+工具回边」 |
| 2 | Reflexion.md | Reflexion | 成 | 5529 | 40 | 正常 | |
| 3 | Voyager.md | Voyager | 成 | 3404 | 47 | 中高（模型自标） | 卡首自标「机制层面可靠；部分实现细节与预算数字标注存疑」，已逐处标"存疑" |
| 4 | SWE-agent.md | SWE-agent | 成 | 5918 | 70 | 正常 | |
| 5 | MemGPT.md | MemGPT | 成 | 3703 | 41 | 正常 | 未动用 Mem0 备选 |
| 6 | MetaGPT.md | MetaGPT | 成 | 4224 | 53 | 正常 | 映射预判「流水线+结构化工件交接」 |
| 7 | CAMEL.md | CAMEL | 成 | 3213 | 70 | 正常 | 未动用 AgentVerse 备选 |
| 8 | GPTSwarm.md | GPTSwarm | 成 | 3334 | 57 | 正常 | |
| 9 | Agensh-DeLM.md | Agensh + DeLM（『或』条款升级为双目标合一） | 成 | 3171 | 158 | 低置信 → **已重写补课（高，2026-10-24）** | 原卡 m3.1f 不识目标、实写 AutoGen Swarm（已作废）；2026-10-24 由带检索能力的代理（对齐机制卡补写者）按裁决书 §四.2 补卡令重写：Agensh=arXiv:2609.26781（微软研究院，2026-09-22）、DeLM=arXiv:2606.10662（斯坦福，2026-06-09，代码 github.com/yuzhenmao/DeLM），双目标均网络检索核实、六节齐全、机制断言逐条注论文来源，重写后 11701 字（含检索过程与未核实项附录） |
| 10 | Multi-Agent-Debate.md | Multi-Agent Debate | 成 | 2854 | 65 | 正常 | |
| 11 | AFlow.md | AFlow | 成 | 3351 | 58 | 正常 | |
| 12 | ADAS.md | ADAS | 成 | 3609 | 81 | 正常 | |
| 13 | LangGraph-StateGraph.md | LangGraph StateGraph | 成 | 5322 | 33 | 正常 | |
| 14 | AutoGen-Team-JSON.md | AutoGen Team（声明式 JSON） | 成 | 4087 | 61 | 正常 | 覆盖 RoundRobin/Selector/MagenticOne 拓扑与 termination conditions |
| 15 | CrewAI-YAML.md | CrewAI YAML 装配 | 成 | 4604 | 65 | 正常 | |

合计耗时（通过判定的那次运行）：约 15 分钟（并发≤2 下批跑墙钟 ≈9 分钟 + memgpt 补跑）。

## 过程记录（如实）

1. 冒烟探针 1 次（12s，stdout=纯最终答复文本），随后批跑 pass1 **15/15 一次通过**，单卡 33~158s。
2. 事故（自伤、已止血）：驱动脚本 `run-all.sh` 重试判读函数变量名笔误（`$SLUG` vs `$s`），pass2 误判全量失败并重跑已成功目标，其间 4 张卡被覆盖重跑（react/reflexion/voyager/swe-agent，重跑产物均仍过六节校验）、memgpt 被截断为 0 字节。处置：pkill 止血（首轮 pkill 自匹配误杀本机 ssh 会话一次，未伤及他者；后按显式 pid 清场）→ 校验全量 → 单发补跑 memgpt（OK）。最终 15 张全部有效。批跑台账：`pipeline/status.tsv`（R 行按 slug 取首次=pass1 计时；memgpt 取末次=补跑）。
3. 免费通道零熔断：全程无 QUOTA_HIT（status.tsv 无 QUOTA 行）；auth-sync 每卡执行前各跑一次。
4. anolis 侧改动仅限新建 `~/m31f-mechcards/` + `/tmp/smoke-m31f.{txt,err}` 两个冒烟残件（已清）；`~/mcode-swev`、`/tmp/factory*`、在飞任务零接触。

## 低置信与补课清单

- **Agensh / DeLM**（去中心化协作）：✅ **已销项（2026-10-24）**——带检索能力的代理按裁决书 §四.2 补卡令重写：双目标均检索核实（Agensh=arXiv:2609.26781，微软研究院，1→1024 agent 自组织 harness；DeLM=arXiv:2606.10662，斯坦福，共享上下文+任务队列取代主 agent，Agensh 明引其为共享上下文思想来源）；原 AutoGen Swarm 代写作废；卡内含检索词、命中路径与未核实项附录。
- Voyager 卡内个别实现细节与预算数字带"存疑"标注（模型自报），翻译 DSL 时按机制层采信、数字层复核。
