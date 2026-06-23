#!/usr/bin/env python3

import os
import random
import time
import json
from pathlib import Path

message_file = Path("data/messages.json")

with open(message_file, "r") as f:
    data = json.load(f)

startup = data["startup"]
status = data["status"]
warnings = data["warnings"]

while True:

    os.system("clear")

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

    print("=" * 40)
    print()
    print("            V-XN ASTROMECH")
    print()
    print("=" * 40)
    print()
    print(f"  {title}")
    print()
    print(f"  {message}")
    print()
    print("=" * 40)

    time.sleep(10)
