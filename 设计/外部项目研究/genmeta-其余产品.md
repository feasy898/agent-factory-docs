# 外部项目评审：github.com/genmeta（dHttp 以外全部产品）

> 评审立场：默认拒绝，一切以效果证据为核心。评审日期 2026-10-19。
> 研究对象：`github.com/genmeta` 组织 **除 `dhttp` 外的全部 21 个仓库**（dHttp 由另一代理并行深研，本报告不重复）。
> 对照基线：`/home/pan-ding/workspace/临时工作区/temp2/产品设计_拍板版.md` §1–2 已读（13 抽象 / 13 机制 / 四层形态 / 三无关纪律）。
> 代码证据获取方式：`git clone --depth 300` + `codeload.github.com` tarball 至 `~/tmp-extresearch/`，逐文件阅读后删除。文末附完整命令与原始输出。

---

## 一、项目是什么：组织全貌

### 1.1 组织是什么

Genmeta 是一个做 **DHttp（去中心化 HTTP）** 的单厂商组织，组织 profile（`.github/profile/README.md:1-8`）自述两条纲领：

> **⚖️ Clients are servers; all endpoints are created equal.** / **🏷️ Domains are IDs, and everything can be named.**

产品叙事是"把域名推广到任何一个设备上"：每个端点有自己的域名与 X.509 证书，既能呼叫也能应答，跨 NAT／私网／IPv4-IPv6 点对点直连（`.github/profile/README.md:10-12`）。技术栈是 **QUIC + HTTP/3 + mTLS + DNS 扩展**，外加一层 Nginx 类网关和一套 CLI。

### 1.2 全部 22 个仓库清单（按 stars 排序）

来源：`curl -s 'https://api.github.com/orgs/genmeta/repos?per_page=100'`

| # | repo | stars | forks | 语言 | license | created | pushed | 性质 |
|---|---|---|---|---|---|---|---|---|
| 1 | `dquic` | **282** | 24 | Rust | Apache-2.0 | 2024-06-21 | 2026-10-15 | 自研 |
| 2 | `h3x` | 8 | 0 | Rust | Apache-2.0 | 2025-10-09 | 2026-10-12 | 自研 |
| 3 | `dhttp` | 3 | 0 | Rust | Apache-2.0 | 2026-04-24 | 2026-10-16 | 自研（**本报告范围外**） |
| 4 | `ddns` | 1 | 1 | Rust | Apache-2.0 | 2025-04-20 | 2026-10-12 | 自研 |
| 5 | `pishoo` | 0 | 0 | Rust | Apache-2.0 | 2025-01-24 | 2026-10-15 | 自研 |
| 6 | `quic-view` | 0 | 0 | TypeScript | **NOLICENSE** | 2025-03-11 | **2025-03-11** | 自研·已死 |
| 7 | `gmutils` | 0 | 0 | Rust | Apache-2.0 | 2025-04-21 | 2026-10-15 | 自研 |
| 8 | `rankey` | 0 | 0 | Rust | MIT | 2025-09-09 | 2026-10-12 | 自研 |
| 9 | `rk8s` | 0 | 0 | — | Apache-2.0 | 2025-09-25 | **2025-09-25** | **fork**·已死 |
| 10 | `dssh` | 0 | 1 | Rust | **NOLICENSE** | 2025-09-28 | 2026-08-19 | 自研 |
| 11 | `r2cn` | 0 | 0 | — | Apache-2.0 | 2025-11-06 | **2025-11-06** | **fork**·已死 |
| 12 | `genmeta-xtask-release` | 0 | 0 | Rust | Apache-2.0 | 2026-07-01 | 2026-10-15 | 自研·内部工具 |
| 13 | `homebrew-stable` | 0 | 0 | Ruby | NOLICENSE | 2025-05-26 | 2026-08-31 | 打包仓 |
| 14 | `homebrew-preview` | 0 | 0 | Ruby | NOLICENSE | 2026-07-02 | 2026-10-15 | 打包仓 |
| 15 | `scoop-Extras` | 0 | 0 | PowerShell | Unlicense | 2025-08-25 | 2025-08-25 | **fork**（Scoop 官方 extras bucket） |
| 16 | `scoop-preview` | 0 | 0 | — | NOLICENSE | 2026-07-02 | 2026-08-28 | 打包仓 |
| 17 | `scoop-stable` | 0 | 0 | — | NOLICENSE | 2026-07-02 | 2026-08-31 | 打包仓 |
| 18 | `specs` | 0 | 0 | — | NOLICENSE | 2026-07-21 | 2026-08-10 | **空壳**（见 §2.11） |
| 19 | `.github` | 0 | 0 | — | Apache-2.0 | 2026-07-30 | 2026-07-30 | 组织 profile |
| 20 | `daccess` | 0 | 0 | Rust | Apache-2.0 | 2026-08-05 | 2026-10-15 | 自研 |
| 21 | `rustls` | 0 | 0 | Rust | NOASSERTION | 2026-09-03 | 2026-10-09 | **上游同步 fork** |
| 22 | `kundy-bootstrap` | 0 | 0 | Rust | NOLICENSE | 2026-09-10 | 2026-09-14 | 自研·**单次提交** |

**排除后本报告覆盖 21 个仓库。**其中 4 个是 fork（`rk8s`/`r2cn`/`scoop-Extras`/`rustls`），4 个是打包仓（`homebrew-*`/`scoop-*`），1 个是空壳（`specs`），1 个是组织 profile（`.github`）——即 **10/21 属"不值得独立评估"的低价值仓**，下文仍逐个给出理由（§2.12–2.13）。

