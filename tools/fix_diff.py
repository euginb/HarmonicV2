#!/usr/bin/env python3
"""fix_diff.py — нормализация unified diff от ИИ под git apply / patch -p1.

Стадия 1 (синтаксис): CRLF/BOM/UTF-16 патча, строки diff --git / new file mode /
deleted file mode, счётчики @@, пустые строки без префикса, пути без a/ b/;
переименования и копирования (rename/copy from/to); C-квотинг путей git —
октальные \\NNN декодируются в UTF-8 (не-ASCII имена файлов, пробелы).
Стадия 2 (сверка с рабочим деревом, для изменяемых и удаляемых файлов):
  * hunk ищется в реальном файле (сравнение без учёта ведущих и хвостовых
    пробелов — отступы контекста в патче часто не совпадают с файлом);
  * строки ' ' и '-' берутся из файла дословно;
  * если контекст совпал только с точностью до ведущих пробелов, отступ
    добавленной строки ('+') берётся из файла (у ближайшей контекстной
    строки), а не из патча;
  * если строгих кандидатов нет, первая/последняя строка контекста может
    совпасть как префикс строки файла (обрезан хвост) — в diff идёт строка
    файла;
  * контекст добирается до 3 строк с каждой стороны (иначе git apply
    привязывает hunk без хвостового контекста к концу файла);
  * расставляется '\\ No newline at end of file';
  * сохраняется стиль окончаний строк файла (LF/CRLF).
Для переименования/копирования hunk'и сверяются со старым путём (содержимое
до переименования); чистое переименование без правок проходит как есть.
Стадия 2 устойчива к ошибкам ИИ в номерах строк, отступах контекста и обрезанных
хвостах его строк: hunk ищется по содержимому по
всему файлу, а не только после предыдущего; найденные hunk'и сортируются по
позиции в файле (порядок в патче может не совпадать с ним), уже применённые
hunk'и распознаются и пропускаются, а в сообщении «не найден» указывается
причина (полное совпадение вне доступной позиции, перекрытие и т. п.).

Использование:
  python tools/fix_diff.py IN [OUT] [--root DIR]
  OUT по умолчанию <IN>.fixed.diff, DIR — корень репозитория (по умолчанию текущий каталог).
Код выхода: 0 — успех, 1 — ошибка (см. сообщение).
"""
import re
import subprocess
import sys
from itertools import takewhile
from pathlib import Path

HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")
BASE_RE = re.compile(r"^#\s*base:\s*([0-9a-fA-F]{7,40})")
FENCE_RE = re.compile(r"^(```|~~~)")  # markdown-обрамление из чата; строка diff так начинаться не может
GITLINE_Q_RE = re.compile(r'^diff --git ("(?:[^"\\]|\\.)*") (".*")$')  # оба пути в C-кавычках git
GIT_META = ("diff --git ", "index ", "new file mode", "deleted file mode",
            "old mode", "new mode", "similarity index", "dissimilarity index",
            "rename from", "rename to", "copy from", "copy to")
DEV_NULL = "/dev/null"
CTX = 3
NO_EOL = ("\\", " No newline at end of file")
WARNINGS = []


def die(msg):
    sys.exit("ОШИБКА: " + msg)


def warn(msg):
    WARNINGS.append(msg)


# ---------- C-квотинг путей git (не-ASCII имена: кириллица и т. п.) ----------

UNQUOTE_ESC = {"a": 7, "b": 8, "f": 12, "n": 10, "r": 13, "t": 9, "v": 11,
               "\\": 92, '"': 34}
OCT_RE = re.compile(r"[0-7]{1,3}")


