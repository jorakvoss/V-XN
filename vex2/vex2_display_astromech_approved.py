from PIL import Image, ImageDraw, ImageFont
import math

WIDTH = 480
HEIGHT = 320
FRAMEBUFFER = "/dev/fb1"

BG = "#080A0D"
ARMOR = "#292D33"
ARMOR_LIGHT = "#49505A"
ARMOR_DARK = "#13171D"
RED = "#FF0000"
RED_DARK = "#721010"
STEEL = "#8A929A"
AMBER = "#FFAA20"
CYAN = "#45C7D8"


def show(image):
    """Convert RGB image into RGB565 for the SPI framebuffer."""
    rgb = image.convert("RGB").tobytes()
    pixels = bytearray(WIDTH * HEIGHT * 2)

    for i in range(0, len(rgb), 3):
        r, g, b = rgb[i], rgb[i + 1], rgb[i + 2]

        value = (
            ((r >> 3) << 11)
            | ((g >> 2) << 5)
            | (b >> 3)
        )

        j = (i // 3) * 2
        pixels[j] = value & 255
        pixels[j + 1] = value >> 8

    with open(FRAMEBUFFER, "wb", buffering=0) as fb:
        fb.write(pixels)


def bolt(draw, x, y):
    draw.ellipse(
        (x-4, y-4, x+4, y+4),
        fill="#707780",
        outline="#15191D",
        width=1
    )
    draw.line(
        (x-2, y+2, x+2, y-2),
        fill="#20252B",
        width=1
    )


def draw_lens(draw, cx, cy, radius, glow=AMBER):
    """Draw a recessed mechanical camera lens."""

    draw.ellipse(
        (
            cx-radius-7, cy-radius-7,
            cx+radius+7, cy+radius+7
        ),
        fill="#090B10",
        outline="#535B65",
        width=5
    )

    draw.ellipse(
        (
            cx-radius, cy-radius,
            cx+radius, cy+radius
        ),
        fill="#03060B",
        outline="#9BA3AA",
        width=3
    )

    draw.ellipse(
        (
            cx-radius+9, cy-radius+9,
            cx+radius-9, cy+radius-9
        ),
        fill="#08141D",
        outline="#263B48",
        width=3
    )

    # Subtle illuminated aperture
    inner = max(7, radius // 3)

    draw.ellipse(
        (
            cx-inner, cy-inner,
            cx+inner, cy+inner
        ),
        fill="#070B10",
        outline=glow,
        width=3
    )

    draw.ellipse(
        (
            cx-inner+4, cy-inner+4,
            cx+inner-4, cy+inner-4
        ),
        fill="#020407"
    )

    # Lens reflection
    draw.ellipse(
        (
            cx-radius//3, cy-radius//2,
            cx-radius//3+8, cy-radius//2+8
        ),
        fill="#7F9FA8"
    )

    # Four retaining screws
    for angle in (0, 90, 180, 270):
        rad = math.radians(angle)
        x = int(cx + (radius+3) * math.cos(rad))
        y = int(cy + (radius+3) * math.sin(rad))
        draw.ellipse(
            (x-2, y-2, x+2, y+2),
            fill="#A0A6AC"
        )


def draw_face():
    image = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(image)

    font_large = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        23
    )

    font_small = ImageFont.truetype(
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        14
    )

    # Main armored faceplate
    draw.polygon(
        [
            (23, 18), (457, 18),
            (470, 33), (470, 205),
            (455, 221), (25, 221),
            (10, 205), (10, 33)
        ],
        fill=ARMOR_DARK,
        outline=ARMOR_LIGHT,
        width=3
    )

    # Top armor
    draw.polygon(
        [
            (30, 25), (450, 25),
            (440, 45), (40, 45)
        ],
        fill=RED_DARK,
        outline=RED,
        width=2
    )

    draw.text(
        (240, 29),
        "V-XN  //  ASTROMECH SYSTEMS",
        font=font_small,
        fill="#D3D7DC",
        anchor="mt"
    )

    # Primary photoreceptor armor
    draw.polygon(
        [
            (43, 76), (63, 55),
            (220, 55), (240, 76),
            (240, 185), (220, 205),
            (63, 205), (43, 185)
        ],
        fill=ARMOR,
        outline=RED,
        width=3
    )

    draw.polygon(
        [
            (59, 84), (75, 70),
            (208, 70), (224, 84),
            (224, 177), (208, 191),
            (75, 191), (59, 177)
        ],
        fill=ARMOR_DARK,
        outline="#60666F",
        width=2
    )

    draw_lens(draw, 141, 131, 49, AMBER)

    for x, y in (
        (55, 83), (228, 83),
        (55, 183), (228, 183)
    ):
        bolt(draw, x, y)

    # Smaller secondary sensor assembly
    draw.polygon(
        [
            (266, 75), (281, 59),
            (428, 59), (445, 75),
            (445, 166), (428, 182),
            (281, 182), (266, 166)
        ],
        fill=ARMOR,
        outline="#A11C1C",
        width=3
    )

    draw.polygon(
        [
            (280, 85), (290, 75),
            (420, 75), (431, 85),
            (431, 157), (420, 168),
            (290, 168), (280, 157)
        ],
        fill=ARMOR_DARK,
        outline="#626B76",
        width=2
    )

    draw_lens(draw, 354, 121, 32, CYAN)

    # Secondary sensor indicator
    draw.rectangle(
        (326, 164, 383, 170),
        fill="#090C10",
        outline="#77818D"
    )

    for x in range(332, 381, 9):
        draw.rectangle(
            (x, 166, x+4, 168),
            fill=AMBER
        )

    # Additional lower-right diagnostics
    draw.rectangle(
        (271, 190, 440, 211),
        fill="#090D12",
        outline="#525B66",
        width=2
    )

    for index, color in enumerate(
        [RED, AMBER, "#18C760", CYAN, RED]
    ):
        x = 288 + index * 33
        draw.ellipse(
            (x, 197, x+7, 204),
            fill=color
        )

    # Faceplate seam
    draw.line(
        (240, 53, 250, 67, 250, 205),
        fill="#515B65",
        width=2
    )

    # Lower message console
    draw.polygon(
        [
            (32, 234), (448, 234),
            (462, 247), (462, 296),
            (448, 310), (32, 310),
            (18, 296), (18, 247)
        ],
        fill="#11171E",
        outline=RED,
        width=3
    )

    draw.text(
        (240, 247),
        "VEX 2.0 ONLINE",
        font=font_large,
        fill="#F1D7B0",
        anchor="mt"
    )

    draw.text(
        (240, 283),
        "ATTITUDE SUBSYSTEM: ACTIVE",
        font=font_small,
        fill=CYAN,
        anchor="mt"
    )

    show(image)


if __name__ == "__main__":
    draw_face()
    print("Vex astromech face rendered!")
