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
