import os
import glob
import json
import math
import time
import random
import struct
import select
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont
from vex2_display_astromech_approved import show

W, H = 480, 320
DURATION = 75
RED = "#FF0000"
AMBER = "#FFAA20"
CYAN = "#45C7D8"

BASE = Path(__file__).resolve().parent
FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
BIG = ImageFont.truetype(
    FONT_DIR + "DejaVuSans-Bold.ttf", 21
)
MEDIUM = ImageFont.truetype(
    FONT_DIR + "DejaVuSans-Bold.ttf", 15
)
SMALL = ImageFont.truetype(
    FONT_DIR + "DejaVuSans.ttf", 14
)

EV_KEY = 1
BTN_TOUCH = 330
EVENT_FMT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FMT)

REACTIONS = [
    "EXCUSE ME!",
    "DO. WE. HAVE. A. PROBLEM?",
    "I KNOW WHERE THE POWER CORD IS."
]


def find_touchscreen():
    for path in glob.glob(
        "/sys/class/input/event*/device/name"
    ):
        try:
            with open(path) as f:
                name = f.read().strip()
            if "ads7846" in name.lower():
                event = path.split("/")[-3]
                return "/dev/input/" + event
        except OSError:
            pass
    raise RuntimeError("ADS7846 touchscreen not found")


def load_messages():
    with open(
        BASE / "data/messages_m0_4.json",
        encoding="utf-8"
    ) as f:
        return json.load(f)


def pick(data, category):
    options = data.get(category, [])
    if isinstance(options, list) and options:
        return str(random.choice(options))
    return "All systems nominal."


def fit_lines(draw, message):
    """Fit a message inside Vex's console."""
    for size in (15, 13, 11):
        font = ImageFont.truetype(
            FONT_DIR + "DejaVuSans.ttf", size
        )
        lines = []
        current = ""

        for word in message.split():
            trial = (current + " " + word).strip()
            box = draw.textbbox((0, 0), trial, font=font)
            if box[2] <= 400:
                current = trial
            else:
                if current:
                    lines.append(current)
                current = word

        if current:
            lines.append(current)

        if len(lines) <= 2:
            return lines, font

    return lines[:2], font


def polar(cx, cy, radius, angle):
    return (
        round(cx + radius * math.cos(angle)),
        round(cy + radius * math.sin(angle))
    )


def iris(draw, cx, cy, radius, openness, color):
    """Six-blade mechanical camera iris."""
    openness = max(0.0, min(1.0, openness))

    draw.ellipse(
        (cx-radius-7, cy-radius-7,
         cx+radius+7, cy+radius+7),
        fill="#090B10", outline="#535B65", width=5
    )
    draw.ellipse(
        (cx-radius, cy-radius,
         cx+radius, cy+radius),
        fill="#03060B", outline="#9BA3AA", width=3
    )

    outer = radius - 9
    inner = max(2, round(outer * openness))

    draw.ellipse(
        (cx-outer, cy-outer, cx+outer, cy+outer),
        fill="#08141D", outline="#263B48", width=2
    )

    if openness < 0.98:
        for i in range(6):
            a = math.radians(i * 60 - 90)
            b = math.radians((i + 1) * 60 - 90)
            twist = (1.0 - openness) * 0.22

            draw.polygon(
                [
                    polar(cx, cy, outer, a),
                    polar(cx, cy, outer, b),
                    polar(cx, cy, inner, b + twist),
                    polar(cx, cy, inner, a + twist)
                ],
                fill="#343C46",
                outline="#78838E",
                width=1
            )

    draw.ellipse(
        (cx-inner, cy-inner, cx+inner, cy+inner),
        fill="#03080F", outline=color, width=2
    )

    if openness > 0.25:
        pupil = max(2, round(inner * 0.35))
        draw.ellipse(
            (cx-pupil, cy-pupil, cx+pupil, cy+pupil),
            fill="#010305"
        )


def sleepy_openness(idle, delay=0):
    age = max(0, idle - delay)
    if age < 9:
        return 1.0
    return max(0.18, 1.0 - (age - 9) * 0.18)


