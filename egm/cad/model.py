"""Модель детали для чертежей (Д-32): геометрия без формата вывода.

Генератор детали строит PartModel; рендеры: egm/cad/svg.py (2D), egm/cad/step.py (3D).
Одна модель — одинаковые 2D и 3D.
"""
from dataclasses import dataclass, field


@dataclass
class Contour:
    pts: list                  # замкнутая ломаная [(x, y)], против часовой стрелки


@dataclass
class Circle:
    r: float
    role: str = "axis"         # axis — штрихпунктир


@dataclass
class Hole:
    x: float
    y: float
    d: float
    kind: str = "bolt"         # bolt | pin


@dataclass
class Disk:
    x: float
    y: float
    d: float
    role: str = "roller"       # сборочный примитив (Д-44): roller | bearing | bore | ecc | shaft | sep


@dataclass
class Window:
    angle: float               # ось радиального окна, град (Д-46)
    r_in: float
    r_out: float
    w: float                   # ширина поперёк радиуса, мм
    z0: float                  # начало по оси, мм
    h: float                   # высота по оси, мм
    row: int = 1


@dataclass
class PinHole:
    angle: float               # ось радиального отверстия, град (CP-63, Д-76)
    z: float                   # центр по оси, мм (локальная система детали)
    d: float
    r0: float                  # отверстие от радиуса r0 …
    r1: float                  # … до r1, мм (сквозное — за обе стенки, глухое — гнездо)


@dataclass
class AxialHole:
    angle: float               # угол центра отверстия, град (CP-79, Д-93)
    r: float                   # радиус окружности центров, мм
    d: float
    z0: float                  # начало по оси, мм (локальная система детали)
    h: float                   # длина отверстия, мм (сквозное — с выходом за торцы)


@dataclass
class Band:
    r_in: float                # кольцо r_in…r_out вокруг оси (0, 0); r_in = 0 — сплошной цилиндр
    r_out: float
    z0: float                  # начало по оси, мм (локальная система детали)
    h: float
    op: str = "add"            # add — приварить к телу, cut — вырезать (CP-45)


@dataclass
class Dim:
    d: float                   # размер диаметра
    label: str                 # обозначение колонки SPEC-10


@dataclass
class Mark:
    angle: float               # радиальная метка, град
    r0: float
    r1: float
    text: str


@dataclass
class PartModel:
    id: str
    thick: float
    d_out: float
    cut: Contour
    holes: list = field(default_factory=list)
    axes: list = field(default_factory=list)
    dims: list = field(default_factory=list)
    marks: list = field(default_factory=list)
    notes: list = field(default_factory=list)
    legend: list = field(default_factory=list)   # [(обозначение SPEC-10, значение, смысл)]
    prims: list = field(default_factory=list)    # сборочные примитивы Disk (Д-44): SVG, не STEP
    cx: tuple = (0.0, 0.0)                       # центр наружной окружности (эксцентрик, Д-46)
    cut_mode: str = ""                           # "" — как --step; poly — контур с углами (паз)
    windows: list = field(default_factory=list)  # окна Window (сепаратор)
    row: int = 0                                 # ряд вида SVG: окна только этого ряда
    view: str = ""                               # "" — вид по оси; unroll — развёртка втулки (Д-47)
    bands: list = field(default_factory=list)    # ступени вращения Band: дно, ступица, гнёзда (CP-45)
    pins: list = field(default_factory=list)     # радиальные отверстия PinHole: штифты .02–.12 (CP-63)
    axial: list = field(default_factory=list)    # осевые отверстия AxialHole: штифты collar (CP-79)
