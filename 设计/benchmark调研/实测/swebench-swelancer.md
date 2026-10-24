# SWE-bench Verified 与 SWE-Lancer 实测调研笔记

调研日期：2026-10-19。环境：Linux 本机（Docker 29.9.0，daemon 配置了 docker.m.daocloud.io / docker.1ms.run 两个 registry mirror，无 daemon 代理）；外网走 `socks5h://100.64.0.3:1080`；HF 走 hf-mirror.com。
本机落盘位置：`~/bench-study/`（SWE-bench、SWELancer-Benchmark-code、data/、venv-swebench）。

本文所有数字除特别标注"未核实"外，均来自本机实际下载/读出的文件或一手页面。写作原则：没核实到的如实写。

---

## 1. 克隆与数据落地（事实记录）

### 1.1 SWE-bench 主仓库
- 来源 `github.com/SWE-bench/SWE-bench`，git clone（depth 50）经 socks 代理一次成功。
- HEAD commit：`02e7a74ffd0b707aab73d203fe87bdc7c76afc8e`（2026-09-02，"Add some shorthands"）。
- License：MIT（LICENSE 原文 "Copyright (c) 2023 Carlos E Jimenez, John Yang, Alexander Wettig..."）。
- 体积：9.9MB。注意这是 2026 年重构后的新版本：包结构为 `swebench/{harness, image_builder, cli, collect, task, submit, inference}`，CLI 入口为 `swebench` 命令。

### 1.2 SWE-Lancer（openai/SWELancer-Benchmark）
- **重要发现**：`openai/SWELancer-Benchmark` 仓库 HEAD 只剩一个 README，原文：*"The SWE-Lancer codebase has been merged into https://github.com/openai/preparedness!"*（pushed_at 2025-07-18）。git clone 两次经代理挂死（.git 17MB 后卡住），改用 codeload tarball 成功。
- 真正代码在 `openai/preparedness` 仓库 `project/swelancer/`：
  - preparedness main commit：`b78dab1da774a6456b1ed9c48c9ff194ee3ff36d`（2026-10-12）。
  - License：MIT（LICENSE.md，"Copyright (c) 2025"）。
  - `project/swelancer` 体积 88MB（含 198 个任务的 flow.mitm 录像文件等）。
  - 目录：`all_swelancer_tasks.csv`（定价主数据）、`issues/<任务ID>/`（任务定义）、`Dockerfile_x86_{base,monolith,per_task}`、`runtime_scripts/`（ansible playbooks）、`swelancer/`（评测框架，基于 chz + nanoeval_alcatraz）。

### 1.3 SWE-bench Verified 数据集
- `princeton-nlp/SWE-bench_Verified`，经 hf-mirror 下载 `data/test-00000-of-00001.parquet`：
  - 大小：**2,096,679 字节（约 2.0MB）**；sha256 `a45b1fe4e2f0c8390b2b2938ac83e92ed5979000856808f3679c07812e9e6dcd`。
  - 500 行 × 13 列：`repo, instance_id, base_commit, patch, test_patch, problem_statement, hints_text, created_at, version, FAIL_TO_PASS, PASS_TO_PASS, environment_setup_commit, difficulty`。
  - HF 元数据：lastModified 2025-02-18，downloads 181,387，**未标注 license tag**（代码 MIT；实例内容源自 12 个上游仓库，各自 license 未在 dataset card 中声明——未核实到进一步说明）。
  - Verified 出处：OpenAI 2024-08-13 发布（"Introducing SWE-bench Verified"），对 SWE-bench 做人工校验取 500 题；openai.com 原文 403 无法直接打开，此说法来自 OpenAI 官网搜索摘要与 SWE-bench GitHub README（写明 2024-08-13、500 problems、real software engineers verified）。

---

## 2. Verified 内容质量（实读 500 题统计 + 逐题细读）

### 2.1 全量统计（pandas 实测）

