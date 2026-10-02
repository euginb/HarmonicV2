"""3D-рендер PartModel в STEP через CadQuery (Д-32); cadquery — опционально."""


def export(m, path):
    import cadquery as cq
    body = cq.Workplane("XY").circle(m.d_out / 2).extrude(m.thick)
    body = body.cut(cq.Workplane("XY").polyline(m.cut.pts).close().extrude(m.thick))
    for h in m.holes:
        body = body.cut(cq.Workplane("XY").center(h.x, h.y).circle(h.d / 2).extrude(m.thick))
    cq.exporters.export(body, str(path))
