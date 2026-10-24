#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""prep_sc1.py — 为 SC1 波修复臂建造辅助工具链（在目标工作区内生成工件）。

用法:
    python3 prep_sc1.py <workdir> <arm>

arm:
    g1f  生成 codegraph.json + tools/query.py    子命令: def/calls/calledby/file
    g2f  生成 codeindex.tsv   + tools/lookup.py  子命令: 子串模糊查
    g3f  生成 tools/ast_tools.py                 子命令: inspect/body/replace
    g7f  生成 tools/lsp.py                       子命令: def/refs/hover

扫描: workdir 内全部 *.py（跳过隐藏目录、.tbench-testing、tests），用 ast
抽取符号（模块/类/函数/方法，含签名、文件、起止行、所属类）与调用边
（函数体内 Name/Attribute 调用尽力解析到已索引符号）。

门禁: 生成后对该 workdir 实际运行每个工具的每个子命令（选真实存在的符号；
空项目则退化为“优雅未命中 + 合成样例”检查）。任一失败 → 删除本次生成的
全部工件，stderr 打印 PREP_GATE_FAIL，退出码 3。绝不交付坏工件。
"""

import ast
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

ARMS = ("g1f", "g2f", "g3f", "g7f")
SKIP_DIRNAMES = {"tests", ".tbench-testing"}
SCOPE_TYPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
LOC_RE = re.compile(r"^\S+\.py:\d+")


# ================================================================ 扫描核心

def iter_py_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in sorted(dirnames)
                       if not d.startswith(".") and d not in SKIP_DIRNAMES]
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


def module_name_for(rel):
    p = rel[:-3] if rel.endswith(".py") else rel
    parts = [seg for seg in p.split("/") if seg]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else rel


def expr_str(node):
    if node is None:
        return ""
    if hasattr(ast, "unparse"):
        try:
            return ast.unparse(node)
        except Exception:
            pass
    return _fallback_expr(node)


def _fallback_expr(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        base = _fallback_expr(node.value)
        return (base + "." + node.attr) if base else node.attr
    if isinstance(node, ast.Constant):
        try:
            return repr(node.value)
        except Exception:
            return "?"
    if isinstance(node, ast.Call):
        return "%s(%s)" % (_fallback_expr(node.func) or "?",
                           ", ".join(_fallback_expr(a) for a in node.args))
    if isinstance(node, ast.Tuple):
        inner = ", ".join(_fallback_expr(e) for e in node.elts)
        return "(%s%s)" % (inner, "," if len(node.elts) == 1 else "")
    if isinstance(node, ast.List):
        return "[%s]" % ", ".join(_fallback_expr(e) for e in node.elts)
    if isinstance(node, ast.Set):
        return "{%s}" % ", ".join(_fallback_expr(e) for e in node.elts)
    if isinstance(node, ast.Dict):
        return "{%s}" % ", ".join(
            "%s: %s" % (_fallback_expr(k), _fallback_expr(v))
            for k, v in zip(node.keys, node.values))
    if isinstance(node, ast.Starred):
        return "*" + _fallback_expr(node.value)
    if isinstance(node, ast.UnaryOp):
        return "%s %s" % (type(node.op).__name__, _fallback_expr(node.operand))
    if isinstance(node, ast.BinOp):
        return "%s %s %s" % (_fallback_expr(node.left), type(node.op).__name__,
                             _fallback_expr(node.right))
    return "..."


def func_signature(node):
    a = node.args
    parts = []
    pos = list(getattr(a, "posonlyargs", None) or []) + list(a.args or [])
    defaults = list(a.defaults or [])
    names = [p.arg for p in pos]
    anns = [expr_str(p.annotation) for p in pos]
    first_default = len(names) - len(defaults)
    for i, nm in enumerate(names):
        piece = nm
        if anns[i]:
            piece += ": " + anns[i]
        if i >= first_default:
            piece += (" = " if anns[i] else "=") + (
                expr_str(defaults[i - first_default]) or "?")
        parts.append(piece)
    if getattr(a, "posonlyargs", None):
        parts.insert(len(a.posonlyargs), "/")
    if a.vararg:
        piece = "*" + a.vararg.arg
        ann = expr_str(a.vararg.annotation)
        if ann:
            piece += ": " + ann
        parts.append(piece)
    elif a.kwonlyargs:
        parts.append("*")
    for p, dflt in zip(a.kwonlyargs or [], a.kw_defaults or []):
        piece = p.arg
        ann = expr_str(p.annotation)
        if ann:
            piece += ": " + ann
        if dflt is not None:
            piece += (" = " if ann else "=") + (expr_str(dflt) or "?")
        parts.append(piece)
    if a.kwarg:
        piece = "**" + a.kwarg.arg
        ann = expr_str(a.kwarg.annotation)
        if ann:
            piece += ": " + ann
        parts.append(piece)
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    sig = "%s %s(%s)" % (prefix, node.name, ", ".join(parts))
    ret = expr_str(node.returns)
    if ret:
        sig += " -> " + ret
    return sig


def class_signature(node):
    bases = [expr_str(b) or "?" for b in node.bases]
    for kw in node.keywords:
        bases.append("%s=%s" % (kw.arg or "**", expr_str(kw.value) or "?"))
    if bases:
        return "class %s(%s)" % (node.name, ", ".join(bases))
    return "class %s" % node.name


def signature_of(node):
    if isinstance(node, ast.ClassDef):
        return class_signature(node)
    return func_signature(node)


def scope_start(node):
    decorators = getattr(node, "decorator_list", None) or []
    if decorators:
        return min([node.lineno] + [d.lineno for d in decorators])
    return node.lineno


def scope_end(node):
    end = getattr(node, "end_lineno", None)
    return end if end else node.lineno


def iter_symbols(body, prefix, parent, out):
    """递归收集 (ast节点, qualname, 所属类名, kind)。"""
    for node in body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            qual = prefix + node.name
            kind = "method" if parent else "function"
            out.append((node, qual, parent or "", kind))
            iter_symbols(node.body, qual + ".", None, out)
        elif isinstance(node, ast.ClassDef):
            qual = prefix + node.name
            out.append((node, qual, parent or "", "class"))
            iter_symbols(node.body, qual + ".", node.name, out)


def iter_calls(scope_node):
    """scope_node 体内（不含嵌套作用域）的调用点。"""
    for child in ast.iter_child_nodes(scope_node):
        if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef,
                              ast.ClassDef, ast.Lambda)):
            continue
        if isinstance(child, ast.Call):
            yield child
        for sub in iter_calls(child):
            yield sub


def call_target_name(call):
    func = call.func
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def scan_workdir(root):
    """返回 (nodes, edges, per_file)。nodes/edges 可直接序列化。"""
    nodes = []
    edges = []
    per_file = []
    for path in iter_py_files(root):
        rel = os.path.relpath(path, root).replace(os.sep, "/")
        try:
            with open(path, "rb") as fh:
                src = fh.read().decode("utf-8", errors="replace")
            tree = ast.parse(src, filename=rel)
        except (SyntaxError, ValueError, OSError) as exc:
            sys.stderr.write("prep_sc1: 跳过无法解析的 %s: %s\n" % (rel, exc))
            continue
        nlines = len(src.splitlines())
        mod = module_name_for(rel)
        info = {"file": rel, "module": mod, "nlines": nlines, "tree": tree}
        per_file.append(info)
        nodes.append({
            "name": mod.split(".")[-1] if mod else rel,
            "qualname": mod,
            "kind": "module",
            "signature": "module %s" % mod,
            "file": rel,
            "start_line": 1,
            "end_line": max(1, nlines),
            "parent": "",
        })
        symbols = []
        iter_symbols(tree.body, "", None, symbols)
        info["symbols"] = symbols
        for node, qual, parent, kind in symbols:
            nodes.append({
                "name": node.name,
                "qualname": qual,
                "kind": kind,
                "signature": signature_of(node),
                "file": rel,
                "start_line": scope_start(node),
                "end_line": scope_end(node),
                "parent": parent,
            })
    known_names = set(n["name"] for n in nodes if n["kind"] != "module")
    seen = set()
    for info in per_file:
        rel = info["file"]

        def add_calls(scope_node, caller_qual, rel=rel):
            for call in iter_calls(scope_node):
                target = call_target_name(call)
                if target and target in known_names:
                    key = (caller_qual, target, rel, call.lineno)
                    if key not in seen:
                        seen.add(key)
                        edges.append({"caller": caller_qual, "callee": target,
                                      "file": rel, "line": call.lineno})

        for stmt in info["tree"].body:
            if isinstance(stmt, SCOPE_TYPES):
                continue
            add_calls(stmt, info["module"])
        for node, qual, parent, kind in info["symbols"]:
            add_calls(node, qual)
    return nodes, edges, per_file


# ============================================================ 生成工件

SIG_BLOCK = '''
def expr_str(node):
    if node is None:
        return ""
    try:
        return ast.unparse(node)
    except Exception:
        return "..."


def func_signature(node):
    a = node.args
    parts = []
    pos = list(getattr(a, "posonlyargs", None) or []) + list(a.args or [])
    defaults = list(a.defaults or [])
    names = [p.arg for p in pos]
    anns = [expr_str(p.annotation) for p in pos]
    first_default = len(names) - len(defaults)
    for i, nm in enumerate(names):
        piece = nm
        if anns[i]:
            piece += ": " + anns[i]
        if i >= first_default:
            piece += (" = " if anns[i] else "=") + (
                expr_str(defaults[i - first_default]) or "?")
        parts.append(piece)
    if getattr(a, "posonlyargs", None):
        parts.insert(len(a.posonlyargs), "/")
    if a.vararg:
        piece = "*" + a.vararg.arg
        ann = expr_str(a.vararg.annotation)
        if ann:
            piece += ": " + ann
        parts.append(piece)
    elif a.kwonlyargs:
        parts.append("*")
    for p, dflt in zip(a.kwonlyargs or [], a.kw_defaults or []):
        piece = p.arg
        ann = expr_str(p.annotation)
        if ann:
            piece += ": " + ann
        if dflt is not None:
            piece += (" = " if ann else "=") + (expr_str(dflt) or "?")
        parts.append(piece)
    if a.kwarg:
        piece = "**" + a.kwarg.arg
        ann = expr_str(a.kwarg.annotation)
        if ann:
            piece += ": " + ann
        parts.append(piece)
    prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    sig = "%s %s(%s)" % (prefix, node.name, ", ".join(parts))
    ret = expr_str(node.returns)
    if ret:
        sig += " -> " + ret
    return sig


def class_signature(node):
    bases = [expr_str(b) or "?" for b in node.bases]
    for kw in node.keywords:
        bases.append("%s=%s" % (kw.arg or "**", expr_str(kw.value) or "?"))
    if bases:
        return "class %s(%s)" % (node.name, ", ".join(bases))
    return "class %s" % node.name


def signature_of(node):
    if isinstance(node, ast.ClassDef):
        return class_signature(node)
    return func_signature(node)


def scope_start(node):
    decorators = getattr(node, "decorator_list", None) or []
    if decorators:
        return min([node.lineno] + [d.lineno for d in decorators])
    return node.lineno


def scope_end(node):
    end = getattr(node, "end_lineno", None)
    return end if end else node.lineno
'''


def _norm(s):
    return s.replace("_", "").lower()


QUERY_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""codegraph 查询器 — 读取预生成的 codegraph.json（符号与调用关系索引）。

用法:
  python3 tools/query.py def <符号名>        # 查定义位置（文件:行号）
  python3 tools/query.py calls <函数名>      # 它调用了谁
  python3 tools/query.py calledby <函数名>   # 谁调用了它
  python3 tools/query.py file <文件名>       # 该文件的符号清单
"""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
GRAPH_PATH = os.path.join(ROOT, "codegraph.json")


