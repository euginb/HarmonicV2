"""python -m egm.cad <ID исполнения | ID детали> [...] [--phase φ | --row k]
                     [--step spline|poly|off] [--assy] [--design NAME]
-> out/cad/<ID>/<деталь>[-r<k>].svg|.step
--assy — сборка исполнения: out/cad/<ID>/<ID>.step + <ID>.assy.json (Д-49).
--design NAME или ID детали <ID>.03B-NAME — эксцентрики и вал проработки шага 2 (Д-48)
из specs/ptk_designs.json; файлы <деталь>-NAME…, сборка <ID>-NAME.step.

--phase φ / --row k — ряд редуктора: строится только венец этого ряда, на чертеже —
направление его эксцентрика.
--spec specs/cad_set.yaml — комплект чертежей по спецификации (Д-61): записи items[] —
исполнения целиком (id, design, assy, фильтры rows/parts); ID из командной строки —
низкоуровневый путь. Данные — specs/ptk_configs.json, specs/products.yaml.
Пути в выводе — от корня репозитория; весь вывод консоли дублируется в
reports/cad_report.md (Д-14, переписывается каждым запуском; в конце лога — куда
сохранён) с легендой каждой позиции: что это за чертёж и что это за деталь.
Коды выхода: 0 — ok; 1 — ID не найден / нет генератора / ошибка геометрии; 2 — аргументы.
"""
import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

from egm import config, products, ptk, ptk_design
from egm.cad import assy, ptk_cover, ptk_ecc, ptk_ring, ptk_sep, ptk_spacer, step, svg

ROOT = Path(__file__).resolve().parents[2]
GENERATORS = {"ptk_ring": ptk_ring.build, "ptk_sep": ptk_sep.build, "ptk_ecc": ptk_ecc.build,
              "ptk_spacer": ptk_spacer.build, "ptk_cover": ptk_cover.build}


def _rel(p):
    """Путь для вывода — от корня репозитория: полный путь избыточен."""
    return p.relative_to(ROOT)


class _Report:
    """Дубликат вывода консоли в reports/cad_report.md (Д-14): say — консоль и отчёт,
    only — только отчёт (легенда позиции). Без path — только консоль."""

    def __init__(self, path=None):
        self.path = path
        self._fh = None
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            self._fh = path.open("w", encoding="utf-8", newline="\n")

    def say(self, text="", flush=False):
        print(text, flush=flush)
        self._write(text)

    def only(self, text=""):
        self._write(text)

    def _write(self, text):
        if self._fh:
            self._fh.write(text + "\n")
            self._fh.flush()

    def close(self):
        if self._fh:
            self._fh.close()
            self._fh = None


_CONSOLE = _Report()      # по умолчанию — только консоль (self-тесты, чужие вызовы build)


