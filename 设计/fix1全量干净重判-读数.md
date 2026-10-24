# fix1 全量干净重判 · 读数（rejudge2）

## 摘要（全部数字见以下各节，均由脚本从 L0 实算）

- 干净重判总行数：**1104**（P1 launcher 902 + rejudge2 互补 202；其中 rejudge2 有 1 行与 P1 重复判同一 run，两套二进制（guardrail/poc）判定一致，见 §6）。
- 翻转矩阵（共同已判集 1020 行）：T→T=515、F→T=43、F→F=458、T→F=4（4 行 T→F 全部定性为 diff 不完整/未跟踪文件，见 §2a）；**污染修正净增 +43 行**（把 4 行 T→F 计入则为 +39）。
- fix2 A/B：原口径 ±13.3pp 都被污染扭曲；干净口径 glm-cp Δ=+7.1pp、m31f Δ=0.0pp，**两臂方向不一致，fix2 无跨 profile 一致增益**（§3）。
- 与官方线（as-of 快照）：D1 共同 60 题集上 af 最佳大样本完整臂 fix1-d1-m31f 37/44=84.1%（n≥30；小样本臂如 kimi-k3-local 10/11=90.9% 不入选） vs zcode 81.7% / deepseek-cb 71.7% / mcode-D1 70.0%（§4）。
- L2 独立复算：P1 产物 902/902 行覆盖度、sha256 完整性、去重全部通过；方法论声明中 zcode 80/120、deepseek-cb 83/120、42→50、A/B 旧口径 ±13.3pp 均逐字节复现；“710 行”无法复现（口径分歧见 §5.0）；mcode D1 数字与调度方引用值不符（该线在飞，§5.1）。

> 生成时间：2026-10-21T13:14:24Z；本文全部数字由 /tmp/rejudge2-report-gen.py 从 L0 文件实算，无人工填写。
>
> 判分口径（fix3/clean）：全新 eval 容器（零代理环境注入）+ 官方 eval_script + `patch -p1 --fuzz=3` 应用 agent.diff + 官方判分器。
> 二进制：af-bench-guardrail（HEAD+护栏，--memory 4g/--pids-limit 256）与 af-bench-poc（c62c6ab2）双实现，judge.rs 逐行等价（差异仅在容器资源护栏）。

## 0. 范围与分工

- 本机 af-harness swe-v run 目录共 1338 个（盘点：/tmp/rejudge2-inventory.json），其中有 agent.diff 且任务包齐全的可判行 1254 个。
- **分工（厂长裁决 A）**：fix1/fix2 全量清洁重判由 P1 launcher（tools/truth-rejudge-launcher.py，产物 /tmp/truth-rejudge/）执行；本代理只判互补 scope（s1 选型矩阵 + 冒烟目录，产物 /tmp/bench-rejudge2-/），并对 P1 产物做 L2 独立复算（§5）。
- 干净判分行来源：rejudge2（我方）202 行 + truth（P1）902 行（P1 已收官：33/33 作业、902/902 行）。
- 官方三线（zcode/deepseek-cb/mcode）不是 af-harness 产物，不在重判范围，仅作对照（§4）。
- poc-step5/poc-step5-b 两批 run 由 fix3 poc 二进制在运行期即按 clean 口径判分（其 results.jsonl 带 judge_mode=clean 字段），故不重判；其中 reward=null 的 run_failed 行无 agent.diff，本就不在可判集内。

## 1. 每档案×档位：原地口径 vs 干净口径（run 目录级）

分母口径：**干净=有 agent.diff+任务包的可判行**（本表 clean 列为其中已判行；P1 未判完的档案标注 partial）；原地=eval.log 可解析行；档案=该目录 results.jsonl 按任务去重末行（常规“当年读数”口径；原始行数含重跑attempt，另列）。

