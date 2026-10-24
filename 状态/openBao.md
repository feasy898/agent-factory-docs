# 状态 · openBao（权威底本：2026-10-10 实测核对版）

> **更新纪律**：bao 实例/密钥/策略/token 任何变化 → 更新下表并在文末追加更新记录。路径清单用 \`bao-agent paths\` 现查，不依赖本文枚举。

| 项 | 当前 |
|---|---|
| 端点 | http://100.64.0.6:8200（gov company-bao-1，healthy，2026-10-19 实测在役） |

---

# OpenBao 接入指南（终态单一权威）

> 适用范围：`pandev-comp`、`governance-machine`、`anolis-gpu-01`、`mingda-website` 上的任何 agent 与人工操作。（hk-gateway 已于 2026-10-20 移出 tailnet。）
> 本文件是 OpenBao 接入的**唯一权威说明**。所有条目均于 **2026-10-10** 在 `governance-machine`
> （`100.64.0.6`）上实测核对，事实与在役状态一致；其他文档不得与之冲突。
> 端点：`http://100.64.0.6:8200`（容器内 `http://127.0.0.1:8200`）。全文不含任何凭据明文，
> 凭据一律以 accessor 或 sha256 前 8 位指纹指代。

---

## 1. 一句话

bao 运行于 `company-bao-1`（OpenBao 2.6.2，已解封，file 存储），
**7 件在役 scoped token 与 broker 身份的 `explicit_max_ttl` 全部为 0（永不过期）**，
策略面共 **26 条**，root 与 unseal key 的托管件落在 **escrow zip 双备份**（gov 盘 + 本机，离机副本见 §10）。

---

## 2. 容器 / 版本 / 配置

| 项 | 值 |
|---|---|
| 容器 | `company-bao-1`（compose 服务名 `bao`），`Up (healthy)` |
| 镜像 | `docker.io/openbao/openbao:2.6.2` |
| 版本 | OpenBao **2.6.2**，commit date `2026-08-18T15:48:19Z` |
| 存储 | `file`，容器内 `/openbao/file` ← 宿主 bind `/opt/company/data/bao` |
| 封印 | shamir **1-of-1**（Total Shares=1 / Threshold=1），HA Enabled=false，disable_clustering=true |
| 封印状态 | `Sealed=false`（运行中） |
| 集群 | Cluster Name `vault-cluster-d160c05b`，Cluster ID `24f3017b-9ce9-d983-40d4-4699e4d3becc` |
| 资源 | `mem_limit: 256m`，`cap_add: IPC_LOCK`，`restart: unless-stopped` |
| 服务端配置 | `governance-machine:/opt/company/platform/ops/bao/config.hjson`（容器内 `/openbao/config/local.hjson`，ro） |
| compose | `governance-machine:/opt/company/platform/ops/compose/docker-compose.yml`（服务定义在第 81 行起） |
| 引擎挂载 | `kv/`（v2）、`secret/`（v2）、`transit/`、`cubbyhole/`、`identity/`、`sys/` |
| 密钥规模 | `kv/` 53 条（`company/` 下分域）、`secret/` 18 条；`transit/` 两个签名密钥 `eval-signer`、`human-signer` |
| 网络暴露 | **无宿主机端口映射**（`docker port` 为空）；tailnet 上经 `100.64.0.6:8200` 由 Caddy 前置 |
| TLS | 容器内 `tls_disable = 1`，TLS 由 Caddy 终止 |
| 健康检查 | `wget /v1/sys/health` 退出 0（已解封）或 8（封存/standby 均视为 API 可达） |

健康检查把「已封存」也算作 API 可达，这是刻意设计：容器健康表示 API 端点活着，
不表示实例处于解封态。判断能否服务要另外看 `bao status` 的 `Sealed` 字段。

`kv/` 的 53 条分布在 `company/` 13 个域下：`Cloud-Resource/`、`Cloud-platform/`、`Git-Platform/`、
`LLM-upstream/`、`agent-gitea-smoke/`、`ci/`、`delivery/`、`gpu/`、`my/`、`otlp/`、`srv1/`、
`upstream/`、`windev/`。`secret/` 的 18 条在 `credentials/`、`chenmai8/`、`opch/`（holdout 密钥与
session 命名空间）、`stepfun`、`tencentcloud`、`tencentcloud-provided`。
路径全量清单用 `bao-agent paths` 现查，不依赖本文件的枚举。

---

## 3. root token：位置与取用方式

| 项 | 值 |
|---|---|
| 指纹 | `sha8=15542b22`（26 字节，`s.` 前缀） |
| accessor | `5mh8IRZKcflTZbOqbgvpxYME` |
| 属性 | `policies=["root"]`、`creation_ttl=0`、`explicit_max_ttl=0`、`expire_time=None`、orphan=true —— **永不过期** |
| 托管形态 | age 密文 `/opt/opch/secrets/root-token.age`，私钥 `/opt/opch/secrets/owner.key`（189B，0600 root） |
| escrow 形态 | `openbao-key-escrow.zip` 内 `vault/root-token.age`，age **scrypt 口令**收件人（owner 口令） |