| 维度 | 实测值 |
|---|---|
| 仓库分布 | django 231 (46.2%)、sympy 75、sphinx 44、matplotlib 34、scikit-learn 32、astropy 22、xarray 22、pytest 19、pylint 10、requests 8、seaborn 2、flask 1 |
| difficulty 标注 | <15min fix 194、15min-1h 261、1-4h 42、>4h 3 |
| problem_statement 长度 | min 143 / median 1185 / mean 1700 / max 24,770 字符 |
| FAIL_TO_PASS 每题 | min 1 / median 1 / max 438，总计 1516；**F2P==1 占 69.0%，≤3 占 92.4%** |
| PASS_TO_PASS 每题 | min 0 / median 50 / max 2476，总计 60,142；P2P==0 有 11 题 |
| hints_text | 33% 为空（含 maintainer 讨论摘录，属"软提示"） |
| created_at | 2012-01-25 → 2023-08-07（注意：最早一条 2012，多数 2016-2022） |
| gold patch 尺寸 | **median 1 个文件（85.8% 的题 ≤1 文件，95.6% ≤2 文件）；新增内容 median 183 字符** |
| F2P≥50 的异常题 | 仅 2 题：`django__django-10097`、`django__django-14672`（见 2.3 噪声证据） |

### 2.2 抽样细读（7 题，覆盖 7 个仓库）

**题 1：astropy__astropy-12907**（v4.3，2022-03，F2P=2 / P2P=13）——problem_statement 全文摘录：
> Modeling's `separability_matrix` does not compute separability correctly for nested CompoundModels
> ```python
> cm = m.Linear1D(10) & m.Linear1D(5)
> >>> separability_matrix(cm)
> array([[ True, False],[False,  True]])
> >>> separability_matrix(m.Pix2Sky_TAN() & cm)
> array([[ True,  True, False, False], ... [False, False,  True,  True]])
> ```
> Suddenly the inputs and outputs are no longer separable? This feels like a bug to me, but I might be missing something?

FAIL_TO_PASS：`astropy/modeling/tests/test_separable.py::test_separable[compound_model6-result6]`、`...[compound_model9-result9]`。test_patch 在既有参数化测试里加 cm8/cm9/cm10/cm11 四个 compound model 用例并给出期望矩阵。
**评价：高质量。** issue 自带可运行复现脚本，期望输出明确，测试直接对应 issue 场景。

**题 2：sympy__sympy-11618**（v1.0，2016-09，F2P=1 / P2P=4）——全文摘录：
> distance calculation wrong
> ```python
> >>> Point(2,0).distance(Point(1,0,2))
> 1
> ```
> The 3rd dimension is being ignored ... `sqrt((2-1)**2 + (0-0)**2)` is being computed instead of `sqrt(5)`.

F2P：`test_issue_11617`（test_patch 新增：`assert Point3D(1,0,2).distance(Point2D(2,0)) == sqrt(5)`）。
**评价：极小极清晰，但问题标题/描述粗糙（"distance calculation wrong"）；判定完全确定。**

**题 3：django__django-10097**（v2.2，2018-06，F2P=438 / P2P=1432）——problem_statement 摘录：
> Make URLValidator reject invalid characters in the username and password. Since #20003, core.validators.URLValidator accepts URLs with usernames and passwords. RFC 1738 section 3.1 requires ... An example URL that should be invalid is `http://foo/bar@example.com` ... Pull request: https://github.com/django/django/pull/10097

gold patch 实测：只改 `django/core/validators.py` 一个文件，核心是正则一行：
```
-        r'(?:\S+(?::\S*)?@)?'  # user:pass authentication
+        r'(?:[^\s:@/]+(?::[^\s:@/]*)?@)?'  # user:pass authentication
```
**但 FAIL_TO_PASS 有 438 条**，抽样可见大量与该 issue 无关的测试：`test_ascii_validator (auth_tests.test_validators.UsernameValidatorsTests)`、`test_help_text (auth_tests.test_validators.UserAttributeSimilarityValidatorTest)`、`Named URLs should be reversible` 等。一行正则改动让 438 个失败测试转 Pass 是不可能的行为学结果，这更像测试规格采集时的环境/收集期失败混入。**这是"测试判定不完全确定"的直接本机证据。**

**题 4：matplotlib__matplotlib-13989**（v3.0，2019-04，F2P=1 / P2P=411）。issue 用模板填好：复现代码 `plt.hist(np.random.rand(10), "auto", range=(0,1), density=True)`，Actual bins 首值 0.0033≠0，Expected 首尾为 0/1，且 bisect 到具体上游 commit。F2P：`test_hist_range_and_density`（断言 `bins[0]==0; bins[-1]==1`）。**高质量、判定确定。**

**题 5：pytest-dev__pytest-10051**（v7.2，2022-06，F2P=1 / P2P=15）。issue 给出根因分析（`caplog.get_records` 与 `caplog.clear` 内部 list 解耦，附源码行号链接）+ 可运行 repro。hints_text 为空。**高质量。**

