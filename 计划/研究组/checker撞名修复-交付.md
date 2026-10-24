# checker 撞名修复-交付（obs-checker.py，2026-10-22）

> 修理组子代理（step-5-preview 载体）。对象=金丝雀收口发现（obs金丝雀-20261022.md §6.3）的
> run_id 撞名绑定缺陷。纪律：只改 `工具状态备份/observability/obs-checker.py`；事件流/索引/
> manifest 数据文件零改动（陈旧行保留原样）；密钥零明文；没跑过就说没跑过。

## 1. 结论

**缺陷已修，三件验证全过，fail-closed 未削弱**。索引/manifest 绑定由 run_id 首匹配改为
精确联合键（索引=(run_id,path)；manifest=归属 scope (line,arm)），聚合范围同步 scope 化。
修后全量 15 流裸跑 **14 PASS + 1 FAIL**（唯一 FAIL=canary 3151-a1 撕裂 casualty，见 §4③），
金丝雀两个消歧 run 裸跑即 PASS——**消歧成本归零**（不再需要 --index 字节级过滤 + --manifest 显式）。

## 2. 缺陷与改前基线（亲跑复现，非引用）

根因：索引行/manifest 绑定按 run_id 首匹配（load_index_rows 文件序 + break / candidates[0]），
不区分 line/arm。③组 obs-smoke1/2 旧流占用 `pydata__xarray-{2905,3151,4094}-a1` 等 run_id 后，
canary-20261022 线复用同名的合法流被绑到陈旧行。改前 15 流裸跑实测 **5 PASS / 10 FAIL**：

| 流 | 改前 rc | FAIL 形态 |
|---|---|---|
| canary 3151-a2 | 1 | manifest b3 双重计数：兄弟 4094-a1 陈旧行被 Σ 两遍（546≠354；completed 3≠2） |
| canary 4094-a1 | 1 | ×7：索引绑 obs-smoke1 陈旧行（655b1feb≠实算 a9361a2b）+ manifest 误绑 obs-smoke1 批次（merkle/ec/status 全错） |
| canary 2905-a1 | 1 | ×10：索引绑 obs-smoke2 陈旧行 + manifest 误绑 obs-smoke2 批次 |
| canary 3151-a1（撕裂） | 1 | ×9：陈旧索引绑定 + 自身末行非 run_finished |
| obs-smoke1×3（3677/4094/4629） | 1 | ×3 each：manifest 聚合被 canary 4094-a1 兄弟行污染（merkle/ec/status） |
| obs-smoke2×2（2905/3151） | 1 | ×3 each：manifest 聚合被 canary 2905-a1 兄弟行污染 |
| canary 4075/7277、d1×4 | 0 | PASS（5 条本来就对） |

勘误一条：金丝雀证据 `/tmp/obs-canary-20261022/checker-evidence.txt` 的 4094-a1 段缺
ec_sum/status_counts 两条 FAIL（该文件 16:11 生成时的记录不全）——本次复跑实测 4094-a1 改前
为 7 fail 全貌，以此交付为准。

## 3. 修法（只改 obs-checker.py；设计取最稳既有字段，未新造字段）

数据事实：索引行结构=`{run_id, path, ts_started, ts_finished, status, event_count, final_seq,
events_sha256, torn_lines, fp_image_digest}`（path=写侧钉死的本流绝对路径）；manifest 结构=
`{batch_id, created_ts, run_count, run_ids, event_count_total, status_counts, merkle_root, merkle_algo}`
（**只有 run_ids，无 path/line/arm**）；run_started/run_finished payload 亦无 batch_id 字段。

1. **索引绑定：run_id 首匹配 → (run_id, path) 联合键**。path 是索引行里既有的本流绝对路径，
   与事件流来源路径精确相等才绑；撞名时拒绑陈旧行，报"run_id 有 N 行但无一行 path=本流"。
