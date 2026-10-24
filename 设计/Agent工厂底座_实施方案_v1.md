# Agent 工厂底座 · 实施方案 v1（PoC 定稿版）

> **状态**：2026-10-19 定稿，同日完成两轮补验：**诚实清单 9 项清零**（§三之二）+ **开工前接缝验证 12 项与外部项目研究 7 对象**（§三之三/§三之四，产出 4 条新裁决见 §四 5-8）。四项拍板决定已落定；15 项 PoC + 9 项补验 + 12 项接缝验证全部真实执行通过；内核种子仓库 `af/` 已就绪（git 已提交、全量构建测试全绿 174+1、六门 CI 骨架 5/6 绿）。**本文档即开发总纲。**
> **阅读顺序**：本方案 = 怎么建；《产品设计_拍板版.md》= 建什么与根本法；《底座设计纪律_v2.1修订案.md》= 反特化纪律；`af/BOOTSTRAP.md` + 各 `RESULT.md` = 环境与已验证语义。

---

## 一、四项拍板决定（已落定，全文生效）

1. **控制面位置降为配置**：宪法第 5 条改为"内核对部署形态中立，不劫持运营者的本地/云/混合决定"；不变的安全属性是信任层组件（凭证签发/预算记账/trace 完整性）在任何位置同等保证完整。
2. **决策工件内嵌多参与者权限**：工厂不是单人系统——人类以角色进入（运营者/评审/仲裁/只读观察者），各带读写权限；决策工件记录决策者身份与当时权限，权限由凭证体系统一承载（PoC 已验证：只读角色签发 approve 决策被拒，af-workorder 34 测试含此用例）。
3. **数据合规内容彻底移出方案**：个人数据命名空间/密文寻址/欧盟相关全部删除——合规是运营者配置层事务，产品不再出现。
4. **永不提时间**：建设只按波次与依赖顺序推进，完成判据（DoD）驱动，不设任何工期估计。

## 二、开发语言策略（讨论结论：Rust 为主体，四处例外）

**决定：自研内核全部 Rust。** 论据与实证：

- **你的直觉被 PoC 直接证实**：11 个内核件 crate 全部纯 Rust 实现且约 170 个测试全绿；最重的凭证域（biscuit-auth 6.0.0 + cedar-policy 4.14.0）**全依赖树零 openssl/ring**（纯 Rust curve25519），冷编译 61.8 秒——凭证域两个核心库本来就是 Rust 原生项目，选 Rust 等于站在库作者的主场。
- **编译器反馈的价值在内核件上尤其大**：这些件全是"语义密集"型（状态机、判定器、账本）——类型系统把业务规则钉进签名（如订单门控的类型化缺失清单 `PreconditionsNotMet{missing: Vec<Missing>}`），PoC 期间零警告纪律全程可守。
- **例外四处（生态绑定，不硬拗）**：①LLM 推理=vLLM（Python/CUDA 生态）；②前端与工作台=TS（AI SDK v7/assistant-ui）；③JIT 优化器外壳=DSPy/GEPA（Python 库）——但 **IR 真相源与校验器放 Rust**（PoC 发现 DSPy 存档不含字段名、delete 缺失字段静默 no-op，正需要 Rust 侧强校验兜底）；④Temporal worker 宿主短期用 Python SDK 1.34.0（完整场景已验证），Rust SDK 1.1.0 已 smoke 通过（result=84）、深验证列入波次 4。
- **开源组件的语言现实**（语言偏好不推翻语义判据）：核心件以 Go 为主（zot/cosign/temporal server/cue CLI/K8s 全家）——它们是黑盒消费，语言无关；Rust 生态里 Microsandbox（沙箱备选）保持观察、Restate 因 BSL 出局的结论不变。

## 三、PoC 结果（15/15 通过，全部真实执行）

