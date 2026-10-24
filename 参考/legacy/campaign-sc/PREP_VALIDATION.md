# PREP_VALIDATION — prep_sc1.py 自测记录

- 主机：anolis（全部命令经 `ssh anolis` 真跑，非本地模拟）
- 日期：2026-10-16
- 被测脚本：`/home/pan-ding/campaign-sc/scripts/prep_sc1.py`
- Python：3.11.6（/usr/bin/python3）

## 1. 准备被测工作区

```
$ python3 /home/pan-ding/bench/scripts/prepare_task.py \
      /home/pan-ding/bench/tasks/sc-sqlparse-bugfix /tmp/prep-test /tmp/prep-test-p.txt
OK
RC=0
```

`/tmp/prep-test` 下为 vendored sqlparse（21 个 .py 文件）。
注意：本工作区中**不存在**小写 `strip_comments` 的 def/class 符号（仅 `StripCommentsFilter` 类，
`strip_comments` 只作为 formatter.py 的选项/局部变量名出现，grep 证实：
formatter.py:31 `strip_comments = options.get('strip_comments', False)` 等）。
因此 `def` 查询带一层"忽略大小写/下划线"的模糊回退（精确命中优先，回退时显式标注），
使 `def strip_comments` 能定位到 `StripCommentsFilter` —— 见 §2 关键检查①。

## 2. 四臂生成 + 门禁（对 /tmp/prep-test 真跑）

```
$ python3 /home/pan-ding/campaign-sc/scripts/prep_sc1.py /tmp/prep-test g1f
  [gate] PASS query.py def parse | rc=0 out='sqlparse/__init__.py:23 [function] def parse(sql, encoding=None)' err=''
  [gate] PASS query.py calls parse | rc=0 out='sqlparse/__init__.py:33 parsestream' err=''
  [gate] PASS query.py calledby parsestream | rc=0 out='sqlparse/__init__.py:23 parse' err=''
  [gate] PASS query.py file __init__.py | rc=0 out='== sqlparse/__init__.py == L1-L72 [module] sqlparse ...' err=''
prep_sc1[g1f] 完成: 21 文件 / 274 符号 / 471 调用边
  生成 codegraph.json (127915 bytes)
  生成 tools/query.py (4819 bytes)
prep_sc1[g1f] 门禁通过（4 项检查全部 PASS）      RC=0

$ python3 /home/pan-ding/campaign-sc/scripts/prep_sc1.py /tmp/prep-test g2f
  [gate] PASS lookup.py pars | rc=0 out='sqlparse/__init__.py:23 [function] parse L23-L30 def parse(sql, encoding=None) ...' err=''
prep_sc1[g2f] 完成: 22 文件 / 286 符号 / 488 调用边
  生成 codeindex.tsv (24240 bytes)
  生成 tools/lookup.py (1960 bytes)
prep_sc1[g2f] 门禁通过（1 项检查全部 PASS）      RC=0

$ python3 /home/pan-ding/campaign-sc/scripts/prep_sc1.py /tmp/prep-test g3f
  [gate] PASS ast_tools.py inspect | rc=0 out='/tmp/prep_gate_g3f_v0q0hsb2/gate_file.py (72 行) L23-L30 def def parse(sql, encoding=None) ...' err=''
  [gate] PASS ast_tools.py body parse | rc=0 out='def parse(sql, encoding=None): """Parse sql and return a list of statements. ...' err=''
  [gate] PASS ast_tools.py replace parse (字节级校验) | rc=0 out='已替换 ... :: parse (L23-L30, 旧 331 字节 -> 新 358 字节)' err=''
prep_sc1[g3f] 完成: 23 文件 / 289 符号 / 492 调用边
  生成 tools/ast_tools.py (7146 bytes)
prep_sc1[g3f] 门禁通过（3 项检查全部 PASS）      RC=0

$ python3 /home/pan-ding/campaign-sc/scripts/prep_sc1.py /tmp/prep-test g7f
  [gate] PASS lsp.py def parse | rc=0 out='sqlparse/__init__.py:23 [def] def parse(sql, encoding=None)' err=''
  [gate] PASS lsp.py refs parse | rc=0 out='tools/ast_tools.py:121: return ast.parse(src, filename=path) tools/lsp.py:133: ...' err=''
  [gate] PASS lsp.py hover parse | rc=0 out='sqlparse/__init__.py:23 [def] def parse(sql, encoding=None) Parse sql and return ...' err=''
  [gate] PASS lsp.py def gate_target (合成工程) | rc=0 out='sample.py:4 [def] def gate_target(a, b=1)' err=''
  [gate] PASS lsp.py refs gate_target (合成工程) | rc=0 out='sample.py:9: return gate_target(2) 共 1 处引用' err=''
  [gate] PASS lsp.py hover gate_target (合成工程) | rc=0 out='sample.py:4 [def] def gate_target(a, b=1) (无 docstring)' err=''
prep_sc1[g7f] 完成: 24 文件 / 304 符号 / 527 调用边
  生成 tools/lsp.py (9058 bytes)
prep_sc1[g7f] 门禁通过（6 项检查全部 PASS）      RC=0
```