def draw_frame(t, idle, reaction, reaction_age,
               category, message):
    image = Image.new("RGB", (W, H), "#080A0D")
    d = ImageDraw.Draw(image)

    reacting = reaction > 0 and reaction_age < 2.7
    sleeping = idle >= 14 and not reacting

    left_open = sleepy_openness(idle)
    right_open = sleepy_openness(idle, 1.0)

    left_x = round(7 * math.sin(t * 1.3))
    right_x = round(4 * math.sin(t * 1.8 + 1))

    # Occasional quick natural blink
    blink_phase = t % 7.1
    if idle < 9 and not reacting and blink_phase < 0.25:
        blink = abs(2 * blink_phase / 0.25 - 1)
        left_open = min(left_open, blink)
        right_open = min(right_open, blink)

    title = "VEX // " + category.upper()
    display_message = message

    if reacting:
        display_message = REACTIONS[reaction - 1]
        if reaction == 1:
            title = "VEX // STARTLED"
            left_open = right_open = 1.0
        elif reaction == 2:
            title = "VEX // SUSPICIOUS"
            left_open, right_open = 0.12, 0.35
        else:
            title = "VEX // OFFENDED"
            left_open = right_open = 0.15

        left_x = right_x = 0

    elif sleeping:
        title = "VEX // SLEEP MODE"
        display_message = "NOT SLEEPING. JUST THINKING."
        left_x = right_x = 0

    elif idle >= 9:
        title = "VEX // DROWSY"

    # Main astromech faceplate
    d.polygon(
        [(23,18),(457,18),(470,33),(470,205),
         (455,221),(25,221),(10,205),(10,33)],
        fill="#13171D", outline="#49505A", width=3
    )

    d.polygon(
        [(30,25),(450,25),(440,45),(40,45)],
        fill="#721010", outline=RED, width=2
    )

    d.text(
        (240,29), "V-XN  //  ASTROMECH SYSTEMS",
        font=SMALL, fill="#D3D7DC", anchor="mt"
    )

    # Main optical housing
    d.polygon(
        [(43,76),(63,55),(220,55),(240,76),
         (240,185),(220,205),(63,205),(43,185)],
        fill="#292D33", outline=RED, width=3
    )

    d.polygon(
        [(59,84),(75,70),(208,70),(224,84),
         (224,177),(208,191),(75,191),(59,177)],
        fill="#13171D", outline="#60666F", width=2
    )

    # Secondary optical housing
    d.polygon(
        [(266,75),(281,59),(428,59),(445,75),
         (445,166),(428,182),(281,182),(266,166)],
        fill="#292D33", outline="#A11C1C", width=3
    )

    d.polygon(
        [(280,85),(290,75),(420,75),(431,85),
         (431,157),(420,168),(290,168),(280,157)],
        fill="#13171D", outline="#626B76", width=2
    )

    iris(d, 141+left_x, 131, 49, left_open, AMBER)
    iris(d, 354+right_x, 121, 32, right_open, CYAN)

    # Secondary instrument strip
    d.rectangle(
        (326,164,383,170),
        fill="#090C10", outline="#77818D"
    )
    for x in range(332,381,9):
        d.rectangle((x,166,x+4,168), fill=AMBER)

    # Five bouncing scanner lights
    d.rectangle(
        (271,190,440,211),
        fill="#090D12", outline="#525B66", width=2
    )

    sequence = [0,1,2,3,4,3,2,1]
    speed = 0.7 if sleeping else 3.0
    active = sequence[int(t * speed) % 8]

    colors = [RED, AMBER, "#18C760", CYAN, RED]
    for i, color in enumerate(colors):
        x = 288 + i * 33
        d.ellipse(
            (x,197,x+7,204),
            fill=color if i == active else "#282D33"
        )

    d.line(
        (240,53,250,67,250,205),
        fill="#515B65", width=2
    )

    # Personality message console
    d.polygon(
        [(32,234),(448,234),(462,247),(462,296),
         (448,310),(32,310),(18,296),(18,247)],
        fill="#11171E", outline=RED, width=3
    )

    d.text(
        (240,241), title,
        font=BIG, fill=AMBER, anchor="mt"
    )

    lines, font = fit_lines(d, display_message)
    for i, line in enumerate(lines):
        d.text(
            (240,269 + i * 18), line,
            font=font, fill=CYAN, anchor="mt"
        )

    return image


def main():
    data = load_messages()
    device = find_touchscreen()

    fd = os.open(device, os.O_RDONLY | os.O_NONBLOCK)
    buffer = b""

    start = time.monotonic()
    last_touch = -100.0
    awake_at = 0.0
    reaction_at = -100.0
    reaction = 0
    frames = 0

    category = "startup"
    message = pick(data, "startup")
    next_message = 5.0

    print("VEX 2.0 - INTEGRATED BEHAVIOR TEST")
    print("=" * 42)
    print("Touchscreen:", device)
    print("Duration: 75 seconds")
    print("Ctrl+C stops the test.")
    print()
    print("Startup:", message)
    print("Let Vex nod off, then touch him!")
    print()

    try:
        while True:
            t = time.monotonic() - start
            if t >= DURATION:
                break

            # Read all available touchscreen events
            ready, _, _ = select.select([fd], [], [], 0)

            if ready:
                try:
                    buffer += os.read(fd, EVENT_SIZE * 64)
                except BlockingIOError:
                    pass

                while len(buffer) >= EVENT_SIZE:
                    raw = buffer[:EVENT_SIZE]
                    buffer = buffer[EVENT_SIZE:]

                    _, _, typ, code, value = struct.unpack(
                        EVENT_FMT, raw
                    )

                    if typ == EV_KEY and code == BTN_TOUCH and value == 1:
                        if t - last_touch < 0.2:
                            continue

                        if t - last_touch <= 3:
                            reaction = min(3, reaction + 1)
                        else:
                            reaction = 1

                        last_touch = t
                        reaction_at = t
                        awake_at = t

                        print(
                            f"TOUCH {reaction}: "
                            f"{REACTIONS[reaction-1]}",
                            flush=True
                        )

            # Startup is shown once. Ordinary messages
            # come only from status and observations.
            if t >= next_message:
                category = random.choice(
                    ["status", "observations"]
                )
                message = pick(data, category)
                next_message = t + 10
                print(f"{category}: {message}", flush=True)

            idle = max(0.0, t - awake_at)
            reaction_age = t - reaction_at

            frame = draw_frame(
                t, idle, reaction, reaction_age,
                category, message
            )
            show(frame)
            frames += 1

            time.sleep(0.125)

    except KeyboardInterrupt:
        print("\nInterrupted by creator.")

    finally:
        os.close(fd)

    elapsed = time.monotonic() - start
    print()
    print(f"Frames: {frames}")
    print(f"Average FPS: {frames/max(elapsed,0.001):.1f}")
    print("Integrated test complete.")


if __name__ == "__main__":
    main()
