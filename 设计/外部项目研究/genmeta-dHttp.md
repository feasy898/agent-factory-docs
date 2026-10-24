# 外部项目研究：genmeta/dHttp

> 研究对象：github.com/genmeta 组织的 dHttp（据称"用于支持 agent 拥有身份且互联"）。
> 方法：GitHub API 列组织仓库 → 浅克隆源码 → 代码级 + 文档级评估 → 本机编译/测试验证。
> 评估立场：默认拒绝；一切以效果证据为核心。
> 日期：2026-10-19。所有引用均为本次会话实际读取/运行的记录。

---

## 一、项目是什么

### 1.1 组织全貌

`curl 'https://api.github.com/orgs/genmeta/repos'`（本次会话实际执行）：组织共 **22 个 public 仓库**，org 自述 "Build for omniconnectivity!"，博客 https://www.dhttp.net，注册地香港，2024-05-21 创建。与 dHttp 直接相关的仓库：

| 仓库 | 语言 | Stars | License | 最近 push | 作用 |
|---|---|---|---|---|---|
| **dhttp** | Rust | 3 | Apache-2.0 | 2026-10-16 | 本报告主角：Decentralized HTTP 协议实现（workspace 含 dhttp/home/access/log/api 五个 crate） |
| dquic | Rust | **282** | Apache-2.0 | 2026-10-15 | IETF QUIC 传输协议 async Rust 实现（组织内唯一有社区牵引的项目） |
| h3x | Rust | 8 | Apache-2.0 | 2026-10-12 | zero-copy 异步 HTTP/3 实现 |
| ddns | Rust | 1 | Apache-2.0 | 2026-10-12 | 分布式 DNS（crate 名 `dyns`），E 记录发现协议 |
| daccess | Rust | 0 | Apache-2.0 | 2026-10-15 | crate 名 `access_control`：按名字的访问控制（allow/review/deny），服务 pishoo 网关 |
| pishoo | Rust | 0 | Apache-2.0 | 2026-10-15 | "world's first DHttp gateway"，可部署于任何设备 |
| rankey | Rust | 0 | **MIT** | 2026-10-12 | 密钥生成 / CSR / CA 签名工具（配套发证） |
| gmutils | Rust | 0 | Apache-2.0 | 2026-10-15 | DHttp 网络命令行工具 |
| specs | — | 0 | 无 | 2026-08-10 | **空壳**：全仓只有一个 `# specs` 标题的 README（已完整克隆核实），协议文档实际在 docs.dhttp.net |
| 其他 | — | — | — | — | rustls/qrustls 分叉、rk8s、quic-view、scoop/homebrew 打包仓、r2cn 实习计划等 |

### 1.2 dHttp 的自我定位

README 开篇的叙事非常直白：HTTP 造成了 client/server 的等级制，"servers became the aristocracy… clients remained nameless subjects"，这是 "technological feudalism and data colonialism" 的机器（README.md:15）。DHttp 的对策是 **Decentralized HTTP on QUIC and HTTP/3**：每个端点同时是 client 和 server，域名从服务器延伸到每个端点，"A name for every endpoint… enabling identification, discovery, invocation, authorization, and authentication—all through a simple name. This is DHttp—opening a new era of Omniconnectivity for the Internet of Agents"（README.md:17）。

**关键澄清（对本次选品至关重要）**：这里的 "Decentralized" 指**连通性的去中心化**（客户端可监听、不依赖特权服务器），**不指身份的去中心化**——身份模型是传统 X.509 PKI（见 2.1），没有 DID。它确实瞄准 "Internet of Agents"，但是以"给每个 agent 一个全球可寻址名字 + mTLS 身份"的路径，不是以去中心化身份标识符的路径。

---

## 二、深研：四个技术问题

### 2.1 agent 身份如何建模？——X.509 PKI + mTLS，**不是 DID**

**身份材料 = 一个 profile 目录**。`Endpoint::load("alice.smith~")` 从 `DHTTP_HOME`（默认 `~/.dhttp`）下的身份 profile 读取三件套：`ssl/fullchain.crt`（证书链）、`ssl/privkey.pem`（私钥）、`ssl/stapling.ocsp`（OCSP 装订）（README.md:63-68；dhttp/src/endpoint.rs:159-177）。

