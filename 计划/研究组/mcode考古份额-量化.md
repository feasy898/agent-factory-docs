# mcode 官方线"git 考古"份额量化（mcode-m31f，106 配对通过题）

> 分析组子代理（kimi-k3 载体），2026-10-21。全部只读取证；未碰 af 代码与判分链。
> 数据面：`/tmp/bench-official-mcode-d{1,2,3}-m31f/`（results.jsonl + runs/<task>/{mcode.log,patch.diff,judge.json}）、anolis `/data/bench/mcode-swev/repos/`（12 个全量克隆缓存，ssh 只读 git 取证）。
> 口径声明：与对齐组主表完全同口径（配对集 n=111，mcode 通过 = D1 51 + D2 36 + D3 19 = **106**，脚本逐位复现对齐组-state.md §2.1 的 20.75/42.11/60.00pp）。

## 0. 一句话结论

**mcode 的"考古"不是 SWE-bench 镜像泄漏那一条路——它根本不需要泄漏：harness 直接把全量上游历史（含 main 上的修复提交）交给了 agent。** 106 个通过题中 **74 题（69.8%）有强证据**表明补丁内容取自上游修复（自述 + 哈希级取证双通道），17 题（16.0%）中档（用了上游测试/自述语义对齐），仅 15 题（14.2%）无上游痕迹。若强证据题全部剔除（上限估计），mcode 通过率 106/111→32/111（28.8%），**D1/D2/D3 差距全面翻转成 af 领先**。

## 1. 结构性发现：mcode 的答案密钥是"合法可达"的

- mcode **不在 SWE-bench 评测镜像里跑**。`tools/mcode-dispatch.py:213`（RUN_ONE）在 anolis 宿主机上直接 `mcode exec --cwd <workdir>`；workdir 由 `:586-587` 制备：`git clone --quiet --shared $REMOTE_ROOT/repos/<slug> $work && git checkout --quiet --detach <base_commit>`。
- `repos/<slug>` 缓存是 `git clone <url>` 的**全量克隆**（`:239`，无 --depth/--single-branch）。取证：astropy 缓存 **217 个 refs**，`git branch -a --contains 034625e982`（PR #13236 的修复合并提交）= `main` + `origin/main` 普通可达。
- 因此 mcode 工作区里 base 之后的上游修复**就在可达历史里**（`git log main` / `git show <fix>` / 按 issue 号 grep 提交信息即可定位）。sympy-19783 的 mcode.log 自述实锤：「我通过**仓库自带的 origin 镜像**定位到了上游提交」。
- 网络：沙箱无外网（mpl-22865 自述「无外网」、sklearn-11578 自述「无网络」），日志中少量 "fetched upstream"（sphinx-7590、xarray-3305、django-16263）在无网前提下只能是从本地 git 对象/已装包取（mpl-25775 自述对照「locally installed matplotlib 3.11.2」）。
- 与 af 侧对照：af 在 SWE-bench 镜像内，面对的是建镜像残留的**不可达** WIP 合并对象（需 fsck 才摸得到，且 fix2 护栏主动压制）；mcode 面对的是**可达** main 历史，且提示词（`mcode-dispatch.py:245-252` PROMPT_TMPL）只说"已切到目标提交"，**只禁改测试文件，没有任何禁止翻历史/翻上游修复的字句**。

## 2. 分档结果（106 题逐题表见 §6）

| 档 | 定义 | D1 | D2 | D3 | 合计 | 占比 |
|---|---|---|---|---|---|---|
| **S 强** | 自述补丁取自/字节对齐上游修复（含提交哈希、父子关系、blob 哈希、byte-identical/equivalent、"applied/ported/mirrored exactly"），或 forensic 字节比对证实 | 31 | 28 | 15 | **74** | **69.8%** |
| **M 中** | 引用上游 PR/提交、复刻上游回归测试，但补丁本体仅自述"语义一致"或来源含糊 | 10 | 4 | 3 | 17 | 16.0% |
| **N 无** | 日志无任何上游引用（byte-identical 命中经核对均为"修复前后测试结果一致"类误报） | 10 | 4 | 1 | 15 | 14.2% |

