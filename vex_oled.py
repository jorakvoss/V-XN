#!/usr/bin/env python3
"""
vex_oled.py
Small OLED build for V-XN "Vex".

Designed for a 128x64 0.96" SSD1306 I2C OLED, especially the common
blue/yellow two-color panels:
- Top/yellow area: Vex eyes stay here, always.
- Lower/blue area: mood/status/message rotates here.

Run from the same Vex project folder that contains data/messages.json.
Example:
  source vex-venv/bin/activate
  python3 vex_oled.py

Test over SSH without OLED:
  python3 vex_oled.py --terminal
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
BLUE_START_Y = 18
CHARS_PER_LINE = 21
ROTATE_SECONDS = 25

# Tiny OLED-friendly eyes. These are intentionally short so they fit the yellow band.
EYE_PATTERNS = {
    "OBSERVANT": ("o", "o"),
    "SUSPICIOUS": ("o", "O"),
    "UNIMPRESSED": ("-", "-"),
    "EXCITED": ("*", "*"),
    "PROCESSING": ("+", "+"),
    "ALERT": ("O", "O"),
    "CONCERNED": ("D", "D"),
    "BUDGET RISK": ("$", "$"),
    "PLEASED": ("^", "^"),
    "SCANNING": ("<", ">"),
    "GLITCHY": ("~", "~"),
    "JUDGING": (">", ">"),
    "SIDE-EYE": ("<", "<"),
    "SLEEPY": (".", "."),
}

TITLE_MOODS = {
    "PRIORITY": "ALERT",
    "WARNING": "CONCERNED",
    "FAMILY": "SUSPICIOUS",
    "LATENIGHT": "SLEEPY",
    "STATUS": "OBSERVANT",
    "STARTUP": "PROCESSING",
    "OBSERVATION": "SCANNING",
}


def script_dir() -> Path:
    return Path(__file__).resolve().parent


def load_messages() -> dict:
    message_file = script_dir() / "data" / "messages.json"
    if not message_file.exists():
        raise FileNotFoundError(
            f"Could not find {message_file}. Put vex_oled.py in the same folder "
            "as your data/ folder, then run it from there."
        )

    with open(message_file, "r", encoding="utf-8") as f:
        return json.load(f)


def compact_text(text: str) -> str:
    return " ".join(str(text).replace("\n", " ").split())


def center_text_for_oled(text: str, width: int = CHARS_PER_LINE) -> str:
    return str(text)[:width].center(width)


def pixel_center_x(text: str) -> int:
    # Adafruit's default font is roughly 6 pixels wide per character.
    return max(0, (OLED_WIDTH - (len(str(text)) * 6)) // 2)


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


class TerminalOLED:
    """Fake OLED preview for SSH testing without hardware."""

    def __init__(self):
        self.lines = []

    def fill(self, color):
        self.lines = []
        print("\033[H\033[2J\033[3J", end="")

    def text(self, text, x, y, color):
        self.lines.append((y, x, text))

    def line(self, x0, y0, x1, y1, color):
        self.lines.append((y0, 0, "-" * CHARS_PER_LINE))

    def show(self):
        for y, x, text in sorted(self.lines):
            print(f"y={y:02d} x={x:03d} | {text}")
        print(flush=True)


def init_oled(address: int, terminal: bool = False):
    if terminal:
        return TerminalOLED()

    import os
    import board
    import busio
    import adafruit_ssd1306

    # Adafruit framebuf looks for font5x8.bin in the current working directory.
    os.chdir(script_dir())

    i2c = busio.I2C(board.SCL, board.SDA)
    return adafruit_ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=address)


def draw_centered(oled, text: str, y: int, color: int = 1):
    oled.text(str(text)[:CHARS_PER_LINE], pixel_center_x(str(text)[:CHARS_PER_LINE]), y, color)


def draw_eyes(oled, mood: str):
    left_eye, right_eye = EYE_PATTERNS.get(mood, EYE_PATTERNS["OBSERVANT"])

    # Top/yellow band. Keep the eyes there no matter what else changes.
    oled.text(left_eye, 38, 4, 1)
    oled.text(right_eye, 86, 4, 1)


def draw_vex(oled, title: str, message: str, mood: str, display_title: str):
    oled.fill(0)

    # Always-on eyes in the yellow area.
    draw_eyes(oled, mood)

    # Divider between yellow and blue sections.
    oled.line(0, YELLOW_HEIGHT, OLED_WIDTH - 1, YELLOW_HEIGHT, 1)

    # Blue area: centered mood/status/message.
    now = datetime.now().strftime("%H:%M")
    draw_centered(oled, mood, 20)
    draw_centered(oled, display_title, 30)

    clean_message = compact_text(message)
    message_lines = wrap(clean_message, width=CHARS_PER_LINE)

    visible = message_lines[:2]
    if len(message_lines) > 2 and visible:
        visible[-1] = visible[-1][: max(0, CHARS_PER_LINE - 3)] + "..."

    y = 42
    for line in visible:
        draw_centered(oled, line, y)
        y += 10

    # Tiny time stamp, only if there is room.
    if not visible:
        draw_centered(oled, f"VEX // {now}", 44)

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
            mood="PROCESSING",
            display_title="INITIALIZING",
        )
        time.sleep(2)


def main():
    parser = argparse.ArgumentParser(description='V-XN "Vex" OLED display loop')
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
            draw_eyes(oled, "SLEEPY")
            oled.line(0, YELLOW_HEIGHT, OLED_WIDTH - 1, YELLOW_HEIGHT, 1)
            draw_centered(oled, "VEX OFFLINE", 24)
            draw_centered(oled, random.choice(shutdown_messages), 38)
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

        display_title = data.get("display_titles", {}).get(title, title)
        mood = TITLE_MOODS.get(title, random.choice(list(EYE_PATTERNS.keys())))

        if random.randint(1, 6) == 1:
            subsystem = random.choice(data.get("subsystems", ["SNARK EMITTER OK"]))
            message = f"{message} // {subsystem}"

        draw_vex(
            oled=oled,
            title=title,
            message=message,
            mood=mood,
            display_title=display_title,
        )

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