**盘面无常驻 root 明文**：`/etc/bao/` 为空目录，`find /opt/opch/secrets -name root-token -type f` 无结果。
需要 root 时现解密、用完即弃：

```bash
# gov 上取用（解密进环境变量，不落盘、不进 argv）
T=$(age -d -i /opt/opch/secrets/owner.key /opt/opch/secrets/root-token.age)
docker exec -e BAO_ADDR=http://127.0.0.1:8200 -e BAO_TOKEN="$T" company-bao-1 bao <命令>
```

本机持有 escrow zip 时，用托管工具取用（口令由 age 直接从终端读取，不回显、不进 history）：

```bash
export PATH="$HOME/.local/bin:$PATH"
openbao-escrow unlock        # 解出 root token 到 0600 取回件
openbao-escrow status        # 只看解锁状态，不显示内容
openbao-escrow as bao status # 以 root 身份执行一条命令
openbao-escrow lock          # shred 覆写销毁取回件
```

**纪律**：agent 一律用 scoped token，不用 root。root 只用于签发轮换、改策略、运维窗口操作。

---

## 4. unseal key：位置

unseal key **只以 age 密文形态存在**，明文不落在任何长期路径：

| 位置 | 形态 |
|---|---|
| `openbao-key-escrow.zip` → `vault/unseal-key.age`（377B） | age **scrypt 口令**收件人（owner 口令） |
| `governance-machine:/opt/opch/secrets/unseal-key.age`（244B） | age 公钥收件人 `owner.pub`，私钥 `/opt/opch/secrets/owner.key` |

指纹 `sha8=4985cf5f`（44 字节，实测可解封当前实例）。
取用：escrow 侧 `openbao-escrow unlock-unseal`；gov 侧 `age -d -i /opt/opch/secrets/owner.key /opt/opch/secrets/unseal-key.age`。
`operator unseal` 只需 unseal key、不需要 root token，这是 OpenBao 2.6 上唯一不依赖 root 的恢复入口。

---

## 5. broker 策略面（11 条）+ deny 自签

broker 身份 token（`jit-broker-token`，`sha8=45c481e6`，accessor `f4alTMQOYXs0j5G52Qjs6BKr`）
持 **11 条策略**（含 `default`）：

```
default, jit-broker,
jit/bailian-cred, jit/bill-pull, jit/gate-decide, jit/kv-read-credentials,
jit/meter-read, jit/mq-gitea-cred, jit/mq-write, jit/session-write, jit/zcode-obs
```

`jit-broker` 策略本身只开三处：`auth/token/create`（create/sudo/update）、
`auth/token/lookup-self`（read）、`auth/token/renew-self`（update）。

**deny 自签 —— broker 不能给自己扩权**（实测）：

| 路径 | broker 能力 |
|---|---|
| `sys/policies/acl` | **deny** ← 无法写策略，无法自助附加新 `jit/<scope>` |
| `auth/token/create` | create, sudo, update |

新增 scope 是**治理动作**，必须由 root 在盘面完成：建 `jit/<scope>` 策略 → 附加到 broker token 身份 → 重签 broker token。
broker 只有附加好的 scope 才有签发权；**没附加的 scope 即使 `jit-issue` 申报也会被拒**。

签发面（gov）：

```bash
/usr/local/bin/jit-issue --agent <agent> --scope <scope> --task <task_id> --ttl 10m
# 机制：agent 申报 → 校验 opch.tasks（task 存在、created_by=申报 agent、非终态）→ broker 身份签发
# 返回 JSON 含 token/accessor/policies/ttl；审计见 gov:/var/log/jit-broker/issue.log（只记 accessor）
```

---

## 6. 7 件在役 scoped token

全部 `creation_ttl=86400`（24h 滚动）、**`explicit_max_ttl=0`（无绝对寿命上限）**、orphan=true。
均由 `periodic-token-renew.timer` 每 30 分钟以各自身份 `bao token renew` 续期回满。

| token 件 | accessor | 策略（不含 default） | sha8 |
|---|---|---|---|
| `jit-broker-token` | `f4alTMQOYXs0j5G52Qjs6BKr` | `jit-broker` + 9 条 `jit/*`（共 10） | `45c481e6` |
| `gate-decide-token` | `KoYHlus126USiFUy4nLD2iOM` | `jit/gate-decide` | `992dc764` |
| `kv-read-credentials-token` | `veOdqeBxaRXpkNqWuuX8aqVt` | `jit/kv-read-credentials` | `7520538c` |
| `meters-token` | `Qe1jy85mOw5BIOTnHnXj5SVA` | `gov-meters-readonly` | `f073388b` |
| `mq-write-token` | `xtLqBvhIdqktHTSV0SmvVks0` | `jit/mq-write` | `e57b94da` |
| `session-write-token` | `whZ01P5ymRyAxLcCOGg01P1E` | `jit/session-write` | `3b73682e` |
| `git-read-token` | `PQDmDGWHtvP6NJLlqYcdStgA` | `agent-git-read` | `0e9d0f26` |