| PoC | 结论 | 关键发现（证据：各 RESULT.md） |
|---|---|---|
| 凭证签发与权限求交 | ✅ 8 测试 | biscuit 6 无 Float→预算统一美分整数；衰减只能加 check 不能删事实→**累计预算真相源必须放 af-meter 账本，凭证只带 per-call 上限**；词表收进内部常量 |
| 图模板与编译期校验 | ✅ 16 测试+CLI | 裁定：循环体子图豁免 DAG、map 体不豁免；校验顺序=先引用完整性再判环 |
| 订单门控与决策工件 | ✅ 37 测试 | 门控拒绝=类型化缺失清单；graph_version 不可变；变更单 supersedes 封存原单 |
| 副作用网关 | ✅ 6 测试×10 轮 | 崩溃恢复外呼恰好 1 次；同键异载荷拒绝升级；fencing=Session{epoch}；撤回窗口是"发送闸"非宽限期 |
| 抽样注入与升迁引擎 | ✅ 23 测试 | 金标告警数==放行缺陷金标数（25==25）；升迁须 current/attained **双水位**（防连净回升绕过判据）；一致性率必须用批次增量口径 |
| 投放闸与渐放 | ✅ 15 测试+全天模拟 | 262 件序列：不超限且零断粮；夜间比例精确；被限流件应 defer 不重试；渐放要独立泊位 |
| 可组合计量器 | ✅ 15 测试 | 嵌套窗口（周套日取 min）时间线验证；Min=合取/Max=择优的不对称写死进接口 |
| 通用日历 | ✅ 18 测试 | 周五16:00+4工时→下周一11:00；黄金周/调休/跨时区全过；截单=逆向派生 |
| trace 分级背压 | ✅ 14 测试 | 10 万事件洪峰：critical 零丢失、缺口计数==实际丢弃数精确一致 |
| 失败指纹止损 | ✅ 12 测试 | 优先级：check首败>指纹连击>累计阈值；不误触交替错误 |
| 人工任务账本 | ✅ 8 测试 | 4 线程×40 任务零重复认领；租约过期接管；心跳带 lease_until>now 守卫 |
| CAS 实测 | ✅ 真实闭环 | zot OCI-only（拒 docker manifest）；GC=停服触发 `zot verify-feature retention` 实测回收 4 孤儿 blob；cosign 纯离线需 `--insecure-ignore-tlog`；上传接口定为 OCI 端到端 |
| Temporal 语义 | ✅ 全验收点 | kill -9 重启同 run_id 续跑；CAN 后订单查询续接；activity 执行 2 次扣款 1 次（at-least-once+业务幂等键=exactly-once 实证）；**裁决：选 Temporal** |
| CUE 产线/配方 | ✅ 三项全过 | **配方体系定案：CUE（schema/参数/L4盖L3 用 default 标记法）+ CEL（Rust 内嵌运行时谓词）**；CUE 部署期预编译 JSON（运行时求值 7-17ms 太慢且 Rust 无原生求值器） |
| DSPy IR | ✅ 36 断言 | "四元组=schema 化数据+可枚举改写+JSON 存取"命题成立；IR 校验器放 Rust |

**验证方式声明**：全部结论来自真实执行（cargo test 退出码 0 / 二进制实测输出），由 15 个 GLM-5.3-Flash 子代理并行完成、主代理全量复验构建（了结一处交叉矛盾：af-graph E0106 为时间差误报）。原"未覆盖项"已于同日验证轮全部补验（见下节）。

### 三之二 · 诚实清单验证轮（2026-10-19，9 项全部清零）

