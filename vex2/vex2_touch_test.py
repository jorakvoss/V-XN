import os
import glob
import math
import time
import struct
import select

from PIL import Image, ImageDraw, ImageFont
from vex2_display_astromech_approved import show

WIDTH = 480
HEIGHT = 320
DURATION = 45

RED = "#FF0000"
AMBER = "#FFAA20"
CYAN = "#45C7D8"

FONT_PATH = "/usr/share/fonts/truetype/dejavu/"
FONT_BIG = ImageFont.truetype(
    FONT_PATH + "DejaVuSans-Bold.ttf", 23
)
FONT_SMALL = ImageFont.truetype(
    FONT_PATH + "DejaVuSans.ttf", 14
)

# Linux touchscreen event constants
EV_KEY = 1
BTN_TOUCH = 330

# Linux input_event on the 64-bit Pi OS
EVENT_FORMAT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)

# Reaction behavior
TAP_WINDOW = 3.0
REACTION_DURATION = 3.0

REACTIONS = [
    "EXCUSE ME!",
    "DO. WE. HAVE. A. PROBLEM?",
    "I KNOW WHERE THE POWER CORD IS."
]


def find_touchscreen():
    """Find the ADS7846 touchscreen input device."""
    for path in sorted(glob.glob(
        "/sys/class/input/event*/device/name"
    )):
        try:
            with open(path, "r") as f:
                name = f.read().strip()

            if "ads7846" in name.lower():
                event_name = path.split("/")[-3]
                return "/dev/input/" + event_name

        except OSError:
            continue

    raise RuntimeError(
        "ADS7846 touchscreen not found. "
        "Check /proc/bus/input/devices."
    )


def clamp(value, low, high):
    return max(low, min(high, value))


def point(cx, cy, radius, angle):
    return (
        round(cx + radius * math.cos(angle)),
        round(cy + radius * math.sin(angle))
    )


def draw_iris(draw, cx, cy, radius, openness, color):
    """Draw the six-blade mechanical optic."""
    openness = clamp(openness, 0.0, 1.0)

    draw.ellipse(
        (cx-radius-7, cy-radius-7,
         cx+radius+7, cy+radius+7),
        fill="#090B10",
        outline="#535B65",
        width=5
    )

    draw.ellipse(
        (cx-radius, cy-radius,
         cx+radius, cy+radius),
        fill="#03060B",
        outline="#9BA3AA",
        width=3
    )

    outer = radius - 9
    inner = max(2, round(outer * openness))

    draw.ellipse(
        (cx-outer, cy-outer,
         cx+outer, cy+outer),
        fill="#08141D",
        outline="#263B48",
        width=2
    )

    if openness < 0.98:
        for i in range(6):
            a1 = math.radians(i * 60 - 90)
            a2 = math.radians((i + 1) * 60 - 90)
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

    draw.ellipse(
        (cx-inner, cy-inner,
         cx+inner, cy+inner),
        fill="#03080F",
        outline=color,
        width=2
    )

    if openness > 0.25:
        pupil = max(2, round(inner * 0.35))
        draw.ellipse(
            (cx-pupil, cy-pupil,
             cx+pupil, cy+pupil),
            fill="#010305"
        )

    for angle in (0, 90, 180, 270):
        a = math.radians(angle)
        x, y = point(cx, cy, radius+3, a)
        draw.ellipse(
            (x-2, y-2, x+2, y+2),
            fill="#A0A6AC"
        )


