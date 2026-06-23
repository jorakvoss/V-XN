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
    "[+   +]"
]

message_file = Path("data/messages.json")

with open(message_file, "r") as f:
    data = json.load(f)

startup = data["startup"]
status = data["status"]
warnings = data["warnings"]

TERM_HEIGHT = os.get_terminal_size().lines
TOP_PADDING = max(0, (TERM_HEIGHT - BLOCK_HEIGHT) //2)

while True:

    os.system("clear")
    EYES = random.choice(EYE_PATTERNS)

    for _ in range(TOP_PADDING):
        print()

    title = random.choice([
    "STARTUP",
    "STATUS",
    "WARNING"
])

    if title == "STARTUP":
        message = random.choice(startup)
    elif title == "STATUS":
        message = random.choice(status)
    else:
        message = random.choice(warnings)

    divider = "=" * DISPLAY_WIDTH

    print(divider.center(TERM_WIDTH))
    print()
    print(EYES.center(DISPLAY_WIDTH).center(TERM_WIDTH))
    print()
    print("V-XN ASTROMECH".center(DISPLAY_WIDTH).center(TERM_WIDTH))
    print()
    print(divider.center(TERM_WIDTH))
    print()
    print(title.center(DISPLAY_WIDTH).center(TERM_WIDTH))
    print()
    print(message.center(DISPLAY_WIDTH).center(TERM_WIDTH))
    print()
    print(divider.center(TERM_WIDTH))

    time.sleep(10)