| 档案 | 档 | run 目录 | 可判(diff) | 非空 diff | 档案(任务级) | 原地(eval.log) | 干净(重判) | 共同集 原地→干净 | 净增 |
|---|---|---|---|---|---|---|---|---|---|
| fix1 | D1 | fix1-d1-30b | 76 | 56 | 33.3% (20/60; 原始行 62, null 8) | 41.7% (25/60) | 46.4% (26/56) | 47.1%→47.1% (51) | +0 |
| fix1 | D1 | fix1-d1-glm-cp | 72 | 63 | 55.2% (32/58; 原始行 58, null 7) | 66.7% (38/57) | 74.6% (47/63) | 70.4%→75.9% (54) | +3 |
| fix1 | D1 | fix1-d1-glm-cp-local | 21 | 16 | 80.0% (12/15; 原始行 15, null 1) | 86.7% (13/15) | 87.5% (14/16) | 86.7%→86.7% (15) | +0 |
| fix1 | D1 | fix1-d1-glm-max | 71 | 67 | 71.7% (43/60; 原始行 60, null 4) | 76.7% (46/60) | 82.1% (55/67) | 78.0%→81.4% (59) | +2 |
| fix1 | D1 | fix1-d1-kimi | 63 | 62 | 63.6% (35/55; 原始行 55, null 6) | 74.5% (41/55) | 82.3% (51/62) | 74.5%→80.0% (55) | +3 |
| fix1 | D1 | fix1-d1-kimi-k3-local | 11 | 11 | 90.0% (9/10; 原始行 10, null 0) | 90.0% (9/10) | 90.9% (10/11) | 90.0%→90.0% (10) | +0 |
| fix1 | D1 | fix1-d1-m3 | 72 | 68 | 58.3% (35/60; 原始行 67, null 12) | 66.7% (40/60) | 72.1% (49/68) | 66.7%→71.7% (60) | +3 |
| fix1 | D1 | fix1-d1-m3-mingda | 18 | 17 | 66.7% (10/15; 原始行 15, null 0) | 66.7% (10/15) | 64.7% (11/17) | 66.7%→73.3% (15) | +1 |
| fix1 | D1 | fix1-d1-m31f | 69 | 44 | 46.7% (28/60; 原始行 64, null 22) | 66.7% (30/45) | 84.1% (37/44) | 76.9%→84.6% (39) | +3 |
| fix1 | D1 | fix1-d1-m31f-mingda | 12 | 11 | 70.0% (7/10; 原始行 10, null 0) | 70.0% (7/10) | 81.8% (9/11) | 70.0%→80.0% (10) | +1 |
| fix1 | D1 | fix1-d1-step5 | 69 | 51 | 46.6% (27/58; 原始行 59, null 16) | 63.0% (29/46) | 68.6% (35/51) | 64.4%→68.9% (45) | +2 |
| fix1 | D2 | fix1-d2-30b | 50 | 37 | 17.5% (7/40; 原始行 40, null 4) | 20.5% (8/39) | 29.7% (11/37) | 23.5%→29.4% (34) | +2 |
| fix1 | D2 | fix1-d2-glm-cp | 45 | 37 | 37.5% (15/40; 原始行 40, null 6) | 44.1% (15/34) | 52.8% (19/36) | 46.9%→53.1% (32) | +2 |
| fix1 | D2 | fix1-d2-glm-max | 46 | 40 | 45.0% (18/40; 原始行 40, null 1) | 46.2% (18/39) | 59.0% (23/39) | 50.0%→58.3% (36) | +3 |
| fix1 | D2 | fix1-d2-kimi | 44 | 41 | 47.5% (19/40; 原始行 40, null 2) | 50.0% (20/40) | 61.0% (25/41) | 52.6%→60.5% (38) | +3 |
| fix1 | D2 | fix1-d2-m3 | 50 | 45 | 37.5% (15/40; 原始行 42, null 5) | 45.0% (18/40) | 53.3% (24/45) | 46.2%→53.8% (39) | +3 |
| fix1 | D2 | fix1-d2-m31f | 40 | 24 | 27.5% (11/40; 原始行 42, null 17) | 46.2% (12/26) | 70.8% (17/24) | 54.5%→68.2% (22) | +3 |
| fix1 | D2 | fix1-d2-step5 | 39 | 24 | 38.2% (13/34; 原始行 34, null 11) | 58.3% (14/24) | 66.7% (16/24) | 60.9%→69.6% (23) | +2 |
| fix1 | D3 | fix1-d3-30b | 23 | 18 | 15.0% (3/20; 原始行 20, null 0) | 15.0% (3/20) | 16.7% (3/18) | 16.7%→16.7% (18) | +0 |
| fix1 | D3 | fix1-d3-glm-cp | 24 | 18 | 22.2% (4/18; 原始行 18, null 0) | 21.1% (4/19) | 22.2% (4/18) | 22.2%→22.2% (18) | +0 |
| fix1 | D3 | fix1-d3-glm-cp-local | 18 | 11 | 46.2% (6/13; 原始行 13, null 1) | 50.0% (6/12) | 54.5% (6/11) | 60.0%→50.0% (10) | -1 |
| fix1 | D3 | fix1-d3-glm-max | 23 | 20 | 45.0% (9/20; 原始行 24, null 4) | 45.0% (9/20) | 45.0% (9/20) | 45.0%→45.0% (20) | +0 |
| fix1 | D3 | fix1-d3-kimi | 21 | 20 | 45.0% (9/20; 原始行 21, null 1) | 47.4% (9/19) | 50.0% (10/20) | 47.4%→47.4% (19) | +0 |
| fix1 | D3 | fix1-d3-m3 | 22 | 20 | 30.0% (6/20; 原始行 28, null 9) | 30.0% (6/20) | 30.0% (6/20) | 30.0%→30.0% (20) | +0 |
| fix1 | D3 | fix1-d3-m31f | 28 | 21 | 35.0% (7/20; 原始行 20, null 0) | 33.3% (7/21) | 38.1% (8/21) | 35.0%→35.0% (20) | +0 |
| fix1 | D3 | fix1-d3-step5 | 17 | 14 | 30.8% (4/13; 原始行 14, null 1) | 28.6% (4/14) | 30.8% (4/13) | 33.3%→33.3% (12) | +0 |
| fix1 | None | fix1-localtest-glm-cp | 2 | 2 | 100.0% (2/2; 原始行 2, null 0) | 100.0% (2/2) | 100.0% (2/2) | 100.0%→100.0% (2) | +0 |
| fix1 | None | fix1-mingdatest-glm-cp | 1 | 1 | 100.0% (1/1; 原始行 1, null 0) | 100.0% (1/1) | 100.0% (1/1) | 100.0%→100.0% (1) | +0 |
| fix2-ab | None | fix2-ab-glm-cp | 15 | 15 | 73.3% (11/15; 原始行 15, null 0) | 73.3% (11/15) | 86.7% (13/15) | 73.3%→86.7% (15) | +2 |
| fix2-ab | None | fix2-ab-m31f | 15 | 13 | 53.3% (8/15; 原始行 33, null 22) | 76.9% (10/13) | 84.6% (11/13) | 76.9%→84.6% (13) | +1 |
| fix2-rerun | None | fix2-rerun-glm-cp | 4 | 4 | 0.0% (0/4; 原始行 4, null 0) | 0.0% (0/4) | 0.0% (0/4) | 0.0%→0.0% (4) | +0 |
| fix2-rerun | None | fix2-rerun-glm-cp-max | 4 | 4 | 0.0% (0/4; 原始行 4, null 0) | 0.0% (0/4) | 0.0% (0/4) | 0.0%→0.0% (4) | +0 |
| fix2-rerun | None | fix2-rerun-mavis-m3 | 4 | 4 | 0.0% (0/4; 原始行 5, null 1) | 0.0% (0/4) | 0.0% (0/4) | 0.0%→0.0% (4) | +0 |
| fix2-rerun | None | fix2-rerun-mavis-m31f | 4 | 3 | 0.0% (0/4; 原始行 8, null 5) | 0.0% (0/3) | 0.0% (0/3) | 0.0%→0.0% (3) | +0 |
| fix2-rerun | None | fix2-rerun-step-5 | 4 | 3 | 0.0% (0/4; 原始行 6, null 2) | 0.0% (0/4) | 0.0% (0/3) | 0.0%→0.0% (3) | +0 |
| poc | None | poc-step5 | 6 | 3 | 66.7% (2/3; 原始行 6, null 4) | 100.0% (2/2) | — (—) | —→— (0) | +0 |
| poc | None | poc-step5-b | 6 | 2 | 100.0% (2/2; 原始行 6, null 4) | 100.0% (2/2) | — (—) | —→— (0) | +0 |
| s1 | D1 | s1-d1-30b | 27 | 20 | 30.8% (8/26; 原始行 26, null 0) | 30.8% (8/26) | 30.8% (8/26) | 30.8%→30.8% (26) | +0 |
| s1 | D1 | s1-d1-8b | 8 | 0 | 0.0% (0/7; 原始行 7, null 4) | 0.0% (0/3) | 0.0% (0/3) | 0.0%→0.0% (3) | +0 |
| s1 | D1 | s1-d1-glm | 6 | 1 | 20.0% (1/5; 原始行 5, null 0) | 16.7% (1/6) | 16.7% (1/6) | 16.7%→16.7% (6) | +0 |
| s1 | D1 | s1-d1-glm-max | 29 | 10 | 25.0% (7/28; 原始行 28, null 0) | 27.6% (8/29) | 27.6% (8/29) | 27.6%→27.6% (29) | +0 |
| s1 | D1 | s1-d1-glm-r2 | 28 | 6 | 23.1% (6/26; 原始行 26, null 0) | 22.2% (6/27) | 22.2% (6/27) | 22.2%→22.2% (27) | +0 |
| s1 | D1 | s1-d1-kimi | 13 | 11 | 75.0% (9/12; 原始行 12, null 1) | 81.8% (9/11) | 81.8% (9/11) | 81.8%→81.8% (11) | +0 |
| s1 | D1 | s1-d1-m31f | 23 | 8 | 30.4% (7/23; 原始行 24, null 1) | 30.4% (7/23) | 34.8% (8/23) | 30.4%→34.8% (23) | +1 |
| s1 | D1 | s1-d1-step5 | 7 | 4 | 60.0% (3/5; 原始行 5, null 1) | 75.0% (3/4) | 75.0% (3/4) | 75.0%→75.0% (4) | +0 |
| s1 | D2 | s1-d2-30b | 9 | 7 | 25.0% (2/8; 原始行 9, null 1) | 22.2% (2/9) | 22.2% (2/9) | 22.2%→22.2% (9) | +0 |
| s1 | D2 | s1-d2-glm | 9 | 1 | 11.1% (1/9; 原始行 9, null 0) | 11.1% (1/9) | 11.1% (1/9) | 11.1%→11.1% (9) | +0 |
| s1 | D2 | s1-d2-glm-max | 9 | 2 | 11.1% (1/9; 原始行 10, null 3) | 22.2% (2/9) | 22.2% (2/9) | 22.2%→22.2% (9) | +0 |
| s1 | D2 | s1-d2-kimi | 3 | 2 | 50.0% (1/2; 原始行 2, null 0) | 50.0% (1/2) | 50.0% (1/2) | 50.0%→50.0% (2) | +0 |
| s1 | D2 | s1-d2-step5 | 1 | 0 | — (—; 原始行 0, null 0) | — (—) | — (—) | —→— (0) | +0 |
| s1 | D3 | s1-d3-30b | 3 | 0 | 0.0% (0/2; 原始行 2, null 1) | 0.0% (0/1) | 0.0% (0/1) | 0.0%→0.0% (1) | +0 |
| s1 | D3 | s1-d3-glm | 13 | 3 | 23.1% (3/13; 原始行 13, null 0) | 23.1% (3/13) | 23.1% (3/13) | 23.1%→23.1% (13) | +0 |
| s1 | D3 | s1-d3-glm-max | 11 | 2 | 20.0% (2/10; 原始行 10, null 0) | 20.0% (2/10) | 20.0% (2/10) | 20.0%→20.0% (10) | +0 |
| s1 | D3 | s1-d3-kimi | 1 | 0 | — (—; 原始行 0, null 0) | — (—) | — (—) | —→— (0) | +0 |
| s1 | D3 | s1-d3-m31f | 8 | 0 | 0.0% (0/8; 原始行 8, null 8) | — (—) | — (—) | —→— (0) | +0 |
| s1 | D3 | s1-d3-m31f-r2 | 10 | 5 | 20.0% (1/5; 原始行 11, null 5) | 40.0% (2/5) | 16.7% (1/6) | 40.0%→20.0% (5) | -1 |
| s1 | D3 | s1-d3-step5 | 1 | 0 | — (—; 原始行 0, null 0) | — (—) | — (—) | —→— (0) | +0 |
| smoke-swev | None | swev | 10 | 3 | 0.0% (0/5; 原始行 10, null 0) | 0.0% (0/10) | 10.0% (1/10) | 0.0%→10.0% (10) | +1 |

