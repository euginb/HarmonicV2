"""Эксцентрик ПТК (.03<вар>): PartModel из ptk_configs.json → ecc (Д-36, Д-46).

Ось вала — (0, 0); эксцентриситет a_ω — по +x; наружный Ø D_э — центр (a_ω, 0).
Отверстие вала со шпоночным пазом на угле key_angle варианта; отверстия балансировки —
со стороны эксцентриситета.
"""
import math

from egm.cad.model import Contour, Dim, Hole, Mark, PartModel


def _bore(rs, b, t2, ang, N=180):
    a0 = math.asin(b / 2 / rs)
    pts = [(rs * math.cos(a0 + (2 * math.pi - 2 * a0) * i / N),
            rs * math.sin(a0 + (2 * math.pi - 2 * a0) * i / N)) for i in range(N + 1)]
    pts += [(rs + t2, -b / 2), (rs + t2, b / 2)]
    c, s = math.cos(math.radians(ang)), math.sin(math.radians(ang))
    return [(x * c - y * s, x * s + y * c) for x, y in pts]


def build(cfg, part, row=None):
    e = cfg["ecc"]
    ka = part["key_angle"]
    m = PartModel(part["id"], e["t"], e["De"],
                  Contour(_bore(e["d_shaft"] / 2, e["key_b"], e["key_t2"], ka)))
    m.cx, m.cut_mode = (e["a"], 0.0), "poly"
    b = e["bal"]
    m.holes = [Hole(x, y, b["d"], "bal") for x, y in b["holes"]]
    m.marks = [Mark(0, 0, e["De"] / 2 + e["a"], f"aω = {e['a']:g}"),
               Mark(ka, e["d_shaft"] / 2, e["De"] / 2 + 2, f"паз, {ka:g}°")]
    m.dims = [Dim(e["De"], "Dэ"), Dim(e["d_shaft"], "dвала")]
    brg = "по d подшипника" if cfg.get("bearing") else "поверхность качения тел"
    m.notes = [f"эксцентрик, ряды {part['rows']}; наружный Ø — {brg}",
               f"балансировка (Д-36): U = {e['U']['sum']:g} г·мм, остаток {b['res']:g} г·мм",
               f"подшипник {e['m_brg_g']:g} г" + (" — оценка, задать bearings.m" if e["m_brg_est"] else "")]
    if e.get("groove_r"):
        m.notes.append(f"жёлоб под шарик r = {e['groove_r']:g} (Т2) — в STEP нет, CP-05")
    m.legend = [("aω", e["a"], "эксцентриситет, мм"),
                ("Dэ", e["De"], "наружный Ø, мм"),
                ("t", e["t"], "толщина: B подшипника | l тела"),
                ("паз", f"{e['key_b']:g} × {e['key_t2']:g}", "шпоночный паз b × t2 (сверить DIN 6885)"),
                ("key_angle", ka, "паз от эксцентриситета, °"),
                ("U", e["U"]["sum"], "дисбаланс: диск + подшипник + n/2 тел, г·мм"),
                ("отв.", f"{b['n']}×Ø{b['d']:g} r {b['r']:g}" if b["n"] else "нет", "балансировка")]
    return m