**信任锚 = 内嵌的单一根 CA**。`dhttp/root.crt` 在 build 时被解码校验后编入二进制（`DHTTP_ROOT_CA_DER`，dhttp/src/bootstrap.rs；dhttp/bootstrap_config.rs:5 `DEFAULT_ROOT_CA_PEM`），rustls 的 `RootCertStore` 只装这一个根（dhttp/src/trust.rs:30-39）。trust.rs:26-28 白纸黑字："The current embedded certificate is the **transitional genmeta root CA**. It is expected to be replaced by the dhttp.net root CA when the ecosystem switches domains."——**信任锚尚未定型，且由单一厂商 genmeta 运营**。

**双向 mTLS**。`ClientIdentityPolicy::{Optional, Required}`：Optional 时对端有证书就验、没有就放行（匿名对端是合法公民，CONTEXT.md:51-53）；Required 时强制对端证书来自 DHttp 根存储（dhttp/src/trust.rs:18-23, 52-63）。命名对端必须持有效 OCSP 装订；匿名 client 仍验证 server 证书与 OCSP（README.md:67-68）。

**名字系统**。规范化名称 = `.dhttp.net` 结尾的小写 DNS 名，`~` 是 `.dhttp.net` 的速记（`alice.smith~` = `alice.smith.dhttp.net`）（home/src/dhttp_home.rs:23-33；dhttp/src/uri.rs:27-35）。命名空间隔离在 `dhttp.net` 子域下，预置 home/robot/svc/car 等域（ddns/README.md:78-88）。

**稳定身份钉扎**。叶证书的 Subject Key Identifier 扩展被编码为 `sequence:kind_flag:owner_hash` 三段式，owner_hash 是 64 位小写十六进制（SHA-256 量级）（home/src/certificate.rs:102-256）。应用可在发请求前用 `Request::expect_remote_owner_hash(...)` 要求连接对端的 owner hash 等于钉扎值，不等即 `RemoteIdentityChanged` 错误——对连接池化和反向连接同样生效（dhttp/src/endpoint/request.rs:82-90, 155-168）。签名验证走 ring，支持 ECDSA P256/P384、Ed25519、RSA-PSS（home/src/certificate/rules.rs:83-105）。

**发证侧**。证书由 CA 签发，配套工具是 rankey（生成密钥/CSR/CA 签名，MIT license）；pishoo 网关用证书 SKI 里的 owner hash 作 `SubjectId`（daccess/README.md:52-62）。

**小结**：身份层是**工程上合格的传统 PKI**（mTLS + OCSP + SKI 钉扎 + 明确的可选/强制策略），但（a）无 DID、无去中心化标识符；（b）信任锚是单一厂商的过渡根 CA；（c）身份是**长期通信身份**（"拥有身份不意味着已经提供服务"，CONTEXT.md:12-13），不是可衰减、可委托的执行授权——这与我们的 Credential 是两种东西（见第四节）。

### 2.2 互联协议形态？——HTTP/3 over QUIC 的"客户端可监听"扩展，不是新协议

- **应用面就是标准 HTTP**。`Endpoint::listen(scopes, service)` 接受任何标准 Tower service，axum Router 直接挂（dhttp/src/endpoint.rs:230-247；README.md:130-141）。请求/响应是标准 `http::Request/Response`，H3 握手的 `HandshakeSummary` 放进 request extensions 供应用读取已验证对端身份（dhttp/src/endpoint.rs:289；README.md:146-147）。
- **协议强制约束**：服务端校验请求 authority 必须与本端监听名一致，否则回 `421 MISDIRECTED_REQUEST`（dhttp/src/endpoint.rs:267-287）。出站 URI 的 `~` 速记在发送前展开（dhttp/src/uri.rs:14-62）。
- **传输面是自研 QUIC 栈**。dhttp crate 依赖 `qbase/qconn/qtransport/qprotocol/qresolve/qudp/qrecovery/qtls`（= dquic 项目产物，crates.io 上以 q* 名发布）+ `h3x`（H3）+ `qrustls`（rustls 分叉）（Cargo.toml:44-53）。连接池按 `ConnectionKey::{Outgoing, Incoming}` 双向复用（dhttp/src/network.rs:79-98, 119-150）。
- **与 HTTP 的真差异在连通性**：客户端也能 listen（QUIC 双向建连 + NAT 穿越 + STUN + 志愿中继网络）（README.md:33-37；dhttp/src/network/interfaces/nat.rs）。监听范围分 Internal/External（`Scope::Internal | Scope::External`），由端点自选（README.md:134-137；CONTEXT.md:20-30）。

### 2.3 寻址与发现

