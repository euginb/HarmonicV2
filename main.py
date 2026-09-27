"""Точка входа: python main.py -> out/. Код выхода 0 — все проверки пройдены."""
import json
import sys
from pathlib import Path

from egm import ptk

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
        table.append(f"| {r['u']} | {r['body']} | {r['d_body']} | {r['n_bodies']} | "
                     f"{r['z_ring']} | {r['ecc']} | {r['d_pitch']} | {r['d_out']} | "
                     f"{r['width']} | {m} | {'OK' if r['ok'] else 'нет'} |")
        errs += [f"- u={r['u']}, {r['body']}: {e}" for e in r["errors"]]
    tpl = (TPL / "SPEC-10_PTK_CALC.md.tmpl").read_text(encoding="utf-8")
    n_ok = sum(r["ok"] for r in rows)
    write("SPEC-10_PTK_CALC.md", tpl.format(rows="\n".join(table),
          errors="\n".join(errs) or "нет", n_ok=n_ok, n_all=len(rows)))


def main():
    fails = []
    try:
        ptk.self_test()
    except AssertionError as e:
        fails.append(f"ptk.self_test: {e}")
    run_ptk(load_json("vendor_prices.json"))
    # TODO(CP-02): catalog.build(); TODO(CP-03): cost.report(); TODO(CP-04): machines
    write("checks.md", "# Проверки\n\n" + ("\n".join(fails) or "все пройдены") + "\n")
    print("FAIL" if fails else "OK", *fails, sep="\n")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
