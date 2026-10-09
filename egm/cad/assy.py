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
import time

from egm import products, ptk_profile
from egm.cad import ptk_ecc, ptk_ring, ptk_sep, step

LAYERS = {"01": ("01_RING", "венец"), "02": ("02_CAGE", "сепаратор"),
          "03": ("03_ECC", "эксцентрик"), "04": ("04_BODIES", "тела качения"),
          "08": ("08_BEARING", "подшипник генератора"), "ref": ("REF", "примитивы: вал")}
COLORS = {"01": (0.55, 0.57, 0.60), "02": (0.80, 0.60, 0.20), "03": (0.30, 0.50, 0.80),
          "04": (0.85, 0.20, 0.20), "08": (0.20, 0.65, 0.30), "ref": (0.70, 0.70, 0.70)}
VIEWS = [{"name": "ISO", "dir": [1, -1, 1], "layers": "все"},
         {"name": "по оси", "dir": [0, 0, 1], "layers": "все"},
         {"name": "сбоку", "dir": [1, 0, 0], "layers": "все"},
         {"name": "без венцов и сепаратора", "dir": [1, -1, 1], "layers": "03, 04, 08, REF"}]
SCHEMA = "AP242DIS"


def _nn(pid):
    return pid.split(".", 1)[1][:2]


def _txt(v):
    return f"{v:g}" if isinstance(v, float) else str(v)


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
    if g["limits"].get("shaft_d_min"):
        root.append({"id": f"{cid}.REF-shaft", "nn": "ref", "x": 0.0, "y": 0.0, "z": -5.0,
                     "ang": 0.0})
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
            it = products.item(prods, pid)
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
    elif nn == "04":
        m.update(code=cfg["roller"], d=g["roller"]["d"], l=g["roller"]["l"])
    elif nn == "08":
        m.update(code=cfg["bearing"], **g["bearing"])
    else:
        m.update(d=g["limits"]["shaft_d_min"])
    return m


def _r(x):
    return {"id": x["id"], **{k: round(x[k], 4) for k in ("x", "y", "z", "ang")}}


def manifest(cfg, prods, p):
    """<ID>.assy.json: то же дерево, слои, метаданные и предлагаемые виды (OQ-14)."""
    return {"id": cfg["id"], "schema": SCHEMA, "units": "mm",
            "frame": "z — ось вала, z = 0 — торец пакета; 0° — впадина 0 венца ряда 1 (Д-49)",
            "meta": root_meta(cfg), "layers": {k: {"step": s, "name": t} for k, (s, t) in LAYERS.items()}, "views": VIEWS,
            "items": {pid: {"nn": nn, "layer": LAYERS[nn][0], **item_meta(cfg, prods, pid, nn)}
                      for pid, nn in items(p)},
            "tree": [{"row": r["row"], "phi": r["phi"], "s": r["s"], "zc": round(r["zc"], 3),
                      "inst": [_r(x) for x in r["inst"]]} for r in p["rows"]],
            "root": [_r(x) for x in p["root"]]}


def _shape(cq, cfg, pid, nn, mode):
    g, V, nz = cfg["geom"], cq.Vector, cq.Vector(0, 0, 1)
    part = next((q for q in cfg["parts"] if q["id"] == pid), None)
    if nn == "01":
        return step.solid(ptk_ring.build(cfg, part, part["rows"][0]), mode)
    if nn == "02":
        return step.solid(ptk_sep.build(cfg, part, part["rows"][0]), mode)
    if nn == "03":
        return step.solid(ptk_ecc.build(cfg, part), mode)
    if nn == "04":
        r = g["roller"]
        if r.get("type") == "ball":
            return cq.Solid.makeSphere(r["d"] / 2, V(0, 0, 0), nz, -90, 90, 360)
        return cq.Solid.makeCylinder(r["d"] / 2, r["l"])
    if nn == "08":
        b = g["bearing"]
        return cq.Solid.extrudeLinear(cq.Wire.makeCircle(b["D"] / 2, V(0, 0, 0), nz),
                                      [cq.Wire.makeCircle(b["d"] / 2, V(0, 0, 0), nz)],
                                      V(0, 0, b["B"]))
    return cq.Solid.makeCylinder(g["limits"]["shaft_d_min"] / 2, cfg["sep"]["length"] + 10)


