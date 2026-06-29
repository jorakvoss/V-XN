#!/usr/bin/env python3
"""
vex_oled_pixel_eyes.py
Small OLED build for V-XN "Vex" with drawn pixel-art eyes.

Designed for a 128x64 0.96" SSD1306 I2C OLED, especially blue/yellow panels:
- Yellow area: top ~16 pixels. Vex keeps his eyes here.
- Blue area: lower ~48 pixels. Status/category/messages rotate here.

Run from the same project folder that contains data/messages.json and font5x8.bin.
"""

import argparse
import json
import random
import signal
import sys
import time
from datetime import datetime
from pathlib import Path
from textwrap import wrap

START_TIME = time.time()
OLED_WIDTH = 128
OLED_HEIGHT = 64
YELLOW_HEIGHT = 16
BLUE_START_Y = 17
CHARS_PER_LINE = 21
ROTATE_SECONDS = 25

# Each expression is drawn, not printed as text.
# Kept simple because 16px yellow band is tiny but glorious.
EYE_MOODS = {
    "observant": "OBSERVANT",
    "suspicious": "SUSPICIOUS",
    "unimpressed": "UNIMPRESSED",
    "excited": "EXCITED",
    "processing": "PROCESSING",
    "alert": "ALERT",
    "concerned": "CONCERNED",
    "budget": "BUDGET RISK",
    "pleased": "PLEASED",
    "scanning": "SCANNING",
    "glitchy": "GLITCHY",
    "judging": "JUDGING",
    "side_eye": "SIDE-EYE",
}

IDLE_EXPRESSIONS = [
    "observant",
    "suspicious",
    "unimpressed",
    "excited",
    "processing",
    "pleased",
    "scanning",
    "glitchy",
    "judging",
    "side_eye",
]


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def load_messages() -> dict:
    message_file = script_dir() / "data" / "messages.json"
    if not message_file.exists():
        raise FileNotFoundError(
            f"Could not find {message_file}. Put this script beside the data/ folder."
        )
    with open(message_file, "r", encoding="utf-8") as f:
        return json.load(f)


def center_text(text: str, width: int = CHARS_PER_LINE) -> str:
    return str(text)[:width].center(width)


def compact_text(text: str) -> str:
    return " ".join(str(text).replace("\n", " ").split())


def pick_message(data: dict, last_title: str | None, last_message: str | None):
    titles = ["STARTUP", "STATUS", "WARNING", "OBSERVATION", "FAMILY"]

    current_hour = datetime.now().hour
    if current_hour >= 23 or current_hour < 5:
        titles.append("LATENIGHT")

    for _ in range(5):
        if random.randint(1, 10) == 1:
            title = "PRIORITY"
            message = random.choice(data.get("priority", ["Priority queue empty. Suspicious."]))
        else:
            title = random.choice(titles)
            if title == "STARTUP":
                message = random.choice(data.get("startup", ["Systems nominal."]))
            elif title == "STATUS":
                message = random.choice(data.get("status", ["Monitoring local chaos."]))
            elif title == "WARNING":
                message = random.choice(data.get("warnings", ["Warning: Dad has ideas."]))
            elif title == "LATENIGHT":
                message = random.choice(data.get("latenight", ["Sleep protocol ignored."]))
            elif title == "FAMILY":
                message = random.choice(data.get("family", ["Family unit activity detected."]))
            else:
                message = random.choice(data.get("observations", ["Home Assistant is probably plotting something."]))

        if title != last_title or message != last_message:
            return title, message

    return title, message


def expression_for_title(title: str) -> str:
    if title == "PRIORITY":
        return "alert"
    if title == "WARNING":
        return "concerned"
    if title == "FAMILY":
        return "pleased"
    return random.choice(IDLE_EXPRESSIONS)