def unquote(p):
    """C-строка git '"a/\\320\\242..."' (октальные \\NNN — байты UTF-8) -> путь.
    Строка без кавычек возвращается как есть."""
    if len(p) < 2 or p[0] != '"' or p[-1] != '"':
        return p
    out, body, i = bytearray(), p[1:-1], 0
    while i < len(body):
        c = body[i]
        if c != "\\":
            out += c.encode("utf-8")
            i += 1
            continue
        n = body[i + 1] if i + 1 < len(body) else ""
        if n in UNQUOTE_ESC:
            out.append(UNQUOTE_ESC[n])
            i += 2
        elif n in "01234567":
            m = OCT_RE.match(body, i + 1)
            out.append(int(m[0], 8) & 0xFF)
            i += 1 + len(m[0])
        else:  # не распознанный экран — обратный слэш как есть
            out.append(92)
            i += 1
    try:
        return out.decode("utf-8")
    except UnicodeDecodeError:
        return out.decode("latin-1")


def qp(path):
    """Путь для diff --git / --- +++ / rename from|to: не-ASCII остаётся сырым
    UTF-8 (родной формат git при core.quotepath=false); C-кавычки — только для
    управляющих символов, '"' и '\\'."""
    bs = path.encode("utf-8")
    if not any(b < 0x20 or b in (0x22, 0x5C) or b == 0x7F for b in bs):
        return path
    out = bytearray(b'"')
    for b in bs:
        if b in (0x22, 0x5C):
            out += b"\\" + bytes([b])
        elif b < 0x20 or b == 0x7F:
            out += ("\\%03o" % b).encode("ascii")
        else:
            out.append(b)
    out += b'"'
    return out.decode("latin-1")  # байты не-ASCII; при записи encode('utf-8') вернёт их же


def parse_gitline(ln):
    """Пути из 'diff --git a/X b/Y', в том числе полностью в C-кавычках git."""
    m = GITLINE_Q_RE.match(ln.strip())
    if m:
        return strip_ab(unquote(m[1])), strip_ab(unquote(m[2]))
    rest = ln.strip()[len("diff --git "):]
    if rest.startswith("a/"):
        j = rest.find(" b/")
        if j > 0:
            return rest[2:j], rest[j + 3:]
    return None, None  # пути доберутся позже по ---/+++ или rename from/to


# ---------- стадия 1: разбор патча ----------

def read_patch(path):
    raw = Path(path).read_bytes()
    text = raw.decode("utf-16") if raw[:2] in (b"\xff\xfe", b"\xfe\xff") else raw.decode("utf-8-sig")
    return text.replace("\r\n", "\n").replace("\r", "\n").split("\n")


def strip_ab(p):
    return p[2:] if p.startswith(("a/", "b/")) else p


def clean_path(p):
    p = p.split("\t")[0].strip()
    p = unquote(p)
    if p == DEV_NULL:
        return None
    return strip_ab(p)


def is_file_header(lines, i):
    return (lines[i].startswith("--- ") and i + 2 < len(lines)
            and lines[i + 1].startswith("+++ ") and lines[i + 2].startswith("@@ "))


def new_file_rec(line_no, old=None, new=None):
    return {"old": old, "new": new, "hunks": [], "line": line_no, "hdr": False,
            "rename_from": None, "rename_to": None,
            "new_file": False, "deleted": False}


