# mcode 官方线残留 prepare_failed 定性（分析组，2026-10-22 03:1x CST）

> 范围：只读定性，不做停滞诊断。数据源：本地 /tmp/mcode-dispatch/state.json、
> /tmp/mcode-dispatch.log、tools/mcode-dispatch.py；anolis /data/bench/mcode-swev（只读）。
> 写报告时派发器 pid=3711801 仍在跑（`mcode-dispatch.py run`，已运行约 1.4h），残留仍在收敛。

## 1. 残留清单（state.json，读于 ~03:01）

首次读取时 11 条 prepare_failed + 1 条 error + 2 条 solving；复核时（~03:10）已变为
9 条 prepare_failed + 1 条 error（psf__requests-2317|m31f 于 03:03:57 转入 solving，
psf__requests-1921|m3 于 03:03:55 judged/pass）。残留明细：

| 条目 | 档 | phase(首读) | 最后失败 ts | 现状(复核) |
|---|---|---|---|---|
| pydata__xarray-3095 \| m3 | D2 | prepare_failed | 10-21 20:06:40 | 待重试 |
| pydata__xarray-3095 \| m31f | D2 | error | 10-21 20:35:16 | 待重试 |
| pydata__xarray-3305 \| m3/m31f | D2 | prepare_failed ×2 | 10-21 20:06:42/43 | 待重试 |
| pydata__xarray-3993 \| m3/m31f | D2 | prepare_failed ×2 | 10-21 20:06:45/47 | 待重试 |
| pydata__xarray-4356 \| m3/m31f | D2 | prepare_failed ×2 | 10-21 20:06:48/50 | 待重试 |
| pydata__xarray-4966 \| m3/m31f | D2 | prepare_failed ×2 | 10-21 20:06:51/53 | 待重试 |
| psf__requests-2317 \| m31f | D2 | prepare_failed | 10-21 19:43:51 | 已转 solving（03:03:57，重试中） |

注：psf__requests-1921 两条为 solving 在飞（非残留失败态），1921|m3 已 judged/pass。

## 2. 逐条归因（全部同源，非 7 种原因，而是 1 种）

**根因：2026-10-21 19:43–20:35 窗口内，pydata/xarray（及 psf/requests）仓库缓存
重建竞态 —— 旧版 ensure_repo（无 flock 串行化）下一个 worker 正对缓存做全量
`git clone`，另一 worker 的 `git clone --shared` 拿到零引用的半成品缓存，
clone 出 0 refs 的空壳工作区，checkout base 失败。**

证据链：

