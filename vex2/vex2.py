#!/usr/bin/env python3

import glob
import json
import math
import os
import random
import select
import struct
import time
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image, ImageDraw, ImageFont
from vex2_display_astromech_approved import show

# ------------------------------------------
# VEX 2.0 - SLEEP AND OVERNIGHT STANDBY
# ------------------------------------------

W, H = 480, 320
FRAME_DELAY = 0.125

RED = "#FF0000"
AMBER = "#FFAA20"
CYAN = "#45C7D8"

BASE = Path(__file__).resolve().parent
DATA_FILE = BASE.parent / "data/messages_m0_4.json"

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
TITLE_FONT = ImageFont.truetype(
    FONT_DIR + "DejaVuSans-Bold.ttf", 22
)
SMALL_FONT = ImageFont.truetype(
    FONT_DIR + "DejaVuSans-Bold.ttf", 14
)

# Overnight: midnight to 7 AM, Eastern
NIGHT_START = 0
NIGHT_END = 7
NIGHT_WAKE_SECONDS = 35

# Longer, less frequent naps
NAP_INTERVAL = (60, 150)
NAP_DURATION = (45, 90)
NAP_DROWSY_SECONDS = 9

REACTIONS = [
    "EXCUSE ME!",
    "DO. WE. HAVE. A. PROBLEM?",
    "I KNOW WHERE THE POWER CORD IS."
]

EV_KEY = 1
BTN_TOUCH = 330
EVENT_FORMAT = "llHHi"
EVENT_SIZE = struct.calcsize(EVENT_FORMAT)


def find_touch():
    for path in glob.glob(
        "/sys/class/input/event*/device/name"
    ):
        try:
            name = Path(path).read_text().strip()
            if "ads7846" in name.lower():
                event = path.split("/")[-3]
                return "/dev/input/" + event
        except OSError:
            pass

    raise RuntimeError("ADS7846 touchscreen not found")


def get_messages():
    with open(DATA_FILE, encoding="utf-8") as f:
        return json.load(f)


def polar(cx, cy, r, angle):
    return (
        round(cx + r * math.cos(angle)),
        round(cy + r * math.sin(angle))
    )