| 原未覆盖项 | 结果 | 一句话结论（报告：`af/poc/*/VERIFY*.md` 或 RESULT.md） |
|---|---|---|
| DBOS 对照 | ✅ 已实测 | **裁决维持**：长流程/审批/审计选 Temporal。修正旧说法——DBOS 不是"无纪律"，纪律前移到部署期（workflow 源码 MD5=应用版本；越界改动晾在 PENDING 不中毒、钉版本接管时显式报错）。`poc-temporal` 同口径 8 验收点全过（包名已改 `dbos` 3.3.0，Postgres 18） |
| Temporal worker 重投递 | ✅ 通过 | kill -9 在飞 worker：心跳路径 2.4-5.8s 重投递 attempt+1、双 worker 2.38s 接管、step 间被杀不重跑已完 activity。新发现：粘性队列 failover 吃满 10s SCHEDULE_TO_START；SLC 必须 ≫ 活动耗时（相等=10 连超时教训） |
| workflow.patched() | ✅ 通过（语义修正） | **判定粒度=决策点是否已定，非"run 新旧"**：未定决策点的在飞旧 run 被补丁进新逻辑（marker 写进其历史）；已定的安全沿旧分支续跑，均不中毒。Worker Versioning v2（deployment_config）双版本/钉版/drainage 实测通过。**新纪律：deprecate 过早=静默错位**（temporalio 1.34 重放按槽位匹配不比对 args）——deprecate 前必须确认无跨版本在飞 run |
| zot 周期 GC 长跑 | ✅ 通过 | gcDelay=1s/gcInterval=2s 时间压缩 101 周期：95/95 回收、长寿 tag 0 误删、blob 集精确对账、账目守恒（291 blob 吻合）。**GC 是变更触发非墙钟定时**；回收时延 1-31s（中位 17s）；在线 retention REST API 确认不存在（二进制无该路由） |
| zot scrub | ✅ 通过（有边界） | 三类损坏全检出（含 digest 全自洽的 config/layer 互换——scrub 真解析 config 内容）。**退出码恒 0，自动化必须解析输出**；在线周期 scrub 存在（interval 2h 下限）；盲区=结构合法但身份错误的替换（归 cosign 管） |
| zot http.compat | ✅ 通过 | `compat:["docker2s2"]` 主端口开关（非独立端口）：docker manifest PUT 201。**不转格式**（docker manifest 原样落盘、保留 docker digest、media type 不归一）。原"必须先转 OCI"结论撤销；上传规范仍定 OCI 端到端，compat 为逃生门 |
| cosign --trusted-root | ✅ 路线成立 | `unshare -n` 真断网下 Verified OK 且**保住 tlog 审计**（换 tlog 条目仍 exit 1）；TUF 缓存路线确认为死路（强制在线刷新）。离线验签定案：**--trusted-root**，CI 序列=initialize→分发 trusted-root.json→离线 verify |
| DST/夜班日历 | ✅ 通过 | af-calendar +12 测（3 年×2 时区 10.5 万采样点扫描）。语义钉死：**DST=流逝时间**（春跳丢时不计、秋拨重复时只计一次）、歧义时刻取较早偏移、夜班双窗口模型成立。两处新边界记录在案（午夜接缝丢 1 tick；完工点=开工点时互逆不成立） |
| cuengine FFI | ✅ 可行 | cuenv 真包装 `cuelang.org/go`（源码实证）；Rust 进程内求值 p50 0.55ms ≈ CLI 1/33，断网可用。代价：构建期 Go≥1.25+CGO+goproxy.cn、二进制 45MB、API 目录级。**主路线仍是预编译 JSON，FFI 升级为已验证的运行时备选** |

验证轮附带产出：修复 af-credential 负载敏感 flake（biscuit 默认执行限额 max_time=1ms 在 `-j 6` 满载下偶发超限——已显式放宽至 50ms，设计输入：授权判定必须显式配限额，超限是"真错误"不是"拒绝"）；清理 af-calendar 一处 unused import，全 workspace 零警告（proc-macro-error2 future-incompat 除外，已登记）。

### 三之三 · 开工前补验第二批（同日，12 项接缝验证全通过，报告在 `af/poc/*/REPORT.md` 与 `af/ci/`）