### 1.3 一句话结论（先给结果）

> **这是一家公司的网络协议栈产品线，不是一条与"Agent 工厂底座"相邻的技术线。**
> 21 个仓库中，**没有一个**对应我们的 13 抽象或 13 机制中的任何一件（逐条对照见 §4）。
> 唯一有语义交集的是 `daccess` 的**三态授权**（allow / review / deny），它与我们的 **Evaluation 三态（通过／不通过／需人工）** 属同一族设计——但那是**设计模式**的借鉴，不是代码可引入。
> **最终裁决：部分引入（只借一个设计模式，零行代码）。**

---

## 二、逐仓库深研（按价值降序）

### 2.1 `dquic` — 唯一有真实外部信誉的资产（**观望**）

**是什么**：IETF QUIC 传输层实现，扩展了 NAT 穿透与多路径。核心创新是 `ep-&EP` 配对模型：私网端点 `ep` 与一个公网委托端 `&EP` 配对，`&EP` 只在 IP 层转发直到直连路径建立，随后降级为中继（README.md:21-49）。工作区 14 个 crate：`dquic/qbase/qrecovery/qcongestion/qprotocol/qdatagram/qconnection/qtls/qtransport/qtraversal/qresolve/qevent/qmacro/qudp`（`Cargo.toml:3-18`）。

**读了什么**：README.md、CONTEXT.md（自维护的领域术语表，含 AddressBook／BindUri／PathCids／本地绑定等定义）、Cargo.toml 工作区、CI workflow 列表、测试计数。

**成熟度（证据）**：
- 提交：300 次提交集中在 2026-01-28 → 2026-10-12（8.5 个月），**8 名人类作者**（`git shortlog -sne`）。
- 代码：**78,815 行 Rust**；`grep -rc '#[test]'` 合计 **709 个测试**。
- 发版：tag 至 `v0.8.1`；crates.io `dquic 0.8.1`，**4,274 次下载**（2026-10-12 更新）。
- CI：`.github/workflows/` 含 `rust.yml`、`traversal.yml`、`codecov.yml`、`publish-crates.yml`、`commitlint.yml`。
- 外部贡献者：近 300 次提交中含 `Ayrton Sparling`、`Borber`（非 @genmeta 邮箱），说明被协议社区使用过。

**替我们省了什么**：零。我们的栈里没有任何一件需要自研 QUIC；若真需要 QUIC，rustls-ecosystem 的 `quinn` 是默认选择。

**为什么仍是观望而不是引入**：`dquic` 的差异化价值全部在 **NAT 穿透 + 去中心化寻址 + 多路径**——这解决的是"内网里的 agent 端点如何被外部触达"。我们的部署形态问题（宪法 5）在设计上被明确判为**运营者配置**，交付物是内核 + 配方 + 适配器 SDK（拍板版 §1.5 条），不是一个 P2P 网络。**引入它等于给产品加一条我们明确声明不做的路线。**

**引入成本**：Rust 2024、无 C 依赖（`qtls` 走 crates.io 的 `qrustls`）——成本低；**但引入的理由不存在**。若未来某个运营者真的要跑"内网 agent 端点被公网触达"的形态，正确做法是 L2 适配器里挂 `quinn`/反向隧道，而不是把 `dquic` 打进内核（否则内核就被特化，`判据 9 第二运营者测试`会立刻失败）。

### 2.2 `pishoo` — DHttp 网关（**不引入**）

**是什么**：Nginx 类网关（Web 服务／反向代理／负载均衡／NAT 穿透），特点是**可部署在任意无公网 IP 的设备上**；0.9 版本采用 per-identity SQLite 配置、名字访问控制与 WASM 组件（README.md:39-41「Pishoo 0.9 uses per-identity SQLite configuration, name-based access control, and WASM components」）。

**成熟度**：302 次提交（2026-03-19 → 2026-10-15），8 名作者，28,320 行 Rust。**0 stars，未发布到 crates.io**（`crates.io/api/v1/crates/pishoo` 返回无此 crate）。构建需要 Rust 1.97.1 + Bun 1.4.2 + Node 23.11.0 + 原生 C/C++ 工具链（README.md:47-52）——工具链偏重。

**对照**：它做的是"把本地服务暴露到网络上"的入向流量治理。我们的 `Delivery` 抽象（第 11 条）是**出库**语义：出库清单 + 发布投影 + 产品遥测回连，不是入站网关；我们的 `Sandbox`（第 7 条）是隔离执行，不是代理。**语义不同向，零交集。**

**低价值理由**：解的是我们没有的问题（内网服务暴露），且构建链与我们的 Rust 内核基线冲突（Bun/Node/C++）。

### 2.3 `ddns` — DHttp 的 DNS 解析层（**不引入**）

**是什么**：为 DHttp 解析名字到 `EndpointAddr`（E 记录，Direct 或 Mediate 形态），支持 DoH3／DoH／mDNS，含 resolvers 与 publishers（README.md:20-22）。

**成熟度**：298 次提交（2025-04-20 → 2026-10-12），7 名作者，9,369 行 Rust，**99 个测试**。crates.io 发布名为 **`dyns`**（0.8.0，3,988 下载）——注意 `crates.io/crates/ddns` 这个名字**属于另一个仓库**（`lvillis/ddns-rs`，1,387 下载），我们若引用需注明是 `dyns`。