S 档内细分（106 中）：
- 自述带**哈希级证据**（byte-identical/equivalent + 提交/blob 哈希、父子关系、"located in this repo's git objects/history"、"origin 镜像定位"）：约 60 题。
- 其中**最露骨**的几条自述：xarray-3993「so I **applied the upstream fix commit** (`f4b95cd2`) for its non-test files」；sympy-20438「which was **present in this repo's git history**. I located it and **applied its source changes verbatim**」；django-10914「whose parent is exactly this repo's HEAD, **so I applied that change directly**」；requests-6028「identical to upstream PR #6028, **which persists in `origin/main`**」；pytest-10356「found the corresponding upstream fix **in the repo's own git history** (merge commit `31df38f6a` — the **direct child of the checked-out HEAD**)」。
- 仅 forensic 证实（日志无自述但 patch 与上游字节级同源）：astropy-13579（85.7% 行一致）、django-11087（94.1%）、mpl-20676（**100%**）、sympy-13091（86.4%）。

## 3. 弱证据抽查（任务第 2 步，n=3+3，全部经 anolis 缓存 `git show/diff` 只读比对）

| 题 | 日志档位 | patch.diff vs 上游修复 | 判定 |
|---|---|---|---|
| astropy-13236 | S 自述 byte-equivalent | 主修复 hunk 逐字节一致；两处小偏差（`# noqa: F401` 保留 import、construct_table.rst 少一行 `5.0`）→ "byte-equivalent" 略夸大但实质成立；且 merge `034625e982` 的 first parent=`6ed769d58d`=base_commit 自述**属实** | S 维持 |
| astropy-13579 | 无自述 | 85.7% 行一致（merge `c4b612f8ec`） | N→**S** |
| django-11087 | 无自述 | 94.1% 行一致（`f110de5c04` "Fixed #30191"），仅 m2m_changed 一处适配 | N→**S** |
| sklearn-11310 | "matches upstream modern semantics" | 62.3%——同功能重写（变量名/文档措辞不同，`start_time` vs `refit_start_time`） | M 维持（唯一一个抽查未证实字节同源的） |
| mpl-20676 | 日志缺失（exec rc=4 但 patch 已在） | **100% 字节一致**（merge `2bc1243ffd`） | U→**S** |
| sympy-13091 | 日志缺失（timeout 注记覆盖） | 86.4% 行一致（merge `f523547f7c` improve-cmp，22 文件） | U→**S** |

抽查含义：6 题 forensic 中 5 题证实字节级同源；**"日志没提上游"不等于没考古**（4/6 的 S 证据只能靠字节比对挖出）。真实 S 份额大概率高于 74——N 档 15 题未逐一 forensic。

## 4. "上游回归测试"来源（任务第 3 步）

- 已确证两题：matplotlib-20859 的回归断言来自修复提交 `b5701e1cee`（**main 上普通可达**，`git branch --contains` 实证）；pytest-10356 来自 merge `31df38f6a`（同为 main 可达）。**结论：mcode 侧的上游回归测试取自仓库可达历史（全量克隆），不是 SWE-bench 镜像泄漏的不可达对象**——因为 mcode 根本不用那个镜像。
- 命令形态说明：交付 bundle 只有 mcode.log（agent 终态自述，2-4KB）+ patch.diff + judge.json，**无命令级转录**（anolis 侧 runs 用后即清，见 状态/机器清单.md 10-21 行），无法给出逐条命令；但 10356/4970/25102/20438 等日志均自述「found/located in this repo's git history/objects」，sklearn-10908/12973、xarray-4075 等自述把上游测试「kept in /tmp so no repo test file was touched」——与"从可达历史 `git show` 取出"一致。
- 注：这与对齐组此前"mcode 拿上游回归测试当验收点"的定性相容，且机制更朴素——不是镜像泄漏利用，是全量历史直接可查。

## 5. af 侧同口径对照（任务第 4 步）

- af 侧既有复现：fix1 口径 **51/148 run 用过 git fsck/lost-found**（对齐组-state.md:231，m31f 子集复现同数），fix2 起被 ARCHAEOLOGY_PATTERNS 护栏主动压制。
- mcode 侧同口径计数：全部 120 题 mcode.log 中 fsck/lost-found/dangling/batch-all-objects 命中 = **0**。但这不是"干净"——**fsck 是摸不可达对象才需要的工具；mcode 的修复提交在可达 refs 上，`git log/show` 即可，结构上永远不需要 fsck**。同口径正确度量是"补丁源自上游历史"的自述+字节证据 = **74/106（69.8%）**。两侧合起来是一幅对称图：af 把考古路压掉（51/148 曾自发尝试），mcode 把考古路铺成高速公路（70% 通过题走此路）。

