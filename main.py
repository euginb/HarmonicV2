"""Точка входа: python main.py [calc|design|all] [--publish]. Код выхода 0 — все проверки.

Шаги (Д-60): calc — шаг 1 «Расчёт» (SPEC-10, ptk_configs.json из ptk_input.yaml +
vendor_prices.yaml); design — шаг 2 «Проработка» (SPEC-11, ptk_designs.json из
ptk_design_input.yaml по ОПУБЛИКОВАННОМУ specs/ptk_configs.json — связка выход шага 1 →
вход шага 2); all (по умолчанию) — весь прогон, как прежде: шаг 1 → шаг 2 по его
результату → проверки products → каталог.

Конфигурация — configs/application.yaml (Д-64): пути, ссылки на пучок конфигов
(configs:), разделы продуктов (products.PTK — входы шагов 1 и 2), механизм чертежей (cad:).

out/specs/   — code-first спецификации и БД -> переносятся в specs/   (Д-14)
out/reports/ — отчёты прогона               -> переносятся в reports/ (Д-14)
--publish    — скопировать самому: reports — всегда, specs — только при коде 0.
"""
import json
import re
import shutil
import sys
from pathlib import Path

from egm import catalog, config, naming, products, ptk, ptk_design, ptk_force, ptk_parts, ptk_profile
from egm.cad import (assy as cad_assy, freecad as cad_freecad, ptk_ring, ptk_sep, ptk_spacer,
                     step as cad_step, techdraw as cad_techdraw)

ROOT = Path(__file__).resolve().parent
APP = config.load_app()                     # общий конфиг приложения (Д-64)
PATHS = APP.get("paths") or {}
SPECS = ROOT / PATHS.get("specs", "specs")      # каталоги — application.yaml (Д-64)
REPORTS = ROOT / PATHS.get("reports", "reports")
TPL = ROOT / PATHS.get("templates", "templates")
OUT = ROOT / PATHS.get("out", "out")
DEST = {"specs": SPECS, "reports": REPORTS}


def write(kind, name, text):
    """kind: 'specs' | 'reports' (Д-14)."""
    d = OUT / kind
    d.mkdir(parents=True, exist_ok=True)
    (d / name).write_text(text, encoding="utf-8", newline="\n")


FIELD_RE = re.compile(r"\{([A-Za-z_]\w*)\}")


def fill(tpl, **kw):
    """Подстановка полей {name} шаблона за один проход -> (текст, отсутствующие поля).

    Не str.format: в шаблоне LaTeX ($D_\\text{ш}$), его скобки — не поля. Заменяются
    только переданные ключи; прочие {…} и скобки в подставленных значениях не трогаются."""
    missing = sorted(k for k in kw if "{" + k + "}" not in tpl)
    text = FIELD_RE.sub(lambda m: str(kw[m[1]]) if m[1] in kw else m[0], tpl)
    return text, missing


def fill_self_test():
    t, miss = fill(r"$D_\text{ш}$ {a} {b} {x}", a=1, b="{a}", c=0)
    assert t == r"$D_\text{ш}$ 1 {a} {x}" and miss == ["c"], (t, miss)
    return True


def publish(ok):
    for kind, dst in DEST.items():
        if kind == "specs" and not ok:
            print("publish: specs/ не обновлены — есть непрошедшие проверки")
            continue
        src = OUT / kind
        if not src.exists():
            continue
        dst.mkdir(exist_ok=True)
        for f in sorted(src.iterdir()):
            if f.is_file():
                shutil.copy2(f, dst / f.name)
                print(f"publish: {kind}/{f.name}")


