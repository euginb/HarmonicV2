#!/usr/bin/env python3
"""import_graph.py — граф импортов питон-кода проекта (только stdlib).

По корням (по умолчанию egm, tools, main.py): для каждого модуля внутренние
импорты, imported-by (обратные), LOC; точки входа (их не импортирует никто)
и циклы импорта. Вывод: текст (по умолчанию) или mermaid (--mermaid).
Используется при подготовке контекста (INS-91 §6), в review и рефакторинге.

Использование:
  python tools/import_graph.py [--mermaid] [--roots egm tools main.py] [--out FILE]
Код выхода: 0 — ok; 2 — не найден ни один корень.
"""
import argparse
import ast
import sys
from pathlib import Path


def module_name(root, path):
    rel = path.relative_to(root).with_suffix("")
    parts = list(rel.parts)
    if parts[-1] == "__init__":
        parts = parts[:-1]
    return ".".join(parts)


def collect(root, roots):
    mods = {}
    for r in roots:
        base = root / r
        if r.endswith(".py"):
            if base.is_file():
                mods[module_name(root, base)] = base
        elif base.is_dir():
            for p in sorted(base.rglob("*.py")):
                if "__pycache__" in p.parts:
                    continue
                mods[module_name(root, p)] = p
    return mods


def resolve(name, mods):
    while name:
        if name in mods:
            return name
        name = name.rsplit(".", 1)[0] if "." in name else ""
    return None


def imports_of(path, mod, mods):
    text = path.read_text(encoding="utf-8")
    tree = ast.parse(text, filename=str(path))
    parts = mod.split(".")
    pkg = parts if path.name == "__init__.py" else parts[:-1]
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                r = resolve(a.name, mods)
                if r:
                    out.add(r)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                k = max(len(pkg) - (node.level - 1), 0)
                prefix = ".".join(pkg[:k])
            else:
                prefix = node.module or ""
                r = resolve(node.module, mods) if node.module else None
                if r:
                    out.add(r)
            for a in node.names:
                cand = f"{prefix}.{a.name}" if prefix else a.name
                r = resolve(cand, mods)
                if r:
                    out.add(r)
    out.discard(mod)
    return out, len(text.splitlines())


def find_cycles(adj):
    WHITE, GRAY, BLACK = 0, 1, 2
    color = dict.fromkeys(adj, WHITE)
    cycles = []

    def dfs(m, stack):
        color[m] = GRAY
        stack.append(m)
        for d in sorted(adj[m]):
            if color.get(d) == GRAY and d in stack:
                cycles.append(stack[stack.index(d):] + [d])
            elif color.get(d) == WHITE:
                dfs(d, stack)
        stack.pop()
        color[m] = BLACK

    for m in sorted(adj):
        if color[m] == WHITE:
            dfs(m, [])
    return cycles


def mermaid(mods, imports):
    lines = ["graph LR"]
    for m in sorted(mods):
        lines.append(f'  {m.replace(".", "_")}["{m}"]')
    for m in sorted(imports):
        for d in sorted(imports[m]):
            lines.append(f"  {m.replace('.', '_')} --> {d.replace('.', '_')}")
    return "\n".join(lines)


def main(argv=None):
    ap = argparse.ArgumentParser(description="Граф импортов питон-кода проекта")
    ap.add_argument("--mermaid", action="store_true", help="вывести mermaid-диаграмму")
    ap.add_argument("--roots", nargs="+", default=["egm", "tools", "main.py"],
                    help="корни: папки и/или .py файлы от корня репозитория")
    ap.add_argument("--out", help="записать в файл (по умолчанию stdout)")
    args = ap.parse_args(argv)
    root = Path.cwd()
    mods = collect(root, args.roots)
    if not mods:
        sys.exit(2)
    imports, locs = {}, {}
    for m, p in mods.items():
        imports[m], locs[m] = imports_of(p, m, mods)
    rev = {m: [] for m in mods}
    for m, ds in imports.items():
        for d in ds:
            rev[d].append(m)
    cycles = find_cycles(imports)
    out = []
    if args.mermaid:
        out.append(mermaid(mods, imports))
    else:
        out.append(f"# Импорт-граф — корни: {', '.join(args.roots)}")
        out.append("")
        for m in sorted(mods):
            out.append(f"{m} ({locs[m]} строк)")
            out.append(f"  imports: {', '.join(sorted(imports[m])) or '-'}")
            out.append(f"  imported by: {', '.join(sorted(rev[m])) or '-'}")
        orphans = sorted(m for m in mods if not rev[m])
        out.append("")
        out.append("Точки входа (не импортирует никто): " + (", ".join(orphans) or "-"))
        out.append("Циклы импорта: " + ("; ".join(" -> ".join(c) for c in cycles) or "не найдены"))
    text = "\n".join(out) + "\n"
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        sys.stdout.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