件落在 gov `governance-machine:/opt/opch/secrets/<name>`（0600 root）。
续期器：`/opt/opch/ops/renew-periodic-tokens.sh`（`periodic-token-renew.timer`，`OnCalendar=*:0/30`，Persistent），
日志 `/var/log/periodic-token-renew.log`；单件失败 POST 本机 feishu-inbox receiver（127.0.0.1:9876/webhook），
同件 2h 限频；任一失败非零退出。日志与告警只记文件名与 ttl，不落明文。

`git-read-token` 授权面是 **`kv/` 挂载**（不是 `secret/`）：持该策略的 token 对 `secret/data/...` 一律 deny，
对 `kv/data/company/Git-Platform/*` 任意子路径可 read。凭据键名（大写 G，以 LIST 实读为准）：

| 路径 | 说明 |
|---|---|
| `kv/company/Git-Platform/Github/Feasy898-PAT-repo-only` | 仅仓库权限 PAT —— **默认取用这个** |
| `kv/company/Git-Platform/Github/Feasy898-PAT-all-previlege` | 全权限 PAT（字段 `PAT_token`） |
| `kv/company/Git-Platform/Github/Feasy898-PAT-no-admin` | 无 admin 权限 PAT |
| `kv/company/Git-Platform/Github/CloudCrane-Software-{CI-bot,Reader,Repo-Writer}-APP` | GitHub App 凭据 |

---

## 7. 策略清单（26 条）

```
agent-billing-probe          agent-git-read              agent-holdout-authoring
agent-holdout-judging        agent-holdout-owner-exclusion agent-holdout-rotator
agent-infra-read             agent-llm-upstream-read      billing-pull
ci-reader                    default                     egress-tools-read
execution-worker             gov-meters-readonly         gpu-harness-read
jit-broker                   root
jit/bailian-cred             jit/bill-pull               jit/gate-decide
jit/kv-read-credentials      jit/meter-read              jit/mq-gitea-cred
jit/mq-write                 jit/session-write           jit/zcode-obs
```

已从盘面移除的 4 条（无在役引用，2026-10-10 删除）：

```
agent-session-registry   gov-billing-broker   jit-billing-pull-v2   test-tencent
```

策略要点：

- 全部 agent/scoped 策略只带读权限 + `auth/token/renew-self`，**不含写、不含 `auth/token/create`**；
  持 scoped token 请求 `auth/token/create` 返回 403，无法提权。
- `agent-holdout-owner-exclusion` 对 holdout 命名空间显式全拒：
  `path "+/data/opch/holdout/*"` 与 `path "+/metadata/opch/holdout/*"` 均为 `capabilities = ["deny"]`。
- `jit/zcode-obs` 只开 `kv/data/company/otlp/public-ingest` 一条 read；父路径与 metadata 面隐式 deny。
- `gov-meters-readonly` 与 `jit/meter-read` 同面（`secret/data/credentials/cnb` 只读）：
  前者是常驻计量 cron 持件，后者是 broker 可签发的 scope 面。

---

## 8. 审计配置

| 项 | 值 |
|---|---|
| 设备 | `bao-audit/`，type=file，声明于 `config.hjson` 的 `audit "file" "bao-audit"` 块 |
| 文件路径 | 容器内 `/openbao/logs/audit.log` |
| 承载 | docker volume `4780ec5204362080…`（**匿名卷**，非 bind mount） |
| 规模 | 5.5 万行量级，持续增长 |
| 开关 | OpenBao 2.6.2 禁止经 API 启用审计设备，只能走 config；**移除该块并重启容器即回滚** |

审计卷是匿名 docker 卷：`docker volume prune` 或 `compose down -v` 会连同审计轨迹一起删除。
运维上禁止在这两个命令上使用 `-v` / `prune`；如需清理空间，先 `docker volume ls` 核对再逐个处理。

---

## 9. 应急路径

### 解封（容器/宿主重启后必需）

```bash
# gov 上；密码/密钥从终端隐藏读取，绝不进 argv
bash /opt/company/platform/ops/scripts/bao-unseal.sh
# 或管道式：printf %s "$KEY" | bash /opt/company/platform/ops/scripts/bao-unseal.sh
```

`unseal` 命令只需 unseal key，不需要 root token。

### 快照与恢复

```bash
bash /opt/company/platform/ops/scripts/bao-snapshot.sh    # 每日 04:10 cron，保留 14 份
bash /opt/company/platform/ops/scripts/bao-restore-drill.sh # 恢复演练：一次性容器 + 原 unseal key 解封 + KV 抽查
```

快照落 `/opt/company/backups/bao/bao-data-<ts>.tgz`，先写 `.part` 再原子 rename，
`gzip -t` + 结构断言（`bao/core/_keyring`、`bao/logical/` 必在）兜底，保留最近 14 份。