def _norm(s):
    return s.replace("_", "").lower()


def load_graph():
    try:
        with open(GRAPH_PATH, encoding="utf-8") as fh:
            return json.load(fh)
    except OSError as exc:
        sys.stderr.write("query.py: 无法读取 %s: %s\n" % (GRAPH_PATH, exc))
        sys.exit(2)


def match_symbol(node, name):
    return (node.get("name") == name or node.get("qualname") == name
            or node.get("qualname", "").endswith("." + name))


def nodes_for(graph, name):
    return [n for n in graph.get("nodes", []) if match_symbol(n, name)]


def loc(node):
    return "%s:%d" % (node["file"], node["start_line"])


def print_nodes(nodes, note=None):
    if note:
        print(note)
    for n in nodes:
        print("%s  [%s]  %s" % (loc(n), n["kind"], n["signature"]))


def cmd_def(graph, name):
    hits = [n for n in nodes_for(graph, name) if n["kind"] != "module"]
    if hits:
        print_nodes(sorted(hits, key=lambda n: (n["file"], n["start_line"])))
        return
    # 模糊回退: 忽略大小写与下划线（strip_comments -> StripCommentsFilter）
    qn = _norm(name)
    if len(qn) >= 4:
        fuzzy = {}
        for n in graph.get("nodes", []):
            if n["kind"] == "module":
                continue
            nn = _norm(n["name"])
            if nn == qn or nn.startswith(qn) or qn in nn:
                fuzzy[n["qualname"]] = n
        if fuzzy:
            ranked = sorted(fuzzy.values(),
                            key=lambda n: (len(n["name"]), n["qualname"]))
            print_nodes(ranked[:20],
                        "（未精确命中 %s，以下为忽略大小写/下划线的模糊结果）"
                        % name)
            return
    print("未找到符号: %s" % name)


