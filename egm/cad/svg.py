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
PRIM = {"roller": 'stroke="blue" stroke-width="0.2" fill="none"',
        "bearing": 'stroke="green" stroke-width="0.25" fill="none"',
        "ecc": 'stroke="green" stroke-width="0.25" fill="none"',
        "bore": 'stroke="green" stroke-width="0.18" stroke-dasharray="1.5,1" fill="none"',
        "shaft": 'stroke="gray" stroke-width="0.18" stroke-dasharray="1.5,1" fill="none"',
        "sep": 'stroke="gray" stroke-width="0.15" stroke-dasharray="3,1" fill="none"'}


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
    if m.view == "unroll":                     # Д-47: сепаратор — развёртка втулки
        return render_unroll(m)
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
         f'<circle cx="{m.cx[0]:g}" cy="{-m.cx[1]:g}" r="{R:g}" {ST["part"]}/>',
         f'<path d="M{" L".join(_pt(*p) for p in m.cut.pts)} Z" {ST["part"]}/>']
    for wn in m.windows:
        if m.row and wn.row != m.row:
            continue
        c, s = math.cos(math.radians(wn.angle)), math.sin(math.radians(wn.angle))
        q = [(r * c - sg * wn.w / 2 * s, r * s + sg * wn.w / 2 * c)
             for r, sg in ((wn.r_in, 1), (wn.r_out, 1), (wn.r_out, -1), (wn.r_in, -1))]
        o.append(f'<path d="M{" L".join(_pt(*p) for p in q)} Z" {ST["part"]}/>')
    o += [f'<circle cx="0" cy="0" r="{c.r:g}" {ST[c.role]}/>' for c in m.axes]
    o += [f'<circle cx="{hl.x:.4f}" cy="{-hl.y:.4f}" r="{hl.d / 2:g}" {ST["part"]}/>'
          for hl in m.holes]
    o += [f'<circle cx="{p.x:.4f}" cy="{-p.y:.4f}" r="{p.d / 2:g}" '
          f'{PRIM.get(p.role, ST["thin"])}/>' for p in m.prims]
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
            '</marker></defs>\n'
            f'<rect x="{x0:g}" y="{y0:g}" width="{w:g}" height="{h:g}" fill="white"/>\n'
            + "\n".join(o) + "\n</svg>\n")


def _widths(m, fl):
    """Ширины колонок легенды по длине текста."""
    return (max([tw(s, fl) for s, _, _ in m.legend] + [0]) + 3,
            max([tw(_fmt(v), fl) for _, v, _ in m.legend] + [0]) + 3,
            max([tw(t, fl) for _, _, t in m.legend] + [0]))


def _legend(m, x0, ly, fl, c1, c2):
    o = [f'<text x="{x0 + 4:g}" y="{ly:g}" font-size="3.2">Легенда — обозначения '
         f'колонок SPEC-10_PTK_CALC.md</text>']
    for i, (sym, val, txt) in enumerate(m.legend):
        yy = ly + 4.5 * (i + 1)
        o += [f'<text x="{x0 + 4:g}" y="{yy:g}" font-size="{fl}">{esc(str(sym))}</text>',
              f'<text x="{x0 + 4 + c1:g}" y="{yy:g}" font-size="{fl}">{esc(_fmt(val))}</text>',
              f'<text x="{x0 + 4 + c1 + c2:g}" y="{yy:g}" font-size="{fl}">{esc(txt)}</text>']
    return o


def _wrap(x0, y0, w, h, o):
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}mm" height="{h:g}mm" '
            f'viewBox="{x0:g} {y0:g} {w:g} {h:g}">\n'
            '<defs><marker id="a" viewBox="0 0 6 6" refX="3" refY="3" markerWidth="4" '
            'markerHeight="4" orient="auto-start-reverse"><path d="M0,0 L6,3 L0,6 z"/>'
            '</marker></defs>\n'
            f'<rect x="{x0:g}" y="{y0:g}" width="{w:g}" height="{h:g}" fill="white"/>\n'
            + "\n".join(o) + "\n</svg>\n")


