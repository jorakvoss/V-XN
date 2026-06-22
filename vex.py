#!/usr/bin/env python3

import os
import random
import time

messages = [
    ("NETWORK", "ALL SYSTEMS NOMINAL"),
    ("COFFEE", "REFILL RECOMMENDED"),
    ("CAMTONO", "CREDITS LOW"),
    ("TEMU", "WALLET IN DANGER"),
    ("PRINTER", "DO NOT TOUCH"),
    ("STATUS", "CHECK DNS"),
]

while True:

    os.system("clear")

    title, message = random.choice(messages)

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

    time.sleep(5)