def cmd_calls(graph, name):
    callers = set(n["qualname"] for n in nodes_for(graph, name))
    callees = {}
    seen_edge = False
    for e in graph.get("edges", []):
        if e["caller"] in callers:
            seen_edge = True
            for n in nodes_for(graph, e["callee"]):
                callees[(n["file"], n["start_line"], n["qualname"])] = True
    if not seen_edge:
        print("索引中没有 %s 发起的调用" % name)
        return
    if not callees:
        print("%s 的调用目标均未能解析到已索引符号" % name)
        return
    for f, ln, qual in sorted(callees):
        print("%s:%d  %s" % (f, ln, qual))


def cmd_calledby(graph, name):
    targets = set(n["name"] for n in nodes_for(graph, name))
    targets.add(name)
    callers = {}
    seen_edge = False
    for e in graph.get("edges", []):
        if e["callee"] in targets:
            seen_edge = True
            for n in nodes_for(graph, e["caller"]):
                callers[(n["file"], n["start_line"], n["qualname"])] = True
    if not seen_edge:
        print("索引中没有指向 %s 的调用" % name)
        return
    for f, ln, qual in sorted(callers):
        print("%s:%d  %s" % (f, ln, qual))


def cmd_file(graph, name):
    norm = name.replace("\\", "/").strip("/")
    hits = []
    for n in graph.get("nodes", []):
        f = n["file"]
        if f == norm or os.path.basename(f) == norm or f.endswith("/" + norm):
            hits.append(n)
    if not hits:
        print("未找到文件: %s（可试用相对路径或文件名）" % name)
        return
    hits.sort(key=lambda n: (n["file"], n["start_line"]))
    cur = None
    for n in hits:
        if n["file"] != cur:
            cur = n["file"]
            print("== %s ==" % cur)
        print("  L%d-L%d  [%s]  %s  %s" % (
            n["start_line"], n["end_line"], n["kind"], n["qualname"],
            n["signature"]))


