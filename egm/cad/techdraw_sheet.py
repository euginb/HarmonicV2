"""Лист TechDraw деталей (Д-66, CP-56): рамка, основная надпись, зоны, блоки SVG — без FreeCAD.

A3 альбомный 420×297. Координаты листа TechDraw — мм от левого нижнего угла, Y вверх;
X, Y вида и символа — его центр (OQ-20). Шаблон (template_svg) — в координатах SVG (Y вниз).
Зоны:
  рамка — поле 20 мм слева, 5 мм с остальных сторон (ГОСТ 2.301);
  основная надпись 185×55 — правый нижний угол (упрощённая форма 1 ГОСТ 2.104, OQ-21),
  графа 26 (обозначение, повёрнуто на 180°) — левый верхний угол;
  зона видов VZ — слева: вид по оси и вид сбоку (z по горизонтали), масштаб ГОСТ 2.302;
  под видами — блок предупреждений (красный), если есть;
  правая колонка COL над основной надписью: легенда, примечания, ISO-вид.
Легенда, примечания, предупреждения — SVG-символы (TechDraw::DrawViewSymbol): шрифт, переносы
и ширина колонок задаются здесь; Spreadsheet/LegendView и аннотации не создаются (Д-66).
"""
from xml.sax.saxutils import escape

from egm.cad import techdraw as TD

W, H = 420.0, 297.0
FRAME = (20.0, 5.0, 415.0, 292.0)          # рамка x0, y0, x1, y1 (Y вверх)
TB_W, TB_H = 185.0, 55.0                   # основная надпись
TB_X = FRAME[2] - TB_W                     # 230
COL = (TB_X + 1.0, FRAME[1] + TB_H + 3.0, FRAME[2] - 1.0, FRAME[3] - 3.0)
COL_W = COL[2] - COL[0]                    # 183
VZ = (FRAME[0] + 3.0, FRAME[1] + 3.0, TB_X - 5.0, FRAME[3] - 3.0)
PAD = 12.0                                 # поле вокруг видов под размеры, мм
GAP = TD.GAP
FONT = "Arial, 'DejaVu Sans', 'Liberation Sans', sans-serif"
FONT_NAME = "Arial"                        # шрифт текста размеров (ViewObject.Font)
DIM_TEXT = 3.5
TEXT, CHAR, LEAD = 2.5, 0.6, 1.6           # кегль, ширина знака / кегль, интервал
RED = "#d00000"
WARN_MAX = 10
ISO_MIN = 30.0
SYM_SCALE = 1.0                            # масштаб SVG-символов (OQ-20)
NS = "http://www.freecad.org/wiki/index.php?title=Svg_Namespace"
LEG_COLS = (("Обозн.", 18.0), ("Значение", 24.0), ("Источник", 28.0),
            ("Смысл — колонки SPEC-10 / SPEC-11", None))
FIELDS = ("designation", "designation_top", "name1", "name2", "material", "mass", "letter",
          "scale", "sheet", "sheets", "dev", "chk", "date", "org")
ORG = "EG-MACHINES"


def wrap(text, width, size=TEXT):
    """Перенос по словам под ширину width мм при кегле size."""
    n = max(4, int(width / (CHAR * size)))
    out = []
    for para in str(text).split("\n"):
        line = ""
        for w in para.split():
            while len(w) > n:
                if line:
                    out.append(line)
                    line = ""
                out.append(w[:n])
                w = w[n:]
            if not line:
                line = w
            elif len(line) + 1 + len(w) <= n:
                line += " " + w
            else:
                out.append(line)
                line = w
        out.append(line)
    return out


def _ln(x1, y1, x2, y2, w=0.35):
    return (f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="#000" stroke-width="{w:g}"/>')


def _rect(x, y, w, h, sw=0.7):
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'fill="none" stroke="#000" stroke-width="{sw:g}"/>')


def _text(x, y, s, size=TEXT, fill="#000", weight="normal", anchor="start"):
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{FONT}" font-size="{size:g}" '
            f'fill="{fill}" font-weight="{weight}" text-anchor="{anchor}">{escape(str(s))}</text>')