- **DDns 的 E 记录（EndpointAddress Record）**。RRTYPE = 266（README 明说 "has not yet been assigned by IANA"）。核心是 `EndpointAddr::{Direct{addr}, Mediate{agent, outer}}`：私有网络的端点由一个公网端点做授权中介（"agent"），记录里带端口，所以私有端点不必抢 443（ddns/README.md:52-72）。
- **一名多端、一端多址**。同一名字可对应多个端点（按 device id 区分，如手机+电脑）；同一端点可有多条 E 记录（多网卡/双栈，服务 QUIC multipath）（ddns/README.md:66-72）。
- **自报告发布 + 验签**。端点自己发现并发布自己的 E 记录，网络变化即宣布；经 DoH 发布时 resolver 验证名称合法性与记录内容签名（ddns/README.md:64-65）。
- **解析来源三路**：mDNS（本地，`.dhttp.net` 映射到 `._dhttp.local`）、DoH（查询/发布）、System DNS（普通域名照旧）（ddns/README.md:74-88）。应用显式注册 resolver：`Resolver::add(SystemResolver)` + `H3Resolver::anonymous("https://ddns.genmeta.net")`（README.md:84-88）。
- **判断**：发现层的 bootstrap 依赖 genmeta 运营的公共服务 `ddns.genmeta.net`（协议上任何人可自建 resolver，但默认路径是中心化服务）；E 记录未过 IANA。寻址模型（名字→端点地址集合）设计清晰，但是**厂商私有生态**。

### 2.4 安全模型（认证/授权/衰减）

**认证** = mTLS + OCSP（如 2.1）。证书轮换需要重启进程，`reload()` 只换 OCSP 装订（dhttp/src/network.rs:164-219）。

**授权有两代实现，且都不在内核 crate 里强制**（dhttp crate 只是 `pub use dhttp_access as access`  re-export，dhttp/src/dhttp.rs:34-35；授权由承载应用如 pishoo 接入）：

1. **dhttp-access 0.5.0（workspace 内）——ACL/防火墙范式**：
   - 模型 = location pattern（API 路径 pattern）匹配 + 有序规则集；每条规则 = 布尔表达式 + action。原子谓词只有四类：client name pattern、method、header kv、query kv（access/src/expr/atomics.rs:308-314）；action 只有 `Allow`/`Deny`（connection 级和 request 级各一套，access/src/action.rs:14-65）。
   - 表达式中缀 + 波兰式双表示存 sea-orm 数据库，反序列化时重新解析校验（access/src/expr/exprs.rs:129-164, 225-246）；规则按创建时间倒序，首个命中生效（access/src/db/evaluator.rs:73-81）。
   - **求值失败 fallback = Deny**（access/src/expr/atomics.rs:105-110）——宁错拒不放，这一点与我们的"超时安全缺省是拒绝"同构。
   - **pattern 编译用 regex-automata DFA 并做可达性验证**：保证线性时间匹配（防 ReDoS），且验证 pattern 与合法输入语言有非空交集（防空匹配规则）（access/src/pattern/reachability.rs:1-50）——这是值得抄的工程质量实践。
2. **daccess 0.1.1（独立 crate `access_control`，更新、更完整）**：
   - **三态决策** `allow / review / deny`（daccess/src/policy.rs:9-13）。
   - 输入 = 经 mTLS 验证的来访者名称 + `SubjectId`（证书 SKI 的 64 字符 owner hash）+ method + path；名称与 SubjectId 必须同时存在或同时缺失（daccess/README.md:52-62；SPEC.md §7.1）。
   - 默认 **deny all、allow profile owner**；路径最长匹配逐段回退；方法具体优先于 `*`；grantee 优先级：精确名称 > `**`（所有命名来访者）> `*?`（匿名）；全不命中即 deny（SPEC.md §7.2-7.3）。
   - **SubjectId 复核**：已知名称但 SubjectId 变了 → 转 review（原因 `subject_id changed`）（SPEC.md §7.4）。
   - **异步审批**：命中 review 立即返回 `202 Accepted` + `status_url`；pending 有效期 1 天；`allowed` 决定被一次性原子消费，调用方用相同请求字段重试（SPEC.md §8.1）。管理队列只展示未过期 pending（§8.2）。
   - **联系人交换协议**：申请（按 API 聚合的权限请求）/批准/拉黑/恢复；7 天有效期；`offers`/`granted_access` 权限声明交换；本地批准不访问网络，申请方上线后自行拉取状态（SPEC.md §9）。
   - 每 profile 独立 SQLite + 内存索引；管理 API 可挂 axum Router（daccess/README.md:66-78）。

