"""Сборка ПТК в один STEP (Д-49): дерево «исполнение → ряд k → детали», слои, цвета, метаданные.

Система корпуса: ось z — ось вала, z = 0 — торец пакета (как z0 окон сепаратора);
угол 0° — впадина 0 венца ряда 1; отверстия всех венцов пакета совпадают (Д-19).
Ряд k (φk, s_k из ptk.phasing): венец .01<вар> повёрнут на −s_k; эксцентрик .03<вар> — на φk,
паз шпонки тогда у всех рядов на key_angle; подшипник .08 — центр a_ω на угле φk; тела .04 —
ptk_profile.bodies(θe = φk + s_k), повёрнутые на −s_k, — попадают в окна .02 (cage, Д-46).
Детали .01–.03 — те же PartModel и step.solid, что у STEP деталей; .04, .08, вал — примитивы.
Одинаковые детали — одно определение и экземпляры с положением (тела — rows·n экземпляров).
Сохранённые виды AP242 (Views) OCCT не пишет — предлагаемые виды в <ID>.assy.json (OQ-14).
"""
import math
import re
import time
from pathlib import Path

from egm import products, ptk_profile
from egm.cad import ptk_cover, ptk_ecc, ptk_hub, ptk_ring, ptk_sep, ptk_spacer, step, techdraw

LAYERS = {"01": ("01_RING", "венец"), "02": ("02_CAGE", "сепаратор"),
          "03": ("03_ECC", "эксцентрик"), "04": ("04_BODIES", "тела качения"),
          "05": ("05_SPACER", "межрядные шайбы"), "07": ("07_COVER", "крышки"),
          "08": ("08_BEARING", "подшипник генератора"), "09": ("09_BEARING_OUT", "подшипник выхода"),
          "10": ("10_BEARING_IN", "подшипники входного вала"),
          "11": ("11_DIST", "дистанционные кольца эксцентриков"), "12": ("12_HUB", "ступица выхода"),
          "13": ("13_LEAF", "дно-лист"),
          "ref": ("REF", "примитивы: вал")}
COLORS = {"01": (0.55, 0.57, 0.60), "02": (0.80, 0.60, 0.20), "03": (0.30, 0.50, 0.80),
          "04": (0.85, 0.20, 0.20), "05": (0.45, 0.47, 0.52), "08": (0.20, 0.65, 0.30),
          "07": (0.62, 0.64, 0.68), "09": (0.20, 0.55, 0.25), "10": (0.25, 0.60, 0.35),
          "11": (0.35, 0.55, 0.85), "12": (0.75, 0.50, 0.20), "13": (0.60, 0.45, 0.30),
          "ref": (0.70, 0.70, 0.70)}
VIEWS = [{"name": "ISO", "dir": [1, -1, 1], "layers": "все"},
         {"name": "по оси", "dir": [0, 0, 1], "layers": "все"},
         {"name": "сбоку", "dir": [1, 0, 0], "layers": "все"},
         {"name": "без венцов и сепаратора", "dir": [1, -1, 1], "layers": "03, 04, 08, REF"}]
SCHEMA = "AP242DIS"
ALIAS = {"01": "RING", "02": "CAGE", "03": "ECC", "04": "BODY", "05": "SPACER",
         "07": "COVER", "08": "BEARING", "09": "BRG_OUT", "10": "BRG_IN", "11": "DIST",
         "12": "HUB", "13": "LEAF", "ref": "SHAFT"}   # Д-52: имена узлов STEP — только латиница
_ENT = re.compile(r"#(\d+)\s*=\s*([A-Z0-9_]+)\s*\((.*?)\)\s*;", re.S)
_TOK = re.compile(r"'EGM(\d+)'")


def _nn(pid):
    return pid.split(".", 1)[1][:2]


def _base(pid):
    """ID детали без суффикса проработки (Д-48): <ID>.03B-K8 -> <ID>.03B."""
    head, _, tail = pid.partition(".")
    return f"{head}.{tail.split('-')[0]}" if tail else pid


def _txt(v):
    return f"{v:g}" if isinstance(v, float) else str(v)


def _shaft(cfg):
    """Вал (REF) -> (z0, длина): с конструктивом шага 2 — от .07A до второй .10 в ступице."""
    lay = cfg.get("layout") or {}
    cov, cup, b10 = lay.get("covers"), lay.get("cup") or {}, lay.get("b10") or {}
    if cov and cup.get("z_in"):
        z0 = -cov["tA"] - 5.0
        return z0, cup["z_in"] + b10.get("B", 0.0) - z0
    return -5.0, cfg["sep"]["length"] + 10


