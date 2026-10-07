"""python -m egm.cad <ID исполнения | ID детали> [...] [--phase φ | --row k]
                     [--step spline|poly|off]
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


def build(arg, configs, prods, phase=None, row=None, step_mode="spline"):
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
        if step_mode == "off":
            print("step: пропущен (--step off)")
            continue
        try:
            import cadquery  # noqa: F401
        except Exception as e:   # не только ImportError: DLL OCP, numpy, другой venv
            print(f"step: пропущен — cadquery не импортируется в {sys.executable}: "
                  f"{type(e).__name__}: {e}")
            continue
        print(f"step: строится ({step_mode}, {len(model.cut.pts)} точек профиля, "
              f"{len(model.holes)} отв.)…", flush=True)
        try:
            dt = step.export(model, out / f"{name}.step", step_mode)
            print(f"step: {out / (name + '.step')} ({dt:.1f} с)")
        except Exception:
            import traceback
            traceback.print_exc()
            raise ValueError(f"{part['id']}: ошибка построения STEP (traceback выше)")


def main(argv):
    ap = argparse.ArgumentParser(prog="python -m egm.cad", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="+")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--phase", type=float, help="фаза ряда φ, град (row_phases)")
    grp.add_argument("--row", type=int, help="номер ряда 1…rows")
    ap.add_argument("--step", choices=("spline", "poly", "off"), default="spline",
                    help="контур впадин в STEP: B-сплайн | ломаная | без STEP")
    a = ap.parse_args(argv)
    load = lambda n: json.loads((ROOT / "specs" / n).read_text(encoding="utf-8"))
    configs, prods = load("ptk_configs.json"), load("products.json")
    rc = 0
    for arg in a.ids:
        try:
            build(arg, configs, prods, a.phase, a.row, a.step)
        except (KeyError, ValueError) as e:
            print(f"ошибка: {e}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