**对照**：我们的 `Trigger` 抽象（第 8 条）允许 webhook／定时／信息源变化派生订单，但**不涉及 DNS 发现**；DHttp 名字体系是这套协议的必需件，而对我们不是。零交集。

### 2.4 `h3x` — HTTP/3 库（**不引入**，且官方劝退）

**是什么**：为 `dquic` 实现的零拷贝 HTTP/3 库（15,930 行 Rust）。README 第一段就写着：

> "It is not recommended for direct use; use dhttp instead."（`README.md:14`）

**成熟度**：200+ 次提交（2026-05-27 → 2026-10-12），4 名作者；crates.io `h3x 0.7.0`，**4,489 次下载**。CHANGELOG 0.7.0：「Rework native HTTP/3 streams, QPACK feedback and cancellation」。

**低价值理由**：①官方明确劝退直接使用；②我们的 HTTP 出口由模型网关（Bifrost）与沙箱协议承担，不需要自控 HTTP/3；③零拷贝能力对我们无收益——我们是控制面调用，不是高 QPS 数据面。

### 2.5 `daccess` — 三态名字访问控制（**部分引入：只借设计，不引代码**）

这是本组织**唯一与我们抽象有语义交集**的仓库，因此读得最深。

**是什么**：与传输协议解耦的名字访问控制库（crate 名 `access_control`，包名 `daccess`，v0.1.1，Apache-2.0，6,871 行）。按**已 mTLS 认证的来访者名字 + 证书 SubjectId + HTTP method + API 路径**作出 `allow`／`review`／`deny` 三态决策，并提供联系人、规则与审批管理 API（README.md:3-5）。

**关键源码证据**：

1. **三态枚举**（`src/policy.rs:9-14`）：
   ```rust
   pub enum Effect { Allow, Deny, Review }
   ```
   规则四元组 `(method, api, grantee, effect)`，同一 `(grantee, method, api)` 至多一条（SPEC.md「2. 术语」）。

2. **grantee 的三档回退**（`src/service.rs:186-189`）：已命名来访者按 `One(name)` → `Named` → `All` 逐级放宽；匿名只能 `Anony` → `All`。

3. **"名字没变但主体变了 ⇒ 撤销已授予的 allow"**（`src/service.rs:195-206`）：
   ```rust
   let subject_changed = ... .get(name).is_some_and(|known| known != subject_id);
   let reason = match policy_effect {
       Effect::Allow if subject_changed => String::from("subject_id changed"),
       Effect::Allow => return Ok(AuthResult::Allowed),
       Effect::Deny    => return Ok(AuthResult::Denied),
       Effect::Review  => format!("matched review rule: ...")
   };
   ```
   **这是本仓库唯一真正值得抄的东西**：授权不只绑定名字（可转让的易变量），还绑定一个密码学主体标识；名字复用而密钥已换 ⇒ 旧授权立即失效。

4. **"需人工"永不阻塞业务请求，且失败方向是关闭"**（`src/service.rs:216-236`）：匿名请求命中 `review` 直接返回 `Denied`（fail closed），有身份的请求落一条持久审批记录后返回 `Reviewing`。README：「异步持久审批：业务请求立即返回 `202 Accepted`，由调用方查询状态后重试」。

5. **决定一次性消费**（`src/service.rs:248-253`）：`DELETE FROM access_reviews WHERE visitor = ? AND request_id = ? AND visitor_sid = ?` 在事务内先删后判——同一决定不能用第二次。

6. **最后一名管理员保护**（README.md「直接管理规则」）：`set_policy`/`remove_policy` 在同一事务内校验管理 API 至少还剩一位有 allow 权限的具名管理员，否则拒绝提交——防把自己锁在门外。

**成熟度**：**19 次提交，4 名作者，2026-08-05 → 2026-10-15（两个半月）**；67 个 `#[test]`（`src/api/contact.rs` 27、`src/service.rs` 16、`src/api/access.rs` 9）。crates.io `daccess 0.1.1`，**220 次下载**。依赖：`axum 0.8` + `sea-orm 2 (sqlx-sqlite)` + `radix_trie` + `sha2`。

**为什么只借设计、不引代码（决定性理由）**：它的判定逻辑 `self.policies.read().await.evaluate(&method, &api, &grantees)`（`src/service.rs:190-194`）是**写死在 Rust 里的 radix-trie 最长前缀匹配 + 硬编码的 grantee 回退序**。我们宪法 9 的判据「默认即数据测试」明写：*内核代码里出现策略常量（阈值、系数、枚举、写死的状态流转）即缺陷*。把 `daccess` 当内核引入，等于把一份策略实现焊进 L1 —— 它的规则表也不是我们的配方 DSL（CUE/CEL 受限 DSL），而是 SQLite 行。**引入它会直接违反我们已拍板的两条纪律（判据 5 机制/策略分离、判据 9 默认即数据）。**

**借什么（三条，可直接写进我们的机制设计）**：

| 借的东西 | 落到我们的哪一层 | 具体落点 |
|---|---|---|
| 授权绑定"名字 + 主体标识"双因子，主体变更即撤权 | L1 `Credential` + `Human Station` | 人工工位里"评审员 Alice"的角色授予不能只存名字，须存凭证主体标识；凭证轮换/转交后旧授权自动失效 |
| 三态（allow／deny／**review**）且 review 永不阻塞、失败方向 fail-closed | L1 `Evaluation` + 决策工件 | 与我们已有的"通过／不通过／需人工"三态同构；补一条约束：**匿名或凭证已失效的请求不得进入"需人工"，必须直接判不通过** |
| 决定一次性消费 + 最后一名管理员保护 | L1 决策工件 / `WorkOrder` 变更单 | 审批工件只能被消费一次（重放防护）；撤销权限的工单必须校验不会移除最后一位有权签发者 |