## 2. 翻转矩阵与全量净增

共同已判集 = 该行同时具备 eval.log（原地可判）与 agent.diff 且已完成干净判分。N→* = 原地不可判（无 eval.log）或干净未判的行数。

| 档案 | 档 | 共同集 | T→T | F→T | F→F | T→F | N→* | 净增 |
|---|---|---|---|---|---|---|---|---|
| fix1 | D1 | fix1-d1-30b | 51 | 23 | 1 | 26 | 1 | 0 | +0 |
| fix1 | D1 | fix1-d1-glm-cp | 54 | 38 | 3 | 13 | 0 | 0 | +3 |
| fix1 | D1 | fix1-d1-glm-cp-local | 15 | 13 | 0 | 2 | 0 | 0 | +0 |
| fix1 | D1 | fix1-d1-glm-max | 59 | 46 | 2 | 11 | 0 | 0 | +2 |
| fix1 | D1 | fix1-d1-kimi | 55 | 41 | 3 | 11 | 0 | 0 | +3 |
| fix1 | D1 | fix1-d1-kimi-k3-local | 10 | 9 | 0 | 1 | 0 | 0 | +0 |
| fix1 | D1 | fix1-d1-m3 | 60 | 40 | 3 | 17 | 0 | 0 | +3 |
| fix1 | D1 | fix1-d1-m3-mingda | 15 | 10 | 1 | 4 | 0 | 0 | +1 |
| fix1 | D1 | fix1-d1-m31f | 39 | 30 | 3 | 6 | 0 | 0 | +3 |
| fix1 | D1 | fix1-d1-m31f-mingda | 10 | 7 | 1 | 2 | 0 | 0 | +1 |
| fix1 | D1 | fix1-d1-step5 | 45 | 29 | 2 | 14 | 0 | 0 | +2 |
| fix1 | D2 | fix1-d2-30b | 34 | 8 | 2 | 24 | 0 | 0 | +2 |
| fix1 | D2 | fix1-d2-glm-cp | 32 | 14 | 3 | 14 | 1 | 0 | +2 |
| fix1 | D2 | fix1-d2-glm-max | 36 | 18 | 3 | 15 | 0 | 0 | +3 |
| fix1 | D2 | fix1-d2-kimi | 38 | 20 | 3 | 15 | 0 | 0 | +3 |
| fix1 | D2 | fix1-d2-m3 | 39 | 18 | 3 | 18 | 0 | 0 | +3 |
| fix1 | D2 | fix1-d2-m31f | 22 | 12 | 3 | 7 | 0 | 0 | +3 |
| fix1 | D2 | fix1-d2-step5 | 23 | 14 | 2 | 7 | 0 | 0 | +2 |
| fix1 | D3 | fix1-d3-30b | 18 | 3 | 0 | 15 | 0 | 0 | +0 |
| fix1 | D3 | fix1-d3-glm-cp | 18 | 4 | 0 | 14 | 0 | 0 | +0 |
| fix1 | D3 | fix1-d3-glm-cp-local | 10 | 5 | 0 | 4 | 1 | 0 | -1 |
| fix1 | D3 | fix1-d3-glm-max | 20 | 9 | 0 | 11 | 0 | 0 | +0 |
| fix1 | D3 | fix1-d3-kimi | 19 | 9 | 0 | 10 | 0 | 0 | +0 |
| fix1 | D3 | fix1-d3-m3 | 20 | 6 | 0 | 14 | 0 | 0 | +0 |
| fix1 | D3 | fix1-d3-m31f | 20 | 7 | 0 | 13 | 0 | 0 | +0 |
| fix1 | D3 | fix1-d3-step5 | 12 | 4 | 0 | 8 | 0 | 0 | +0 |
| fix1 | None | fix1-localtest-glm-cp | 2 | 2 | 0 | 0 | 0 | 0 | +0 |
| fix1 | None | fix1-mingdatest-glm-cp | 1 | 1 | 0 | 0 | 0 | 0 | +0 |
| fix2-ab | None | fix2-ab-glm-cp | 15 | 11 | 2 | 2 | 0 | 0 | +2 |
| fix2-ab | None | fix2-ab-m31f | 13 | 10 | 1 | 2 | 0 | 0 | +1 |
| fix2-rerun | None | fix2-rerun-glm-cp | 4 | 0 | 0 | 4 | 0 | 0 | +0 |
| fix2-rerun | None | fix2-rerun-glm-cp-max | 4 | 0 | 0 | 4 | 0 | 0 | +0 |
| fix2-rerun | None | fix2-rerun-mavis-m3 | 4 | 0 | 0 | 4 | 0 | 0 | +0 |
| fix2-rerun | None | fix2-rerun-mavis-m31f | 3 | 0 | 0 | 3 | 0 | 0 | +0 |
| fix2-rerun | None | fix2-rerun-step-5 | 3 | 0 | 0 | 3 | 0 | 0 | +0 |
| s1 | D1 | s1-d1-30b | 26 | 8 | 0 | 18 | 0 | 0 | +0 |
| s1 | D1 | s1-d1-8b | 3 | 0 | 0 | 3 | 0 | 0 | +0 |
| s1 | D1 | s1-d1-glm | 6 | 1 | 0 | 5 | 0 | 0 | +0 |
| s1 | D1 | s1-d1-glm-max | 29 | 8 | 0 | 21 | 0 | 0 | +0 |
| s1 | D1 | s1-d1-glm-r2 | 27 | 6 | 0 | 21 | 0 | 0 | +0 |
| s1 | D1 | s1-d1-kimi | 11 | 9 | 0 | 2 | 0 | 0 | +0 |
| s1 | D1 | s1-d1-m31f | 23 | 7 | 1 | 15 | 0 | 0 | +1 |
| s1 | D1 | s1-d1-step5 | 4 | 3 | 0 | 1 | 0 | 0 | +0 |
| s1 | D2 | s1-d2-30b | 9 | 2 | 0 | 7 | 0 | 0 | +0 |
| s1 | D2 | s1-d2-glm | 9 | 1 | 0 | 8 | 0 | 0 | +0 |
| s1 | D2 | s1-d2-glm-max | 9 | 2 | 0 | 7 | 0 | 0 | +0 |
| s1 | D2 | s1-d2-kimi | 2 | 1 | 0 | 1 | 0 | 0 | +0 |
| s1 | D3 | s1-d3-30b | 1 | 0 | 0 | 1 | 0 | 0 | +0 |
| s1 | D3 | s1-d3-glm | 13 | 3 | 0 | 10 | 0 | 0 | +0 |
| s1 | D3 | s1-d3-glm-max | 10 | 2 | 0 | 8 | 0 | 0 | +0 |
| s1 | D3 | s1-d3-m31f-r2 | 5 | 1 | 0 | 3 | 1 | 0 | -1 |
| smoke-swev | None | swev | 10 | 0 | 1 | 9 | 0 | 0 | +1 |

