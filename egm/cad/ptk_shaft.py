"""Входной вал ПТК .15 (CP-91 этап 4; Д-107, Д-110): PartModel из проработки шага 2.

Данные — cfg после ptk_design.apply: shaft (выбранная конфигурация SH, марка, шпонка .03
из link), keys (keys.table, Д-109), layout (крышки, дно/ступица, .10). Чисел в коде нет:
диаметры и длины — из расчёта, константы (хвостовик, перемычка паза, вылет инструмента) —
DEFAULTS egm/shafts.py («сверить»).
Ось — z сборки (egm/cad/assy.py); локальная z = 0 — торец хвостовика, в сборке z0 = −tA − tail_l.
Участки по оси сборки:
  хвостовик   [z0, −B.10]     Ø min(d, d.10) — проходит через .10; паз keys.table на выходе за .07A;
  шейка .10   [−B.10, 0]      Ø d.10 — подшипник в .07A;
  тело        [0, z.10B]      Ø d — эксцентрики .03 и кольца .11; паз шпонки .03 по пакету;
  шейка .10   [z.10B, +B.10]  Ø d.10 — второй .10 в ступице (сдвигается со ступицей, Д-102 п. 2).
Длина — по пакету и конструктиву, не из номенклатуры (length в shafts.yaml не читается).
Без конструктива шага 2 — предварительный цилиндр Ø shaft_d_min: пакет + 2·tail_l (как прежний REF).
Фаски и галтели не моделируются (PartModel: тела вращения Band) — на чертеже по ГОСТ.
"""
import math

from egm import shafts
from egm.cad.model import Band, Circle, Contour, Dim, KeySlot, PartModel

D = shafts.DEFAULTS


