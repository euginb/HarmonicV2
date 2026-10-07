import ezdxf                        #
import matplotlib.pyplot as plt     # Перед запуском скрипта установите библиотеки (если они еще не установлены):
import sys                          # $ pip3 install ezdxf matplotlib numpy
import numpy as np                  #

""" Скрипт расчета и построения профиля волнового редуктора с промежуточными телами качения (ВПТК)
Автор: Артём TrashRobotics 
Канал: https://www.youtube.com/@trashrobotics
Бусти: https://boosty.to/trashrobotics
Git: https://codeberg.org/TrashRobotics

В общем, вводите основные данные (передаточое число, диаметр шариков, радиус профиля жесткого колеса) для редуктора, 
который вам нужен и скрипт автоматически посчитает все параметры и построит: 
1) профиль жесткого колеса (BASE_WHEEL_SHAPE)
2) сепаратор (SEPARATOR)
3) волнообрахователь/эксцентрик (ECCENTRIC)
4) шарики (BALLS)
5) внешний диаметр редуктора (OUT_DIAMETER)

После чего запишет все в файл с разрешением DXF, который можно будет открыть в любом CAD.
"""
OUT_FILE = "vptc6.dxf"  # Имя файла в который будет сохранен профиль
RESOLUTION = 600       # Количество точек построения профиля жесткого колеса
i = 17                 # Нужное вам передаточное число
dsh = 6                # Диаметр шариков от подшипника
Rout = 38              # Внешний радиус впадин жесткого колеса
D = 90                 # Внешний диаметр редуктора (опционально)
u = 1                  # Число волн, создаваемых волнообразователем (НЕ ТРОГАТЬ, т.к для более чем 1 не расчитывалось)

# Флаги, определяющие какие профили будут построены и перенесены в чертеж. Те, которые не нужны, можно отключить
BASE_WHEEL_SHAPE = True
SEPARATOR = True
ECCENTRIC = True
BALLS = False       # только для демонстрации (в чертеж НЕ переносить: запутаетесь. Шарики расположены друг от друга не на равном расстоянии)
OUT_DIAMETER = True
""" --------------------------------------------------------------------------------------- """
""" Все, что ниже вам уже не нужно, оно будет работать само. Или скажет: почему не работает """
""" --------------------------------------------------------------------------------------- """

e = 0.2 * dsh
zg = (i+1)*u
zsh = i
Rin = Rout - 2*e
rsh = dsh/2
rd = Rin + e - dsh
hc = 2.2*e
Rsep_m = rd + rsh
Rsep_out = Rsep_m + hc/2
Rsep_in = Rsep_m - hc/2

print("........................")
print("Основные параметры ВПТК:")
print("- Передаточное число: ", i)
print("- Эксцентриситет: ", e)
print("- Радиус эксцентрика: ", rd)
print("- Внешний радиус профиля жесткого колеса: ", Rout)
print("- Внутренний радиус профиля жесткого колеса: ", Rin)
print("- Число впадин профиля жесткого колеса: ", zg)
print("- Число шариков: ", zsh)
print("- Диаметр шариков: ", dsh)
print("- Делительный радиус сепаратора: ", Rsep_m)
print("- Толщина сепаратора: ", hc)
print("........................")
print("........................")

if Rin <= ((1.03 * dsh)/np.sin(np.pi/zg)):
    print("Так не пойдет -_-)")
    print("Внутренний радиус впадин жесткого колеса Rin({0}мм) должен быть больше: {1}мм. Увеличьте Rout или уменьшите "
          "передаточное число (i)!".format(Rin, (1.03 * dsh)/np.sin(np.pi/zg)))
    sys.exit(1)

#print(rd/rsh, 0.65*zg+2.8)

theta = np.linspace(0, 2*np.pi, RESOLUTION)

S = np.sqrt((rsh + rd) ** 2 - np.power(e * np.sin(zg * theta), 2))
l = e * np.cos(zg * theta) + S
Xi = np.arctan2(e*zg*np.sin(zg*theta), S)

x = l*np.sin(theta) + rsh * np.sin(theta + Xi)
y = l*np.cos(theta) + rsh * np.cos(theta + Xi)

xy = np.stack((x, y), axis=1)


sh_angle = np.linspace(0, 1, zsh+1) * 2*np.pi
S_sh = np.sqrt((rsh + rd) ** 2 - np.power(e * np.sin(zg * sh_angle), 2))
l_Sh = e * np.cos(zg * sh_angle) + S_sh
x_sh = l_Sh*np.sin(sh_angle)
y_sh = l_Sh*np.cos(sh_angle)


doc = ezdxf.new("R2000")
msp = doc.modelspace()

if BASE_WHEEL_SHAPE:
    msp.add_point([0, 0])
    msp.add_lwpolyline(xy)
    # msp.add_circle((0, 0), radius=Rout)
    # msp.add_circle((0, 0), radius=Rin)

if SEPARATOR:
    msp.add_circle((0, 0), radius=Rsep_out)
    msp.add_circle((0, 0), radius=Rsep_in)

if ECCENTRIC:
    msp.add_point([0, e])
    msp.add_lwpolyline([[0, 0], [0, e]])
    msp.add_lwpolyline([[-6, 0], [6, 0]])
    msp.add_lwpolyline([[-3, e], [3, e]])
    msp.add_circle((0, e), radius=rd)

if BALLS:
    for i in range(zsh):
        msp.add_circle((x_sh[i], y_sh[i]), radius=rsh)

if OUT_DIAMETER:
    msp.add_circle((0, 0), radius=D/2)

doc.saveas(OUT_FILE)

print("Профиль построен и записа в файл:", OUT_FILE)

# Дополнительная визуализация результата в matplotlib
if True:
    fig, ax = plt.subplots(figsize=(8, 8))

    ax.plot(x, y, linewidth=1.0)
    ax.plot([0, 0], (0, e), ".", linewidth=1.0)
    ax.plot([-6, 6], (0, 0), "--k", linewidth=1.0)
    ax.plot([-3, 3], (e, e), "--k", linewidth=1.0)
    D_circle = plt.Circle((0, 0), D / 2, color='b', fill=False, linewidth=1.0)
    rd_circle = plt.Circle((0, e), rd, color='b', fill=False, linewidth=1.0)
    Rsep_out_circle = plt.Circle((0, 0), Rsep_out, fill=False, linewidth=1.0)
    Rsep_in_circle = plt.Circle((0, 0), Rsep_in, fill=False, linewidth=1.0)
    ax.add_patch(D_circle)
    ax.add_patch(rd_circle)
    ax.add_patch(Rsep_out_circle)
    ax.add_patch(Rsep_in_circle)

    for i in range(zsh):
        sh_circle = plt.Circle((x_sh[i], y_sh[i]), rsh, color='r', fill=False, linewidth=1.0)
        ax.add_patch(sh_circle)

    # test = plt.Circle((0, 0), Rin, color='g', fill=False, linewidth=1.0)
    # ax.add_patch(test)
    # test2 = plt.Circle((0, 0), Rout, color='g', fill=False, linewidth=1.0)
    # ax.add_patch(test2)
    plt.show()