### root 与 agent token 轮换

```bash
T=$(age -d -i /opt/opch/secrets/owner.key /opt/opch/secrets/root-token.age)

# 新 root（unseal 窗口内，2.6 不会在 unseal 时打印 Initial Root Token，必须显式 generate-root）
docker exec -e BAO_ADDR=http://127.0.0.1:8200 -e BAO_TOKEN="$T" company-bao-1 \
  bao operator generate-root -format=json      # 走 -generate-otp → -init → -otp 三步，全过程需有效 root

# 轮换某件 scoped token：撤旧 + 重签 + 写回 0600
docker exec -e BAO_ADDR=http://127.0.0.1:8200 -e BAO_TOKEN="$T" company-bao-1 \
  bao token revoke -accessor <accessor>
docker exec -e BAO_ADDR=http://127.0.0.1:8200 -e BAO_TOKEN="$T" company-bao-1 \
  bao token create -policy=<策略> -period=24h -orphan -explicit-max-ttl=0 -field=token
# → auth.client_token 写入 /opt/opch/secrets/<name>，chmod 600
```

**轮换三处同步**（缺一即制造延迟爆雷）：① 新凭据生效 ② escrow zip 更新 ③ **验证 escrow 里解出来的东西真能用**。
轮换 root 或 unseal key 后，重封 escrow：

```bash
/opt/opch/jit-broker/escrow-rebuild.sh   # 重建 zip 并自验往返（解包→解密→lookup）
```

### 常见故障

| 现象 | 原因与处理 |
|---|---|
| `permission denied` 且 `sealed: true` | 实例已封存 → gov 上跑 `bao-unseal.sh` |
| 所有命令 403 | token 策略不含该路径 → `bao token lookup` 看策略，`bao policy read <名>` 看授权 |
| `couldn't connect` / `HTTP response to HTTPS client` | 服务端 `tls_disable=1`，须用 `http://`；容器内打 `127.0.0.1:8200`，宿主机/网络侧打 `100.64.0.6:8200` |
| `LIST` 返回空 | KV v2 的 LIST 端点是 `/v1/{mount}/metadata/{path}`，不是 `/v1/{mount}/{path}/metadata` |
| `bao-agent: 错误: 找不到 token` | 本机 `openbao-escrow unlock`；或设 `BAO_AGENT_TOKEN`；gov 上 agent 任务走 `jit-issue` |

### 在役 token 自检

```bash
# 列出全部 accessor 与策略面（不打印明文）
docker exec -e BAO_ADDR=http://127.0.0.1:8200 company-bao-1 bao list auth/token/accessors
# 单件核对 ttl/策略/expire（token 值不进 argv 历史）
bao write -format=json auth/token/lookup token=<值>
```

`auth/token/lookup-accessor` 与 `bao token lookup-accessor` 在 2.6.2 上均未提供；按 accessor 查只能走
`auth/token/accessors/<accessor>` 的 LIST 端点。

---

## 10. 托管件位置与基线指纹

escrow zip（root + unseal key 的 age 密文与 manifest）。**基线 sha256 = `113b770a9dc4d281…`（1743B，2026-10-20 21:20 重新封存，v2 清单）**。owner 离线设备（笔记本/U 盘）**不再作为副本维护**（2026-10-20 运营者决定），本机 + mingda + hk + gov 即为全部持有点：

| # | 位置 | 说明 |
|---|---|---|
| 1 | `governance-machine:/root/openbao-key-escrow.zip` | **主位置**，0600 root；`~/.local/share/openbao-escrow/` 下软链指过来 |
| 2 | 本机 pandev-comp `~/.local/share/openbao-escrow/openbao-key-escrow.zip` | 本机离机副本，0600 |
| 3 | `mingda-website(100.64.0.2):/root/key-escrow/openbao-key-escrow.zip` | 旧「副本B」目录，0600；9-27 明文散件已于 2026-10-20 全部 shred |
| 4 | `hk-gateway(100.64.0.3):/root/key-escrow/openbao-key-escrow.zip` | 旧「副本C」目录，0600；10-07 明文 unseal key 已 shred。**⚠️ 该机 2026-10-20 已移出 tailnet，此后只能带外取用/核验，tailnet 内不再可达** |
| 5 | `governance-machine:/opt/opch/backups/escrow/openbao-key-escrow-20261020-211958.zip` | 时点备份 |
| 6 | `governance-machine:/root/m0-backups/bao-offline-escrow/openbao-key-escrow.zip` | 离线兜底副本；同名旧 L2 包已改名留存为 `openbao-key-escrow-20261008-stale-L2.zip`（内含 Windows age.exe 工具链，未销毁） |
1–6 处 sha256 一致（`113b770a9dc4d2818356da46ff266cde…`）。四台机器都装了修好的 `openbao-escrow` 工具，可零口令自检：