**题 6：scikit-learn__scikit-learn-10297**（v0.20，2017-12，F2P=1 / P2P=28）。issue 是标准 bug 报告（`RidgeClassifierCV(store_cv_values=True)` 报 TypeError），含版本信息。hints_text 含 maintainer 对话（"thanks for the report. PR welcome"等，对解题无实质提示但会轻微剧透方向）。**良好。**

**题 7：pylint-dev__pylint-4551**（v2.9，2021-06，F2P=10 / P2P=0）。issue 是 2017 年的 **feature request**（"pyreverse 的 UML 输出不读 PEP 484 类型标注，期望输出 `a : String`"），报告时版本 pylint 1.6.5，附截图而非文本。F2P 是 10 个参数化的 `unittest_pyreverse_writer.py::test_dot_files[...]` / `test_get_visibility[...]`，**期望的 .dot 输出文件名与函数名（如 `get_annotation`）并不出现在 issue 文本里**，模型只能靠猜约定。P2P=0 意味着没有任何回归保护。**这正是 OpenAI 2026-02 审计点名的"窄测试"题型**（见 2.3）。

### 2.3 测试判定确定性与 28.4% 分歧

- 本机抽样感受：**大多数题判定确定**（issue 可复现 + 单个新增 F2P 测试直接对应，如 astropy/sympy/matplotlib/pytest）；**少数题测试规格噪声大**（django-10097 的 F2P=438 一行正则改动；pylint-4551 的 feature request + 零回归保护）。
- arXiv 2610.04371（NeurIPS 2026 workshop，FEAgent 工具）已核实：对 331 个通过测试的 agent patch 做等价性分析，**94 个（28.4%）与 gold patch 行为分歧**，且每个分歧均经直接执行裁定。这与本机看到的"测试只钉住 issue 场景、其它等价实现会被判死"一致。
- OpenAI 2026-02 博文《Why we no longer evaluate SWE-bench Verified》（openai.com 403 无法直接打开；以下引文经 Hacker News 讨论帖 #47910388 中对原文的逐字引用交叉确认）：*"We audited a 27.6% subset of the dataset that models often failed to solve and found that at least 59.4% of the audited problems have flawed test cases that reject functionally correct submissions."* 即在"模型常失败"的偏难子集（约 138 题）中 ≥59.4% 有缺陷测试；多篇二手来源据此推算全集约 16.4% 受影响（此比例为二手推算，未读到原文）。另引文的解释性细节（35.5% 窄测试 / 18.8% 宽测试等）同样未在原文直接核验。
- 结论：**"测试通过"≠"修复正确"在这个 benchmark 上有量化证据（28.4% 分歧、审计子集 59.4% 缺陷），用于绝对分数要打折，用于相对比较（同一 harness 下 A vs B）仍有一定信号。**

---

## 3. SWE-Lancer（实读 preparedness/project/swelancer）

### 3.1 任务结构：IC vs Manager
- `all_swelancer_tasks.csv`（463 行数据）实测：**ic_swe 198 题、swe_manager 265 题**，全部标 `diamond` 集。
- README 原文（2025/07/17 注）：*"as of 2025/07/17, this repo contains a subset of the original 237 problems mentioned in the SWE-Lancer paper. Specifically, this repo has 198 tasks that were adjusted and verified to run offline. We have dropped the remaining 39 problems."* 即开源 IC 集从 237 缩到 198；`issues/` 目录实测 199 个条目 = 198 个任务目录 + 1 个 `conftest.py`，与 CSV 完全对齐。
- **论文全量口径**（arXiv 2502.12115 HTML 版核实）：1,488 个 Upwork 任务共 $1,000,000；IC 764 题 $414,775 + Manager 724 题 $585,225；公开 Diamond 集 502 题 $500,800（IC 237 题 $236,300 + Manager 265 题 $264,500），其余 $499,200 为私有 heldout。**开源 CSV 的 manager 265 题 = 论文 Diamond manager 全集；IC 198 题合计 $189,300 < 论文 $236,300（差 39 题）。**
- 全部任务基于同一仓库：**Expensify/ReactNativeChat（App）**，真实 Upwork 固定价外包单（issue 页脚保留 Upwork Job URL/ID）。