这三条属于"设计模式借鉴"，对应拍板版 §2.4 的**四级漏斗第二级（升格为新机制前先在配方层兜着）**语境——它们是既有机制的加固，**不新增机制件数，不动 26 件基线**。

### 2.6 `rankey` — X.509／OCSP 库（**不引入**，且与我们的凭证模型冲突）

**是什么**：1,274 行 Rust 的证书工具库，`secp384r1` 密钥生成、CSR 创建、CA 签发叶子证书、证书信息提取、OCSP 响应（good/revoked/unknown）签发（README.md:5-9）。MIT license，v0.3.0。

**API 面**（`src/lib.rs`）：`generate_secp384r1_key():81`、`generate_csr():103`、`sign_certificate():165`、`sign_good_ocsp_response():239`、`sign_revoked_ocsp_response():259`、`sign_unknown_ocsp_response():299`、`extract_certificate_info():494`。9 个测试（`src/lib.rs:630-876`）。私钥用 `Zeroizing<String>` 承载（README.md:11）——细节做对了。

**成熟度**：26 次提交，4 名作者，2025-09-01 → 2026-10-12。crates.io `rankey 0.3.0`，939 下载。

**为什么冲突（这是重点，不是"太小"）**：我们的 `Credential` 抽象（第 4 条）明确要求"全厂唯一签发点签发的短期凭证，派生子 agent 时凭证只能收紧不能放宽，过期自动作废"——这是**能力式（capability）凭证**模型，语义就是 biscuit。`rankey` 提供的是**身份式 PKI**：需要 CA、需要吊销列表、需要 OCSP responder、需要 SubjectId 与证书生命周期对齐。而 DHttp 生态选 X.509 的原因是**端到端 mTLS 互认身份**（`.github/profile/README.md:11`「every endpoint gets a domain name and a PKI certificate」），这是它的协议前提，不是通用需求。

**结论**：引入它等于把我们的凭证层从能力式降级为身份式——撤销机制从"过期即失效"变成"过期前还得查吊销"。**能力更强的东西被更弱的东西替换，是负收益。** 且我们的 Trace 签名（Merkle + 签名 + 外部见证）由 cosign/rekor 承担，不需要自建 CA。

### 2.7 `gmutils` — CLI 工具族（**不引入**）

**是什么**：9 个 crate 的命令行工具家族（`genmeta/Cargo.toml:4-14` 的 workspace members），统一入口 `genmeta <tool>`：`identity`／`access`／`curl`／`proxy`／`nslookup`／`discover`／`doctor`／`package`（README.md:22-31）。

**成熟度**：445 次提交（2026-03-11 → 2026-10-15），**10 名作者**——组织内最活跃的仓库之一。76 个 Rust 源文件。各工具单独发 crates.io：`genmeta` 412／`genmeta-curl` 389／`genmeta-identity` 523／`genmeta-access` 384／`genmeta-ssh` 409 次下载，版本均为 `0.x.0-preview.N`。

**低价值理由**：这些工具 100% 操作 DHttp 身份与 DHttp 服务（激活码、CertServer、`~/.dhttp` Home、`db/access.db`）。我们没有 DHttp 概念，`genmeta-curl` 这类东西对我们的唯一用途是"零"。发布状态全是 `preview`，也说明 API 未冻结。

### 2.8 `dssh`（crate 名 `dshell`）— 远程 shell（**不引入**，且有法务瑕疵）

**是什么**：基于 `h3x` 的远程 shell：session/channel/wire-format 基础，WebTransport 承载，16,750 行 Rust。

**关键源码**：
- 认证只有两档（`src/auth.rs:12-25`）：`Basic { username, password }` 与 `Certificate`（mTLS 已在传输层验过）；`parse_authorization_header` 只认 `Basic`（`src/auth.rs:41-73`）。
- `src/lib.rs:22-31` 有一条**用源码文本自检**的测试，断言"dshell transport must stay WebTransport-only"。

**成熟度**：200+ 次提交（2026-03-18 → 2026-08-19），3 名作者。**仓库根目录没有 LICENSE 文件**（GitHub API 亦返回 `NOLICENSE`），但 `Cargo.toml:7` 声明 `license = "Apache-2.0"`——**声明与实际授权文本不一致，任何引入都带法务不确定性。**

**低价值理由**：我们的沙箱（`Sandbox`，第 7 条）已由 E2B 承担执行隔离；远程交互式 shell 是给人用的终端形态，而我们的"人在环"是 **Human Station 的工单账本**（技能路由 + SLA + 修订语义），二者形态不同。能力式凭证（biscuit）与"用户名 + 口令"也方向相反。

### 2.9 `genmeta-xtask-release` — 内部发布工具（**不引入**）

**是什么**：14,141 行 Rust 的发布打包"契约 + 规划"库，覆盖 deb／rpm／brew／scoop／S3 发布、manifest 生成、dry-run 与真实发布的双轨、以及一份 **4,757 行的契约测试**（`tests/contract_v0.rs`）与 594 行 CLI 测试（`tests/cli_v0.rs`）。`Cargo.toml:8` 有 **`publish = false`**——不打算对外发布，只能 vendor。

**成熟度**：26 次提交，2 名作者，2026-07-01 → 2026-10-15。无 license 文件（API 报 NOLICENSE）。