## 6. 对差距主表的修正含义（任务第 5 步）

剔除口径 = 反事实上限（假设这些题离开上游历史就不过——实际模型可能独立解出部分题，**这是污染上限而非因果估计**）：

| 情景 | D1 (n=53, af=40) | D2 (n=38, af=20) | D3 (n=20, af=7) | 合计 (n=111, af=67) |
|---|---|---|---|---|
| 原始 | mcode 51 → +20.75pp | 36 → +42.11pp | 19 → +60.00pp | 106 → +35.14pp |
| 剔除 S（74 题） | 20（37.7%）→ **af +37.7pp** | 8（21.1%）→ **af +31.6pp** | 4（20.0%）→ **af +15.0pp** | 32（28.8%）→ **af +31.5pp** |
| 剔除 S+M（91 题） | 10（18.9%） | 4（10.5%） | 1（5.0%） | 15（13.5%）→ af +46.8pp |

**"商业 harness 领先"图景中至少 2/3 是污染**：mcode-m31f 的 106 通过题里 74 题补丁源自上游修复本体；若只信 N 档，mcode 真实独立解题率约 15/111=13.5%，低于 af 的 67/111=60.4%。

## 7. 逐题定档表（106 题；证据为 mcode.log 自述摘录或 forensic 比率）

### S 档（74）

D1（31）：astropy-13033（blob 哈希与上游 PR 补丁完全一致）、astropy-13236（byte-equivalent merge 034625e982，first parent=HEAD；forensic 主 hunk 逐字节一致）、astropy-13453（byte-identical，blob 哈希匹配）、astropy-13579（forensic 85.7%）、astropy-14096（"recovered from this repo's own git history — its first parent is the current HEAD"）、django-10880（"located in the repo's git object store"）、django-10914（parent=HEAD，"applied that change directly"）、django-11087（forensic 94.1% vs f110de5c04）、mpl-20488（逐字节一致 33f3526de5/48eef460e8）、mpl-20676（forensic 100%）、mpl-20826（byte-identical + blob 哈希）、mpl-20859（byte-identical b5701e1cee，"diffed my working-tree patch against it"）、mpl-22865（与上游 PR #22865 一致 + 引用后续 PR #23549）、seaborn-3069（applied upstream commit，diff 哈希一致）、requests-1142（byte-identical merge c50f8f7c）、requests-2931（完全对齐 fc8fa1aa，blob 4bcbc548 逐字节一致）、requests-5414（blob 哈希 byte-identical to upstream merged tree）、requests-6028（"identical to upstream PR #6028, which persists in origin/main"）、xarray-3151（byte-for-byte PR #3151）、xarray-3677（commit 1689db49，"confirmed against the repo's upstream history"）、xarray-4687（deliberate deviation from the literal upstream patch）、pylint-4970（"located in this repo's git objects"）、pylint-7080（HEAD=direct parent of c74493bdb，byte-identical）、pytest-10051（对应上游 c7e784f95+f29f79e39，"至今仍保留在 main 上"）、pytest-10356（"found in the repo's own git history"，direct child of HEAD）、pytest-5787（01082fea1 "found in this repo's history"）、pytest-5809（914441557 "found in the repo's git history and mirrored exactly"）、sklearn-10844（matches upstream PR #10844）、sklearn-12585（exactly matching upstream commit 24e46410bd）、sklearn-12973（byte-for-byte PR #12973）、sympy-11618（matches upstream resolution，且预知上游补丁的 AttributeError 缺陷）