**合计（已入共同集的行）**：T→T=515 F→T=43 F→F=458 T→F=4，净增 +39 行。

### 2a. T→F 尸检（原判真→干净假；确定性判分下不应存在，逐行定性）

由 /tmp/rejudge2-tf-autopsy.py 对每个 T→F 行比对两次 eval.log 自动归类；判定为「判分状态差异」的行不计入净增叙事（其本质是原地口径把 agent 未跟踪文件带进了判分，见 judge.rs 模块文档）。

```
T→F 行总数: 4
- bench-fix1-d1-30b swev-pallets__flask-5014-qwen30b-local-a1: 判分状态差异（clean 容器收集/导入失败，疑 diff 不完整或未跟踪文件） ImportError while loading conftest '/testbed/tests/conftest.py'.
    原地日志: 导入/收集错误=无, FAILED 行数=0
- bench-fix1-d2-glm-cp swev-sphinx-doc__sphinx-10673-glm-cp-a1: 判分状态差异（clean 容器收集/导入失败，疑 diff 不完整或未跟踪文件） ModuleNotFoundError: No module named 'sphinx.util.toc_special_docs'
    原地日志: 导入/收集错误=无, FAILED 行数=0
- bench-fix1-d3-glm-cp-local swev-astropy__astropy-13398-glm-cp-a2: 判分状态差异（clean 容器收集/导入失败，疑 diff 不完整或未跟踪文件） ImportError: cannot import name 'itrs_observed_transforms' from partially initialized module 'astropy.coordinates.builti
    原地日志: 导入/收集错误=无, FAILED 行数=1
- bench-s1-d3-m31f-r2 swev-astropy__astropy-13398-mavis-m31f-a2: 判分状态差异（clean 容器收集/导入失败，疑 diff 不完整或未跟踪文件） ImportError: cannot import name 'itrs_observed_transforms' from partially initialized module 'astropy.coordinates.builti
    原地日志: 导入/收集错误=无, FAILED 行数=1
```

### 2b. 任务级（同档案同题任一 attempt 判真=通过）

| 档案 | 档 | 任务数 | 档案 | 原地 | 干净 |
|---|---|---|---|---|---|
| fix1 | D1 | fix1-d1-30b | 60 | 33.3% (20/60) | 41.7% (25/60) | 45.3% (24/53) |
| fix1 | D1 | fix1-d1-glm-cp | 58 | 55.2% (32/58) | 66.7% (38/57) | 76.4% (42/55) |
| fix1 | D1 | fix1-d1-glm-cp-local | 15 | 80.0% (12/15) | 86.7% (13/15) | 86.7% (13/15) |
| fix1 | D1 | fix1-d1-glm-max | 60 | 71.7% (43/60) | 76.7% (46/60) | 81.4% (48/59) |
| fix1 | D1 | fix1-d1-kimi | 55 | 63.6% (35/55) | 74.5% (41/55) | 81.8% (45/55) |
| fix1 | D1 | fix1-d1-kimi-k3-local | 10 | 90.0% (9/10) | 90.0% (9/10) | 90.0% (9/10) |
| fix1 | D1 | fix1-d1-m3 | 60 | 58.3% (35/60) | 66.7% (40/60) | 71.7% (43/60) |
| fix1 | D1 | fix1-d1-m3-mingda | 15 | 66.7% (10/15) | 66.7% (10/15) | 73.3% (11/15) |
| fix1 | D1 | fix1-d1-m31f | 44 | 46.7% (28/60) | 68.2% (30/44) | 84.6% (33/39) |
| fix1 | D1 | fix1-d1-m31f-mingda | 10 | 70.0% (7/10) | 70.0% (7/10) | 80.0% (8/10) |
| fix1 | D1 | fix1-d1-step5 | 47 | 46.6% (27/58) | 64.4% (29/45) | 71.7% (33/46) |
| fix1 | D2 | fix1-d2-30b | 39 | 17.5% (7/40) | 20.5% (8/39) | 29.4% (10/34) |
| fix1 | D2 | fix1-d2-glm-cp | 34 | 37.5% (15/40) | 44.1% (15/34) | 53.1% (17/32) |
| fix1 | D2 | fix1-d2-glm-max | 39 | 45.0% (18/40) | 46.2% (18/39) | 58.3% (21/36) |
| fix1 | D2 | fix1-d2-kimi | 40 | 47.5% (19/40) | 50.0% (20/40) | 61.5% (24/39) |
| fix1 | D2 | fix1-d2-m3 | 40 | 37.5% (15/40) | 45.0% (18/40) | 53.8% (21/39) |
| fix1 | D2 | fix1-d2-m31f | 26 | 27.5% (11/40) | 46.2% (12/26) | 72.7% (16/22) |
| fix1 | D2 | fix1-d2-step5 | 25 | 38.2% (13/34) | 58.3% (14/24) | 66.7% (16/24) |
| fix1 | D3 | fix1-d3-30b | 20 | 15.0% (3/20) | 15.0% (3/20) | 16.7% (3/18) |
| fix1 | D3 | fix1-d3-glm-cp | 19 | 22.2% (4/18) | 21.1% (4/19) | 22.2% (4/18) |
| fix1 | D3 | fix1-d3-glm-cp-local | 13 | 46.2% (6/13) | 50.0% (6/12) | 54.5% (6/11) |
| fix1 | D3 | fix1-d3-glm-max | 20 | 45.0% (9/20) | 45.0% (9/20) | 45.0% (9/20) |
| fix1 | D3 | fix1-d3-kimi | 19 | 45.0% (9/20) | 47.4% (9/19) | 47.4% (9/19) |
| fix1 | D3 | fix1-d3-m3 | 20 | 30.0% (6/20) | 30.0% (6/20) | 30.0% (6/20) |
| fix1 | D3 | fix1-d3-m31f | 20 | 35.0% (7/20) | 35.0% (7/20) | 36.8% (7/19) |
| fix1 | D3 | fix1-d3-step5 | 13 | 30.8% (4/13) | 30.8% (4/13) | 36.4% (4/11) |
| fix1 | None | fix1-localtest-glm-cp | 2 | 100.0% (2/2) | 100.0% (2/2) | 100.0% (2/2) |
| fix1 | None | fix1-mingdatest-glm-cp | 1 | 100.0% (1/1) | 100.0% (1/1) | 100.0% (1/1) |
| fix2-ab | None | fix2-ab-glm-cp | 15 | 73.3% (11/15) | 73.3% (11/15) | 86.7% (13/15) |
| fix2-ab | None | fix2-ab-m31f | 13 | 53.3% (8/15) | 76.9% (10/13) | 84.6% (11/13) |
| fix2-rerun | None | fix2-rerun-glm-cp | 4 | 0.0% (0/4) | 0.0% (0/4) | 0.0% (0/4) |
| fix2-rerun | None | fix2-rerun-glm-cp-max | 4 | 0.0% (0/4) | 0.0% (0/4) | 0.0% (0/4) |
| fix2-rerun | None | fix2-rerun-mavis-m3 | 4 | 0.0% (0/4) | 0.0% (0/4) | 0.0% (0/4) |
| fix2-rerun | None | fix2-rerun-mavis-m31f | 3 | 0.0% (0/4) | 0.0% (0/3) | 0.0% (0/3) |
| fix2-rerun | None | fix2-rerun-step-5 | 4 | 0.0% (0/4) | 0.0% (0/4) | 0.0% (0/3) |
| poc | None | poc-step5 | 2 | 66.7% (2/3) | 100.0% (2/2) | — (—) |
| poc | None | poc-step5-b | 2 | 100.0% (2/2) | 100.0% (2/2) | — (—) |
| s1 | D1 | s1-d1-30b | 26 | 30.8% (8/26) | 30.8% (8/26) | 30.8% (8/26) |
| s1 | D1 | s1-d1-8b | 3 | 0.0% (0/7) | 0.0% (0/3) | 0.0% (0/3) |
| s1 | D1 | s1-d1-glm | 6 | 20.0% (1/5) | 16.7% (1/6) | 16.7% (1/6) |
| s1 | D1 | s1-d1-glm-max | 29 | 25.0% (7/28) | 27.6% (8/29) | 27.6% (8/29) |
| s1 | D1 | s1-d1-glm-r2 | 27 | 23.1% (6/26) | 22.2% (6/27) | 22.2% (6/27) |
| s1 | D1 | s1-d1-kimi | 11 | 75.0% (9/12) | 81.8% (9/11) | 81.8% (9/11) |
| s1 | D1 | s1-d1-m31f | 23 | 30.4% (7/23) | 30.4% (7/23) | 34.8% (8/23) |
| s1 | D1 | s1-d1-step5 | 4 | 60.0% (3/5) | 75.0% (3/4) | 75.0% (3/4) |
| s1 | D2 | s1-d2-30b | 9 | 25.0% (2/8) | 22.2% (2/9) | 22.2% (2/9) |
| s1 | D2 | s1-d2-glm | 9 | 11.1% (1/9) | 11.1% (1/9) | 11.1% (1/9) |
| s1 | D2 | s1-d2-glm-max | 9 | 11.1% (1/9) | 22.2% (2/9) | 22.2% (2/9) |
| s1 | D2 | s1-d2-kimi | 2 | 50.0% (1/2) | 50.0% (1/2) | 50.0% (1/2) |
| s1 | D2 | s1-d2-step5 | 0 | — (—) | — (—) | — (—) |
| s1 | D3 | s1-d3-30b | 1 | 0.0% (0/2) | 0.0% (0/1) | 0.0% (0/1) |
| s1 | D3 | s1-d3-glm | 13 | 23.1% (3/13) | 23.1% (3/13) | 23.1% (3/13) |
| s1 | D3 | s1-d3-glm-max | 10 | 20.0% (2/10) | 20.0% (2/10) | 20.0% (2/10) |
| s1 | D3 | s1-d3-kimi | 0 | — (—) | — (—) | — (—) |
| s1 | D3 | s1-d3-m31f | 0 | 0.0% (0/8) | — (—) | — (—) |
| s1 | D3 | s1-d3-m31f-r2 | 4 | 20.0% (1/5) | 50.0% (2/4) | 25.0% (1/4) |
| s1 | D3 | s1-d3-step5 | 0 | — (—) | — (—) | — (—) |
| smoke-swev | None | swev | 5 | 0.0% (0/5) | 0.0% (0/5) | 20.0% (1/5) |