```bash
openbao-escrow verify    # 不需要口令：验包完整性 + 显示清单布局
openbao-escrow unlock    # 需要口令：解密 → 明文指纹 → 活性(policies=root) 三道校验
```

zip 结构（与 owner 原设计同构）：

```
openbao-key-escrow/
└── vault/
    ├── root-token.age    353B  age 密文（owner 口令）
    ├── unseal-key.age    377B  age 密文（owner 口令）
    └── manifest.tsv      102B  name  sha256(密文)  size  note
```

`manifest.tsv` 里的指纹是**密文**的 sha256，不是明文凭据指纹，不能用它判断凭据活性。

**离线副本到端后核验**（口令由 age 从终端读取，不回显）：

```bash
sha256sum openbao-key-escrow.zip   # 必须等于 7110d090a33f5074…
unzip openbao-key-escrow.zip -d ./escrow-check
cd escrow-check/openbao-key-escrow/vault
age -d -o /tmp/root.txt root-token.age
BAO_ADDR=http://100.64.0.6:8200 curl -s -o /dev/null -w "HTTP %{http_code}\n" \
  -H "X-Vault-Token: $(cat /tmp/root.txt)" "$BAO_ADDR/v1/auth/token/lookup-self"   # 期望 HTTP 200
shred -u /tmp/root.txt; rm -rf escrow-check openbao-key-escrow.zip
```

不要 `cat` 解出的凭据文件。核验完立即 shred。

### 10.1 manifest 布局与"指纹校验失败"的真相（2026-10-20 定位）

同一个 `manifest.tsv` 先后被两种布局写出来过，**解封工具按哪种布局读，决定了它会不会误判**：

| 布局 | 列 | 谁产出 | 何时 |
|---|---|---|---|
| **L1** | `key / 密文 sha256[:12] / 密文字节数 / note` | `escrow-rebuild.sh` | 2026-10-10 重建起的包 |
| **L2** | `key / 封存日期 / 明文字节数 / sha256:明文指纹…` | `reseal-root-token.sh` | 2026-10-08 及以前的包 |
| **v2** | `key / 封存日期 / 明文字节数 / 明文 sha256[:12] / 密文字节数 / 密文 sha256[:12] / note` | `escrow-reseal-v2.sh` | 2026-10-20 起 |

2026-10-20 20:53 在本机执行 `openbao-escrow unlock` 报「指纹校验失败: root-token 实得 26B/155 期望 353B/aee」，**根因不是包坏、也不是口令错**：老版工具按 L2 去读第 2、3 列，而当时的包是 L1 布局 —— 于是把「密文字节数 353」当成明文字节数，把备注列 `age密文(owner口令)` 里的十六进制字母 `a`、`e` 当成期望指纹。**期望指纹 `ae` 这个值本身就是 bug 的指纹**。同时工具在解密后先把明文写进正式取回件再校验，校验不过也不销毁（只在 age 解密失败时才 shred），所以盘上留下了那个 26 字节文件。

该 26 字节文件经实测确认就是**现役真 root token**（非残次品）：`lookup-self` HTTP 200、`policies=[root]`、`parent=None`、`display_name=root`、`orphan=True`、`num_uses=0 / ttl=0`，且 `sha256[:16]=15542b224bddd5bb` 与 gov 侧 `age -d -i owner.key` 解出的现役值**逐字节一致**。本节结论：escrow zip 本身完好（zip sha256 与 gov 主位置、10-10 时点备份三方一致，`root-token.age` 密文指纹 `e570a85c4f40`/353B 与 manifest 登记相符）。

**处置**（2026-10-20）：本机 `openbao-escrow` 已重写，三道校验各司其职且任一不过就不落取回件 ——
① 包完整性：`.age` 密文 vs manifest 密文指纹/字节数；
② 明文指纹：manifest 登记了明文指纹时（v2/L2）比对，否则跳过并明说；
③ 凭据活性：`lookup-self` 必须 200 且 `policies` 含 `root`，bao 不可达才跳过并明说。
另新增 `openbao-escrow verify`（不需要口令，只验包完整性）。

**gov 上做 bao 查询的两条硬约束**（写任何 bao 运维脚本都会踩，2026-10-20 实测）：
① bao 的 8200 **没有映射到宿主机**——宿主机 `curl 127.0.0.1:8200` 恒为 `000`，只有 tailnet 地址 `100.64.0.6:8200` 通；② **容器镜像里没有 curl/wget**，容器内查询必须走容器自带的 `bao` CLI：

```bash
T=$(age -d -i /opt/opch/secrets/owner.key /opt/opch/secrets/root-token.age)
docker exec -i -e "BAO_TOKEN=$T" company-bao-1 \
  sh -c 'export BAO_ADDR=http://127.0.0.1:8200 VAULT_ADDR=http://127.0.0.1:8200; bao token lookup -format=json'
```