def render_unroll(m):
    """Развёртка втулки по среднему Ø (Д-47): x — дуга от 0°, y — ось от торца, 1:1.

    Окна всех рядов; ряд m.row — основной линией, прочие — тонкой. Диаметры, толщина,
    длины окружностей — в легенде (сноски), на виде не изображаются."""
    first = {}
    for wn in m.windows:
        first.setdefault(wn.row, wn)
    w0 = next(iter(first.values()))
    L, B = math.pi * (w0.r_in + w0.r_out), m.thick
    lab = [(wn, f"ряд {k}: z0 = {wn.z0:g}, поворот {wn.angle:g}°")
           for k, wn in sorted(first.items())]
    fl = 2.8
    c1, c2, c3 = _widths(m, fl)
    lw = max([tw(t, 2.5) for _, t in lab] + [0])
    top = max([tw(m.id, 4)] + [tw(t, 3) for t in m.notes])
    x0, y0 = -14, -5 * (len(m.notes) + 1) - 10
    w = max(L + 24 + lw, c1 + c2 + c3 + 8, top + 8)
    ly = B + 20
    h = ly + 4.5 * (len(m.legend) + 1) + 4 - y0
    o = [f'<rect x="0" y="0" width="{L:.3f}" height="{B:g}" {ST["part"]}/>']
    for wn in m.windows:
        st = ST["part"] if not m.row or wn.row == m.row else ST["thin"]
        xc = (wn.angle % 360) / 360 * L
        for c in (xc - L, xc, xc + L):                 # окно на шве 0° — две части
            xa, xb = max(0.0, c - wn.w / 2), min(L, c + wn.w / 2)
            if xb - xa > 1e-6:
                o.append(f'<rect x="{xa:.3f}" y="{wn.z0:.3f}" width="{xb - xa:.3f}" '
                         f'height="{wn.h:g}" {st}/>')
    for wn, t in lab:
        yc = wn.z0 + wn.h / 2
        o += [f'<line x1="{L:.3f}" y1="{yc:.3f}" x2="{L + 4:.3f}" y2="{yc:.3f}" {ST["mark"]}/>',
              f'<text x="{L + 5:.3f}" y="{yc + 0.9:.3f}" font-size="2.5" fill="red">{esc(t)}</text>']
    yd = B + 8
    o += [f'<line x1="0" y1="{B:g}" x2="0" y2="{yd + 1:g}" {ST["thin"]}/>',
          f'<line x1="{L:.3f}" y1="{B:g}" x2="{L:.3f}" y2="{yd + 1:g}" {ST["thin"]}/>',
          f'<line x1="0" y1="{yd:g}" x2="{L:.3f}" y2="{yd:g}" {ST["thin"]} '
          'marker-start="url(#a)" marker-end="url(#a)"/>',
          f'<text x="{L / 2:.3f}" y="{yd - 1:g}" font-size="3" text-anchor="middle">'
          f'π·Dm = {L:.2f}</text>',
          f'<line x1="0" y1="0" x2="-7" y2="0" {ST["thin"]}/>',
          f'<line x1="0" y1="{B:g}" x2="-7" y2="{B:g}" {ST["thin"]}/>',
          f'<line x1="-6" y1="0" x2="-6" y2="{B:g}" {ST["thin"]} '
          'marker-start="url(#a)" marker-end="url(#a)"/>',
          f'<text x="-7.5" y="{B / 2:g}" font-size="3" text-anchor="middle" '
          f'transform="rotate(-90 -7.5 {B / 2:g})">B = {B:g}</text>']
    ty = y0 + 6
    o.append(f'<text x="{x0 + 4:g}" y="{ty:g}" font-size="4">{esc(m.id)}</text>')
    o += [f'<text x="{x0 + 4:g}" y="{ty + 5 * (i + 1):g}" font-size="3">{esc(t)}</text>'
          for i, t in enumerate(m.notes)]
    return _wrap(x0, y0, w, h, o + _legend(m, x0, ly, fl, c1, c2))