def export(cfg, prods, path, mode="spline"):
    """Пишет STEP сборки -> (время, с; метаданные записаны в STEP: bool)."""
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
    try:
        from OCP.TDataStd import TDataStd_NamedData
    except ImportError:
        TDataStd_NamedData = None
    t0 = time.perf_counter()
    p = plan(cfg)
    app = XCAFApp_Application.GetApplication_s()
    doc = TDocStd_Document(XS("XmlOcaf"))
    app.InitDocument(doc)
    st = XCAFDoc_DocumentTool.ShapeTool_s(doc.Main())
    ct = XCAFDoc_DocumentTool.ColorTool_s(doc.Main())
    lt = XCAFDoc_DocumentTool.LayerTool_s(doc.Main())
    layer = {k: lt.AddLayer(XS(v[0])) for k, v in LAYERS.items()}
    meta_ok = [TDataStd_NamedData is not None]

    def name(lab, text, meta):
        TDataStd_Name.Set_s(lab, XS(text))
        if meta_ok[0]:
            try:
                nd = TDataStd_NamedData.Set_s(lab)
                for k, v in meta.items():
                    nd.SetString(XS(str(k)), XS(_txt(v), True))
            except Exception:            # другая версия OCP — метаданные только в .assy.json
                meta_ok[0] = False

    defs = {}
    for pid, nn in items(p):
        lab = st.AddShape(_shape(cq, cfg, pid, nn, mode).wrapped, False)
        name(lab, pid, item_meta(cfg, prods, pid, nn))
        ct.SetColor(lab, cq.Color(*COLORS[nn]).wrapped, XCAFDoc_ColorGen)
        lt.SetLayer(lab, layer[nn])
        defs[pid] = lab

    def put(parent, x, text):
        loc = cq.Location(cq.Vector(x["x"], x["y"], x["z"]), cq.Vector(0, 0, 1), x["ang"])
        TDataStd_Name.Set_s(st.AddComponent(parent, defs[x["id"]], loc.wrapped), XS(text))

    root = st.NewShape()
    name(root, cfg["id"], root_meta(cfg))
    for r in p["rows"]:
        sub = st.NewShape()
        name(sub, f"{cfg['id']}_ROW{r['row']}",
             {"row": r["row"], "phi": r["phi"], "s": r["s"], "zc": round(r["zc"], 3)})
        TDataStd_Name.Set_s(st.AddComponent(root, sub, cq.Location().wrapped),
                            XS(f"ROW{r['row']}"))
        cnt = {}
        for x in r["inst"]:
            cnt[x["id"]] = cnt.get(x["id"], 0) + 1
            put(sub, x, f".{x['id'].split('.', 1)[1]} #{cnt[x['id']]} ROW{r['row']}")
    for x in p["root"]:
        put(root, x, "." + x["id"].split(".", 1)[1])
    st.UpdateAssemblies()
    Interface_Static.SetCVal_s("write.step.schema", SCHEMA)
    Interface_Static.SetCVal_s("xstep.cascade.unit", "MM")
    Interface_Static.SetCVal_s("write.step.unit", "MM")
    ws = XSControl_WorkSession()
    w = STEPCAFControl_Writer(ws, False)
    w.SetColorMode(True)
    w.SetLayerMode(True)
    w.SetNameMode(True)
    meta = meta_ok[0] and hasattr(w, "SetMetaMode")
    if meta:
        w.SetMetaMode(True)
    w.Transfer(doc, STEPControl_StepModelType.STEPControl_AsIs)
    if w.Write(str(path)) != IFSelect_ReturnStatus.IFSelect_RetDone:
        raise ValueError(f"{cfg['id']}: STEP сборки не записан: {path}")
    return time.perf_counter() - t0, meta


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
    return True
