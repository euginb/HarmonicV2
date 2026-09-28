"""Точка входа: python main.py -> out/. Код выхода 0 — все проверки пройдены."""
import json
import sys
from pathlib import Path

from egm import catalog, naming, ptk

ROOT = Path(__file__).resolve().parent
SPECS, OUT, TPL = ROOT / "specs", ROOT / "out", ROOT / "templates"


def load_json(name):
    return json.loads((SPECS / name).read_text(encoding="utf-8"))


def write(name, text):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(text, encoding="utf-8", newline="\n")


def run_ptk(prices):
    rows = ptk.to_rows(ptk.sweep(prices["bodies"]))
    write("ptk_configs.json", json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    table, errs = [], []
    for r in rows:
        m = r["torque_Nm_est"] if r["ok"] else "—"
        table.append(f"| {r['u']} | {r['body']} | {r['d_body']} | {r['d_body_max']} | {r['n_bodies']} | "
                     f"{r['z_ring']} | {r['ecc']} | {r['d_pitch']} | {r['d_out']} | "
                     f"{r['width']} | {m} | {'OK' if r['ok'] else 'нет'} |")
        errs += [f"- u={r['u']}, {r['body']}: {e}" for e in r["errors"]]
    tpl = (TPL / "SPEC-10_PTK_CALC.md.tmpl").read_text(encoding="utf-8")
    n_ok = sum(r["ok"] for r in rows)
    write("SPEC-10_PTK_CALC.md", tpl.format(rows="\n".join(table),
          errors="\n".join(errs) or "нет", n_ok=n_ok, n_all=len(rows),
          two_stage=ptk.two_stage_table()))


def run_catalog(prices):
    """CP-02: CAT-01 -> catalog_hiwin_hg.json, пары (Д-10), отчёт проверок."""
    md = ROOT / "docs" / "HG-Series-Catalog_opt.md"
    db = catalog.parse_md(md.read_text(encoding="utf-8"), source=md.name)
    pairs = catalog.build_pairs(db)
    rep = catalog.validate(db, pairs, prices)
    write("catalog_hiwin_hg.json", json.dumps(db, ensure_ascii=False, indent=1) + "\n")
    write("catalog_hiwin_hg_pairs.json", catalog.pairs_json(pairs))
    write("catalog_report.md", catalog.report_md(db, pairs, rep))
    return [f"catalog: {e}" for e in rep["errors"]]


def main():
    fails = []
    for name, test in (("ptk", ptk.self_test), ("naming", naming.self_test),
                       ("catalog", catalog.self_test)):
        try:
            test()
        except AssertionError as e:
            fails.append(f"{name}.self_test: {e!r}")
    prices = load_json("vendor_prices.json")
    run_ptk(prices)
    fails += run_catalog(prices)
    # TODO(CP-03): cost.report(); TODO(CP-04): машины по naming.MACHINES (HMC + VMC)
    write("checks.md", "# Проверки\n\n" + ("\n".join(fails) or "все пройдены") + "\n")
    print("FAIL" if fails else "OK", *fails, sep="\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