`escrow-reseal-v2.sh` 的活性校验已按"宿主机直连 → 容器内 `bao` CLI → 容器内 curl（兜底）"三级降级实现；2026-10-20 首次运行即栽在这条上（报"端点不可达"），已在 gov 抽出该函数定点验证 `policies=root` 通过。

数据面备份另走快照链：gov `/opt/company/backups/bao/bao-data-*.tgz`（每日 04:10，保留 14 份）。

### 10.2 明文凭据清零（2026-10-20 结清）

铺新包时全网排查发现三台机器上有**明文**凭据。运营者裁决：**unseal key 日常不需要明文**（它只在 vault 被 seal 的异常路径上用；`bao-unseal.sh` 本来就是从终端/stdin 读、从不读明文文件），最佳策略就是只以 age 密文存在于 escrow —— **2026-10-20 21:20 的 v2 重新封存已经把 unseal key 封进去了**（manifest 行 `unseal-key 44B/4985cf5ff3d5` + 377B 密文），所以无需再跑一次封存，只需把明文残件清掉：

| 位置 | 内容 | 处置 |
|---|---|---|
| `gov:/opt/opch/secrets/unseal-key` | 44B `4985cf5ff3d5…` 现役 unseal key 明文 | **已 shred**。`edge-recovery.sh` 自动回落到 `age -d -i owner.key /opt/opch/secrets/unseal-key.age`，已实测回落路径解出的指纹仍是 `4985cf5ff3d59936`，恢复能力不受影响 |
| `gov:/root/.local/share/openbao-escrow/.unseal-key` | 同上（escrow-base 解封件） | **已 shred**。取用改为 `openbao-escrow unlock-unseal` |
| `mingda:/root/key-escrow/unseal-key` | 同上 | **已 shred** |
| `hk-gateway:/root/key-escrow/unseal-key` | 同上（hk 是公网出口机，暴露面最大） | **已 shred** |
| `mingda:/root/key-escrow/root-token` | 26B `8dd7814919bc…` | **已 shred**。10-05 d5 轮换作废的那把，实测 `lookup-self` HTTP 403 |
| `mingda:/root/key-escrow/srv1-ssh-key` | 1675B PEM RSA 私钥 | **已 shred**。经查为冗余副本——同一把（`574ea7a46c1e677b`）仍在 `mingda:/root/.ssh/migration-159.75.21.149.key`，删的只是 escrow 目录里那份 |

**现在的恢复口径**：unseal key 只存在于 ①escrow zip（owner 口令加密，6 处）②gov 的 `unseal-key.age`（owner.key 身份加密，专供 `edge-recovery.sh` 自动恢复）③任何持包机上 `openbao-escrow unlock-unseal` 现场解出的临时件（用完 `openbao-escrow lock` shred）。全网无明文常驻。

**重新封存时的取用顺序变了**：明文源已清空，`escrow-reseal-v2.sh` 会直接报「找不到明文 unseal key」并提示先跑 `openbao-escrow unlock-unseal`（脚本已内置该提示）。

anolis 上的 `/opt/opch/exec/fixtures/unseal-target/escrow/unseal-key.enc`（37B）是解封演练夹具，非真实凭据，不在处置范围。


---

## 附：工具与相关文件

| 位置 | 用途 |
|---|---|
| `~/.local/bin/openbao-escrow` | 本机 escrow 取用（unlock / unlock-unseal / as / status / **verify** / lock） |
| `~/.local/bin/bao-agent` | agent 侧只读封装（status / paths / get / policy / token issue / audit） |
| `gov:/usr/local/bin/bao` | gov 上 bao CLI 垫片（docker exec 进容器，外部 `BAO_TOKEN` 优先） |
| `gov:/usr/local/bin/jit-issue` | JIT scoped token 签发入口 |
| `gov:/opt/opch/ops/renew-periodic-tokens.sh` | 7 件 periodic token 续期器 |
| `gov:/opt/opch/jit-broker/escrow-rebuild.sh` | escrow zip 重建 + 往返自验（产 **L1** 布局清单） |
| `gov:/opt/opch/jit-broker/escrow-reseal-v2.sh` | escrow 重新封存（产 **v2** 布局清单，密文+明文双指纹）+ 往返自验 + 副本同步 |
| `gov:/opt/opch/jit-broker/age-pw.py` | 托管口令一次采集、经 pty 投喂多次 age 调用（口令不进 argv/环境/history） |
| `本机工作区 tools/escrow-reseal-v2.sh`、`tools/age-pw.py` | 上面两个文件的本地源副本（改脚本改这里，再 scp 到 gov） |
| `gov:/opt/company/platform/ops/scripts/bao-unseal.sh` | 解封 |
| `gov:/opt/company/platform/ops/scripts/bao-snapshot.sh` | 快照 |
| `gov:/opt/company/platform/ops/scripts/bao-restore-drill.sh` | 恢复演练 |

> `escrow-rebuild.sh`（L1）与 `escrow-reseal-v2.sh`（v2）都能重建包，**优先用 v2**：它额外登记明文指纹，解封端才有第二道真值可验。两者产出的包解封端都兼容（工具按列语义自适应）。

