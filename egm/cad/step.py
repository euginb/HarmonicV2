"""3D-рендер PartModel в STEP через CadQuery (Д-32, CP-29); cadquery — опционально.

Деталь строится одной гранью и одним выдавливанием, без булевых операций:
наружная окружность D + контур впадин + окружности отверстий. Прежний вариант
(цилиндр − выдавленная ломаная из z·k граней − каждое отверстие) на u = 63 давал
9+ булевых операций по ~1500 граням, и построение «зависало».
Контур впадин: mode="spline" — периодический B-сплайн через точки профиля (одна
гладкая боковая грань), mode="poly" — ломаная (z·k плоских граней).
"""
import math
import time

MODES = ("spline", "poly")


def _inner(cq, pts, mode):
    if mode == "spline":
        return cq.Wire.assembleEdges([cq.Edge.makeSpline(pts, periodic=True)])
    if mode == "poly":
        try:
            return cq.Wire.makePolygon(pts, close=True)
        except TypeError:              # CadQuery < 2.2: без аргумента close
            return cq.Wire.makePolygon(pts + [pts[0]])
    raise ValueError(f"step: режим {mode!r} не из {MODES}")


def solid(m, mode="spline"):
    """PartModel -> cq.Solid: грань (D, впадины, отверстия) × толщина."""
    import cadquery as cq
    V, nz = cq.Vector, cq.Vector(0, 0, 1)
    outer = cq.Wire.makeCircle(m.d_out / 2, V(m.cx[0], m.cx[1], 0), nz)
    inner = [_inner(cq, [V(x, y, 0) for x, y in m.cut.pts], m.cut_mode or mode)]
    inner += [cq.Wire.makeCircle(h.d / 2, V(h.x, h.y, 0), nz) for h in m.holes]
    body = cq.Solid.extrudeLinear(outer, inner, V(0, 0, m.thick))
    for b in m.bands:                  # CP-45: ступени вращения (дно и ступица стакана, гнёзда)
        ring = cq.Solid.makeCylinder(b.r_out, b.h, V(0, 0, b.z0), nz)
        if b.r_in > 0:
            ring = ring.cut(cq.Solid.makeCylinder(b.r_in, b.h, V(0, 0, b.z0), nz))
        body = body.fuse(ring).clean() if b.op == "add" else body.cut(ring)
        if hasattr(body, "Solids") and len(body.Solids()) == 1:
            body = body.Solids()[0]
    if m.windows:                      # Д-46: все окна сепаратора — одна булева операция
        tools = [cq.Solid.makeBox(wn.r_out - wn.r_in + 2, wn.w, wn.h,
                                  V(wn.r_in - 1, -wn.w / 2, wn.z0))
                 .rotate(V(0, 0, 0), V(0, 0, 1), wn.angle) for wn in m.windows]
        body = body.cut(*tools)
        if hasattr(body, "Solids") and len(body.Solids()) == 1:
            body = body.Solids()[0]
    if m.pins:                         # CP-63: радиальные отверстия штифтов — одна булева операция
        tools = [cq.Solid.makeCylinder(p.d / 2, p.r1 - p.r0, V(p.r0, 0, p.z), V(1, 0, 0))
                 .rotate(V(0, 0, 0), V(0, 0, 1), p.angle) for p in m.pins]
        body = body.cut(*tools)
        if hasattr(body, "Solids") and len(body.Solids()) == 1:
            body = body.Solids()[0]
    if getattr(m, "axial", None):      # CP-79: осевые сквозные отверстия штифтов — одна булева операция
        tools = [cq.Solid.makeCylinder(h.d / 2, h.h, V(h.r * math.cos(math.radians(h.angle)),
                                                        h.r * math.sin(math.radians(h.angle)), h.z0), nz)
                 for h in m.axial]
        body = body.cut(*tools)
        if hasattr(body, "Solids") and len(body.Solids()) == 1:
            body = body.Solids()[0]
    if not body.isValid():
        raise ValueError(f"{m.id}: тело STEP невалидно (режим {mode}); попробуйте --step poly")
    return body


def export(m, path, mode="spline"):
    """Пишет STEP; возвращает время построения, с."""
    import cadquery as cq
    t0 = time.perf_counter()
    body = solid(m, mode)
    cq.exporters.export(cq.Workplane("XY").add(body), str(path))
    return time.perf_counter() - t0


def self_test():
    """Без cadquery — пропуск. С cadquery: кольцо с отверстием строится в обоих режимах,
    объём = π·(R² − r² − r_отв²)·B с точностью 1 %."""
    try:
        import cadquery  # noqa: F401
    except Exception:
        return True
    from egm.cad.model import Contour, Hole, PartModel
    n, r = 6 * 24, 10.0
    pts = [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n))
           for i in range(n)]
    m = PartModel("T", 3.0, 30.0, Contour(pts), holes=[Hole(12.5, 0.0, 2.0)])
    ref = math.pi * (15.0 ** 2 - r ** 2 - 1.0) * 3.0
    for mode in MODES:
        try:
            v = solid(m, mode).Volume()
        except Exception as e:
            raise AssertionError(f"step {mode}: {type(e).__name__}: {e}")
        assert abs(v - ref) < 0.01 * ref, (mode, v, ref)
    from egm.cad.model import Band
    m2 = PartModel("T2", 3.0, 30.0, Contour(pts),
                   bands=[Band(5.0, 15.0, 3.0, 2.0), Band(0.0, 7.0, -1.0, 10.0, "cut")])
    ref2 = math.pi * (375.0 + 400.0 - 48.0)
    v2 = solid(m2, "spline").Volume()
    assert abs(v2 - ref2) < 0.01 * ref2, ("ступени Band (CP-45)", v2, ref2)
    from egm.cad.model import PinHole
    m3 = PartModel("T3", 10.0, 30.0, Contour(pts),
                   pins=[PinHole(a, 5.0, 2.0, 9.0, 16.0) for a in (0.0, 90.0, 180.0, 270.0)])
    ref3 = math.pi * (225.0 - 100.0) * 10.0 - 4 * math.pi * 1.0 * 5.0
    v3 = solid(m3, "spline").Volume()
    assert abs(v3 - ref3) < 0.005 * ref3, ("радиальные отверстия PinHole (CP-63)", v3, ref3)
    return True