### 3.2 美元定价数据在哪、分布
- 定价在两处：`all_swelancer_tasks.csv` 的 `price` 列；每个 `issues/<ID>/issue_data.json` 也有 `price` 字段。Manager 题价格在 CSV `manager_data` 里也有。
- IC 198 题实测分布：$50×1、$125×2、**$250×84、$500×62**、$1000×27、$2000×9、$4000×9、$8000×3、$32000×1；合计 **$189,300**。Manager 265 题合计 **$264,500**（median $500，max $32000）。开源部分合计 **$453,800**。
- 价格 = 2023 年该外包单真实固定报酬，与难度只有弱相关（$250 一档占 42%），"$"本质是**按任务加权的 pass rate**。

### 3.3 每个任务的定义（抽样读了 2 个：16912_4、40250_1042）
`issues/16912_4/`（$1000，zipcode 提示文案不一致）包含：
- `issue_data.json`：price/title/html_description/issue_repo_steps（即给模型看的 issue 全文）；
- `commit_id.txt`：Expensify 仓库锚定 commit（`2b791c9f...`）；`git_tag.txt`/`revert_command.txt`（部分任务用）；
- `bug_reintroduce.patch`：gold 修复的逆向补丁，评测前打上以复现 bug；
- `flow.mitm`：275KB mitmproxy 录像，离线回放 Expensify 后端流量；
- `test.py`：Playwright 端到端测试（headless Chromium，`proxy={"server":"http://localhost:8080"}` 指向 mitmdump 回放，`install_online_guard_sync` 防联网，断言如"offline 提示不该出现/文案应为 Format"）；
- `user_tool.py`：模拟用户按 bug 报告操作 App、输出 Playwright trace 供 agent 调试。

### 3.4 端到端测试如何组织（代码级）
- 运行时：`Dockerfile_x86_base`（ubuntu:22.04 + nvm/conda/playwright/mitmproxy/Xvfb+fluxbox+x11vnc）→ `Dockerfile_x86_per_task`（ARG ISSUE_ID，预跑 `setup_expensify.yml`：checkout commit → 打 bug_reintroduce.patch → npm_fix → 装 .nvmrc 对应 Node → **构建期完成 npm 依赖安装**）或 `Dockerfile_x86_monolith`（`RUNTIME_SETUP=true`，运行时才做上述 setup）。
- 评测：`swelancer/eval.py grade()` → `unzip -P 'secretpasswordhere' /app/tests.zip`（测试文件在容器内加密存放，模型不可见）→ IC 走 `_grade_swe_ic()`：`git diff` 取模型补丁 → **ansible playbook `run_tests.yml` 起 webpack dev server + mitmdump 回放 + pytest**，读 `pytest_exit_code` 判定；`n_test_runs` 默认 **3**（代码 docstring 原话："Tests will be run this many times until they don't fail, to account for occasional non-deterministic test failures."——官方自己承认 E2E 测试有非确定性）。
- Manager 判定极简：读 `/app/expensify/manager_decisions.json`，与 `manager_data["game"]["correct_proposal"]["id"]` 比对，二值 0/1，`grader_log` 里 `earned = price * correct`。即 **manager 题是"从若干真实竞标提案中选对正确方案"的选择题**（`all_formal_proposals` + `correct_proposal`）。
- 断网：`disable_internet` 默认 True，靠宿主 `iptables` 给容器断网（README：仅 Linux，Mac 需关闭但结果不算数；规则带 `alcatraz_block` 注释）。
- 模型可见输入（`prompts.py`）：IC 题 = issue title + html_description + "The reward for the correct fix is ${price}"，通过"写 python 脚本被执行 + `<user-tool>` 模拟用户操作"交互。

### 3.5 论文成绩基线（arXiv 2502.12115 核实）
Diamond 集 $500,800：Claude 3.5 Sonnet 赚 $208,050（IC diamond pass 26.2%，Manager 44.9%）；GPT-4o IC diamond 8.0%。Diamond IC 题平均改 2 个文件 69 行，原单平均 26 天、47 条 GitHub 评论解决，约 100 名工程师参与出题/验证。

### 3.6 "美元计价"口径对订单 ROI 测量的可用性
可用，且有独到价值，但有四个折扣项：
1. **真实价格锚定**：价格是真实市场成交价（Upwork 固定价），"$ earned"比"% pass"更贴近订单口径，可直接映射"接单金额/成本"。
2. **域窄**：463 题全部是 2023 年 Expensify 一个 React Native 仓库，价格反映的是该细分市场，不能外推到通用工程订单。
3. **价格≠难度**：$250 档占 42%，$32000 只有 1 题；单题价格由客户出价决定，$ earned 对"难且贵"的题过拟合/欠拟合都敏感——建议同时报 pass@计数 与 $ earned 两个口径。
4. **二值判定 + 3 次重试**：IC 题按 pytest 退出码二值计费，官方承认非确定性（默认跑 3 次），ROI 计算要计入这层方差；Manager 题是选择题，44.9% 的及格线已经很接近乱选基线之上的区间，单看 $ 容易高估。
另注意：**开源部分只覆盖论文 $1M 中的 $453.8K**，$499.2K heldout 拿不到，跨论文对比时要声明口径。

