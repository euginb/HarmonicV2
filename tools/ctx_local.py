#!/usr/bin/env python3
"""ctx_local — «пол» контекста для внешней модели (INS-91B §10, Д-146).

Профиль задаёт обязательный состав контекста. Скрипт:
  1) проверяет, что каждый обязательный файл существует и читается целиком;
  2) вставляет файлы ДОСЛОВНО, с путём, sha256, числом строк и байт;
  3) фрагменты (реестры, сортамент, products) режет по ключам, а не пересказом;
  4) перечитывает собранный документ и сверяет sha256 каждого блока с файлом —
     расхождение означает обрезку или подмену и валит сборку;
  5) пишет манифест .manifest.json и чек-лист; без --allow-missing отсутствие
     обязательного файла — ошибка (контекст не выпускается).

Использование:
    python3 tools/ctx_local.py --profile ring --check
    python3 tools/ctx_local.py --profile ring --base <sha> --cp CP-130 --out /tmp/ctx.md
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# профиль ring — серия «Венец .01» (CP-128…CP-135), требования модели 2026-11-26
PROFILES = {
    "ring": {
        "title": "Серия «Венец .01» — снижение массы",
        "whole": [
            "egm/ptk.py",
            "egm/ptk_force.py",
            "egm/ptk_profile.py",
            "egm/ptk_parts.py",
            "egm/ptk_doc.py",
            "egm/materials.py",
            "egm/cad/ptk_ring.py",
            "egm/cad/model.py",
            "specs/ptk_input.yaml",
            "specs/materials.yaml",
            "templates/SPEC-10_PTK_CALC.md.tmpl",
        ],
        "optional": [
            "egm/cad/step.py",
            "egm/cad/svg.py",
            "specs/ptk_design_input.yaml",
            "configs/application.yaml",
        ],
        "decisions": ["Д-08", "Д-19", "Д-126", "Д-140", "Д-141", "Д-142",
                      "Д-143", "Д-144", "Д-145", "Д-146"],
        "oq": ["OQ-48", "OQ-51", "OQ-52", "OQ-53"],
        "cp_prefix": ["CP-128", "CP-129", "CP-130", "CP-131", "CP-132",
                      "CP-133", "CP-134", "CP-135"],
        "stock_keys": ["ШХ15"],
        "product_parts": ["01", "05", "07", "18"],
        # Д-147: основной образец серии; его запись обязательна в контексте
        "config_ids": ["PTK-032-R7X20-22M5P2-F84938"],
        "main_id": "PTK-032-R7X20-22M5P2-F84938",
        "spec10_neighbours": 2,
    },
}
PROFILES["ring"]["stock_keys"] += []      # новые марки добавляет CP-129

sha = lambda b: hashlib.sha256(b).hexdigest()
def read(rel):
    with open(os.path.join(ROOT, rel), "rb") as f:
        return f.read()


def block(rel, data=None):
    data = read(rel) if data is None else data
    text = data.decode("utf-8")
    h = sha(data.rstrip(b"\n"))
    return (f"### FILE: {rel}\n"
            f"<!-- sha256 {h} | {len(data)} байт | {text.count(chr(10))} строк -->\n"
            f"```{_lang(rel)}\n{text.rstrip(chr(10))}\n```\n"), h


def _lang(rel):
    return {".py": "python", ".yaml": "yaml", ".md": "markdown", ".tmpl": "markdown"}.get(
        os.path.splitext(rel)[1], "text")


def _section(text, key):
    """Блок YAML по ключу верхнего уровня второго уровня вложенности (stock/products)."""
    lines = text.split("\n")
    out, depth = [], None
    for i, ln in enumerate(lines):
        if depth is None and re.match(rf"^\s*{re.escape(key)}\s*:", ln):
            depth = len(ln) - len(ln.lstrip())
            out = [ln]
            continue
        if depth is not None:
            ind = len(ln) - len(ln.lstrip())
            if ln.strip() and ind <= depth and not ln.lstrip().startswith("#"):
                break
            out.append(ln)
    return "\n".join(out).rstrip()


def _registry(text, key, cont=re.compile(r"^\s{2,}\S")):
    """Пункт реестра: строка с ключом + продолжения (отступ ≥ 2)."""
    lines = text.split("\n")
    res = []
    for i, ln in enumerate(lines):
        if key in ln and (ln.startswith("- ") or ln.startswith("|")):
            res.append(ln)
            j = i + 1
            while j < len(lines) and cont.match(lines[j]) and not lines[j].startswith("|"):
                res.append(lines[j])
                j += 1
    return "\n".join(res)


def _records(text, prefix):
    """Записи list-YAML по префиксу id, дословно, без вложенного parts:."""
    lines = text.split("\n")
    out, i = [], 0
    while i < len(lines):
        if re.match(r"^\s*-\s+u:", lines[i]):
            j = i
            cur = []
            while j < len(lines):
                ln = lines[j]
                if j > i and re.match(r"^\s*-\s+u:", ln):
                    break
                cur.append(ln)
                j += 1
            if any(re.search(rf"^\s*id:\s*{re.escape(prefix)}", x) for x in cur):
                keep, skip = [], False
                for x in cur:
                    if re.match(r"^\s+parts:\s*$", x):
                        skip = True
                        keep.append(x)
                        continue
                    if skip:
                        if re.match(r"^\s{2}\S", x) and not re.match(r"^\s{4,}", x):
                            skip = False
                        else:
                            continue
                    keep.append(x)
                out.extend(keep + [""])
            i = j
        else:
            i += 1
    return "\n".join(out).rstrip()


def _spec10(prof_main, neighbours):
    """SPEC-10 — выборкой (Д-147): строки design_input + образец + соседи по u/телу."""
    text = open(os.path.join(ROOT, "specs/SPEC-10_PTK_CALC.md"), encoding="utf-8").read()
    rows, head, seen = [], [], set()
    for ln in text.split("\n"):
        if ln.startswith("| ID |"):
            head = [ln]
        elif ln.startswith("|---") and head and len(head) == 1:
            head.append(ln)
        elif ln.startswith("| PTK-"):
            c = [x.strip() for x in ln.strip().strip("|").split("|")]
            if c[0] in seen:
                continue
            seen.add(c[0])
            rows.append((c, ln))
    prefixes = [d["id"] for d in yaml_ids()]
    chosen, why = [], {}
    for c, ln in rows:
        for pr in prefixes:
            if c[0].startswith(pr):
                chosen.append(c[0]); why[c[0]] = "designs[] (ptk_design_input)"
    main = next(((c, ln) for c, ln in rows if c[0] == prof_main), None)
    if main:
        if main[0][0] not in why:
            chosen.append(main[0][0])
        why[main[0][0]] = "ОБЯЗАТЕЛЬНО: основной образец (Д-147)"
        u, rol, d_out = main[0][1], main[0][2], float(main[0][15])
        near = sorted(((c, ln) for c, ln in rows
                       if c[1] == u and c[2] == rol and c[0] != prof_main),
                      key=lambda t: abs(float(t[0][15]) - d_out))[:neighbours]
        for c, ln in near:
            if c[0] not in why:
                chosen.append(c[0])
                why[c[0]] = f"соседняя позиция: u {u}, то же тело, |D − D_обр| = {abs(float(c[15]) - d_out):g} мм"
    out = ["### FRAGMENT: specs/SPEC-10_PTK_CALC.md — «Результаты» выборкой (Д-147, не целиком)\n",
           "Отбор: " + "; ".join(f"`{k}` — {v}" for k, v in why.items()) + ".\n"]
    out += head + [ln for c, ln in rows if c[0] in chosen]
    return "\n".join(out) + "\n", chosen


def yaml_ids():
    import yaml
    return yaml.safe_load(open(os.path.join(ROOT, "specs/ptk_design_input.yaml"), encoding="utf-8"))["designs"]


def build(prof, base, cp, out, allow_missing=False, opt=False):
    P = PROFILES[prof]
    doc, manifest, problems = [], {"profile": prof, "base": base, "cp": cp, "files": []}, []
    doc.append(f"# КОНТЕКСТ — {P['title']}\n\n"
               f"- Профиль: `{prof}` (пол по INS-91B §10, Д-146)\n"
               f"- База: `{base}`\n- Задача: `{cp}`\n"
               f"- Собрано: `python3 tools/ctx_local.py --profile {prof}`\n"
               "- Правило: файлы ниже — дословные, с sha256; при расхождении хэша "
               "контекст недействителен.\n")
    for rel in P["whole"]:
        try:
            b, h = block(rel)
        except FileNotFoundError:
            problems.append(f"нет обязательного файла: {rel}")
            continue
        doc.append(b)
        manifest["files"].append({"path": rel, "sha256": h, "mode": "whole",
                                  "bytes": len(read(rel))})
    for rel in (P["optional"] if opt else []):
        try:
            b, h = block(rel)
        except FileNotFoundError:
            manifest["files"].append({"path": rel, "mode": "absent"})
            continue
        doc.append(b)
        manifest["files"].append({"path": rel, "sha256": h, "mode": "whole"})

    dec = read("specs/DECISIONS.md").decode()
    frag = [f"### FRAGMENT: specs/DECISIONS.md ({', '.join(P['decisions'] + P['oq'])})\n"]
    for k in P["decisions"] + P["oq"]:
        s = _registry(dec, k)
        frag.append(f"#### {k}\n{s if s else '— не найдено —'}\n")
    doc.append("\n".join(frag))

    plan = read("specs/CODE_PLAN.md").decode()
    doc.append("### FRAGMENT: specs/CODE_PLAN.md — серия «Венец .01»\n"
               + "\n".join(_registry(plan, k) for k in P["cp_prefix"]) + "\n")

    stock = read("specs/stock.yaml").decode()
    doc.append("### FRAGMENT: specs/stock.yaml — разделы марок\n"
               + "\n".join(f"#### {k}\n{_section(stock, k)}" for k in P["stock_keys"]) + "\n")

    prods = read("specs/products.yaml").decode()
    doc.append("### FRAGMENT: specs/products.yaml — детали\n"
               + "\n".join(f"#### parts.{n}\n{_section(prods, repr(n))}" for n in P["product_parts"]) + "\n")

    cfgs = read("specs/ptk_configs.yaml").decode()
    recs = "\n".join(_records(cfgs, i) for i in P["config_ids"])
    doc.append("### FRAGMENT: specs/ptk_configs.yaml — записи (без parts:, Д-139/3.4.1)\n" + recs + "\n")
    if P["main_id"] not in recs:
        problems.append(f"нет записи ptk_configs основного образца: {P['main_id']}")
    sp, chosen = _spec10(P["main_id"], P["spec10_neighbours"])
    doc.append(sp)
    if P["main_id"] not in chosen:
        problems.append(f"в выборке SPEC-10 нет основного образца: {P['main_id']}")
    manifest["spec10_rows"] = chosen
    doc.append("### Данные прогона\n"
               "- Таблица SPEC-10 после `d_out_max = 203`: `python3 main.py calc` (exit 0, 2026-11-27), "
               "57 исполнений; выгрузка — `out/specs/SPEC-10_PTK_CALC.md`.\n"
               "- `.assy.json` венца локально НЕ строится (нет cadquery) — запросить у заказчика.\n"
               "- Осевой порядок фаз — цитата `egm/ptk.py::phasing` (см. файл выше).\n"
               "- `specs/ptk_designs.yaml` (шаг 2) на базе построен до смены подшипника на "
               "NU213-ECJ — проработки в контекст НЕ подаются как актуальные.\n")
    text = "\n".join(doc)

    # самопроверка: каждый блок читается обратно и совпадает по sha
    for f in manifest["files"]:
        if f.get("mode") != "whole":
            continue
        rel, h = f["path"], f["sha256"]
        m = re.search(rf"### FILE: {re.escape(rel)}\n<!-- sha256 ([0-9a-f]{{64}}).*?\n```.*?\n(.*?)\n```",
                      text, re.S)
        if not m:
            problems.append(f"блок не найден в собранном тексте: {rel}")
        elif m.group(1) != h:
            problems.append(f"хэш блока не совпал: {rel}")
        elif sha(m.group(2).encode()) != h:
            problems.append(f"содержимое блока отличается от файла: {rel}")

    manifest["problems"] = problems
    if problems and not allow_missing:
        print("КОНТЕКСТ НЕ СОБРАН:")
        for p in problems:
            print(" -", p)
        return 2
    if out:
        with open(out, "w", encoding="utf-8") as f:
            f.write(text)
        with open(out + ".manifest.json", "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=1)
        print(f"собрано: {out} ({len(text.encode())} байт), файлов: {len(manifest['files'])}")
    else:
        print(f"ok: профиль {prof}, файлов {len(manifest['files'])}, проблем {len(problems)}")
    return 0


def check(prof):
    P = PROFILES[prof]
    bad = [r for r in P["whole"] if not os.path.exists(os.path.join(ROOT, r))]
    print(f"профиль {prof}: обязательно {len(P['whole'])}, есть {len(P['whole']) - len(bad)}")
    for r in bad:
        print("  НЕТ:", r)
    for r in P["optional"]:
        if not os.path.exists(os.path.join(ROOT, r)):
            print("  нет (необязательный):", r)
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--profile", default="ring", choices=sorted(PROFILES))
    ap.add_argument("--base", default="")
    ap.add_argument("--cp", default="")
    ap.add_argument("--out")
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--allow-missing", action="store_true")
    ap.add_argument("--with-optional", action="store_true")
    a = ap.parse_args()
    if a.check:
        return check(a.profile)
    base = a.base or subprocess.run(["git", "-C", ROOT, "rev-parse", "--short", "HEAD"],
                                    capture_output=True, text=True).stdout.strip()
    return build(a.profile, base, a.cp or "—", a.out, a.allow_missing, a.with_optional)


if __name__ == "__main__":
    sys.exit(main())