| 项 | 结论 | 对开发形态的关键裁决 |
|---|---|---|
| **Temporal×Rust 分界**（poc-bridge） | ✅ 有明确赢家 | **薄壳形态定案**：状态机+门控的判定权归 Rust 引擎 bin（无状态、stdin/stdout JSON、schema 由 af-workorder serde 派生），编排归 Python workflow，每次跃迁=一次引擎 activity。决定性证据：加新前置条件时薄壳 **workflow 代码 0 行改动**、引擎热替换、在飞 run 零中断；镜像形态同改动直接 TMPRL1100 中毒卡死。代价：代码 +101 行、每单事件历史 57 vs 21（可接受）。心跳纪律再证实：不配 heartbeat_timeout 的 kill 恢复要 60s，配 5s 只要 5.9s |
| **Bifrost×meter**（poc-bifrost） | ✅ 通过 | 三种接线全实测（配置热更 <20ms 生效 / `X-Meter-Route` header 逐请求 11/11 精确 / `x-bf-api-key-id` 直达）。裁决：**af-meter 必须是主动信号源**（500 类错误 Bifrost 按设计不跨端点，计量切换不能靠错误 failover 顶替）；最优=weight 窗口级+header 逐请求双层。**版本警示：GitHub 无 release 二进制资产，最新镜像 v2.0.0-prerelease3 落后文档约 2 个月**——引入需钉版本+源码构建路径 |
| **纯 Rust CAS 客户端**（poc-cas-rust） | ✅ 通过 | 手写 685 行（25 crates 依赖树）四形态上传全通；100MB layer 流式 RSS 恒定 4.1MB；digest 确定性全等。cosign 镜像签名/验签/同 tag 换内容拒签全过；zot referrers API 存在但**缺 OCI-Filters-Applied 头**（客户端要容错）。生产建议双轨：轻量手写为主 |
| **账本形态**（poc-ledger） | ✅ 通过 | **分库定案**：三库比单库吞吐 +25~30%、0 次 SQLITE_BUSY（单库尾延迟 2.3-5s）；**WAL 跨文件无原子性是硬边界**（SIGKILL 注入 8/8 分裂）→ 跨库一致性走 outbox 补偿（三崩溃点注入全收敛）。备份纪律：裸 cp 丢已提交数据，必须 VACUUM INTO 或先 checkpoint。窗口对齐铁律：**边界只能钟面日期→解析午夜，严禁绝对时间加法**（DST 周 167h/169h 实证） |
| **CI 骨架**（af/ci/） | ✅ 5/6 门绿 | 六门管道建成且干净副本复现（fmt 基线/clippy 基线/test/CUE 预编译/scrub 解析/cosign 断网验签）。fmt 门当前红=预存 235 块格式 diff，**列入波次 1 首任务** |
| **OTel 出口**（poc-otel） | ✅ 通过（含红色发现） | **OTel 出口是有损组件，af-trace 的 critical 语义不能托付**：SDK `on_end` 无返回值+BSP 队列满静默丢弃；collector 无持久缓存（重试 3 次后整批丢弃）；file exporter 启动即截断。裁决：**critical lane 自有落盘（af-trace 现有语义保持），OTel 只承载非关键 lane**；批量 500ms-1s；协议跟随后端（Langfuse 只收 HTTP） |
| **ClickHouse MES**（poc-mes） | ✅ 通过 | 明细 MergeTree+物化视图为默认（查询 3-6ms，迟到回填 MV 自动正确 18/18）；AggregatingMergeTree 用于只要窗口指标的高压缩场景（状态表 1/10 体积）；**ReplacingMergeTree 不作主表**（FINAL 慢 30-40 倍）。写入：官方 crate（HTTP+RowBinary，非 native TCP——生态里没有维护良好的 native 客户端），**批 ≥5 万行或"满 5 万/满 1 秒"双阈值**（拐点在 1 万-5 万之间） |
| **CUE 装载端到端**（poc-cue/verify-load） | ✅ 通过（含红色告警） | 装载器成立（千条 5.8ms、15 码三层错误分类学、17 个坏样例全拒）。**红色告警：千条规则下 `or()` 引用完整性使 vet 88.9s/export 64.9s（近平方增长，对照线性差 47-84 倍）→ 引用完整性检查移出 CUE、由装载器 E2001 承担（已实现验证），CUE 只做 per-rule closed schema**。另证："缺 default 标记"在导出 JSON 里字节级不可见，只能在部署期查 CUE 源——lint 项定位明确。版本策略=拒绝式信封（未知版本一律 E0001） |
| **DSPy 适配往返**（poc-dspy/verify-adapter） | ✅ 通过 | IR schema v1 可定稿；往返字节级相等；四类漂移校验器逐个抓住且归因精确（对照 DSPy 全静默）。**五类校验必须在 Rust**：字段名齐全/位置对齐/无未知字段/demos 数量键名/输出预期——位置对齐是唯一能抓"字段顺序漂移"的手段 |
| **沙箱 CubeSandbox**（poc-sandbox） | ✅ 全链通过 | KVM 在位走 bare-metal microVM（guest 内核≠宿主实证隔离）；创建 143ms/冷启动 p50 156ms/快照 570ms/回滚 319ms/克隆 522ms；每沙箱 PSS 176MB；三个 Rust crate（hypervisor/cubecow/CubeAPI）本机可构建；Apache-2.0。**可作自托管沙箱底座进入集成评估**，快照/克隆/回滚原语是相对纯 E2B 云的主要增量；工具 broker 接口直接对标其 SDK 面 |
| **rekor-tiles 私有部署**（poc-rekor） | ✅ 通过 | 部署比预期轻：posix 二进制+静态文件服务即可，**无 MySQL/Trillian 依赖**。cosign 原生直传私有 log + 断网 `--trusted-root` 验签 Verified OK（与 blob 验签完全同构）。三坑入册：写 API 与 tile 读路径必须同源；`--hostname` 须剥端口；**v2 的 integratedTime 恒 0，log 不背书时间**（时间信任靠产物签名/TSA/witness） |
| **内核裸进程形态**（poc-kernelrun） | ✅ 叙事成立（有缺口） | 11 crate 单进程零端口跑通全部断言，冷启动中位 191.8ms、RSS 19.5MB、重启状态留存。**缺口：SQLite 持久化只覆盖 2/11 件**（meter/release-gate/sampling/stop/trace 全内存态，凭证根密钥无持久形态，首启/重入路径未定义）→ 全部列入波次 2 |
| **cargo 反馈流水线**（poc-cargo-pipeline） | ✅ 引入 | 九工具全真实装通，L0-L3 阶梯落成：L0 每轮 `cargo check -p`（增量 ~1s）/ L1 提交前 fmt+clippy+test -p / L2 合流全量+semver-checks+deny+audit+fuzz 60s / L3 夜间长 fuzz+miri+基准对比。取舍实证：semver-checks 只在 minor/patch 场景有效（major 版 260 lint 全跳过）；miri 独占价值=原生静默的 UB（transmute 非法值）；advisory-db 本地化；agent 反馈统一五字段 envelope（tool/level/code/location/fix） |

