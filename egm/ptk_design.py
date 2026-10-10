"""Шаг 2 — проработка выбранного исполнения ПТК (Д-48, CP-38).

Вход: specs/ptk_design_input.json → designs[]; исполнение шага 1 — ptk_configs.json.
Выход: ptk_designs.json и SPEC-11_PTK_DESIGN.md; детали проработки — <ID>.03<вар>-<name>.
Исполнение задаётся полным ID или префиксом без хэша (+ bearing, gen): хэш меняется
с геометрией шага 1 (Д-22), а проработка остаётся привязанной (Д-51).
Считается: момент входного вала и доля эксцентрика, кручение вала (полый — 1 − β⁴),
шпонка (смятие), стенки эксцентрика, балансировка свёрлами из списка
(ptk_parts.eccentric), масса и момент инерции пакета на входе. Формулы — THEORY.
"""
import math
import re
from types import SimpleNamespace

from egm import ptk_layout, ptk_parts

LINKS = ("key", "flat", "integral", "spline", "press")
CALC = ("key", "flat", "integral")             # spline, press — только кручение вала
NAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
THEORY = (
    "Момент входного вала T_вх = M/(u·eta): M — допускаемый выходной момент SPEC-10, "
    "eta — оценка КПД из входа (η не считается, OQ-08). Доля эксцентрика T_э = ecc_share·T_вх: "
    "ряды сдвинуты по фазе, нагрузка между ними распределена неравномерно (OQ-15).\n\n"
    "Кручение вала: τ = 16·T_вх/(π·d_t³·(1 − β⁴)), d_t = d − t1 при шпонке (ослабление пазом), "
    "β = d_отв/d_t; d_req — диаметр, при котором τ = [τ]. Изгиб не считается, его покрывает "
    "заниженное [τ] (сталь 45 на предварительном этапе — 15…30 МПа).\n\n"
    "Шпонка призматическая, исп. A (DIN 6885 / ГОСТ 23360, таблица keys во входе): "
    "σ_см = 2·T_э/(d·(h − t1)·l_p), l_p = t − b, t — толщина эксцентрика.\n\n"
    "Стенки эксцентрика: у паза — Y(key_angle) − d/2 − t2, напротив эксцентриситета — "
    "D_э/2 − a_ω − d/2; обе ≥ ecc_wall_min.\n\n"
    "Балансировка — Д-36, Д-46, диаметры только из balance.drills. Масса и момент инерции на "
    "входе: эксцентрики (диск со смещением a_ω, минус отверстия), подшипники как кольца, "
    "обегающие ось на a_ω (оценка сверху), вал длиной B пакета; тела не учитываются. "
    "J вых = J вх·u² — то же, приведённое к выходу.")


def select(configs, d):
    """Исполнение шага 1 по id (полный | префикс) и bearing, gen -> (cfg | None, причина)."""
    c = [r for r in configs if r.get("id", "").startswith(d["id"]) and r.get("ok") and r.get("ecc")]
    for k in ("bearing", "gen"):
        if d.get(k) is not None:
            c = [r for r in c if (r.get(k) or "") == d[k]]
    if len(c) == 1:
        return c[0], ""
    if not c:
        f = "".join(f", {k} = {d[k]}" for k in ("bearing", "gen") if d.get(k) is not None)
        return None, f"нет реализуемого исполнения {d['id']}{f} в ptk_configs.json (SPEC-10)"
    return None, f"id {d['id']} неоднозначен: {[r['id'] for r in c]} — уточнить bearing / gen"


