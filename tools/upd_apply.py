#!/usr/bin/env python3
"""upd_apply.py — применение к рабочему дереву обновлений из файла upd.md (CP-47).

Дополняет fix_diff.py (Д-78) там, где unified diff неудобен: правки строк
таблиц, которые инструменты переформатирования постоянно сдвигают (контекст
патча «плывёт»), и добавление новых файлов целиком (в diff «+» на каждой
строке). Правки применяются к рабочему дереву напрямую, git apply не нужен.
Формат и порядок работы — instructions/README.md §2.5.

Файл upd.md — последовательность блоков; блок начинается директивой:

  # --- Journal: '<путь>': <заголовок раздела>
  |ключ| ячейки | ... |    — ключ (первая ячейка) есть в таблице — строка
                             заменяется целиком; нет — добавляется в конец
  # --- NewFile: '<путь>'
  <содержимое до следующей директивы / конца файла>

Ключ и заголовок раздела сравниваются без учёта концевых пробелов (ведущие
«##» заголовка на сравнение не влияют); записанная строка выравнивается по
текущим ширинам колонок таблицы; число ячеек строки должно совпадать с шапкой.
Блок применяется атомарно: ошибка в середине блока не записывает ничего.
Новый файл создаётся вместе с родительскими каталогами; существующий без
--overwrite-new — ошибка. Кодировка — UTF-8 без BOM; EOL целевого файла
сохраняется, новые файлы — LF.
Директива — только строка, совпавшая с шаблоном директивы ('# --- Journal: …'
или '# --- NewFile: …'); прочие строки содержимого, начинающиеся с '# ---'
(например, заголовки секций python-файла '# ---------- лист ----------'), —
обычное содержимое блока NewFile. Ограничения: путь в одинарных кавычках,
относительный, без '..'; строка содержимого, совпадающая с директивой, не
представима; '|' внутри ячейки — как '\\|'; повторный прогон одного upd.md:
замены идемпотентны, добавления строк задвоятся.

Использование:
  python tools/upd_apply.py <upd.md> [--dry-run] [--overwrite-new] [--root DIR]
Код выхода: 0 — всё применено; 1 — ошибка запуска или есть блоки с ошибками.
"""
import re
import sys
from pathlib import Path

DIR_RE = re.compile(r"^# ---\s+(Journal|NewFile):\s+'([^']*)'\s*(?::\s*(.+?))?\s*$")
HEAD_RE = re.compile(r"^#{1,6}\s")
SEP_RE = re.compile(r":?-{2,}:?")


class UpdError(Exception):
    """Ошибка применения одного блока upd.md (блок при этом не записывается)."""


def die(msg):
    sys.exit("ОШИБКА: " + msg)


# ---------- разбор upd.md ----------

def parse_upd(text):
    """-> [{'kind': 'Journal'|'NewFile', 'path', 'section'|None, 'body': [строки]}]"""
    blocks, cur = [], None
    for n, ln in enumerate(text.split("\n"), 1):
        m = DIR_RE.match(ln)
        if m:
            kind, path = m[1], m[2].strip()
            sec = m[3].strip() if m[3] else None
            if kind == "Journal" and not sec:
                die(f"строка {n}: у Journal не указан раздел: {ln.strip()!r}")
            if kind == "NewFile" and sec:
                die(f"строка {n}: у NewFile текст после пути не предусмотрен: {sec!r}")
            cur = {"kind": kind, "path": path, "section": sec, "body": [], "line": n}
            blocks.append(cur)
        elif cur is not None:
            cur["body"].append(ln)
    return blocks


def target(root, blk):
    p = Path(blk["path"])
    if p.is_absolute() or blk["path"].startswith("~"):
        raise UpdError(f"путь должен быть относительным: {blk['path']!r}")
    if ".." in p.parts:
        raise UpdError(f"'..' в пути не допускается: {blk['path']!r}")
    return root / p


# ---------- таблицы ----------

def read_lines(tgt):
    try:
        text = tgt.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as e:
        raise UpdError(f"целевой файл не UTF-8 ({e})")
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(eol)
    tail = eol if (lines and lines[-1] == "") else ""
    if tail:
        lines.pop()
    return lines, eol, tail


def is_row(s):
    s = s.strip()
    return s.startswith("|") and s.endswith("|")


def split_row(line):
    """'| a | b\\|c |' -> ['a', 'b|c']; '\\|' — литеральная вертикальная черта."""
    cells, buf, esc = [], [], False
    for ch in line.strip()[1:-1]:
        if esc:
            buf.append(ch)
            esc = False
        elif ch == "\\":
            esc = True
        elif ch == "|":
            cells.append("".join(buf).strip())
            buf = []
        else:
            buf.append(ch)
    cells.append("".join(buf).strip())
    return [c.replace("\\|", "|") for c in cells]


def is_sep(cells):
    return bool(cells) and all(SEP_RE.fullmatch(c) for c in cells)


def esc_cell(c):
    return c.replace("|", "\\|")


def col_widths(rows):
    w = []
    for cells in rows:
        for i, c in enumerate(cells):
            if i == len(w):
                w.append(0)
            w[i] = max(w[i], len(esc_cell(c)))
    return w


def fmt_row(cells, widths):
    parts = []
    for i, c in enumerate(cells):
        e = esc_cell(c)
        w = widths[i] if i < len(widths) else 0
        parts.append(e + " " * max(0, w - len(e)))
    return "| " + " | ".join(parts) + " |"