def _layout_inst(cfg, rows):
    """CP-45: экземпляры конструктива шага 2 у корня (cfg["layout"] из ptk_design.apply):
    .07A [−tA, 0], .07B [W, W + tB], .11 между эксцентриками, .10 в .07A и в ступице, .09 в .07B."""
    lay, cid = cfg.get("layout") or {}, cfg["id"]
    cov, cup, W = lay.get("covers"), lay.get("cup") or {}, cfg["sep"]["length"]
    out = []

    def at(pid, nn, z):
        out.append({"id": pid, "nn": nn, "x": 0.0, "y": 0.0, "z": z, "ang": 0.0})
    for q in lay.get("cad_parts", []):
        nn = _nn(q["id"])
        if nn == "07" and cov:
            at(q["id"], nn, -cov["tA"] if q["side"] == "A" else W)
        elif nn == "11":
            for r in rows[:-1]:
                at(q["id"], nn, r["zc"] + cfg["ecc"]["t"] / 2)
        elif nn in ("12", "13") and cup.get("z_in"):  # CP-63: .12A | .12B от дна; CP-80: .13 за буртом,
            j = q.get("join") or {}                   # .12 (фланец) за дном-листом
            dz = (j.get("h_b", 0.0) + (j.get("t_s", 0.0) if nn == "12" else 0.0)) if j.get("hub") else 0.0
            at(q["id"], nn, round(cup["z_in"] + dz, 3))
    b09, b10 = lay.get("b09"), lay.get("b10")
    if b10 and cov:
        at(f"{cid}.10", "10", -b10["B"])
    pr = lay.get("parts", {})
    if b10 and cup.get("hub_d") and (pr.get("02") == "cup" or pr.get("12")):   # .10 в ступице .02A | .12
        at(f"{cid}.10", "10", cup["z_in"])
    if b09 and cov:
        at(f"{cid}.09", "09", W + cov["pocket"][1])
    return out


def plan(cfg):
    """Состав сборки без CadQuery -> {"rows": [...], "root": [...], "B", "pitch"}.

    Экземпляр {"id", "nn", "x", "y", "z", "ang"}: поворот на ang° вокруг z, затем сдвиг."""
    g, sep = cfg["geom"], cfg["sep"]
    rol, brg = g["roller"], g.get("bearing")
    a, R, n, cid = cfg["a_w"], cfg["R_sum"], int(cfg["n"]), cfg["id"]
    gap = g["limits"]["row_gap"]
    pitch = max(rol["l"], brg["B"]) if brg else rol["l"]
    by = {(_nn(p["id"]), r): p for p in cfg["parts"] for r in p["rows"]}
    ball = rol.get("type") == "ball"
    rows = []
    for k, ph in enumerate(cfg["phasing"]):
        rk, phi, sk = ph["row"], ph["phi"], ph["s"]
        zc = gap + k * (pitch + gap) + pitch / 2
        ex, ey = a * math.cos(math.radians(phi)), a * math.sin(math.radians(phi))
        inst = [{"id": by[("01", rk)]["id"], "nn": "01", "x": 0.0, "y": 0.0,
                 "z": zc - rol["l"] / 2, "ang": -sk},
                {"id": by[("03", rk)]["id"], "nn": "03", "x": 0.0, "y": 0.0,
                 "z": zc - cfg["ecc"]["t"] / 2, "ang": phi}]
        if brg:
            inst.append({"id": f"{cid}.08", "nn": "08", "x": ex, "y": ey,
                         "z": zc - brg["B"] / 2, "ang": 0.0})
        c, s = math.cos(math.radians(-sk)), math.sin(math.radians(-sk))
        for x, y in ptk_profile.bodies(a, R, n, phi + sk):
            inst.append({"id": f"{cid}.04", "nn": "04", "x": x * c - y * s, "y": x * s + y * c,
                         "z": zc if ball else zc - rol["l"] / 2, "ang": 0.0})
        rows.append({"row": rk, "phi": phi, "s": sk, "zc": zc, "ecc": (ex, ey), "inst": inst})
    root = [{"id": by[("02", rows[0]["row"])]["id"], "nn": "02",
             "x": 0.0, "y": 0.0, "z": 0.0, "ang": 0.0}]
    for x in (cfg.get("spacer") or {}).get("pos", []):      # Д-53: шайбы пакета венцов
        root.append({"id": f"{cid}.05{x['variant']}", "nn": "05", "x": 0.0, "y": 0.0,
                     "z": x["z"], "ang": 0.0})
    root += _layout_inst(cfg, rows)
    if g["limits"].get("shaft_d_min"):
        root.append({"id": f"{cid}.REF-shaft", "nn": "ref", "x": 0.0, "y": 0.0,
                     "z": _shaft(cfg)[0], "ang": 0.0})
    return {"rows": rows, "root": root, "B": sep["length"], "pitch": pitch}


def items(p):
    """Определения деталей в порядке появления -> [(id, nn)]."""
    seen = {}
    for x in p["root"] + [i for r in p["rows"] for i in r["inst"]]:
        seen.setdefault(x["id"], x["nn"])
    return list(seen.items())


def root_meta(cfg):
    keys = ("u", "z", "n", "roller", "Drol", "a_w", "R_sum", "gen", "bearing", "Dgen",
            "d_root", "d_tip", "d_out", "width", "alpha_max", "M", "M_by", "holes", "mount")
    m = {k: cfg[k] for k in keys if cfg.get(k) is not None}
    m["source"] = "egm.cad.assy (Д-49) ← specs/ptk_configs.json"
    return m