def _ed(name, x, y, size=3.5, anchor="middle", rot=False):
    tr = f' transform="rotate(180 {x:.2f} {y:.2f})"' if rot else ""
    return (f'<text freecad:editable="{name}" x="{x:.2f}" y="{y:.2f}" font-family="{FONT}" '
            f'font-size="{size:g}" text-anchor="{anchor}"{tr}>'
            f'<tspan x="{x:.2f}" y="{y:.2f}"> </tspan></text>')


def _svg(w, h, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:.2f}mm" height="{h:.2f}mm" '
            f'viewBox="0 0 {w:.2f} {h:.2f}">' + "".join(body) + "</svg>")


def legend_svg(rows, width=None):
    """Легенда [обозн., значение, источник, смысл] -> (svg, w, h); строки с ⚠ — красным."""
    width = width or COL_W
    fixed = sum(w for _, w in LEG_COLS if w)
    ws = [w or width - fixed for _, w in LEG_COLS]
    lh = LEAD * TEXT
    data = [[c for c, _ in LEG_COLS]] + [[str(x) for x in r] for r in rows]
    body, y, ys = [], 0.0, [0.0]
    for i, row in enumerate(data):
        cells = [wrap(c, w - 2.0) for c, w in zip(row, ws)]
        fill = RED if i and any("⚠" in c for c in row) else "#000"
        x = 0.0
        for c, w in zip(cells, ws):
            for j, s in enumerate(c):
                body.append(_text(x + 1.0, y + 0.75 + (j + 0.8) * lh, s, fill=fill,
                                  weight="bold" if i == 0 else "normal"))
            x += w
        y += max(len(c) for c in cells) * lh + 1.5
        ys.append(y)
    body += [_ln(0.0, q, width, q, 0.5 if k in (0, 1, len(ys) - 1) else 0.18)
             for k, q in enumerate(ys)]
    x = 0.0
    for k, w in enumerate([0.0] + ws):
        x += w
        body.append(_ln(x, 0.0, x, y, 0.5 if k in (0, len(ws)) else 0.18))
    return _svg(width, y, body), width, y


def block_svg(title, lines, width, fill="#000", max_lines=None, numbered=False):
    """Текстовый блок с заголовком -> (svg, w, h); сверх max_lines — ссылка на отчёт."""
    lh = LEAD * TEXT
    out = []
    for k, s in enumerate(lines, 1):
        out += wrap(f"{k}. {s}" if numbered else str(s), width - 2.0)
    if max_lines and len(out) > max_lines:
        out = out[:max_lines - 1] + [f"… ещё строк: {len(out) - max_lines + 1} — "
                                     "полностью в <ID>.techdraw.md"]
    body = [_text(1.0, 0.75 + 0.8 * lh, title, fill=fill, weight="bold")]
    body += [_text(1.0, 0.75 + (j + 1.8) * lh, s, fill=fill) for j, s in enumerate(out)]
    h = (len(out) + 1) * lh + 1.5
    return _svg(width, h, body), width, h