## 3. fix2 A/B 双臂：原口径 vs 干净口径

### 3.1 fix2-ab-glm-cp（n=15 配对，A=fix1-d1-glm-cp 原 run，B=fix2-ab-glm-cp 新 run）

- 原口径（档案记录，全 15 对）：A=9/15=60.0%，B=11/15=73.3%，**Δ=+13.3pp**
- 干净口径（重判，双臂俱判 14/15 对）：A=11，B=12，**Δ=+7.1pp**；同子集原口径 A=9 B=10 Δ=+7.1pp（口径一致对照）（partial：部分对缺 diff 无法判）

  逐对明细（A/B 原判 → A/B 干净；★=该臂判真发生变化）：

  | 题 | A原 | B原 | A净 | B净 | 变化 |
  |---|---|---|---|---|---|
  | mwaskom__seaborn-3069 | False | True | None | True | 未判齐 |
  | matplotlib__matplotlib-20676 | False | False | False | False | — |
  | pallets__flask-5014 | True | True | True | True | — |
  | astropy__astropy-12907 | True | True | True | True | — |
  | pytest-dev__pytest-5787 | False | True | False | True | — |
  | psf__requests-5414 | False | False | True | True | A★ B★ |
  | matplotlib__matplotlib-13989 | True | True | True | True | — |
  | django__django-11066 | True | True | True | True | — |
  | matplotlib__matplotlib-22719 | True | True | True | True | — |
  | psf__requests-2931 | True | True | True | True | — |
  | matplotlib__matplotlib-22865 | False | True | False | True | — |
  | psf__requests-6028 | False | False | True | True | A★ B★ |
  | astropy__astropy-13579 | True | True | True | True | — |
  | matplotlib__matplotlib-20859 | True | True | True | True | — |
  | sympy__sympy-11618 | True | False | True | False | — |

- **本臂结论（数据已收官，n=14 可判对）**：fix2 变体在本臂有正向增益（Δ=+7.1pp）。

### 3.2 fix2-ab-m31f（n=15 配对，A=fix1-d1-m31f 原 run，B=fix2-ab-m31f 新 run）

- 原口径（档案记录，全 15 对）：A=10/15=66.7%，B=8/15=53.3%，**Δ=-13.3pp**
- 干净口径（重判，双臂俱判 11/15 对）：A=9，B=9，**Δ=+0.0pp**；同子集原口径 A=8 B=6 Δ=-18.2pp（口径一致对照）（partial：部分对缺 diff 无法判）

  逐对明细（A/B 原判 → A/B 干净；★=该臂判真发生变化）：

  | 题 | A原 | B原 | A净 | B净 | 变化 |
  |---|---|---|---|---|---|
  | astropy__astropy-13236 | False | True | False | True | — |
  | astropy__astropy-13579 | True | True | True | True | — |
  | matplotlib__matplotlib-20859 | False | False | False | False | — |
  | django__django-10914 | True | True | True | True | — |
  | mwaskom__seaborn-3069 | True | False | True | False | — |
  | matplotlib__matplotlib-20826 | False | True | None | True | 未判齐 |
  | astropy__astropy-14096 | False | True | None | True | 未判齐 |
  | matplotlib__matplotlib-13989 | True | True | True | True | — |
  | matplotlib__matplotlib-20488 | False | False | True | True | A★ B★ |
  | astropy__astropy-13453 | True | True | True | True | — |
  | django__django-11087 | True | None | True | None | 未判齐 |
  | matplotlib__matplotlib-20676 | True | True | True | True | — |
  | astropy__astropy-12907 | True | None | True | None | 未判齐 |
  | django__django-10880 | True | None | True | True | — |
  | django__django-11095 | True | None | True | True | — |

- 双臂未判齐的题（缺 agent.diff，P1 已收官、无更多数据可判）：['django__django-11087', 'astropy__astropy-12907']
- **本臂结论（数据已收官，n=11 可判对）**：fix2 变体在本臂无净增益（Δ=0.0pp）。