`bao-agent` 明文纪律：默认隐藏字段内容，需明文时加 `--reveal` 或精确取 `--field K`。
明文一旦打印即进入对话记录与终端历史（2026-09-28 曾发生 consumer key 泄入子代理转录）。
密钥全量清单用 `bao-agent paths` 现查，不依赖文档枚举。

### bao-agent 命令参考

| 命令 | 说明 |
|---|---|
| `bao-agent status` | 封印状态、版本、存储类型、n/t、引擎挂载 |
| `bao-agent whoami` | 当前 token 的身份、策略、有效期 |
| `bao-agent paths [前缀]` | 递归列出密钥路径；带前缀可过滤 |
| `bao-agent get <路径>` | 列出该密钥的字段名与字节数（**不显示明文**） |
| `bao-agent get <路径> --field K` | 指定字段，同样默认隐藏 |
| `bao-agent get <路径> --reveal` | 输出 JSON 明文 |
| `bao-agent get <路径> --field K --reveal` | 输出该字段明文 |
| `bao-agent policy list` | 列出全部 ACL 策略 |
| `bao-agent policy show <名>` | 显示某策略的路径与能力 |
| `bao-agent token issue --policy P [--ttl s] [--name N]` | 签发 scoped token，输出只含 accessor/策略/TTL |
| `bao-agent audit` | 显示审计设备状态 |
| `bao-agent --admin <子命令>` | 管理动作：经 governance SSH 引导签发**短时** root token（不落盘） |

路径可省略引擎前缀：`company/gpu/x` 自动补成 `kv/data/company/gpu/x`。
`--admin` 必须置于子命令之前。

## 11. af 工厂 gitea 通道（2026-10-19 建立）

- **gitea 端点**：`http://100.64.0.6:3300`（gov 容器 opch-gitea，容器 3000→tailnet 3300；admin=opchadmin）。
- **仓库**：`opchadmin/af`（私有，id=38，af 主仓镜像）+ 分支 `probe/anolis-roundtrip`（通道往返验证探针，保留作证据）。
- **凭据**：admin 面在 `kv/company/agent-gitea-smoke/m0-round1`（admin_user/admin_pass/api_token 字段；注意 10-文档 §4 曾把 PAT 位置写成 `Git-Platform/Github/`——那是 GitHub PAT，gitea 凭据实际在 agent-gitea-smoke 域）。
- **本机用法**：`~/.local/bin/af-gitea-askpass`（GIT_ASKPASS，git 推拉时现取 token）与 `af-gitea-api`（API 调用包装）——token 全程经管道，不落盘不进转录。
- **anolis 用法**：专用 scoped token（仅 `write:repository`+`read:repository`，名 anolis-af-sync-2，由 admin basic-auth 经 API 签发）落在 anolis `/data/af-factory/.git-token`（0600）+ `/data/af-factory/git-askpass`；孤儿 token anolis-af-sync 已删（204）。
- **克隆形态**：anolis 侧用稀疏克隆（`--depth 1 --filter=blob:none --sparse` + crates/ci sparse-checkout，`/data/af-factory/af-sync`）——全量树 5.2G 不值得拉，实例工作副本另走 rsync/git 本地克隆。

<!-- M-4 gate5 gitea round-trip probe: anolis commit 2026-10-08T21:06:38+08:00 -->
---

## 更新记录

