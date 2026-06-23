#!/usr/bin/env python3

import os
import random
import time
import json
from pathlib import Path

DISPLAY_WIDTH = 60
BLOCK_HEIGHT = 9
TERM_WIDTH = os.get_terminal_size().columns

EYE_PATTERNS = [
    "[o   o]",
    "[o   O]",
    "[-   -]",
    "[*   *]",
    "[+   +]",
    "[O - O]",
    "[D - D]"
]

LOADING_MESSAGES = [
    "Initializing systems...",
    "Loading personaily matrix...",
    "Calibrating sarcasm...",
    "Checking coffee reserves...",
    "Scanning local network...",
    "Boot sequence complete."
]

message_file = Path("data/messages.json")

with open(message_file, "r") as f:
    data = json.load(f)

startup = data["startup"]
status = data["status"]
warnings = data["warnings"]
observations = data["observations"]

TERM_HEIGHT = os.get_terminal_size().lines
TOP_PADDING = max(0, (TERM_HEIGHT - BLOCK_HEIGHT) //2)

def print_centered(line=""):
    print(line.center(DISPLAY_WIDTH).center(TERM_WIDTH))

def print_screen(lines):
    for line in lines:
        print_centered(line)

def clear_screen():
    print("\033[H\033[2J\033[3J", end="", flush=True)

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

        time.sleep(1)

show_loading_screen()

while True:

    os.system("clear")
    EYES = random.choice(EYE_PATTERNS)

    for _ in range(TOP_PADDING):
        print()

    title = random.choice([
    "STARTUP",
    "STATUS",
    "WARNING",
    "OBSERVATION"
])

    if title == "STARTUP":
        message = random.choice(startup)
    elif title == "STATUS":
        message = random.choice(status)
    elif title == "WARNING":
        message = random.choice(warnings)
    else:
        message = random.choice(observations)

    divider = "=" * DISPLAY_WIDTH

    main_screen = [
        divider,
        "",
        EYES,
        "",
        "V-XN ASTROMECH",
        "",
        divider,
        "",
        title,
        "",
        message,
        "",
        divider
]

    print_screen(main_screen)

    time.sleep(10)