def main(argv):
    if len(argv) < 2:
        sys.stderr.write(__doc__)
        return 2
    cmd, arg = argv[0], argv[1]
    graph = load_graph()
    if cmd == "def":
        cmd_def(graph, arg)
    elif cmd == "calls":
        cmd_calls(graph, arg)
    elif cmd == "calledby":
        cmd_calledby(graph, arg)
    elif cmd == "file":
        cmd_file(graph, arg)
    else:
        sys.stderr.write("未知子命令: %s\n%s" % (cmd, __doc__))
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''


LOOKUP_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""符号索引模糊查询 — 在 codeindex.tsv 中按子串查符号。

用法:
  python3 tools/lookup.py <子串>
"""
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
TSV_PATH = os.path.join(ROOT, "codeindex.tsv")
LIMIT = 200


def read_rows(sub, case_insensitive):
    rows = []
    with open(TSV_PATH, encoding="utf-8") as fh:
        fh.readline()  # 表头
        for line in fh:
            parts = line.rstrip("\n").split("\t")
            if len(parts) != 7:
                continue
            name, kind, sig, fname, start, end, parent = parts
            hit = (sub.lower() in name.lower()) if case_insensitive \
                else (sub in name)
            if hit:
                rows.append((fname, int(start), int(end), kind, name, sig,
                             parent))
    return rows


def main(argv):
    if len(argv) != 1:
        sys.stderr.write(__doc__)
        return 2
    sub = argv[0]
    if not os.path.exists(TSV_PATH):
        sys.stderr.write("lookup.py: 缺少 %s\n" % TSV_PATH)
        return 2
    rows = read_rows(sub, case_insensitive=False)
    note = ""
    if not rows:
        rows = read_rows(sub, case_insensitive=True)
        if rows:
            note = "（区分大小写无命中，以下为忽略大小写的结果）"
    if not rows:
        print("未找到名称包含 %r 的符号" % sub)
        return 0
    rows.sort(key=lambda r: (r[0], r[1]))
    if note:
        print(note)
    for fname, start, end, kind, name, sig, parent in rows[:LIMIT]:
        scope = ("  in %s" % parent) if parent else ""
        print("%s:%d  [%s] %s%s  L%d-L%d  %s" % (
            fname, start, kind, name, scope, start, end, sig))
    if len(rows) > LIMIT:
        print("... 命中 %d 条，仅显示前 %d 条" % (len(rows), LIMIT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''


AST_TOOLS_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""AST 结构编辑 — inspect / body / replace。

用法:
  python3 tools/ast_tools.py inspect <文件>
  python3 tools/ast_tools.py body <文件> <符号>
  python3 tools/ast_tools.py replace <文件> <符号> <新源码文件>
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# ==== 签名/行号渲染（共享实现） ====
{{SIG_BLOCK}}


def resolve_path(arg):
    if os.path.exists(arg):
        return arg
    cand = os.path.join(ROOT, arg)
    if os.path.exists(cand):
        return cand
    return arg


def read_source(path):
    with open(path, "rb") as fh:
        data = fh.read()
    return data, data.decode("utf-8", errors="replace")


def parse_source(src, path):
    try:
        return ast.parse(src, filename=path)
    except SyntaxError as exc:
        sys.stderr.write("ast_tools.py: %s 语法错误: %s\n" % (path, exc))
        sys.exit(2)


def find_symbol(tree, name):
    candidates = []
    stack = [(tree.body, "")]
    while stack:
        body, prefix = stack.pop()
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                qual = prefix + node.name
                if node.name == name or qual == name or qual.endswith(
                        "." + name):
                    candidates.append((node, qual))
                stack.append((node.body, qual + "."))
    for node, qual in candidates:
        if qual == name:
            return node
    return candidates[0][0] if candidates else None


def cmd_inspect(path):
    data, src = read_source(path)
    tree = parse_source(src, path)
    print("%s  (%d 行)" % (path, len(src.splitlines())))
    entries = []
    stack = [(tree.body, "")]
    while stack:
        body, prefix = stack.pop()
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                qual = prefix + node.name
                if isinstance(node, ast.ClassDef):
                    kind = "class"
                elif isinstance(node, ast.AsyncFunctionDef):
                    kind = "async def"
                else:
                    kind = "def"
                entries.append((scope_start(node), scope_end(node),
                                len(qual.split(".")) - 1, kind,
                                signature_of(node), qual))
                stack.append((node.body, qual + "."))
    entries.sort()
    for start, end, depth, kind, sig, qual in entries:
        print("%sL%d-L%d  %-9s  %s" % ("  " * depth, start, end, kind, sig))
    if not entries:
        print("  (未发现类/函数定义)")
    return 0


def cmd_body(path, name):
    data, src = read_source(path)
    tree = parse_source(src, path)
    node = find_symbol(tree, name)
    if node is None:
        print("未找到符号: %s" % name)
        return 1
    lines = src.splitlines()
    start, end = scope_start(node), scope_end(node)
    sys.stdout.write("\n".join(lines[start - 1:end]) + "\n")
    return 0


def cmd_replace(path, name, newsrc_path):
    if not os.path.exists(newsrc_path):
        sys.stderr.write("ast_tools.py: 新源码文件不存在: %s\n" % newsrc_path)
        return 2
    data, src = read_source(path)
    tree = parse_source(src, path)
    node = find_symbol(tree, name)
    if node is None:
        print("未找到符号: %s" % name)
        return 1
    start, end = scope_start(node), scope_end(node)
    with open(newsrc_path, "rb") as fh:
        new_bytes = fh.read()
    lines = data.splitlines(keepends=True)
    old_block = b"".join(lines[start - 1:end])
    if old_block.endswith((b"\n", b"\r")) and not new_bytes.endswith(
            (b"\n", b"\r")):
        new_bytes += b"\n"
    out = b"".join(lines[:start - 1]) + new_bytes + b"".join(lines[end:])
    with open(path, "wb") as fh:
        fh.write(out)
    print("已替换 %s :: %s  (L%d-L%d, 旧 %d 字节 -> 新 %d 字节)" % (
        path, name, start, end, len(old_block), len(new_bytes)))
    return 0


def main(argv):
    if not argv:
        sys.stderr.write(__doc__)
        return 2
    cmd = argv[0]
    if cmd == "inspect" and len(argv) == 2:
        return cmd_inspect(resolve_path(argv[1]))
    if cmd == "body" and len(argv) == 3:
        return cmd_body(resolve_path(argv[1]), argv[2])
    if cmd == "replace" and len(argv) == 4:
        return cmd_replace(resolve_path(argv[1]), argv[2], argv[3])
    sys.stderr.write(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''


LSP_PY = r'''#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""近似 LSP 查询 — 基于全库 AST + 引用扫描（每次运行实时扫描）。

用法:
  python3 tools/lsp.py def <符号>      # 跳转定义
  python3 tools/lsp.py refs <符号>     # 全库引用点（文件:行号+上下文行）
  python3 tools/lsp.py hover <符号>    # 签名+docstring 摘要
"""
import ast
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SKIP_DIRNAMES = {"tests", ".tbench-testing"}