def _mass(cfg, ecc, dsh, bore, rho, rows):
    """Масса, г, и момент инерции на входе, кг·м²."""
    De, t, a, b = ecc["De"], ecc["t"], ecc["a"], ecc["bal"]
    q = rho * t * math.pi / 4
    m_e = q * (De ** 2 - dsh ** 2 - b["n"] * b["d"] ** 2)
    J_e = q * De ** 2 * (De ** 2 / 8 + a ** 2) - q * dsh ** 4 / 8
    J_e -= sum(q * b["d"] ** 2 * (b["d"] ** 2 / 8 + x * x + y * y) for x, y in b["holes"])
    brg = cfg["geom"].get("bearing") if cfg["gen"] == "bearing" else None
    m_b = ecc["m_brg_g"] if brg else 0.0
    J_b = m_b * ((brg["D"] ** 2 + brg["d"] ** 2) / 8 + a ** 2) if brg else 0.0
    m_s = rho * math.pi / 4 * (dsh ** 2 - bore ** 2) * float(cfg["width"])
    J = rows * (J_e + J_b) + m_s * (dsh ** 2 + bore ** 2) / 8
    return {"ecc_g": round(m_e, 1), "brg_g": round(m_b, 1), "shaft_g": round(m_s, 1),
            "sum_g": round(rows * (m_e + m_b) + m_s, 1), "J_in": float(f"{J * 1e-9:.3e}"),
            "J_out": float(f"{J * 1e-9 * int(cfg['u']) ** 2:.3e}")}


def design(cfg, d, lim, keys, extra=None):
    """Проработка одного исполнения -> запись ptk_designs.json."""
    name, sh, bal = d["name"], d["shaft"], d.get("balance", {})
    err, warn = [], []
    u, M = int(cfg["u"]), float(cfg.get("M") or 0.0)
    eta, share = float(d.get("eta", 0.8)), float(d.get("ecc_share", 0.5))
    if M <= 0:
        warn.append("M исполнения = 0 — вал и шпонка не нагружены, проверки формальные")
    T_in = M / (u * eta)
    T_e = T_in * share
    link, dsh, bore = sh.get("link", "key"), float(sh["d"]), float(sh.get("bore", 0.0))
    key = next((k for k in keys if dsh <= k["d_max"] + 1e-9), None) if link == "key" else None
    if link == "key" and key is None:
        err.append(f"шпонка: в keys нет размера для вала Ø{dsh:g}")
    if link not in CALC:
        warn.append(f"соединение {link}: расчёт не реализован, проверено только кручение вала")
    if link == "flat":
        warn.append("лыска: смятие не считается, в CAD отверстие круглое")
    if link == "integral":
        warn.append("вал-эксцентрик заодно: CAD детали — CP-05, на чертеже .03 — отверстие вала")
    t1 = key["t1"] if key else 0.0
    d_t, wmin = dsh - t1, float(sh.get("wall_min", 1.5))
    wall = (dsh - bore) / 2 - t1
    if bore and wall < wmin - 1e-9:
        err.append(f"вал: стенка {wall:.2f} < wall_min {wmin:g} мм "
                   f"(Ø{dsh:g}, отв. {bore:g}, t1 {t1:g})")
    k4 = max(1.0 - (bore / d_t) ** 4, 1e-6)
    ta = float(sh.get("tau_allow", 25.0))
    tau = 16 * T_in * 1e3 / (math.pi * d_t ** 3 * k4)
    d_req = (16 * T_in * 1e3 / (math.pi * ta * k4)) ** (1 / 3) + t1
    if tau > ta + 1e-9:
        err.append(f"вал Ø{dsh:g}: τ = {tau:.1f} > [τ] = {ta:g} МПа — нужен d ≥ {d_req:.1f} мм")
    over = {"shaft_d_min": dsh, "shaft_key_b": key["b"] if key else 0.0,
            "shaft_key_t2": key["t2"] if key else 0.0,
            "key_angle": float(d.get("key_angle", lim.key_angle)),
            "bal_n_max": int(bal.get("n_max", lim.bal_n_max)),
            "bal_wall": float(bal.get("wall", lim.bal_wall)),
            "bal_drills": sorted(float(x) for x in bal.get("drills", [])) or None}
    L = SimpleNamespace(**{**vars(lim), **over})
    g = cfg["geom"]
    ecc = ptk_parts.eccentric(int(cfg["n"]), cfg["a_w"], cfg["Drol"], g["roller"], g.get("bearing"),
                              cfg["phasing"], L, cfg["gen"], cfg["R_sum"])
    warn += [w for w in ecc.pop("warnings") if "у паза" not in w]
    wb, kw = ecc["De"] / 2 - ecc["a"] - dsh / 2, min(x["key_wall"] for x in ecc["rows"])
    if min(wb, kw) < lim.ecc_wall_min - 1e-9:
        err.append(f"эксцентрик: стенка {min(wb, kw):.2f} < ecc_wall_min {lim.ecc_wall_min:g} мм "
                   f"(напротив эксцентриситета {wb:.2f}, у паза {kw:.2f})")
    lk = {"type": link, "sigma": None}
    if key:
        lp, kh = ecc["t"] - key["b"], key["h"] - key["t1"]
        sig = 2 * T_e * 1e3 / (dsh * kh * lp) if lp > 0 else 1e9
        sa = float(sh.get("sigma_crush", 100.0))
        lk.update(b=key["b"], h=key["h"], t1=key["t1"], t2=key["t2"], lp=lp,
                  sigma=round(sig, 1), sigma_allow=sa)
        if sig > sa + 1e-9:
            err.append(f"шпонка {key['b']:g}×{key['h']:g}: σ см = {sig:.0f} > [σ] = {sa:g} МПа "
                       f"(l_p = {lp:g} мм)")
    lay = None
    if extra is not None:
        lay, le, lw = ptk_layout.layout(cfg, d, ecc, dsh, L.row_gap, **extra)
        err += le
        warn += lw
    parts = [{**p, "base": p["id"], "id": f"{p['id']}-{name}"}
             for p in ptk_parts.parts(cfg["id"], ecc) if p["id"].split(".", 1)[1].startswith("03")]
    return {"id": cfg["id"], "name": name, "ok": not err, "errors": err, "warnings": warn,
            "input": d, "layout": lay,
            "shaft": {"d": dsh, "bore": bore, "link": link, "eta": eta, "ecc_share": share, "M": M,
                      "T_in": round(T_in, 3), "T_e": round(T_e, 3), "tau": round(tau, 1),
                      "tau_allow": ta, "d_req": round(d_req, 2)},
            "link": lk, "ecc": ecc, "mass": _mass(cfg, ecc, dsh, bore, L.rho * 1e-6,
                                                  len(cfg["phasing"])),
            "parts": parts}