def draw_iris(d, cx, cy, radius, opening, color):
    opening = max(0.0, min(1.0, opening))

    d.ellipse(
        (cx-radius-7, cy-radius-7,
         cx+radius+7, cy+radius+7),
        fill="#090B10",
        outline="#535B65",
        width=5
    )

    d.ellipse(
        (cx-radius, cy-radius,
         cx+radius, cy+radius),
        fill="#03060B",
        outline="#9BA3AA",
        width=3
    )

    outer = radius - 9
    inner = max(2, round(outer * opening))

    d.ellipse(
        (cx-outer, cy-outer, cx+outer, cy+outer),
        fill="#08141D",
        outline="#263B48",
        width=2
    )

    if opening < 0.98:
        for i in range(6):
            a = math.radians(i * 60 - 90)
            b = math.radians((i + 1) * 60 - 90)
            twist = (1 - opening) * 0.22

            d.polygon(
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

    d.ellipse(
        (cx-inner, cy-inner, cx+inner, cy+inner),
        fill="#03080F",
        outline=color,
        width=2
    )

    if opening > 0.25:
        p = max(2, round(inner * 0.35))
        d.ellipse(
            (cx-p, cy-p, cx+p, cy+p),
            fill="#010305"
        )


# Cache fonts and layouts: the display redraws eight times per second.
from functools import lru_cache


@lru_cache(maxsize=32)
def message_font(size):
    return ImageFont.truetype(
        FONT_DIR + "DejaVuSans-Bold.ttf", size
    )


@lru_cache(maxsize=256)
def message_layout(text):
    """Fit every word inside the console; never truncate a message."""
    measure = ImageDraw.Draw(Image.new("RGB", (1, 1)))

    def wrap(font):
        lines = []
        current = ""
        for word in str(text).split():
            candidate = (current + " " + word).strip()
            if measure.textlength(candidate, font=font) <= 400:
                current = candidate
                continue
            if current:
                lines.append(current)
                current = ""
            # Even an unusually long unbroken word must fit.
            for char in word:
                if measure.textlength(current + char, font=font) > 400:
                    lines.append(current)
                    current = char
                else:
                    current += char
        if current:
            lines.append(current)
        return lines or [""]

    for size in (18, 17, 16):
        font = message_font(size)
        lines = wrap(font)
        if len(lines) <= 2:
            break
    pages = tuple(tuple(lines[i:i + 2]) for i in range(0, len(lines), 2))
    return pages, size


def fit_message(d, text):
    # Compatibility helper: callers needing every page use message_layout.
    pages, size = message_layout(str(text))
    return list(pages[0]), message_font(size)


class Vex:
    def __init__(self):
        self.messages = get_messages()
        self.device = find_touch()
        self.fd = None
        self.buffer = b""

        self.start = time.monotonic()
        self.last_touch = -100.0
        self.reaction_at = -100.0
        self.reaction = 0

        self.category = "startup"
        self.message = self.pick("startup")
        self.next_message = 5.0

        self.nap_started = None
        self.nap_end = None
        self.next_nap = random.uniform(
            *NAP_INTERVAL
        )

        self.night_awake_until = 0.0
        self.night_blank = False
        self.frames = 0

    def pick(self, category):
        options = self.messages.get(category, [])
        if isinstance(options, list) and options:
            return str(random.choice(options))
        return "All systems nominal."

    def is_night(self):
        if os.environ.get("VEX_FORCE_NIGHT") == "1":
            return True

        if os.environ.get("VEX_FORCE_DAY") == "1":
            return False

        hour = datetime.now(
            ZoneInfo("America/New_York")
        ).hour

        return NIGHT_START <= hour < NIGHT_END

    def touch(self, t):
        if t - self.last_touch < 0.2:
            return

        if t - self.last_touch <= 3:
            self.reaction = min(3, self.reaction + 1)
        else:
            self.reaction = 1

        self.last_touch = t
        self.reaction_at = t

        # Interrupt naps immediately.
        self.nap_started = None
        self.nap_end = None
        self.next_nap = t + random.uniform(
            *NAP_INTERVAL
        )

        # Overnight touches wake him temporarily.
        if self.is_night():
            self.night_awake_until = (
                t + NIGHT_WAKE_SECONDS
            )

        self.night_blank = False

        print(
            "TOUCH:", REACTIONS[self.reaction - 1],
            flush=True
        )

    def read_touch(self, t):
        try:
            self.buffer += os.read(
                self.fd, EVENT_SIZE * 64
            )
        except BlockingIOError:
            return

        while len(self.buffer) >= EVENT_SIZE:
            raw = self.buffer[:EVENT_SIZE]
            self.buffer = self.buffer[EVENT_SIZE:]

            _, _, typ, code, value = struct.unpack(
                EVENT_FORMAT, raw
            )

            if (
                typ == EV_KEY
                and code == BTN_TOUCH
                and value == 1
            ):
                self.touch(t)

    def update(self, t, overnight):
        if overnight:
            return

        if t >= self.next_message:
            self.category = random.choice(
                ["status", "observations"]
            )
            self.message = self.pick(self.category)

            self.next_message = (
                t + random.uniform(12, 25)
            )

            pages, _ = message_layout(str(self.message))
            reading_seconds = sum(
                max(3.0, len(" ".join(page).split()) * 0.4)
                for page in pages
            )
            self.next_message = max(self.next_message, t + reading_seconds)

            print(
                f"[{self.category}] {self.message}",
                flush=True
            )

        # Begin a natural nap.
        if (
            self.nap_started is None
            and t >= self.next_nap
        ):
            self.nap_started = t
            self.nap_end = (
                t + random.uniform(*NAP_DURATION)
            )

            print(
                "VEX: Getting sleepy...",
                flush=True
            )

        # Natural wake-up when nap expires.
        if (
            self.nap_end is not None
            and t >= self.nap_end
        ):
            self.nap_started = None
            self.nap_end = None
            self.next_nap = (
                t + random.uniform(*NAP_INTERVAL)
            )

            print(
                "VEX: Awake. Nobody saw that.",
                flush=True
            )

    def draw(self, t):
        im = Image.new("RGB", (W, H), "#080A0D")
        d = ImageDraw.Draw(im)

        reacting = (
            self.reaction > 0
            and t - self.reaction_at < 3
        )

        sleeping = (
            self.nap_started is not None
            and not reacting
        )

        title = "VEX // " + self.category.upper()
        message = self.message

        left_open = right_open = 1.0
        left_x = round(7 * math.sin(t * 1.3))
        right_x = round(4 * math.sin(t * 1.8 + 1))

        # Natural mechanical blinking.
        blink_phase = t % 7.1

        if blink_phase < 0.25:
            blink = abs(
                2 * blink_phase / 0.25 - 1
            )
            left_open = right_open = blink

        if sleeping:
            age = t - self.nap_started

            lp = max(
                0.0,
                min(1.0, age / NAP_DROWSY_SECONDS)
            )

            rp = max(
                0.0,
                min(
                    1.0,
                    (age - 1.5) / NAP_DROWSY_SECONDS
                )
            )

            left_open = 1 - 0.82 * lp
            right_open = 1 - 0.82 * rp
            left_x = right_x = 0

            title = "VEX // DROWSY"
            message = "NOT SLEEPING. JUST THINKING."

            if age >= NAP_DROWSY_SECONDS + 1.5:
                title = "VEX // SLEEP MODE"

        if reacting:
            message = REACTIONS[self.reaction - 1]
            left_x = right_x = 0

            if self.reaction == 1:
                title = "VEX // STARTLED"
                left_open = right_open = 1.0

            elif self.reaction == 2:
                title = "VEX // SUSPICIOUS"
                left_open = 0.12
                right_open = 0.35

            else:
                title = "VEX // OFFENDED"
                left_open = right_open = 0.15

        # Main armored faceplate.
        d.polygon(
            [(23,18),(457,18),(470,33),(470,205),
             (455,221),(25,221),(10,205),(10,33)],
            fill="#13171D",
            outline="#49505A",
            width=3
        )

        # Upper red armor.
        d.polygon(
            [(30,25),(450,25),(440,45),(40,45)],
            fill="#721010",
            outline=RED,
            width=2
        )

        d.text(
            (240,29),
            "V-XN  //  ASTROMECH SYSTEMS",
            font=SMALL_FONT,
            fill="#D3D7DC",
            anchor="mt"
        )

        # Primary optic housing.
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

        # Secondary optic housing.
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

        # Mechanical camera irises.
        draw_iris(
            d, 141+left_x, 131,
            49, left_open, AMBER
        )

        draw_iris(
            d, 354+right_x, 121,
            32, right_open, CYAN
        )

        # Secondary sensor strip.
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

        # Bouncing five-light diagnostic scanner.
        d.rectangle(
            (271,190,440,211),
            fill="#090D12",
            outline="#525B66",
            width=2
        )

        pattern = [0,1,2,3,4,3,2,1]
        speed = 0.7 if sleeping else 3.0
        active = pattern[
            int(t * speed) % len(pattern)
        ]

        colors = [
            RED, AMBER, "#18C760", CYAN, RED
        ]

        for i, color in enumerate(colors):
            x = 288 + i * 33

            d.ellipse(
                (x,197,x+7,204),
                fill=(
                    color if i == active
                    else "#282D33"
                )
            )

        # Faceplate seam.
        d.line(
            (240,53,250,67,250,205),
            fill="#515B65",
            width=2
        )

        # Message console.
        d.polygon(
            [(32,234),(448,234),(462,247),
             (462,296),(448,310),(32,310),
             (18,296),(18,247)],
            fill="#11171E",
            outline=RED,
            width=3
        )

        d.text(
            (240,241), title,
            font=TITLE_FONT,
            fill="#FFFFFF",
            anchor="mt"
        )

        pages, size = message_layout(str(message))
        font = message_font(size)
        page_key = (title, message)
        if getattr(self, "_page_key", None) != page_key:
            self._page_key = page_key
            self._page_started = t

        # Give each page time to read. All source text is retained.
        durations = [max(3.0, len(" ".join(page).split()) * 0.4)
                     for page in pages]
        phase = max(0.0, t - self._page_started) % sum(durations)
        page_index = 0
        for index, duration in enumerate(durations):
            if phase < duration:
                page_index = index
                break
            phase -= duration
        lines = pages[page_index]
        line_height = 21
        top = 268 if len(lines) == 2 else 278
        for i, line in enumerate(lines):
            d.text(
                (240, top + i * line_height), line,
                font=font,
                fill="#F4FCFF",
                anchor="mt"
            )

        return im

    def run(self):
        self.fd = os.open(
            self.device,
            os.O_RDONLY | os.O_NONBLOCK
        )

        print("VEX 2.0 ONLINE")
        print("Touchscreen:", self.device)
        print("Long naps: ENABLED")
        print("Overnight standby: 00:00-07:00 ET")
        print("Press Ctrl+C to stop.")
        print("Startup:", self.message)

        try:
            while True:
                t = time.monotonic() - self.start

                ready, _, _ = select.select(
                    [self.fd], [], [], 0
                )

                if ready:
                    self.read_touch(t)

                overnight = self.is_night()

                standby = (
                    overnight
                    and t >= self.night_awake_until
                )

                if standby:
                    if not self.night_blank:
                        show(
                            Image.new(
                                "RGB", (W, H), "black"
                            )
                        )

                        self.night_blank = True

                        print(
                            "VEX: Overnight standby.",
                            flush=True
                        )

                    # Keep touch input active.
                    time.sleep(0.05)
                    continue

                if self.night_blank:
                    self.night_blank = False
                    print(
                        "VEX: Display awake.",
                        flush=True
                    )

                self.update(t, overnight)

                show(self.draw(t))
                self.frames += 1

                time.sleep(FRAME_DELAY)

        except KeyboardInterrupt:
            print("\nShutdown requested.")

        finally:
            if self.fd is not None:
                os.close(self.fd)

            print("Vex offline.")


if __name__ == "__main__":
    Vex().run()
