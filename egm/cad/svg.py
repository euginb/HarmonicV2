"""Минимальный SVG-чертёж с размерами (CP-06), без внешних зависимостей. Ед. — мм."""
from xml.sax.saxutils import escape

STYLE = {"part": 'stroke="black" stroke-width="0.35" fill="none"',
         "axis": 'stroke="black" stroke-width="0.18" stroke-dasharray="6,1.5,1,1.5" fill="none"',
         "dim": 'stroke="black" stroke-width="0.18" fill="none"'}


class Drawing:
    def __init__(self, size, title=""):
        self.r = size / 2
        self.m = 0.35 * size + 20                             # поле под размеры
        self.items, self.title, self.notes = [], title, []

    def circle(self, x, y, r, kind):
        self.items.append(f'<circle cx="{x:g}" cy="{-y:g}" r="{r:g}" {STYLE[kind]}/>')

    def path(self, segs, kind):
        """Замкнутый контур из сегментов 'arc' (p0, p1, r, large) и 'line' (p0, p1).

        Обход против часовой стрелки на виде; ось y SVG направлена вниз и
        переворачивается, поэтому sweep-flag = 0 (Д-30)."""
        pt = lambda p: f"{p[0]:.4f},{-p[1]:.4f}"
        cmd = [f"M{pt(segs[0]['p0'])}"]
        for s in segs:
            if s["kind"] == "arc":
                cmd.append(f"A{s['r']:.4f},{s['r']:.4f} 0 {int(s['large'])} 0 {pt(s['p1'])}")
            else:
                cmd.append(f"L{pt(s['p1'])}")
        self.items.append(f'<path d="{" ".join(cmd)} Z" {STYLE[kind]}/>')

    def dia(self, d, level, fmt):
        """Горизонтальный размер диаметра под видом, уровень level."""
        y = self.r + 8 + 7 * level
        h = d / 2
        self.items += [
            f'<line x1="{-h:g}" y1="0" x2="{-h:g}" y2="{y + 1:g}" {STYLE["dim"]}/>',
            f'<line x1="{h:g}" y1="0" x2="{h:g}" y2="{y + 1:g}" {STYLE["dim"]}/>',
            f'<line x1="{-h:g}" y1="{y:g}" x2="{h:g}" y2="{y:g}" {STYLE["dim"]} '
            'marker-start="url(#a)" marker-end="url(#a)"/>',
            f'<text x="0" y="{y - 1:g}" font-size="3" text-anchor="middle">'
            f'{escape(fmt.format(round(d, 2)))}</text>']

    def note(self, lines):
        self.notes += lines

    def render(self):
        w = 2 * (self.r + self.m)
        x0, y0 = -self.r - self.m, -self.r - self.m
        y_note = -self.r - self.m + 6
        txt = [f'<text x="{x0 + 4:g}" y="{y_note:g}" font-size="4">{escape(self.title)}</text>']
        txt += [f'<text x="{x0 + 4:g}" y="{y_note + 5 * (i + 1):g}" font-size="3">'
                f'{escape(t)}</text>' for i, t in enumerate(self.notes)]
        axes = [f'<line x1="{-self.r - 4:g}" y1="0" x2="{self.r + 4:g}" y2="0" {STYLE["axis"]}/>',
                f'<line x1="0" y1="{-self.r - 4:g}" x2="0" y2="{self.r + 4:g}" {STYLE["axis"]}/>']
        return ('<?xml version="1.0" encoding="UTF-8"?>\n'
                f'<svg xmlns="http://www.w3.org/2000/svg" width="{w:g}mm" height="{w:g}mm" '
                f'viewBox="{x0:g} {y0:g} {w:g} {w:g}">\n'
                '<defs><marker id="a" viewBox="0 0 6 6" refX="3" refY="3" markerWidth="4" '
                'markerHeight="4" orient="auto-start-reverse"><path d="M0,0 L6,3 L0,6 z"/>'
                '</marker></defs>\n'
                + "\n".join(axes + self.items + txt) + "\n</svg>\n")
