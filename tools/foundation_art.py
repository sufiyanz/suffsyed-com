"""Original, static line studies. Geometry is decorative, never measured data."""
import math
import random

from PIL import Image


def write_grain(directory):
    directory.mkdir(parents=True, exist_ok=True)
    rng = random.Random(1741)
    image = Image.new("RGBA", (160, 160))
    image.putdata([(20, 35, 22, rng.randrange(0, 16)) for _ in range(160 * 160)])
    image.save(directory / "grain.png")


def path(points, css_class=""):
    coordinates = " ".join(f"{x:.2f},{y:.2f}" for x, y in points)
    return f'<polyline class="{css_class}" points="{coordinates}"/>'


def ribbon():
    def point(u, v):
        radius = 242 + 78 * v * math.cos(u / 2)
        x, y, z = radius * math.cos(u), radius * math.sin(u), 120 * v * math.sin(u / 2)
        return 460 + 1.15 * x - .55 * y, 395 + .42 * x + 1.22 * y + z

    curves = [path([point(step * math.tau / 160, v / 8) for step in range(161)])
              for v in range(-8, 9)]
    curves += [path([point(u * math.tau / 40, v / 8) for v in range(-8, 9)], "cross-line")
               for u in range(40)]
    nodes = "".join(f'<circle class="art-node" cx="{x:.2f}" cy="{y:.2f}" r="4"/>'
                    for x, y in (point(.55, -1), point(2.1, 1), point(4.4, -.6)))
    return f'''<svg class="hero-geometry line-study" viewBox="0 0 960 840" aria-hidden="true" focusable="false">
<g>{"".join(curves)}</g>
<path class="construction" d="M40 430H880M460 0V810"/>
{nodes}</svg>'''


def writing_study(index):
    if index == 0:
        drawing = '''<ellipse cx="170" cy="165" rx="148" ry="65" transform="rotate(-34 170 165)"/>
<ellipse cx="214" cy="165" rx="148" ry="65" transform="rotate(34 214 165)"/>
<path class="construction" d="M192 0v320M0 165h440"/>
<circle class="art-node" cx="192" cy="165" r="4"/>'''
    elif index == 1:
        curves = []
        for i in range(12):
            curves.append(path([(50 + i * 29 + 58 * math.sin(t / 110),
                                 t + 40 * math.sin(i / 3)) for t in range(-100, 430, 8)]))
        for t in range(-40, 390, 30):
            curves.append(path([(50 + i * 29 + 58 * math.sin(t / 110),
                                 t + 40 * math.sin(i / 3)) for i in range(12)]))
        drawing = "".join(curves)
    else:
        drawing = '''<path d="M45 300C45 80 410 300 410-80M70 330C70 50 390 280 390-80M95 360C95 20 370 260 370-80"/>
<path class="construction" d="M0 145h440M265 0v360"/>
<circle class="art-node" cx="265" cy="145" r="4"/>'''
    return f'''<svg class="writing-geometry line-study" viewBox="0 0 440 360" aria-hidden="true" focusable="false">{drawing}</svg>'''


def orbit():
    curves = "".join(f'<ellipse cx="520" cy="490" rx="{radius}" ry="{radius * .53:.2f}" transform="rotate({angle} 520 490)"/>'
                     for radius, angle in ((340, -26), (380, -12), (420, 2), (460, 16), (500, 30)))
    return f'''<svg class="photo-geometry line-study" viewBox="0 0 1040 1000" aria-hidden="true" focusable="false">
{curves}<path class="construction" d="M0 490h1040M520 0v1000"/>
<circle class="art-node" cx="520" cy="490" r="5"/></svg>'''