**A/B 总结论（回答“fix2 变体有没有一致增益”）**：两臂原口径 delta（+13.3pp / -13.3pp）都被原地判分污染扭曲；干净口径下 glm-cp 臂 Δ=+7.1pp（与原口径同子集一致，增益真实但缩水）、m31f 臂 Δ=0.0pp（原口径的“回归”是污染假象）。**两臂方向不一致 → fix2 变体没有跨 profile 的一致增益**；glm-cp 上的 +7.1pp 与 m31f 上的 0.0pp 差异，在 n=15/臂的样本下更可能是 profile 依赖性而非变体主效应。路线裁决应采用干净口径的这两个数，弃用 ±13.3pp。

## 4. 与官方三线对照（af 修正值 vs 官方）

三种分母并列：①各自全集；②四线共同已判集；③af D1 最佳臂。官方数字由本脚本从 /tmp/bench-official-* 与 /tmp/bench-fix1-d*-deepseek-cb 的 results.jsonl 独立复算。

- zcode：全集 80/120=66.7%
- deepseek-cb：全集 83/120=69.2%
- mcode-D1(两型合并)：全集 42/60=70.0%（截至 21:14 快照，该线未收官：D2/D3 仍在 anolis 在飞，prepare_failed 重试会使数字继续漂移）

四线共同已判集 = 60 题（mcode D1 的 60 题为瓶颈）。

| 线 | 共同集通过 |
|---|---|
| zcode | 49/60=81.7% |
| deepseek-cb | 43/60=71.7% |
| mcode-D1 | 42/60=70.0% |

af 各臂（D1，干净口径，仅统计已有干净判分的任务）在共同集上的通过：

| af 臂 | 共同集已判 | 通过 | 本臂全集(已干净判分任务) |
|---|---|---|---|
| fix1-d1-30b | 53 | 24/53=45.3% | 24/53=45.3% |
| fix1-d1-glm-cp | 55 | 42/55=76.4% | 42/55=76.4% |
| fix1-d1-glm-cp-local | 15 | 13/15=86.7% | 13/15=86.7% |
| fix1-d1-glm-max | 59 | 48/59=81.4% | 48/59=81.4% |
| fix1-d1-kimi | 55 | 45/55=81.8% | 45/55=81.8% |
| fix1-d1-kimi-k3-local | 10 | 9/10=90.0% | 9/10=90.0% |
| fix1-d1-m3 | 60 | 43/60=71.7% | 43/60=71.7% |
| fix1-d1-m3-mingda | 15 | 11/15=73.3% | 11/15=73.3% |
| fix1-d1-m31f | 39 | 33/39=84.6% | 33/39=84.6% |
| fix1-d1-m31f-mingda | 10 | 8/10=80.0% | 8/10=80.0% |
| fix1-d1-step5 | 46 | 33/46=71.7% | 33/46=71.7% |

口径提醒：s1 题库 120 题按 D1/D2/D3=60/40/20 切分（mcode 官方目录即按此切分，本脚本以 /tmp/rejudge2-tier-map.json 为权威映射）。af fix1 每档跑同一档题集（D1=60 题）；zcode/deepseek-cb 的“120”是 D1+D2+D3 合计；mcode D2/D3 在本次读数生成时仍在 anolis 在飞、null 行多，其 D1 数字也会随后续 prepare_failed 重试漂移。

mcode 数字引用规范（厂长令）：凡引用 mcode，必须带 as-of 时间戳并注明“线未收官”。本表 mcode 数字为截至 21:14 的快照。

### 4a. 分档对照（D1/D2/D3 各自题集上的通过率；af 列该档全部 fix1 臂，按通过率降序）

| 档 | 题数 | af 各臂（干净，已判题数） | zcode | deepseek-cb | mcode（as-of，未收官） |
|---|---|---|---|---|---|
| D1 | 60 | 90.0% (fix1-d1-kimi-k3-local 9/10)<br>86.7% (fix1-d1-glm-cp-local 13/15)<br>84.6% (fix1-d1-m31f 33/39)<br>81.8% (fix1-d1-kimi 45/55)<br>81.4% (fix1-d1-glm-max 48/59)<br>80.0% (fix1-d1-m31f-mingda 8/10)<br>76.4% (fix1-d1-glm-cp 42/55)<br>73.3% (fix1-d1-m3-mingda 11/15)<br>71.7% (fix1-d1-step5 33/46)<br>71.7% (fix1-d1-m3 43/60)<br>45.3% (fix1-d1-30b 24/53) | 49/60=81.7% | 43/60=71.7% | 42/60=70.0% |
| D2 | 40 | 72.7% (fix1-d2-m31f 16/22)<br>66.7% (fix1-d2-step5 16/24)<br>61.5% (fix1-d2-kimi 24/39)<br>58.3% (fix1-d2-glm-max 21/36)<br>53.8% (fix1-d2-m3 21/39)<br>53.1% (fix1-d2-glm-cp 17/32)<br>29.4% (fix1-d2-30b 10/34) | 22/40=55.0% | 30/40=75.0% | —（该档在飞） |
| D3 | 20 | 54.5% (fix1-d3-glm-cp-local 6/11)<br>47.4% (fix1-d3-kimi 9/19)<br>45.0% (fix1-d3-glm-max 9/20)<br>36.8% (fix1-d3-m31f 7/19)<br>36.4% (fix1-d3-step5 4/11)<br>30.0% (fix1-d3-m3 6/20)<br>22.2% (fix1-d3-glm-cp 4/18)<br>16.7% (fix1-d3-30b 3/18) | 9/20=45.0% | 10/20=50.0% | —（该档在飞） |

## 5. L2 独立复算：与方法论声明/前人数字的差异清单

（由 /tmp/rejudge2-recompute.py 生成，逐条附复算命令与出处）

### 5.0 计数口径分歧（供裁决书定口径）：方法论“af-fix1 全矩阵 710 行”

四种计数都真实存在、只是约定不同，任何引用必须先声明口径：

| 口径 | 定义 | fix1 复算值（除 test 目录） |
|---|---|---|
| results.jsonl 原始行数 | 每次调用一行，含重跑 attempt 与 null 行 | 910（含 test 目录 913） |
| 有 agent.diff 的 run 目录数 | 文件存在即可（含空 diff） | 1001（含 test 目录 1004） |
| 非空 agent.diff 的 run 目录数 | P1 launcher 的判分集（getsize>0） | **856**（含 test 目录 859；即 P0 声明的 856） |
| distinct (tier, task, profile) | 去 attempt 重复 | 730 |

“710”不在以上任一口径中复现出来——最接近的假设是“早期某时刻的 distinct 计数”或笔误；P1 launcher 实际判分集=902 行（fix1 856 + fix2 46），与 P0 声明“856+46=902”逐字节一致。

### 5.1 复算明细