def item_meta(cfg, prods, pid, nn):
    it = {}
    if nn != "ref":
        try:
            it = products.item(prods, _base(pid))
        except (KeyError, ValueError):
            it = {}
    m = {"id": pid, "name": it.get("name", "вал (примитив)"), "kind": it.get("kind", "ref")}
    g = cfg["geom"]
    if nn == "01":
        m.update(d_root=cfg["d_root"], d_tip=cfg["d_tip"], d_out=cfg["d_out"],
                 B=g["roller"]["l"], holes=cfg["holes"])
    elif nn == "02":
        s = cfg["sep"]
        m.update(Dc=round(2 * s["r_out"], 3), dc=round(2 * s["r_in"], 3), B=s["length"],
                 windows=f"{s['n']} × {len(s['rows'])} рядов")
    elif nn == "03":
        e, b = cfg["ecc"], cfg["ecc"]["bal"]
        m.update(De=e["De"], t=e["t"], a_w=e["a"], U=e["U"]["sum"],
                 bal=f"{b['n']}×Ø{b['d']:g} r {b['r']:g}" if b["n"] else "нет")
    elif nn == "05":
        s = cfg["spacer"]
        m.update(d_in=round(2 * s["r_in"], 3), d_out=s["d_out"], d_bc=cfg["d_bc"],
                 h=next(q["h"] for q in cfg["parts"] if q["id"] == pid), holes=cfg["holes"])
    elif nn == "04":
        m.update(code=cfg["roller"], d=g["roller"]["d"], l=g["roller"]["l"])
    elif nn == "08":
        m.update(code=cfg["bearing"], **g["bearing"])
    elif nn == "07":
        c, sd = cfg["layout"]["covers"], pid.split(".", 1)[1][2]
        m.update(side=sd, t=c["t" + sd], D=c["D"], seat=c["seat_" + sd], d_bc=cfg["d_bc"])
        if sd == "B":
            m.update(pocket=f"Ø{c['pocket'][0]:g}×{c['pocket'][1]:g}")
    elif nn == "11":
        m.update(**cfg["layout"]["r11"])
    elif nn in ("09", "10"):
        b = cfg["layout"]["b" + nn]
        m.update(code=b["id"], d=b["d"], D=b["D"], B=b["B"])
    elif nn == "12":                   # CP-63
        j = next((q.get("join") or {} for q in cfg["layout"].get("cad_parts", [])
                  if q["id"] == pid), {})
        m.update(scheme=j.get("scheme"), belt=j.get("L"),
                 pins=f"{j.get('pin_n')}×Ø{j.get('pin_d') or 0:g}",
                 hub=f"Ø{j.get('hub_d') or 0:g}×{j.get('hub_l') or 0:g}")
    elif nn == "13":                   # CP-80, Д-93
        j = next((q.get("join") or {} for q in cfg["layout"].get("cad_parts", [])
                  if q["id"] == pid), {})
        h = j.get("hub") or {}
        m.update(t=j.get("t_s"), crit=j.get("crit"), D=j.get("D"),
                 pins=f"{j.get('pin_n')}×Ø{j.get('pin_d') or 0:g}",
                 hub_pins=f"{h.get('n')}×Ø{h.get('d') or 0:g}")
    else:
        m.update(d=g["limits"]["shaft_d_min"])
    return m


def _r(x):
    return {"id": x["id"], **{k: round(x[k], 4) for k in ("x", "y", "z", "ang")}}


def label(cfg, pid, nn):
    """Алиас определения детали (Д-50, Д-52): «ECC (.03D)»; полный ID — только у корня.
    Скобка в конце: FreeCAD у дублей увеличивает хвостовые цифры (.04 → .05 … .152)."""
    lay = cfg.get("layout") or {}
    code = {"04": cfg.get("roller"), "08": cfg.get("bearing"),
            "09": (lay.get("b09") or {}).get("id"), "10": (lay.get("b10") or {}).get("id")}.get(nn)
    suf = pid.split(".", 1)[1] + (f" {code}" if code else "")
    return f"{ALIAS[nn]} (.{suf})"


def row_label(r):
    return f"ROW{r['row']} (phi = {r['phi']:g} deg)"


def bodies_label(r, n):
    return f"BODIES_ROW{r['row']} ({n} pcs)"


def nodes(cfg, prods, p):
    """Метка узла дерева STEP -> метаданные (Д-50): корень, ряды, группы тел, определения."""
    out = {cfg["id"]: root_meta(cfg)}
    for r in p["rows"]:
        out[row_label(r)] = {"row": r["row"], "phi": r["phi"], "s": r["s"],
                                   "zc": round(r["zc"], 3)}
        nb = sum(x["nn"] == "04" for x in r["inst"])
        if nb:
            out[bodies_label(r, nb)] = {"row": r["row"], "n": nb, "code": cfg.get("roller")}
    for pid, nn in items(p):
        out[label(cfg, pid, nn)] = item_meta(cfg, prods, pid, nn)
    return out


def step_str(s):
    """str -> строка STEP (ISO 10303-21): ' -> '', \\ -> \\\\, не ASCII -> \\X2\\…\\X0\\.
    Имена узлов — латиница (Д-52); \\X2\\ — только в значениях атрибутов (имя из products.yaml)."""
    out, wide = [], []

    def flush():
        if wide:
            out.append("\\X2\\" + "".join(f"{c:04X}" for c in wide) + "\\X0\\")
            wide.clear()
    for ch in str(s):
        if 32 <= ord(ch) < 127:
            flush()
            out.append({"'": "''", "\\": "\\\\"}.get(ch, ch))
        else:
            b = ch.encode("utf-16-be")
            wide += [int.from_bytes(b[i:i + 2], "big") for i in range(0, len(b), 2)]
    flush()
    return "'" + "".join(out) + "'"