def _circle(r, n=180):
    return [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def _key(keys, d):
    """Строка keys.table для Ø d (первая с d ≤ d_max, Д-109) или None."""
    return next((k for k in sorted(keys or [], key=lambda k: k["d_max"]) if d <= k["d_max"] + 1e-9),
                None)


def pack(cfg):
    """z пакета эксцентриков по оси сборки (как assy.plan) -> (z начала, z конца)."""
    g = cfg["geom"]
    rol, brg, gap = g["roller"], g.get("bearing"), g["limits"]["row_gap"]
    pitch = max(rol["l"], brg["B"]) if brg else rol["l"]
    n, t = len(cfg["phasing"]), cfg["ecc"]["t"]
    return gap + pitch / 2 - t / 2, gap + (n - 1) * (pitch + gap) + pitch / 2 + t / 2


def key_angle(cfg):
    """Угол паза в системе сборки: у всех рядов один (key_angle варианта .03 + φ его ряда, Д-46)."""
    ph = {p["row"]: p["phi"] for p in cfg["phasing"]}
    p = next((q for q in cfg["parts"] if q["id"].split(".", 1)[1][:2] == "03"
              and "key_angle" in q and q.get("rows")), None)
    return round((p["key_angle"] + ph[p["rows"][0]]) % 360, 3) if p else 0.0


def check(cfg, pid):
    """Отказ подбора — раньше геометрии (CP-91 этап 4 п. 4): ID не разрешён или марка не
    подобрана -> ValueError. Отказ проверок τ/σсм проработки CAD не останавливает:
    вал строится по выбранной конфигурации, статус «нет» — в SPEC-11/SPEC-12."""
    sh = cfg.get("shaft") or {}
    if sh.get("id_req") and not sh.get("id"):
        raise ValueError(f"{pid}: вал не подобран — shaft.id проработки не разрешён "
                         f"(input.shaft_id пуст); CAD .15 не строится (Д-107, Д-110)")
    if sh.get("grade") is None and sh.get("rejected"):
        why = "; ".join(f"{x['grade']}: {x['why']}" for x in sh["rejected"])
        raise ValueError(f"{pid}: материал .15 не подобран ({why}); CAD .15 не строится (Д-110)")


def stations(cfg):
    """Участки вала -> {"z0", "z1", "d", "d10", "B10", "segs": [(z, h, Ø, роль)], "pack", "prelim"}."""
    lay = cfg.get("layout") or {}
    cov, cup, b10 = lay.get("covers"), lay.get("cup") or {}, lay.get("b10") or {}
    sh = cfg.get("shaft") or {}
    d = float(sh.get("d") or cfg["geom"]["limits"].get("shaft_d_min") or 0.0)
    if d <= 0:
        raise ValueError(f"{cfg['id']}: Ø вала не задан (shaft.d проработки / limits.shaft_d_min)")
    tl, pk = D["tail_l"], pack(cfg)
    if not (cov and cup.get("z_in") and b10):
        W = cfg["sep"]["length"]
        return {"z0": -tl, "z1": W + tl, "d": d, "d10": None, "B10": 0.0,
                "segs": [(-tl, W + 2 * tl, d, "тело (предварительно)")], "pack": pk, "prelim": True}
    B10, d10, z0 = float(b10["B"]), float(b10["d"]), -float(cov["tA"]) - tl
    pr = lay.get("parts", {})
    hub = bool(cup.get("hub_d") and (pr.get("02") == "cup" or pr.get("12")))
    s12 = next(((q.get("join") or {}).get("h_b", 0.0) for q in lay.get("cad_parts", [])
                if q["id"].split(".", 1)[1][:2] == "12" and (q.get("join") or {}).get("seat")), 0.0)
    zb = round(cup["z_in"] + (s12 if hub else 0.0), 3)     # .10 в ступице — как assy._layout_inst
    segs = [(z0, -B10 - z0, min(d, d10), "хвостовик"), (-B10, B10, d10, "шейка .10 (.07A)")]
    if hub:
        segs += [(0.0, zb, d, "тело (.03, .11)"), (zb, B10, d10, "шейка .10 (ступица)")]
    else:
        segs += [(0.0, zb + B10, d, "тело (.03, .11)")]
    return {"z0": z0, "z1": zb + B10, "d": d, "d10": d10, "B10": B10, "segs": segs, "pack": pk,
            "prelim": False}


def build(cfg, part=None, row=None):
    """PartModel вала .15; отказ подбора, пустой участок, стенка полого вала — ValueError до геометрии."""
    pid = (part or {}).get("id") or f"{cfg['id']}.15"
    check(cfg, pid)
    st, sh = stations(cfg), cfg.get("shaft") or {}
    d, bore, z0 = st["d"], float(sh.get("bore") or 0.0), st["z0"]
    kb = sh.get("key") or {}
    t1 = float(kb.get("t1") or 0.0)
    for _, h, dd, role in st["segs"]:
        if h <= 0:
            raise ValueError(f"{pid}: участок «{role}» длиной {h:g} мм — крышка .07A тоньше .10 + tail_l?")
        w = (dd - bore) / 2 - (t1 if role.startswith("тело") else 0.0)
        if bore and w < D["wall_min"] - 1e-9:
            raise ValueError(f"{pid}: стенка полого вала {w:.2f} < wall_min {D['wall_min']:g} мм "
                             f"на участке «{role}» (Ø{dd:g}, отв. {bore:g})")
    _, h0, d0, _ = st["segs"][0]
    so = D["slot_over"]
    m = PartModel(pid, h0, d0, Contour(_circle(bore / 2) if bore else []))
    m.bands = [Band(0.0, dd / 2, z - z0, h) for z, h, dd, _ in st["segs"][1:]]
    if bore:
        m.bands.append(Band(0.0, bore / 2, -so, st["z1"] - z0 + 2 * so, "cut"))
    ka, (za, zb) = key_angle(cfg), st["pack"]
    if kb.get("b") and t1:
        m.slots.append(KeySlot(ka, d / 2 - t1, d / 2 + so, kb["b"], za - z0, zb - za))
    kt = None if st["prelim"] else _key(cfg.get("keys"), d0)
    lt = D["tail_l"] - D["key_run"]
    if kt and lt > 0:
        m.slots.append(KeySlot(ka, d0 / 2 - kt["t1"], d0 / 2 + so, kt["b"], -so, lt + so))
    m.axes = [Circle(x / 2, "thin") for x in sorted({s[2] for s in st["segs"]}) if x != d0]
    d10 = st["d10"]
    m.dims = [Dim(d, "d")] + ([Dim(d10, "d.10")] if d10 and abs(d10 - d) > 1e-9 else [])
    L = round(st["z1"] - z0, 3)
    m.legend = [("ID", sh.get("id") or "—", "конфигурация SH-<d>-<link> (Д-107)"),
                ("d", d, "Ø тела под .03, мм"),
                ("d.10", d10 if d10 else "—", "Ø шеек под .10, мм"),
                ("L", L, "длина по пакету и конструктиву, мм"),
                ("паз .03", f"{kb['b']:g} × {t1:g} × {zb - za:g}" if kb.get("b") and t1 else "нет",
                 "b × t1 × l по пакету (keys.table, Д-109)"),
                ("паз хв.", f"{kt['b']:g} × {kt['t1']:g} × {lt:g}" if kt and lt > 0 else "нет",
                 "хвостовик: b × t1 × l"),
                ("bore", bore, "Ø отверстия, мм; 0 — сплошной"),
                ("марка", sh.get("grade") or "—", "материал .15 (Д-110)")]
    m.notes = ["входной вал .15, участки: "
               + "; ".join(f"{r} Ø{dd:g}×{h:g}" for _, h, dd, r in st["segs"]),
               "фаски и галтели не моделируются — по ГОСТ на чертеже; константы — DEFAULTS egm/shafts.py (сверить)"]
    if st["prelim"]:
        m.notes.append("предварительно (шаг 1, без проработки): длина — пакет + 2·tail_l")
    if d10 and d10 > d + 1e-9:
        m.notes.append(f"d.10 = {d10:g} > d = {d:g}: эксцентрики .03 не проходят через шейку .10 — "
                       f"проверить сборку / подбор .10")
    if sh.get("blank"):
        m.notes.append(f"заготовка: {sh['blank']}")
    return m


def self_test():
    """Без CadQuery: участки по пакету и конструктиву, пазы, отказы до геометрии, предварительный."""
    from egm.cad import techdraw
    keys = [{"d_max": 10, "b": 3, "h": 3, "t1": 1.8, "t2": 1.4},
            {"d_max": 12, "b": 4, "h": 4, "t1": 2.5, "t2": 1.8}]
    ph = [{"row": 1, "phi": 0.0, "s": 0.0}, {"row": 2, "phi": 180.0, "s": 0.0}]
    cfg = {"id": "PTK-T", "phasing": ph, "sep": {"length": 20.0}, "ecc": {"t": 7.0},
           "parts": [{"id": "PTK-T.03A-K", "key_angle": 45.0, "rows": [1]},
                     {"id": "PTK-T.03B-K", "key_angle": 225.0, "rows": [2]}],
           "geom": {"roller": {"l": 4.2}, "bearing": {"B": 7.0},
                    "limits": {"row_gap": 1.0, "shaft_d_min": 12.0}},
           "keys": keys,
           "shaft": {"d": 12.0, "bore": 0.0, "id": "SH-12-KEY", "id_req": True, "grade": "40Х",
                     "rejected": [], "key": {"b": 4, "t1": 2.5}},
           "layout": {"covers": {"tA": 6.0}, "cup": {"z_in": 40.0, "hub_d": 20.0},
                      "b10": {"d": 10.0, "D": 19.0, "B": 5.0}, "parts": {"02": "cup"},
                      "cad_parts": []}}
    tl = D["tail_l"]
    assert pack(cfg) == (1.0, 16.0) and key_angle(cfg) == 45.0, (pack(cfg), key_angle(cfg))
    st = stations(cfg)
    assert st["z0"] == -6.0 - tl and st["z1"] == 45.0, st
    assert [s[2] for s in st["segs"]] == [10.0, 10.0, 12.0, 10.0], st["segs"]
    m = build(cfg)
    assert m.id == "PTK-T.15" and len(m.slots) == 2, m.slots
    assert techdraw.extent(m) == (12.0, 0.0, 45.0 + 6.0 + tl), techdraw.extent(m)
    s0, s1 = m.slots
    assert s0.r0 == 3.5 and abs(s0.z0 - (1.0 + 6.0 + tl)) < 1e-9 and s0.h == 15.0, s0
    assert s1.b == 3 and s1.angle == 45.0, s1
    assert techdraw.record(m.id, "15", m, "SHAFT (.15)", "входной вал")["checks"]
    for bad, txt in (({"id": "", "id_req": True}, "не подобран"),
                     ({"grade": None, "rejected": [{"grade": "40Х", "why": "нет прутка"}]}, "материал"),
                     ({"bore": 6.0}, "стенка")):
        try:
            build({**cfg, "shaft": {**cfg["shaft"], **bad}})
            raise AssertionError(bad)
        except ValueError as e:
            assert txt in str(e), e
    pre = {k: v for k, v in cfg.items() if k not in ("layout", "shaft", "keys")}
    sp = stations(pre)
    assert sp["prelim"] and (sp["z0"], sp["z1"]) == (-tl, 20.0 + tl), sp
    mp = build(pre)
    assert not mp.slots and mp.notes[-1].startswith("предварительно"), mp.notes
    return True
