from PIL import Image, ImageDraw, ImageFont
from vex2_display_astromech_approved import show
import math
import time

WIDTH, HEIGHT = 480, 320
DURATION = 24

RED = "#FF0000"
AMBER = "#FFAA20"
CYAN = "#45C7D8"

FONT = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    22
)

SMALL = ImageFont.truetype(
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    14
)


def point(cx, cy, radius, angle):
    return (
        round(cx + radius * math.cos(angle)),
        round(cy + radius * math.sin(angle))
    )


def draw_iris(draw, cx, cy, radius, openness, color):
    """
    Simulate a six-blade mechanical camera iris.
    openness: 1.0 = open, 0.0 = fully closed.
    """

    # Outer mechanical mounting ring
    draw.ellipse(
        (cx-radius-7, cy-radius-7,
         cx+radius+7, cy+radius+7),
        fill="#090B10",
        outline="#535B65",
        width=5
    )

    # Camera glass
    draw.ellipse(
        (cx-radius, cy-radius,
         cx+radius, cy+radius),
        fill="#03060B",
        outline="#9BA3AA",
        width=3
    )

    glass_radius = radius - 9

    draw.ellipse(
        (cx-glass_radius, cy-glass_radius,
         cx+glass_radius, cy+glass_radius),
        fill="#08141D",
        outline="#263B48",
        width=2
    )

    # Illuminated optical aperture
    aperture_radius = max(
        2, round(glass_radius * openness)
    )

    draw.ellipse(
        (cx-aperture_radius, cy-aperture_radius,
         cx+aperture_radius, cy+aperture_radius),
        fill="#03080F",
        outline=color,
        width=2
    )

    # Six overlapping-looking mechanical blades.
    # Each covers the area outside the shrinking aperture.
    outer = glass_radius
    inner = aperture_radius

    if openness < 0.98:
        for i in range(6):
            a1 = math.radians(i * 60 - 90)
            a2 = math.radians((i + 1) * 60 - 90)

            # Small twist makes the blades appear angled
            twist = (1.0 - openness) * 0.22

            polygon = [
                point(cx, cy, outer, a1),
                point(cx, cy, outer, a2),
                point(cx, cy, inner, a2 + twist),
                point(cx, cy, inner, a1 + twist)
            ]

            draw.polygon(
                polygon,
                fill="#343C46",
                outline="#78838E",
                width=1
            )

        # Redraw illuminated central opening
        draw.ellipse(
            (cx-inner, cy-inner,
             cx+inner, cy+inner),
            fill="#03080F",
            outline=color,
            width=2
        )

    # Central camera pupil, visible only when open
    if openness > 0.25:
        pupil = max(2, round(aperture_radius * 0.35))
        draw.ellipse(
            (cx-pupil, cy-pupil,
             cx+pupil, cy+pupil),
            fill="#010305"
        )

    # Mechanical retaining screws
    for angle in (0, 90, 180, 270):
        a = math.radians(angle)
        x, y = point(cx, cy, radius+3, a)
        draw.ellipse(
            (x-2, y-2, x+2, y+2),
            fill="#A0A6AC"
        )


def smooth(a, b, progress):
    progress = max(0.0, min(1.0, progress))
    return a + (b-a) * progress


def get_expression(t):
    """
    Return:
    name, primary openness, secondary openness,
    primary horizontal offset, secondary horizontal offset
    """

    phase = t % DURATION

    # 0-4: Scanning, with quick natural blink
    if phase < 4:
        blink = 1.0

        if 2.0 <= phase < 2.3:
            p = (phase - 2.0) / 0.3
            blink = abs(2*p - 1)

        return (
            "NORMAL SCAN",
            blink, blink,
            int(7 * math.sin(t * 1.4)),
            int(4 * math.sin(t * 1.9 + 1))
        )

    # 4-8: Suspicious. Primary nearly closed.
    if phase < 8:
        p = min(1.0, (phase - 4) / 0.7)

        return (
            "SUSPICIOUS",
            smooth(1, 0.12, p),
            0.85,
            7, 4
        )

    # 8-12: Both optics look unimpressed
    if phase < 12:
        p = min(1.0, (phase - 8) / 0.7)

        return (
            "UNIMPRESSED",
            smooth(0.12, 0.22, p),
            smooth(0.85, 0.22, p),
            0, 0
        )

    # 12-16: Alternating confused blinks
    if phase < 16:
        p = phase - 12

        left = 1.0
        right = 1.0

        if 0.5 <= p < 1.1:
            left = abs(2*((p-0.5)/0.6)-1)

        if 2.0 <= p < 2.6:
            right = abs(2*((p-2.0)/0.6)-1)

        return (
            "CONFUSED",
            left, right,
            -5, 4
        )

    # 16-20: Both irises get sleepy
    if phase < 20:
        p = min(1.0, (phase - 16) / 2.5)

        return (
            "SLEEPY",
            smooth(1, 0.08, p),
            smooth(1, 0.08, p),
            0, 0
        )

    # 20-24: Alert, snap open
    p = min(1.0, (phase - 20) / 0.25)

    return (
        "ALERT",
        smooth(0.08, 1.0, p),
        smooth(0.08, 1.0, p),
        0, 0
    )


