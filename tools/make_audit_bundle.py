#!/usr/bin/env python3
"""Полный снимок репозитория для ИИ одним файлом — AUDIT_BUNDLE.md (INS-90 §3).

Снимок: HEAD, список файлов (`git ls-files`, UTF-8 без экранирования путей),
содержимое текстовых файлов. Файлы, которые не удалось прочитать (нет на
диске, не UTF-8), перечисляются в разделе пропусков с причиной — молча не
теряются.
Содержимое файлов можно исключать правилами в синтаксисе .gitignore (Д-27):
базовые правила SKIP_FILES действуют всегда, профили добавляют свои наборы
правил по ключам запуска. Исключённый файл остаётся в списке `## Git tree`,
но его содержимое в снимок не попадает.

Использование:
  python tools/make_audit_bundle.py [--<профиль> ...] [--exclude ПРАВИЛО ...]
                                    [--out ФАЙЛ] [--list]

Без ключей — максимально полный снимок (только базовые правила SKIP_FILES).
Профили и их правила: `--list` или INS-90 §3.3.

Синтаксис правил (как в .gitignore, сопоставление с путём файла от корня):
  docs/             — папка целиком (завершающий «/» — только папка)
  *.pdf             — без «/» внутри: имя на любой глубине
  specs/catalog_*.json, /README.md — с «/»: путь от корня репозитория
  *  ?  [abc]       — в пределах одного сегмента пути; ** — любое число сегментов
  !правило          — вернуть файл, исключённый правилом выше
  Порядок: базовые → профили (в порядке PROFILES) → --exclude (в порядке
  ключей); для файла действует последнее совпавшее правило. Отличие от git:
  `!` возвращает файл и из исключённой папки.

Коды выхода: 0 — ok; 2 — неверный ключ или правило.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(".").resolve()
OUT = ROOT / "AUDIT_BUNDLE.md"

TEXT_EXT = {
    ".md", ".py", ".json", ".toml", ".yaml", ".yml", ".txt",
    ".cfg", ".ini", ".j2", ".jinja", ".jinja2", ".csv", ".tsv",
    ".svg", ".tmpl"
}

"""
 Базовые правила исключения (действуют всегда): правило .gitignore → обоснование
"""
SKIP_FILES = {
    "docs/HG-Series-Catalog_opt.pdf": "Пропущен так-как vendor based, out of scope by review process",
    "docs/RU2359790C1.pdf": "СПОСОБ НАРЕЗАНИЯ ЗУБЧАТОГО ВЕНЦА ЖЕСТКОГО КОЛЕСА ВОЛНОВОЙ ПЕРЕДАЧИ С ПРОМЕЖУТОЧНЫМИ ТЕЛАМИ КАЧЕНИЯ. Патент RU2359790C1",
    "specs/consolidation.md": "Рабочие запросы к ИИ по консолидации информации",
    "specs/repository-review.md": "Рабочие запросы к ИИ по аудиту информации"
}

"""
 Профили исключения: ключ запуска --<имя> → (назначение, {правило: обоснование}).
 Порядок профилей фиксирован и определяет порядок правил (детерминизм).