def parse(lines):
    """-> (base_sha|None, [ {old,new,rename_from,rename_to,new_file,deleted,line,
    hunks:[{old_start,tail,line,body:[[kind,text,lineno]]}]} ])
    kind: ' ', '-', '+', '?' (пустая строка без префикса — смысл уточняется позже)."""
    files, cur, hunk, base, i = [], None, None, None, 0
    while i < len(lines):
        ln = lines[i]
        if FENCE_RE.match(ln):
            warn(f"строка {i + 1}: markdown-обрамление {ln.strip()!r} пропущено")
            hunk = None  # закрывающее обрамление завершает hunk
            i += 1
            continue
        if ln.startswith("diff --git "):
            old, new = parse_gitline(ln)
            cur = new_file_rec(i + 1, old, new)
            files.append(cur)
            hunk = None
            i += 1
            continue
        if is_file_header(lines, i):
            if cur is None or cur["hdr"]:
                cur = new_file_rec(i + 1)
                files.append(cur)
            cur["hdr"] = True
            # ---/+++ главнее diff --git: у нового файла слева /dev/null,
            # у удалённого справа /dev/null; для rename значения совпадают
            cur["old"] = clean_path(ln[4:])
            cur["new"] = clean_path(lines[i + 1][4:])
            hunk = None
            i += 2
            continue
        if ln.startswith("@@ ") and cur is not None:
            m = HUNK_RE.match(ln)
            if not m:
                die(f"строка {i + 1}: неразборчивый заголовок hunk: {ln!r}")
            hunk = {"old_start": int(m[1]), "tail": m[5], "body": [], "line": i + 1}
            cur["hunks"].append(hunk)
            i += 1
            continue
        if ln.startswith(GIT_META):
            hunk = None
            if cur is not None:
                if ln.startswith("rename from "):
                    cur["rename_from"] = clean_path(ln[12:])
                elif ln.startswith("rename to "):
                    cur["rename_to"] = clean_path(ln[10:])
                elif ln.startswith("copy from "):
                    cur["rename_from"] = clean_path(ln[10:])
                elif ln.startswith("copy to "):
                    cur["rename_to"] = clean_path(ln[8:])
                elif ln.startswith("new file mode"):
                    cur["new_file"] = True
                elif ln.startswith("deleted file mode"):
                    cur["deleted"] = True
            i += 1
            continue
        if hunk is None:
            m = BASE_RE.match(ln)
            if m:
                base = m[1].lower()
            elif ln.strip():
                warn(f"строка {i + 1}: текст вне hunk пропущен: {ln[:60]!r}")
            i += 1
            continue
        if ln.startswith("\\"):
            pass  # маркеры '\ No newline' расставляются заново по реальному файлу
        elif ln == "":
            hunk["body"].append(["?", "", i + 1])
        elif ln[0] in " +-":
            hunk["body"].append([ln[0], ln[1:], i + 1])
        else:
            die(f"строка {i + 1}: строка без префикса ' ', '+', '-' внутри hunk: {ln[:60]!r}")
        i += 1
    return base, files


# ---------- стадия 2: сверка с рабочим деревом ----------

def read_target(root, rel):
    p = root / rel
    if not p.is_file():
        die(f"{rel}: файл не найден в рабочем дереве ({p})")
    text = p.read_bytes().decode("utf-8")
    eol = "\r\n" if "\r\n" in text else "\n"
    lines = text.split(eol)
    final_nl = lines[-1] == ""
    if final_nl:
        lines.pop()
    return lines, eol, final_nl


def find(flines, old, hint, lo, occupied=()):
    """Позиция (0-based) блока old в flines, начиная со строки lo; участки occupied
    (уже занятые другими hunk'ами) пропускаются; из кандидатов — ближайший к hint.
    Сравнение — без учёта ведущих и хвостовых пробелов: отступ контекста в патче
    может не совпадать с файлом (для '+' строк он затем берётся из файла). Если
    строгих кандидатов нет — первая и последняя строки блока могут совпасть как
    ПРЕФИКС строки файла (обрезан хвост контекста в патче), с предупреждением."""
    key = [s.strip() for s in old]
    n = len(key)

    def cands(edges):
        out = []
        for p in range(lo, len(flines) - n + 1):
            if any(p < b and p + n > a for a, b in occupied):
                continue
            if all(flines[p + k].strip() == key[k]
                   or (edges and k in (0, n - 1) and key[k]
                       and flines[p + k].strip().startswith(key[k]))
                   for k in range(n)):
                out.append(p)
        return out

    c = cands(False)
    if not c:
        c = cands(True)
        if c:
            warn("хвост первой/последней строки контекста в патче обрезан — "
                 "в diff взята строка файла")
    return min(c, key=lambda p: abs(p - hint)) if c else None


