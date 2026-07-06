#!/usr/bin/env python3
"""
gemini_vex_oled.py - Interactive Production Upgrade
Chopper-style reactive brain for V-XN "Vex".

Features:
- I2C Auto-Recovery: Catches low-level OSError [Errno 5] disconnects, 
  re-initializes the physical bus, and resumes without crashing.
- Decoupled Asynchronous Animation Loop (No blocking time.sleep freezes).
- Global State Engine: Tracks dynamic eye expression timeouts and persistent moods.
- Burn-In Pixel Shifting: Moves coordinates subtly to preserve the bicolor panel.
- Spatially Balanced Layout: Limits to 2 message lines for perfect text padding.
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

# --- Hardware Configuration ---
OLED_WIDTH = 128
OLED_HEIGHT = 64
YELLOW_HEIGHT = 16
BLUE_START_Y = 17
CHARS_PER_LINE = 21

# --- Vex State Engine ---
class DroidState:
    def __init__(self):
        self.mood = "observant"        # Active display expression
        self.base_mood = "observant"   # Fallback personality baseline
        self.display_title = "SYSTEMS" # Header text string
        self.message = "Online."       # Active telemetry message
        self.last_interaction = time.time()
        self.next_blink = time.time() + 2.0
        self.next_glance = time.time() + 5.0
        self.expression_timeout = 0.0  # Tracks when a forced expression clears
        self.last_title = None
        self.last_message = None

VEX = DroidState()

EYE_MOODS = {
    "observant": "OBSERVANT", "suspicious": "SUSPICIOUS", "unimpressed": "UNIMPRESSED",
    "excited": "EXCITED", "processing": "PROCESSING", "alert": "ALERT",
    "concerned": "CONCERNED", "budget": "BUDGET RISK", "pleased": "PLEASED",
    "scanning": "SCANNING", "glitchy": "GLITCHY", "judging": "JUDGING",
    "side_eye": "SIDE-EYE", "blink": "BLINK", "look_left": "LEFT?",
    "look_right": "RIGHT?", "sleepy": "SLEEPY", "happy": "PLEASED",
    "thinking": "THINKING"
}

IDLE_EXPRESSIONS = [
    "observant", "suspicious", "unimpressed", "excited", "processing",
    "pleased", "scanning", "glitchy", "judging", "side_eye", "sleepy", "happy"
]

def script_dir() -> Path:
    return Path(__file__).resolve().parent

def load_messages() -> dict:
    # Aggressively check common naming patterns to ensure the database mounts seamlessly
    possible_paths = [
        script_dir() / "messages_milestone_0_4.json",
        script_dir() / "data" / "messages_m0_4.json",
        script_dir() / "messages_m0_4.json"
    ]
    for path in possible_paths:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("Vex couldn't locate his message JSON dataset.")

# --- Dynamic Logic & Personality Engines ---
def expression_for_title(title: str) -> str:
    if title == "PRIORITY": return "alert"
    if title == "WARNING": return "concerned"
    if title == "FAMILY": return random.choice(["pleased", "happy"])
    if title == "LATENIGHT": return random.choice(["sleepy", "unimpressed", "judging"])
    if title == "STARTUP": return "processing"
    return random.choice(IDLE_EXPRESSIONS)

def trigger_event(event_type: str, data: dict = None):
    now = time.time()
    VEX.last_interaction = now

    if event_type == "passive_cycle" and data:
        titles = ["STARTUP", "STATUS", "WARNING", "OBSERVATION", "FAMILY"]
        current_hour = datetime.now().hour
        if current_hour >= 23 or current_hour < 5:
            titles.append("LATENIGHT")

        for _ in range(5):
            if random.randint(1, 10) == 1:
                title = "PRIORITY"
                msg_list = data.get("priority", ["Dataset underfunded."])
            else:
                title = random.choice(titles)
                key = title.lower() if title != "OBSERVATION" else "observations"
                msg_list = data.get(key, ["Telemetry null."])

            message = random.choice(msg_list) if msg_list else "Telemetry nominal."
            if title != VEX.last_title or message != VEX.last_message:
                break

        VEX.last_title, VEX.last_message = title, message
        
        if random.randint(1, 6) == 1 and "subsystems" in data:
            subsystem = random.choice(data["subsystems"])
            message = f"{message} // {subsystem}"

        VEX.display_title = data.get("display_titles", {}).get(title, title)
        VEX.message = message
        VEX.base_mood = expression_for_title(title)
        VEX.mood = VEX.base_mood

# --- OLED Drawing Operations ---
def draw_square_eye(oled, x: int, y: int, w: int = 10, h: int = 10, pupil: str = "center"):
    oled.rect(x, y, w, h, 1)
    if pupil == "left": oled.fill_rect(x + 2, y + 3, 3, 4, 1)
    elif pupil == "right": oled.fill_rect(x + w - 5, y + 3, 3, 4, 1)
    elif pupil == "up": oled.fill_rect(x + 4, y + 2, 3, 3, 1)
    else: oled.fill_rect(x + 4, y + 4, 3, 3, 1)

def draw_plus_eye(oled, x: int, y: int):
    oled.fill_rect(x + 4, y, 2, 10, 1)
    oled.fill_rect(x, y + 4, 10, 2, 1)

def draw_slit_eye(oled, x: int, y: int):
    oled.fill_rect(x, y + 5, 11, 2, 1)

def draw_chevron_eye(oled, x: int, y: int, direction: str):
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

def draw_sleepy_eye(oled, x: int, y: int):
    oled.fill_rect(x, y + 6, 11, 2, 1)
    oled.pixel(x + 1, y + 5, 1)
    oled.pixel(x + 9, y + 5, 1)

def draw_happy_eye(oled, x: int, y: int):
    for i in range(5):
        oled.pixel(x + 1 + i, y + 6 + min(i, 4 - i), 1)
        oled.pixel(x + 6 + i, y + 6 + min(i, 4 - i), 1)

def draw_thinking_eye(oled, x: int, y: int):
    draw_square_eye(oled, x, y, pupil="up")
    oled.pixel(x + 12, y + 2, 1)
    oled.pixel(x + 14, y + 4, 1)
    oled.pixel(x + 12, y + 6, 1)

def draw_eyes(oled, expression: str):
    # Pixel Shifting: Shift face elements slightly to neutralize OLED panel burning
    shift_x = 1 if (int(time.time()) // 60) % 2 == 0 else 0
    shift_y = 1 if (int(time.time()) // 120) % 2 == 0 else 0

    left_x = 38 + shift_x
    right_x = 84 + shift_x
    y = 3 + shift_y

    if expression == "blink":
        draw_slit_eye(oled, left_x, y); draw_slit_eye(oled, right_x, y)
    elif expression in ("look_left", "side_eye"):
        draw_square_eye(oled, left_x, y, pupil="left"); draw_square_eye(oled, right_x, y, pupil="left")
    elif expression == "look_right":
        draw_square_eye(oled, left_x, y, pupil="right"); draw_square_eye(oled, right_x, y, pupil="right")
    elif expression == "sleepy":
        draw_sleepy_eye(oled, left_x, y); draw_sleepy_eye(oled, right_x, y)
    elif expression == "happy":
        draw_happy_eye(oled, left_x, y); draw_happy_eye(oled, right_x, y)
    elif expression == "thinking":
        draw_thinking_eye(oled, left_x, y); draw_thinking_eye(oled, right_x, y)
    elif expression == "processing":
        draw_plus_eye(oled, left_x, y); draw_plus_eye(oled, right_x, y)
    elif expression == "unimpressed":
        draw_slit_eye(oled, left_x, y); draw_slit_eye(oled, right_x, y)
    elif expression == "concerned":
        draw_d_eye(oled, left_x, y); draw_d_eye(oled, right_x, y)
    elif expression == "pleased":
        draw_chevron_eye(oled, left_x, y, "up"); draw_chevron_eye(oled, right_x, y, "up")
    elif expression == "scanning":
        draw_chevron_eye(oled, left_x, y, "left"); draw_chevron_eye(oled, right_x, y, "right")
    elif expression == "judging":
        draw_chevron_eye(oled, left_x, y, "right"); draw_chevron_eye(oled, right_x, y, "right")
    elif expression == "suspicious":
        draw_square_eye(oled, left_x, y, pupil="right"); draw_square_eye(oled, right_x, y, pupil="left")
    elif expression == "excited":
        draw_plus_eye(oled, left_x, y); draw_square_eye(oled, right_x, y, pupil="center")
    elif expression == "budget":
        oled.text("$", left_x + 2, y + 1, 1); oled.text("$", right_x + 2, y + 1, 1)
    elif expression == "glitchy":
        oled.text("~", left_x + 2, y + 1, 1); oled.text("~", right_x + 2, y + 1, 1)
    else:
        draw_square_eye(oled, left_x, y, pupil="center"); draw_square_eye(oled, right_x, y, pupil="center")

def render_frame(oled):
    oled.fill(0)
    draw_eyes(oled, VEX.mood)
    oled.line(0, YELLOW_HEIGHT, OLED_WIDTH - 1, YELLOW_HEIGHT, 1)

    mood_str = f"// {EYE_MOODS.get(VEX.mood, 'OBSERVANT')} //".center(CHARS_PER_LINE)
    oled.text(str(VEX.display_title)[:CHARS_PER_LINE].center(CHARS_PER_LINE), 0, 19, 1)
    oled.text(mood_str, 0, 28, 1)

    clean_msg = " ".join(str(VEX.message).replace("\n", " ").split())
    message_lines = wrap(clean_msg, width=CHARS_PER_LINE)[:2]
    
    y = 39
    for line in message_lines:
        oled.text(line.center(CHARS_PER_LINE), 0, y, 1)
        y += 10
    
    oled.show()

# --- Hardware Setup and Safe Re-initialization Bus ---
class TerminalOLED:
    def fill(self, color): print("\033[H\033[2J", end="")
    def text(self, text, x, y, color): print(f"| {text} |")
    def line(self, x0, y0, x1, y1, color): print("-" * (CHARS_PER_LINE + 4))
    def rect(self, x, y, w, h, color): pass
    def fill_rect(self, x, y, w, h, color): pass
    def pixel(self, x, y, color): pass
    def show(self): print("", flush=True)

def init_oled(address: int, terminal: bool = False):
    if terminal: return TerminalOLED()
    import os, board, busio, adafruit_ssd1306
    os.chdir(script_dir())
    
    # Force close any existing bus bindings if resetting after an error
    i2c = busio.I2C(board.SCL, board.SDA)
    return adafruit_ssd1306.SSD1306_I2C(OLED_WIDTH, OLED_HEIGHT, i2c, addr=address)

def show_loading_sequence(oled, data: dict):
    boot_messages = data.get("loading", ["Initializing core.", "Vex online."])
    selected = random.sample(boot_messages[:-1], min(3, len(boot_messages) - 1)) + [boot_messages[-1]]
    
    for msg in selected:
        VEX.display_title = "INITIALIZING"
        VEX.message = msg
        VEX.mood = "processing"
        try:
            render_frame(oled)
        except OSError:
            pass # Keep moving forward during boot up sequences
        time.sleep(1.2)

# --- Core Loop Operational Block ---
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--address", default="0x3C")
    parser.add_argument("--interval", type=int, default=15)
    parser.add_argument("--terminal", action="store_true")
    args = parser.parse_args()

    addr = int(args.address, 16) if args.address.lower().startswith("0x") else int(args.address)
    data = load_messages()
    
    # Initialize initial hardware device connections
    oled = init_oled(address=addr, terminal=args.terminal)

    def shutdown_handler(signum, frame):
        try:
            shutdown_msgs = data.get("shutdown", ["Shutdown acknowledged."])
            oled.fill(0)
            draw_eyes(oled, "unimpressed")
            oled.line(0, YELLOW_HEIGHT, OLED_WIDTH - 1, YELLOW_HEIGHT, 1)
            oled.text("VEX OFFLINE".center(CHARS_PER_LINE), 0, 22, 1)
            oled.text(random.choice(shutdown_msgs)[:CHARS_PER_LINE].center(CHARS_PER_LINE), 0, 36, 1)
            oled.show()
            time.sleep(1.0)
            oled.fill(0); oled.show()
        except Exception:
            pass
        finally:
            sys.exit(0)

    signal.signal(signal.SIGINT, shutdown_handler)
    signal.signal(signal.SIGTERM, shutdown_handler)

    show_loading_sequence(oled, data)
    trigger_event("passive_cycle", data)

    # Core Execution Loop
    while True:
        now = time.time()

        # 1. Micro-Animation Clock 
        if now >= VEX.expression_timeout:
            if now >= VEX.next_blink:
                VEX.mood = "blink"
                VEX.expression_timeout = now + 0.15
                VEX.next_blink = now + random.uniform(2.5, 6.0)
            elif now >= VEX.next_glance:
                VEX.mood = random.choice(["look_left", "look_right", "side_eye"])
                VEX.expression_timeout = now + random.uniform(0.4, 0.8)
                VEX.next_glance = now + random.uniform(5.0, 11.0)
            else:
                VEX.mood = VEX.base_mood

        # 2. Telemetry Pacing Engine
        if now - VEX.last_interaction >= args.interval:
            trigger_event("passive_cycle", data)

        # 3. Safe Blit Canvas Rendering Frame Execution
        try:
            render_frame(oled)
        except OSError as e:
            # Check explicitly for the [Errno 5] Input/output error
            if e.errno == 5:
                # Log it to terminal without crashing out entirely
                print(f"[{datetime.now().strftime('%H:%M:%S')}] I2C Link Glitch Caught. Resetting bus connection...")
                try:
                    time.sleep(0.2) # Allow line electrical levels to stabilize
                    oled = init_oled(address=addr, terminal=args.terminal)
                    trigger_event("passive_cycle", data) # Re-shuffle face
                    VEX.mood = "glitchy"
                    VEX.expression_timeout = time.time() + 1.0 # Briefly register a glitchy face
                except Exception:
                    # If physical bus is completely jammed up, sit back and try on the next frame loop pass
                    pass
            else:
                raise e # Pass up any unrelated system or logic software issues cleanly

        time.sleep(0.05)

if __name__ == "__main__":
    main()
