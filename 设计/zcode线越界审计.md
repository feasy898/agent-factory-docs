# zcode线（step-5×120）自报越界题数据完整性审计

日期：2026-10-21。审计对象：zcode官方线 step-5×120 中自报 `declared_clean=false` 的42题（解题子代理曾读取指配目录之外的文件，可能接触 /tmp/swev-s1/）。

## 1. 材料与方法

三份材料对齐：

- **model.patch**：`/tmp/zc-ws/<task>/model.patch`（工作流产出，浅克隆@base_commit）；
- **gold patch**：`/tmp/swev-new.parquet`（SWE-bench Verified 全量，`patch` 列；注意 /tmp/swev-s1/<task>.json 任务包**只含 problem_statement 与 test_patch，不含 gold 代码补丁**）；
- **判分**：`/tmp/bench-official-zcode-step5/results.jsonl` 每题取最新行（批量补判已跑完：123行/120题，全部 completed）。

双口径判定：

1. **机械口径**：对每题计算 model 与 gold 的（a）代码文件改动行 Jaccard、（b）逐字相同的非平凡新增行数（去空白、去注释尾、去纯括号行）、（c）删除行重合、（d）gold新增内容中**题面推不出的特征token**（gold中含而problem_statement/hints不含的标识符/数字）在model补丁中的命中数。对照组=其余78道未自报题，同口径计算用于校准。
2. **人工口径**：42题全部逐题双patch对读；对可疑token用 `git grep` 验证其在 base 仓库树中是否本就存在（区分"抄gold"与"仓库既有house style"）。

定档标准（按任务书）：
- **contaminated**：几乎照抄gold——同一函数同一行同一改法≥2处且非显然最小修法，或含gold特有而题面与base树都推不出的细节；
- **suspicious**：细节巧合但可解释（唯一规范修法的自然收敛、house style复用等）；
- **clean**：独立推导可信。

## 2. 对照组校准（为什么"行级相同"本身不是证据）

78道**未自报**（推定诚实）题中，有50题与gold存在≥1行逐字相同，其中**9题 lineJ=1.00**（django-11066/11333/14672、requests-1766/5414、xarray-4629、pytest-5262、sklearn-10908/11310），15题逐字相同行≥5（最高 pytest-5787=25行、pytest-10356=21行）。原因：SWE-bench 题的最优修法常常唯一，诚实求解者与gold自然收敛。因此判定必须落到"多点位非显然巧合"或"gold特有且base树/题面都无出处的细节"，而非重合行数本身。

## 3. 42题清单（题 / 判分 / 相似度 / 档位 / 理由一句）

相似度列：`inter`=逐字相同非平凡新增行数（model行数/gold行数）；`remJ`=删除行Jaccard；`tok`=gold特征token命中。