def step_unstr(s):
    """Содержимое строки STEP (без кавычек) -> str: '', \\X2\\…\\X0\\, \\X\\hh, \\\\."""
    s = s.replace("''", "'")
    s = re.sub(r"\\X2\\((?:[0-9A-Fa-f]{4})+)\\X0\\",
               lambda m: bytes.fromhex(m.group(1)).decode("utf-16-be"), s)
    s = re.sub(r"\\X\\([0-9A-Fa-f]{2})", lambda m: bytes.fromhex(m.group(1)).decode("latin-1"), s)
    return s.replace("\\\\", "\\")


def _refs(a):
    return [int(x) for x in re.findall(r"#(\d+)", a)]


def finish(path, texts, meta):
    """Д-50: подставляет в STEP имена узлов и дописывает атрибуты -> число узлов с атрибутами.

    В XCAF узлы названы ASCII-метками 'EGM<i>' (texts[i] — настоящее имя): результат не
    зависит от того, как писатель OCCT кодирует кириллицу. Атрибуты — по рекомендации
    CAx-IF «User Defined Attributes»: PROPERTY_DEFINITION → PROPERTY_DEFINITION_REPRESENTATION
    → REPRESENTATION из DESCRIPTIVE_REPRESENTATION_ITEM(ключ, значение) на PRODUCT_DEFINITION."""
    s = path.read_text(encoding="latin-1")
    ents = [(int(m.group(1)), m.group(2), m.group(3)) for m in _ENT.finditer(s)
            if m.group(2).startswith("PRODUCT")]
    prod = {i: texts[int(m.group(1))] for i, t, a in ents
            if t == "PRODUCT" and (m := _TOK.search(a))}
    form = {i: prod[_refs(a)[-1]] for i, t, a in ents
            if t.startswith("PRODUCT_DEFINITION_FORMATION") and _refs(a) and _refs(a)[-1] in prod}
    pdef = {}
    for i, t, a in ents:
        f = next((x for x in _refs(a) if x in form), None) if t == "PRODUCT_DEFINITION" else None
        if f is not None:
            pdef.setdefault(form[f], i)
    s = _TOK.sub(lambda m: step_str(texts[int(m.group(1))]), s)
    nxt = max([int(x) for x in re.findall(r"#(\d+)\s*=", s)] + [0]) + 1
    ctx, out, n = nxt, [], 0
    nxt += 1
    for text, pd in pdef.items():
        kv = [(k, v) for k, v in meta.get(text, {}).items() if v is not None]
        if not kv:
            continue
        ids = list(range(nxt, nxt + len(kv)))
        a, b, c = nxt + len(kv), nxt + len(kv) + 1, nxt + len(kv) + 2
        nxt += len(kv) + 3
        out += [f"#{j}=DESCRIPTIVE_REPRESENTATION_ITEM({step_str(k)},{step_str(_txt(v))});"
                for j, (k, v) in zip(ids, kv)]
        out += [f"#{a}=PROPERTY_DEFINITION('user defined attributes','EGM',#{pd});",
                f"#{b}=PROPERTY_DEFINITION_REPRESENTATION(#{a},#{c});",
                f"#{c}=REPRESENTATION('EGM',({','.join(f'#{j}' for j in ids)}),#{ctx});"]
        n += 1
    if n:
        out.insert(0, f"#{ctx}=REPRESENTATION_CONTEXT('EGM','user defined attributes');")
        k = s.rfind("ENDSEC;")
        s = s[:k] + "\n".join(out) + "\n" + s[k:]
    path.write_text(s, encoding="latin-1", newline="")
    return n


def manifest(cfg, prods, p):
    """<ID>.assy.json: дерево, слои, метаданные, метки узлов STEP (labels) и виды (OQ-14)."""
    return {"id": cfg["id"], "schema": SCHEMA, "units": "mm",
            "frame": "z — ось вала, z = 0 — торец пакета; 0° — впадина 0 венца ряда 1 (Д-49)",
            "meta": root_meta(cfg), "layers": {k: {"step": s, "name": t} for k, (s, t) in LAYERS.items()}, "views": VIEWS,
            "items": {pid: {"nn": nn, "label": label(cfg, pid, nn), "layer": LAYERS[nn][0],
                            **item_meta(cfg, prods, pid, nn)} for pid, nn in items(p)},
            "labels": nodes(cfg, prods, p),
            "drawings": drawings(cfg, prods, p),
            "tree": [{"row": r["row"], "label": row_label(r), "phi": r["phi"], "s": r["s"],
                      "zc": round(r["zc"], 3), "inst": [_r(x) for x in r["inst"]]} for r in p["rows"]],
            "root": [_r(x) for x in p["root"]]}


_GEN = {"01": ptk_ring.build, "02": ptk_sep.build, "03": ptk_ecc.build,
        "05": ptk_spacer.build, "07": ptk_cover.build, "11": ptk_cover.build,
        "12": ptk_hub.build, "13": ptk_hub.build_leaf}