def run(inp, configs, lim, extra=None):
    """ptk_design_input.json -> [запись]; ошибка входа — ValueError (в checks.md)."""
    keys = sorted(inp.get("keys", {}).get("table", []), key=lambda k: k["d_max"])
    out, names = [], set()
    for d in inp.get("designs", []):
        name = str(d.get("name", ""))
        if not NAME_RE.match(name) or name in names:
            raise ValueError(f"designs: имя «{name}» — латиница, цифры, _, без «-», уникальное (Д-48)")
        if d["shaft"].get("link", "key") not in LINKS:
            raise ValueError(f"designs.{name}.shaft.link: {d['shaft'].get('link')} — допустимы {LINKS}")
        names.add(name)
        cfg, why = select(configs, d)
        out.append(design(cfg, d, lim, keys, extra) if cfg else
                   {"id": d["id"], "name": name, "ok": False, "errors": [why], "warnings": [], "input": d})
    return out


def find(designs, cid, name):
    """Запись ptk_designs.json по ID исполнения (детали) и имени проработки."""
    base = cid.split(".")[0]
    for r in designs:
        if r["id"] == base and r["name"] == name and r.get("ecc"):
            return r
    raise KeyError(f"проработка {name} для {base} не найдена в specs/ptk_designs.json — "
                   f"проверить ptk_design_input.json, python main.py --publish (Д-48)")