**低价值理由**：我们的产品交付物是**内核 + 配方库 + 适配器 SDK + 运营者配置模板 + 运营手册**（拍板版 §1 五件），不是需要 deb/rpm/brew/scoop 四渠道分发的终端产品；且"发布契约"这件事在我们这里属于 L4 运营者配置与手册范畴，不是内核件。

### 2.10 `rk8s` — Rust 版轻量 Kubernetes（**不引入，已死**）

**是什么**：fork 仓库（API `fork: true`），README 自述基于 Youki 实现 CRI，含 RKL（运行时）／RKS（控制面：apiserver + scheduler + controller）／Xline（etcd 兼容存储）／libbridge CNI，支持单容器、Pod、Docker Compose 三种工作负载形态。

**成熟度**：**20 次提交，全部落在 2025-09-09 → 2025-09-25，此后 13 个月零提交**；0 stars；136,744 KB。**已废弃。**

**低价值理由**：即使它活着也不该用——我们的调度基线是 **k3s + Karmada + Kueue**（拍板版 §7），三者都在 CNCF 治理下、有真实生产负载；用一个 13 个月没动过、0 star 的个人 fork 去替换它们，是在拿生产稳定性换"语言统一"这笔不划算的交易。（宪法 D5 明确：*语义判据优先于语言偏好*。）

### 2.11 `specs` — 空壳仓库（**不引入，无内容**）

API 描述为"API standards and specifications for each module under the DHttp protocol"。实际内容：`find` 结果只有 **一个 `README.md`，8 字节**（内容为 `# specs\n`）；1 次提交，1 名作者，2026-07-21。

**结论**：**这是一个还没写的占位符。** 不构成可评估对象。

### 2.12 打包仓 4 个 + `scoop-Extras` fork（**不引入，零价值**）

`homebrew-stable` / `homebrew-preview` / `scoop-stable` / `scoop-preview` 四个仓库的全部内容就是各自产品的 formula／manifest：`homebrew-stable` 只有 **2 个文件**（`gmutils.rb`、`pishoo.rb`，见 `hb/gmutils.rb`：从 `download.dhttp.net` 下载 tarball + sha256 + `bin.install "genmeta"`）。`scoop-Extras` 是 **fork 自 Scoop 官方 extras bucket，59 MB**，一次 2025-08-24 之后无提交。

**低价值理由**：分发渠道配置是我们的 L4 运营者配置/手册层内容，且我们一期不产出面向终端用户的二进制分发物。这四仓**没有一行代码**可借鉴。

### 2.13 `quic-view` / `r2cn` / `.github` / `rustls` fork（**不引入**）

| repo | 实情 | 为什么低价值 |
|---|---|---|
| `quic-view` | 唯一的提交在 **2025-03-11**（19 个月前），此后无提交。`package.json` 的 `name` 至今是脚手架默认值 `"vite-react-typescript-starter"`、`"version": "0.0.0"`，无 license。内容是一个 Highcharts 折线图 + 文件上传的 React Demo（`src/components/NetworkChart.tsx`、`FileUpload.tsx`）。 | **从未改过的脚手架 + 19 个月死项目 + 无 license**，连"私有 demo"都算不上，是仓库垃圾。 |
| `r2cn` | fork 仓库（`RISC-V Rust for Cloud Native 开源实习计划`），20 次提交全在 2025-01 → 2025-11，之后无提交。 | 实习计划 fork，与底座无关。 |
| `.github` | 3 次提交，2026-07-30 一天完成；内容 = `profile/README.md` + `LICENSE` + `.gitignore`。 | 组织名片，非软件。 |
| `rustls` | **上游同步 fork**，非 genmeta 自研。最近 30 次提交的作者是 `Daniel McCarney`／`Michael Paddon`／`Dirkjan Ochtman`／`shanyu`／`vmaheshw`——**全是 rustls 上游维护者**，改的是 `rustls/src/crypto/...`、`rustls-aws-lc-rs/src/hpke.rs` 等上游文件；README 与上游逐字相同。 | 它是 dquic 定制 TLS 后端（`qtls` → crates.io 的 `qrustls`）的落地管道，**没有 genmeta 自己的分化**。我们要 TLS 就直接用上游 rustls／quinn，跟这个 fork 无关。 |

---

## 三、成熟度与效果证据（汇总）

### 3.1 组织画像

| 指标 | 观察 |
|---|---|
| 外部采用 | **21 个仓库里 20 个 stars = 0**；唯一有星的是 `dquic`（282 stars / 24 forks）。crates.io 下载量最高 4,489（h3x），多数在几百量级。 |
| 人力集中 | 提交作者邮箱几乎全为 `@genmeta.net`；dquic 近 300 次提交有 8 名人类作者，但产出高度集中在 3 人（114 + 86 + 82 = 282/300）。**单厂商团队，无基金会治理。** |
| 发版纪律 | 做得比多数个人项目好：14 个 crate 走 CI 自动发布到 crates.io（`publish-crates.yml`），有 codecov、RELEASING.md、CHANGELOG、commitlint、SECURITY.md、CODE_OF_CONDUCT。**工程素养是真的。** |
| 版本状态 | 对外 CLI 全是 `0.x.0-preview.N`；`daccess 0.1.1`、`rankey 0.3.0`、`h3x 0.7.0`、`dquic 0.8.1` —— 均**未到 1.0**，API 无冻结保证。 |
| 授权卫生 | 大部分 Apache-2.0（好）；但 **`dssh` 声明 Apache-2.0 却无 LICENSE 文件**、`genmeta-xtask-release` 与 `kundy-bootstrap` 无 license 文件、`quic-view` 完全无 license、`specs` 无 license。 |