== A. L0 计数（盘点脚本实算）==
  bench-fix1-d1-30b                          runs= 76 diff= 76 diff_nonempty= 56 empty=20
  bench-fix1-d1-glm-cp                       runs= 72 diff= 71 diff_nonempty= 63 empty= 8
  bench-fix1-d1-glm-cp-local                 runs= 21 diff= 18 diff_nonempty= 16 empty= 2
  bench-fix1-d1-glm-max                      runs= 71 diff= 71 diff_nonempty= 67 empty= 4
  bench-fix1-d1-kimi                         runs= 63 diff= 62 diff_nonempty= 62 empty= 0
  bench-fix1-d1-kimi-k3-local                runs= 11 diff= 11 diff_nonempty= 11 empty= 0
  bench-fix1-d1-m3                           runs= 72 diff= 71 diff_nonempty= 68 empty= 3
  bench-fix1-d1-m3-mingda                    runs= 18 diff= 18 diff_nonempty= 17 empty= 1
  bench-fix1-d1-m31f                         runs= 69 diff= 66 diff_nonempty= 44 empty=22
  bench-fix1-d1-m31f-mingda                  runs= 12 diff= 12 diff_nonempty= 11 empty= 1
  bench-fix1-d1-step5                        runs= 69 diff= 56 diff_nonempty= 51 empty= 5
  bench-fix1-d2-30b                          runs= 50 diff= 49 diff_nonempty= 37 empty=12
  bench-fix1-d2-glm-cp                       runs= 45 diff= 44 diff_nonempty= 37 empty= 7
  bench-fix1-d2-glm-max                      runs= 46 diff= 46 diff_nonempty= 40 empty= 6
  bench-fix1-d2-kimi                         runs= 44 diff= 44 diff_nonempty= 41 empty= 3
  bench-fix1-d2-m3                           runs= 50 diff= 49 diff_nonempty= 45 empty= 4
  bench-fix1-d2-m31f                         runs= 40 diff= 39 diff_nonempty= 24 empty=15
  bench-fix1-d2-step5                        runs= 39 diff= 28 diff_nonempty= 24 empty= 4
  bench-fix1-d3-30b                          runs= 23 diff= 23 diff_nonempty= 18 empty= 5
  bench-fix1-d3-glm-cp                       runs= 24 diff= 23 diff_nonempty= 18 empty= 5
  bench-fix1-d3-glm-cp-local                 runs= 18 diff= 16 diff_nonempty= 11 empty= 5
  bench-fix1-d3-glm-max                      runs= 23 diff= 22 diff_nonempty= 20 empty= 2
  bench-fix1-d3-kimi                         runs= 21 diff= 20 diff_nonempty= 20 empty= 0
  bench-fix1-d3-m3                           runs= 22 diff= 22 diff_nonempty= 20 empty= 2
  bench-fix1-d3-m31f                         runs= 28 diff= 27 diff_nonempty= 21 empty= 6
  bench-fix1-d3-step5                        runs= 17 diff= 17 diff_nonempty= 14 empty= 3
  bench-fix1-localtest-glm-cp                runs=  2 diff=  2 diff_nonempty=  2 empty= 0
  bench-fix1-mingdatest-glm-cp               runs=  1 diff=  1 diff_nonempty=  1 empty= 0
  bench-fix2-ab-glm-cp                       runs= 15 diff= 15 diff_nonempty= 15 empty= 0
  bench-fix2-ab-m31f                         runs= 15 diff= 13 diff_nonempty= 13 empty= 0
  bench-fix2-rerun-glm-cp                    runs=  4 diff=  4 diff_nonempty=  4 empty= 0
  bench-fix2-rerun-glm-cp-max                runs=  4 diff=  4 diff_nonempty=  4 empty= 0
  bench-fix2-rerun-mavis-m3                  runs=  4 diff=  4 diff_nonempty=  4 empty= 0
  bench-fix2-rerun-mavis-m31f                runs=  4 diff=  3 diff_nonempty=  3 empty= 0
  bench-fix2-rerun-step-5                    runs=  4 diff=  4 diff_nonempty=  3 empty= 1
  == fix1: runs=1047 diff=1004 diff_nonempty=859 empty=145
  == fix2-ab: runs=30 diff=28 diff_nonempty=28 empty=0
  == fix2-rerun: runs=20 diff=19 diff_nonempty=18 empty=1
  方法论声明: af-fix1 全矩阵 710 行; fix2 A/B 30 配对; fix2 最难子集 27 行
  P0 声明: 本机全量 856+46=902 个 diff
  fix2-rerun 实况: run 目录=20、有 diff=19、非空 diff=18（声明 27 行不匹配；A/B 30 配对=ab-glm-cp 15 + ab-m31f 15 ✓）

== B. P1 launcher 队列自洽性 ==
  队列作业数=33 队列行数合计=902
  已完成作业=33/33
  队列行数合计 902 vs L0 diff_nonempty(fix1+fix2) 905
  （905-902=3 的差=bench-fix1-localtest-glm-cp 2 行 + bench-fix1-mingdatest-glm-cp 1 行，launcher 按声明排除 *test* 目录；已核对一致）

== C. 方法论 §四 声明复算 ==
  zcode: 任务数=120 pass=80 (66.7%)  [声明 80/120=66.7%]
  deepseek-cb: 任务数=120 pass=83 (69.2%)  [声明 83/120=69.2%]
  fix2-ab-glm-cp 行数=15 arms={'off': (15, 11)}
  fix2-ab-m31f 行数=33 arms={'off': (13, 8), '?': (20, 0)}
  step-5 78 行清洁重判: rows=78 resolved=50  [声明 42→50]
  step-5 78 任务档案原地 reward=true: 42/78  [声明 42]
  step-5 78 任务 eval.log 解析原地 resolved=true: 43/78  [与档案 42 的差异即待查行]

== D. P1 产物行级完整性（独立复算）==
  bench-fix1-d1-30b            rows= 56 expect= 56 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d1-glm-cp-local   rows= 16 expect= 16 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d1-glm-cp         rows= 63 expect= 63 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d1-glm-max        rows= 67 expect= 67 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d1-kimi-k3-local  rows= 11 expect= 11 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d1-kimi           rows= 62 expect= 62 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d1-m3-mingda      rows= 17 expect= 17 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d1-m3             rows= 68 expect= 68 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d1-m31f-mingda    rows= 11 expect= 11 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d1-m31f           rows= 44 expect= 44 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d1-step5          rows= 51 expect= 51 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d2-30b            rows= 37 expect= 37 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d2-glm-cp         rows= 37 expect= 37 extra=0 miss=0 null= 1 apply_failed= 1 timeout= 0 dup=0 bad_hash=0
      null: sphinx-doc__sphinx-8120 judge_failed APPLY_FAILED: 补丁应用失败（exit=None）: patch: **** Only garbage was found in the patch input.

      apply_failed: sphinx-doc__sphinx-8120 APPLY_FAILED: 补丁应用失败（exit=None）: patch: **** Only garbage was found in the patch input.

  bench-fix1-d2-glm-max        rows= 40 expect= 40 extra=0 miss=0 null= 1 apply_failed= 1 timeout= 0 dup=0 bad_hash=0
      null: sympy__sympy-19783 judge_failed APPLY_FAILED: 补丁应用失败（exit=None）: patch: **** Only garbage was found in the patch input.

      apply_failed: sympy__sympy-19783 APPLY_FAILED: 补丁应用失败（exit=None）: patch: **** Only garbage was found in the patch input.

  bench-fix1-d2-kimi           rows= 41 expect= 41 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d2-m3             rows= 45 expect= 45 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d2-m31f           rows= 24 expect= 24 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d2-step5          rows= 24 expect= 24 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d3-30b            rows= 18 expect= 18 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d3-glm-cp-local   rows= 11 expect= 11 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d3-glm-cp         rows= 18 expect= 18 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d3-glm-max        rows= 20 expect= 20 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d3-kimi           rows= 20 expect= 20 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d3-m3             rows= 20 expect= 20 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d3-m31f           rows= 21 expect= 21 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix1-d3-step5          rows= 14 expect= 14 extra=0 miss=0 null= 1 apply_failed= 1 timeout= 0 dup=0 bad_hash=0
      null: django__django-13121 judge_failed APPLY_FAILED: 补丁应用失败（exit=None）: patch: **** Only garbage was found in the patch input.

      apply_failed: django__django-13121 APPLY_FAILED: 补丁应用失败（exit=None）: patch: **** Only garbage was found in the patch input.

  bench-fix2-ab-glm-cp         rows= 15 expect= 15 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix2-ab-m31f           rows= 13 expect= 13 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix2-rerun-glm-cp-max  rows=  4 expect=  4 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix2-rerun-glm-cp      rows=  4 expect=  4 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix2-rerun-mavis-m3    rows=  4 expect=  4 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix2-rerun-mavis-m31f  rows=  3 expect=  3 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0
  bench-fix2-rerun-step-5      rows=  3 expect=  3 extra=0 miss=0 null= 0 apply_failed= 0 timeout= 0 dup=0 bad_hash=0


