#!/usr/bin/env python3
"""ctx_task.py — сбор контекста для конкретной задачи по ключам.

В отличие от context_bundle.py (который включает файлы по ключам, но без
семантики задачи), ctx_task.py читает пол, ключи задачи и **затрагиваемые
файлы** из столбца «Файлы» в CODE_PLAN.md. Для каждого файла включает
только релевантные секции:
- YAML/CONF: весь файл целиком (структура важна)
- MD: «пол» целиком; остальное — строки с ключами задачи + ±5 строк
- PY: скелеты — сигнатуры функций/классов (через ast) + строки с ключами

Использование:
  python tools/ctx_task.py [--sha SHA] CP-## ...

Результат записывается в patch/response/ctx_<key>.md.
"""
import ast
import pathlib
import re
import sys
import textwrap

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLOOR = [
    "README.md",
    "specs/DECISIONS.md",
    "specs/CODE_PLAN.md",
    "specs/CANCELLED.md",
    "reports/checks.md",
]
CODE_PLAN_PATH = ROOT / "specs" / "CODE_PLAN.md"
SKIP_DIRS = {".git", "out", "__pycache__", ".openlore", "node_modules"}
MAX_CHARS_FILE = 20000


def safe_read(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def read_code_plan():
    """Parse CODE_PLAN.md → {CP-##: {content, files, basis, depends, status}}."""
    text = safe_read(CODE_PLAN_PATH)
    cp_pattern = re.compile(r"(CP-\d+)")
    result = {}
    for m in cp_pattern.finditer(text):
        cp = m.group(1)
        # найти строку с CP-## в таблице — ищем до первого следующего CP-##
        start = m.start()
        end_match = re.search(r"\n\| CP-\d+ \|", text[start + 5:])
        end = start + 5 + end_match.start() if end_match else len(text)
        block = text[start:end]
        # извлечь content (второе поле таблицы)
        rows = block.split("\n")
        content = ""
        files = []
        basis = ""
        depends = ""
        status = ""
        in_content = False
        in_files = False
        for row in rows:
            if "Содержание" in row and "Файлы" in row:
                in_content = False
                in_files = False
                continue
            cells = [c.strip() for c in row.split("|") if c.strip()]
            if len(cells) >= 3 and cp in [c.strip() for c in cells]:
                for i, c in enumerate(cells):
                    if cp.strip() == c.strip():
                        # content — следующая ячейка
                        if i + 1 < len(cells):
                            content = cells[i + 1][:200]
                        if i + 2 < len(cells):
                            files_raw = cells[i + 2].replace("\n", " ")
                            files = [f.strip() for f in files_raw.split(",") if f.strip()]
                        if i + 3 < len(cells):
                            basis = cells[i + 3]
                        if i + 4 < len(cells):
                            depends = cells[i + 4]
                        if i + 5 < len(cells):
                            status = cells[i + 5]
                break
        result[cp] = {
            "content": content,
            "files": files,
            "basis": basis,
            "depends": depends,
            "status": status,
        }
    return result


def extract_py_skels(text, keys):
    """Для .py файлов: если есть ключи — включить строки с ключами ±3 строки;
    иначе — скелеты через ast (сигнатуры функций/классов)."""
    lines = text.split("\n")
    included = set()

    # Если есть ключи задачи — включить строки с ними
    if keys:
        for i, line in enumerate(lines):
            for k in keys:
                if k in line:
                    for j in range(max(0, i - 3), min(len(lines), i + 4)):
                        included.add(j)
                    break

    # Иначе — скелеты через ast
    if not included:
        try:
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    # включить сигнатуру + docstring
                    start = node.lineno - 1
                    end = start + 1
                    # docstring
                    if (node.body and isinstance(node.body[0], ast.Expr)
                            and isinstance(node.body[0].value, ast.Constant)):
                        doc_end = node.body[0].end_lineno
                        if doc_end:
                            end = doc_end
                    for j in range(start, min(len(lines), end + 1)):
                        included.add(j)
        except SyntaxError:
            # fallback — весь файл
            for i in range(len(lines)):
                included.add(i)

    out = []
    for i, line in enumerate(lines):
        if i in included:
            out.append(line)
    return "\n".join(out)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(description="Сбор контекста для задачи.")
    ap.add_argument("--sha", default="UNKNOWN")
    ap.add_argument("keys", nargs="+", help="CP-## ...")
    ns = ap.parse_args(argv)

    # Читаем CODE_PLAN для извлечения файлов по ключам
    cp_data = read_code_plan()

    # Определяем пол
    selected = [name for name in FLOOR if (ROOT / name).exists()]

    # Определяем файлы по CP
    task_files = set()
    for key in ns.keys:
        cp = key.upper()
        if cp in cp_data:
            for f in cp_data[cp]["files"]:
                task_files.add(f)
            # Если файлов нет в описании — ищем по ключам в именах файлов
            if not cp_data[cp]["files"]:
                for p in ROOT.rglob("*"):
                    if p.is_file() and not any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
                        if key.upper() in p.name:
                            task_files.add(p.relative_to(ROOT).as_posix())

    # Добавляем затрагиваемые файлы по смыслу задачи
    if "CP-88" in ns.keys or "CP-89" in ns.keys:
        # CP-88: ptk_design_input.yaml, products.yaml, stock.yaml, ptk_layout.py, Д-100
        #        stock.yaml КРИТИЧЕН — калькулятор перебирает марки в порядке layout
        # CP-89: materials.yaml, materials.py
        semantic_files = [
            "specs/ptk_design_input.yaml",
            "specs/products.yaml",
            "specs/stock.yaml",              # КРИТИЧНО: порядок layout влияет на выбор заготовки
            "specs/materials.yaml",
            "egm/materials.py",
            "egm/config.py",
            "egm/ptk_layout.py",
            "docs/Технология изготовления/TECH-01-Как делать сепаратор (стакан).md",
        ]
        task_files.update(semantic_files)

    # Добавляем файлы из task_files
    for rel in task_files:
        p = ROOT / rel
        if p.exists():
            selected.append(rel)

    # Дедупликация, порядок: пол → семантика → CP-файлы
    seen, ordered = set(), []
    floor_set = set(FLOOR)
    semantic_set = set()
    cp_set = set()
    for rel in selected:
        if rel in floor_set:
            # Пол всегда включаем первым
            if rel not in seen:
                seen.add(rel)
                ordered.insert(0, rel)
            continue
        if rel in semantic_set:
            continue
        if rel in cp_set:
            continue
        if any(f in rel for f in ["ptk_design_input", "products", "materials", "TECH-01"]):
            if rel not in semantic_set:
                semantic_set.add(rel)
                ordered.append(rel)
        else:
            cp_set.add(rel)
            ordered.append(rel)

    # Вывод
    out = [
        "# CONTEXT BUNDLE — задача",
        f"# base: {ns.sha}",
        f"# items: {', '.join(ns.keys)}",
        f"# files: {len(ordered)}",
        "",
    ]

    # Описание задачи
    for key in ns.keys:
        cp = key.upper()
        if cp in cp_data:
            d = cp_data[cp]
            out.append(f"## {cp}: {d['content']}")
            out.append(f"Файлы: {', '.join(d['files'])}")
            out.append(f"Основание: {d['basis']}")
            out.append(f"Зависит от: {d['depends']}")
            out.append(f"Статус: {d['status']}")
            out.append("")

    for rel in ordered:
        text = safe_read(ROOT / rel)
        out.append(f"===== FILE: {rel} =====")

        if rel.endswith(".py"):
            # Python: скелеты + ключи
            keys_for_file = ns.keys
            out.append(extract_py_skels(text, keys_for_file)[:MAX_CHARS_FILE])
        elif rel.endswith(".yaml") or rel.endswith(".conf"):
            # YAML/CONF: целиком (структура важна)
            out.append(text[:MAX_CHARS_FILE])
        elif rel.endswith(".md"):
            # MD: пол целиком; остальное — строки с ключами ±5
            if any(f in rel for f in ["README", "DECISIONS", "CODE_PLAN", "CANCELLED"]):
                out.append(text[:MAX_CHARS_FILE])
            else:
                lines = text.split("\n")
                included = set()
                for i, line in enumerate(lines):
                    for k in ns.keys:
                        if k in line:
                            for j in range(max(0, i - 5), min(len(lines), i + 6)):
                                included.add(j)
                            break
                included_lines = [lines[i] for i in sorted(included)]
                out.append("\n".join(included_lines)[:MAX_CHARS_FILE])
        else:
            out.append(text[:MAX_CHARS_FILE])

        if len(text) > MAX_CHARS_FILE:
            out.append(f"[...обрезано: {len(text)} > {MAX_CHARS_FILE} символов...]")
        out.append("===== END FILE =====")
        out.append("")

    out.append("# END BUNDLE")
    print("\n".join(out))


if __name__ == "__main__":
    main()