### 3.2 "效果证据"这一栏的真实答案

**没有一项能力有外部效果证据。** 具体地：
- 无一个仓库有第三方 benchmark、paper、case study 或生产部署公告；
- `dquic` 的 282 stars 与 4,274 次下载是真实信号，但它证明的是"QUIC 实现质量不错"，**不是"去中心化 Agent 网络解决了我们的问题"**；
- 全部仓库的下载量加起来不足 3 万次，最高的几个是网络协议库——这是"发布"而非"被使用"。

按我们的判据（*效果证据：成熟度、贡献者、发版节奏、license、能力演示*）：成熟度与发版节奏**合格**，能力演示**没有**，采用度**近乎为零**。

### 3.3 一个值得记下的信号

`dquic/CONTEXT.md` 与 `h3x/CONTEXT.md` 都在文件开头维护一份**领域术语表**（"本项目的领域术语。以下定义记录已确定的含义"，含 Avoid: 反例），`pishoo`、`ddns` 有同构的 `SPEC.md`（daccess 的 SPEC.md 甚至用 RFC 2119 规范性语言写就，声明"不是 IETF 提案"）。这是很强的"把概念钉死"的工程习惯——**这个习惯本身比任何代码都更值得学**，且它正是我们拍板版 §2.2 宪法（"Trace 是正式接口，从第一天版本化"）想要的东西。建议直接抄这个做法：每个机制的术语表进内核仓 `CONTEXT.md`，禁止同义词漂移。

---

## 四、与我们底座的对照（13 抽象 + 13 机制逐条）

### 4.1 十三个抽象

| 我们的抽象 | genmeta 侧有无对应物 | 证据 / 判定 |
|---|---|---|
| 1 Run（执行单元） | 无 | 全部仓库无执行引擎概念 |
| 2 Artifact（内容寻址） | 无 | 有 `rankey` 的证书 PEM、`daccess` 的 SQLite 行，但都不是不可变内容寻址块 |
| 3 Task Graph | 无 | `dssh` 有 wire format，无图 |
| 4 Credential（biscuit + cedar） | **有且冲突** | `rankey`=X.509/OCSP（身份式）、`daccess`=SQLite 规则表（策略写死在 Rust）。二者都不是能力式凭证 |
| 5 Trace（Merkle + 签名 + 见证） | 无 | 无任何 trace/日志工件系统 |
| 6 Evaluation（三态） | **语义同构** | `daccess/src/policy.rs:9-14` 的 `Allow/Deny/Review` ≈ 我们的 通过/不通过/需人工（见 §2.5） |
| 7 Tool+Skill broker / Sandbox | 无 | `pishoo` 是入站网关，不是能力 broker |
| 8 Trigger | 无 | `gmutils` 的触发是 DNS 发现，不是订单派生 |
| 9 Channel（流式产物） | 无 | — |
| 10 Resident Agent | 无 | — |
| 11 Delivery | 无（方向相反） | `pishoo` 是**入站**暴露，我们是**出库**交付 |
| 12 Human Station | **部分形态相似** | `daccess` 的持久审批 + 联系人 + 管理员概念 ≈ 工位账本的弱化版，但无 SLA、无技能路由、无班次日历、无修订工件 |
| 13 WorkOrder | 无 | — |

**命中：1 个半（Evaluation 三态 = 同构；Human Station = 形态相似）。**

### 4.2 十三个机制

| 我们的机制 | genmeta 侧有无对应物 | 判定 |
|---|---|---|
| 1 CONWIP 投放闸 | 无 | — |
| 2 CSP 采样状态机 | 无 | — |
| 3 升迁/降级 + 熔断 | 无 | — |
| 4 已知答案注入器 | 无 | — |
| 5 渐放机制 | 无 | — |
| 6 止损规则（失败指纹） | 无 | — |
| 7 副作用网关 | 无 | `daccess` 的 `review` 闸门是人审批，不是副作用幂等/撤回窗口/fencing |
| 8 Meter 可组合计量 | 无 | `gmutils` 的额度概念是 DHttp 端点的 API 配额 |
| 9 通用日历 | 无 | — |
| 10 调度提示接口 | 无 | `rk8s` 有 scheduler，但已死 13 个月且我们用 Kueue |
| 11 观测与安灯 | 无 | `quic-view` 是一个 19 个月前的 Highcharts demo |
| 12 容量测量 | 无 | — |
| 13 JIT 编译器 | 无 | — |

**命中：0 个。**

### 4.3 与我们既有选型基线的正面冲突

拍板版 §7 的选型基线里，**唯一与 genmeta 构成竞争关系的是 `rk8s` ↔ k3s+Karmada+Kueue**，而这个竞争方已在 2025-09 死掉，且是 fork（无原创性主张空间上的自由度）。其余全部正交。

---

## 五、评估四问与结论

### 5.1 四问逐条回答

**Q1 替我们省了什么？**
答：**几乎为零。** 唯一能"省"的是三处认知——(a) 授权要绑主体标识而非只绑名字；(b) "需人工"不能阻塞业务请求且要一次性消费；(c) 每个机制仓配一份 `CONTEXT.md` 术语表。这三条省的是**设计返工**，不是工程量。

**Q2 效果证据？**
答：**不足以支撑任何代码引入。** 20/21 仓库 0 star；外部采用近乎为零；无第三方案例、无 benchmark、无生产公告；关键库全部 1.0 以下。唯一例外 `dquic` 有真实外部信号（282 stars、8 名作者含 2 名外部贡献者、709 测试、CI 完整），但**它解决的问题我们没有**。

