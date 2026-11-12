"""Шаг 2 — проработка выбранного исполнения ПТК (Д-48, CP-38).

Вход: specs/ptk_design_input.yaml → designs[]; исполнение шага 1 — ptk_configs.yaml.
Выход: ptk_designs.yaml (комментированный YAML, design_doc) и SPEC-11_PTK_DESIGN.md; детали проработки — <ID>.03<вар>-<name>.
Исполнение задаётся полным ID или префиксом без хэша (+ bearing, gen): хэш меняется
с геометрией шага 1 (Д-80), а проработка остаётся привязанной (Д-51).
Считается: момент входного вала и доля эксцентрика, кручение вала (полый — 1 − β⁴),
шпонка (смятие), стенки эксцентрика, балансировка свёрлами из списка
(ptk_parts.eccentric), масса и момент инерции пакета на входе. Формулы — THEORY.
"""
import math
import re
from types import SimpleNamespace

from egm import config, ptk_layout, ptk_parts

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
    "Шпонка призматическая, исп. A (DIN 6885 / ГОСТ 23360, keys.table в specs/shafts.yaml, "
    "Д-109): "
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
        return None, f"нет реализуемого исполнения {d['id']}{f} в ptk_configs.yaml (SPEC-10)"
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
        lay, le, lw = ptk_layout.layout(cfg, {**d, "_keys": keys}, ecc, dsh, L.row_gap,
                                        **extra)   # CP-90: шпонки выходного вала — та же keys.table
        err += le
        warn += lw
    parts = [{**p, "base": p["id"], "id": f"{p['id']}-{name}"}
             for p in ptk_parts.parts(cfg["id"], ecc) if p["id"].split(".", 1)[1].startswith("03")]
    return {"id": cfg["id"], "name": name, "ok": not err, "errors": err, "warnings": warn,
            "input": d, "layout": lay, "keys": keys,       # CP-90: шпонки выхода — для egm.cad
            "shaft": {"d": dsh, "bore": bore, "link": link, "eta": eta, "ecc_share": share, "M": M,
                      "T_in": round(T_in, 3), "T_e": round(T_e, 3), "tau": round(tau, 1),
                      "tau_allow": ta, "d_req": round(d_req, 2)},
            "link": lk, "ecc": ecc, "mass": _mass(cfg, ecc, dsh, bore, L.rho * 1e-6,
                                                  len(cfg["phasing"])),
            "parts": parts}


def keys_table(app=None):
    """Таблица шпонок из номенклатуры валов (Д-109, OQ-35 решён).

    Источник — products.SH.configs.shafts (configs/application.yaml → specs/shafts.yaml)
    → keys.table. Одна таблица на входной вал и на выходной вал в ступице (CP-90);
    во входе проработки её нет: паз — свойство сечения вала, а не проработки.
    """
    app = config.load_app() if app is None else app
    rel = config.cfg_file(app, "products.SH.configs.shafts")
    tbl = ((config.load(rel) or {}).get("keys") or {}).get("table")
    if not tbl:
        raise ValueError(f"{rel.relative_to(config.ROOT)}: нет keys.table — таблица "
                         f"шпонок живёт в номенклатуре валов (Д-109)")
    return tbl


def run(inp, configs, lim, extra=None, keys=None):
    """ptk_design_input.yaml -> [запись]; ошибка входа — ValueError (в checks.md).

    keys — таблица шпонок; None — читается из номенклатуры валов (Д-109).
    """
    if inp.get("keys"):
        raise ValueError("ptk_design_input: ключ keys перенесён в specs/shafts.yaml → "
                         "keys.table (Д-109) — во входе проработки его быть не должно")
    keys = sorted(keys if keys is not None else keys_table(), key=lambda k: k["d_max"])
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
    raise KeyError(f"проработка {name} для {base} не найдена в specs/ptk_designs.yaml — "
                   f"проверить ptk_design_input.yaml, python main.py --publish (Д-48)")


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
    g, lay = cfg["geom"], des.get("layout") or {}
    extra = lay.get("cad_parts") or []                 # CP-45: .02A|B, .07A/B, .11 конструктива
    drop = {"03"} | {p["id"].split(".", 1)[1][:2] for p in extra}
    keep = [p for p in cfg["parts"] if p["id"].split(".", 1)[1][:2] not in drop]
    return {**cfg, "ecc": des["ecc"], "parts": keep + des["parts"] + extra, "layout": lay or None,
            "geom": {**g, "limits": {**g["limits"], "shaft_d_min": des["shaft"]["d"]}}}


