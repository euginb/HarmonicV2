"""2D-рендер PartModel в SVG (Д-32). Ед. — мм, вид по оси, y вверх, масштаб 1:1.

Ширина колонок легенды и листа — по длине текста (CW·кегль на символ, с запасом
для кириллицы). Подписи меток — на полках за Øнар, раздвинуты по высоте.
"""
import math
from xml.sax.saxutils import escape as esc

CW = 0.62
ST = {"part": 'stroke="black" stroke-width="0.35" fill="none"',
      "axis": 'stroke="black" stroke-width="0.18" stroke-dasharray="6,1.5,1,1.5" fill="none"',
      "thin": 'stroke="black" stroke-width="0.18" fill="none"',
      "mark": 'stroke="red" stroke-width="0.25" fill="none"'}


def _pt(x, y):
    return f"{x:.4f},{-y:.4f}"


def tw(s, fs):
    return CW * fs * len(str(s))


def _fmt(v):
    return f"{v:g}" if isinstance(v, (int, float)) and not isinstance(v, bool) else str(v)


def _labels(m, R):
    """[(метка, x1, y1, x полки, y полки, сторона)]: сверху вниз, шаг по y ≥ 4 мм."""
    out = []
    for side in (1, -1):
        mk = [k for k in m.marks if (math.cos(math.radians(k.angle)) >= -1e-9) == (side > 0)]
        mk.sort(key=lambda k: -k.r1 * math.sin(math.radians(k.angle)))
        y_prev = math.inf
        for k in mk:
            a = math.radians(k.angle)
            x1, y1 = k.r1 * math.cos(a), k.r1 * math.sin(a)
            y = min(y1, y_prev - 4)
            y_prev = y
            out.append((k, x1, y1, side * (R + 4), y, side))
    return out


def render(m):
    R = m.d_out / 2
    lab = _labels(m, R)
    lw = max([tw(k.text, 2.5) for k, *_ in lab] + [0])
    fl = 2.8
    c1 = max([tw(s, fl) for s, _, _ in m.legend] + [0]) + 3
    c2 = max([tw(_fmt(v), fl) for _, v, _ in m.legend] + [0]) + 3
    c3 = max([tw(t, fl) for _, _, t in m.legend] + [0])
    top = max([tw(m.id, 4)] + [tw(t, 3) for t in m.notes])
    w = max(2 * (R + 8 + lw), c1 + c2 + c3, top) + 8
    x0 = -w / 2
    y0 = -(R + 10) - 5 * (len(m.notes) + 1) - 4
    h_dims = R + 10 + 7 * len(m.dims)
    ly = h_dims + 8
    h = ly + 4.5 * (len(m.legend) + 1) + 4 - y0
    o = [f'<line x1="{-R - 4:g}" y1="0" x2="{R + 4:g}" y2="0" {ST["axis"]}/>',
         f'<line x1="0" y1="{-R - 4:g}" x2="0" y2="{R + 4:g}" {ST["axis"]}/>',
         f'<circle cx="0" cy="0" r="{R:g}" {ST["part"]}/>',
         f'<path d="M{" L".join(_pt(*p) for p in m.cut.pts)} Z" {ST["part"]}/>']
    o += [f'<circle cx="0" cy="0" r="{c.r:g}" {ST[c.role]}/>' for c in m.axes]
    o += [f'<circle cx="{hl.x:.4f}" cy="{-hl.y:.4f}" r="{hl.d / 2:g}" {ST["part"]}/>'
          for hl in m.holes]
    for k, x1, y1, xs, ys, side in lab:
        a = math.radians(k.angle)
        p0 = _pt(k.r0 * math.cos(a), k.r0 * math.sin(a))
        o += [f'<polyline points="{p0} {_pt(x1, y1)} {_pt(xs, ys)}" {ST["mark"]}/>',
              f'<text x="{xs + side * 1:.3f}" y="{-ys + 0.9:.3f}" font-size="2.5" fill="red" '
              f'text-anchor="{"start" if side > 0 else "end"}">{esc(k.text)}</text>']
    for i, dm in enumerate(m.dims):
        y, hh = R + 8 + 7 * i, dm.d / 2
        o += [f'<line x1="{-hh:g}" y1="0" x2="{-hh:g}" y2="{y + 1:g}" {ST["thin"]}/>',
              f'<line x1="{hh:g}" y1="0" x2="{hh:g}" y2="{y + 1:g}" {ST["thin"]}/>',
              f'<line x1="{-hh:g}" y1="{y:g}" x2="{hh:g}" y2="{y:g}" {ST["thin"]} '
              'marker-start="url(#a)" marker-end="url(#a)"/>',
              f'<text x="0" y="{y - 1:g}" font-size="3" text-anchor="middle">'
              f'{esc(dm.label)} = {dm.d:g}</text>']
    ty = y0 + 6
    o.append(f'<text x="{x0 + 4:g}" y="{ty:g}" font-size="4">{esc(m.id)}</text>')
    for i, t in enumerate(m.notes):
        o.append(f'<text x="{x0 + 4:g}" y="{ty + 5 * (i + 1):g}" font-size="3">{esc(t)}</text>')
    o.append(f'<text x="{x0 + 4:g}" y="{ly:g}" font-size="3.2">Легенда — обозначения '
             f'колонок SPEC-10_PTK_CALC.md</text>')
    for i, (sym, val, txt) in enumerate(m.legend):
        yy = ly + 4.5 * (i + 1)
        o += [f'<text x="{x0 + 4:g}" y="{yy:g}" font-size="{fl}">{esc(str(sym))}</text>',
              f'<text x="{x0 + 4 + c1:g}" y="{yy:g}" font-size="{fl}">{esc(_fmt(val))}</text>',
              f'<text x="{x0 + 4 + c1 + c2:g}" y="{yy:g}" font-size="{fl}">{esc(txt)}</text>']
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}mm" height="{h:g}mm" '
            f'viewBox="{x0:g} {y0:g} {w:g} {h:g}">\n'
            '<defs><marker id="a" viewBox="0 0 6 6" refX="3" refY="3" markerWidth="4" '
            'markerHeight="4" orient="auto-start-reverse"><path d="M0,0 L6,3 L0,6 z"/>'
            '</marker></defs>\n' + "\n".join(o) + "\n</svg>\n")
