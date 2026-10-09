"""python -m egm.cad <ID исполнения | ID детали> [...] [--phase φ | --row k]
                     [--step spline|poly|off] [--assy] [--design NAME]
-> out/cad/<ID>/<деталь>[-r<k>].svg|.step
--assy — сборка исполнения: out/cad/<ID>/<ID>.step + <ID>.assy.json (Д-49).
--design NAME или ID детали <ID>.03B-NAME — эксцентрики и вал проработки шага 2 (Д-48)
из specs/ptk_designs.json; файлы <деталь>-NAME…, сборка <ID>-NAME.step.

--phase φ / --row k — ряд редуктора: строится только венец этого ряда, на чертеже —
направление его эксцентрика. Данные — specs/ptk_configs.json, specs/products.json.
Коды выхода: 0 — ok; 1 — ID не найден / нет генератора / ошибка геометрии; 2 — аргументы.
"""
import argparse
import json
import sys
from pathlib import Path

from egm import products, ptk, ptk_design
from egm.cad import assy, ptk_ecc, ptk_ring, ptk_sep, ptk_spacer, step, svg

ROOT = Path(__file__).resolve().parents[2]
GENERATORS = {"ptk_ring": ptk_ring.build, "ptk_sep": ptk_sep.build, "ptk_ecc": ptk_ecc.build,
              "ptk_spacer": ptk_spacer.build}


def _row(cfg, phase, row):
    if row is None and phase is None:
        return None
    for r in cfg["phasing"]:
        if r["row"] == row or (phase is not None and abs(r["phi"] - phase % 360) < 1e-6):
            return r["row"]
    raise ValueError(f"ряд {row if row is not None else f'φ={phase:g}°'} не найден; "
                     f"фазы: {[r['phi'] for r in cfg['phasing']]}")


def build(arg, configs, prods, phase=None, row=None, step_mode="spline", des=None):
    cfg = ptk_design.apply(ptk.find(configs, arg), des)
    if not cfg["ok"]:
        why = cfg["errors"] or [f"исключено по технологии {cfg.get('excluded')} (Д-45, SPEC-10)"]
        print(f"предупреждение: {cfg['id']} нереализуема: {'; '.join(why)}")
    k = _row(cfg, phase, row)
    parts = [p for p in cfg["parts"] if ("." not in arg or arg in (p["id"], p.get("base")))
             and (k is None or k in p["rows"])]
    if not parts:
        raise KeyError(f"{arg}: нет детали (ряд {k}) или она не сгенерирована калькулятором")
    out = ROOT / "out" / "cad" / cfg["id"]
    out.mkdir(parents=True, exist_ok=True)
    for part in parts:
        gen = products.item(prods, part.get("base", part["id"])).get("cad")
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


def build_assy(arg, configs, prods, step_mode="spline", des=None):
    """Д-49: сборка исполнения -> out/cad/<ID>/<ID>.step + <ID>.assy.json."""
    cfg = ptk_design.apply(ptk.find(configs, arg), des)
    tag = cfg["id"] + (f"-{des['name']}" if des else "")
    if not cfg.get("sep") or not cfg.get("ecc"):
        raise ValueError(f"{cfg['id']}: нет деталей .02/.03 (нереализуемо или исключено) — "
                         f"сборка не строится")
    out = ROOT / "out" / "cad" / cfg["id"]
    out.mkdir(parents=True, exist_ok=True)
    p = assy.plan(cfg)
    man = out / f"{tag}.assy.json"
    data = assy.manifest(cfg, prods, p)
    if des:
        data["design"] = {k: des[k] for k in ("name", "shaft", "link", "mass")}
    man.write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n",
                   encoding="utf-8", newline="\n")
    print(f"assy: {man}")
    sh = cfg["geom"]["limits"].get("shaft_d_min") or 0
    print(f"вал Ø{sh:g}, эксцентрики .03 — " + (f"проработка {des['name']} (SPEC-11, Д-48)" if des
          else "предварительные шага 1 (limits.shaft_d_min); окончательные — --design"))
    if step_mode == "off":
        print("step: пропущен (--step off)")
        return
    try:
        import cadquery  # noqa: F401
    except Exception as e:
        print(f"step: пропущен — cadquery не импортируется в {sys.executable}: "
              f"{type(e).__name__}: {e}")
        return
    n = sum(len(r["inst"]) for r in p["rows"]) + len(p["root"])
    print(f"step: сборка строится ({len(assy.items(p))} деталей, {n} экземпляров, "
          f"{step_mode})…", flush=True)
    path = out / f"{tag}.step"
    try:
        dt, meta = assy.export(cfg, prods, path, step_mode)
    except Exception:
        import traceback
        traceback.print_exc()
        raise ValueError(f"{cfg['id']}: ошибка построения STEP сборки (traceback выше)")
    print(f"step: {path} ({dt:.1f} с); метаданные в STEP: "
          + (f"{meta} узлов (PROPERTY_DEFINITION, Д-50)" if meta else "нет — только в .assy.json")
          + "; FreeCAD: макрос tools/freecad_meta.py")


def main(argv):
    ap = argparse.ArgumentParser(prog="python -m egm.cad", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="+")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--phase", type=float, help="фаза ряда φ, град (row_phases)")
    grp.add_argument("--row", type=int, help="номер ряда 1…rows")
    ap.add_argument("--step", choices=("spline", "poly", "off"), default="spline",
                    help="контур впадин в STEP: B-сплайн | ломаная | без STEP")
    ap.add_argument("--assy", action="store_true",
                    help="сборка исполнения в один STEP: дерево, слои, метаданные (Д-49)")
    ap.add_argument("--design", help="проработка шага 2 из specs/ptk_designs.json (Д-48)")
    a = ap.parse_args(argv)
    load = lambda n: json.loads((ROOT / "specs" / n).read_text(encoding="utf-8"))
    configs, prods = load("ptk_configs.json"), load("products.json")
    designs = load("ptk_designs.json") if (ROOT / "specs" / "ptk_designs.json").exists() else []
    rc = 0
    for arg in a.ids:
        try:
            des = ptk_design.pick(designs, arg, a.design)
            if a.assy:
                build_assy(arg, configs, prods, a.step, des)
            else:
                build(arg, configs, prods, a.phase, a.row, a.step, des)
        except (KeyError, ValueError) as e:
            print(f"ошибка: {e}")
            rc = 1
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