def md(res):
    """Формирование разделов SPEC-11 в новом порядке.

    Структура:
    1. Сводка (транспонированная таблица параметров × проработок)
    2. Детали проработки (таблица)
    3. Номенклатура (01–14)
    4. Конструктивы L1–L4 (справочный блок)
    5. Проработка K8 — весь блок данных по проработке:
       - Конструктив (выбранный)
       - Состав (номенклатура деталей)
       - Подшипники и опоры
       - Соединение .02–.12
       - Выход: вал в ступице
       - Заготовка .02
       - Балансировка и масса
       - Оснастка
       - Ошибки и предупреждения (внутри блока проработки)
    6. Проработка K10 — аналогично
    7. Расчёт (теория)

    Примечание: ошибки и предупреждения выводятся только внутри блоков
    проработок (К8, К10). Общие разделы "Ошибки"/"Предупреждения" в конце
    убраны — они дублировали информацию.
    """
    P = ["| Деталь | Как на шаге 1 | Паз, ° | Ряды |", "|---|---|---|---|"]

    for r in res:
        s = r.get("shaft")
        if s:
            P += [f"| {p['id']} | {p['base']} | {p['key_angle']:g} | "
                  f"{', '.join(str(x) for x in p['rows'])} |" for p in r["parts"]]

    # Генерация блоков по проработкам
    workpieces = []
    for r in res:
        if r.get("shaft"):
            workpieces.append(_md_workpiece(r))

    # Блок конструктивов L1–L4
    layouts_block = ptk_layout.md_layouts_info()

    # Блок номенклатуры
    nomenclature_block = ptk_layout.md_nomenclature()

    return {
        "summary": _md_summary(res) if res else "нет проработок",
        "parts": "\n".join(P) if len(P) > 2 else "нет",
        "workpieces": "\n\n".join(workpieces) if workpieces else "нет",
        "layouts": layouts_block,
        "nomenclature": nomenclature_block,
        "theory": THEORY,
        "n_ok": sum(r["ok"] for r in res),
        "n_all": len(res)
    }