（说明：四臂先后 prep 进同一目录，后跑的臂会把先生成的 tools/*.py 一并索引，
故文件数 21→24 递增；实际战役中每个臂使用独立工作区副本，无此现象。）

## 3. 每个工具的每个子命令逐一真跑（cwd=/tmp/prep-test）

### 3.1 g1f tools/query.py（def/calls/calledby/file）

```
$ python3 tools/query.py def strip_comments
（未精确命中 strip_comments，以下为忽略大小写/下划线的模糊结果）
sqlparse/filters/others.py:14  [class]  class StripCommentsFilter
```
**关键检查①达成**：定位到 `sqlparse/filters/others.py`。

```
$ python3 tools/query.py def StripCommentsFilter
sqlparse/filters/others.py:14  [class]  class StripCommentsFilter

$ python3 tools/query.py calls parse
sqlparse/__init__.py:33  parsestream

$ python3 tools/query.py calledby parse
索引中没有指向 parse 的调用          （如实报告：函数体内无 Name 调用 parse）

$ python3 tools/query.py calledby _process
sqlparse/filters/aligned_indent.py:40  AlignedIndentFilter._process_statement
sqlparse/filters/aligned_indent.py:115 AlignedIndentFilter._process_default
sqlparse/filters/aligned_indent.py:133 AlignedIndentFilter.process
sqlparse/filters/others.py:53          StripCommentsFilter.process
sqlparse/filters/others.py:127         SpacesAroundOperatorsFilter.process
sqlparse/filters/output.py:21          OutputFilter.process
sqlparse/filters/reindent.py:232       ReindentFilter._process_default
sqlparse/filters/reindent.py:238       ReindentFilter.process
sqlparse/filters/right_margin.py:23    RightMarginFilter._process

$ python3 tools/query.py file others.py
== sqlparse/filters/others.py ==
  L1-L149  [module]  sqlparse.filters.others  module sqlparse.filters.others
  L14-L56  [class]   StripCommentsFilter  class StripCommentsFilter
  L16-L51  [method]  StripCommentsFilter._process  def _process(tlist)
  L18-L20  [function] StripCommentsFilter._process.get_next_comment  def get_next_comment()
  L22-L32  [function] StripCommentsFilter._process._get_insert_token  def _get_insert_token(token)
  L53-L56  [method]  StripCommentsFilter.process  def process(self, stmt)
  L59-L105 [class]   StripWhitespaceFilter  class StripWhitespaceFilter
  ...（StripTrailingSemicolonFilter / SerializerUnicode 等同样列出，共 21 行）

$ python3 tools/query.py def 不存在的符号xyz
未找到符号: 不存在的符号xyz      RC=0
```

### 3.2 g2f tools/lookup.py（子串模糊查）

```
$ python3 tools/lookup.py StripCommentsFilter
sqlparse/filters/others.py:14  [class] StripCommentsFilter  L14-L56  class StripCommentsFilter
```
**关键检查②达成**：找到类定义。

```
$ python3 tools/lookup.py stripcomments
（区分大小写无命中，以下为忽略大小写的结果）
sqlparse/filters/others.py:14  [class] StripCommentsFilter  L14-L56  class StripCommentsFilter

$ python3 tools/lookup.py Strip
sqlparse/filters/others.py:14  [class] StripCommentsFilter     L14-L56   class StripCommentsFilter
sqlparse/filters/others.py:59  [class] StripWhitespaceFilter   L59-L105  class StripWhitespaceFilter
sqlparse/filters/others.py:133 [class] StripTrailingSemicolonFilter L133-L139 class StripTrailingSemicolonFilter
...

$ python3 tools/lookup.py zzz_notexist
未找到名称包含 'zzz_notexist' 的符号      RC=0
```

codeindex.tsv 表头与列序（name/kind/signature/file/start_line/end_line/parent）：
```
$ head -3 codeindex.tsv
name	kind	signature	file	start_line	end_line	parent
sqlparse	module	module sqlparse	sqlparse/__init__.py	1	72	
parse	function	def parse(sql, encoding=None)	sqlparse/__init__.py	23	30	
```

### 3.3 g3f tools/ast_tools.py（inspect/body/replace）

```
$ python3 tools/ast_tools.py inspect sqlparse/filters/others.py
sqlparse/filters/others.py  (149 行)
L14-L56  class      class StripCommentsFilter
  L16-L51  def        def _process(tlist)
    L18-L20  def        def get_next_comment()
    L22-L32  def        def _get_insert_token(token)
  L53-L56  def        def process(self, stmt)
L59-L105  class      class StripWhitespaceFilter
  ...（全文件 21 个符号均列出）

$ python3 tools/ast_tools.py body sqlparse/filters/others.py StripCommentsFilter
class StripCommentsFilter:

    @staticmethod
    def _process(tlist):
        def get_next_comment():
            # TODO(andi) Comment types should be unified, see related issue38
            return tlist.token_next_by(i=sql.Comment, t=T.Comment)
        ...
    def process(self, stmt):
        [self.process(sgroup) for sgroup in stmt.get_sublists()]
        StripCommentsFilter._process(stmt)
        return stmt
```
**关键检查③达成**：完整打印类源码（L14-L56，43 行）。

replace 在副本上真跑 + 字节级验证：
```
$ cp sqlparse/filters/others.py /tmp/others_copy.py
$ printf 'class StripCommentsFilter:\n...(新实现 10 行)...\n' > /tmp/new_impl.py
$ python3 tools/ast_tools.py replace /tmp/others_copy.py StripCommentsFilter /tmp/new_impl.py
已替换 /tmp/others_copy.py :: StripCommentsFilter  (L14-L56, 旧 1975 字节 -> 新 263 字节)   RC=0
$ python3 -c "import ast; ast.parse(open('/tmp/others_copy.py').read()); print('ast.parse OK')"
ast.parse OK
$ diff sqlparse/filters/others.py /tmp/others_copy.py | grep -E '^[0-9]'
18,51c18          ← 唯一 diff 块，严格落在被替换区间 L14-L56 内
$ head -14 两个文件的 md5 相同：263242a5a86e3b389fc014e5bc0f5dd1（前缀字节不变）
$ tail -n +24 copy 与 tail -n +57 原文件 md5 相同：cf80ecd95c94069a01ba46f175399146（后缀 3325 字节不变）
```

### 3.4 g7f tools/lsp.py（def/refs/hover）

```
$ python3 tools/lsp.py def StripCommentsFilter
sqlparse/filters/others.py:14  [class]  class StripCommentsFilter

$ python3 tools/lsp.py refs StripCommentsFilter
sqlparse/filters/__init__.py:9: from sqlparse.filters.others import StripCommentsFilter
sqlparse/filters/others.py:55: StripCommentsFilter._process(stmt)
sqlparse/formatter.py:164: stack.stmtprocess.append(filters.StripCommentsFilter())
共 3 处引用
```
**关键检查④达成**：refs 找到 `filters/__init__.py` 的引用（含该行内容）。

```
$ python3 tools/lsp.py hover StripCommentsFilter
sqlparse/filters/others.py:14  [class]
class StripCommentsFilter
(无 docstring)

$ python3 tools/lsp.py def strip_comments
（未精确命中 strip_comments，以下为忽略大小写/下划线的模糊结果）
sqlparse/filters/others.py:14  [class]  class StripCommentsFilter

$ python3 tools/lsp.py refs zzz_notexist
全库未发现 zzz_notexist 的引用      RC=0
```

## 4. 空项目门禁不误伤

`/tmp/prep-empty`（空目录，无任何 .py）四臂全跑：
```
g1f: 0 文件 / 0 符号 / 0 调用边；4 项检查 PASS（def/calls/calledby/file 均优雅"未找到"，RC=0）
g2f: （同目录已有 tools/query.py 被索引）1 文件 / 12 符号；lookup 命中 _norm，PASS，RC=0
g3f: 2 文件；inspect/body/replace（合成样例 + 字节级校验）PASS，RC=0
g7f: 3 文件；def/refs/hover 真符号 + 合成工程 gate_target 三查 PASS，RC=0
生成工件：codegraph.json、codeindex.tsv、tools/{query,lookup,ast_tools,lsp}.py 全部就位
空索引抽查：query def anything / lookup anything / lsp def anything → 均"未找到"，RC=0
```
另做全新空目录单跑 g2f：`0 文件 / 0 符号 / 0 调用边`，门禁 1 项 PASS，RC=0（走真空索引分支）。

## 5. 边界与失败路径

| 场景 | 命令 | 结果 |
|---|---|---|
| 非法 arm | `prep_sc1.py /tmp/prep-bad g9x` | rc=2，"未知 arm: g9x" |
| workdir 不存在 | `prep_sc1.py /tmp/no_such_dir g1f` | rc=2 |
| 含语法错误 .py 的项目 | `printf 'def broken(:\n    pass\n' > bad.py` 后跑 g1f | stderr "跳过无法解析的 bad.py"，门禁 4 项 PASS，RC=0 |
| 门禁失败（故障注入） | 导入 prep_sc1 模块，把 `run_tool` 对 `tools/query.py def` 注入 rc=1 后调 `main()` | 输出 `GATE-FAIL: ...`；**rc=3**；stderr 含 `PREP_GATE_FAIL`；codegraph.json、tools/query.py、tools/ 目录全部删除 |

故障注入为对交付脚本原样加载后仅替换工具执行结果的测试，脚本文件本身未改动。

## 6. 交付物清单（anolis）

- `/home/pan-ding/campaign-sc/scripts/prep_sc1.py`
- `/home/pan-ding/campaign-sc/sc-lib.json`（`python3 -m json.tool` 校验通过；四条 technique 的 id=g1f/g2f/g3f/g7f，prompt 逐字采用任务给定文本）
- `/home/pan-ding/campaign-sc/scripts/PREP_VALIDATION.md`（本文档）

## 结论

四臂工具链在真实 sc-sqlparse-bugfix 工作区上生成并全子命令跑通；题目点名的四个关键检查点全部达成；
空项目不误伤；门禁失败路径经故障注入证实会删工件、打 PREP_GATE_FAIL、退 3。
唯一与任务描述的偏差：工作区中不存在小写 `strip_comments` 符号，`def` 查询以"忽略大小写/下划线"
模糊回退命中 `StripCommentsFilter`（sqlparse/filters/others.py:14），行为已在工具输出中显式标注。