def part_model(cfg, pid, nn):
    """PartModel детали сборки (Д-32): из неё строится STEP и берутся эталоны чертежа (Д-65);
    покупные .04, .08, .09, .10 и вал — None. Венец и сепаратор — по первому ряду варианта.
    Детали конструктива — из layout.cad_parts (cup, join — CP-63), прочие — из cfg["parts"]."""
    lay = [q for q in (cfg.get("layout") or {}).get("cad_parts", []) if q["id"] == pid]
    part = lay[0] if lay else next((q for q in cfg["parts"] if q["id"] == pid), None)
    if nn not in _GEN or part is None:
        return None
    if nn in ("01", "02"):
        return _GEN[nn](cfg, part, part["rows"][0])
    return _GEN[nn](cfg, part)


_MATS = None


def _mats():
    """specs/materials.yaml (Д-67) — читается один раз; нет файла или ключа — {}."""
    global _MATS
    if _MATS is None:
        from egm import config
        try:
            p = config.cfg_file(config.load_app(), "configs.materials")
            _MATS = config.load(p) if p.exists() else {}
        except Exception:
            _MATS = {}
    return _MATS


def material(cfg, prods, pid, nn):
    """Графа 3 основной надписи (Д-67): .02 — марка заготовки, выбранной на шаге 2
    (layout.blank.material); иначе первая марка products.yaml → material; нет — ""."""
    from egm import materials as MAT
    grade = ((cfg.get("layout") or {}).get("blank") or {}).get("material") if nn == "02" else None
    if not grade:
        try:
            grade = (products.item(prods, _base(pid)).get("material") or [None])[0]
        except (KeyError, ValueError):
            grade = None
    return MAT.title(_mats(), grade)


def drawings(cfg, prods, p):
    """<ID>.assy.json → drawings (Д-65): на каждое определение с генератором — эталоны
    проверок, легенда, примечания, формат (egm/cad/techdraw.py). Геометрию листа макрос
    берёт из STEP. Ошибка модели — запись {"label", "error"}, сборка не прерывается."""
    out = {}
    for pid, nn in items(p):
        if nn not in _GEN:
            continue
        lab = label(cfg, pid, nn)
        try:
            name = item_meta(cfg, prods, pid, nn).get("name", "")
            out[pid] = techdraw.record(pid, nn, part_model(cfg, pid, nn), lab, name)
            out[pid]["material"] = material(cfg, prods, pid, nn)
        except (AttributeError, KeyError, TypeError, ValueError) as e:
            out[pid] = {"label": lab, "error": f"{type(e).__name__}: {e}"}
    return out


def _shape(cq, cfg, pid, nn, mode):
    g, V, nz = cfg["geom"], cq.Vector, cq.Vector(0, 0, 1)
    if nn in _GEN:
        m = part_model(cfg, pid, nn)
        if m is None:
            raise ValueError(f"{pid}: детали нет в cfg['parts']")
        return step.solid(m, mode)
    if nn == "04":
        r = g["roller"]
        if r.get("type") == "ball":
            return cq.Solid.makeSphere(r["d"] / 2, V(0, 0, 0), nz, -90, 90, 360)
        return cq.Solid.makeCylinder(r["d"] / 2, r["l"])
    if nn in ("08", "09", "10"):
        b = g["bearing"] if nn == "08" else cfg["layout"]["b" + nn]
        return cq.Solid.extrudeLinear(cq.Wire.makeCircle(b["D"] / 2, V(0, 0, 0), nz),
                                      [cq.Wire.makeCircle(b["d"] / 2, V(0, 0, 0), nz)],
                                      V(0, 0, b["B"]))
    return cq.Solid.makeCylinder(g["limits"]["shaft_d_min"] / 2, _shaft(cfg)[1])