def draw_frame(t, awake_since, reaction, reaction_at):
    image = Image.new(
        "RGB", (WIDTH, HEIGHT), "#080A0D"
    )
    d = ImageDraw.Draw(image)

    reacting = (
        reaction > 0
        and t - reaction_at < REACTION_DURATION
    )

    # Start awake, slowly nod off over eight seconds.
    # After reacting, begin the sleepy cycle again.
    idle_time = max(0, t - awake_since)

    if reacting:
        if reaction == 1:
            left_open = right_open = 1.0
            mode = "STARTLED"
        elif reaction == 2:
            left_open = 0.12
            right_open = 0.35
            mode = "SUSPICIOUS"
        else:
            left_open = right_open = 0.15
            mode = "OFFENDED"

        message = REACTIONS[reaction - 1]
        left_x = 0
        right_x = 0

    else:
        # First three seconds: normal scanning
        if idle_time < 3:
            left_open = right_open = 1.0
            mode = "SCANNING"

        # Next five seconds: gradually fall asleep
        elif idle_time < 8:
            progress = (idle_time - 3) / 5

            left_open = 1.0 - 0.82 * clamp(
                progress * 1.3, 0, 1
            )
            right_open = 1.0 - 0.82 * clamp(
                (progress - 0.15) * 1.3, 0, 1
            )

            mode = "GETTING SLEEPY"

        # After eight seconds: nearly asleep
        else:
            left_open = right_open = 0.18
            mode = "Zzzzz..."

        message = (
            "ENVIRONMENTAL SCAN ACTIVE"
            if idle_time < 3
            else "NOT SLEEPING. JUST THINKING."
        )

        left_x = int(7 * math.sin(t * 1.3))
        right_x = int(4 * math.sin(t * 1.8 + 1))

        # Stop scanning once he's nearly asleep
        if idle_time >= 8:
            left_x = right_x = 0

    # Main armored faceplate
    d.polygon(
        [(23,18),(457,18),(470,33),(470,205),
         (455,221),(25,221),(10,205),(10,33)],
        fill="#13171D",
        outline="#49505A",
        width=3
    )

    # Upper red armor
    d.polygon(
        [(30,25),(450,25),(440,45),(40,45)],
        fill="#721010",
        outline=RED,
        width=2
    )

    d.text(
        (240,29),
        "V-XN  //  ASTROMECH SYSTEMS",
        font=FONT_SMALL,
        fill="#D3D7DC",
        anchor="mt"
    )

    # Primary optic housing
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

    # Secondary optic housing
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

    draw_iris(
        d, 141 + left_x, 131,
        49, left_open, AMBER
    )
    draw_iris(
        d, 354 + right_x, 121,
        32, right_open, CYAN
    )

    # Small secondary sensor strip
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

    # Five-light diagnostic scanner
    d.rectangle(
        (271,190,440,211),
        fill="#090D12",
        outline="#525B66",
        width=2
    )

    bounce = [0,1,2,3,4,3,2,1]

    # Scan slowly while sleeping.
    speed = 0.7 if idle_time >= 8 and not reacting else 3
    active = bounce[int(t * speed) % len(bounce)]

    colors = [
        RED, AMBER, "#18C760", CYAN, RED
    ]

    for i, color in enumerate(colors):
        x = 288 + i*33

        if i == active:
            fill = color
        else:
            fill = "#282D33"

        d.ellipse(
            (x,197,x+7,204),
            fill=fill
        )

    # Center faceplate seam
    d.line(
        (240,53,250,67,250,205),
        fill="#515B65",
        width=2
    )

    # Message panel
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
        font=FONT_BIG,
        fill=AMBER,
        anchor="mt"
    )

    # Automatically use smaller text for long reactions
    if len(message) > 25:
        size = 14
    else:
        size = 19

    message_font = ImageFont.truetype(
        FONT_PATH + "DejaVuSans-Bold.ttf",
        size
    )

    d.text(
        (240,282),
        message,
        font=message_font,
        fill=CYAN,
        anchor="mt"
    )

    return image


def main():
    device_path = find_touchscreen()

    print("VEX 2.0 - TOUCHSCREEN ATTITUDE TEST")
    print("=" * 42)
    print("Touch device:", device_path)
    print("Test duration: 45 seconds")
    print("Press Ctrl+C to stop early.")
    print()
    print("Let Vex fall asleep, then poke him!")
    print("Tap again within 3 seconds for more sass.")
    print()

    # Linux input event files require permission.
    fd = os.open(
        device_path,
        os.O_RDONLY | os.O_NONBLOCK
    )

    start = time.monotonic()
    awake_since = 0.0
    reaction = 0
    reaction_at = -100.0
    last_tap = -100.0
    frames = 0
    buffer = b""

    try:
        while True:
            t = time.monotonic() - start

            if t >= DURATION:
                break

            # Read touchscreen input without blocking
            ready, _, _ = select.select(
                [fd], [], [], 0
            )

            if ready:
                try:
                    chunk = os.read(
                        fd, EVENT_SIZE * 64
                    )
                except BlockingIOError:
                    chunk = b""

                buffer += chunk

                while len(buffer) >= EVENT_SIZE:
                    event = buffer[:EVENT_SIZE]
                    buffer = buffer[EVENT_SIZE:]

                    _, _, event_type, code, value = (
                        struct.unpack(EVENT_FORMAT, event)
                    )

                    # Count finger-down only, not release
                    if (
                        event_type == EV_KEY
                        and code == BTN_TOUCH
                        and value == 1
                    ):
                        # Debounce accidental duplicate events
                        if t - last_tap < 0.20:
                            continue

                        if t - last_tap <= TAP_WINDOW:
                            reaction = min(3, reaction + 1)
                        else:
                            reaction = 1

                        last_tap = t
                        reaction_at = t
                        awake_since = t

                        print(
                            f"{t:5.1f}s TAP {reaction}: "
                            f"{REACTIONS[reaction-1]}",
                            flush=True
                        )

            image = draw_frame(
                t, awake_since, reaction, reaction_at
            )
            show(image)
            frames += 1

            time.sleep(0.125)

    except KeyboardInterrupt:
        print("\nInterrupted by creator.")

    finally:
        os.close(fd)

    elapsed = time.monotonic() - start

    print()
    print(f"Frames rendered: {frames}")
    print(
        f"Average FPS: "
        f"{frames/max(elapsed, 0.001):.1f}"
    )
    print("Touchscreen attitude test complete.")


if __name__ == "__main__":
    main()