**Q3 引入成本？**

| repo | 语言 | 依赖/运维 | 对接层 | 退出成本 |
|---|---|---|---|---|
| dquic | Rust 2024 | 低（无 C，`qrustls`） | 只可能在 L2 适配器 | 低 |
| pishoo | Rust + **Bun/Node/C++** | **高**（三语言工具链） | 无对接点 | — |
| ddns / h3x | Rust | 低 | 无对接点 | — |
| daccess | Rust | 中（`sea-orm`+SQLite+axum） | L1 但**违规** | 高（策略会渗进内核） |
| rankey | Rust | 低 | 与 L1 `Credential` **冲突** | — |
| gmutils / dssh / xtask-release | Rust | 中 | 无对接点；dssh 还有 license 瑕疵 | — |
| rk8s / rustls / scoop-Extras | — | fork | 已死／上游同步 | — |
| 打包仓 ×4 / specs / quic-view / r2cn / .github | — | — | 无内容或无对接点 | — |

**Q4 对接四层哪层 + 退出成本？**
答：**绝大多数"无处对接"——它们不属于 L1/L2/L3/L4 中的任何一层。** 唯一名义可对接的是 `dquic`→L2 适配器（备用传输），`daccess`→L1（但违规，退出成本高）。

### 5.2 价值排序与逐条裁决

| 排序 | repo | 裁决 | 一句话理由 |
|---|---|---|---|
| 1 | `daccess` | **部分引入（只借设计，0 行代码）** | 三态授权与"名字+主体标识双因子"值得抄进 `Evaluation`/`Credential`；但它的策略写死在 Rust 里，引入即违反判据 5 与 9 |
| 2 | `dquic` | **观望** | 唯一有真实外部信誉的资产；但它解决的 NAT 穿透/去中心化寻址不是我们要解决的问题，引入它=把内核特化 |
| 3 | `pishoo` | 不引入 | 入站网关，方向与 `Delivery`（出库）相反；工具链含 Bun/Node/C++ |
| 4 | `rankey` | 不引入 | X.509+OCSP 是身份式授权，弱于我们的能力式凭证（biscuit）；引入=能力倒退 |
| 5 | `ddns` / `h3x` | 不引入 | DNS 发现与 HTTP/3，对我们无收益；h3x 官方 README 自陈"不建议直接使用" |
| 6 | `gmutils` / `dssh` | 不引入 | 纯 DHttp 工具链与远程 shell，全 `0.x-preview`；dssh 另有 LICENSE 缺失的法务瑕疵 |
| 7 | `genmeta-xtask-release` | 不引入 | `publish = false` 只能 vendor；四渠道分发不属于我们的交付物 |
| 8 | `rk8s` | 不引入 | 2025-09 后死掉 13 个月的 fork；Kueue 在语义判据上完胜 |
| 9 | `rustls` fork / `r2cn` / `scoop-Extras` | 不引入 | 上游同步 fork / 实习计划 fork / 分发 bucket fork，零原创性 |
| 10 | `specs` / `quic-view` / 打包仓 ×4 / `.github` | 不引入 | 空壳 8 字节 / 19 个月前的脚手架 demo / 纯分发配置 / 组织名片 |

### 5.3 最终结论

> **裁决：部分引入——但只引入一条设计模式，零行代码。**
>
> 具体动作：在 `Evaluation` 与 `Credential` 的机制设计中写入三条约束——
> ①授权工件同时绑定可读名与密码学主体标识，主体变更即自动撤销既有授权（源：`daccess/src/service.rs:195-206`）；
> ②"需人工"永不阻塞业务请求、**匿名或凭证失效时不得进入需人工而须直接判不通过**（源：`daccess/src/service.rs:216-220`）；
> ③审批决定一次性消费 + 撤销权限类工单须校验不移除最后一位有权签发者（源：`daccess/src/service.rs:248-253`、README「直接管理规则」）。
>
> 这三条**不新增机制件数**，落在既有 26 件基线之内，不触碰内核预算。另附一条零成本学习项：采纳 `dquic/CONTEXT.md`、`daccess/SPEC.md` 的做法——每个机制的术语表进仓、`CONTEXT.md`，标注 Avoid 反例，禁止同义词漂移。
>
> 其余 20 个仓库：**不引入**，`dquic` 记为**观望**（若某运营者日后真的要求"内网端点被公网触达"，走 L2 适配器挂 `quinn`，而不是把 `dquic` 打进内核）。
>
> 若只看一件事：这个组织证明了**单一厂商可以把一个 IETF 级协议栈做扎实**（14 crate 自动发布、709 测试、codecov、CONTEXT 术语表），但它做的是**网络层**；我们的战场是**工厂控制层**。两者之间没有替换关系。

---

## 附：本次研究的证据清单（可复现）

**环境说明（重要）**：`https://github.com` 的 git 协议初期不可达（`git clone` 报 `Failed to connect to github.com port 443 after 135123 ms`），改用两条路径完成取证：① `codeload.github.com` tarball；② `https://github.com/<repo>/commits.atom` 取提交节奏（不受 api.github.com 限流影响）。GitHub API 未鉴权配额 60/小时，本次在列完仓库后耗尽（`curl -s https://api.github.com/rate_limit` → `{'limit': 60, 'remaining': 0}`），故后续的元数据来自 tarball、atom 与 crates.io API。