"""
PROFILES = {
    "reports": (
        "без каталогов производителя и производных БД каталога",
        {
            "docs/Силовой расчет ПТК/": "Теория по силовому расчету ПТК. В.С. Янгулов",
            "docs/cnc_axes_guide.md": "Обозначение осей в станках с ЧПУ",
            "docs/HG-Series-Catalog_opt.md": "справочные HIWIN Linear Guideways — серия HG (каталог G99TE17-1306)",
            "reports/catalog_*.md": "отчет о парсинге docs/HG-Series-Catalog_opt.md",
            "specs/catalog_*.json": "code-first БД каталога, производная от docs/ (egm/catalog.py)",
        },
    ),
    "ins20": (
        "без инструкций к code-first спецификациям",
        {
            "instructions/INS-20*": "инструкция к каталогу HIWIN HG",
        },
    ),
    "ins": (
        "без инструкций к code-first спецификациям",
        {
            "instructions/INS-10*": "инструкция к SPEC-10 (калькулятор ПТК)",
            "instructions/INS-20*": "инструкция к каталогу HIWIN HG",
        },
    ),
    "data": (
        "без производных данных прогона",
        {
            "specs/catalog_*.json": "code-first БД каталога (egm/catalog.py)",
            "specs/ptk_configs.json": "code-first результаты калькулятора ПТК (egm/ptk.py), дублирует SPEC-10",
        },
    ),
    "tools": (
        "без служебных утилит",
        {
            "tools/": "служебные утилиты (fix_diff, context_bundle, make_audit_bundle)",
        },
    ),
    "workflow": (
        "без референсной копии порядка работы Super Agent",
        {
            "HarmonicV2-workflow.md": "референсная копия, актуальная — в AI Drive (Д-25)",
        },
    ),
}
MIN_PROFILE = "min"  # ключ --min — все профили сразу

MAX_FILE_BYTES = 300_000


def run(cmd):
    return subprocess.check_output(cmd, text=True, stderr=subprocess.STDOUT).strip()


def git_files():
    """`git ls-files` в UTF-8: core.quotepath=false и -z отключают экранирование
    не-ASCII путей (иначе кириллица приходит в escape-виде, а такой путь потом
    не находится на диске и содержимое файла молча пропадает)."""
    raw = subprocess.check_output(["git", "-c", "core.quotepath=false", "ls-files", "-z"])
    return [p for p in raw.decode("utf-8").split("\0") if p]


def _segment_rx(seg):
    """Сегмент шаблона (без «/») → regex; * ? [..] не выходят за пределы сегмента."""
    rx, i = "", 0
    while i < len(seg):
        c = seg[i]
        if c == "\\" and i + 1 < len(seg):
            rx += re.escape(seg[i + 1])
            i += 2
            continue
        if c == "*":
            rx += "[^/]*"
        elif c == "?":
            rx += "[^/]"
        elif c == "[":
            j = seg.find("]", i + 2 if seg[i + 1:i + 2] in ("!", "^") else i + 1)
            if j < 0:
                rx += re.escape(c)
            else:
                body = seg[i + 1:j]
                if body[:1] in ("!", "^"):
                    body = "^" + body[1:]
                rx += "[" + body.replace("\\", "\\\\") + "]"
                i = j
        else:
            rx += re.escape(c)
        i += 1
    return rx


def compile_rule(rule):
    """Правило .gitignore → (negate, regex) для пути файла; None — пустое/комментарий."""
    pat = rule.strip()
    if not pat or pat.startswith("#"):
        return None
    negate = pat.startswith("!")
    if negate:
        pat = pat[1:]
    elif pat.startswith("\\"):
        pat = pat[1:]
    dir_only = pat.endswith("/")
    pat = pat.rstrip("/")
    if not pat:
        raise ValueError(f"пустой шаблон: {rule!r}")
    anchored = "/" in pat
    pat = pat.lstrip("/")
    parts = pat.split("/")
    rx = ""
    for k, seg in enumerate(parts):
        last = k == len(parts) - 1
        if seg == "**":
            rx += ".*" if last else "(?:[^/]+/)*"
        else:
            rx += _segment_rx(seg) + ("" if last else "/")
    head = "^" if anchored else "^(?:[^/]+/)*"
    tail = "/.+$" if dir_only else "(?:/.+)?$"
    return negate, re.compile(head + rx + tail)


def build_rules(ns):
    """-> [(правило, обоснование, источник)] в порядке применения."""
    rules = [(r, d, "base") for r, d in SKIP_FILES.items()]
    on = [n for n in PROFILES if getattr(ns, n) or ns.min]
    for name in on:
        rules += [(r, d, name) for r, d in PROFILES[name][1].items()]
    rules += [(r, "задано ключом --exclude", "exclude") for r in ns.exclude]
    seen, uniq = set(), []
    for item in rules:  # повтор правила из нескольких профилей — один раз
        if item[0] not in seen:
            seen.add(item[0])
            uniq.append(item)
    return on, uniq


def match_files(files, rules):
    """-> (excluded set, {правило: [файлы, совпавшие с ним]})."""
    compiled = []
    for rule, _, _ in rules:
        c = compile_rule(rule)
        if c:
            compiled.append((rule, *c))
    excluded, hits = set(), {r: [] for r, _, _ in rules}
    for f in files:
        state = False
        for rule, negate, rx in compiled:
            if rx.match(f):
                state = not negate
                hits[rule].append(f)
        if state:
            excluded.add(f)
    return excluded, hits


def parse_args(argv):
    ap = argparse.ArgumentParser(
        description="Снимок репозитория AUDIT_BUNDLE.md; без ключей — максимально полный.")
    for name, (desc, rules) in PROFILES.items():
        ap.add_argument(f"--{name}", action="store_true",
                        help=f"{desc}: {', '.join(rules)}")
    ap.add_argument(f"--{MIN_PROFILE}", action="store_true",
                    help="все профили сразу")
    ap.add_argument("--exclude", action="append", default=[], metavar="ПРАВИЛО",
                    help="дополнительное правило .gitignore (можно повторять)")
    ap.add_argument("--out", default=str(OUT), metavar="ФАЙЛ",
                    help="выходной файл (по умолчанию AUDIT_BUNDLE.md в корне)")
    ap.add_argument("--list", action="store_true",
                    help="показать профили и правила, снимок не строить")
    return ap.parse_args(argv)


def print_profiles():
    print("base (всегда):")
    for r, d in SKIP_FILES.items():
        print(f"  {r} - {d}")
    for name, (desc, rules) in PROFILES.items():
        print(f"--{name}: {desc}")
        for r, d in rules.items():
            print(f"  {r} - {d}")
    print(f"--{MIN_PROFILE}: все профили сразу")


def main(argv=None):
    ns = parse_args(argv)
    if ns.list:
        print_profiles()
        return 0
    on, rules = build_rules(ns)
    try:
        for r, _, _ in rules:
            compile_rule(r)
    except (ValueError, re.error) as e:
        print(f"ОШИБКА: неверное правило: {e}", file=sys.stderr)
        return 2

    head = run(["git", "rev-parse", "HEAD"])
    files = git_files()
    excluded, hits = match_files(files, rules)
    out_path = Path(ns.out)

    with out_path.open("w", encoding="utf-8", newline="\n") as out:
        out.write("# AUDIT BUNDLE HarmonicV2\n\n")
        out.write(f"HEAD: `{head}`\n\n")
        if on or ns.exclude:
            keys = [f"--{n}" for n in on] + [f"--exclude {r}" for r in ns.exclude]
            out.write(f"Profiles: {' '.join(keys)}\n\n")

        out.write("## Git tree\n\n")
        out.write("```text\n")
        for f in files:
            out.write(f + "\n")
        out.write("```\n\n")

        out.write("## Skipped content of files from the report for some reasons: \n\n")

        for rule, desc, _ in rules:
            out.write(f"{rule} - {desc}\n")
            matched = hits[rule]
            if matched != [rule]:
                out.write(f"  -> {len(matched)} files: {', '.join(matched) or '—'}\n")
            out.write("\n")

        out.write("## Text file contents\n\n")

        skipped = []
        for rel in files:
            if rel in excluded:
                continue
            path = ROOT / rel
            ext = path.suffix.lower()

            if ext not in TEXT_EXT:
                continue

            try:
                size = path.stat().st_size
            except OSError as e:
                skipped.append((rel, f"нет файла на диске ({e.strerror})"))
                continue

            if size > MAX_FILE_BYTES:
                out.write(f"\n---\n\n")
                out.write(f"### FILE: `{rel}`\n\n")
                out.write(f"Skipped: file is too large, {size} bytes.\n")
                continue

            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                skipped.append((rel, "файл не в UTF-8 — содержимое не включено"))
                continue

            out.write(f"\n---\n\n")
            out.write(f"### FILE: `{rel}`\n\n")
            out.write("```text\n")
            out.write(text)
            if not text.endswith("\n"):
                out.write("\n")
            out.write("```\n")

        if skipped:
            out.write("Пропущены целиком (не правилами, а из-за ошибок чтения):\n\n")
            for rel, why in skipped:
                out.write(f"- `{rel}` — {why}\n")
            out.write("\n")

    if skipped:
        print(f"ВНИМАНИЕ: {len(skipped)} файлов не прочитано, список в bundle",
              file=sys.stderr)
    print(f"Wrote {out_path} ({out_path.stat().st_size} bytes, "
          f"excluded {len(excluded)} of {len(files)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
