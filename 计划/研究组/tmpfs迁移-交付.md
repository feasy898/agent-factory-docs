# tmpfs 迁移交付 — 产线结果目录迁出 /tmp（D-24 主项软施工）

> 执行：修理组子代理（tmpfs 迁移轮，step-5-preview 载体）｜时间：2026-10-22 12:50–13:15 CST
> 任务书：运营者已批软施工第二项（触发条件：④组 tmpfs 治理五补丁全部落地测试通过）
> 依据：`设计/分流默认根约定.md` §1（结果归档默认根 `~/bench-data/`）§2（/tmp 白名单）；`AGENT.md` 硬纪律 7
> 证据日志：`/tmp/tmpfs-migration-20261022.log`（耐久副本 `工具状态备份/tmpfs-migration-20261022.log`）
> 脚本留档：`工具状态备份/tmpfs-migrate.sh`、`工具状态备份/verify-batch1.sh`、`工具状态备份/baseline-first-scan.tsv`

## 1. 结果概要

| 项 | 值 |
|---|---|
| 迁移成功 | **91 项**（87 产线目录 → `~/bench-data/results/`；4 证据项 → `~/bench-data/evidence/`；含臂终态后补迁 1 项，见 §4） |
| 文件总数 | 22738 个（21585 + 96 + 1153） |
| results.jsonl 行数合计 | 3578 行（2598 + 902 + 78） |
| 数据量 | apparent 1,194,020,158 字节（约 1.11 GiB）／du -sm 约 1179 MiB |
| 原位软链 | 91 条，全部 `readlink` 精确指向目标且读回校验通过（旧路径引用全兼容） |
| 跳过 | 6 项（swev-s1、bench-fix2-rerun-*×5），原因见 §6 |
| /tmp 占用 | used 5661→4097 MiB（**净 −1564 MiB**），avail 1957→3521 MiB，75%→**54%** |
| 数据丢失 | **0**（对账不一致即停手机制未触发；批次1 缺陷与补偿见 §8） |

## 2. df 前后对比

| 挂载点 | 指标 | 前（12:55） | 后（13:12） | Delta |
|---|---|---|---|---|
| /tmp（tmpfs 7.5G） | used MiB | 5661 | 4097 | −1564 |
| /tmp | avail MiB | 1957 | 3521 | +1564 |
| /tmp | 使用率 | 75% | 54% | −21pp |
| /（nvme） | used MiB | 398375 | 410819 | +12444 |
| / | avail MiB | 55808 | 43363 | −12445 |
| / | 使用率 | 88% | 91% | +3pp |

**/ 增长归因（诚实记账）**：本迁移迁入 `~/bench-data` 的数据经目录级实测为 **+1602 MiB**（bench-data 623→2225 MiB，含桶；其中补迁项 72 MiB）；其余 **约 +10.8 GiB 为并发写入**——集中在 13:07–13:12 的 5 分钟突发（mcode-clean-rerun driver 的瞬时 cargo 子进程、guardrail 试跑臂、docker 层churn 等同期活动），30s 复测已趋稳（410831→410819，净 −12MB）。本机 `/` 无任何告警码（④组三审 issue 4 同族现象）列为观察项交巡检。

## 3. 方法与对账口径

逐项四步（脚本 `tmpfs-migrate.sh`，源数据在任何校验通过前不删）：
1. **对账前量**：results.jsonl 行数 + sha256(前16) + 文件数（find -type f）+ du -sb 字节；
2. **复制**：`cp -a` 至目标 `.incoming`，复量四指标，不一致即停手（保留源、删 incoming、exit 90）；
3. **切换**：`mv 源 源.migrated-src` → `ln -s 目标 /tmp/原名` → 经软链读回复量四指标 + readlink 断言，不一致即回滚本项（rm 软链、mv 回）；
4. **收尾**：`rm -rf 源.migrated-src`，落 item 日志行。

在飞判定四扫（任务书判定法）：`lsof +D /tmp`（fd）+ `/proc/*/cwd`（cwd）+ `/proc/*/environ`（env）+ `/proc/*/cmdline`（argv）+ mtime 近 30 分钟。批次1 另有独立交叉验证（§8）。

## 4. 批次明细