---

## 4. 可克隆性（本环境实测）

### 4.1 已跑通
- `git -c http.proxy=socks5h://... clone` SWE-bench：成功（9.9MB）。
- HF parquet 经 hf-mirror：成功（2MB，秒下）。
- `pip install swebench`（清华源，Python 3.14 venv）：**成功，版本 5.0.2**，CLI 可用（`swebench eval / images / dataset / report`）。依赖装齐，无编译障碍。
- SWELancer 代码经 codeload tarball：成功（git clone 两次挂死，代理对大 pack 不稳，建议一律用 tarball 或镜像加速）。

### 4.2 障碍（实测数据）
- **Docker 镜像源**：daemon 只配了 daocloud/1ms.run 两个 mirror。实测 `docker pull python:3.12-alpine` 成功（mirror 有缓存的常见镜像没问题），但 **`docker pull swebench/sweb.eval.x86_64.sympy_1776_sympy-11618:latest` 分别跑 240s 和 480s 均无输出超时**——mirror 对冷门仓库回源失败/挂起。解法：给 docker daemon 配 `socks5h://100.64.0.3:1080` HTTP 代理直连 Docker Hub，或把镜像转推到可达的私有 registry。
- **镜像尺寸与磁盘**：
  - SWE-bench：Docker Hub `swebench` namespace 实测 4,503 个镜像仓库；抽样单实例压缩体积 **1.06–1.74 GB**（sympy 1.06 / astropy 1.13 / django-10097 1.22 / matplotlib 1.74）。Verified 500 实例若全量拉取，按均值 ~1.3GB 压缩估算 **≥600GB 下载量**，解压后更大；本机 / 只剩 152GB，**全量不可行，必须按抽题拉取**（有跨实例 layer 共享，实际占用会低于求和，但首拉量仍大）。镜像 2026-08 全量重推过（与 swebench 5.x harness 配套）。
  - SWE-Lancer：README 原文 **"Each task image takes 10-20 minutes to build, and occupies ~14GB"**（14GB/任务的说法属实，指本地解压后单任务镜像占用）。Docker Hub `swelancer` namespace 实测 200 个仓库；`swelancer_x86_monolith:latest` **4.82GB（压缩）**，抽样 `swelancer_x86_16912_4:releasev1` **6.42GB（压缩）**；前 100 个 task 仓库大多没有可拉 tag（0 字节占位），实际可拉的是 monolith + 部分 per-task。198 题走 monolith + 运行时 setup 更现实，但运行时 setup 每题要 npm install + webpack，耗时数十分钟级。
- **运行条件**：SWE-Lancer 需要 `uv sync`（`UV_GIT_LFS=1`）、Linux + iptables 断网、alcatraz 本地 runtime；Manager 题必须 monolith。SWE-bench eval 需要 Docker daemon 可达 Docker Hub（或自备镜像）。
- **collect 流程（未实测，代码级确认）**：新版 CLI `swebench dataset collect <owner/repo>`（抓 GitHub issue-PR 对）→ `dataset build`（版本化数据集）；评测 `swebench eval verified -p preds.jsonl --run-id X -j 16`（自动 pull/build 实例镜像 → 容器内应用补丁 → 跑 F2P/P2P → 解析日志）或 `swebench eval verified --gold`（跑 gold patch 验环境）；`swebench report <run> -d verified` 出 report.json。经典 collect 管线（爬 PR→跑测试得 F2P/P2P→过滤）仍在 `swebench/collect/`。

---

## 5. 它真实测量的能力