def _md_workpiece(r):
    """Генерация полного блока данных по одной проработке (вертикальный формат)."""
    lines = []
    name = r["name"]
    ok_mark = "✓ OK" if r["ok"] else "✗ ОШИБКА"

    lines.append(f"### Проработка {name} — {ok_mark}")
    lines.append("")
    lines.append(f"**ID:** {r['id']}")
    lines.append("")

    # --- Конструктив ---
    lay = r.get("layout")
    if lay:
        lines.append("#### Конструктив")
        lines.append("")
        code = lay.get("code", "—")
        title = lay.get("name", "—")
        lines.append(f"Выбран: **{code}** — {title}")
        lines.append("")

        # Состав — список деталей в этом конструктиве
        parts_dict = lay.get("parts", {})
        var = lay.get("var", {})
        if parts_dict:
            lines.append("| Позиция | Обозначение | Наименование |")
            lines.append("|---|---|---|")
            for pos in sorted(parts_dict.keys(), key=lambda x: int(x) if x.isdigit() else 0):
                det = parts_dict[pos]
                var_name = f"{det}{var.get(pos, '')}"
                # Получаем расшифровку из номенклатуры
                desc = ptk_layout.get_nomenclature_desc(pos)
                lines.append(f"| .{pos} | {var_name} | {desc} |")
            lines.append("")

        # Длина
        length = lay.get("length")
        if length is not None:
            lines.append(f"**Длина по оси:** {length:g} мм")
            lines.append("")

    # --- Подшипники и опоры ---
    if lay:
        b09 = lay.get("b09")
        b10 = lay.get("b10")
        if b09 or b10:
            lines.append("#### Подшипники и опоры (.09 — подшипник выхода, .10 — подшипник генератора)")
            lines.append("")
            lines.append("| Подшипник | Обозначение | d×D×B, мм | C, кН | da, мм |")
            lines.append("|---|---|---|---|---|")
            if b09:
                lines.append(f"| .09 выход | {b09.get('id', '—')} | {b09.get('d', '—')}×{b09.get('D', '—')}×{b09.get('B', '—')} | {b09.get('C', '—')} | {b09.get('da', '—')} |")
            if b10:
                lines.append(f"| .10 вход | {b10.get('id', '—')} | {b10.get('d', '—')}×{b10.get('D', '—')}×{b10.get('B', '—')} | {b10.get('C', '—')} | {b10.get('da', '—')} |")
            lines.append("")

            # Доп. данные опор
            tau_hub = lay.get("tau_hub")
            if tau_hub is not None:
                tau_allow = lay.get("tau_allow", 25)
                lines.append(f"**τ ступицы:** {tau_hub:g} / [{tau_allow}] МПа — касательное напряжение кручения ступицы")
            r11 = lay.get("r11")
            if r11:
                lines.append(f"**Кольцо .11:** {r11.get('n', 0)} × {r11.get('h', 0):g} мм")
            covers = lay.get("covers")
            if covers:
                tA = covers.get("tA")
                tB = covers.get("tB")
                if tA is not None and tB is not None:
                    lines.append(f"**Крышки:** .07A (вход) = {tA:g} мм, .07B (выход) = {tB:g} мм")
            cup = lay.get("cup")
            if cup:
                z_in = cup.get("z_in")
                t = cup.get("t")
                hub_d = cup.get("hub_d")
                hub_l = cup.get("hub_l")
                if z_in is not None and t is not None:
                    txt = f"**Дно .02:** z = {z_in:g}, t = {t:g} мм"
                    if hub_d and hub_l:
                        txt += f"; ступица Ø{hub_d:g}×{hub_l:g} мм"
                    lines.append(txt)
            lines.append("")

            # --- Стопорные кольца ГОСТ 13942 / 13943 ---
            grooves = (lay.get("output") or {}).get("grooves")
            if grooves:
                ext = grooves.get("ext")
                int_ = grooves.get("int")
                if ext or int_:
                    lines.append("**Стопорные кольца .09 (ГОСТ 13942 / 13943):**")
                    if ext:
                        std = ext.get("std", "ГОСТ 13942-86")
                        s = ext.get("s", "—")
                        m = ext.get("m", "—")
                        d2 = ext.get("d2", "—")
                        d9 = b09.get("d", "—") if b09 else "—"
                        lines.append(f"- rings_ext (вал): d = {d9} → {std}, s = {s} мм, m = {m} мм, d2 = {d2} мм")
                    if int_:
                        std = int_.get("std", "ГОСТ 13943-86")
                        s = int_.get("s", "—")
                        m = int_.get("m", "—")
                        d2 = int_.get("d2", "—")
                        D9 = b09.get("D", "—") if b09 else "—"
                        lines.append(f"- rings_int (корпус): D = {D9} → {std}, s = {s} мм, m = {m} мм, d2 = {d2} мм")
                    # Кольцо .11 уже выведено выше
            lines.append("")

    # --- Соединение .02–.12 ---
    if lay and lay.get("join"):
        join = lay["join"]
        pick = join.get("pick")
        if pick:
            lines.append("#### Соединение .02–.12 (Сепаратор — Ступица выхода)")
            lines.append("")
            scheme = pick.get("scheme", "—")
            lines.append(f"**Схема:** {scheme}")

            pins = pick.get("pins")
            if pins:
                n = pins.get("n", 0)
                d = pins.get("d", 0)
                l = pins.get("l", 0)
                tau = pins.get("tau")
                sig_wall = pins.get("sig_wall")
                sig_hub = pins.get("sig_hub")
                tau_edge = pins.get("tau_edge")
                des = pins.get("des", "")
                lines.append(f"**Штифты:** {n} × Ø{d:g} × {l:g} мм — {des}")
                if tau is not None:
                    lines.append(f"  - τ среза штифта: {tau:g} МПа — касательное напряжение среза штифта")
                if sig_wall is not None:
                    lines.append(f"  - σсм стенки .02: {sig_wall:g} МПа — смятие стенки сепаратора под штифтом")
                if sig_hub is not None:
                    lines.append(f"  - σсм ступицы .12: {sig_hub:g} МПа — смятие ступицы под штифтом")
                if tau_edge is not None:
                    lines.append(f"  - τ среза к торцу: {tau_edge:g} МПа — срез перемычки от штифта до торца")
            lines.append("")

    # --- Выход: вал в ступице ---
    if lay and lay.get("output"):
        out = lay["output"]
        lines.append("#### Выход: вал в ступице")
        lines.append("")
        d_o = out.get("d")
        if d_o:
            lines.append(f"**Ø выходного вала:** {d_o:g} мм")
        key = out.get("key")
        if key:
            b, h, l_key = key.get("b", 0), key.get("h", 0), out.get("l_key", 0)
            lines.append(f"**Шпонка:** {b:g}×{h:g}×{l_key:g} мм")
        tau = out.get("tau")
        if tau is not None:
            tau_allow = out.get("tau_allow", 25)
            lines.append(f"**τ вала:** {tau:g} / [{tau_allow}] МПа")
        flange = out.get("flange")
        if flange:
            fl_txt = out.get("fl_txt", "")
            if fl_txt:
                lines.append(f"**Фланец:** {fl_txt}")
        hub_l = out.get("hub_l")
        if hub_l is not None:
            hub_by = out.get("hub_by", "")
            lines.append(f"**Длина ступицы:** {hub_l:g} мм ({hub_by})")
        rh = out.get("r_h")
        if rh is not None:
            lines.append(f"**r_h .09 (da/2):** {rh:g} мм")
        lines.append("")

    # --- Заготовка .02 ---
    if lay and lay.get("blank"):
        bl = lay["blank"]
        lines.append("#### Заготовка .02")
        lines.append("")
        mat = bl.get("material")
        if mat:
            lines.append(f"**Материал:** {mat}")
        tube = bl.get("tube")
        if tube:
            D = tube.get("D")
            s = tube.get("s")
            note = tube.get("note", "")
            txt = f"**Труба:** Ø{D:g} × {s:g} мм"
            if note:
                txt += f" ({note})"
            lines.append(txt)
        alt = bl.get("alt")
        if alt:
            lines.append(f"**Альтернативы:** {', '.join(alt)}")
        lines.append("")

    # --- Балансировка и масса ---
    ecc = r.get("ecc", {})
    bal = ecc.get("bal", {})
    mass = r.get("mass", {})
    if bal or mass:
        lines.append("#### Балансировка и масса")
        lines.append("")
        bal_n = bal.get("n", 0)
        bal_d = bal.get("d", 0)
        bal_r = bal.get("r", 0)
        if bal_n:
            lines.append(f"**Балансировка:** {bal_n} × Ø{bal_d:g} мм, радиус {bal_r:g} мм")
        res_u = bal.get("res")
        if res_u is not None:
            lines.append(f"**Остаточный дисбаланс:** {res_u:g} г·мм")
        lines.append(f"**m пакета:** {mass.get('sum_g', 0):g} г")
        lines.append(f"**J вх:** {mass.get('J_in', 0):.2e} кг·м²")
        lines.append(f"**J вых:** {mass.get('J_out', 0):.2e} кг·м²")
        lines.append("")

    # --- Оснастка ---
    if lay and lay.get("tooling"):
        tooling = lay["tooling"]
        lines.append("#### Оснастка (Д-81)")
        lines.append("")
        lines.append("| Операция | Деталь | Размер | Маршрут |")
        lines.append("|---|---|---|---|")
        for t in tooling:
            fx = t.get("fx", "—")
            part = t.get("part", "—")
            size = t.get("size", "—")
            route = t.get("route", "—")
            lines.append(f"| {fx} | {part} | {size} | {route} |")
        lines.append("")

    # --- Ошибки и предупреждения ---
    if r.get("errors"):
        lines.append("##### Ошибки")
        lines.append("")
        for e in r["errors"]:
            lines.append(f"- {e}")
        lines.append("")

    if r.get("warnings"):
        lines.append("##### Предупреждения")
        lines.append("")
        for w in r["warnings"]:
            lines.append(f"- {w}")
        lines.append("")

    return "\n".join(lines)