def draw_frame(t):
    image = Image.new(
        "RGB", (WIDTH, HEIGHT), "#080A0D"
    )
    d = ImageDraw.Draw(image)

    mode, left_open, right_open, left_x, right_x = (
        get_expression(t)
    )

    # Astromech main faceplate
    d.polygon(
        [(23,18),(457,18),(470,33),(470,205),
         (455,221),(25,221),(10,205),(10,33)],
        fill="#13171D",
        outline="#49505A",
        width=3
    )

    # Red upper armor
    d.polygon(
        [(30,25),(450,25),(440,45),(40,45)],
        fill="#721010",
        outline=RED,
        width=2
    )

    d.text(
        (240,29),
        "V-XN  //  ASTROMECH SYSTEMS",
        font=SMALL,
        fill="#D3D7DC",
        anchor="mt"
    )

    # Primary optic armored housing
    d.polygon(
        [(43,76),(63,55),(220,55),(240,76),
         (240,185),(220,205),(63,205),(43,185)],
        fill="#292D33",
        outline=RED,
        width=3
    )

    d.polygon(
        [(59,84),(75,70),(208,70),(224,84),
         (224,177),(208,191),(75,191),(59,177)],
        fill="#13171D",
        outline="#60666F",
        width=2
    )

    # Secondary optic armored housing
    d.polygon(
        [(266,75),(281,59),(428,59),(445,75),
         (445,166),(428,182),(281,182),(266,166)],
        fill="#292D33",
        outline="#A11C1C",
        width=3
    )

    d.polygon(
        [(280,85),(290,75),(420,75),(431,85),
         (431,157),(420,168),(290,168),(280,157)],
        fill="#13171D",
        outline="#626B76",
        width=2
    )

    # Our new mechanical irises!
    draw_iris(
        d, 141 + left_x, 131,
        49, left_open, AMBER
    )

    draw_iris(
        d, 354 + right_x, 121,
        32, right_open, CYAN
    )

    # Small fixed sensor strip
    d.rectangle(
        (326,164,383,170),
        fill="#090C10",
        outline="#77818D"
    )

    for x in range(332,381,9):
        d.rectangle(
            (x,166,x+4,168),
            fill=AMBER
        )

    # Diagnostic LED bar
    d.rectangle(
        (271,190,440,211),
        fill="#090D12",
        outline="#525B66",
        width=2
    )

    bounce = [0,1,2,3,4,3,2,1]
    active = bounce[int(t*3) % len(bounce)]

    colors = [
        RED, AMBER, "#18C760", CYAN, RED
    ]

    for i, color in enumerate(colors):
        x = 288 + i*33

        d.ellipse(
            (x,197,x+7,204),
            fill=color if i == active else "#282D33"
        )

    # Center faceplate seam
    d.line(
        (240,53,250,67,250,205),
        fill="#515B65",
        width=2
    )

    # Message display
    d.polygon(
        [(32,234),(448,234),(462,247),(462,296),
         (448,310),(32,310),(18,296),(18,247)],
        fill="#11171E",
        outline=RED,
        width=3
    )

    d.text(
        (240,245),
        "VEX // " + mode,
        font=FONT,
        fill=AMBER,
        anchor="mt"
    )

    d.text(
        (240,282),
        "MECHANICAL IRIS TEST",
        font=SMALL,
        fill=CYAN,
        anchor="mt"
    )

    return image


def main():
    print("VEX 2.0 - MECHANICAL IRIS TEST")
    print("24-second demonstration")
    print("Press Ctrl+C to stop early.")
    print()

    start = time.monotonic()
    frames = 0
    last_expression = None

    try:
        while True:
            elapsed = time.monotonic() - start

            if elapsed >= DURATION:
                break

            expression = get_expression(elapsed)[0]

            if expression != last_expression:
                print(
                    f"{elapsed:5.1f}s: {expression}"
                )
                last_expression = expression

            show(draw_frame(elapsed))
            frames += 1

            time.sleep(0.125)

    except KeyboardInterrupt:
        print("Test interrupted.")

    elapsed = time.monotonic() - start

    print()
    print(f"Frames: {frames}")
    print(f"Average FPS: {frames/max(elapsed, 0.001):.1f}")
    print("Iris test complete.")


if __name__ == "__main__":
    main()