2. **manifest 绑定：run_id 首匹配 → 归属 scope (line,arm) 精确绑定**。manifest 无 path，但
   一个批次=一个 af-bench 进程=一个 (line,arm)（AF_OBS_LINE/AF_OBS_ARM 进程级环境变量），
   其全部 run_ids 的索引行都应落在本流所在 (line,arm)（`manifest_home_scopes`：逐 run_id 求
   索引行 scope 集合的交集）。跨 line 陈旧清单归属在旧线，不再被误绑。
3. **聚合 scope 化**：merkle/Σevent_count/status_counts 只数本 scope 的索引行
   （`derive_manifest_facts(m, scoped_rows)`）——同名兄弟流的陈旧行不再被双重计数。
4. **单 run 批次遇 run_id 跨线重名**（归属天然歧义：清单不记自己的 line/arm）：在完整归属本
   scope 的候选里取自洽者（`manifest_self_consistent`：merkle/run_count/计数/status 对本 scope
   索引行全部复算一致），挑对后仍走全额复验，**不 fail-open**；无一自洽取第一份，FAIL 行如实暴露。
5. **回退路径（保检测力）**：本线清单的兄弟索引行缺失/被删（无任何完整归属 scope）时仍绑定，
   让 `missing_runs` fail-closed 照常暴露（防"删索引行躲 manifest 检查"）；跨线陈旧清单在自己
   线上有完整归属，不会被这条回退捞回。
6. **兜底**：cur_scope 不可判定（非 `runs/<line>/<arm>/<run_id>/events.jsonl` 布局）时维持
   旧行为首匹配，不猜 scope。

新增函数：`line_arm_of` / `manifest_home_scopes` / `derive_manifest_facts` / `manifest_merkle` /
`manifest_self_consistent`；docstring 校验项 10/11 同步改写并加变更史。

## 4. 验证（全部亲跑，2026-10-22 16:2x-16:4x）

**① 金丝雀两个消歧 run 裸跑（无 --index/--manifest）= PASS（0 fail / 0 warn，rc=0）**：
`canary-20261022/mavis-m31f/pydata__xarray-3151-a2`、`…pydata__xarray-4094-a1`。
消歧成本归零（字节级过滤子集与显式 --manifest 不再需要）。

**② obs-smoke 陈旧行互不干扰**：obs-smoke1 的 3677/4094/4629 与 obs-smoke2 的 2905/3151
裸跑全 PASS 0/0（各绑各的索引行与批次清单）；受控对照（/tmp scratch，同 run_id 双线双流+
两份单 run 清单）两线各自 PASS——证明这不是"巧合排序"而是联合键生效。

**③ 全量 14 流回归 PASS**：15 流裸跑 14 PASS + 1 FAIL。唯一 FAIL=canary 3151-a1 撕裂
casualty（冻结挂死留证：末行 harness.resource、无 run_finished、按约定无索引行），其 FAIL 项=
自身撕裂 + 联合键拒绑（obs-smoke2 同名陈旧行在场，报"有 1 行但无一行 path=本流"）——
fail-closed 方向正确且归属精确。另 canary 2905-a1 PASS 带 1 warn（b2 manifest 因进程被 kill
从未写盘，缺位如实记 WARN，不伪造）。

**负面对照（scratch 复刻，全部 rc=1 复现——绑定修好后篡改检测未削弱）**：
- T2 篡改事件流 1 字节 → `events_sha256 不一致` FAIL；还原后回 PASS。
- T4 篡改 manifest merkle_root → `merkle_root 不一致` FAIL。
- T3 本线清单兄弟行缺失 → `missing_runs` + ec/status FAIL（clause-4 回退路径生效）；
  换正确清单后对照 PASS。
- 附带实证：索引行 path 与实流不符（拷贝搬迁未改 path）→ 拒绑 FAIL（联合键不放松）。