class TerminalOLED:
    """Fake OLED for testing over SSH without hardware."""

    def __init__(self):
        self.ops = []

    def fill(self, color):
        self.ops = []
        print("\033[H\033[2J\033[3J", end="")

    def text(self, text, x, y, color):
        print(f"y={y:02d} x={x:03d} | {text}")

    def line(self, x0, y0, x1, y1, color):
        print(f"y={y0:02d}        " + "-" * 21)

    def rect(self, x, y, w, h, color):
        print(f"rect x={x:03d} y={y:02d} w={w:02d} h={h:02d}")

    def fill_rect(self, x, y, w, h, color):
        print(f"fill x={x:03d} y={y:02d} w={w:02d} h={h:02d}")

    def pixel(self, x, y, color):
        pass

    def show(self):
        print(flush=True)


def init_oled(address: int, terminal: bool = False):
    if terminal:
        return TerminalOLED()

    import os
    import board
    import busio
    import adafruit_ssd1306

    # Adafruit framebuf expects font5x8.bin in current working directory.
    os.chdir(script_dir())

    i2c = busio.I2C(board.SCL, board.SDA)
    return adafruit_ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=address)


def draw_centered(oled, text: str, y: int, color: int = 1, width: int = CHARS_PER_LINE):
    oled.text(center_text(text, width), 0, y, color)


def draw_square_eye(oled, x: int, y: int, w: int = 10, h: int = 10, pupil: str = "center"):
    oled.rect(x, y, w, h, 1)
    if pupil == "left":
        oled.fill_rect(x + 2, y + 3, 3, 4, 1)
    elif pupil == "right":
        oled.fill_rect(x + w - 5, y + 3, 3, 4, 1)
    elif pupil == "up":
        oled.fill_rect(x + 4, y + 2, 3, 3, 1)
    else:
        oled.fill_rect(x + 4, y + 4, 3, 3, 1)


def draw_plus_eye(oled, x: int, y: int):
    oled.fill_rect(x + 4, y, 2, 10, 1)
    oled.fill_rect(x, y + 4, 10, 2, 1)


def draw_slit_eye(oled, x: int, y: int):
    oled.fill_rect(x, y + 5, 11, 2, 1)


def draw_chevron_eye(oled, x: int, y: int, direction: str):
    # Direction is "left", "right", "up", or "down".
    if direction == "left":
        for i in range(5):
            oled.pixel(x + i, y + 5 - i, 1)
            oled.pixel(x + i, y + 5 + i, 1)
    elif direction == "right":
        for i in range(5):
            oled.pixel(x + 10 - i, y + 5 - i, 1)
            oled.pixel(x + 10 - i, y + 5 + i, 1)
    elif direction == "up":
        for i in range(5):
            oled.pixel(x + 5 - i, y + 5 + i, 1)
            oled.pixel(x + 5 + i, y + 5 + i, 1)
    else:
        for i in range(5):
            oled.pixel(x + 5 - i, y + i, 1)
            oled.pixel(x + 5 + i, y + i, 1)


def draw_d_eye(oled, x: int, y: int):
    oled.fill_rect(x, y, 2, 10, 1)
    oled.rect(x, y, 8, 10, 1)


def draw_eyes(oled, expression: str):
    # Coordinates tuned for your yellow band and current screen mount.
    left_x = 38
    right_x = 84
    y = 3

    if expression == "processing":
        draw_plus_eye(oled, left_x, y)
        draw_plus_eye(oled, right_x, y)
    elif expression == "unimpressed":
        draw_slit_eye(oled, left_x, y)
        draw_slit_eye(oled, right_x, y)
    elif expression == "alert":
        draw_square_eye(oled, left_x, y, pupil="center")
        draw_square_eye(oled, right_x, y, pupil="center")
    elif expression == "concerned":
        draw_d_eye(oled, left_x, y)
        draw_d_eye(oled, right_x, y)
    elif expression == "pleased":
        draw_chevron_eye(oled, left_x, y, "up")
        draw_chevron_eye(oled, right_x, y, "up")
    elif expression == "scanning":
        draw_chevron_eye(oled, left_x, y, "left")
        draw_chevron_eye(oled, right_x, y, "right")
    elif expression == "judging":
        draw_chevron_eye(oled, left_x, y, "right")
        draw_chevron_eye(oled, right_x, y, "right")
    elif expression == "side_eye":
        draw_square_eye(oled, left_x, y, pupil="left")
        draw_square_eye(oled, right_x, y, pupil="left")
    elif expression == "suspicious":
        draw_square_eye(oled, left_x, y, pupil="right")
        draw_square_eye(oled, right_x, y, pupil="left")
    elif expression == "excited":
        draw_plus_eye(oled, left_x, y)
        draw_square_eye(oled, right_x, y, pupil="center")
    elif expression == "budget":
        oled.text("$", left_x + 2, y + 1, 1)
        oled.text("$", right_x + 2, y + 1, 1)
    elif expression == "glitchy":
        oled.text("~", left_x + 2, y + 1, 1)
        oled.text("~", right_x + 2, y + 1, 1)
    else:
        draw_square_eye(oled, left_x, y, pupil="center")
        draw_square_eye(oled, right_x, y, pupil="center")