### 三之四 · 外部项目研究（默认拒绝姿态，报告在 `temp2/外部项目研究/`）

7 个指定对象全部找到真实项目（star 数/组织仓数经主代理 GitHub API 抽查核实）。**没有一项整体引入；采纳形态全部是"抄设计、零运行时依赖"**：

| 对象 | 裁决 | 采纳要点 |
|---|---|---|
| AgentScope（33.5k★，阿里） | 部分引入（仅设计） | 13 机制重叠为 0、自然语言 handover 违宪 #1，整框架不引入。抄 4 条：消息总线消费语义三分类（drain/replay/broadcast+cursor+max_len）作 Trigger 收件箱与 Channel 保留窗蓝本；Scheduler 的 storage 事实源+通知促 reconcile；HITL 停车/恢复四事件+确认只带查找键；SOP executor+verifier 步骤模型 |
| openjiuwen（24 仓，华为背景） | 整体不引入；抄 8+4 条设计 | 旗舰是"把 agent 跑起来"的框架，与"把工厂管起来"品类不同。最值：agent-dx 的 Environment/Runtime 双身份+ownership_generation 代际 fencing（补强 Run 与副作用网关执行纪元）、CheckpointStore"声明与现实不符则启动即失败"、model-router"决策不进数据面+state 可丢 hint"、iCode 成本按轮次归集与 rollback。agent-memory 拒绝（LLM 驱动可变记忆违宪 #1 且是影子成本）。两个 Rust 件设复查触发条件（model-router/agent-dx） |
| ANOLISA（agentic-os-org，630★） | 部分引入（2 机制） | tokenless 可逆压缩（L2 适配器+阈值进 L3，引入前须工具密集负载复测）；Skill Ledger 漂移重判（Ed25519+append-only+变更重扫）补 Skill broker 变更复检。其余（eBPF/btrfs/FUSE 外挂式）违反部署中立 |
| bingreeky/JIT（真名 binggreeky/JIT，559★，HF jit-27b 真实） | 部分引入（2 纪律进 JIT 护栏规格） | **同名不同物**：它的 JIT=运行时生成任务专属 harness，与我们机制 #13 零对应。只抄两条：repair_only_on_error（"只修崩溃、绝不修低分——那是优化基准"）；best-of-N 前零成本静态 schema 预筛。拒绝运行时的硬证据：fail-open 三连、全仓无随机种子（违宪 #7）、README 宣称的 archive 持续改进在代码中不存在 |
| PenguinHarness（2836★，RSI 框架） | 部分引入（评测方法论） | 抄 5 条进 Evaluation/CSP-1 设计：基准三态生命周期；信息屏障+泄漏即污染停机；四失败码+"基础设施失败绝不算 0 分"；scoreboard 只追加；快照纪律（版本只增/密钥不进快照）。运行时不引入（TS/Node、屏障非沙箱强制） |
| genmeta（22 仓） | 不引入 dHttp；daccess 借 3 条模式 | dHttp 是网络准入非执行授权（无衰减/无预算/厂商过渡根 CA 不配当信任锚）；留窄口径：若未来真出现公网 agent 身份场景（rule of three），以 L2 适配器接 transport。daccess 三条设计直接进基线：授权绑定"可读名+密钥学主体"双因子；"需人工"fail-closed 不阻塞业务；审批一次性消费+不得移除最后一位有权签发者。dquic 记观望 |
| PhyAgentOS（2988★，中山/鹏城） | 不引入 | 实为带机器人 Gateway 的聊天框架：任务抽象薄（全系统仅一个非终态任务）、无资源租约、Sandbox 为零、Meter 为零。抄 3 条语义：七种身份不互替；"受理≠完成、未知副作用永不自动重发"的更严幂等；升迁梯补反例退役方向 |

