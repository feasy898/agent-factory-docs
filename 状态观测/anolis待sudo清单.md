# anolis 待 sudo 清单（2026-10-21 修理组，step-5-preview 载体）

背景：2026-10-21 anolis-gpu-01（16C/125G，100.64.0.7）因"测评容器无内存上限 + 无 swap"
耗尽假死，运营者硬重启两次（最近一次 16:20）。pan-ding 在 anolis 有 docker 组但**无免密
sudo**（实测 `sudo -n true` 要密码），以下事项需运营者执行。每项含：现状实测、理由、
可直接复制的命令、验证、风险/窗口要求。

配套已落地（无需 sudo，本会话完成，供上下文）：
- af-bench 容器资源上限（af main=f373113 已推 gitea，CI 七门全绿）：swev agent 容器
  6g/512、干净判分容器 4g/256、TB 路径容器 2g/256，按 125G×14 臂校准；新二进制暂存
  `af/target/debug/af-bench-guardrail`（sha256 d7f2953f…），**未换上生产位**（换上需重启
  调度器=杀在飞臂，归运营者裁决，见最终报告）。
- 调度器内存门（tools/factory-sched.py，py_compile 过）：anolis available <15G 时
  fail-closed 暂派新臂（不杀在跑任务），恢复自动放行；同样需重启调度器生效。
- anolis ~/ch-mes ClickHouse 已按原启动方式拉起（pid 50003，5221/5222，探针行
  repair_probe 写入+回读成功，版本 26.7.34.3）。

---

## ① 32G swapfile（安全网，不是性能件）

现状实测（2026-10-21 17:5x）：`/proc/swaps` 为空（无 swap）；fstab 无 swap 项；
`/`（ext4，98G）仅剩 **19G（80% 用）**，`/data`（ext4，295G）余 **162G（43%）**。

理由：125G 机器无 swap = 内存压力瞬间 OOM 击杀；32G swap 让内核在极端压力下先溢出，
给容器上限与调度器内存门争取反应时间。**注意：32G 放不进 `/`（仅 19G 余量，放下去根分区
秒满，10-19/10-20 两次根分区满载事故就是这么来的）——命令按放 `/data` 给出。**

```bash
# 32G swapfile 放 /data（余 162G）。如需放 /，先把根分区清出 >33G 再自行替换路径。
sudo fallocate -l 32G /data/swapfile        # ext4 支持；若报不支持改用下行 dd
# sudo dd if=/dev/zero of=/data/swapfile bs=1M count=32768 status=progress
sudo chmod 600 /data/swapfile
sudo mkswap /data/swapfile
sudo swapon /data/swapfile
echo '/data/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
```

验证：`swapon --show`（应见 32G）、`free -h`。
回滚：`sudo swapoff /data/swapfile` 并删除 fstab 对应行。
交互说明：docker 的 `--memory-swap` 未显式设置时默认=2×`--memory`，即单容器最坏可再用
与其内存上限相等的 swap——14 臂 agent 6g 理论极端值远超 32G。**swap 是缓冲不是许可，
真正的闸是 af-bench 容器上限（已落地代码）+ 本文件 §④ 的 swappiness**。

## ② journald 限速

现状实测：anolis journal 占用 315.1M（2026-10-21 17:5x `journalctl --disk-usage`）。
本机（pandev-comp）同项曾 3.9G 无上限（10-20 审计记录），事故期日志风暴会把根分区推向写满。

```bash
sudo mkdir -p /etc/systemd/journald.conf.d
sudo tee /etc/systemd/journald.conf.d/00-rate-limit.conf > /dev/null <<'EOF'
[Journal]
RateLimitBurst=1000
RateLimitIntervalSec=30s
EOF
sudo systemctl restart systemd-journald
```

验证：`journalctl --disk-usage`（restart 安全：不杀业务进程，已归档日志不丢）。
说明：只限速不限额（未设 SystemMaxUse）；如想同时限容量可加一行 `SystemMaxUse=500M`
（本次未含，运营者可选）。

## ③ docker daemon 代理（现状已变，先读再动；会重启 docker，务必工厂空闲窗口执行）

现状实测（2026-10-21 17:5x，与运营者表述有出入，先核实）：
- `/etc/systemd/system/docker.service.d/proxy.conf` **已不是**死掉的
  `socks5h://100.64.0.3:1080`——主代理 10-21 00:33（计划/60 落地）已把它改写为
  **governance-machine 出口网关 100.64.0.6:7890（带认证凭据，明文在文件里）**；
  anolis dockerd 已于 10-21 16:20:54（本次重启）后带上该代理，现役生效中。