1. 派发器日志 /tmp/mcode-dispatch.log:
   - L1243,1255,1262,1269,1276,1283,1290,1297,1304,1311：上述 10 条 prepare 失败，
     stderr 尾部均为同一截断片段 `ain', 'trunk' and`（prepare() 只存 stderr[-200:]，
     tools/mcode-dispatch.py:590-591）。该片段是 git `init.defaultBranch` 建议
     ("Names commonly chosen instead of 'master' are 'main', 'trunk' and
     'development'") 的子串——git 对"零引用空仓库 clone"才会打印此 hint。
   - L1326（20:35:16）：`pydata__xarray-3095|m31f` 异常 TimeoutExpired——
     旧 ensure_repo 内联 `git clone --quiet https://github.com/pydata/xarray.git
     /data/bench/mcode-swev/repos/pydata__xarray` 满 1800s 超时（github 直连慢），
     phase=error。此即当时正在进行的缓存重建，其余 9 条正是与它竞态的受害者。
2. anolis 残留工作区（只读核实）：
   - /data/bench/mcode-swev/runs/ 下留有 10 个 10-21 20:06 的残壳目录
     （pydata__xarray-{3095,3305,3993,4356,4966}-{m3,m31f}，缺 3095-m31f——
     它死在 ensure_repo 阶段、未建工作区，时间线吻合）。
   - 抽检 pydata__xarray-3095-m3/.git：HEAD=ref:refs/heads/master、refs 计数=0、
     `git log` 报 "your current branch 'master' does not have any commits yet"、
     objects/info/alternates 指向共享缓存——零引用空壳 clone 的确证。
3. 缓存现状健康：repos/pydata__xarray 于 10-22 00:31 由新版 repo-cache.sh
   （flock 串行 + 毒缓存自清理，见 anolis:~/mcode-swev/repo-cache.sh 头注）
   重建成功（dispatch.log L1446 "clone 缓存 pydata/xarray …"）；5 个残留题的
   base commit（1757dffa/69c7e01e/8cc34cb4/e05fddea/37522e99）在现缓存中
   全部 `cat-file -t` = commit；requests 的 091991be 同样存在。

**分类口径**：不是镜像缺失/拉取失败（本线不用 docker 镜像做 prepare），不是
prepare 脚本超时，不是出口代理抖动。准确分类 = **环境构建失败（git 仓库缓存
重建竞态，旧代码缺陷）**；其中 3095|m31f 附加 **缓存重建超时（github 直连 1800s
超时）→ phase=error**。

**为何此后未再犯**：repo-cache.sh（2026-10-22 修 D2 停滞）已把缓存重建 flock
串行化且不留半成品；本波 00:31 起所有以 prepare_failed 起步的 xarray 题
（6992/2905/3151/3677/4075/4094/4629/4687 等）全部 prepare 成功。

## 3. 会不会被自然重试消除？——会，且正在发生

依据 tools/mcode-dispatch.py:

- 重试逻辑（L740-752, worker L754-785）：prepare_failed/error 不再一次判死，
  每进程每任务 ≤3 次（MAX_ATTEMPTS=3，L115），间隔 60s 重排队；attempts 为
  进程内存字典（L519），**进程重启即清零重新计数**。
- build_queue（L787-799）每次启动把计划全部 240 条入队，worker 跳过 judged
  （L772-773），非 judged 一律重跑 run_one——即每轮重启都是一次全量收敛扫描。
- 队列顺序 = (TIER_ORDER[D1=0,D2=1,D3=2], instance_id)（L109,789）。残留 5 题
  xarray 全部属 D2，按字典序排在 psf__requests 之后（'psf'<'pydata'）——
  **当前扫描恰好推进到 D2 尾部**：03:00/03:01 起 requests-1921、03:03 起
  requests-2317|m31f 已进入 solving，xarray 五题是队列中下一批。
- 即使本进程 3 次用尽，日志明示"可人工 once 补跑"（L750-752，
  `mcode-dispatch.py once <tid> <profile>`，经 mcode-once-wrapper.sh 过资源闸）。

**结论：无需人工处置（不需拉镜像、不需跳过）。残留纯粹是"扫描还没扫到"，
不是"重试治不好"——根因缺陷已被 repo-cache.sh 修复，base commit 在健康缓存中
全部在场，扫到即应通过 prepare。** 建议仅作观察项：若 dispatcher 扫过后仍有个别
prepare_failed，再派单查；人工 once 补跑仅在进程内 3 次耗尽后需要。

## 4. 本重试波统计（供官方线分母口径注记）

口径：dispatch.log 中 2026-10-22 起以 `开始 … (phase=prepare_failed)` 起步、
后有 `完成` 记录的条目（n=57 起步，含跨 profile）。

- prepare_failed → judged 完成：**55/57**（剩 2 条 solving 在飞：
  requests-1921|m31f、requests-2317|m31f；后者完成后预计 56/57，
  xarray 五题 10 条尚在队列未起步，不在此 57 内）。
- 55 条判分分布：**pass 47 / fail 5 / judge_error 3**。
  fail 5 = django-14315|m3、django-15629|m3、pylint-4604|m3、requests-2931|m3、
  xarray-2905|m3（注：fail 全部落在 m3 档案，5/5——单点模式，样本小，仅供注记）。
  judge_error 3 = django-16263|m3、flask-5014|m3、xarray-4687|m3（reward=None）。
- 分母注记：state.json 中 judged 共 228 条，其中 reward=None（judge_error）
  4 条（上述 3 条 + matplotlib-13989|m31f 为更早遗留）——算通过率时它们既非
  pass 也非 fail，分母口径需显式声明是否剔除。

## 5. 已查位置清单（无"无痕迹"条目）

- 本地：/tmp/mcode-dispatch/state.json；/tmp/mcode-dispatch.log（L1242-1326,
  1445-1536，尾部至 03:01）；tools/mcode-dispatch.py（L94-127,513-603,700-799）；
  /tmp/swev-s1/{6 题}.json（base_commit）；计划/s1-swev-120.json（tier）。
- anolis（只读）：/data/bench/mcode-swev/repos/{pydata__xarray,psf__requests}
  （cat-file 验证 6 个 base commit 全在）；/data/bench/mcode-swev/runs/ 残壳
  10 目录及 pydata__xarray-3095-m3/.git 内部；~/mcode-swev/repo-cache.sh；
  `df /data` 余量 107G（非磁盘因素）。