def draw_vex(oled, title: str, message: str, expression: str, display_title: str):
    oled.fill(0)

    # Yellow zone: eyes only. No mood text here, so his face gets the whole band.
    draw_eyes(oled, expression)

    # Divider between yellow and blue areas.
    oled.line(0, YELLOW_HEIGHT, OLED_WIDTH - 1, YELLOW_HEIGHT, 1)

    # Blue zone: status/category/message. The eyes show the mood; text tells the story.
    now = datetime.now().strftime("%H:%M")
    mood = EYE_MOODS.get(expression, "OBSERVANT")

    draw_centered(oled, display_title, 19)
    draw_centered(oled, mood, 28)

    clean_message = compact_text(message)
    message_lines = wrap(clean_message, width=CHARS_PER_LINE)

    visible = message_lines[:3]
    if len(message_lines) > 3 and visible:
        visible[-1] = visible[-1][: max(0, CHARS_PER_LINE - 3)] + "..."

    y = 38
    for line in visible:
        draw_centered(oled, line, y)
        y += 9

    if not visible:
        draw_centered(oled, f"VEX // {now}", 38)

    oled.show()


def show_loading(oled, data: dict):
    loading = data.get("loading", ["Initializing snark emitter.", "Vex online."])
    if len(loading) > 1:
        boot_messages = random.sample(loading[:-1], min(3, len(loading) - 1))
        boot_messages.append(loading[-1])
    else:
        boot_messages = loading

    for msg in boot_messages:
        draw_vex(
            oled=oled,
            title="STARTUP",
            message=msg,
            expression="processing",
            display_title="INITIALIZING",
        )
        time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description="V-XN Vex OLED display loop with pixel-art eyes")
    parser.add_argument("--address", default="0x3C", help="OLED I2C address, usually 0x3C")
    parser.add_argument("--interval", type=int, default=ROTATE_SECONDS, help="Seconds between messages")
    parser.add_argument("--terminal", action="store_true", help="Preview output in terminal instead of OLED")
    args = parser.parse_args()

    address = int(str(args.address), 16) if str(args.address).lower().startswith("0x") else int(args.address)
    data = load_messages()
    oled = init_oled(address=address, terminal=args.terminal)

    shutdown_messages = data.get("shutdown", ["Shutdown acknowledged."])

    def shutdown_handler(signum, frame):
        try:
            oled.fill(0)
            draw_eyes(oled, "unimpressed")
            oled.line(0, YELLOW_HEIGHT, OLED_WIDTH - 1, YELLOW_HEIGHT, 1)
            draw_centered(oled, "VEX OFFLINE", 22)
            draw_centered(oled, random.choice(shutdown_messages), 34)
            oled.show()
            time.sleep(1)
            oled.fill(0)
            oled.show()
        finally:
            sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    show_loading(oled, data)

    last_title = None
    last_message = None

    while True:
        title, message = pick_message(data, last_title, last_message)
        last_title, last_message = title, message

        expression = expression_for_title(title)
        display_title = data.get("display_titles", {}).get(title, title)
        subsystem = random.choice(data.get("subsystems", ["SNARK EMITTER OK"]))

        if random.randint(1, 6) == 1:
            message = f"{message} // {subsystem}"

        draw_vex(oled, title, message, expression, display_title)
        time.sleep(args.interval)


if __name__ == "__main__":
    main()