- 运营者要求的目标 `http://100.64.0.8:7890` = **pandev-comp 本机的 mihomo**
  （pid 2000426，只绑 100.64.0.8:7890、tailnet 内可达、无鉴权）。实测
  `ssh anolis 'curl -x http://100.64.0.8:7890 https://github.com'` → **200 通**。
  （gov 网关 100.64.0.6:7890 无凭据直连会被拒——计划/60 设计的强口令认证，属预期；
  带文件内凭据的代理今天实测拉取 daocloud mirror 时 EOF 过一次，节点在 8↔37 抖动属已知态。）

方案 A（运营者指定：改用本机 mihomo，无鉴权）：
```bash
sudo tee /etc/systemd/system/docker.service.d/proxy.conf > /dev/null <<'EOF'
[Service]
Environment="HTTP_PROXY=http://100.64.0.8:7890"
Environment="HTTPS_PROXY=http://100.64.0.8:7890"
Environment="NO_PROXY=localhost,127.0.0.1,100.64.0.0/10"
EOF
sudo systemctl daemon-reload && sudo systemctl restart docker
```
验证：`systemctl show docker --property=Environment`；随后 `ssh anolis 'docker pull python:3.12-slim'` 应能拉通（今天因 mirror EOF 失败过一次）。
**窗口要求：restart docker 会打断 anolis 上全部在跑测评容器（含在飞臂）——请在工厂
空闲窗口执行（建议等当前臂自然跑完/或运营者指定的停机窗）。**

方案 B（保持现役 gov 网关）：**无需任何操作**，现文件已生效。

风险提示（须运营者知晓）：方案 A 的代理对全 tailnet 无鉴权开放——正是计划/60 §1.4
前车之鉴的模式（hk gost 曾被无鉴权滥用 89 万连接/370MB 日志）。gov 网关（方案 B）
有强口令认证，是计划/60 定案的共享出口。如无特殊理由建议保留现役。

### 安全事件附注（本次排查产生，需运营者处置）
本子代理今日排查时 `cat` 了上述 proxy.conf，**gov 网关口令明文进入子代理转录**
（2026-09-28 consumer key 泄入转录的先例同款）。建议：轮换 gov `/opt/egress-gw/` 的
mihomo 认证口令，并同步更新全部消费端（anolis 本 proxy.conf、gov/anolis 的 profile.d、
grok env.sh）。轮换属 gov 侧动作，不在本 anolis 清单内；本清单与最终报告均已如实登记。
（后续排查一律只出键名/主机名，不出值——教训已固化。）

## ④ vm.swappiness 建议值：10

现状：非 root 读不到当前值（`sysctl` 不在 pan-ding PATH，sudo 需密码），执行时可见原值。
理由：默认 60 对 125G 富内存 bench 机是纯损耗（积极换出匿名页，破坏判分/V100 负载的
局部性）；10 = 几乎不主动换出，只在真实压力下溢出——与 ① 的 32G swap 定位一致
（"快死了缓冲一下"，不是日常换出）。

```bash
sudo sysctl -w vm.swappiness=10
echo 'vm.swappiness=10' | sudo tee /etc/sysctl.d/99-anolis-bench.conf
```

验证：`cat /proc/sys/vm/swappiness` 应返回 10。

---

## 更新记录

| 日期 | 身份 | 变化 |
|---|---|---|
| 2026-10-21 17:5x | 修理组子代理（资源护栏轮） | 建单：四项+两附注（安全事件、磁盘约束）。现状全部 ssh 实测：无 swap、/ 余 19G、journal 315M、drop-in 已为 gov 网关（00:33 主代理写入）、100.64.0.8:7890 从 anolis 实测 200、swappiness 非 root 不可读 |
| 2026-10-22 00:5x | 主代理（fork·运营者授权 sudo） | **①②④ 三项执行完毕并验收**：①32G swapfile 落 /data（swapon 见 32G、fstab 已记、free 显示 Swap 31Gi 可用 0 使用=纯缓冲）；②journald 限速+SystemMaxUse=500M 双配置（服务重启 active，占用 499.3M=已按上限收敛）；④vm.swappiness=10（运行时+99-anolis-bench.conf 持久化；执行时原值 30）。**③ 不动**：现役 gov 网关按清单建议保留（方案 B 零操作）；如改方案 A 需 restart docker=打断在飞臂，待工厂空闲窗+运营者明确指定后执行。**产线无损核验**：docker active、容器原样、mcode 线判分数继续增长（87→92 / 85→93）。**身份事实（影响后续协作）**：运营者提供的 sudo 口令属 anuser（pan-ding 的 sudo 口令三次被拒，勿再试防锁定）；且 pan-ding 可直接 `ssh root@100.64.0.7` 密钥登录——本清单前提"无 root 途径"已失效，D-29 轮换的 anolis 侧写权限阻碍已解除（可与 gov 侧同窗口执行）。口令未落本工作区任何文档。 |