| 日期 | 身份 | 变化 | 验证 |
|---|---|---|---|
| 2026-10-20 | 审计接续执行子代理 | **本机 escrow 恢复"用完即弃"纪律**：`openbao-escrow lock` shred 销毁解锁滞留 8 天的在役 root token 明文取回件（.root-token，10-12 解锁后未 lock）；同目录 shred 清理 `.root-token.stale-20261008`（旧 root 明文）与 3 个旧 escrow zip（3.4MB 级 age 密文残件）。现存仅权威 zip（sha256 前 8 位 7110d090 与 §10 登记一致）+ reseal 工具。gov 侧明文残留（/opt/opch/secrets/unseal-key、.last-token、.pre-* 目录）未动——属保留区+owner 窗口事项，待厂长裁决 | openbao-escrow status 前后对照（已解锁→已锁定）；ls 目录清单；全程无明文输出 |
| 2026-10-20 | 审计接续执行子代理 | **lock 连带事故与工具迁移**：escrow lock 后发现 local-image-feed/cnb-relay/cb-dispatch 三工具原直接读 .root-token 明文换 bao kv 的 CNB 平台令牌（审计"解锁 8 天未用"漏判此依赖）——feed 当场崩溃。处置：三工具补丁为"~/.config/cnb/relay-tokens.json（0600）优先、root 路径回退"；该文件经 gov 设计内 admin 管道（openBao.md §3 原样路径，只读）播种三枚 CNB 平台令牌；feed 已恢复。**纪律后果**：本机盘面自此无常驻 bao root 明文（符合 §3 设计态）；代价=CNB 令牌多一处 0600 落盘，轮换时须与 bao kv 同步（技术债 D-19）。escrow 取回件保持锁定 | feed 恢复拉取实测；registry token exchange OK；值未进任何转录 |
| 2026-10-20 | 主代理（escrow 专项） | **escrow「指纹校验失败」定位并修工具 + 备好 v2 重新封存**：20:53 本机 unlock 报「实得 26B/155 期望 353B/aee」——查证为**工具 bug 非包坏**：manifest 有 L1（密文指纹）/L2（明文指纹）两套布局，10-10 重建的包是 L1，老工具按 L2 读第 2/3 列，把密文字节数当明文字节数、把备注 `age密文(owner口令)` 的 `ae` 当期望指纹；且解密后先写正式取回件再校验、校验不过也不 shred，故留下 26B 文件。**该 26B 文件实测=现役真 root token**（lookup-self 200、policies=[root]、orphan、num_uses 0/ttl 0，sha256[:16]=15542b224bddd5bb 与 gov `age -d -i owner.key` 解出值逐字节一致）。**包本身完好**：本机 zip sha256 7110d090a33f5074 与 gov 主位置、10-10 时点备份三方一致，两个 .age 密文指纹与清单登记相符。处置：①重写 `~/.local/bin/openbao-escrow`（三道校验：包完整性/明文指纹/凭据活性，任一不过不落取回件；新增无需口令的 `verify`；按列语义自适应 L1/L2/v2），自检 12/12 过（含篡改拒收、错口令拒收、非 root 拒收、403 拒收、bao 不可达跳过）；②新增 `tools/age-pw.py`（口令一次采集经 pty 投喂，不进 argv/环境/history）+ `tools/escrow-reseal-v2.sh`（产 v2 双指纹清单、封存前必验 policies=root、往返自验、旧包备份、副本同步），全假环境端到端演练 11/11 过，已部署到 gov `/opt/opch/jit-broker/`（sha256 与本地一致）。**未完成一步**：重新封存需 owner 托管口令（只能在真终端输入），脚本已就位待运营者执行 | 全程零明文输出（凭据一律以 sha256 前 12/16 位指代）；bash/python 语法检查；桩 bao + 合成托管包自检；gov 端 sha256 比对 |
| 2026-10-20 | 主代理（escrow 专项，收尾） | **escrow 重新封存完成并铺全网**：运营者持托管口令在 gov 执行 `escrow-reseal-v2.sh` 成功（首次因容器内无 curl 失败，已改为三级降级：宿主机直连→容器内 `bao` CLI→容器内 curl）。新包 **`sha256 113b770a9dc4d281…`（1743B，21:20）**，manifest 升 v2 双指纹（root 26B/`15542b224bdd`、unseal 44B/`4985cf5ff3d5`，均与登记值吻合），经封存前 `policies=root` 校验 + 往返自验（解包→解密→逐字节比对→lookup）。铺到 6 处并全部零口令验收通过：gov 主位置、本机、mingda、hk、gov 两处备份；副本C 的旧 L2 包改名留存未销毁。四台机器均装上修好的 `openbao-escrow`（修了 `stat` 不解引用导致软链包大小显示成 39B 的小 bug）。**owner 离线设备（第 7 处）未同步，待手工搬运验指纹** | 四处 sha256 逐一比对一致；每机 `openbao-escrow verify` 通过并显示布局=v2；全程零明文 |
| 2026-10-20 | 主代理（escrow 专项，清零） | **明文凭据全网清零 + 离线设备出副本序列**：运营者裁决「unseal key 日常不需要明文，最佳策略就是封在 escrow 里」——v2 重新封存已把它封进去（manifest `unseal-key 44B/4985cf5ff3d5`），故**无需再跑封存**，改为清残件。shred 6 处：gov 两处明文 unseal key（`/opt/opch/secrets/unseal-key`、escrow-base `.unseal-key`）、mingda 明文 unseal key、hk 明文 unseal key、mingda 已作废 root token（`8dd7814919bc…`，实测 403）、mingda `srv1-ssh-key`（**经查为冗余**：同一把私钥 `574ea7a46c1e677b` 仍在 mingda `~/.ssh/migration-159.75.21.149.key`）。删明文前先验依赖：`bao-unseal.sh` 本就从终端/stdin 读不读文件；`edge-recovery.sh` 有明文→`unseal-key.age` 降级链，已实测回落路径解出指纹仍为 `4985cf5ff3d59936`。owner 离线设备按运营者决定**移出副本序列**，§10 台账定为 6 处。`escrow-reseal-v2.sh` 补"明文源已清空→先跑 `openbao-escrow unlock-unseal`"的失败提示（演练 11/11 复跑通过后重新部署，sha256 一致） | 逐文件 shred 后 `ls` 复核目录；`age -d -i owner.key unseal-key.age` 指纹比对；mingda/hk/gov 三机目录清单；演练 11/11 |