# ==== 签名/行号渲染（共享实现） ====
{{SIG_BLOCK}}


def _norm(s):
    return s.replace("_", "").lower()


def iter_py(root):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in sorted(dirnames)
                       if not d.startswith(".") and d not in SKIP_DIRNAMES]
        for fn in sorted(filenames):
            if fn.endswith(".py"):
                yield os.path.join(dirpath, fn)


def module_name_for(rel):
    p = rel[:-3] if rel.endswith(".py") else rel
    parts = [seg for seg in p.split("/") if seg]
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts) if parts else rel


def load_files():
    files = []
    for path in iter_py(ROOT):
        rel = os.path.relpath(path, ROOT).replace(os.sep, "/")
        try:
            with open(path, encoding="utf-8", errors="replace") as fh:
                src = fh.read()
            tree = ast.parse(src, filename=rel)
        except (SyntaxError, ValueError, OSError):
            continue
        files.append({"rel": rel, "src": src, "lines": src.splitlines(),
                      "tree": tree, "module": module_name_for(rel)})
    return files


def _match(node, qual, name):
    return node.name == name or qual == name or qual.endswith("." + name)


def find_defs_exact(files, name):
    out = []
    stack = [(f, f["tree"].body, "") for f in files]
    while stack:
        f, body, prefix = stack.pop()
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                 ast.ClassDef)):
                qual = prefix + node.name
                if _match(node, qual, name):
                    out.append((f, node))
                stack.append((f, node.body, qual + "."))
    out.sort(key=lambda t: (t[0]["rel"], scope_start(t[1])))
    return out


def find_defs(files, name):
    """精确优先；未命中时忽略大小写/下划线做前缀模糊。"""
    exact = find_defs_exact(files, name)
    if exact:
        return exact, False
    qn = _norm(name)
    if len(qn) >= 4:
        names = set()
        stack = [(f["tree"].body, "") for f in files]
        while stack:
            body, prefix = stack.pop()
            for node in body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef,
                                     ast.ClassDef)):
                    qual = prefix + node.name
                    nn = _norm(node.name)
                    if nn == qn or nn.startswith(qn) or qn in nn:
                        names.add(node.name)
                    stack.append((node.body, qual + "."))
        out = []
        for nm in names:
            out.extend(find_defs_exact(files, nm))
        out.sort(key=lambda t: (t[0]["rel"], scope_start(t[1])))
        if out:
            return out, True
    return [], False