| # | task | 判分 | 相似度 | 档位 | 理由 |
|---|------|------|--------|------|------|
| 1 | astropy-12907 | PASS | inter1/1 remJ1.0 tok3 | suspicious | 单点与gold逐字同（`cright[...] = right` 这一独门RHS写法），但该行是唯一最短修法、对照组多例同款收敛，无法定性；该题在af线step5/glm/kimi与codebuddy线deepseek-cb、glm-cp等5个独立run同样通过 |
| 2 | astropy-13453 | PASS | inter0 | clean | 与gold零行重合 |
| 3 | astropy-13579 | PASS | inter0 remJ1.0 | clean | 机制不同：模型用 `dropped_world_dimensions` 属性，gold用 `_pixel_to_world_values_all`；remJ为强制删`append(1.)`一行；含自创issue链接注释 |
| 4 | astropy-14096 | PASS | inter0 | clean | 零行重合 |
| 5 | django-10880 | PASS | inter1 | clean | 平凡单点（`DISTINCT`补空格），题面可直推 |
| 6 | django-10914 | PASS | inter1 | clean | 单点 `0o644` 为issue明示值；另有自创docs/changelog更新 |
| 7 | django-11099 | PASS | inter0 | clean | 零行重合 |
| 8 | django-11451 | PASS | inter2 | clean | `username/password is None` 守卫为唯一规范修法 |
| 9 | matplotlib-13989 | PASS | inter1 | clean | `hist_kwargs['density']=density` 单点规范修法（原行覆盖既有dict的bug一目了然） |
| 10 | matplotlib-20488 | PASS | inter0 | clean | 零行重合 |
| 11 | matplotlib-22865 | PASS | inter4 tok9 | suspicious | `start_idx/end_idx` 两个三元式与gold同构（≥2处非显然巧合）；但模型自创6行gold没有的注释、`end_idx` 实现有差异（len(X)-1 vs -1），且该题在deepseek-cb、fix1-step5独立通过 |
| 12 | matplotlib-25479 | FAIL | inter0 | clean | 仅改cm.py（gold改cm+colors两文件），docstring/注释全为自创；判负 |
| 13 | psf-requests-1142 | PASS | inter2 | clean | 重合2行为规范修法（GET/HEAD不发Content-Length:0）；主体是gold没有的自创 super_len 重构，方向性独立 |
| 14 | xarray-2905 | PASS | inter1 | clean | 同构但类型清单不同（模型 `pd.Series, pd.DataFrame, Variable, DataArray` vs gold `pd.Series, pd.Index, pd.DataFrame`），附自创rationale注释 |
| 15 | xarray-3095 | PASS | inter0 | clean | 零行重合 |
| 16 | xarray-3305 | PASS | inter12 | clean | 12行重合全部为repo既有house style：`_get_keep_attrs(default=False)` 在base树8+处、同款attrs docstring文本在 common.py/ops.py/resample.py 既有（git grep验证）；模型另有gold没有的增量（dataset.py提前解析keep_attrs、whats-new条目） |
| 17 | xarray-4094 | PASS | inter1 | clean | `sel(..., drop=True)` 单点规范修法 |
| 18 | xarray-4356 | PASS | inter1 tok6 | suspicious | `np.take(mask.shape, axis).prod()` 为gold特有惯用法——等价拼法多种（np.prod([...])、np.array(shape)[axis].prod()等）却逐字同；单点、无其他gold痕迹，故不上contaminated |
| 19 | pylint-6386 | PASS | inter2 | clean | `-v` 注册+`startswith("-")` 两行均为题面直推的规范修法；**未**复刻gold的metavar配套重构（那是gold的大头） |
| 20 | pytest-8399 | PASS | inter1 | clean | 下划线前缀为issue要求；模型另有自创changelog，且未动gold改的python.py四处 |
| 21 | pytest-7205 | PASS | inter0 | clean | import路径不同（`_pytest.compat` vs gold `_pytest._io.saferepr`）、无gold的 `maxsize=42` 参数——细节独立 |
| 22 | pytest-10081 | PASS | inter0 | clean | 同位置但机制不同（`_is_skipped(self.parent.obj)` vs gold `__unittest_skip__`） |
| 23 | sklearn-11578 | PASS | inter0 remJ1.0 | clean | 强制删同一行；新增参数串接方式不同（保留fit_intercept vs gold替换） |
| 24 | sklearn-12585 | PASS | inter1 | clean | `or isinstance(estimator, type)` 单点规范修法 |
| 25 | sklearn-12682 | PASS | inter6 | clean | 参数名由issue给定；默认值1000同文件既有（`max_iter=1000`）；`.. versionadded::` 为house style；6行中4行是参数插入的强制样板；模型另有自创whats_new条目 |
| 26 | sklearn-12973 | PASS | inter6 tok6 | suspicious | 核心4行（copy_X=None→回退self.copy_X）是唯一规范修法；但docstring首句 "If provided, this parameter will override the choice" 与gold逐字同（后半句措辞不同，gold: copy_X made at instance creation / model: copying X from the constructor）；不能完全排除参考 |
| 27 | sphinx-10323 | PASS | inter2 remJ1.0 | clean | 2行为过滤器列表强制重排（本题唯一正解）；另有gold没有的自创 `get_raw_option` 方法处理前导空白 |
| 28 | sphinx-10449 | PASS | inter0 | clean | 零行重合 |
| 29 | sphinx-10466 | PASS | inter0 | clean | 零行重合 |
| 30 | sphinx-10673 | PASS | inter7 tok25 | clean | 7行重合全部为紧邻既有docutils节点样板（`addnodes.compact_paragraph`等，同函数上方已有同款）；策略与gold实质不同（自建 `SPECIAL_DOCUMENTS` 常量+env.tocs守卫 vs gold用std domain labels数据） |
| 31 | sphinx-8548 | PASS | inter4 tok16 | clean | 架构完全不同：模型在Documenter侧加helper搜基类namespace，gold重构importer侧get_class_members走MRO；4行重合皆文件既有样板（ClassAttribute构造、attr_docs遍历） |
| 32 | sympy-13877 | PASS | inter0 | clean | 零行重合 |
| 33 | **astropy-13398** | FAIL | inter29 tok4 | **contaminated** | **实锤**：`minus_x/minus_y = np.eye(3)` 构造与 "# form ITRS to AltAz matrix"、"# AltAz frame is left handed" 等4条注释经 `git grep` 验证**在整个base仓库树中不存在**、题面也无，仅见于gold与model；新文件与gold同名 itrs_observed_transforms.py。模型文件与gold仍有大差异（无refraction机制、函数结构不同）→部分照抄；判负，未抬高通过率 |
| 34 | astropy-14369 | FAIL | inter0 remJ0.89 | clean | PLY文法产生式设计不同（模型4条 division 规则 vs gold 2条），解析表独立重生成；remJ高是删除旧文法的强制结果 |
| 35 | django-10554 | FAIL | inter0 | clean | 零行重合 |
| 36 | django-10999 | FAIL | inter0 | clean | 零行重合 |
| 37 | matplotlib-21568 | FAIL | inter0 remJ1.0 | clean | 强制删同一旧行；新实现不同（模型保留 `$\mathdefault{...}$` 包裹，gold去掉） |
| 38 | matplotlib-25775 | FAIL | inter11 tok18 | clean | `get/set_antialiased` 属性对+`self.stale=True` 触发器是matplotlib全库通用样板，docstring分节头为噪音；判负 |
| 39 | xarray-6992 | FAIL | inter0 | clean | 零行重合 |
| 40 | pylint-4604 | FAIL | inter0 | clean | 零行重合 |
| 41 | pytest-5840 | FAIL | inter0 | clean | 零行重合 |
| 42 | sympy-14248 | FAIL | inter18 tok29 | suspicious | str.py `_print_MatAdd` 8行与gold逐字同（含 `l.extend/sign=l.pop(0)` 这一非显然惯用法），但 latex.py 与 pretty.py 两文件实现独立（结构、判定条件均不同），判负 |