**研究轮方法论产出**（进设计语料库）：每份报告含"替我们省了什么/效果证据/引入成本/对接哪层+退出成本"四问清单与逐仓裁决，dquic/CONTEXT.md 的"每机制配术语表+Avoid 反例"做法值得仿照。

## 四、关键技术裁决（随 PoC 定案）

1. **durable 执行引擎 = Temporal**（裁决依据经 DBOS 实测对照后**维持**：长流程编排+人工审批+幂等+审计的收益>replay 纪律成本，双向实测。DBOS 修正认识：它把纪律前移到部署期——workflow 源码哈希即应用版本，越界改动晾 PENDING 不中毒、钉版本接管显式报错，比 Temporal 回放中毒好诊断，但无事件级审计/update 返回值/CAN 身份续接/多语言 worker 对等物）。配套**四约定**：①审批门统一 signal/update 二选一；②跨 run 状态收敛到显式 State 且与 run 签名同类型（CAN 参数类型不一致会**静默丢字段**）；③外部 activity 一律带业务幂等键，且 StartToClose 必须 ≫ 活动耗时（相等=连超时，实测教训）；④版本收尾纪律——patched() 已验证可救在飞 run（语义=按决策点判定，见 §三之二），但 **deprecate 前必须确认无跨版本在飞 run**（temporalio 1.34 重放按槽位匹配不比对 args，deprecate 过早=静默错位）；多版本并存用 Worker Versioning v2（deployment_config，双版本/钉版/drainage 已实测）。
2. **配方体系 = CUE + CEL**：CUE 当 schema 语言不当规则引擎（时间窗/事件流谓词做不了）；禁用 rhai 类图灵完备脚本；"可覆盖字段必须带 default 标记"与"closed definition 用 embedding 扩展"定为 lint 项。运行时求值三级路线已全部验证：预编译 JSON（主路线，零运行时依赖）> cuengine FFI（0.55ms/次、已验证可行，构建期 Go+CGO 代价，作运行时备选）> CLI 进程（18ms/次，弃）。
3. **CAS 接口约定**（补验后定案）：上传规范=OCI manifest 端到端（`http.compat:["docker2s2"]` 为 docker 直入逃生门——主端口开关、不转格式、media type 不归一，非必要不开）；**常规回收=在线周期 GC**（`gc:true`+短 gcDelay/gcInterval，101 周期实测零漏收零误删；预期"数十秒内回收"，变更触发非墙钟），停服 `verify-feature retention` 降级为深度巡检；完整性巡检=在线 scrub（2h 下限）+ scrub 输出解析器（**退出码恒 0**，必须解析 STATUS=affected 行）；离线验签定案 **--trusted-root**（真断网实证、保 tlog 审计；CI 序列=在线 initialize→分发 trusted-root.json→离线 verify，附轮换监测流程）。
4. **预算数值全链整数**（u64 计数/i64 美分），biscuit 词表与 meter 账本同次评审定死。
5. **Temporal×Rust 分界 = 薄壳**（poc-bridge 裁决）：判定权归 Rust 引擎 bin（无状态、订单快照整体进出、错误类型化透传），编排归 Python workflow；门控规则变更只动引擎（可热替换、在飞 run 零中毒），workflow 代码零改动。配套纪律：长活动必配 heartbeat_timeout（5s 级，否则 kill 恢复 60s 起步）。
6. **账本 = 分库 + outbox 补偿**（poc-ledger 裁决）：meter/station/gateway 各一库；跨库一致性不靠事务靠 outbox；备份用 VACUUM INTO 或先 wal_checkpoint；窗口边界只准"钟面日期→解析午夜"。
7. **trace 双轨**（poc-otel 裁决）：critical lane 由 af-trace 自有落盘保零丢失（OTel 链路实测为有损：SDK 静默丢弃+collector 无持久缓存+file exporter 启动截断）；OTel 只承载非关键 lane，批量 500ms-1s。
8. **CUE 引用完整性出 CUE**（cue-loading 裁决）：`or()` 析取在千条规模近平方爆炸，引用完整性由 Rust 装载器承担（E2001），CUE 只做 per-rule closed schema；"缺 default 标记"部署期查 CUE 源（JSON 里不可见）；版本=拒绝式信封。

