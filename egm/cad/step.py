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
    outer = cq.Wire.makeCircle(m.d_out / 2, V(0, 0, 0), nz)
    inner = [_inner(cq, [V(x, y, 0) for x, y in m.cut.pts], mode)]
    inner += [cq.Wire.makeCircle(h.d / 2, V(h.x, h.y, 0), nz) for h in m.holes]
    body = cq.Solid.extrudeLinear(outer, inner, V(0, 0, m.thick))
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
    return True