def already_applied(flines, body, occupied=()):
    """True, если новая сторона hunk'а (контекст + строки '+') уже есть в файле:
    повторная выдача патча на уже пропатченном дереве не должна быть ошибкой."""
    for amb in ("+", " "):
        cand = [(amb if k == "?" else k, t) for k, t, _ in body]
        new = [t for k, t in cand if k in " +"]
        if len(new) < 2 or not any(k == "+" for k, _ in cand):
            continue
        if find(flines, new, 0, 0, occupied) is not None:
            return True
    return False


def diagnose(flines, old, hint, lo, occupied):
    best_m, best_p = -1, 0
    for p in range(max(1, len(flines))):
        m = 0
        while m < len(old) and p + m < len(flines) and flines[p + m].strip() == old[m].strip():
            m += 1
        if m > best_m or (m == best_m and abs(p - hint) < abs(best_p - hint)):
            best_m, best_p = m, p
    if best_m == len(old):
        why = []
        if best_p < lo:
            why.append(f"лежит раньше курсора (строка {lo + 1})")
        if any(best_p < b and best_p + len(old) > a for a, b in occupied):
            why.append("перекрывается с уже найденным hunk'ом")
        note = " (" + "; ".join(why) + ")" if why else ""
        return f"полное совпадение найдено со строки {best_p + 1}, но блок недоступен{note}"
    exp = old[best_m] if best_m < len(old) else "?"
    got = flines[best_p + best_m] if best_p + best_m < len(flines) else "<конец файла>"
    return (f"лучшее совпадение с строки {best_p + 1}: совпало {best_m} из {len(old)}; "
            f"ожидалось {exp!r}, в файле {got!r}")


def fix_eof(out):
    """Файл без перевода строки в конце, hunk доходит до последней строки."""
    idx = max((i for i, (k, _) in enumerate(out) if k in " -"), default=None)
    if idx is None:
        return
    k, t = out[idx]
    if k == " " and any(kk == "+" for kk, _ in out[idx + 1:]):
        out[idx:idx + 1] = [("-", t), NO_EOL, ("+", t)]  # дописываем перевод строки
    else:
        out.insert(idx + 1, NO_EOL)


def render(out, eol):
    cr = "\r" if eol == "\r\n" else ""
    return [k + t if k == "\\" else k + t + cr for k, t in out]


def emit_new(f, root, path, hdr):
    if (root / path).exists():
        die(f"{path}: помечен как новый, но уже существует в рабочем дереве")
    body = [b for h in f["hunks"] for b in h["body"]]
    while body and body[-1][0] == "?":
        body.pop()
    bad = [b for b in body if b[0] in " -"]
    if bad:
        die(f"{path}: новый файл содержит строки ' '/'-' (строка патча {bad[0][2]})")
    hdr.append("new file mode 100644")
    if not body:
        return hdr
    return hdr + ["--- /dev/null", f"+++ {qp('b/' + path)}", f"@@ -0,0 +1,{len(body)} @@"] + \
        ["+" + t for _, t, _ in body]


def emit_deleted(root, path, f, hdr):
    flines, eol, final_nl = read_target(root, path)
    hdr.append("deleted file mode 100644")
    if not flines:
        return hdr
    out = [("-", t) for t in flines]
    if not final_nl:
        fix_eof(out)
    return hdr + [f"--- {qp('a/' + path)}", "+++ /dev/null", f"@@ -1,{len(flines)} +0,0 @@"] + \
        render(out, eol)


def merge_close(flines, located):
    """Соседние hunk'и ближе 2·CTX сливаются в один. Отдельный hunk, прижатый к границе
    (без хвостового контекста), git apply и patch отказываются применять; при слиянии
    хвостовой контекст появляется, и форма совпадает с каноническим diff -u."""
    merged = []
    for p, n, body, tail in located:
        if merged and p - (merged[-1][0] + merged[-1][1]) <= 2 * CTX:
            p0, n0, b0, _ = merged[-1]
            gap = [[" ", flines[j], None] for j in range(p0 + n0, p)]
            merged[-1] = (p0, p + n - p0, b0 + gap + [list(b) for b in body], tail)
        else:
            merged.append((p, n, [list(b) for b in body], tail))
    return merged


