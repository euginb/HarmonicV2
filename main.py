"""Точка входа: python main.py [--publish]. Код выхода 0 — все проверки пройдены.

out/specs/   — code-first спецификации и БД -> переносятся в specs/   (Д-14)
out/reports/ — отчёты прогона               -> переносятся в reports/ (Д-14)
--publish    — скопировать самому: reports — всегда, specs — только при коде 0.
"""
import json
import re
import shutil
import sys
from pathlib import Path

from egm import catalog, naming, products, ptk, ptk_force, ptk_profile
from egm.cad import ptk_ring, step as cad_step

ROOT = Path(__file__).resolve().parent
SPECS, REPORTS, TPL = ROOT / "specs", ROOT / "reports", ROOT / "templates"
OUT = ROOT / "out"
DEST = {"specs": SPECS, "reports": REPORTS}


def load_json(name):
    return json.loads((SPECS / name).read_text(encoding="utf-8"))


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
    """SPEC-10: калькулятор ПТК по specs/ptk_input.json (Д-16, Д-18)."""
    try:
        lim, mounts, fast, mode = ptk.load_config(load_json("ptk_input.json"))
    except (KeyError, ValueError, TypeError) as e:
        return [f"ptk_input.json: {e!r}"]
    rows = ptk.to_rows(ptk.sweep(prices["rollers"], prices.get("bearings", {}), lim, mounts,
                                 fast, mode), mounts)
    write("specs", "ptk_configs.json", json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    table, errs, warns = [], [], []
    for r in rows:
        m = f"{r['M']:g} ({r['M_by']})" if r["M"] else "—"
        table.append(f"| {r['id']} | {r['u']} | {r['roller']} | {r['Drol']} | {r['Drol_max']} | "
                     f"{r['n']} | {r['z']} | {r['a_w']} | {r['bearing'] or '—'} | "
                     f"{r['Dgen'] or '—'} | {r['d_root']} | "
                     f"{r['alpha_max'] or '—'} | "
                     f"{(r['holes'] + ' (' + r['mount'] + ')') if r['holes'] else '—'} | "
                     f"{r['ring_variants'] or '—'} | {r['d_bc']} | {r['d_out']} | "
                     f"{r['width']} | {m} | {r['t_hold']} | {'OK' if r['ok'] else 'нет'} |")
        tag = f"- u={r['u']}, {r['roller']}: "
        errs += [tag + e for e in r["errors"]]
        warns += [tag + w for w in r["warnings"]]
    tpl = (TPL / "SPEC-10_PTK_CALC.md.tmpl").read_text(encoding="utf-8")
    params = "\n\n".join(f"Крепление `{k}` (режим `{mode}`, Д-33):\n\n" + ptk.params_md(lim, h, fast)
                         for k, h in mounts.items())
    phasing = "\n\n".join(f"### Крепление `{k}`\n\n" + ptk.phasing_table(lim, h)
                          for k, h in mounts.items())
    text, missing = fill(
        tpl,
        params=params, rows="\n".join(table),
        profile=(ptk_profile.theory_md() + "\n\n" + ptk_force.theory_md() + "\n\n"
                 + ptk.profile_table(rows)),
        errors="\n".join(errs) or "нет", warnings="\n".join(warns) or "нет",
        n_ok=sum(r["ok"] for r in rows), n_all=len(rows),
        two_stage=ptk.two_stage_table(lim), phasing=phasing)
    write("specs", "SPEC-10_PTK_CALC.md", text)
    bad = [f"SPEC-10: в шаблоне нет полей {missing}"] if missing else []
    ids = [r["id"] for r in rows]
    dup = sorted({i for i in ids if ids.count(i) > 1})
    if dup:
        bad.append(f"ptk: одинаковые ID {dup} — одно тело под разными ключами "
                   "vendor_prices.json → rollers (Д-22)")
    return bad


def run_catalog(prices):
    """CP-02: CAT-01 -> catalog_hiwin_hg.json, пары (Д-10), отчёт проверок."""
    md = ROOT / "docs" / "HG-Series-Catalog_opt.md"
    db = catalog.parse_md(md.read_text(encoding="utf-8"), source=md.name)
    pairs = catalog.build_pairs(db)
    rep = catalog.validate(db, pairs, prices)
    write("specs", "catalog_hiwin_hg.json", json.dumps(db, ensure_ascii=False, indent=1) + "\n")
    write("specs", "catalog_hiwin_hg_pairs.json", catalog.pairs_json(pairs))
    write("reports", "catalog_report.md", catalog.report_md(db, pairs, rep))
    return [f"catalog: {e}" for e in rep["errors"]]


def main(argv):
    for kind in DEST:
        shutil.rmtree(OUT / kind, ignore_errors=True)
    fails = []
    for name, test in (("ptk", ptk.self_test), ("naming", naming.self_test),
                       ("catalog", catalog.self_test), ("products", products.self_test),
                       ("ptk_profile", ptk_profile.self_test), ("cad", ptk_ring.self_test),
                       ("fill", fill_self_test), ("step", cad_step.self_test),
                       ("force", ptk_force.self_test)):
        try:
            test()
        except AssertionError as e:
            fails.append(f"{name}.self_test: {e!r}")
    prices = load_json("vendor_prices.json")
    fails += run_ptk(prices)
    cfg_path = OUT / "specs" / "ptk_configs.json"
    if cfg_path.exists():
        fails += products.check(load_json("products.json"), json.loads(cfg_path.read_text(encoding="utf-8")))
    fails += run_catalog(prices)
    # TODO(CP-03): cost.report(); TODO(CP-04): машины по naming.MACHINES (HMC + VMC)
    write("reports", "checks.md", "# Проверки прогона (code-first, НЕ ПРАВИТЬ РУКАМИ)\n\n"
          + ("\n".join(f"- {f}" for f in fails) or "все пройдены") + "\n")
    ok = not fails
    print("OK" if ok else "FAIL", *fails, sep="\n")
    if "--publish" in argv[1:]:
        publish(ok)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
