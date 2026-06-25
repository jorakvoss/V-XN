#!/usr/bin/env python3

import os
import random
import time
import json
import sys
import signal
from pathlib import Path
from datetime import datetime
from textwrap import wrap

DISPLAY_WIDTH = 60
TERM_WIDTH = os.get_terminal_size().columns
START_TIME = time.time()

EYE_PATTERNS = [
    "[o   o]",
    "[o   O]",
    "[-   -]",
    "[*   *]",
    "[+   +]",
    "[O - O]",
    "[D - D]",
    "[$ - $]",
    "[^ - ^]",
    "[< - >]",
    "[~ - ~]",
    "[> - >]",
    "[< - <]"
]

EYE_MOODS = {
    "[o   o]": "OBSERVANT",
    "[o   O]": "SUSPICIOUS",
    "[-   -]": "UNIMPRESSED",
    "[*   *]": "EXCITED",
    "[+   +]": "PROCESSING",
    "[O - O]": "ALERT",
    "[D - D]": "CONCERNED",
    "[$ - $]": "BUDGET RISK",
    "[^ - ^]": "PLEASED",
    "[< - >]": "SCANNING",
    "[~ - ~]": "GLITCHY",
    "[> - >]": "JUDGING",
    "[< - <]": "SIDE-EYE"
}

message_file = Path("data/messages.json")

with open(message_file, "r") as f:
    data = json.load(f)

startup = data["startup"]
status = data["status"]
warnings = data["warnings"]
observations = data["observations"]
latenight = data["latenight"]
shutdown = data["shutdown"]
loading = data["loading"]
beeps = data["beeps"]
priority = data["priority"]
family = data["family"]

DISPLAY_TITLES = data["display_titles"]

def print_centered(line=""):
    print(line.center(DISPLAY_WIDTH).center(TERM_WIDTH), flush=True)

def print_screen(lines):
    term_height = os.get_terminal_size().lines
    top_padding = max(0, (term_height - len(lines)) //2)

    for _ in range(top_padding):
        print()

    for line in lines:
        print_centered(line)

def clear_screen():
    print("\033[H\033[2J\033[3J", end="", flush=True)

def shutdown_handler(signum, frame):
    clear_screen()
    print("\033[?25h", end="", flush=True)
    print()
    print(f"V-XN: {random.choice(shutdown)}")
    print()
    sys.exit(0)

signal.signal(signal.SIGINT, shutdown_handler)

print("\033[?25l", end="", flush=True)

def show_loading_screen():
    divider = "=" * DISPLAY_WIDTH
    for loading_message in loading:
        clear_screen()

        eyes = random.choice(EYE_PATTERNS)

        loading_screen = [
            divider,
            "",
            eyes,
            "",
            "V-XN ASTROMECH",
            "",
            divider,
            "",
            "INITIALIZING",
            "",
            loading_message,
            "",
            divider
        ]

        print_screen(loading_screen)

        time.sleep(2)

show_loading_screen()

last_title = None
last_message = None

while True:

    clear_screen()
    EYES = random.choice(EYE_PATTERNS)
    BEEP = random.choice(beeps)

    titles = [
    "STARTUP",
    "STATUS",
    "WARNING",
    "OBSERVATION",
    "FAMILY"
    ]

    current_hour = datetime.now().hour

    if current_hour >=23 or current_hour <5:
        titles.append("LATENIGHT")

    for _ in range(5):
        if random.randint(1, 10) == 1:
            title = "PRIORITY"
            message = random.choice(priority)
        else:
            title = random.choice(titles)

            if title == "STARTUP":
                message = random.choice(startup)
            elif title == "STATUS":
                message = random.choice(status)
            elif title == "WARNING":
                message = random.choice(warnings)
            elif title == "LATENIGHT":
                message = random.choice(latenight)
            elif title == "FAMILY":
                message = random.choice(family)
            else:
                message = random.choice(observations)

        if title != last_title or message != last_message:
            break

    last_title = title
    last_message = message

    if title == "PRIORITY":
        EYES = "[O - O]"
    elif title == "WARNING":
        EYES = "[D - D]"
    elif title == "FAMILY":
        EYES = "[o O]"

    MOOD = EYE_MOODS.get(EYES, "UNKNOWN")

    divider = "=" * DISPLAY_WIDTH

    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%a, %b %d, %Y")
    uptime_seconds = int(time.time() - START_TIME)
    uptime = time.strftime("%H:%M:%S", time.gmtime(uptime_seconds))

    message_lines = wrap(message, width=DISPLAY_WIDTH - 4)
    display_title = DISPLAY_TITLES.get(title, title)

    main_screen = [
        divider,
        "",
        EYES,
        BEEP,
        f"MOOD: {MOOD}",
        "",
        'V-XN "VEX" ASTROMECH',
        "COMMAND NODE // LOCAL",
        "",
        current_time,
        current_date,
        "",
        divider,
        "",
        display_title,
        "",
        *message_lines,
        "",
        divider,
        "",
        "",
        f"UPTIME {uptime}"
    ]

    print_screen(main_screen)

    time.sleep(25)