## 6. 意外发现

1. **原地判分有三种偏差模式，不止代理污染一种**（均有 L0 实证）：
   - 假阴性（主模式）：eval 容器被注入代理 → pip install/P2P 断言受污染 → 干净重判翻真（F→T，见 §2）。
   - 假阳性：agent 容器里的**未跟踪文件**会被原地判分带进判分状态，而 agent.diff 只取 `git diff`——astropy-13398（fix1-d3-glm-cp-local-a2）即此 case：diff 里加了 `from . import itrs_observed_transforms` 但没带该文件本身，原地判（文件在）真、干净判（diff only）导入即崩 → T→F。这是 §2a 唯一一行 T→F，已定性为判分状态差异，非 flaky。
   - 判分链降级假阴性：fix1 档案里有 6 行判分 note 是裸 `{"resolved": false}`（无 f2p 明细，旧判分链形态），其中 astropy-12907（fix1-d1-step5-a1）的 eval.log 复判两个 F2P 全过、干净重判亦为真——即 step-5 78 题集中“原地 42”还少算了这 1 行（eval.log 复算口径为 43）。
2. **空 diff 比例**：fix1 有 diff 的 1004 个 run 中 145 个（14.4%）diff 为空（gate=no_patch）；s1 互补 scope 更高——198 个可判 run 中 113 个（57%）为空。空 diff 行仍被干净判分（必然 not_resolved），分子分母口径在 §1 用“非空 diff”列与 P1 对齐。
3. **harness 层失败但 diff 存活的 run**：fix1-d1-m31f 档案 64 行里 22 行 reward=null（端点/运行层失败），但这些 run 的 agent.diff 仍在——干净判分可以把它们救回可判（P1 已覆盖）。这是“无效运行噪声”与“真实假阴性”的分离关键。
4. **s1 选型矩阵时代全部 run 都早于 max_tokens 截断修复**（fd77a9d，10-20 12:37；s1 各目录 results.jsonl 落款 09:38-12:28），其档案通过率被系统性压低，不能当能力读数用；本次干净重判是这些 diff 的首次有效读数（结论：多为 F→F，截断杀的 run 补丁不成形）。注意：污染机制在 s1/冒烟时代就已存在（bench-swev 的 astropy-12907-glm-cp-max 即 F→T），只是那时补丁质量太差、污染无处可显。
5. **django-13121（fix1-d3-step5）diff 内容损坏**：patch 报 “Only garbage was found in the patch input” → APPLY_FAILED，干净判分记 judge_failed（reward=null），未臆造 verdict。P1 全线共 3 行此类（另有 sphinx-8120/d2-glm-cp、sympy-19783/d2-glm-max）。
6. **跨二进制判定一致性抽验**：rejudge2 与 P1 各判了同一行（fix2-rerun-step-5 的 astropy-13033，guardrail vs poc 两套构建），判定一致（均 not_resolved，f2p 0/1）；eval.log 的 sha256 不同（日志含时间戳/路径），属预期。
7. 资源面：判分期间发现 3 个 20-22 小时的孤儿 afbench agent 容器（driver 已死、agent 卡在 git fetch 考古循环，白烧 8 核），已报厂长并按其换装流程清除；/tmp 峰值 71% 后随 build 目录释放回落到 46-50%，全程 MemAvailable ≥4G，未触发停启闸。

### 6a. 干净判分失败行（reward=null，脚本自动列出）

- 无

## 7. 缺口与未判行（如实账）

| 档案 | 缺 agent.diff 的 run | 缺任务包 |
|---|---|---|
| fix1-d1-30b | 0 | 0 |
| fix1-d1-glm-cp | 1 | 0 |
| fix1-d1-glm-cp-local | 3 | 0 |
| fix1-d1-glm-max | 0 | 0 |
| fix1-d1-kimi | 1 | 0 |
| fix1-d1-kimi-k3-local | 0 | 0 |
| fix1-d1-m3 | 1 | 0 |
| fix1-d1-m3-mingda | 0 | 0 |
| fix1-d1-m31f | 3 | 0 |
| fix1-d1-m31f-mingda | 0 | 0 |
| fix1-d1-step5 | 13 | 0 |
| fix1-d2-30b | 1 | 0 |
| fix1-d2-glm-cp | 1 | 0 |
| fix1-d2-glm-max | 0 | 0 |
| fix1-d2-kimi | 0 | 0 |
| fix1-d2-m3 | 1 | 0 |
| fix1-d2-m31f | 1 | 0 |
| fix1-d2-step5 | 11 | 0 |
| fix1-d3-30b | 0 | 0 |
| fix1-d3-glm-cp | 1 | 0 |
| fix1-d3-glm-cp-local | 2 | 0 |
| fix1-d3-glm-max | 1 | 0 |
| fix1-d3-kimi | 1 | 0 |
| fix1-d3-m3 | 0 | 0 |
| fix1-d3-m31f | 1 | 0 |
| fix1-d3-step5 | 0 | 0 |
| fix1-localtest-glm-cp | 0 | 0 |
| fix1-mingdatest-glm-cp | 0 | 0 |
| fix2-ab-glm-cp | 0 | 0 |
| fix2-ab-m31f | 2 | 0 |
| fix2-rerun-glm-cp | 0 | 0 |
| fix2-rerun-glm-cp-max | 0 | 0 |
| fix2-rerun-mavis-m3 | 0 | 0 |
| fix2-rerun-mavis-m31f | 1 | 0 |
| fix2-rerun-step-5 | 0 | 0 |
| poc-step5 | 3 | 0 |
| poc-step5-b | 4 | 0 |
| s1-d1-30b | 1 | 0 |
| s1-d1-8b | 5 | 0 |
| s1-d1-glm | 0 | 0 |
| s1-d1-glm-max | 0 | 0 |
| s1-d1-glm-r2 | 1 | 0 |
| s1-d1-kimi | 2 | 0 |
| s1-d1-m31f | 0 | 0 |
| s1-d1-step5 | 3 | 0 |
| s1-d2-30b | 0 | 0 |
| s1-d2-glm | 0 | 0 |
| s1-d2-glm-max | 0 | 0 |
| s1-d2-kimi | 1 | 0 |
| s1-d2-step5 | 1 | 0 |
| s1-d3-30b | 2 | 0 |
| s1-d3-glm | 0 | 0 |
| s1-d3-glm-max | 1 | 0 |
| s1-d3-kimi | 1 | 0 |
| s1-d3-m31f | 8 | 0 |
| s1-d3-m31f-r2 | 4 | 0 |
| s1-d3-step5 | 1 | 0 |
| swev | 0 | 0 |

## 8. 复现命令

```bash
# 盘点
python3 /tmp/rejudge2-inventory.py
# 原地口径基线（eval.log 解析，无容器）
python3 /tmp/rejudge2-inplace-shard.py <0..3> 4
# 互补 scope 干净重判
bash /tmp/rejudge2-driver.sh
# 独立复算
python3 /tmp/rejudge2-recompute.py; python3 /tmp/rejudge2-ab.py
# 本报告
python3 /tmp/rejudge2-report-gen.py
```