def pick(designs, arg, name=None):
    """Проработка по --design или суффиксу ID детали (<ID>.03B-K8) -> запись | None."""
    tail = arg.partition(".")[2]
    if not name and "-" in tail:
        name = tail.rsplit("-", 1)[1]
    return find(designs, arg, name) if name else None


def apply(cfg, des):
    """Исполнение шага 1 с эксцентриками и валом проработки (для egm.cad); cfg не меняется."""
    if des is None:
        return cfg
    g = cfg["geom"]
    keep = [p for p in cfg["parts"] if not p["id"].split(".", 1)[1].startswith("03")]
    return {**cfg, "ecc": des["ecc"], "parts": keep + des["parts"],
            "geom": {**g, "limits": {**g["limits"], "shaft_d_min": des["shaft"]["d"]}}}


def md(res):
    """Поля шаблона SPEC-11."""
    L = ["| Проработка | ID | Вал d / отв., мм | Соединение | M, Н·м | T вх / T э, Н·м | "
         "τ / [τ], МПа | σ см / [σ], МПа | Балансировка | Остаток, г·мм | m пакета, г | "
         "J вх, кг·м² | Статус |", "|---" * 13 + "|"]
    P = ["| Деталь | Как на шаге 1 | Паз, ° | Ряды |", "|---|---|---|---|"]
    E, W, C = [], [], [ptk_layout.HEAD, "|---" * 10 + "|"]
    for r in res:
        s = r.get("shaft")
        if s:
            k, b, m = r["link"], r["ecc"]["bal"], r["mass"]
            lk = k["type"] + (f" {k['b']:g}×{k['h']:g}" if k.get("b") else "")
            sig = f"{k['sigma']:g} / {k['sigma_allow']:g}" if k.get("sigma") is not None else "—"
            bal = f"{b['n']}×Ø{b['d']:g}, r {b['r']:g}" if b["n"] else "нет"
            L.append(f"| {r['name']} | {r['id']} | {s['d']:g} / {s['bore']:g} | {lk} | {s['M']:g} | "
                     f"{s['T_in']:g} / {s['T_e']:g} | {s['tau']:g} / {s['tau_allow']:g} | {sig} | "
                     f"{bal} | {b['res']:g} | {m['sum_g']:g} | {m['J_in']:.2e} | "
                     f"{'OK' if r['ok'] else 'нет'} |")
            P += [f"| {p['id']} | {p['base']} | {p['key_angle']:g} | "
                  f"{', '.join(str(x) for x in p['rows'])} |" for p in r["parts"]]
            if r.get("layout"):
                C.append(ptk_layout.md_row(r["name"], r["layout"]))
        else:
            L.append(f"| {r['name']} | {r['id']} |" + " — |" * 10 + " нет |")
        tag = f"- {r['name']} ({r['id']}): "
        E += [tag + e for e in r["errors"]]
        W += [tag + w for w in r["warnings"]]
    return {"summary": "\n".join(L) if res else "нет проработок",
            "parts": "\n".join(P) if len(P) > 2 else "нет",
            "layouts": "\n".join(C) if len(C) > 2 else "нет",
            "errors": "\n".join(E) or "нет", "warnings": "\n".join(W) or "нет",
            "theory": THEORY, "n_ok": sum(r["ok"] for r in res), "n_all": len(res)}