def _md_summary(res):
    """Транспонированная таблица «Сводка»: параметры как строки, проработки как колонки.
    Колонка «Описание» содержит расшифровку каждого параметра.
    """
    names = [r["name"] for r in res if r.get("shaft")]
    if not names:
        return "нет проработок"

    # Расшифровки параметров
    DESCR = {
        "ID": "ID исполнения шага 1 (SPEC-10).",
        "Вал d": "Ø входного вала, мм (расчёт кручения, шпонка).",
        "Соединение .03–вал": "Тип и размер: шпонка b×h / лыска / вал-эксцентрик.",
        "M выходной": "M выходной, Н·м — допускаемый момент из SPEC-10.",
        "T вх / T э": "T вх — момент на входе, Н·м; T э — доля на один эксцентрик, Н·м.",
        "τ кручения": "τ вала, МПа — кручение с ослаблением шпоночным пазом.",
        "σсм шпонки": "σсм шпонки, МПа — смятие рабочей высоты паза.",
        "Балансировка": "Балансировка: число отверстий × Ø, радиус r (Д-36, Д-46).",
        "Остат. дисб.": "Остаточный дисбаланс после балансировки, г·мм.",
        "m пакета": "m пакета, г — суммарная масса эксцентриков, подшипников и вала.",
        "J вх": "J вх, кг·м² — момент инерции пакета на входе (приведённый к выходу: J вых = J вх·u²).",
        "Итог": "✓ — все проверки пройдены; ✗ — есть ошибки (не проходят вал/шпонка/стенка).",
    }

    H = "| Параметр | " + " | ".join(names) + " | Описание |"
    R = "|---" * (len(names) + 2) + "|"

    def _ok(r):
        return "✓" if r["ok"] else "✗"

    params = {}
    for r in res:
        s = r.get("shaft")
        if not s:
            continue
        k = r["link"]
        b = r["ecc"]["bal"]

        lk = k["type"]
        if k.get("b"):
            lk = f"шпонка {k['b']:g}×{k['h']:g}"
        elif k.get("type") in ("flat",):
            lk = "лыска"
        elif k.get("type") in ("integral",):
            lk = "вал-эксцентрик"

        bal = f"{b['n']}×Ø{b['d']:g} r {b['r']:g}" if b["n"] else "нет"

        params.setdefault("ID", {})[r["name"]] = r["id"]
        params.setdefault("Вал d", {})[r["name"]] = f"Ø{s['d']:g} мм" if s["d"] else "—"
        params.setdefault("Соединение .03–вал", {})[r["name"]] = lk
        params.setdefault("M выходной", {})[r["name"]] = f"{s['M']:g} Н·м"
        params.setdefault("T вх / T э", {})[r["name"]] = f"{s['T_in']:g} / {s['T_e']:g} Н·м"
        params.setdefault("τ кручения", {})[r["name"]] = f"{s['tau']:g} / {s['tau_allow']:g} МПа"
        params.setdefault("σсм шпонки", {})[r["name"]] = (
            f"{k['sigma']:g} / {k['sigma_allow']:g} МПа" if k.get("sigma") is not None else "—"
        )
        params.setdefault("Балансировка", {})[r["name"]] = bal
        params.setdefault("Остат. дисб.", {})[r["name"]] = f"{b['res']:g} г·мм"
        params.setdefault("m пакета", {})[r["name"]] = f"{r['mass']['sum_g']:g} г"
        params.setdefault("J вх", {})[r["name"]] = f"{r['mass']['J_in']:.2e} кг·м²"
        params.setdefault("Итог", {})[r["name"]] = _ok(r)

    out = [H, R]
    for param, vals in params.items():
        cells = " | ".join(f"{vals.get(n, '—')}" for n in names)
        desc = DESCR.get(param, "")
        out.append(f"| {param} | {cells} | {desc} |")

    return "\n".join(out)


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
    inp = {"designs": [
        {"id": "PTK-T-X", "bearing": "61810", "name": "K8", "shaft": {**sh, "d": 8.0}, "balance": dr},
        {"id": "PTK-T-X", "gen": "bearing", "name": "K10", "shaft": {**sh, "d": 10.0}, "balance": dr},
        {"id": "PTK-T-X", "name": "AMB", "shaft": {**sh, "d": 10.0}}]}
    r8, r10, amb = run(inp, cfgs, lim, keys=keys)
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
        run({"designs": [{"id": "x", "name": "K-8", "shaft": {"d": 8.0}}]}, cfgs, lim, keys=keys)
        raise AssertionError("имя с «-» принято")
    except ValueError:
        pass
    try:                      # Д-109: keys во входе — ошибка, а не тихое игнорирование
        run({"keys": {"table": keys}, "designs": []}, cfgs, lim)
        raise AssertionError("keys.table во входе принята")
    except ValueError as e:
        assert "Д-109" in str(e), e
    assert keys_table(), "keys.table пуста (Д-109)"
    assert ptk_layout.self_test()
    return True