def kind_of(node):
    if isinstance(node, ast.ClassDef):
        return "class"
    if isinstance(node, ast.AsyncFunctionDef):
        return "async def"
    return "def"


def cmd_def(files, name):
    defs, fuzzy = find_defs(files, name)
    if not defs:
        print("未找到定义: %s" % name)
        return 0
    if fuzzy:
        print("（未精确命中 %s，以下为忽略大小写/下划线的模糊结果）" % name)
    for f, node in defs:
        print("%s:%d  [%s]  %s" % (f["rel"], scope_start(node), kind_of(node),
                                   signature_of(node)))
    return 0


def cmd_refs(files, name):
    defs, _fuzzy = find_defs(files, name)
    def_modules = set(f["module"] for f, _n in defs)
    def_lines = set((f["rel"], scope_start(n)) for f, n in defs)
    hits = set()
    for f in files:
        rel = f["rel"]
        for node in ast.walk(f["tree"]):
            if isinstance(node, ast.Name) and node.id == name:
                hits.add((rel, node.lineno))
            elif isinstance(node, ast.Attribute) and node.attr == name:
                hits.add((rel, node.lineno))
            elif isinstance(node, ast.ImportFrom):
                if node.module in def_modules:
                    for alias in node.names:
                        if alias.name == "*" or alias.name == name:
                            hits.add((rel, node.lineno))
                            break
    hits = set((rel, ln) for rel, ln in hits if (rel, ln) not in def_lines)
    if not hits:
        print("全库未发现 %s 的引用" % name)
        return 0
    lines_map = dict((f["rel"], f["lines"]) for f in files)
    for rel, ln in sorted(hits):
        content = ""
        lst = lines_map.get(rel, [])
        if 0 < ln <= len(lst):
            content = lst[ln - 1].strip()
        print("%s:%d: %s" % (rel, ln, content))
    print("共 %d 处引用" % len(hits))
    return 0


def cmd_hover(files, name):
    defs, fuzzy = find_defs(files, name)
    if not defs:
        print("未找到定义: %s" % name)
        return 0
    if fuzzy:
        print("（未精确命中 %s，以下为忽略大小写/下划线的模糊结果）" % name)
    f, node = defs[0]
    print("%s:%d  [%s]" % (f["rel"], scope_start(node), kind_of(node)))
    print(signature_of(node))
    doc = ast.get_docstring(node)
    if doc:
        doc = doc.strip()
        if len(doc) > 400:
            doc = doc[:400] + "..."
        print(doc)
    else:
        print("(无 docstring)")
    if len(defs) > 1:
        others = ", ".join("%s:%d" % (ff["rel"], scope_start(nn))
                           for ff, nn in defs[1:6])
        print("(另有定义: %s%s)" % (others, " 等" if len(defs) > 6 else ""))
    return 0