| 批次 | 内容 | 项数 | 结果 |
|---|---|---|---|
| batch1-prod | /tmp/bench-fix1-*（−在飞1）、bench-fix2-*（−rerun5）、bench-s1-*、bench-official-*、bench-rejudge* 目录 | 86 | 全部 OK（补偿对账，§8） |
| batch2-evidence | truth-rejudge/、truth-manifest.jsonl、rejudge-xarray-3095/、rejudge-xarray-4687/ | 4 | 全部 OK（实时对账） |
| batch3-taskpkg | swev-s1 任务包 | 0 | **跳过**（§6），留证 |
| batch4-supplement | bench-fix1-d1-m31f（批次1 时在飞臂 pid 484784 持写句柄；13:15 前臂退出、复扫零句柄零进程引用后，按"臂换题间隙"窗口补迁） | 1 | OK（实时对账；截断行见 §8） |

## 5. 逐目录对账表

> 行数/sha/文件数/字节为迁移后经软链读回实测；基线文件数=12:52 首扫实测（迁移前独立记录）。
> `-` = 该目录无顶层 results.jsonl（truth-rejudge 为 P1 launcher 账本、xarray 为重判证据件）。

| # | 目录/文件 | 类 | results.jsonl 行数 | sha256(前16) | 文件数 | 字节数(du -sb) | 基线文件数 | 对账 |
|---|---|---|---|---|---|---|---|---|
| 1 | bench-fix1-d1-30b | 产线 | 62 | 485dafad7caa3a7d | 1255 | 50857567 | 1255 | OK |
| 2 | bench-fix1-d1-deepseek-cb | 产线 | 60 | 78076068b08c7db4 | 185 | 12583962 | 185 | OK |
| 3 | bench-fix1-d1-glm-cp | 产线 | 58 | 62129f8e68bb960c | 1089 | 52782455 | 1089 | OK |
| 4 | bench-fix1-d1-glm-cp-local | 产线 | 15 | 1a62d71767b6e9e4 | 311 | 16009575 | 311 | OK |
| 5 | bench-fix1-d1-glm-max | 产线 | 60 | 730e1d2ff3a6de32 | 1100 | 51401954 | 1100 | OK |
| 6 | bench-fix1-d1-kimi | 产线 | 55 | 953fa459e26fb86a | 989 | 43994953 | 989 | OK |
| 7 | bench-fix1-d1-kimi-k3-local | 产线 | 10 | a00651157e526a89 | 197 | 5351032 | 197 | OK |
| 8 | bench-fix1-d1-m3 | 产线 | 67 | a1abe54385ef94f2 | 1114 | 49689260 | 1114 | OK |
| 9 | bench-fix1-d1-m3-mingda | 产线 | 15 | 21be04f6aabd963f | 315 | 16431931 | 315 | OK |
| 10 | bench-fix1-d1-m31f-mingda | 产线 | 10 | 880ee562779e1ca7 | 209 | 17511278 | 209 | OK |
| 11 | bench-fix1-d1-step5 | 产线 | 73 | 3025842e35c22243 | 995 | 60727636 | 995 | OK |
| 12 | bench-fix1-d2-30b | 产线 | 42 | 1c836024f3d1e9c3 | 820 | 26178080 | 820 | OK |
| 13 | bench-fix1-d2-deepseek-cb | 产线 | 40 | d6aa5168bb1f0237 | 121 | 3822079 | 121 | OK |
| 14 | bench-fix1-d2-glm-cp | 产线 | 46 | e48a055691c76185 | 738 | 32650785 | 738 | OK |
| 15 | bench-fix1-d2-glm-max | 产线 | 41 | e0c61e6c55c93124 | 757 | 30134506 | 757 | OK |
| 16 | bench-fix1-d2-kimi | 产线 | 40 | eb32b2c26bbb3a84 | 773 | 24144199 | 773 | OK |
| 17 | bench-fix1-d2-m3 | 产线 | 42 | 1b3cd3ae2c62dba3 | 860 | 31291297 | 860 | OK |
| 18 | bench-fix1-d2-m31f | 产线 | 57 | ebb780511a0cf135 | 532 | 39426550 | 532 | OK |
| 19 | bench-fix1-d2-step5 | 产线 | 57 | 69568ff317a0ee95 | 630 | 35635456 | 630 | OK |
| 20 | bench-fix1-d3-30b | 产线 | 20 | be5093b563c30664 | 390 | 18392720 | 390 | OK |
| 21 | bench-fix1-d3-deepseek-cb | 产线 | 20 | fe49bf3483329864 | 61 | 7249861 | 61 | OK |
| 22 | bench-fix1-d3-glm-cp | 产线 | 18 | 94969c405e6be601 | 371 | 24166408 | 371 | OK |
| 23 | bench-fix1-d3-glm-cp-local | 产线 | 13 | 0444e470a002779e | 272 | 21904761 | 272 | OK |
| 24 | bench-fix1-d3-glm-max | 产线 | 24 | 1fdb9d2d6f30d47b | 349 | 31192688 | 349 | OK |
| 25 | bench-fix1-d3-kimi | 产线 | 21 | 3ff726dab59c894e | 367 | 21942427 | 367 | OK |
| 26 | bench-fix1-d3-m3 | 产线 | 28 | d2d1f78cd132d349 | 385 | 23056660 | 385 | OK |
| 27 | bench-fix1-d3-m31f | 产线 | 20 | 2eea8ae68a764f7a | 349 | 29259310 | 349 | OK |
| 28 | bench-fix1-d3-step5 | 产线 | 21 | 8eec7d75141b91b1 | 302 | 32631367 | 302 | OK |
| 29 | bench-fix1-localtest-glm-cp | 产线 | 2 | 40dfb5f1c7cf6d45 | 39 | 2921826 | 39 | OK |
| 30 | bench-fix1-mingdatest-glm-cp | 产线 | 1 | 6ee555a9f834daa0 | 19 | 1437851 | 19 | OK |
| 31 | bench-fix2-ab-glm-cp | 产线 | 15 | c7e0b717843d3ea1 | 254 | 12506258 | 254 | OK |
| 32 | bench-fix2-ab-m31f | 产线 | 35 | 379b63ba7e722409 | 222 | 21641794 | 222 | OK |
| 33 | bench-official-mcode-d1-m3 | 产线 | 97 | a77b69281726732d | 301 | 12760811 | 301 | OK |
| 34 | bench-official-mcode-d1-m31f | 产线 | 95 | c961a6a96eebcd9f | 301 | 12930308 | 301 | OK |
| 35 | bench-official-mcode-d2-m3 | 产线 | 88 | f896f17aa0ebaf8b | 201 | 4300990 | 201 | OK |
| 36 | bench-official-mcode-d2-m31f | 产线 | 87 | 445affea7c8c4723 | 201 | 4317454 | 201 | OK |
| 37 | bench-official-mcode-d3-m3 | 产线 | 38 | e782b6f89daa7746 | 101 | 7567455 | 101 | OK |
| 38 | bench-official-mcode-d3-m31f | 产线 | 39 | 5118ea8568dcc364 | 101 | 7600397 | 101 | OK |
| 39 | bench-official-mcode-m3 | 产线 | 226 | 8aa08fec2d8e3201 | 1 | 93080 | 1 | OK |
| 40 | bench-official-mcode-m31f | 产线 | 221 | 3fd85dec151db14e | 1 | 90435 | 1 | OK |
| 41 | bench-official-zcode-step5 | 产线 | 123 | 192ac6896982cabe | 481 | 23579954 | 481 | OK |
| 42 | bench-rejudge-d1 | 产线 | 47 | e85cf93fb52fdd37 | 1 | 18784 | 1 | OK |
| 43 | bench-rejudge-d2 | 产线 | 24 | 25825f13f5aa6754 | 1 | 9579 | 1 | OK |
| 44 | bench-rejudge-d3 | 产线 | 7 | 133ea083b05594b5 | 1 | 2717 | 1 | OK |
| 45 | bench-rejudge-fix1-step5 | 产线 | 9 | 52b1e7893564d5dd | 1 | 3639 | 1 | OK |
| 46 | bench-rejudge2-fix1-localtest-glm-cp | 产线 | 2 | 5aab884f9ba2d577 | 1 | 822 | 1 | OK |
| 47 | bench-rejudge2-fix1-mingdatest-glm-cp | 产线 | 1 | ead5f9f5a2d8e3d1 | 1 | 412 | 1 | OK |
| 48 | bench-rejudge2-fix2-rerun-step-5 | 产线 | 1 | d87a28f13660b63b | 1 | 413 | 1 | OK |
| 49 | bench-rejudge2-s1-d1-30b | 产线 | 26 | bd053c9a47e3881d | 1 | 11064 | 1 | OK |
| 50 | bench-rejudge2-s1-d1-8b | 产线 | 3 | c133501ed7decfec | 1 | 1277 | 1 | OK |
| 51 | bench-rejudge2-s1-d1-glm | 产线 | 6 | 3070a06de452ba10 | 1 | 2466 | 1 | OK |
| 52 | bench-rejudge2-s1-d1-glm-max | 产线 | 29 | 3c10c1590152a188 | 1 | 12270 | 1 | OK |
| 53 | bench-rejudge2-s1-d1-glm-r2 | 产线 | 27 | 4b41bf27fc49e221 | 1 | 11197 | 1 | OK |
| 54 | bench-rejudge2-s1-d1-kimi | 产线 | 11 | 0a29356a73fe2abd | 1 | 4495 | 1 | OK |
| 55 | bench-rejudge2-s1-d1-m31f | 产线 | 23 | f959492c1417346d | 1 | 9679 | 1 | OK |
| 56 | bench-rejudge2-s1-d1-step5 | 产线 | 4 | c7591b61aa8cac84 | 1 | 1638 | 1 | OK |
| 57 | bench-rejudge2-s1-d2-30b | 产线 | 9 | b0a191a7304471ac | 1 | 3824 | 1 | OK |
| 58 | bench-rejudge2-s1-d2-glm | 产线 | 9 | 505a483ccb457e34 | 1 | 3704 | 1 | OK |
| 59 | bench-rejudge2-s1-d2-glm-max | 产线 | 9 | 418318303eb28adf | 1 | 3806 | 1 | OK |
| 60 | bench-rejudge2-s1-d2-kimi | 产线 | 2 | 8bba5544382147e6 | 1 | 822 | 1 | OK |
| 61 | bench-rejudge2-s1-d3-30b | 产线 | 1 | ca8c501935cf07e5 | 1 | 426 | 1 | OK |
| 62 | bench-rejudge2-s1-d3-glm | 产线 | 13 | 53dd70f61a3ae789 | 1 | 5302 | 1 | OK |
| 63 | bench-rejudge2-s1-d3-glm-max | 产线 | 10 | 5a7122223293fa4b | 1 | 4203 | 1 | OK |
| 64 | bench-rejudge2-s1-d3-m31f-r2 | 产线 | 6 | cdfd499d17e0fca8 | 1 | 2486 | 1 | OK |
| 65 | bench-rejudge2-swev | 产线 | 10 | 8365dce679283533 | 1 | 4112 | 1 | OK |
| 66 | bench-s1-d1-30b | 产线 | 26 | 999adf818c56aa0e | 468 | 23710271 | 468 | OK |
| 67 | bench-s1-d1-8b | 产线 | 7 | ed49a0fc2b0ec866 | 104 | 2883882 | 104 | OK |
| 68 | bench-s1-d1-glm | 产线 | 5 | f06083e1d9b5d70d | 99 | 5601948 | 99 | OK |
| 69 | bench-s1-d1-glm-max | 产线 | 28 | bf20a861c95da677 | 485 | 23670138 | 485 | OK |
| 70 | bench-s1-d1-glm-r2 | 产线 | 26 | adab84e29d3a3b2d | 456 | 21537926 | 456 | OK |
| 71 | bench-s1-d1-kimi | 产线 | 12 | bf0cad10096bb078 | 211 | 13523292 | 211 | OK |
| 72 | bench-s1-d1-m31f | 产线 | 24 | 13bd754fc214d819 | 385 | 19203649 | 385 | OK |
| 73 | bench-s1-d1-m31f-r2 | 产线 | 0 | e3b0c44298fc1c14 | 1 | 0 | 1 | OK |
| 74 | bench-s1-d1-step5 | 产线 | 5 | 3664c3ef27f67cca | 96 | 10713631 | 96 | OK |
| 75 | bench-s1-d2-30b | 产线 | 9 | 9a774c240d5da263 | 159 | 6630760 | 159 | OK |
| 76 | bench-s1-d2-glm | 产线 | 9 | ba11bd0d8cea95eb | 147 | 3898533 | 147 | OK |
| 77 | bench-s1-d2-glm-max | 产线 | 10 | 399ff999b9b4839c | 149 | 4192432 | 149 | OK |
| 78 | bench-s1-d2-kimi | 产线 | 2 | b779a15db5c0ff68 | 48 | 6742529 | 48 | OK |
| 79 | bench-s1-d2-step5 | 产线 | 0 | e3b0c44298fc1c14 | 12 | 2636961 | 12 | OK |
| 80 | bench-s1-d3-30b | 产线 | 2 | ba5a29c959086775 | 29 | 1494792 | 29 | OK |
| 81 | bench-s1-d3-glm | 产线 | 13 | cd803309e4f0b6ec | 215 | 15029687 | 215 | OK |
| 82 | bench-s1-d3-glm-max | 产线 | 10 | 933fef239d74d423 | 176 | 13592440 | 176 | OK |
| 83 | bench-s1-d3-kimi | 产线 | 0 | e3b0c44298fc1c14 | 12 | 2694584 | 12 | OK |
| 84 | bench-s1-d3-m31f | 产线 | 8 | 40abd98d6d044b52 | 89 | 1267236 | 89 | OK |
| 85 | bench-s1-d3-m31f-r2 | 产线 | 11 | ddbd9da6bf3eb812 | 149 | 13035849 | 149 | OK |
| 86 | bench-s1-d3-step5 | 产线 | 0 | e3b0c44298fc1c14 | 12 | 5166213 | 12 | OK |
| b1 | truth-rejudge | 证据 | - | - | 66 | 540738 | — | OK |
| b2 | truth-manifest.jsonl | 证据 | 902 | 2c015a658240aa15 | 1 | 251135 | — | OK |
| b3 | rejudge-xarray-3095 | 证据 | - | - | 13 | 85325 | — | OK |
| b4 | rejudge-xarray-4687 | 证据 | - | - | 16 | 383333 | — | OK |
| 87 | bench-fix1-d1-m31f | 产线 | 78 | 90fdcc641d36aa10 | 1153 | 73248867 | 1153 | OK（补迁，第76行截断见 §8） |