**这个安全模型里没有什么**（与我们对照的关键）：
- **没有能力衰减/委托链**：没有 biscuit 式的"派生子 agent 只能收紧不能放宽"；daccess 的联系人审批是**人审**，不是密码学委托。
- **没有预算/计量维度**：授权判定只看名称/路径/方法，不看资源消耗。
- **没有 trace 完整性**：`dhttp-log` 只是通信日志的格式化原语（64KiB ASCII 行记录、访问日志字段），无签名、无 Merkle、无锚定（log/src/record.rs:8-20）。
- 隐私立场是产品叙事的一部分（README.md:15 的"data colonialism"论调），本地优先（mDNS 优先、本地网络优先，ddns/README.md:88）。

---

## 三、成熟度与效果证据

**我在本会话实际执行的检查**（沙箱备注：`/tmp` tmpfs 被并行会话占满触发磁盘配额，首次克隆被清、后续下载改到 home 盘；这不影响项目本身判定）：

| 检查 | 命令 | 结果 |
|---|---|---|
| 编译 | `cargo check --locked --workspace`（dhttp 仓库根，rustc 经 ~/.cargo/bin） | **exit 0**，1m13s；workspace 五个 crate + q* QUIC 栈 15+ 依赖全部编译通过 |
| 测试 | `cargo test --locked --workspace --all-features -- --test-threads=1`（README.md:210 记载的命令） | **257 passed / 0 failed / 3 ignored**（exit 0）。3 个 ignored 为需 OpenSSL 与本地 UDP socket 权限的真实 QUIC 测试（dhttp/tests/dns_bootstrap.rs 等），沙箱内跳过 |
| 环境排除 | 首跑 1 个 listener 测试报 `Os { code: 122, QuotaExceeded }`，定位为 `std::env::temp_dir()` 写在配额耗尽的 /tmp；`TMPDIR` 换 home 盘后该测试单独重跑通过 | 失败归因为**沙箱环境问题，非项目缺陷** |

**元数据证据**：

- **体量与工程**：157 个文件、20,509 行 Rust；36 个文件含测试；CI 覆盖 Linux GNU/musl、macOS、Windows + iOS 设备/模拟器 + 四个 Android ABI（README.md:199-217）；SPEC 级文档（daccess/SPEC.md 878 行）；错误处理用 snafu 成体系。
- **发版节奏**：crates.io `dhttp` 自 2026-06-15 首发，共 **20 个版本**，最新 0.7.1（2026-10-14）；GitHub tags 从 2026-07 到 2026-10 密集（v0.7.1 = Oct 15, 2026；v0.7.0 = Oct 12；v0.6.2 = Aug 19……）。**开发活跃**。
- **社区采用度**：dhttp **3 stars / 0 forks / 267 commits**（WebFetch github.com/genmeta/dhttp，2026-10-19）；`git shortlog -sn`（完整克隆）：**4 个贡献者——eareimu 189 commits（71%）、metah3m 70（26%）、huster-zhangpeng 7、passion 1**，首个 commit 2026-04-24，即项目实际年龄约 6 个月、实质是 2 个开发者；crates.io 总下载 **2,713**（recent 1,958）。同组织 dquic 282★ 是社区牵引主力，dhttp 本身几乎没有外部使用者证据。
- **License**：Apache-2.0（rankey 为 MIT）；specs 仓无 license 且为空壳。

**结论**：**工程质量证据强**（我跑通了编译和 257 个测试、发版节奏快、文档/CI/错误处理严谨）；**采用度证据弱**（3★、2 个主要开发者、千次下载、生产使用者不可考、信任锚是单一厂商过渡 CA）。作为"可学习的工程"它及格；作为"可托付的依赖"它远未证明。

---

## 四、与我们底座的对照：互补还是竞争

我们的对照基线（产品设计_拍板版.md）：Credential = 全厂唯一签发点签发的短期凭证，编码工具白名单/工件命名空间/模型端点/多维资源预算，**派生子 agent 时凭证只能收紧不能放宽**，过期自动作废，有效权限 = 策略引擎允许 ∩ 凭证持有（§4-4，:103）；机制含凭证衰减；Trigger = webhook/定时/信息源变化自动派生订单，**事件是消息不是命令**（§4-8，:110）；Channel = 流式产物通道（§4-9，:111）；Resident Agent = 产品级身份租约（§4-10，:112）。