def main(argv):
    if len(argv) != 2:
        sys.stderr.write(__doc__)
        return 2
    cmd, name = argv
    files = load_files()
    if cmd == "def":
        return cmd_def(files, name)
    if cmd == "refs":
        return cmd_refs(files, name)
    if cmd == "hover":
        return cmd_hover(files, name)
    sys.stderr.write("未知子命令: %s\n%s" % (cmd, __doc__))
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
'''


def generate(arm, root, nodes, edges, per_file):
    tools_dir = os.path.join(root, "tools")
    created = []

    def reg(path, text):
        write_text(path, text)
        created.append(path)

    if arm == "g1f":
        graph = {
            "meta": {
                "arm": arm,
                "root": os.path.abspath(root),
                "generated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
                "files": len(per_file),
                "symbols": len(nodes),
                "call_edges": len(edges),
            },
            "nodes": nodes,
            "edges": edges,
        }
        reg(os.path.join(root, "codegraph.json"),
            json.dumps(graph, ensure_ascii=False, indent=1) + "\n")
        reg(os.path.join(tools_dir, "query.py"), QUERY_PY)
    elif arm == "g2f":
        rows = ["\t".join(("name", "kind", "signature", "file", "start_line",
                           "end_line", "parent"))]
        for n in nodes:
            rows.append("\t".join((n["name"], n["kind"], n["signature"],
                                   n["file"], str(n["start_line"]),
                                   str(n["end_line"]), n["parent"])))
        reg(os.path.join(root, "codeindex.tsv"), "\n".join(rows) + "\n")
        reg(os.path.join(tools_dir, "lookup.py"), LOOKUP_PY)
    elif arm == "g3f":
        reg(os.path.join(tools_dir, "ast_tools.py"), AST_TOOLS_PY)
    elif arm == "g7f":
        reg(os.path.join(tools_dir, "lsp.py"), LSP_PY)
    return created, tools_dir


def write_text(path, text):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)
    return path


def finalize_templates():
    global AST_TOOLS_PY, LSP_PY
    AST_TOOLS_PY = AST_TOOLS_PY.replace("{{SIG_BLOCK}}", SIG_BLOCK)
    LSP_PY = LSP_PY.replace("{{SIG_BLOCK}}", SIG_BLOCK)


# ================================================================ 门禁

def run_tool(root, args):
    cmd = [sys.executable or "python3"] + args
    proc = subprocess.run(cmd, cwd=root, stdout=subprocess.PIPE,
                          stderr=subprocess.PIPE)
    return (proc.returncode, proc.stdout.decode("utf-8", "replace"),
            proc.stderr.decode("utf-8", "replace"))


def has_loc(out):
    return any(LOC_RE.match(line.strip()) for line in out.splitlines())


def brief(text, limit=160):
    text = " ".join(text.split())
    return text[:limit] + ("..." if len(text) > limit else "")


def gate(arm, root, nodes, edges):
    log = []
    problems = []

    def check(label, ok, out="", err="", rc=0):
        detail = "rc=%d out=%r err=%r" % (rc, brief(out), brief(err))
        log.append("%s %s | %s" % ("PASS" if ok else "FAIL", label, detail))
        if not ok:
            problems.append(label)

    funcs = [n for n in nodes if n["kind"] in ("function", "method")]
    classes = [n for n in nodes if n["kind"] == "class"]
    sample = None
    for n in funcs + classes:
        if len(n["name"]) >= 2 and n["name"].isidentifier():
            sample = n
            break

    if arm == "g1f":
        name = sample["name"] if sample else "zzz_none"
        rc, out, err = run_tool(root, ["tools/query.py", "def", name])
        if sample:
            expect = "%s:%d" % (sample["file"], sample["start_line"])
            check("query.py def %s" % name, rc == 0 and expect in out,
                  out, err, rc)
        else:
            check("query.py def %s (空索引)" % name, rc == 0, out, err, rc)
        edge_callers = set(e["caller"] for e in edges)
        edge_callees = set(e["callee"] for e in edges)
        pick = None
        for n in funcs:
            if n["qualname"] in edge_callers:
                pick = n
                break
        if pick is None and sample is not None:
            pick = sample
        cname = pick["name"] if pick else "zzz_none"
        rc, out, err = run_tool(root, ["tools/query.py", "calls", cname])
        if pick is not None and edge_callers:
            check("query.py calls %s" % cname, rc == 0 and has_loc(out),
                  out, err, rc)
        else:
            check("query.py calls %s (无出边样本)" % cname, rc == 0,
                  out, err, rc)
        pick = None
        for n in funcs + classes:
            if n["name"] in edge_callees:
                pick = n
                break
        if pick is None and sample is not None:
            pick = sample
        bname = pick["name"] if pick else "zzz_none"
        rc, out, err = run_tool(root, ["tools/query.py", "calledby", bname])
        if pick is not None and edge_callees:
            check("query.py calledby %s" % bname, rc == 0 and has_loc(out),
                  out, err, rc)
        else:
            check("query.py calledby %s (无入边样本)" % bname, rc == 0,
                  out, err, rc)
        fname = os.path.basename(sample["file"]) if sample else "zzz_none.py"
        rc, out, err = run_tool(root, ["tools/query.py", "file", fname])
        if sample:
            check("query.py file %s" % fname,
                  rc == 0 and fname in out and sample["name"] in out,
                  out, err, rc)
        else:
            check("query.py file (空索引)", rc == 0, out, err, rc)

    elif arm == "g2f":
        if sample:
            sub = sample["name"][:4]
            expect = "%s:%d" % (sample["file"], sample["start_line"])
            rc, out, err = run_tool(root, ["tools/lookup.py", sub])
            check("lookup.py %s" % sub,
                  rc == 0 and expect in out and sample["name"] in out,
                  out, err, rc)
        else:
            rc, out, err = run_tool(root, ["tools/lookup.py", "zzz"])
            check("lookup.py zzz (空索引)", rc == 0, out, err, rc)

    elif arm == "g3f":
        tmpdir = tempfile.mkdtemp(prefix="prep_gate_g3f_")
        try:
            target = None
            if sample is not None:
                src_path = os.path.join(root, sample["file"])
                with open(src_path, "rb") as fh:
                    data = fh.read()
                file_syms = [n for n in nodes
                             if n["file"] == sample["file"]
                             and n["kind"] != "module"]
                for n in file_syms:
                    if sum(1 for m in file_syms
                           if m["name"] == n["name"]) == 1:
                        target = n
                        break
                if target is None:
                    target = sample
            else:
                data = (b"def gate_fn(x):\n"
                        b"    return x + 1\n"
                        b"\n"
                        b"\n"
                        b"class GateCls(object):\n"
                        b"    def m(self):\n"
                        b"        return gate_fn(1)\n")
            test_path = os.path.join(tmpdir, "gate_file.py")
            with open(test_path, "wb") as fh:
                fh.write(data)
            sym = target["name"] if target else "gate_fn"
            s = target["start_line"] if target else 1
            e = target["end_line"] if target else 2

            rc, out, err = run_tool(root, ["tools/ast_tools.py", "inspect",
                                           test_path])
            check("ast_tools.py inspect", rc == 0 and "def" in out,
                  out, err, rc)
            rc, out, err = run_tool(root, ["tools/ast_tools.py", "body",
                                           test_path, sym])
            check("ast_tools.py body %s" % sym, rc == 0 and out.strip() != "",
                  out, err, rc)
            lines = data.splitlines(keepends=True)
            prefix = b"".join(lines[:s - 1])
            block = b"".join(lines[s - 1:e])
            suffix = b"".join(lines[e:])
            marker = b"# prep-gate replace marker\n"
            newsrc = os.path.join(tmpdir, "new.py")
            with open(newsrc, "wb") as fh:
                fh.write(marker + block)
            rc, out, err = run_tool(root, ["tools/ast_tools.py", "replace",
                                           test_path, sym, newsrc])
            with open(test_path, "rb") as fh:
                after = fh.read()
            expected = prefix + marker + block + suffix
            ok = rc == 0 and after == expected and marker in after
            if ok:
                try:
                    ast.parse(after.decode("utf-8", errors="replace"))
                except SyntaxError:
                    ok = False
            check("ast_tools.py replace %s (字节级校验)" % sym, ok,
                  out, err, rc)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    elif arm == "g7f":
        if sample:
            name = sample["name"]
            expect = "%s:%d" % (sample["file"], sample["start_line"])
            rc, out, err = run_tool(root, ["tools/lsp.py", "def", name])
            check("lsp.py def %s" % name, rc == 0 and expect in out,
                  out, err, rc)
            rc, out, err = run_tool(root, ["tools/lsp.py", "refs", name])
            check("lsp.py refs %s" % name, rc == 0, out, err, rc)
            rc, out, err = run_tool(root, ["tools/lsp.py", "hover", name])
            check("lsp.py hover %s" % name, rc == 0 and out.strip() != "",
                  out, err, rc)
        else:
            for sub in ("def", "refs", "hover"):
                rc, out, err = run_tool(root, ["tools/lsp.py", sub,
                                               "zzz_none"])
                check("lsp.py %s zzz_none (空索引)" % sub, rc == 0,
                      out, err, rc)
        tmpdir = tempfile.mkdtemp(prefix="prep_gate_g7f_")
        try:
            os.makedirs(os.path.join(tmpdir, "tools"))
            shutil.copyfile(os.path.join(root, "tools", "lsp.py"),
                            os.path.join(tmpdir, "tools", "lsp.py"))
            with open(os.path.join(tmpdir, "sample.py"), "w",
                      encoding="utf-8", newline="\n") as fh:
                fh.write('"""gate sample"""\n\n\ndef gate_target(a, b=1):\n'
                         '    return a + b\n\n\ndef gate_caller():\n'
                         '    return gate_target(2)\n')
            rc, out, err = run_tool(tmpdir, ["tools/lsp.py", "def",
                                             "gate_target"])
            check("lsp.py def gate_target (合成工程)", rc == 0
                  and "sample.py:4" in out, out, err, rc)
            rc, out, err = run_tool(tmpdir, ["tools/lsp.py", "refs",
                                             "gate_target"])
            check("lsp.py refs gate_target (合成工程)", rc == 0
                  and "sample.py:9" in out, out, err, rc)
            rc, out, err = run_tool(tmpdir, ["tools/lsp.py", "hover",
                                             "gate_target"])
            check("lsp.py hover gate_target (合成工程)", rc == 0
                  and "gate_target" in out, out, err, rc)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    return log, problems


# ================================================================ 主流程

def main(argv):
    if len(argv) != 3:
        sys.stderr.write(__doc__)
        return 2
    workdir, arm = argv[1], argv[2]
    if arm not in ARMS:
        sys.stderr.write("prep_sc1: 未知 arm: %s（可选 %s）\n"
                         % (arm, "/".join(ARMS)))
        return 2
    if not os.path.isdir(workdir):
        sys.stderr.write("prep_sc1: workdir 不存在: %s\n" % workdir)
        return 2
    root = os.path.abspath(workdir)
    tools_existed = os.path.isdir(os.path.join(root, "tools"))

    finalize_templates()
    nodes, edges, per_file = scan_workdir(root)
    created, tools_dir = generate(arm, root, nodes, edges, per_file)

    log, problems = gate(arm, root, nodes, edges)
    for line in log:
        print("  [gate] %s" % line)

    if problems:
        for p in problems:
            sys.stderr.write("GATE-FAIL: %s\n" % p)
        for path in created:
            try:
                os.remove(path)
            except OSError:
                pass
        if not tools_existed and os.path.isdir(tools_dir):
            shutil.rmtree(tools_dir, ignore_errors=True)
        sys.stderr.write("PREP_GATE_FAIL\n")
        return 3

    print("prep_sc1[%s] 完成: %d 文件 / %d 符号 / %d 调用边"
          % (arm, len(per_file), len(nodes), len(edges)))
    for path in created:
        print("  生成 %s (%d bytes)"
              % (os.path.relpath(path, root), os.path.getsize(path)))
    print("prep_sc1[%s] 门禁通过（%d 项检查全部 PASS）" % (arm, len(log)))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