## 6. 跳过清单与原因（6 项，全部留证于证据日志）

| 项 | 尺寸 | 跳过原因（判定证据） |
|---|---|---|
| /tmp/swev-s1（任务包） | 4 MiB | **在飞**：5 个活进程以 `--data-root /tmp/swev-s1` 逐题取任务（af-bench 484784/540277、af-bench-guardrail 485135/485150、af-bench-fix2、mcode-clean-rerun driver 454598 进程群）；且 `设计/分流默认根约定.md` §2 白名单明文列入"工厂运行时件"（任务包），由三道闸守护。任务书"若约定允许则迁"——约定明确其可驻留 /tmp 且在飞，故不迁 |
| /tmp/bench-fix2-rerun-glm-cp 等 5 个 | 36 MiB | **在飞守护进程显式登记**：factory-watch pid 3692358 的 environ 实持 `AF_WATCH_EXTRA_DIRS=/tmp/bench-fix2-rerun-*,/tmp/factory2-status.json`（sibling 会话为盯 fix2 rerun 线注入），按判定法列入跳过。注：watch 对内建产线臂目录为只读观测（scan_arm 纯 isdir/stat/open，软链透明，已读码核实），故主产线目录不因此跳过 |

> 原第 3 项 /tmp/bench-fix1-d1-m31f（批次1 时在飞臂 pid 484784）已于 13:15 前臂退出、复扫零句柄后按"臂换题间隙"补迁（§4 batch4），跳过清单随之减为 6 项。