def layout(d, l, legend, notes, warns, scales=None):
    """Масштаб, центры видов и блоков по габариту формы из STEP (d — max(X, Y), l — Z)."""
    scales = tuple(scales or TD.SCALES)
    blocks, over = [], []
    top = COL[3]
    svg, w, h = legend_svg(legend)
    blocks.append({"name": "Legend", "svg": svg, "x": COL[0] + w / 2, "y": top - h / 2,
                   "w": w, "h": h})
    top -= h + 4.0
    if notes:
        svg, w, h = block_svg("Примечания", notes, COL_W, numbered=True)
        blocks.append({"name": "Notes", "svg": svg, "x": COL[0] + w / 2, "y": top - h / 2,
                       "w": w, "h": h})
        top -= h + 4.0
    if top < COL[1]:
        over.append(f"правая колонка переполнена на {COL[1] - top:.0f} мм")
    vw, wy = VZ[2] - VZ[0], VZ[1]
    if warns:
        svg, w, h = block_svg("ПРЕДУПРЕЖДЕНИЯ: 3D (STEP) ≠ .assy.json (Д-65)", warns, vw, RED,
                              WARN_MAX)
        blocks.append({"name": "Warn", "svg": svg, "x": VZ[0] + w / 2, "y": VZ[1] + h / 2,
                       "w": w, "h": h})
        wy = VZ[1] + h + 3.0
    aw, ah = vw - 2 * PAD, VZ[3] - wy - 2 * PAD
    s = next((q for q in scales if d * q <= ah and (d + l) * q + GAP <= aw), scales[-1])
    span = (d + l) * s + GAP
    x0 = VZ[0] + PAD + max(0.0, (aw - span) / 2)
    cy = (wy + VZ[3]) / 2
    views = {"front": [x0 + d * s / 2, cy, s], "side": [x0 + d * s + GAP + l * s / 2, cy, s],
             "iso": None}
    box = top - COL[1]
    need = d + 0.85 * l
    iso = next((q for q in scales if q <= s and need * q <= min(box - 4.0, COL_W)), None)
    if iso is not None and box >= ISO_MIN:
        views["iso"] = [COL[0] + COL_W / 2, COL[1] + box / 2, iso]
    else:
        over.append("ISO-вид не помещается в правую колонку — не построен")
    return {"scale": s, "scale_txt": TD.scale_txt(s), "d": d, "l": l, "views": views,
            "blocks": blocks, "overflow": over}


def template_svg(ns=NS):
    """Шаблон A3: рамка, графа 26, основная надпись; поля — freecad:editable (FIELDS)."""
    x0, y0, fy0 = TB_X, H - FRAME[1] - TB_H, H - FRAME[3]

    def X(dx):
        return x0 + dx

    def Y(dy):
        return y0 + dy

    b = [_rect(FRAME[0], fy0, FRAME[2] - FRAME[0], FRAME[3] - FRAME[1]),
         _rect(x0, y0, TB_W, TB_H), _rect(FRAME[0], fy0, 70.0, 14.0),
         _ed("designation_top", FRAME[0] + 35.0, fy0 + 9.0, 3.0, rot=True)]
    b.append(_ln(X(7.0), Y(0.0), X(7.0), Y(30.0)))
    for dx in (17.0, 40.0, 55.0):
        b.append(_ln(X(dx), Y(0.0), X(dx), Y(TB_H)))
    b.append(_ln(X(65.0), Y(0.0), X(65.0), Y(TB_H), 0.7))
    for k in range(1, 11):
        b.append(_ln(X(0.0), Y(5.0 * k), X(65.0), Y(5.0 * k), 0.7 if k in (5, 6) else 0.35))
    for dx, s in ((3.5, "Изм."), (12.0, "Лист"), (28.5, "№ докум."), (47.5, "Подп."),
                  (60.0, "Дата")):
        b.append(_text(X(dx), Y(28.8), s, anchor="middle"))
    for k, s in enumerate(("Разраб.", "Пров.", "Т.контр.", "Н.контр.", "Утв.")):
        b.append(_text(X(1.0), Y(33.8 + 5.0 * k), s))
    b += [_ln(X(65.0), Y(15.0), X(185.0), Y(15.0), 0.7),
          _ln(X(65.0), Y(40.0), X(185.0), Y(40.0), 0.7),
          _ln(X(135.0), Y(15.0), X(135.0), Y(55.0), 0.7),
          _ln(X(135.0), Y(20.0), X(185.0), Y(20.0)), _ln(X(135.0), Y(35.0), X(185.0), Y(35.0)),
          _ln(X(150.0), Y(15.0), X(150.0), Y(35.0)), _ln(X(167.0), Y(15.0), X(167.0), Y(35.0)),
          _ln(X(160.0), Y(35.0), X(160.0), Y(40.0))]
    for dx, s in ((142.5, "Лит."), (158.5, "Масса"), (176.0, "Масштаб")):
        b.append(_text(X(dx), Y(18.8), s, anchor="middle"))
    b += [_text(X(136.0), Y(38.8), "Лист"), _text(X(161.0), Y(38.8), "Листов"),
          _ed("designation", X(125.0), Y(9.5)), _ed("name1", X(100.0), Y(26.0)),
          _ed("name2", X(100.0), Y(32.5)), _ed("letter", X(142.5), Y(29.0)),
          _ed("mass", X(158.5), Y(29.0)), _ed("scale", X(176.0), Y(29.0)),
          _ed("sheet", X(152.0), Y(38.8), TEXT), _ed("sheets", X(176.0), Y(38.8), TEXT),
          _ed("material", X(100.0), Y(49.0)), _ed("org", X(160.0), Y(49.0)),
          _ed("dev", X(28.5), Y(33.8), TEXT), _ed("chk", X(28.5), Y(38.8), TEXT),
          _ed("date", X(60.0), Y(33.8), 2.0)]
    return (f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:freecad="{ns}" width="{W:g}mm" '
            f'height="{H:g}mm" viewBox="0 0 {W:g} {H:g}">' + "".join(b) + "</svg>\n")


