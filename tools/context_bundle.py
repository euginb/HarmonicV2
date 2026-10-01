#!/usr/bin/env python3
"""Детерминированный сбор контекста для задачи (bundle).

Одинаковый ввод даёт одинаковый вывод: нет времени, сети и случайности;
порядок обхода и пределы зафиксированы. Дополняет правила взаимодействия
с ИИ (README): агент начинает с bundle по ключам задачи, а не с
произвольного обхода репозитория.

Использование:
  python tools/context_bundle.py [--sha <base-sha>] <ключ|путь> [...]

Ключи: Д-##, CP-##, OQ-##, X-##, SPEC-##, CAT-##, INS-## (регистр не важен).
Пути: файлы внутри репозитория, например specs/SPEC-10_PTK_CALC.md.

Коды выхода: 0 — ok; 2 — неверный аргумент; 3 — ключ не найден ни в одном
файле (bundle при этом всё равно выводится).
"""
import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
FLOOR = [  # фиксированный «пол» чтения — начало любого bundle
    "README.md",
    "specs/DECISIONS.md",
    "specs/CODE_PLAN.md",
    "specs/CANCELLED.md",
    "reports/checks.md",
]
SKIP_DIRS = {".git", "out", "__pycache__", ".openlore", "node_modules"}
KEY_RE = re.compile(r"^(Д|CP|OQ|X|SPEC|CAT|INS)-\d+$")
PATH_RE = re.compile(r"^[\w][\w/.\-]*\.(md|json|py|txt)$")
MAX_FILES = 300    # предел файлов от одного ключа
MAX_CHARS = 20000  # предел символов содержимого одного файла


def iter_text_files():
    for p in sorted(ROOT.rglob("*")):
        if p.is_dir():
            continue
        if any(part in SKIP_DIRS for part in p.relative_to(ROOT).parts):
            continue
        yield p


def safe_read(p):
    try:
        return p.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="Детерминированный сбор контекста (bundle).")
    ap.add_argument("--sha", default="UNKNOWN",
                    help="base sha задачи (для заголовка bundle)")
    ap.add_argument("items", nargs="+",
                    help="ключи Д-/CP-/OQ-/X-/SPEC-/CAT-/INS-## и/или пути")
    ns = ap.parse_args(argv)

    keys, paths = [], []
    for item in ns.items:
        norm = item.upper()
        if KEY_RE.match(norm):
            keys.append(norm)
        elif PATH_RE.match(item):
            paths.append(item)
        else:
            ap.error(f"не распознан аргумент: {item} (ожидались ключи или пути)")

    texts = {p.relative_to(ROOT).as_posix(): safe_read(p)
             for p in iter_text_files()}

    selected = [name for name in FLOOR if (ROOT / name).exists()]
    for path_arg in paths:
        if path_arg in texts:
            selected.append(path_arg)
        else:
            print(f"ПРЕДУПРЕЖДЕНИЕ: путь не найден: {path_arg}", file=sys.stderr)
    missing = []
    for key in keys:
        hits = [rel for rel in sorted(texts) if key in texts[rel]]
        if not hits:
            print(f"ПРЕДУПРЕЖДЕНИЕ: ключ не найден: {key}", file=sys.stderr)
            missing.append(key)
            continue
        selected.extend(hits[:MAX_FILES])

    seen, ordered = set(), []
    for rel in selected:  # дедупликация, порядок: пол → пути → ключи
        if rel not in seen:
            seen.add(rel)
            ordered.append(rel)

    out = [
        "# CONTEXT BUNDLE",
        f"# base: {ns.sha}",
        f"# items: {', '.join(ns.items)}",
        f"# files: {len(ordered)}",
        "",
    ]
    for rel in ordered:
        text = texts[rel]
        out.append(f"===== FILE: {rel} =====")
        out.append(text[:MAX_CHARS].rstrip("\n"))
        if len(text) > MAX_CHARS:
            out.append(f"[...обрезано: {len(text)} > {MAX_CHARS} символов...]")
        out.append("===== END FILE =====")
        out.append("")
    out.append("# END BUNDLE")
    sys.stdout.write("\n".join(out) + "\n")
    return 3 if missing else 0


if __name__ == "__main__":
    sys.exit(main())
