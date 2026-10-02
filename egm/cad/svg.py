"""2D-рендер PartModel в SVG (Д-32). Ед. — мм, вид по оси, y вверх, масштаб 1:1."""
import math
from xml.sax.saxutils import escape as esc

ST = {"part": 'stroke="black" stroke-width="0.35" fill="none"',
      "axis": 'stroke="black" stroke-width="0.18" stroke-dasharray="6,1.5,1,1.5" fill="none"',
      "thin": 'stroke="black" stroke-width="0.18" fill="none"',
      "mark": 'stroke="red" stroke-width="0.25" fill="none"'}


def _pt(x, y):
    return f"{x:.4f},{-y:.4f}"


def render(m):
    R = m.d_out / 2
    M = 0.35 * m.d_out + 20
    x0, y0 = -R - M, -R - M
    w = 2 * (R + M)
    h_dims = R + 10 + 7 * len(m.dims)
    h = (h_dims - y0) + 8 + 4.5 * (len(m.legend) + 2)
    o = [f'<line x1="{-R - 4:g}" y1="0" x2="{R + 4:g}" y2="0" {ST["axis"]}/>',
         f'<line x1="0" y1="{-R - 4:g}" x2="0" y2="{R + 4:g}" {ST["axis"]}/>',
         f'<circle cx="0" cy="0" r="{R:g}" {ST["part"]}/>',
         f'<path d="M{" L".join(_pt(*p) for p in m.cut.pts)} Z" {ST["part"]}/>']
    o += [f'<circle cx="0" cy="0" r="{c.r:g}" {ST[c.role]}/>' for c in m.axes]
    o += [f'<circle cx="{hl.x:.4f}" cy="{-hl.y:.4f}" r="{hl.d / 2:g}" {ST["part"]}/>'
          for hl in m.holes]
    for mk in m.marks:
        a = math.radians(mk.angle)
        c, s = math.cos(a), math.sin(a)
        o += [f'<line x1="{_pt(mk.r0 * c, mk.r0 * s).replace(",", chr(34) + " y1=" + chr(34))}" '
              f'x2="{_pt(mk.r1 * c, mk.r1 * s).replace(",", chr(34) + " y2=" + chr(34))}" {ST["mark"]}/>',
              f'<text x="{(mk.r1 + 1.5) * c:.3f}" y="{-(mk.r1 + 1.5) * s:.3f}" font-size="2.5" '
              f'fill="red">{esc(mk.text)}</text>']
    for i, dm in enumerate(m.dims):
        y, hh = R + 8 + 7 * i, dm.d / 2
        o += [f'<line x1="{-hh:g}" y1="0" x2="{-hh:g}" y2="{y + 1:g}" {ST["thin"]}/>',
              f'<line x1="{hh:g}" y1="0" x2="{hh:g}" y2="{y + 1:g}" {ST["thin"]}/>',
              f'<line x1="{-hh:g}" y1="{y:g}" x2="{hh:g}" y2="{y:g}" {ST["thin"]} '
              'marker-start="url(#a)" marker-end="url(#a)"/>',
              f'<text x="0" y="{y - 1:g}" font-size="3" text-anchor="middle">'
              f'{esc(dm.label)} = {dm.d:.2f}</text>']
    ty = y0 + 6
    o.append(f'<text x="{x0 + 4:g}" y="{ty:g}" font-size="4">{esc(m.id)}</text>')
    for i, t in enumerate(m.notes):
        o.append(f'<text x="{x0 + 4:g}" y="{ty + 5 * (i + 1):g}" font-size="3">{esc(t)}</text>')
    ly = h_dims + 8
    o.append(f'<text x="{x0 + 4:g}" y="{ly:g}" font-size="3.2">Легенда — обозначения '
             f'колонок SPEC-10_PTK_CALC.md</text>')
    for i, (sym, val, txt) in enumerate(m.legend):
        yy = ly + 4.5 * (i + 1)
        v = f"{val:g}" if isinstance(val, (int, float)) else str(val)
        o += [f'<text x="{x0 + 4:g}" y="{yy:g}" font-size="2.8">{esc(sym)}</text>',
              f'<text x="{x0 + 26:g}" y="{yy:g}" font-size="2.8">{esc(v)}</text>',
              f'<text x="{x0 + 50:g}" y="{yy:g}" font-size="2.8">{esc(txt)}</text>']
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}mm" height="{h:g}mm" '
            f'viewBox="{x0:g} {y0:g} {w:g} {h:g}">\n'
            '<defs><marker id="a" viewBox="0 0 6 6" refX="3" refY="3" markerWidth="4" '
            'markerHeight="4" orient="auto-start-reverse"><path d="M0,0 L6,3 L0,6 z"/>'
            '</marker></defs>\n' + "\n".join(o) + "\n</svg>\n")