## 7. 未枚举遗留项（未动，供运营者裁决是否扩批）

| 类别 | 项 | 尺寸 |
|---|---|---|
| 在飞线产物（非枚举） | /tmp/bench-clean-mcode-m31f（考古重跑线 out，driver 454598 在飞）、/tmp/mcode-clean-rerun/（driver 状态与脚本）、/tmp/sample-agg/（guardrail 试跑 attempt-a2/a3） | ~10 MiB |
| 旧产线目录（非枚举） | bench-s0、bench-s0-glm、bench-s0-m31f、bench-poc-step5(-b)、bench-prof-×5、bench-swev、bench-tb、bench-tb5 | ~55 MiB |
| 臂启动日志（非枚举为文件） | /tmp/bench-*.log ×32 | 1 MiB |
| 证据散件（非枚举） | truth-agg*.json(6)、truth-final.json、truth-launcher.log、truth-launcher.pid（进程已亡）、truth-smoke/-out/-stage、rejudge-audit、rejudge-fix1、rejudge-src-d1/d2/d3、rejudge-*.log/*.txt | 4 MiB |
| 任务书点名不迁 | /tmp/align2-*、align-probe-*、mcode-tune-*、af-wt-*、obs-smoke* | 未动 |

## 8. 缺陷记录与补偿对账（诚实记账）

**缺陷**：批次1 首跑 `metrics()` 内 `local p=$1 rp=$p` 在 `set -u` 下整行展开即报"未绑定变量"→ 命令替换子 shell 静默退出 → 三项指标比较双双为空被判"一致" → **86 行 item 日志的 lines/files/bytes/sha 全为空，对账被旁路**。机械迁移未受影响（cp -a 零报错、mv/ln/rm 全执行、无 `.incoming`/`.migrated-src` 残留）。已修（local 拆行），后续批次实时对账正常。

**补偿对账（verify-batch1.sh，四路交叉，全部亲跑）**：
1. 86/86 软链 `readlink` 精确指向且读回可达；
2. **文件数与 12:52 首扫基线（迁移前独立实测）逐一精确一致：21585 个，0 差异**；du -sm 与基线差全部 ≤2 MiB（tmpfs→ext4 目录块差），0 WARN；
3. 86 个 results.jsonl 共 2598 行 **JSON 逐行解析 0 坏行**；
4. 文档聚合读数复现：bench-rejudge2-* 合计 **202 行** = `设计/fix1全量干净重判-读数.md` 所载互补 202 行；mcode d1-d3 共 444 行 = 235 completed + 203 prepare_failed + 1 apply_failed + 5 judge_error，distinct(task,profile)=**240** = 文档 judged 240；truth-manifest.jsonl **902 行** = 文档 P1 902 行。

**数据质量观察（batch4 补迁项，只记录不修）**：`bench-fix1-d1-m31f/results.jsonl` 第 76 行（sphinx-doc__sphinx-10449，partial record 725B 中断于 verifier_note）为**迁移前既有截断行**——before/after 字节级一致证明非迁移所致；形态与该臂 12:31"partial 重回队列"、进程 13:15 前退出半写相符，第 77/78 行为完整记录。全量 91 个 results.jsonl 复扫仅此 1 处。按证据零改写纪律不修不补（如需修正须走追加 correction 行先例，归分析组/运营者裁决）。

## 9. 实况验证：软链经受生产重派检验

调度器于迁移后 13:07:53 新派臂 pid 540277（af-bench，sympy 题）写入**已迁软链** /tmp/bench-fix1-d2-m31f：lsof 实证其 fd 穿透解析至 `/home/pan-ding/bench-data/results/bench-fix1-d2-m31f/results.jsonl`(3w) 与 runs/ 下 sqlite，臂正常工作。即 af-bench 现役实现对 out 仅 `create_dir_all`（main.rs:642，旧实现的 remove_dir_all 已移除）+ 软链穿透 = 未来重派零打扰，方案经实况证实。

## 10. 回滚（整链软链天然可回滚）

**总回滚一行**（全部 91 项；异设备 mv=复制+删源非瞬时，与桶先例同）：
```bash
cd ~/bench-data && for f in results/* evidence/*; do n=$(basename "$f"); [ -L "/tmp/$n" ] && { rm -f "/tmp/$n" && mv "$f" "/tmp/$n"; }; done
```
**单项回滚**：`rm /tmp/<名> && mv ~/bench-data/<results|evidence>/<名> /tmp/<名>`

## 11. 遗留与后续建议

1. **P1-6 `results-archiver.py`**（④组 10-25 前）落地时需兼容 `~/bench-data/{results,evidence}/` 现布局（人工迁移先行占用），归档与完整性巡检并入后 D-24 可终偿；
2. ~~bench-fix1-d1-m31f 待臂终态后补迁~~ —— 已于 13:21 补迁完成（§4 batch4）；该臂在调度器为 pending 态，若再派发将穿透软链追加写入（实况已验证两例）；
3. §7 遗留项（约 70 MiB）是否扩批归运营者裁决——本代理未自行扩权（任务书枚举范围外不动）；
4. 观察项：本机 `/` 88%→91%（并发突发所致，已趋稳）且无告警码，交下轮巡检；与迁移无因果（迁移仅 +1.6G）。

## 12. 复现命令

```bash
# 软链有效性全量
for n in $(ls ~/bench-data/results ~/bench-data/evidence); do l="/tmp/$n"; [ -L "$l" ] && [ "$(readlink "$l")" = "$(echo ~/bench-data/{results,evidence}/$n)" ] || echo "BAD $n"; done
# 对账表重算（任一项）
d=/tmp/bench-fix1-d1-30b; wc -l $d/results.jsonl; find $d -type f | wc -l; du -sb $d
# 在飞判定
lsof +D /tmp | awk 'NR>1{print $NF}' | grep -E "^/tmp/(bench|truth|swev|rejudge)" | sort -u
```