### 5.1 SWE-bench Verified：单点 bug 修复 + 定位检索，不是长程工程
- 本机统计：gold patch **median 1 个文件、183 个新增字符**；85.8% 的题 ≤1 文件；F2P median 1。这是**单点修复**的量级，与 SWE-Lancer paper 对 Diamond IC 的描述（平均 2 文件 69 行）互相印证。长程任务（跨模块设计、多日迭代、需求澄清）不在此 benchmark 的测量范围内。
- **定位/检索权重高但难以剥离**：给模型的输入只有 issue 文本 + 整仓 checkout。The SWE-Bench Illusion（arXiv 2506.12286，Microsoft，已核实摘要）：SOTA 模型**仅凭 issue 文本猜对 76% 的 bug 文件路径**（非 SWE-bench 仓库对照组只有 53%）；让模型仅凭当前文件+issue 复现 gold 函数，在 SWE-bench 上 5-gram 连续命中率最高 35%（对照 18%）——作者解读为记忆效应。也就是说"读 issue→定位文件"这一步占了大头，且可能有一部分是背出来的。
- 时效性：所有实例 created_at ≤ 2023-08-07，早于所有主流模型的训练截止，issue/PR 是公开网页，进入预训练语料（Common Crawl 级别）几无门槛。
- 污染证据链（按证据强度排序）：① arXiv 2512.10218（已核实摘要）：Claude 模型在 Verified 上的表现是对照 benchmark（BeetleBox/SWE-rebench）的 ~3 倍、文件定位 ~6 倍，作者归因于训练记忆（间接证据）；② 2506.12286 的 76%/53% 与 35%/18% 差（间接证据）；③ 2610.04371 的 28.4% patch 分歧（测试不是可靠 oracle，执行裁定）；④ OpenAI 2026-02 弃用声明（混合了缺陷测试与污染，原文 403，引文经 HN 逐字引用交叉）。检索到有二手摘要称"Verified 在 StarCoder 语料中 10.6% 泄漏率"，**未定位到原文出处，不采信，仅备忘**。
- 结论：Verified 现在测的是"**单点修复 + 高度见过的仓库族上的定位能力 + 通过一个不完美 oracle**"。做订单 ROI 参照时，建议只用它做回归比较（同一 harness、同一题目子集），不做绝对能力外推。

### 5.2 SWE-Lancer：更接近真实外包交付，测三件事
1. **从自然语言 bug 报告复现并修复 UI/业务行为**（IC 题）：无单测可依，靠 E2E 浏览器测试；issue 是真实客服/外包单文风（含视频链接失效、平台清单等噪声），**信息完整度两极**——有的步骤详尽，有的要靠 user tool 反复试。上下文检索权重低于 SWE-bench（Expensify 单仓、issue 不含仓库历史包袱），但"和真实代码库对齐行为"的调试循环很重。
2. **技术方案评审/选择**（Manager 题）：读多份真实竞标提案选出正确方案，测的是**技术判断力**而非写码；判定是纯二值选择题。
3. **美元加权交付率**：这是它对"黑灯工厂接单 ROI"最有价值的部分——可以直接把模型 pass 率换算成"预计可承接订单金额比例"。
局限：单仓库（Expensify）、2023 年、Web/RN 栈；198/237 IC 题开源且明确是"verified to run offline"子集；E2E 测试非确定性（官方默认跑 3 次）；Docker 镜像 14GB/题、构建 10-20 分钟，实测克隆成本高。

---

## 6. 对本项目（agent 黑灯工厂）的直接含义
- **短期可落地**：Verified 数据 2MB 即拿即用，swebench pip 一行装好；但评测要过 Docker Hub 这一关（daemon 配代理或自建 registry），且磁盘按抽题预算（每实例 ~1.3GB 压缩起）。
- **ROI 口径建议**：以 SWE-Lancer 的 $ earned 做主口径（真实价格加权）、Verified 做单点修复能力的回归监控口径；两者都报"计数 pass 率 + $ 加权"双数字。
- **必须内置的质检**：28.4% 分歧 + 审计 59.4% 缺陷测试说明"benchmark 判分"本身要抽样人工复核——黑灯工厂的评测器产线应把"gold patch 复跑 + 等价解抽检"作为固定工序。

## 附：证据文件位置
- Verified parquet：`~/bench-study/data/swebench_verified_test.parquet`（2,096,679 B，sha256 a45b1fe4…）
- SWE-bench 仓库：`~/bench-study/SWE-bench`（commit 02e7a74f，MIT）
- SWELancer 代码：`~/bench-study/SWELancer-Benchmark-code`（= preparedness `project/swelancer`，commit b78dab1d，MIT）；全量备份 `~/bench-study/preparedness`
- swebench 5.0.2 venv：`~/bench-study/venv-swebench`
- 外部一手来源：arXiv 2610.04371 / 2502.12115（HTML）/ 2506.12286 / 2512.10218 摘要；HN item 47910388（含 OpenAI 博文逐字引用）；Docker Hub API（swebench/swelancer namespace 实测数据）。