def locate(path, flines, hunks):
    located, lo, occupied = [], 0, []
    for h in hunks:
        body = [list(b) for b in h["body"]]
        while body and body[-1][0] in " ?" and not body[-1][1].strip():
            body.pop()  # хвостовые пустые строки контекста доберём из файла
        if not any(b[0] in "+-" for b in body):
            warn(f"{path}: hunk со строки патча {h['line']} без изменений — пропущен")
            continue
        hint = max(h["old_start"] - 1, 0)
        res = None
        for amb in (" ", "+"):  # '?' сперва как контекст, затем как добавленная строка
            cand = [(amb if k == "?" else k, t, n) for k, t, n in body]
            old = [t for k, t, _ in cand if k in " -"]
            if not old:
                p = min(max(h["old_start"], lo), len(flines))
                warn(f"{path}: hunk со строки патча {h['line']} без контекста — вставка после строки {p}")
                res = (p, 0, cand, h["tail"])
                break
            p = find(flines, old, hint, lo, occupied)
            if p is None and lo:
                # номера строк у ИИ могут врать: ищем блок по всему файлу, а не только ниже курсора
                p = find(flines, old, hint, 0, occupied)
                if p is not None:
                    warn(f"{path}: hunk со строки патча {h['line']} лежит раньше предыдущего "
                         f"(строка файла {p + 1}); порядок hunk'ов в патче не совпадает с файлом")
            if p is not None:
                res = (p, len(old), cand, h["tail"])
                break
        if res is None:
            if already_applied(flines, body, occupied):
                warn(f"{path}: hunk со строки патча {h['line']} уже применён — пропущен")
                continue
            old = [t for k, t, _ in body if k in " -?"]
            die(f"{path}: hunk со строки патча {h['line']} не найден в файле. "
                + diagnose(flines, old, hint, lo, occupied))
        p, n, cand, tail = res
        occupied.append((p, p + n))
        located.append((p, n, cand, tail))
        lo = max(lo, p + n)
    located.sort(key=lambda t: t[0])  # git apply требует hunk'и в порядке возрастания позиций
    return merge_close(flines, located)  # смежные hunk'и сливаются, чтобы не терять контекст


def emit_modified(root, old, new, f, hdr):
    flines, eol, final_nl = read_target(root, old)
    located = locate(old, flines, f["hunks"])
    if not located:
        warn(f"{old}: нет изменений — файл пропущен")
        return []
    res = hdr + [f"--- {qp('a/' + old)}", f"+++ {qp('b/' + new)}"]
    delta, prev_end = 0, 0
    for idx, (p, n, body, tail) in enumerate(located):
        nxt = located[idx + 1][0] if idx + 1 < len(located) else len(flines)
        lead = sum(1 for _ in takewhile(lambda b: b[0] == " ", body))
        trail = sum(1 for _ in takewhile(lambda b: b[0] == " ", reversed(body)))
        s = max(prev_end, p - max(0, CTX - lead))
        e = min(nxt, p + n + max(0, CTX - trail))
        out = [(" ", flines[j]) for j in range(s, p)]
        # Контекст мог совпасть только без учёта ведущих пробелов — тогда отступ
        # добавляемых строк ('+') берём из файла (у ближайшей контекстной строки).
        fline, k0 = {}, p
        for bi, (kind, t, _) in enumerate(body):
            if kind in " -":
                fline[bi] = flines[k0]
                k0 += 1

        def adopt(t, bi, ln):
            if not t.strip():
                return t
            for j in sorted(fline, key=lambda j: (abs(j - bi), 0 if j < bi else 1)):
                ftext = fline[j]
                if not ftext.strip():
                    continue  # пустая контекстная строка отступ не задаёт
                ptext = body[j][1]
                plead = ptext[:len(ptext) - len(ptext.lstrip())]
                flead = ftext[:len(ftext) - len(ftext.lstrip())]
                if plead != flead:
                    warn(f"{old}: строка патча {ln}: отступ добавленной строки взят из файла")
                    return flead + t.lstrip()
                return t
            return t

        k = p
        for bi, (kind, t, ln) in enumerate(body):
            if kind in " -":
                out.append((kind, flines[k]))  # дословно из файла
                k += 1
            else:
                out.append(("+", adopt(t, bi, ln)))
        out += [(" ", flines[j]) for j in range(k, e)]
        if e == len(flines) and not final_nl:
            fix_eof(out)
        o = sum(kk in " -" for kk, _ in out)
        nn = sum(kk in " +" for kk, _ in out)
        res.append(f"@@ -{s + (1 if o else 0)},{o} +{s + delta + (1 if nn else 0)},{nn} @@{tail}")
        res += render(out, eol)
        delta += nn - o
        prev_end = e
    return res


