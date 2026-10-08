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