def headings_with_tables(lines):
    found, cur = [], None
    for l in lines:
        ls = l.strip()
        if HEAD_RE.match(ls):
            cur = ls
        elif is_row(l) and cur and cur not in found:
            found.append(cur)
    return found


# ---------- применение блоков ----------

def apply_journal(root, blk, dry):
    tgt = target(root, blk)
    if not tgt.is_file():
        raise UpdError(f"файл не найден ({tgt})")
    lines, eol, tail = read_lines(tgt)
    sec = blk["section"]
    hi = None
    for i, l in enumerate(lines):
        ls = l.strip()
        if HEAD_RE.match(ls) and ls in (sec, sec.lstrip("#").strip(), sec.strip()):
            hi = i
            break
        if HEAD_RE.match(ls) and ls.lstrip("#").strip() == sec.lstrip("#").strip():
            hi = i
            break
    if hi is None:
        found = headings_with_tables(lines)
        hint = ("; разделы с таблицами: " + " | ".join(found)) if found else ""
        raise UpdError(f"раздел {sec.strip()!r} не найден{hint}")
    ti = None
    for j in range(hi + 1, len(lines)):
        if HEAD_RE.match(lines[j].strip()):
            break  # начался следующий раздел — таблицы в этом нет
        if is_row(lines[j]):
            ti = j
            break
    if ti is None:
        raise UpdError("в указанном разделе нет таблицы")
    te = ti
    while te < len(lines) and is_row(lines[te]):
        te += 1
    header = split_row(lines[ti])
    body = [l for l in blk["body"] if l.strip()]
    if not body:
        raise UpdError("в блоке нет строк таблицы")
    bad = [l for l in body if not is_row(l)]
    if bad:
        raise UpdError(f"строка вне таблицы в блоке Journal: {bad[0].strip()[:50]!r}")
    for l in body:  # валидация до записи — блок атомарен
        cells = split_row(l)
        if len(cells) != len(header):
            raise UpdError(f"ключ {cells[0]!r}: ячеек {len(cells)}, в шапке таблицы {len(header)}")
    rep = []
    for l in body:
        cells = split_row(l)
        rows = [split_row(x) for x in lines[ti:te]]
        matches = [i for i, c in enumerate(rows) if not is_sep(c) and c and c[0] == cells[0]]
        if len(matches) > 1:
            raise UpdError(f"ключ {cells[0]!r} встречается в таблице {len(matches)} раз — неоднозначно")
        if matches:
            i = matches[0]
            lines[ti + i] = fmt_row(cells, col_widths(rows))
            rep.append(f"{cells[0]}: строка {ti + i + 1} файла заменена")
        else:
            lines.insert(te, fmt_row(cells, col_widths(rows)))
            te += 1
            rep.append(f"{cells[0]}: добавлена в конец таблицы")
    if not dry:
        tgt.write_bytes((eol.join(lines) + tail).encode("utf-8"))
    return "; ".join(rep)


def apply_newfile(root, blk, dry, ovr):
    tgt = target(root, blk)
    body = blk["body"]
    while body and not body[0].strip():
        body.pop(0)
    while body and not body[-1].strip():
        body.pop()
    existed = tgt.exists()
    if existed and not ovr:
        raise UpdError(f"файл уже существует (перезаписать — --overwrite-new): {tgt}")
    if existed and not tgt.is_file():
        raise UpdError(f"по пути каталог, а не файл: {tgt}")
    if not dry:
        tgt.parent.mkdir(parents=True, exist_ok=True)
        tgt.write_bytes(("\n".join(body) + ("\n" if body else "")).encode("utf-8"))
    return (f"перезаписан (--overwrite-new), {len(body)} строк" if existed
            else f"создан, {len(body)} строк")


# ---------- запуск ----------

def main(argv):
    args, root = list(argv[1:]), Path.cwd()
    if "--root" in args:
        i = args.index("--root")
        root = Path(args[i + 1])
        del args[i:i + 2]
    if "--dry-run" in args:
        args.remove("--dry-run")
        dry = True
    else:
        dry = False
    if "--overwrite-new" in args:
        args.remove("--overwrite-new")
        ovr = True
    else:
        ovr = False
    if len(args) != 1 or any(a.startswith("-") for a in args):
        sys.exit(__doc__)
    src = Path(args[0])
    if not src.is_file():
        die(f"файл upd не найден: {src}")
    try:
        text = src.read_bytes().decode("utf-8-sig")
    except UnicodeDecodeError as e:
        die(f"{src}: не UTF-8 ({e})")
    blocks = parse_upd(text)
    if not blocks:
        die("в файле нет директив Journal/NewFile.")
    ok = err = 0
    for blk in blocks:
        where = blk["path"] + (f" :: {blk['section']}" if blk["section"] else "")
        try:
            msg = (apply_journal(root, blk, dry) if blk["kind"] == "Journal"
                   else apply_newfile(root, blk, dry, ovr))
            print(f"OK   {blk['kind']} {where} — {msg}")
            ok += 1
        except UpdError as e:
            print(f"FAIL {blk['kind']} {where} — {e}")
            err += 1
    print(f"Итог: {ok} OK, {err} с ошибками" + ("; dry-run — ничего не записано" if dry else ""))
    return 1 if err else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