def _open_report(argv):
    """Отчёт прогона reports/cad_report.md (Д-14): переписывается каждым запуском,
    в конце лога печатается, куда он сохранён."""
    rep = _Report(ROOT / "reports" / "cad_report.md")
    rep.only("# Отчёт построения чертежей (code-first, НЕ ПРАВИТЬ РУКАМИ)\n")
    rep.only(f"- Запуск: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    rep.only(f"- Команда: python -m egm.cad {' '.join(argv)}\n")
    return rep


def _legend(rep, cfg, part, gen, des, name, prod):
    """Легенда позиции в отчёте: что это за чертёж и что это за деталь."""
    nn = part["id"].split(".", 1)[1][:2]
    pname = part.get("name") or prod.get("name") or ""   # у деталей проработки name нет
    rep.only(f"### {name} — {pname}\n")
    rep.only(f"Деталь {nn} «{pname}» исполнения {cfg['id']}"
             + (f", вариант {part['variant']}" if part.get("variant") else "")
             + f"; ряды пакета: {', '.join(str(r) for r in part.get('rows', []))}.")
    rep.only(f"Чертёж: SVG — 2D-вид по оси (1:1, мм), STEP — 3D-модель (egm/cad/{gen}.py).")
    if des:
        rep.only(f"Проработка: {des['name']} (шаг 2, SPEC-11) — эксцентрики и вал.")
    rep.only("")


def _legend_assy(rep, cfg, tag, des, man):
    """Легенда сборки в отчёте."""
    rep.only(f"### {tag} — сборка исполнения\n")
    rep.only(f"Сборка исполнения {cfg['id']} одним STEP (Д-49): дерево рядов и деталей, "
             f"слои, атрибуты CAx-IF; дубль дерева и метаданных — {_rel(man)} (Д-50)."
             + (f" Эксцентрики и вал — проработка {des['name']} (шаг 2, SPEC-11)." if des
                else ""))
    rep.only("")


def _row(cfg, phase, row):
    if row is None and phase is None:
        return None
    for r in cfg["phasing"]:
        if r["row"] == row or (phase is not None and abs(r["phi"] - phase % 360) < 1e-6):
            return r["row"]
    raise ValueError(f"ряд {row if row is not None else f'φ={phase:g}°'} не найден; "
                     f"фазы: {[r['phi'] for r in cfg['phasing']]}")


def build(arg, configs, prods, phase=None, row=None, step_mode="spline", des=None,
          only=None, rep=_CONSOLE):
    """only — подмножество позиций {"01", "02"} для спецификации комплекта (Д-61) или None."""
    cfg = ptk_design.apply(ptk.find(configs, arg), des)
    if not cfg["ok"]:
        why = cfg["errors"] or [f"исключено по технологии {cfg.get('excluded')} (Д-45, SPEC-10)"]
        rep.say(f"предупреждение: {cfg['id']} нереализуема: {'; '.join(why)}")
    k = _row(cfg, phase, row)
    parts = [p for p in cfg["parts"] if ("." not in arg or arg in (p["id"], p.get("base")))
             and (k is None or k in p["rows"])
             and (only is None or p["id"].split(".", 1)[-1][:2] in only)]
    if not parts:
        raise KeyError(f"{arg}: нет детали (ряд {k}) или она не сгенерирована калькулятором")
    out = ROOT / "out" / "cad" / cfg["id"]
    out.mkdir(parents=True, exist_ok=True)
    for part in parts:
        prod = products.item(prods, part.get("base", part["id"]))
        gen = prod.get("cad")
        if gen not in GENERATORS:
            rep.say(f"{part['id']}: генератора нет (products.yaml → cad)")
            continue
        name = part["id"].split(".", 1)[1] + (f"-r{k}" if k else "")
        _legend(rep, cfg, part, gen, des, name, prod)
        model = GENERATORS[gen](cfg, part, k)
        (out / f"{name}.svg").write_text(svg.render(model), encoding="utf-8", newline="\n")
        rep.say(f"svg: {_rel(out / (name + '.svg'))}")
        if step_mode == "off":
            rep.say("step: пропущен (--step off)")
            continue
        try:
            import cadquery  # noqa: F401
        except Exception as e:   # не только ImportError: DLL OCP, numpy, другой venv
            rep.say(f"step: пропущен — cadquery не импортируется в {sys.executable}: "
                    f"{type(e).__name__}: {e}")
            continue
        rep.say(f"step: строится ({step_mode}, {len(model.cut.pts)} точек профиля, "
                f"{len(model.holes)} отв.)…", flush=True)
        try:
            dt = step.export(model, out / f"{name}.step", step_mode)
            rep.say(f"step: {_rel(out / (name + '.step'))} ({dt:.1f} с)")
        except Exception:
            import traceback
            traceback.print_exc()
            raise ValueError(f"{part['id']}: ошибка построения STEP (traceback выше)")


def build_assy(arg, configs, prods, step_mode="spline", des=None, rep=_CONSOLE):
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
    _legend_assy(rep, cfg, tag, des, man)
    rep.say(f"assy: {_rel(man)}")
    sh = cfg["geom"]["limits"].get("shaft_d_min") or 0
    rep.say(f"вал Ø{sh:g}, эксцентрики .03 — " + (f"проработка {des['name']} (SPEC-11, Д-48)" if des
            else "предварительные шага 1 (limits.shaft_d_min); окончательные — --design"))
    lay = cfg.get("layout")
    if lay:
        rep.say(f"конструктив {lay['code']}: "
                + ", ".join(q["id"].split(".", 1)[1] for q in lay.get("cad_parts", []))
                + f"; .09 {(lay.get('b09') or {}).get('id', 'нет')}, "
                f".10 {(lay.get('b10') or {}).get('id', 'нет')}; длина {lay['length']:g} мм (CP-45)")
    if step_mode == "off":
        rep.say("step: пропущен (--step off)")
        return
    try:
        import cadquery  # noqa: F401
    except Exception as e:
        rep.say(f"step: пропущен — cadquery не импортируется в {sys.executable}: "
                f"{type(e).__name__}: {e}")
        return
    n = sum(len(r["inst"]) for r in p["rows"]) + len(p["root"])
    rep.say(f"step: сборка строится ({len(assy.items(p))} деталей, {n} экземпляров, "
            f"{step_mode})…", flush=True)
    path = out / f"{tag}.step"
    try:
        dt, meta = assy.export(cfg, prods, path, step_mode)
    except Exception:
        import traceback
        traceback.print_exc()
        raise ValueError(f"{cfg['id']}: ошибка построения STEP сборки (traceback выше)")
    rep.say(f"step: {_rel(path)} ({dt:.1f} с); метаданные в STEP: "
            + (f"{meta} узлов (PROPERTY_DEFINITION, Д-50)" if meta else "нет — только в .assy.json")
            + "; FreeCAD: макрос tools/freecad_meta.py")


def _resolve(configs, arg):
    """ID в спецификации -> запись configs: полный, деталь или префикс без хэша (Д-51)."""
    try:
        return ptk.find(configs, arg)
    except KeyError:
        c = [r for r in configs if r.get("id", "").startswith(arg)]
        if len(c) == 1:
            return c[0]
        if not c:
            raise
        raise ValueError(f"{arg}: неоднозначен: {[r['id'] for r in c]} — "
                         "уточнить полным ID из SPEC-10")


def _pick_design(designs, arg, name):
    """Проработка по ID (полный или префикс без хэша, Д-51) и имени — как шаг 2
    уточняет prefix+bearing/gen. Не найдена/неоднозначна — ошибка Д-48."""
    base = arg.split(".")[0]
    c = [r for r in designs if r["id"] == base and r["name"] == name and r.get("ecc")]
    if not c:
        c = [r for r in designs if r["id"].startswith(base) and r["name"] == name and r.get("ecc")]
    if len(c) == 1:
        return c[0]
    if len(c) > 1:
        raise ValueError(f"{arg}: проработок {name} несколько: {[r['id'] for r in c]} — "
                         "уточнить полным ID из SPEC-10")
    ptk_design.find(designs, base, name)        # не найдена — штатная ошибка Д-48


def run_spec(spec, configs, prods, designs, rep=_CONSOLE):
    """Комплект чертежей по спецификации (YAML, Д-61): записи items[] — исполнения
    целиком; строятся все детали с генераторами (products.yaml → cad), assy — сборка.
    Возвращает число записей, окончивших ошибкой."""
    data = config.load(spec)
    step_mode = data.get("step", "spline")
    bad = 0
    for i, item in enumerate(data.get("items", []), 1):
        arg = item.get("id")
        if not arg:
            rep.say(f"спецификация: запись {i}: нет id")
            bad += 1
            continue
        try:
            if item.get("design"):
                des = _pick_design(designs, arg, item["design"])
                full = des["id"]        # полный ID из записи проработки (текущий хэш)
            else:
                des = None
                full = _resolve(configs, arg)["id"]
            target = arg if "." in arg else full    # деталь — как задана
            if des is None:
                des = ptk_design.pick(designs, target)   # имя из хвоста ID детали или None
            only = None if item.get("parts", "all") == "all" \
                else {str(p).zfill(2)[:2] for p in item["parts"]}
            rows = item.get("rows", "all")
            if rows == "all":
                build(target, configs, prods, None, None, step_mode, des, only, rep)
            else:
                for k in rows:
                    build(target, configs, prods, None, k, step_mode, des, only, rep)
            if item.get("assy"):
                build_assy(target, configs, prods, step_mode, des, rep)
        except (KeyError, ValueError) as e:
            rep.say(f"ошибка: {e}")
            bad += 1
    return bad

def main(argv):
    ap = argparse.ArgumentParser(prog="python -m egm.cad", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("ids", nargs="*")
    grp = ap.add_mutually_exclusive_group()
    grp.add_argument("--phase", type=float, help="фаза ряда φ, град (row_phases)")
    grp.add_argument("--row", type=int, help="номер ряда 1…rows")
    ap.add_argument("--step", choices=("spline", "poly", "off"), default="spline",
                    help="контур впадин в STEP: B-сплайн | ломаная | без STEP")
    ap.add_argument("--assy", action="store_true",
                    help="сборка исполнения в один STEP: дерево, слои, метаданные (Д-49)")
    ap.add_argument("--design", help="проработка шага 2 из specs/ptk_designs.json (Д-48)")
    ap.add_argument("--spec", help="спецификация комплекта чертежей (YAML, Д-61), "
                                   "например specs/cad_set.yaml; вместе с ID не задаётся")
    a = ap.parse_args(argv)
    if not a.spec and not a.ids:
        ap.error("укажите ID исполнения/детали или --spec (комплект по спецификации, Д-61)")
    if a.spec and a.ids:
        ap.error("--spec и ID вместе не задаются")
    load = lambda n: json.loads((ROOT / "specs" / n).read_text(encoding="utf-8"))
    configs, prods = load("ptk_configs.json"), config.load("products.yaml")
    designs = load("ptk_designs.json") if (ROOT / "specs" / "ptk_designs.json").exists() else []
    rep = _open_report(argv)
    try:
        if a.spec:
            return 1 if run_spec(a.spec, configs, prods, designs, rep) else 0
        rc = 0
        for arg in a.ids:
            try:
                des = ptk_design.pick(designs, arg, a.design)
                if a.assy:
                    build_assy(arg, configs, prods, a.step, des, rep)
                else:
                    build(arg, configs, prods, a.phase, a.row, a.step, des, None, rep)
            except (KeyError, ValueError) as e:
                rep.say(f"ошибка: {e}")
                rc = 1
        return rc
    finally:
        rep.say(f"отчёт: {_rel(rep.path)}")
        rep.close()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
