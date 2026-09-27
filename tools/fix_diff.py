#!/usr/bin/env python3
"""fix_diff.py — нормализация unified diff, подготовленного ИИ, для git apply / patch -p1.

Исправляет:
  * CRLF -> LF, UTF-8 BOM, UTF-16 (вывод PowerShell '>');
  * отсутствие строк 'diff --git' / 'new file mode' / 'deleted file mode';
  * неверные счётчики в заголовках @@ (пересчёт по телу hunk);
  * пустые строки без префикса (внутри hunk -> контекст, в хвосте -> удаляются);
  * пути без префиксов a/ b/.
Использование:
  python tools/fix_diff.py IN [OUT]    (OUT по умолчанию: <IN>.fixed.diff)
Код выхода: 0 — успех, 1 — патч неразборчив (см. сообщение).
"""
import re
import sys
from pathlib import Path

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")
GIT_META = ("diff --git ", "index ", "new file mode", "deleted file mode",
            "old mode", "new mode", "similarity index", "rename from", "rename to")
DEV_NULL = "/dev/null"
WARNINGS = []


def die(line_no, msg):
    sys.exit(f"ОШИБКА (строка {line_no}): {msg}")


def warn(line_no, msg):
    WARNINGS.append(f"строка {line_no}: {msg}")


def read_patch(path):
    raw = Path(path).read_bytes()
    if raw[:2] in (b"\xff\xfe", b"\xfe\xff"):
        text = raw.decode("utf-16")
    else:
        text = raw.decode("utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def clean_path(p):
    p = p.split("\t")[0].strip()
    if p == DEV_NULL:
        return None
    if p.startswith(("a/", "b/")):
        p = p[2:]
    return p


def is_file_header(lines, i):
    """'--- X' + '+++ Y' + '@@ ' — начало блока файла (а не удалённая строка '-- ...')."""
    return (lines[i].startswith("--- ") and i + 2 < len(lines)
            and lines[i + 1].startswith("+++ ") and lines[i + 2].startswith("@@ "))


def parse(lines):
    files, cur, hunk, i = [], None, None, 0
    while i < len(lines):
        ln = lines[i]
        if is_file_header(lines, i):
            cur = {"old": clean_path(ln[4:]), "new": clean_path(lines[i + 1][4:]),
                   "hunks": [], "line": i + 1}
            files.append(cur)
            hunk = None
            i += 2
            continue
        if ln.startswith("@@ ") and cur is not None:
            m = HUNK_RE.match(ln)
            if not m:
                die(i + 1, f"неразборчивый заголовок hunk: {ln!r}")
            hunk = {"old_start": int(m[1]), "tail": m[5], "body": [], "line": i + 1}
            cur["hunks"].append(hunk)
            i += 1
            continue
        if ln.startswith(GIT_META):
            hunk = None  # служебные строки git генерируются заново
            i += 1
            continue
        if hunk is None:
            if ln.strip():
                warn(i + 1, f"текст вне hunk пропущен: {ln[:60]!r}")
            i += 1
            continue
        if ln == "" or ln[0] in " +-\\":
            hunk["body"].append((i + 1, ln))
        else:
            die(i + 1, f"строка без префикса ' ', '+', '-' внутри hunk: {ln[:60]!r}")
        i += 1
    return files


def normalize(body, new_file):
    while body and body[-1][1] == "":
        body.pop()
    out = []
    for no, ln in body:
        if ln == "":
            if new_file:
                warn(no, "пустая строка без '+' в новом файле — считаю добавленной")
                ln = "+"
            else:
                ln = " "
        out.append((no, ln))
    return out


def count(body):
    old = sum(1 for _, l in body if l[0] in " -")
    new = sum(1 for _, l in body if l[0] in " +")
    return old, new


def emit(files):
    out, seen = [], set()
    for f in files:
        old, new = f["old"], f["new"]
        if old is None and new is None:
            die(f["line"], "оба пути /dev/null")
        path_a, path_b = old or new, new or old
        if path_b in seen:
            warn(f["line"], f"файл {path_b} встречается в патче повторно")
        seen.add(path_b)
        is_new, is_del = old is None, new is None
        out.append(f"diff --git a/{path_a} b/{path_b}")
        if is_new:
            out.append("new file mode 100644")
        elif is_del:
            out.append("deleted file mode 100644")
        out.append(f"--- {'a/' + old if old else DEV_NULL}")
        out.append(f"+++ {'b/' + new if new else DEV_NULL}")

        hunks = f["hunks"]
        if is_new and len(hunks) > 1:  # новый файл — всегда один hunk
            merged = [ln for h in hunks for ln in h["body"]]
            hunks = [dict(hunks[0], body=merged)]
        delta = 0
        for h in hunks:
            body = normalize(h["body"], is_new)
            o, n = count(body)
            if is_new and o:
                die(h["line"], f"новый файл {new} содержит строки ' '/'-'")
            if is_del and n:
                die(h["line"], f"удаляемый файл {old} содержит строки ' '/'+'")
            if is_new:
                os_, ns = 0, (1 if n else 0)
            elif is_del:
                os_, ns = h["old_start"], 0
            else:
                os_ = h["old_start"]
                ns = os_ + delta + (1 if o == 0 else 0)
            delta += n - o
            out.append(f"@@ -{os_},{o} +{ns},{n} @@{h['tail']}")
            out.extend(ln for _, ln in body)
    return "\n".join(out) + "\n"


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    src = Path(argv[1])
    dst = Path(argv[2]) if len(argv) > 2 else src.with_suffix(".fixed.diff")
    files = parse(read_patch(src))
    if not files:
        sys.exit("ОШИБКА: не найдено ни одного блока файла ('--- ' / '+++ ' / '@@').")
    dst.write_bytes(emit(files).encode("utf-8"))  # UTF-8 без BOM, LF
    n_h = sum(len(f["hunks"]) for f in files)
    print(f"Файлов: {len(files)}, hunk'ов: {n_h} -> {dst}")
    for w in WARNINGS:
        print("  предупреждение:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