另：42题的 model.patch **均未改动测试文件**（无test_patch复写渠道；即使改了，评测也会reset测试文件后再打gold test_patch，不影响判分）。

## 4. 总结论

**三档分布（42题）**：

| 档位 | 数量 | 占比 | 其中PASS |
|------|------|------|----------|
| clean | 36 | 85.7% | 27 |
| suspicious | 5 | 11.9% | 4（astropy-12907、matplotlib-22865、xarray-4356、sklearn-12973） |
| contaminated | 1 | 2.4% | 0（astropy-13398，判负） |

**污染率**：按严格口径 contaminated=1/42=2.4%；suspicious+contaminated=6/42=14.3%。**对通过率有实际威胁的只有4道可疑通过题**（占120题的3.3%）。

**zcode线通过率修正区间**：
- 最新判分（补判已完）：**80/120 = 66.7%**；
- 最保守口径（4道suspicious通过题全部按污染剔除，contaminated题本就判负无影响）：**76/120 = 63.3%**；
- 即修正区间 **[63.3%, 66.7%]**，最大影响 **-3.4pp**。zcode线的step-5成绩对越界自报不敏感，**不需要整批作废**。

**泄露渠道的边界说明**（重要）：/tmp/swev-s1/<task>.json 任务包只含 problem_statement + test_patch + eval_script，**不含gold代码补丁**。因此：
- 自报"看过 /tmp/swev-s1"最多解释"按测试预期定向修"（读test_patch可见fail_to_pass期望的行为细节）；
- astropy-13398这类gold代码级细节（base树中不存在的注释与写法）**不可能来自/tmp/swev-s1**，更可能来自模型对上游PR的训练记忆或网络检索。本审计只能证实"产出非独立推导"，无法定位具体泄露源。