def self_test():
    """Выбор по префиксу, вал Ø8 не проходит по τ, Ø10 проходит; шпонка, детали, cad-ID."""
    lim = SimpleNamespace(sep_gap=0.05, row_gap=1.0, rho=7850.0, brg_mass_k=0.35,
                          shaft_d_min=6.0, shaft_key_b=2.0, shaft_key_t2=1.0, bal_wall=1.0,
                          bal_n_max=3, bal_d_min=1.0, bal_d_step=0.1, ecc_wall_min=1.0,
                          key_angle=45.0, groove_f=0.52)
    ph = [{"row": k + 1, "phi": p, "s": -p} for k, p in enumerate((0, 90, 180, 270))]
    base = {"u": 50, "n": 50, "a_w": 0.4, "Drol": 2.0, "R_sum": 33.5, "M": 100.0, "width": 33.0,
            "ok": True, "ecc": {"t": 7.0}, "phasing": ph,
            "parts": [{"id": "PTK-T-X-AAAAAA.01A", "rows": [1, 2, 3, 4]}],
            "geom": {"roller": {"type": "roller", "d": 2.0, "l": 4.2},
                     "bearing": {"d": 50.0, "D": 65.0, "B": 7.0}, "limits": {"shaft_d_min": 6.0}}}
    cfgs = [{**base, "id": "PTK-T-X-AAAAAA", "gen": "bearing", "bearing": "61810"},
            {**base, "id": "PTK-T-X-BBBBBB", "gen": "eccentric", "bearing": ""}]
    keys = [{"d_max": 8, "b": 2, "h": 2, "t1": 1.2, "t2": 1.0},
            {"d_max": 10, "b": 3, "h": 3, "t1": 1.8, "t2": 1.4}]
    sh = {"link": "key", "tau_allow": 25.0, "sigma_crush": 100.0}
    dr = {"drills": [3.0, 4.0, 5.0]}
    inp = {"keys": {"table": keys}, "designs": [
        {"id": "PTK-T-X", "bearing": "61810", "name": "K8", "shaft": {**sh, "d": 8.0}, "balance": dr},
        {"id": "PTK-T-X", "gen": "bearing", "name": "K10", "shaft": {**sh, "d": 10.0}, "balance": dr},
        {"id": "PTK-T-X", "name": "AMB", "shaft": {**sh, "d": 10.0}}]}
    r8, r10, amb = run(inp, cfgs, lim)
    assert not r8["ok"] and any("τ" in e for e in r8["errors"]), r8["errors"]
    assert r10["ok"], r10["errors"]
    assert abs(r10["shaft"]["tau"] - 23.1) < 0.2, r10["shaft"]
    assert abs(r10["link"]["sigma"] - 52.1) < 0.2, r10["link"]
    b = r10["ecc"]["bal"]
    assert b["n"] >= 1 and b["d"] in (3.0, 4.0, 5.0), b
    assert "неоднозначен" in amb["errors"][0], amb
    assert [p["id"] for p in r10["parts"]] == [f"PTK-T-X-AAAAAA.03{v}-K10" for v in "ABCD"], r10["parts"]
    assert r10["mass"]["J_in"] > 0 and r10["mass"]["sum_g"] > 0, r10["mass"]
    assert pick([r10], "PTK-T-X-AAAAAA.03B-K10") is r10
    assert pick([r10], "PTK-T-X-AAAAAA") is None and pick([r10], "PTK-T-X-AAAAAA", "K10") is r10
    c = apply(cfgs[0], r10)
    assert c["geom"]["limits"]["shaft_d_min"] == 10.0 == r10["shaft"]["d"]
    assert cfgs[0]["geom"]["limits"]["shaft_d_min"] == 6.0, "apply изменил исходную запись"
    assert sorted(p["id"] for p in c["parts"] if ".03" in p["id"])[0].endswith("-K10")
    ri = design(cfgs[0], {"name": "I", "shaft": {"d": 10.0, "link": "integral"}}, lim, keys)
    assert ri["ok"] and ri["link"]["sigma"] is None and ri["ecc"]["key_b"] == 0.0, ri["errors"]
    assert "K10" in md([r8, r10, amb])["summary"]
    try:
        run({"designs": [{"id": "x", "name": "K-8", "shaft": {"d": 8.0}}]}, cfgs, lim)
        raise AssertionError("имя с «-» принято")
    except ValueError:
        pass
    assert ptk_layout.self_test()
    return True