def run_ptk(prices):
    """SPEC-10: калькулятор ПТК по входу шага 1 (application.yaml → products.PTK, Д-64)."""
    try:
        lim, mounts, fast, mode = ptk.load_config(
            config.load(config.cfg_file(APP, "products.PTK.configs.input")))
    except (KeyError, ValueError, TypeError) as e:
        return [f"products.PTK.configs.input: {e!r}"]
    rows = ptk.to_rows(ptk.sweep(prices["rollers"], prices.get("bearings", {}), lim, mounts,
                                 fast, mode), mounts)
    write("specs", "ptk_configs.json", json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    table, errs, warns, excl = [], [], [], []
    for r in rows:
        if r["excluded"]:                                # Д-45: не молча — в конец SPEC-10
            excl.append(f"| {r['id']} | {r['u']} | {r['roller']} | {r['gen']} | {r['excluded']} |")
            continue
        m = f"{r['M']:g} ({r['M_by']})" if r["M"] else "—"
        gen = (r["bearing"] or "—") if r["gen"] == "bearing" else "эксцентрик"
        st = ("OK" if r["ok"] else "нет") + (f" ({', '.join(r['tech'])})" if r["tech"] else "")
        table.append(f"| {r['id']} | {r['u']} | {r['roller']} | {r['Drol']} | "
                     f"{r['Drol_max'] or '—'} | "
                     f"{r['n']} | {r['z']} | {r['a_w']} | {gen} | "
                     f"{r['Dgen'] or '—'} | {r['d_root']} | "
                     f"{r['alpha_max'] or '—'} | "
                     f"{(r['holes'] + ' (' + r['mount'] + ')') if r['holes'] else '—'} | "
                     f"{r['ring_variants'] or '—'} | {r['d_bc']} | {r['d_out']} | "
                     f"{r['width']} | {m} | {r['t_hold']} | {st} |")
        tag = f"- u={r['u']}, {r['roller']}, {r['gen']}: "
        errs += [tag + e for e in r["errors"]]
        warns += [tag + w for w in r["warnings"]]
    tpl = (TPL / "SPEC-10_PTK_CALC.md.tmpl").read_text(encoding="utf-8")
    phasing = "\n\n".join(f"### Крепление `{k}`\n\n" + ptk.phasing_table(lim, h)
                          for k, h in mounts.items())
    text, missing = fill(
        tpl,
        rows="\n".join(table),
        profile=(ptk_profile.theory_md() + "\n\n" + ptk_force.theory_md() + "\n\n"
                 + ptk.profile_table([r for r in rows if not r["excluded"]])),
        errors="\n".join(errs) or "нет", warnings="\n".join(warns) or "нет",
        n_ok=sum(r["ok"] for r in rows), n_all=len(table), n_excl=len(excl),
        tech=ptk.tech_md(),
        parts=ptk_parts.table(rows),
        excluded=("| ID | u | Тело | Генератор | Код |\n|---|---|---|---|---|\n" + "\n".join(excl))
                 if excl else "нет",
        two_stage=ptk.two_stage_table(lim), phasing=phasing)
    write("specs", "SPEC-10_PTK_CALC.md", text)
    bad = [f"SPEC-10: в шаблоне нет полей {missing}"] if missing else []
    ids = [r["id"] for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        bad.append(f"ptk: одинаковые ID {dup} — одно тело под разными ключами "
                   "vendor_prices.yaml → rollers (Д-22)")
    return bad


def run_catalog(prices):
    """CP-02: CAT-01 -> catalog_hiwin_hg.json, пары (Д-10), отчёт проверок."""
    md = config.cfg_file(APP, "configs.catalog_md")
    db = catalog.parse_md(md.read_text(encoding="utf-8"), source=md.name)
    pairs = catalog.build_pairs(db)
    rep = catalog.validate(db, pairs, prices)
    write("specs", "catalog_hiwin_hg.json", json.dumps(db, ensure_ascii=False, indent=1) + "\n")
    write("specs", "catalog_hiwin_hg_pairs.json", catalog.pairs_json(pairs))
    write("reports", "catalog_report.md", catalog.report_md(db, pairs, rep))
    return [f"catalog: {e}" for e in rep["errors"]]


def run_design(cfg_rows, require=False):
    """SPEC-11: проработка выбранных исполнений, шаг 2 (Д-48).

    cfg_rows — исполнения шага 1 (ptk_configs.json): полный прогон — свежие из
    out/specs/, режим design — опубликованные specs/ (связь выход шага 1 → вход
    шага 2, Д-60)."""
    if not config.cfg_file(APP, "products.PTK.configs.design_input").exists():
        if require:
            return ["products.PTK.configs.design_input: файл не найден — "
                    "проработки designs[] не заданы"]
        return []
    if cfg_rows is None:
        if require:
            return ["specs/ptk_configs.json: не найден — сначала шаг 1: "
                    "python main.py calc --publish (Д-60)"]
        return []
    try:
        lim = ptk.load_config(
            config.load(config.cfg_file(APP, "products.PTK.configs.input")))[0]
        stock = config.cfg_file(APP, "configs.stock")
        extra = {"prods": config.load(config.cfg_file(APP, "configs.products")),
                 "bears": config.load(
                     config.cfg_file(APP, "configs.vendor_prices")).get("bearings", {}),
                 "stock": config.load(stock) if stock.exists() else None}
        res = ptk_design.run(config.load(
            config.cfg_file(APP, "products.PTK.configs.design_input")), cfg_rows, lim, extra)
    except (KeyError, ValueError, TypeError) as e:
        return [f"входные конфиги шага 2 (Д-64): {e!r}"]
    write("specs", "ptk_designs.json", json.dumps(res, ensure_ascii=False, indent=2) + "\n")
    tpl = (TPL / "SPEC-11_PTK_DESIGN.md.tmpl").read_text(encoding="utf-8")
    text, missing = fill(tpl, **ptk_design.md(res))
    write("specs", "SPEC-11_PTK_DESIGN.md", text)
    return [f"SPEC-11: в шаблоне нет полей {missing}"] if missing else []


def main(argv):
    args = argv[1:]
    mode = "all"
    if args and args[0] in ("calc", "design", "all"):
        mode = args.pop(0)
    for kind in DEST:
        shutil.rmtree(OUT / kind, ignore_errors=True)
    fails = []
    if mode in ("all", "calc"):         # шаг 1: проверки ПО + расчёт по диапазону (SPEC-10)
        for name, test in (("config", config.self_test), ("ptk", ptk.self_test),
                           ("naming", naming.self_test),
                           ("catalog", catalog.self_test), ("products", products.self_test),
                           ("ptk_profile", ptk_profile.self_test), ("cad", ptk_ring.self_test),
                           ("fill", fill_self_test), ("step", cad_step.self_test),
                           ("freecad", cad_freecad.self_test),
                           ("force", ptk_force.self_test), ("parts", ptk_parts.self_test),
                           ("sep_svg", ptk_sep.self_test), ("spacer", ptk_spacer.self_test),
                           ("assy", cad_assy.self_test),
                           ("techdraw", cad_techdraw.self_test),
                           ("design", ptk_design.self_test)):
            try:
                test()
            except AssertionError as e:
                fails.append(f"{name}.self_test: {e!r}")
            except Exception as e:      # CP-45: не AssertionError — тоже строка в checks.md, прогон идёт
                import traceback
                f = traceback.extract_tb(e.__traceback__)[-1]
                fails.append(f"{name}.self_test: {e!r} ({f.filename.replace(chr(92), '/').rsplit('/', 1)[-1]}:{f.lineno})")
        try:
            prods = config.load(config.cfg_file(APP, "configs.products"))
            prices = config.load(config.cfg_file(APP, "configs.vendor_prices"))
            fails += products.check_app(APP, prods)   # Д-64: разделы продуктов есть в реестре
            fails += run_ptk(prices)
            cfg_path = OUT / "specs" / "ptk_configs.json"
            rows = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else None
            if mode == "all":           # шаг 2 — по свежим исполнениям шага 1
                fails += run_design(rows)
            if cfg_path.exists():
                fails += products.check(prods,
                                        json.loads(cfg_path.read_text(encoding="utf-8")))
            if mode == "all":
                fails += run_catalog(prices)
        except (KeyError, ValueError, TypeError) as e:
            fails.append(f"входные конфигурации: {e!r}")
    elif mode == "design":              # шаг 2 — по ОПУБЛИКОВАННОМУ шагу 1 (Д-60)
        cfg_path = SPECS / "ptk_configs.json"
        rows = json.loads(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else None
        fails += run_design(rows, require=True)
    # TODO(CP-03): cost.report(); TODO(CP-04): машины по naming.MACHINES (HMC + VMC)
    write("reports", "checks.md", "# Проверки прогона (code-first, НЕ ПРАВИТЬ РУКАМИ)\n\n"
          + ("\n".join(f"- {f}" for f in fails) or "все пройдены") + "\n")
    ok = not fails
    print("OK" if ok else "FAIL", *fails, sep="\n")
    if "--publish" in args:
        publish(ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