def title_fields(pid, rec, sh, date=""):
    """Значения полей основной надписи (EditableTexts)."""
    n = wrap(rec.get("name") or rec.get("label", ""), 68.0, 3.5) + ["", ""]
    return {"designation": pid, "designation_top": pid, "name1": n[0], "name2": n[1],
            "material": rec.get("material", ""), "mass": "", "letter": "",
            "scale": sh["scale_txt"], "sheet": "1", "sheets": "1", "dev": "", "chk": "",
            "date": date, "org": ORG}


def self_test():
    """Переносы, легенда, зоны листа (виды, колонка, предупреждения), шаблон, поля."""
    w = wrap("один два три четыре пять", 12.0)
    assert all(len(s) <= 8 for s in w) and " ".join(w) == "один два три четыре пять", w
    leg, lw, lh = legend_svg([["D", "95", "3D", "наружный диаметр " * 10],
                              ["DВ", "69.8", "расчёт ⚠ не измерено по 3D", "x"]])
    assert leg.startswith("<svg") and lh > 3 * LEAD * TEXT and RED in leg, lh
    sh = layout(95.0, 4.2, [["D", "95", "3D", "x"]] * 15, ["примечание"] * 6, [])
    assert sh["scale"] == 1.0, sh["scale"]
    fx, _, s = sh["views"]["front"]
    assert VZ[0] <= fx - 95.0 * s / 2 and sh["views"]["side"][0] + 4.2 * s / 2 <= VZ[2], sh
    assert sh["views"]["iso"] is not None and sh["views"]["iso"][0] > TB_X, sh
    for b in sh["blocks"]:
        assert COL[0] - 1e-6 <= b["x"] - b["w"] / 2 and b["x"] + b["w"] / 2 <= COL[2] + 1e-6, b
        assert b["y"] - b["h"] / 2 >= COL[1] - 1e-6, b["name"]
    sw = layout(95.0, 4.2, [], [], ["предупреждение"] * 30)
    wb = [b for b in sw["blocks"] if b["name"] == "Warn"][0]
    assert wb["svg"].count("<text") == WARN_MAX + 1 and wb["x"] + wb["w"] / 2 <= TB_X, wb
    assert sw["views"]["front"][1] - 95.0 * sw["scale"] / 2 >= wb["y"] + wb["h"] / 2, sw
    assert layout(14.0, 1.0, [], [], [])["scale"] == 10.0
    t = template_svg()
    for k in FIELDS:
        assert f'freecad:editable="{k}"' in t, k
    f = title_fields("X.01A", {"label": "RING (.01A)", "name": "венец (жёсткое колесо)"}, sh, "16.10.26")
    assert set(f) == set(FIELDS) and f["scale"] == "1:1" and f["name1"].startswith("венец"), f
    return True