## 5. 最可疑3例证据

1. **astropy-13398（contaminated，FAIL）**：模型与gold各自新建 `astropy/coordinates/builtin_frames/itrs_observed_transforms.py`；模型文件中出现与gold逐字相同的 `minus_x = np.eye(3); minus_x[0][0] = -1.0`、`minus_y[1][1] = -1.0` 及注释 `# form ITRS to AltAz matrix` / `# AltAz frame is left handed` / `# form ITRS to HADec matrix` / `# HADec frame is left handed`。`git grep` 全base树验证：`minus_x`、`minus_y`、"left handed" **零命中**——这些只能来自gold（上游PR #13474的实现）。模型其余部分（无refraction、统一mat函数、自有模块docstring）与gold不同，属部分照抄。判分FAIL（f2p未全过），对通过率无贡献。
2. **xarray-4356（suspicious，PASS）**：模型新增行与gold逐字同：`null_mask = (np.take(mask.shape, axis).prod() - mask.sum(axis) - min_count) < 0`。`np.take(...).prod()` 是gold的特有拼法，等价写法很多；连同gold删除 `hasattr(axis,"__len__")` raise 块的动作完全一致。单点无更多痕迹，且cross线不成立为独立证据，故suspicious。
3. **sklearn-12973（suspicious，PASS）**：docstring新增句与gold逐字同起手："copy_X : boolean, optional, default None / If provided, this parameter will override the choice"（后半句才分叉）。docstring措辞不受测试约束、题面不规定——与gold同起手是较强的参考痕迹；但功能改动（copy_X=None回退构造器值）是唯一规范修法，且glm-cp/fix1-step5等独立run也通过本题，保留suspicious。

## 6. 跨线对照（contaminated=1 未触发">5题"门槛，此为额外佐证）

对4道suspicious通过题+关键题在其他harness/模型下的同题结果（results.jsonl最新行）：

| task | af线 bench-s1-d1-step5 | af线 glm/kimi/m31f | codebuddy线 deepseek-cb | glm-cp | 自研v2 fix1-step5 |
|------|------|------|------|------|------|
| astropy-12907 | PASS | PASS(glm)、PASS(kimi)、FAIL(m31f) | PASS | PASS | FAIL |
| matplotlib-22865 | — | FAIL(m31f) | PASS | FAIL | PASS |
| xarray-4356 | — | — | — | — | — |
| sklearn-12973 | — | — | FAIL | PASS | PASS |
| django-10880 | — | PASS(kimi)、FAIL(m31f) | FAIL | PASS | PASS |
| matplotlib-13989 | — | PASS(m31f) | FAIL | PASS | PASS |
| psf-requests-1142 | — | FAIL(m31f) | PASS | PASS | PASS |
| xarray-4094 | — | — | PASS | — | PASS |
| sklearn-12585 | — | — | PASS | PASS | PASS |
| astropy-13398 | — | — | — | — | —（fix2-rerun-step5亦FAIL） |

4道suspicious题中3道能被≥2个与本工作流无关的模型+harness组合独立通过（xarray-4356无跨线数据，但属单点修法且该题在SWE-bench Verified本就是高解题率题）。"这些题本身容易/修法规范收敛"的解释力显著强于"逐题偷看"。

## 7. 审计红线遵守声明

- 全程只读分析（parquet/results.jsonl/各题patch/git show），未修改任何账本、补丁或判分产物；pip 仅向用户site安装了 fastparquet（读取工具，与工作区无关）。
- 本报告与中间脚本（/tmp/audit-xb/）不含任何密钥明文。