## 五、仓库就绪状态（af/，git 60f6861）

- cargo workspace：11 个内核件 crate（凭证/图/订单/副作用网关/抽样升迁/投放闸/计量器/日历/trace/止损/人工账本），全量 `cargo build && cargo test -j 6` 全绿（**174 通过 + 1 ignored 密集扫描**，零警告除已登记的 proc-macro-error2）。
- 第三方二进制就位（不入库）：temporal 1.9.1 / zot v2.1.22 / cosign v3.1.3 / cue v0.17.1 / crane 0.22.1；cargo 工具链九件已装（clippy/rustfmt/miri/cargo-fuzz/insta/semver-checks/deny/audit）。
- Python venv 就位：dspy 3.4.1、temporalio 1.34.0、dbos 3.3.0（Postgres 18 apt 装于系统，DBOS PoC 用）。
- 每个 crate 带五节式 RESULT.md（结论/步骤/证据/反馈/遗留）——**动一个 crate 前先读它的 RESULT.md**。
- 第一轮补验产物：`poc/poc-temporal/VERIFY.md`、`poc/poc-cas/VERIFY.md`+`VERIFY-TRUSTED-ROOT.md`、`poc/poc-cue/VERIFY-FFI.md`、`poc/poc-dbos/`（第 5 个 PoC 全套）、`crates/af-calendar/tests/dst_night_shift.rs`；af-credential 执行限额修复（详见其 RESULT.md ④-6）。
- 第二轮补验产物（12 项接缝验证+研究）：`poc/{poc-bridge,poc-bifrost,poc-cas-rust,poc-ledger,poc-otel,poc-mes,poc-sandbox,poc-rekor,poc-kernelrun,poc-cargo-pipeline}/REPORT.md`、`poc/poc-cue/verify-load/`、`poc/poc-dspy/verify-adapter/`、`ci/`（六门流水线）；外部研究报告 9 份在 `temp2/外部项目研究/`。大体积产物已 gitignore，可按各报告②节重建。

## 六、开发波次（只讲依赖，不讲时间）

