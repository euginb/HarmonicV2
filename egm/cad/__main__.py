"""python -m egm.cad <ID исполнения | ID детали> [...] -> out/cad/<ID>/<деталь>.svg|.step

Данные — specs/ptk_configs.json и specs/products.json (Д-22, Д-24).
Коды выхода: 0 — ok; 1 — ID не найден / нет генератора; 2 — нет аргументов.
"""
import json
import sys
from pathlib import Path

from egm import products, ptk
from egm.cad import ptk_ring

ROOT = Path(__file__).resolve().parents[2]
GENERATORS = {"ptk_ring": (ptk_ring.ring_geom, ptk_ring.step, ptk_ring.drawing)}


def build(arg, configs, prods):
    cfg = ptk.find(configs, arg)
    if not cfg["ok"]:
        print(f"предупреждение: {cfg['id']} нереализуема: {'; '.join(cfg['errors'])}")
    parts = [p for p in cfg["parts"] if "." not in arg or p["id"] == arg]
    if not parts:
        raise KeyError(f"{arg}: деталь не сгенерирована калькулятором или нет генератора")
    out = ROOT / "out" / "cad" / cfg["id"]
    out.mkdir(parents=True, exist_ok=True)
    for part in parts:
        gen = products.item(prods, part["id"]).get("cad")
        if gen not in GENERATORS:
            print(f"{part['id']}: генератора нет (products.json → cad)")
            continue
        geom_fn, step_fn, svg_fn = GENERATORS[gen]
        geo = geom_fn(cfg, part)
        name = part["id"].split(".", 1)[1]
        (out / f"{name}.svg").write_text(svg_fn(geo), encoding="utf-8", newline="\n")
        print(f"svg: {out / (name + '.svg')}")
        try:
            step_fn(geo, out / f"{name}.step")
            print(f"step: {out / (name + '.step')}")
        except ImportError:
            print("step: пропущен — нет cadquery (pip install cadquery)")


def main(argv):
    if not argv:
        print(__doc__)
        return 2
    load = lambda n: json.loads((ROOT / "specs" / n).read_text(encoding="utf-8"))
    configs, prods = load("ptk_configs.json"), load("products.json")
    rc = 0
    for arg in argv:
        try:
            build(arg, configs, prods)
        except (KeyError, ValueError) as e:
            print(f"ошибка: {e}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