### 4.1 与 Credential：层次不同， mostly 互补，不构成替代

| 维度 | 我们的 Credential | DHttp 身份层 |
|---|---|---|
| 证明什么 | 这个 Run/agent **能干什么、花多少** | 这个对端**是谁**（alice.smith）、能否调这个 API |
| 形态 | biscuit 衰减令牌 + cedar 策略 + 唯一签发点 | X.509 证书 + mTLS + OCSP + SKI 钉扎 |
| 委托/衰减 | 一等概念：子 agent 只能收紧 | **不存在**；daccess 审批是人审不是密码学委托 |
| 预算 | token/GPU 时/沙箱并发/人时，可声明维度 | 无 |
| 生命周期 | 短期、过期作废 | 长期通信身份，OCSP 吊销 |

**互补面**（我们缺的正是它有的）：
- 我们当前只有**内核内**凭证，没有"agent 的**对外可寻址身份**"。若产品走到"agent 在 Internet of Agents 里被按名寻址、双向收请求"，DHttp 的命名 + mTLS + E 记录 + NAT 穿越正是那一整层，自己从零造的工作量以人年计。
- Resident Agent 的"产品级身份租约"（:112）可以用 DHttp 命名身份做**对外呈现**；凭证与预算仍归内核 Credential。两层不互斥。
- Trigger 的一种可选 transport：入站请求到达具名 endpoint ≈ webhook 型触发的承载方式——且它天然带 mTLS 身份，比裸 webhook 强。
- daccess 的 `allow/review/deny` 三态 + 202 异步审批 + 超时缺省拒绝，与我们的 Evaluation 三态（通过/不通过/需人工，:105）和 Human Station（超时安全缺省是拒绝，:114）**语义同构**，可作为我们"入站请求授权"配方的设计参照。
- 可抄的工程实践：DFA + 可达性验证的 pattern 引擎（线性时间、防 ReDoS、防空匹配）；SKI 三段式编码（sequence:kind:owner_hash）把"身份钉扎"做进证书扩展的思路。

**竞争面**：几乎不存在直接竞争——DHttp 没有工件内容寻址、TaskGraph、Trace 完整性、评估、预算、编排、CONWIP 中的任何一个。唯一形态重叠区是"入站事件入口"（DHttp 入站请求 vs 我们的 Trigger/Channel），但那是 transport 与机制的层次差，不是同一层的两个选择。

### 4.2 "凭证子系统整体换它或对接它"是否成立？——**不成立**

运营者允许考虑这个方向，但按效果证据裁决：

1. **语义不对齐（致命）**：我们 Credential 的核心卖点是衰减委托（子 agent 只能收紧）+ 多维预算 + cedar 策略组合。DHttp 身份层这三样都没有——换过去等于**丢掉衰减与预算语义**，只剩"证明你是谁"。它是网络准入，不是执行授权。
2. **信任层纪律不容**：设计文档 :45 明确"凡被声明为信任层的组件（凭证签发、预算记账、trace 完整性），无论部署在哪里都同等保证完整性，且信任边界的声明本身是显式配置"。凭证签发正是信任层。DHttp 的根 CA 是单一厂商 genmeta 的**过渡**根（trust.rs:26-28 明说未来还要换 dhttp.net 根），把它作为凭证子系统的信任锚，违背信任边界显式声明与第二运营者测试（:56）。
3. **成熟度不匹配**：3★、2 个主要开发者、crates.io 下载 2,713、生产使用者不可考——不足以承载安全核心组件。它的工程质量和它的生态采用度是两回事，前者我验证了，后者不存在。

**对接**则有一个诚实成立的窄口径：若（且仅若）未来出现"agent 需要公网可寻址身份并被外部调用"的**真实场景**（按 rule of three，第三个独立场景真实出现才固化，:63），以 **L2 适配器**形态接入——DHttp 作为 Trigger/Channel 的一种 transport + Resident Agent 对外身份载体，内核 Credential/Channel/Trigger 抽象零改。这是 L2 决策，永远不需要升级为内核机制。

---

## 五、评估四问与结论

**① 替我们省了什么**：只有当我们决定做"agent 公网互联"时，它才省掉自造 QUIC/NAT/mDNS/DoH/PKI/OCSP 全栈（人年计）。但一期没有任何场景需要它：我们的 Trigger 是工厂内部事件（webhook/定时/信息源变化，:110），Channel 是内部产物流，运营者部署（本地/云/混合）里没有"agent 在公网被按名调用"的需求证据。省下的正是我们现在不花的东西。