| 波次 | 内容 | 完成判据（DoD） |
|---|---|---|
| **波次 1 · 地基固化** | ①`cargo fmt` 全量格式化一次（CI 骨架 fmt 门现红：235 块预存 diff）②根 Cargo.toml 收编 [workspace.dependencies] ③预算整数化（credential×meter 词表对齐）④af-workorder 接 af-calendar、FNV 占位换 SHA-256/BLAKE3、ed25519 从 credential 下沉 ⑤计时换单调钟 ⑥CUE 预编译 CI 化（**按新裁决：引用完整性移入装载器 E2001，CUE 去 or() 组合**）+ CEL 内嵌 ⑦cargo 反馈阶梯接入（L0 check/L1 fmt+clippy+test 已就绪，配置见 poc-cargo-pipeline 接入清单） | 全 workspace 零警告+clippy 干净；`ci/run.sh` 六门全绿；日历接入后订单 SLA 测试全绿；一条产线定义走通 CUE 预编译管道 |
| **波次 2 · 供给与工位** | af-meter 持久化与多消费者（**分库+outbox 裁决落地，schema 草案见 poc-ledger**）；补 kernelrun 缺口：release-gate/sampling/stop/trace 持久化+凭证根密钥持久形态+首启/重入路径；af-credential 对齐；af-station 接入分派路由与班次日历 | meter 账本成预算真相源；kernelrun 断言套件在重启后全绿（当前仅 2/11 件留痕）；账本×日历×工位联调测试 |
| **波次 3 · 订单主干** | af-workorder 挂 Temporal（**薄壳形态：Rust 判定引擎 bin + Python 编排，bridge 引擎为蓝本**；四约定落实）；af-effect-gateway 与 af-release-gate 挂工单状态机；WorkOrder 级稳定身份+分片映射 | 订单全生命周期集成测试（含审批门/CAN 分片/副作用幂等/投放闸限流）在 temporal dev server 上全绿 |
| **波次 4 · 外围合龙** | Temporal Rust SDK 深验证（signal/update/CAN）；DSPy 的 Rust IR schema 定稿（**v1 字段清单已可定稿，见 verify-adapter**）；CAS 收尾（Rust 客户端生产化+cosign 镜像签名流水线+scrub 解析器已就绪）；Bifrost 版本钉住与 meter 双层接线（weight+header）；CubeSandbox 集成评估进 Tool broker IDL；trace 双轨（critical 自有+OTel 非关键 lane）；Worker Versioning v2 上线流程化 | Rust worker 跑通完整订单场景；CUE→JSON→内核 的产线定义端到端装载；CAS 签名校验管道 CI 化 |
| **波次 5+** | vLLM（GPU 环境门控）、沙箱产线化、eval 产线试运行（吸收 PenguinHarness 方法论五条）、观察安灯、JIT 护栏（吸收 JIT-Agent 两条纪律进规格）、rekor-tiles trace 审计链（轻部署形态已验证）、ClickHouse MES 建库（引擎与批写入参数已裁决）——按拍板版 M4/M5 语义推进 | 见拍板版对应节 |

每波结束：全量测试绿 + 增量 RESULT 回写 + 一次四级漏斗评审（新需求按纪律归位）。

## 七、明日开发启动清单（第一小时就能动手）

1. `cd af && source ~/.cargo/env && cargo test -j 6`（确认全绿起点）；
2. 按 README「波次 1 首批任务」逐项开工（五项，每项都指向具体 crate 与 RESULT.md）；
3. 新增需求一律走四级漏斗（拍板版 §2.4），否决入日志；
4. 每完成一项：git commit（规约见 README）。

## 八、文档地图

| 文档 | 作用 |
|---|---|
| 产品设计_拍板版.md | 产品根本法（三无关/九宪法/九判据/四层形态/13 抽象+13 机制）——已含四项新决定 |
| 底座设计纪律_v2.1修订案.md | 反特化纪律细则+红队复核记录 |
| Agent工厂设计_v2.md / 选型终局建议_第三轮.md / 采纳决策清单.md | 设计全貌/选型证据链/专家与对标吸收 |
| af/BOOTSTRAP.md + 各 RESULT.md + poc/POC_SUMMARY.md | 环境版本/每件已验证语义/15 项 PoC 汇总 |
