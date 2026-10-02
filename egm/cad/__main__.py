"""python -m egm.cad <ID исполнения | ID детали> [...] [--phase φ | --row k]
-> out/cad/<ID>/<деталь>[-r<k>].svg|.step

--phase φ / --row k — ряд редуктора: строится только венец этого ряда, на чертеже —
направление его эксцентрика. Данные — specs/ptk_configs.json, specs/products.json.
Коды выхода: 0 — ok; 1 — ID не найден / нет генератора / ошибка геометрии; 2 — аргументы.
"""
import argparse
import json
import sys
from pathlib import Path

from egm import products, ptk
from egm.cad import ptk_ring, step, svg

ROOT = Path(__file__).resolve().parents[2]
GENERATORS = {"ptk_ring": ptk_ring.build}


def _row(cfg, phase, row):
    if row is None and phase is None:
        return None
    for r in cfg["phasing"]:
        if r["row"] == row or (phase is not None and abs(r["phi"] - phase % 360) < 1e-6):
            return r["row"]
    raise ValueError(f"ряд {row if row is not None else f'φ={phase:g}°'} не найден; "
                     f"фазы: {[r['phi'] for r in cfg['phasing']]}")


def build(arg, configs, prods, phase=None, row=None):
    cfg = ptk.find(configs, arg)
    if not cfg["ok"]:
        print(f"предупреждение: {cfg['id']} нереализуема: {'; '.join(cfg['errors'])}")
    k = _row(cfg, phase, row)
    parts = [p for p in cfg["parts"] if ("." not in arg or p["id"] == arg)
             and (k is None or k in p["rows"])]
    if not parts:
        raise KeyError(f"{arg}: нет детали (ряд {k}) или она не сгенерирована калькулятором")
    out = ROOT / "out" / "cad" / cfg["id"]
    out.mkdir(parents=True, exist_ok=True)
    for part in parts:
        gen = products.item(prods, part["id"]).get("cad")
        if gen not in GENERATORS:
            print(f"{part['id']}: генератора нет (products.json → cad)")
            continue
        model = GENERATORS[gen](cfg, part, k)
        name = part["id"].split(".", 1)[1] + (f"-r{k}" if k else "")
        (out / f"{name}.svg").write_text(svg.render(model), encoding="utf-8", newline="\n")
        print(f"svg: {out / (name + '.svg')}")
        try:
            step.export(model, out / f"{name}.step")
            print(f"step: {out / (name + '.step')}")
        except ImportError:
            print("step: пропущен — нет cadquery (pip install cadquery)")


def main(argv):
    ap = argparse.ArgumentParser(prog="python -m egm.cad", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="+")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--phase", type=float, help="фаза ряда φ, град (row_phases)")
    grp.add_argument("--row", type=int, help="номер ряда 1…rows")
    a = ap.parse_args(argv)
    load = lambda n: json.loads((ROOT / "specs" / n).read_text(encoding="utf-8"))
    configs, prods = load("ptk_configs.json"), load("products.json")
    rc = 0
    for arg in a.ids:
        try:
            build(arg, configs, prods, a.phase, a.row)
        except (KeyError, ValueError) as e:
            print(f"ошибка: {e}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