def emit_renamed(f, root, old, new):
    """Переименование/копирование: заголовок rename from/to; hunk'и сверяются со
    старым путём (содержимое до переименования), файл переносит сам git apply."""
    hdr = [f"diff --git {qp('a/' + old)} {qp('b/' + new)}"]
    if f["new_file"]:
        hdr.append("new file mode 100644")
    if f["deleted"]:
        hdr.append("deleted file mode 100644")
    hdr.append(f"rename from {qp(old)}")
    hdr.append(f"rename to {qp(new)}")
    if not f["hunks"]:
        warn(f"{old} -> {new}: переименование без правок содержимого")
        return hdr
    return emit_modified(root, old, new, f, hdr)


def emit_file(f, root):
    old, new = f["old"], f["new"]
    if f["rename_from"] is not None:
        old = f["rename_from"]
    if f["rename_to"] is not None:
        new = f["rename_to"]
    if old is None and new is None:
        die(f"строка {f['line']}: оба пути /dev/null")
    if old and new and old != new:
        return emit_renamed(f, root, old, new)
    path = old or new
    hdr = [f"diff --git {qp('a/' + path)} {qp('b/' + path)}"]
    if old is None:
        return emit_new(f, root, path, hdr)
    if new is None:
        return emit_deleted(root, path, f, hdr)
    return emit_modified(root, path, path, f, hdr)


def git_head(root):
    try:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"],
                              capture_output=True, text=True, check=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def main(argv):
    args, root = list(argv[1:]), Path.cwd()
    if "--root" in args:
        i = args.index("--root")
        root = Path(args[i + 1])
        del args[i:i + 2]
    if not args:
        sys.exit(__doc__)
    src = Path(args[0])
    if not src.is_file():
        die(f"файл патча не найден: {src}")
    dst = Path(args[1]) if len(args) > 1 else src.with_suffix(".fixed.diff")
    base, files = parse(read_patch(src))
    if not files:
        die("не найдено ни одного блока файла ('--- ' / '+++ ' / '@@').")
    head = git_head(root)
    if base and head and not head.startswith(base):
        warn(f"патч построен от {base[:12]}, HEAD = {head[:12]}; контекст сверен с рабочим деревом")
    seen, out = set(), []
    for f in files:
        path = f["old"] or f["new"] or f["rename_from"] or f["rename_to"]
        if path in seen:
            die(f"{path}: файл встречается в патче дважды — объедините блоки")
        seen.add(path)
        out += emit_file(f, root)
    dst.write_bytes(("\n".join(out) + "\n").encode("utf-8"))
    print(f"Файлов: {len(files)}, hunk'ов: {sum(len(f['hunks']) for f in files)} -> {dst}")
    for w in WARNINGS:
        print("  предупреждение:", w)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
