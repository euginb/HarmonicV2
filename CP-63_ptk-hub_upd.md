# --- Journal: 'specs/CODE_PLAN.md': ## 2. Пункты плана
| CP-63 | rev 10.4: CAD .12 (ptk_hub): .12A поясок (L2), .12B дно-вставка с буртом (L3); бурт .02B (Band add), стенка .02C под вставку; PinHole — радиальные штифты по осям окон последнего ряда; осевая длина с поясом (belt = L, insert L + cup_t — бурт .12B); .12 в сборке и TechDraw (n_pins, d_pin, pin_z); weld .02C — каркас (JOIN.weld), подбор листа в choose — CP-67 | egm/cad/ptk_hub.py, egm/cad/model.py, egm/cad/step.py, egm/cad/techdraw.py, egm/cad/ptk_sep.py, egm/cad/assy.py, egm/cad/__main__.py, egm/ptk_layout.py, egm/ptk_join.py, tools/freecad_techdraw.py, specs/products.yaml, main.py, README.md | Д-72, Д-73, Д-76 | CP-64 | открыт |

# --- Journal: 'specs/CODE_PLAN.md': ## 2. Пункты плана
| CP-67 | ptk_join.choose: подбор листа из stock.yaml по JOIN.weld для insert (.02C из листа — включение маршрута weld); штифты на развёртке SVG | egm/ptk_join.py, egm/cad/ptk_sep.py, egm/cad/svg.py | Д-76 | CP-63 | открыт |

# --- Journal: 'specs/DECISIONS.md': ## Принятые решения
| Д-76 | Соединение .02–.12 в CAD (CP-63): штифты радиально на z = z_in + L/2, углы — оси окон последнего ряда (cage + j·360/n); дно/пояс по оси max(cup_t, belt), belt = L (collar) или L + cup_t (insert, бурт .12B = cup_t); стенка под гнездом ≥ pin_wall = 1 мм; шов weld — на перемычке ряда 1 (cage₁ + 180/n), мимо штифтов; z-положение штифтов вне окон проверяется по 3D (Д-65); JOIN.weld — марки листа (по умолчанию пусто) | rev 10.4 |

# --- Journal: 'specs/DECISIONS.md': ## Открытые вопросы
| OQ-20   | TechDraw (Д-65): проверить по версии FreeCAD — нумерацию EdgeN из getVisibleEdges и масштаб её координат, масштаб/систему координат makeCosmeticCircle, точку привязки X/Y таблицы и аннотаций, TextColor аннотации, имена шаблонов A3 и полей основной надписи, TechDrawGui.exportPageAsPdf, что Part.getShape(transform=False) по метке даёт форму в системе детали (проверка «центр D»); допуск сверки профиля Dверш в режиме spline; размеры на косметических окружностях; головной режим FreeCADCmd (CP-56); радиальные отверстия (оси ⟂ z) — _radial в freecad_techdraw.py, слияние половин цилиндра по углу — проверить на версии FreeCAD (CP-63) | открыт |