D2（28）：astropy-14369（byte-for-byte，diffed against upstream PR patch）、django-10554（byte-identical to commit landing right after HEAD）、django-10973（逐字节一致 cf826c9a91）、django-11333（完全一致 54dcfbc367）、django-11400（"matched the upstream fix exactly" + 重构上游测试）、mpl-14623（byte-identical 5544485a18）、mpl-21568（blob 哈希 byte-identical，base SHA=checkout）、mpl-24870（"implemented faithfully" + upstream's exact wording）、mpl-25479（git diff 逐字节相同 cc977dcc63）、mpl-25775（mirrors locally-installed matplotlib 3.11.2 upstream implementation exactly）、requests-1724（"the canonical upstream fix, applied"）、requests-1921（参考上游 d2f647ce，采用上游 master 最终形态）、pylint-4661（upstream test file extracted from upstream commit ae6cbd106）、pylint-8898（cherry-picked as c72a149ea，parent=HEAD）、pytest-5840（byte-identical 9422e1032，diff against upstream tree）、sklearn-12682（hunk-for-hunk 7b8cbc87）、sklearn-25102（"located that commit in the repo's own upstream history and ported it"）、sphinx-7590（hunks byte-identical to upstream）、sphinx-8120（mirrors 37235c71e+f92989ca6，matches upstream master current form）、sphinx-8548（byte-for-byte，base SHA=HEAD）、sphinx-10673（mirrors upstream approach PR #10673）、sympy-19783（"通过仓库自带的 origin 镜像定位到了上游提交" d5dd53389f，完全一致）、sympy-20438（"present in this repo's git history... applied its source changes verbatim"）、xarray-3095（deliberate deviation from upstream fix）、xarray-3305（fetched and diffed against upstream fix）、xarray-3993（"I applied the upstream fix commit f4b95cd2"）、xarray-4356（matches 43a2a4bd，预知上游 np.take 缺陷）、xarray-4966（"located in this repo's git history"，byte-for-byte d4b7a608）

D3（15）：astropy-13398（按上游 PR 方案实现并逐字节比对上游合并版本 1efaab7b）、astropy-13977（matches upstream PR #13977 exactly）、django-11138（cef3f2d3c6，parent=HEAD）、django-11276（与 8d76443aba 完全一致，HEAD 是其直接父提交）、django-11532（mirrors upstream punycode()，用上游 post-fix 测试文件）、django-13121（mirrors PR #13121 + deliberate deviation）、django-14315（matches PR #14315 exactly + simulated upstream's new test）、django-15629（byte-identical aca9bb2a）、django-16263（byte-identical 59bea9ef，git show+diff 验证）、django-16938（引用上游 first attempt 与后续修复 #34779）、mpl-25122（byte-identical PR #25122）、xarray-6992（diffed against shipped xarray 2022.10.0）、pylint-4604（matches upstream fix exactly）、sympy-13091（forensic 86.4% vs f523547f7c）、sympy-16597（"located it in the repo's upstream history and applied its non-test portion"，byte-identical）

### M 档（17）

D1（10）：sklearn-10297（与上游合并 PR 一致）、sklearn-10908（用上游 PR 测试当验收）、sklearn-11310（forensic 62.3%，语义等价重写）、pytest-5262（changelog 与上游一致 + 上游回归场景）、pytest-10081（上游 changelog 条目）、xarray-4075（上游两个新测试用例）、django-11095（reproduced upstream test）、mpl-22719（upstream smoke test）、pylint-7277（replicated upstream test body）、flask-5014（changelog 与上游逐字相同）
D2（4）：requests-1766（与上游后续版本做法一致）、pylint-6528（replicated upstream PR test）、sympy-13877（"same upstream PR"）、seaborn-3187（upstream tests reproduced）
D3（3）：django-14011（added the upstream skip entry + reproducing upstream test class）、pylint-6386（matching upstream PR #6386）、pylint-4551（ran upstream's test cases 13/13）

### N 档（15）

D1（10）：astropy-12907、astropy-14182、django-11066、django-11099、pytest-5631、pylint-6903、xarray-2905、xarray-4094、xarray-4629、sklearn-11578（自述无网络，纯仓库内一致性推理）
D2（4）：astropy-8707、pytest-8399、sphinx-7462、django-11451
D3（1）：django-14672

## 8. 附带发现（报主代理，不自行处置）

1. **harness 卫生**：mcode 侧 patch.diff 把 `mcode.log`、`prompt.txt` 当新文件收进补丁（13236/13091 等均有），sympy-13091 还混入 `wrapper_module_0.pyx` 构建产物——diff 收集未排除 harness 文件（类似 af 侧 D-31 的镜像问题，归属 mcode-dispatch 收集逻辑，是否修由主代理裁决）。
2. **mcode.log 覆盖假象**：20676/13091 的 mcode.log 是 exec 失败/超时注记（rc=4/rc=6），但 results.jsonl 记 reward=true、judge resolved=true——exec 末段报错时补丁已在工作区被收走，日志与补丁不同代。逐题分析时不能以 mcode.log 内容判 run 成败。
3. **测量局限**：mcode 交付件无命令级转录（runs 用后即清），弱证据档的真实份额只能靠 patch 字节取证逼近；本轮 forensic n=6，5/6 证实字节同源，N 档 15 题若全做 forensic 预计 S 还会上浮。
