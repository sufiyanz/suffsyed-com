"""Original line studies, complete without motion. Never measured data."""
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


def ribbon(id_prefix):
    def point(u, v):
        radius = 242 + 78 * v * math.cos(u / 2)
        x, y, z = radius * math.cos(u), radius * math.sin(u), 120 * v * math.sin(u / 2)
        return 460 + 1.15 * x - .55 * y, 395 + .42 * x + 1.22 * y + z

    # A half-twist joins lane +v to -v. Pair the displayed halves, never close
    # one half with an invented chord. Rotate vertices to set each static start.
    starts = {8: (174, 48), 6: (53, 60), 5: (272, 72)}
    curves, nodes = [], []
    for lane in range(9):
        points = [point(step * math.tau / 160, lane / 8) for step in range(160)]
        if lane:
            points += [point(step * math.tau / 160, -lane / 8) for step in range(160)]
        if lane in starts:
            start, duration = starts[lane]
            points = points[start:] + points[:start]
        route_id = f"{id_prefix}-lane-{lane}"
        vertices = " L".join(f"{x:.2f},{y:.2f}" for x, y in points)
        curves.append(f'<path id="{route_id}" data-motion-route="closed" d="M{vertices} Z"/>')
        if lane in starts:
            x, y = points[0]
            origin = f"{x:.2f} {y:.2f}"
            nodes.append(f'''<g data-motion-follower="{route_id}" data-motion-start="{origin}" transform="translate({origin})">
<circle class="art-node" cx="0" cy="0" r="4"/>
<animateMotion begin="indefinite" dur="{duration}s" repeatCount="indefinite" calcMode="paced"><mpath href="#{route_id}"/></animateMotion>
</g>''')
    curves += [path([point(u * math.tau / 40, v / 8) for v in range(-8, 9)], "cross-line")
               for u in range(40)]
    return f'''<svg class="hero-geometry line-study" viewBox="0 0 960 840" aria-hidden="true" focusable="false">
<g data-motion-track="depth">{"".join(curves)}{"".join(nodes)}</g>
<path class="construction" d="M40 430H880M460 0V810"/>
</svg>'''


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


def orbit(id_prefix):
    curves = "".join(f'<ellipse cx="520" cy="490" rx="{radius}" ry="{radius * .53:.2f}" transform="rotate({angle} 520 490)"/>'
                     for radius, angle in ((340, -26), (380, -12), (420, 2), (460, 16), (500, 30)))
    return f'''<svg class="photo-geometry line-study" viewBox="0 0 1040 1000" aria-hidden="true" focusable="false">
<g data-motion-track="depth">{curves}<path id="{id_prefix}-origin" class="construction" d="M0 490h1040M520 0v1000"/>
<circle class="art-node" data-motion-anchor="{id_prefix}-origin" data-anchor-point="520 490" cx="520" cy="490" r="5"/>
</g></svg>'''