```bash
# 1) 全部仓库清单与元数据（成功执行，22 条）
curl -s 'https://api.github.com/orgs/genmeta/repos?per_page=100' | python3 -c "
import json,sys
d=json.load(sys.stdin); print('count',len(d))
for r in sorted(d,key=lambda x:-x['stargazers_count']):
    print('|'.join([r['name'],'stars='+str(r['stargazers_count']),r['language'] or '-',
      (r['license'] or {}).get('spdx_id','NOLICENSE'),'push='+r['pushed_at'][:10],
      'created='+r['created_at'][:10],str(r['size'])+'KB','FORK' if r['fork'] else 'own']))"

# 2) 源码取证（tarball 路径，codeload；rk8s 136MB 未拉取，仅读 raw README）
for r in rankey dquic h3x kundy-bootstrap genmeta-xtask-release dssh ddns daccess gmutils pishoo specs; do
  for b in main master; do
    code=$(curl -sL -o $r.tgz -w "%{http_code}" https://codeload.github.com/genmeta/$r/tar.gz/refs/heads/$b)
    [ "$code" = 200 ] && { mkdir -p x/$r && tar xzf $r.tgz -C x/$r --strip-components=1 && rm $r.tgz; break; }
  done
done

# 3) 提交节奏（部分仓库深度克隆后的实测）
for r in dquic pishoo ddns gmutils daccess rankey h3x dssh genmeta-xtask-release kundy-bootstrap specs; do
  git clone --depth 300 https://github.com/genmeta/$r.git g/$r
  echo "$r newest=$(git -C g/$r log --format='%ad' --date=short|head -1) n=$(git -C g/$r rev-list --count HEAD) authors=$(git -C g/$r shortlog -sne HEAD|wc -l)"
done
# 实测输出：
# dquic newest=2026-10-12 n=300 authors=10（其中 3 人贡献 282/300，含 2 名 @genmeta.net 外作者）
# pishoo newest=2026-10-15 n=302 authors=8   ddns newest=2026-10-12 n=298 authors=7
# gmutils newest=2026-10-15 n=445 authors=10 daccess newest=2026-10-15 n=19  authors=4
# rankey newest=2026-10-12 n=26  authors=4   h3x newest=2026-10-12 n=200 authors=4
# dssh  newest=2026-08-19 n=200 authors=3    xtask-release n=26 authors=2
# kundy-bootstrap n=1 authors=1（2026-09-11 单次提交）  specs n=1 authors=1（README 仅 8 字节）

# 4) 代码规模与测试计数
find . -name '*.rs' | xargs wc -l        # dquic 78,815 / pishoo 28,320 / h3x 15,930 / dssh 16,750
                                            # ddns 9,369 / daccess 6,871 / rankey 1,274 / xtask-release 14,141
grep -rc "#\[test\]" --include=*.rs .      # dquic 709 / ddns 99 / daccess 67 / rankey 9

# 5) crates.io 发布与下载量（外部采用度证据）
for c in dquic h3x daccess rankey ddns dyns dhttp genmeta; do
  curl -s "https://crates.io/api/v1/crates/$c" | python3 -c "
import json,sys; c=json.load(sys.stdin)['crate']
print(c['id'],'dl=',c['downloads'],'ver=',c['max_version'],'updated=',c['updated_at'][:10],'repo=',c.get('repository'))"
done
# 实测：dquic dl=4274 v0.8.1 / h3x dl=4489 v0.7.0 / dyns dl=3988 v0.8.0 / dhttp dl=2731 v0.7.1
#       rankey dl=939 v0.3.0 / daccess dl=220 v0.1.1 / genmeta dl=412 0.9.0-preview.3
#       ⚠ crates.io 的 `ddns` 名字属于 lvillis/ddns-rs（dl=1387），genmeta 的 ddns 发布名为 `dyns`
#       pishoo / gmutils 以 `genmeta-*` 子 crate 名发布

# 6) rustls fork 性质核实（近 30 次提交作者全为上游维护者）
git clone --depth 30 --filter=blob:none https://github.com/genmeta/rustls.git rl
git -C rl log --format='%ad %an %s' --date=short | head -12
# → Daniel McCarney / Michael Paddon / Dirkjan Ochtman / shanyu / vmaheshw，无 @genmeta 作者

# 7) 空壳与脚手架核实
find x/specs -type f; wc -c x/specs/README.md        # 仅 README.md，8 字节
cat quic-view/package.json | head -6                 # name 仍是 "vite-react-typescript-starter"，version 0.0.0
find hb -type f -not -path '*/.git/*'                # homebrew-stable 只有 gmutils.rb、pishoo.rb
find gh -type f -not -path '*/.git/*'                # .github 只有 profile/README.md、LICENSE、.gitignore
```

**未完成/未验证项（如实声明）**：
- `rk8s` 因 136 MB 未克隆，其规模与内容仅依据 raw README 与 API 元数据；最后一次提交 2025-09-25 来自 atom feed 与 API `pushed_at` 双向印证。
- 所有仓库的**单元测试均未执行**（本报告是文档级 + 代码级评估，未跑 `cargo test`）。测试数量为静态计数。
- GitHub 未鉴权 API 配额在列举仓库后耗尽，故 daccess/rankey 等仓库的 `open_issues_count`、贡献者 API 列表未取；贡献者数据来自 git shortlog。
- 克隆目录 `~/tmp-extresearch/`（含 `x/` tarball 展开与 `g/`、`dq/`、`rl/`、`hb/`、`gh/`、`quic-view/`）在本次任务结束前已删除。