**兼容性**：金丝雀绕行法（--index 子集 + --manifest b3）对 3151-a2/4094 仍 PASS（旧用法不破）；
入参形态 a/b/c/d 与 --quiet 全实测（形态 c：`/tmp/obs-canary-20261022` → 7/7 PASS；
形态 d：`runs/obs-smoke1/mavis-m31f` → 3/3 PASS）。

## 5. 指纹登记（冻结集合法变更）

| 项 | 值 |
|---|---|
| 改前 sha256 | `aaae9e53b906df225d9615abeb023262eedeedba016efbaad685f0fda213aa6e` |
| **改后 sha256** | **`3db6bca299ba8deafedbde0951e587480d8348234cf32c20f80b1af911ba0779`** |
| 改前字节备份 | `工具状态备份/observability/obs-checker.py.20261022-pre-撞名修复.bak`（与改前逐字节一致，sha256=旧值） |
| 变更性质 | **修 bug**（run_id 撞名绑定缺陷，金丝雀 §6.3"施工前必修项"）；非测量语义/判分口径/提示词/判分参数变更，无需 bump 结果代号 |

checker 在冻结集内（设计/底座重构施工方案.md §0.3 登记旧值 `aaae9e53…`），指纹变更属
"修 bug 的合法变更"，原因如上。旧 sha 出现位置（**本单未改这些文件**，供主代理传播）：
设计/底座重构施工方案.md（§0.2 观测根行、§0.3 冻结值表、§399 闸1）；设计/RSI自我改进方案.md
（闸 1 段）；计划/研究组/可观测组-state.md（§10.1/§10.6/§16 T0-3 等）；计划/研究组/
RSI诱导演练-交付.md；计划/研究组/obs金丝雀-20261022.md §4.3（"未动"记录）。
patrol.log 历史轮次的 `=== checker=… sha256=aaae9e53…` 行是历史记录，不回改。
补齐一个旧缺口：L1 docstring 勘误当时"改动前原字节未另存"——本次按任务书要求留存了改前字节。

## 6. 边界与后续（未做/留归，如实登记）

1. **只改 obs-checker.py（纪律）**。`tools/obs-patrol.sh` 的分桶器仍按自己的 run_id 重名判据
   把相关流记 AMBIGUOUS，其提示文案"checker 按 run_id 取首行会误配"**已过期**——checker 侧
   rc 现已归零（撕裂 casualty 除外）。分桶器/文案更新（含"AMBIGUOUS 改信 checker rc"）
   归主代理裁决，未自行扩权。
2. **写侧 run_id 全局唯一化**（嵌 line/arm 或全局 attempt 计数，金丝雀 §6.3 建议的另一半）
   未做——属 af 分支改动，不在本单范围。
3. obs-smoke1/2 陈旧索引行与 manifest 按纪律保留原样（③组历史证据）。
4. canary 2905-a1 的 manifest 缺位未补（b2 进程被 kill 于 manifest 写盘前）——不伪造，
   checker 记 WARN（PASS 允许 warning）。
5. 本次修复只解决"读侧绑错行"；若未来出现同 (line,arm) 内 run_id 重复（写侧 -x2 避让机制
   失效），联合键仍可能命中多行——现行取首行且聚合取末行 sha，与旧行为一致，未加新判据
   （现状数据无此形态）。

## 7. 复跑命令（供复核）

```bash
CK=工具状态备份/observability/obs-checker.py
# ① 消歧 run 裸跑
python3 $CK 工具状态备份/observability/runs/canary-20261022/mavis-m31f/pydata__xarray-3151-a2/events.jsonl
python3 $CK 工具状态备份/observability/runs/canary-20261022/mavis-m31f/pydata__xarray-4094-a1/events.jsonl
# ③ 全量
for f in $(find 工具状态备份/observability/runs -name events.jsonl | sort); do python3 $CK "$f" >/dev/null 2>&1; echo "rc=$? $f"; done
# 期望：14×rc=0；唯一 rc=1 = runs/canary-20261022/mavis-m31f/pydata__xarray-3151-a1/events.jsonl（撕裂 casualty）
```