**② 效果证据**：工程质量侧——我跑通 `cargo check --locked --workspace`（exit 0）与 README 记载的 `cargo test --locked --workspace --all-features -- --test-threads=1`（257 passed / 0 failed / 3 ignored，3 个 ignored 需 OpenSSL+UDP 权限）；发版节奏快（4 个月 20 版）。采用度侧——3 stars、0 forks、267 commits、4 贡献者（2 人占 96%）、下载 2,713、单一厂商过渡根 CA。**作为信任层候选：证据不足。作为 L2 可选 transport 的储备：证据够记档。**

**③ 引入成本**：语言一致（Rust，Apache-2.0）是唯一减负。但它是**一整套平行宇宙网络栈**：q* 系列 15+ crates（dquic 分叉）+ qrustls（rustls 分叉）+ h3x，与主流 quinn/h3/rustls 生态完全分叉；运维半径包括 genmeta 运营的 `ddns.genmeta.net` bootstrap 服务、根 CA 轮换（未定型）、E 记录（IANA 未分配）、iOS/Android 构建链。任何"整体换栈"都是把网络栈锁死在一个 3★ 项目上。

**④ 对接哪层 + 退出成本**：正确位置是 **L2 适配器**（transport 插件，只翻译不决策，:89）——退出成本低，换 transport 即可，内核零改。任何深入内核的对接（改 Credential/Trigger/Channel）都违反适配器边界与内核预算测试（:59）。

### 结论

**不引入**。理由浓缩：DHttp 是一个工程质量合格（我验证了编译与 257 测试全绿）但生态采用度极低（3★/2 开发者/2.7k 下载/单一厂商过渡根 CA）的 QUIC 时代 HTTP 扩展栈；它的身份层是传统 PKI + mTLS 的**网络准入**，与我们 Credential 的**衰减执行授权**是不同层的东西，既替不了也无衰减/预算语义；它的发现层依赖厂商运营的公共服务、E 记录未过 IANA。按默认拒绝姿态与效果证据标准，不引入。但记两条档：（a）**设计借鉴**（非代码引入）：daccess 的 allow/review/deny 三态 + 202 异步审批 + SubjectId 变更转审，可作我们入站授权与 Human Station 配方的参照；pattern 引擎的 DFA + 可达性验证（防 ReDoS/空匹配）值得规则引擎借鉴。（b）**未来窄口径**：若"agent 公网可寻址身份"出现第三个独立真实场景，以 L2 适配器（DHttp 作 Trigger/Channel 的一种 transport + Resident Agent 对外身份）小规模试点，内核不动。

---

## 附：本次研究的证据清单

- `curl 'https://api.github.com/orgs/genmeta/repos'`（22 仓库清单，本会话执行）
- dhttp 仓库：tarball（codeload, main）+ 完整克隆（`git shortlog -sn` → 4 贡献者；`git rev-list --count HEAD` → 267）
- 实读文件：README.md、CONTEXT.md、Cargo.toml、CHANGELOG.md、dhttp/src/{dhttp.rs, uri.rs, trust.rs, bootstrap.rs, endpoint.rs, endpoint/request.rs, network.rs}、home/src/{certificate.rs, certificate/rules.rs, dhttp_home.rs, identity.rs}、access/src/{action.rs, expr.rs, expr/exprs.rs, expr/atomics.rs, db/evaluator.rs, matcher.rs, pattern/reachability.rs}、log/src/{record.rs, access.rs}、api/Cargo.toml
- ddns/README.md（E 记录模型）、daccess/{README.md, SPEC.md, src/policy.rs}（三态授权与审批/联系人协议）
- specs 仓库完整克隆核实为仅含 `# specs` 标题 README 的空壳
- 运行：`cargo check --locked --workspace`（exit 0）；`cargo test --locked --workspace --all-features -- --test-threads=1`（257 passed / 0 failed / 3 ignored）；失败测试经 TMPDIR 重定位后复跑通过，归因沙箱 /tmp 配额
- crates.io API：`dhttp` 20 版、下载 2,713（API 无鉴权端点实际返回，HTTP 200）
- GitHub API 贡献者端点限流（HTTP 403 rate limit）→ 改用完整克隆的 git shortlog 获得贡献者证据；gh CLI token 无效（已记录，未使用）
