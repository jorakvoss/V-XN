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
BLOCK_HEIGHT = 9
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

LOADING_MESSAGES = [
    "Initializing systems...",
    "Loading personality matrix...",
    "Calibrating sarcasm...",
    "Checking coffee reserves...",
    "Scanning local network...",
    "Synchronizing temporal awareness...",
    "Checking static IP confidence...",
    "Reminding DHCP to stay away...",
    "Warming sarcasm coils...",
    "Boot sequence complete."
]

message_file = Path("data/messages.json")

with open(message_file, "r") as f:
    data = json.load(f)

startup = data["startup"]
status = data["status"]
warnings = data["warnings"]
observations = data["observations"]
latenight = data["latenight"]
shutdown = data["shutdown"]

TERM_HEIGHT = os.get_terminal_size().lines
TOP_PADDING = max(0, (TERM_HEIGHT - BLOCK_HEIGHT) //2)

def print_centered(line=""):
    print(line.center(DISPLAY_WIDTH).center(TERM_WIDTH), flush=True)

def print_screen(lines):
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
    for loading_message in LOADING_MESSAGES:
        clear_screen()
    
        for _ in range(TOP_PADDING):
            print()

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

while True:

    clear_screen()
    EYES = random.choice(EYE_PATTERNS)

    for _ in range(TOP_PADDING):
        print()

    titles = [
    "STARTUP",
    "STATUS",
    "WARNING",
    "OBSERVATION"
    ]

    current_hour = datetime.now().hour

    if current_hour >=23 or current_hour <5:
        titles.append("LATENIGHT")

    title = random.choice(titles)
    if title == "STARTUP":
        message = random.choice(startup)
    elif title == "STATUS":
        message = random.choice(status)
    elif title == "WARNING":
        message = random.choice(warnings)
    elif title == "LATENIGHT":
        message = random.choice(latenight)
    else:
        message = random.choice(observations)

    divider = "=" * DISPLAY_WIDTH

    current_time = datetime.now().strftime("%H:%M")
    current_date = datetime.now().strftime("%a, %b %d, %Y")
    uptime_seconds = int(time.time() - START_TIME)
    uptime = time.strftime("%H:%M:%S", time.gmtime(uptime_seconds))

    messages_lines = wrap(message, width=DISPLAY_WIDTH - 4)

    main_screen = [
        divider,
        "",
        EYES,
        "",
        "V-XN ASTROMECH",
        current_time,
        current_date,
        "",
        divider,
        "",
        title,
        "",
        message,
        "",
        divider,
        "",
        "",
        f"UPTIME {uptime}"
    ]

    print_screen(main_screen)

    time.sleep(10)