def export(cfg, prods, path, mode="spline", tag=None):
    """Пишет STEP сборки -> (время, с; число узлов с атрибутами в STEP).

    Дерево (Д-50, Д-91): изделие (тег имени файла — ID с суффиксом проработки/конструктива) → «Ряд k (φ)» → венец, эксцентрик, подшипник и группа
    «Тела ряда k»; сепаратор и вал — у корня. Имена — алиасы label(), атрибуты — finish()."""
    import cadquery as cq
    from OCP.IFSelect import IFSelect_ReturnStatus
    from OCP.Interface import Interface_Static
    from OCP.STEPCAFControl import STEPCAFControl_Writer
    from OCP.STEPControl import STEPControl_StepModelType
    from OCP.TCollection import TCollection_ExtendedString as XS
    from OCP.TDataStd import TDataStd_Name
    from OCP.TDocStd import TDocStd_Document
    from OCP.XCAFApp import XCAFApp_Application
    from OCP.XCAFDoc import XCAFDoc_ColorGen, XCAFDoc_DocumentTool
    from OCP.XSControl import XSControl_WorkSession
    t0 = time.perf_counter()
    p = plan(cfg)
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(XS("XmlOcaf"))
    app.InitDocument(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    lt = XCAFDoc_DocumentTool.LayerTool_s(doc.Main())
    layer = {k: lt.AddLayer(XS(v[0])) for k, v in LAYERS.items()}
    texts = []

    def name(lab, text):                 # Д-50: ASCII-метка, настоящее имя — в finish()
        TDataStd_Name.Set_s(lab, XS(f"EGM{len(texts)}"))
        texts.append(text)

    defs = {}
    for pid, nn in items(p):
        lab = st.AddShape(_shape(cq, cfg, pid, nn, mode).wrapped, False)
        name(lab, label(cfg, pid, nn))
        ct.SetColor(lab, cq.Color(*COLORS[nn]).wrapped, XCAFDoc_ColorGen)
        lt.SetLayer(lab, layer[nn])
        defs[pid] = lab

    def put(parent, x, text):
        loc = cq.Location(cq.Vector(x["x"], x["y"], x["z"]), cq.Vector(0, 0, 1), x["ang"])
        name(st.AddComponent(parent, defs[x["id"]], loc.wrapped), text)

    def group(parent, text):
        sub = st.NewShape()
        name(sub, text)
        name(st.AddComponent(parent, sub, cq.Location().wrapped), text)
        return sub

    root = st.NewShape()
    name(root, tag or cfg["id"])          # Д-91 (CP-76): изделие — тег имени файла
    for r in p["rows"]:
        sub = group(root, row_label(r))
        cnt = {}
        for x in r["inst"]:
            if x["nn"] != "04":
                cnt[x["id"]] = cnt.get(x["id"], 0) + 1
                put(sub, x, f"{label(cfg, x['id'], x['nn'])} #{cnt[x['id']]}")
        bod = [x for x in r["inst"] if x["nn"] == "04"]
        if bod:
            grp = group(sub, bodies_label(r, len(bod)))
            for j, x in enumerate(bod, 1):
                put(grp, x, f"#{j}")
    nr, many = {}, {}
    for x in p["root"]:
        many[x["id"]] = many.get(x["id"], 0) + 1
    for x in p["root"]:
        nm = label(cfg, x["id"], x["nn"])
        if many[x["id"]] > 1:          # Д-53, CP-45: шайбы, кольца .11, две .10 — номер экземпляра
            nr[x["id"]] = nr.get(x["id"], 0) + 1
            nm += f" #{nr[x['id']]}"
        put(root, x, nm)
    st.UpdateAssemblies()
    Interface_Static.SetCVal_s("write.step.schema", SCHEMA)
    Interface_Static.SetCVal_s("xstep.cascade.unit", "MM")
    Interface_Static.SetCVal_s("write.step.unit", "MM")
    ws = XSControl_WorkSession()
    w = STEPCAFControl_Writer(ws, False)
    w.SetColorMode(True)
    w.SetLayerMode(True)
    w.SetNameMode(True)
    w.Transfer(doc, STEPControl_StepModelType.STEPControl_AsIs)
    if w.Write(str(path)) != IFSelect_ReturnStatus.IFSelect_RetDone:
        raise ValueError(f"{cfg['id']}: STEP сборки не записан: {path}")
    return time.perf_counter() - t0, finish(Path(path), texts, nodes(cfg, prods, p))


def self_test():
    """Без CadQuery: тела — в окнах сепаратора и на окружности R_Σ генератора (Д-46),
    пазы эксцентриков — на одном угле вала, детали — в длине пакета, состав сборки."""
    from types import SimpleNamespace
    from egm import ptk_parts
    n, a, R, D, l = 50, 0.4, 33.5, 2.0, 4.2
    ph = [{"row": k + 1, "phi": f, "s": s}
          for k, (f, s) in enumerate(((0.0, 0.0), (90.0, 0.3), (180.0, 0.1), (270.0, 0.5)))]
    lim = SimpleNamespace(sep_gap=0.05, row_gap=1.0)
    sep = ptk_parts.separator(n, R, a, D, l, 7.0, ph, lim, 1.1)
    parts = ([{"id": f"PTK-T.01{v}", "s": x["s"], "rows": [x["row"]]} for v, x in zip("ABCD", ph)]
             + [{"id": "PTK-T.02", "rows": [1, 2, 3, 4]}]
             + [{"id": f"PTK-T.03{v}", "key_angle": (45.0 - x["phi"]) % 360, "rows": [x["row"]]}
                for v, x in zip("ABCD", ph)])
    cfg = {"id": "PTK-T", "n": n, "a_w": a, "R_sum": R, "phasing": ph, "parts": parts,
           "sep": sep, "ecc": {"t": 7.0},
           "geom": {"roller": {"type": "roller", "d": D, "l": l},
                    "bearing": {"d": 50.0, "D": 65.0, "B": 7.0},
                    "limits": {"row_gap": 1.0, "shaft_d_min": 6.0}}}
    p = plan(cfg)
    q, cage = 360 / n, {w["row"]: w["cage"] for w in sep["rows"]}
    keys = {x["id"]: x["key_angle"] for x in parts if "key_angle" in x}
    hgt = {"01": l, "03": 7.0, "08": 7.0, "04": l}
    for r in p["rows"]:
        ex, ey = r["ecc"]
        bod = [x for x in r["inst"] if x["nn"] == "04"]
        assert len(bod) == n, ("тел в ряду", len(bod))
        for x in bod:
            d = (math.degrees(math.atan2(x["y"], x["x"])) - cage[r["row"]]) % q
            assert min(d, q - d) < 1e-3, ("тело вне окна сепаратора (Д-46)", r["row"], d)
            assert abs(math.hypot(x["x"] - ex, x["y"] - ey) - R) < 1e-6, ("тело не на R_Σ", r["row"])
        e = next(x for x in r["inst"] if x["nn"] == "03")
        assert abs((e["ang"] + keys[e["id"]]) % 360 - 45.0) < 1e-6, ("паз шпонки", r["row"])
        for x in r["inst"]:
            assert -1e-9 <= x["z"] and x["z"] + hgt[x["nn"]] <= p["B"] + 1e-9, (x["nn"], x["z"])
    assert len(items(p)) == 12, items(p)
    assert sum(len(r["inst"]) for r in p["rows"]) + len(p["root"]) == 4 * 53 + 2
    labs = [label(cfg, pid, nn) for pid, nn in items(p)]
    labs += [row_label(r) for r in p["rows"]] + [bodies_label(r, n) for r in p["rows"]]
    assert len(set(labs)) == len(labs) == 20, ("метки узлов не уникальны (Д-50)", labs)
    assert all(not x[-1].isdigit() for x in labs), "хвостовые цифры: FreeCAD перенумерует дубли"
    assert not any("PTK-T" in x for x in labs), "полный ID — только у корня (Д-50)"
    assert all(x.isascii() for x in labs), ("имена узлов — только латиница (Д-52)", labs)
    assert label(cfg, "PTK-T.03D", "03") == "ECC (.03D)", label(cfg, "PTK-T.03D", "03")
    sp = ptk_parts.spacers(69.8, 88.0, 80.0, 4.5, l, 7.0, 4,
                           SimpleNamespace(row_gap=1.0, spacer_gap=0.5))     # Д-53
    spp = ptk_parts.spacer_parts("PTK-T", sp, 4)
    p2 = plan({**cfg, "spacer": sp, "parts": parts + spp})
    hh = {q["id"]: q["h"] for q in spp}
    seg = sorted([(x["z"], x["z"] + hh[x["id"]]) for x in p2["root"] if x["nn"] == "05"]
                 + [(x["z"], x["z"] + l) for r in p2["rows"] for x in r["inst"] if x["nn"] == "01"])
    assert len(seg) == 9 and abs(seg[0][0]) < 1e-6 and abs(seg[-1][1] - p2["B"]) < 1e-6, seg
    assert all(abs(e0[1] - e1[0]) < 1e-6 for e0, e1 in zip(seg, seg[1:])), ("пакет: зазор", seg)
    assert label(cfg, "PTK-T.05B", "05") == "SPACER (.05B)"
    assert part_model(cfg, "PTK-T.04", "04") is None, "покупные — без чертежа (Д-65)"
    from egm import ptk_layout                                               # CP-45
    lay = {"parts": {"02": "cup", "07": "side", "11": "ring"},
           "covers": {"tA": 6.0, "tB": 14.0, "D": 88.0, "seat_A": 19.0, "seat_B": 42.0,
                      "pocket": [68.9, 6.0]},
           "cup": {"z_in": 36.5, "t": 2.0, "hub_d": 30.0, "hub_bore": 19.0, "hub_l": 10.5},
           "b09": {"id": "61806", "d": 30.0, "D": 42.0, "B": 7.0},
           "b10": {"id": "61800", "d": 10.0, "D": 19.0, "B": 5.0},
           "r11": {"n": 3, "h": 1.0, "d_in": 10.0, "d_out": 14.0}, "shaft_d": 10.0, "ax_gap": 0.5}
    lay["cad_parts"] = ptk_layout.cad_parts(cfg, "K", lay)
    cfg3 = {**cfg, "layout": lay,
            "parts": [x for x in parts if ".02" not in x["id"]] + lay["cad_parts"]}
    p3 = plan(cfg3)
    W, z = p3["B"], {}
    for x in p3["root"]:
        z.setdefault(x["id"], []).append(x["z"])
    assert z["PTK-T.02A-K"] == [0.0] and z["PTK-T.07A-K"] == [-6.0] and z["PTK-T.07B-K"] == [W], z
    assert z["PTK-T.10"] == [-5.0, 36.5] and z["PTK-T.09"] == [W + 6.0], z
    ecc = sorted(x["z"] for r in p3["rows"] for x in r["inst"] if x["nn"] == "03")
    assert all(abs(e + 7.0 + 1.0 - f) < 1e-6 for e, f in zip(ecc, ecc[1:])), ecc
    assert sorted(z["PTK-T.11-K"]) == [e + 7.0 for e in ecc[:-1]], (z["PTK-T.11-K"], ecc)
    assert _shaft(cfg3) == (-11.0, 52.5), _shaft(cfg3)
    l3 = [label(cfg3, pid, nn) for pid, nn in items(p3)]
    assert len(set(l3)) == len(l3) and all(x.isascii() and not x[-1].isdigit() for x in l3), l3
    assert label(cfg3, "PTK-T.10", "10") == "BRG_IN (.10 61800)", l3
    jn = {"scheme": "collar", "z": 36.5, "L": 9.0, "f": 0.0, "r_in": sep["r_in"], "r_out": sep["r_out"],
          "r_j": 32.06, "D": 69.88, "d": 64.12, "pin_d": 3.0, "pin_n": 10, "pin_l": 8.0,
          "hole12": 5.62, "pin_z": 41.0, "pin_a": [36.0 * k for k in range(10)],
          "hub_d": 30.0, "hub_bore": 19.0, "hub_l": 10.5, "weld": None}      # CP-63: L2
    lay2 = {**lay, "parts": {"02": "collar", "07": "side", "11": "ring", "12": "spigot"},
            "cup": {**lay["cup"], "t": 9.0},
            "covers": {**lay["covers"], "tB": 21.0, "pocket": [70.88, 13.0]},
            "cad_parts": [{"id": "PTK-T.02B-K", "base": "PTK-T.02B", "rows": [1, 2, 3, 4], "join": jn},
                          {"id": "PTK-T.12A-K", "base": "PTK-T.12A", "rows": [1, 2, 3, 4], "join": jn}]}
    cfg4 = {**cfg, "layout": lay2,
            "parts": [x for x in parts if ".02" not in x["id"]] + lay2["cad_parts"]}
    z4 = {}
    for x in plan(cfg4)["root"]:
        z4.setdefault(x["id"], []).append(x["z"])
    assert z4["PTK-T.12A-K"] == [36.5] and z4["PTK-T.10"] == [-5.0, 36.5] \
        and z4["PTK-T.09"] == [W + 13.0], z4
    s4, h4 = part_model(cfg4, "PTK-T.02B-K", "02"), part_model(cfg4, "PTK-T.12A-K", "12")
    assert len(s4.bands) == 2 and len(s4.pins) == 10 and len(h4.pins) == 10, (s4.bands, h4.pins)
    assert label(cfg4, "PTK-T.12A-K", "12") == "HUB (.12A-K)"
    jn5 = {**jn, "L": 7.5, "dir": "in", "axial": True, "h_b": 4.5, "t_s": 3.0, "crit": "k_fit",
           "t_s_min": 3.0, "r_j": 28.56, "d": 46.12, "pin_n": 8, "pin_a": [45.0 * k for k in range(8)],
           "hub": {"d": 3.0, "n": 10, "r_h": 19.5, "r_f": 24.0, "h_f": 4.5, "l": None}}   # CP-80
    lay5 = {**lay2, "parts": {**lay2["parts"], "12": "flange", "13": "leaf"},
            "cup": {**lay["cup"], "t": 12.0},
            "cad_parts": [{"id": "PTK-T.02B-K", "base": "PTK-T.02B", "rows": [1, 2, 3, 4], "join": jn5},
                          {"id": "PTK-T.12A-K", "base": "PTK-T.12A", "rows": [1, 2, 3, 4], "join": jn5},
                          {"id": "PTK-T.13-K", "base": "PTK-T.13", "rows": [1, 2, 3, 4], "join": jn5}]}
    cfg5 = {**cfg, "layout": lay5,
            "parts": [x for x in parts if ".02" not in x["id"]] + lay5["cad_parts"]}
    z5 = {}
    for x in plan(cfg5)["root"]:
        z5.setdefault(x["id"], []).append(x["z"])
    assert z5["PTK-T.13-K"] == [41.0] and z5["PTK-T.12A-K"] == [44.0], z5
    h5, l5 = part_model(cfg5, "PTK-T.12A-K", "12"), part_model(cfg5, "PTK-T.13-K", "13")
    assert len(h5.axial) == 10 and len(l5.axial) == 18 and l5.thick == 3.0, (h5.axial, l5.axial)
    assert label(cfg5, "PTK-T.13-K", "13") == "LEAF (.13-K)"
    assert ptk_cover.self_test()
    for s in ("Эксцентрик (.03D)", "it's \\ ok", "φ = 90°"):
        assert step_unstr(step_str(s)[1:-1]) == s, ("кодирование строки STEP", s)
    import tempfile
    txt = ("ISO-10303-21;\nHEADER;\nENDSEC;\nDATA;\n#1=PRODUCT('EGM0','EGM0','',(#9));\n"
           "#2=PRODUCT_DEFINITION_FORMATION('','',#1);\n#3=PRODUCT_DEFINITION('design','',#2,#8);\n"
           "#4=NEXT_ASSEMBLY_USAGE_OCCURRENCE('1','EGM1','',#3,#3,$);\n"
           "#9=( GEOMETRIC_REPRESENTATION_CONTEXT(3) );\nENDSEC;\nEND-ISO-10303-21;\n")
    with tempfile.TemporaryDirectory() as d:
        f = Path(d) / "t.step"
        f.write_text(txt, encoding="latin-1")
        k = finish(f, ["Тело (.04)", "#1"], {"Тело (.04)": {"d": 2.0, "name": "тело 'R'"}})
        out = f.read_text(encoding="latin-1")
    assert k == 1 and "EGM0" not in out and "'#1'" in out, out
    assert step_str("Тело (.04)") in out, "имя узла не подставлено"
    assert "#13=PROPERTY_DEFINITION('user defined attributes','EGM',#3);" in out, out
    assert "#11=DESCRIPTIVE_REPRESENTATION_ITEM('d','2');" in out, out
    assert out.count("ENDSEC;") == 2 and out.rstrip().endswith("END-ISO-10303-21;")
    return True
