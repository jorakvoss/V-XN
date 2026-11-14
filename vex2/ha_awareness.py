
#!/usr/bin/env python3
"""
V-XN Home Assistant Awareness
Local, read-only status interpretation.

No HA credentials, network access, or device control.
"""

import json
import random
from datetime import datetime, timezone, timedelta
from pathlib import Path

BASE = Path(__file__).resolve().parent
STATUS_FILE = BASE / "ha_monitor/status.json"
MEMORY_FILE = BASE / "ha_monitor/awareness_state.json"

MAX_AGE_SECONDS = 180
REMINDER_HOURS = 24
CONFIRM_READINGS = 2


def utcnow():
    return datetime.now(timezone.utc)


def save_json(path, data):
    temp = path.with_suffix(".json.tmp")
    temp.write_text(json.dumps(data, indent=2), encoding="utf-8")
    temp.replace(path)


def load_status():
    try:
        report = json.loads(STATUS_FILE.read_text())
        updated = datetime.fromisoformat(report["updated"])

        if updated.tzinfo is None:
            return None

        age = (utcnow() - updated).total_seconds()

        if not 0 <= age <= MAX_AGE_SECONDS:
            return None

        entities = report["entities"]

        if not isinstance(entities, dict):
            return None

        return report

    except (OSError, ValueError, KeyError, TypeError):
        return None


def get_state(entities, name):
    item = entities.get(name)

    if not isinstance(item, dict):
        return None

    if not item.get("available", False):
        return None

    value = item.get("state")

    if value is None:
        return None

    return str(value).lower()


def load_memory():
    try:
        memory = json.loads(MEMORY_FILE.read_text())
        if isinstance(memory, dict):
            return memory
    except (OSError, ValueError, TypeError):
        pass

    return {"tracked": {}, "events": []}


def monitor_changes():
    """
    Detect confirmed changes without producing repeated alerts.

    First observation becomes the baseline.
    Two distinct snapshots confirm subsequent changes.
    Events are queued for later personality integration.
    """
    report = load_status()

    if report is None:
        return

    memory = load_memory()
    tracked = memory.setdefault("tracked", {})
    events = memory.setdefault("events", [])

    entities = report["entities"]
    snapshot = report["updated"]
    now = utcnow()

    targets = {
        "secondary_pihole": {
            "bad": (
                "SECONDARY PI-HOLE IS NO LONGER REPORTING "
                "TO HOME ASSISTANT. INVESTIGATION RECOMMENDED."
            ),
            "good": (
                "SECONDARY PI-HOLE IS REPORTING AGAIN. "
                "COMMUNICATIONS RESTORED."
            ),
            "reminder": (
                "BOSS, THE SECONDARY PI-HOLE STILL ISN'T "
                "REPORTING TO HOME ASSISTANT. JUST A REMINDER."
            ),
        }
    }

    for name, messages in targets.items():
        current = (
            "available"
            if get_state(entities, name) is not None
            else "unavailable"
        )

        entry = tracked.get(name)

        if entry is None:
            tracked[name] = {
                "confirmed": current,
                "candidate": current,
                "count": 1,
                "last_snapshot": snapshot,
                "since": now.isoformat(),
                "next_reminder": (
                    now + timedelta(hours=REMINDER_HOURS)
                ).isoformat() if current == "unavailable" else None,
            }
            continue

        if entry.get("last_snapshot") == snapshot:
            continue

        entry["last_snapshot"] = snapshot

        if current == entry.get("candidate"):
            entry["count"] = entry.get("count", 0) + 1
        else:
            entry["candidate"] = current
            entry["count"] = 1

        if (
            current != entry.get("confirmed")
            and entry["count"] >= CONFIRM_READINGS
        ):
            entry["confirmed"] = current
            entry["since"] = now.isoformat()

            if current == "unavailable":
                events.append(messages["bad"])
                entry["next_reminder"] = (
                    now + timedelta(hours=REMINDER_HOURS)
                ).isoformat()
            else:
                events.append(messages["good"])
                entry["next_reminder"] = None

        elif entry.get("confirmed") == "unavailable":
            due_text = entry.get("next_reminder")

            if due_text:
                try:
                    due = datetime.fromisoformat(due_text)

                    if now >= due:
                        events.append(messages["reminder"])
                        entry["next_reminder"] = (
                            now + timedelta(hours=REMINDER_HOURS)
                        ).isoformat()

                except ValueError:
                    entry["next_reminder"] = (
                        now + timedelta(hours=REMINDER_HOURS)
                    ).isoformat()

    # Limit pending notifications.
    memory["events"] = events[-10:]
    save_json(MEMORY_FILE, memory)


def get_pending_event():
    """Retrieve and acknowledge one queued event."""
    monitor_changes()
    memory = load_memory()
    events = memory.get("events", [])

    if not events:
        return None

    event = events.pop(0)
    save_json(MEMORY_FILE, memory)
    return event


def get_observation(previous=None, recent=None):
    """Select a casual observation from fresh HA data."""
    report = load_status()

    if report is None:
        return None

    e = report["entities"]
    options = []

    strip1 = get_state(e, "mandalore_strip")
    strip2 = get_state(e, "mandalore_strip_2")

    if strip1 == "on" and strip2 == "on":
        options.append(
            "BOSS, BOTH MANDALORE LIGHT STRIPS ARE ACTIVE. "
            "IMPERIAL INSPECTION?"
        )
    elif strip1 == "off" and strip2 == "off":
        options.append(
            "MANDALORE LIGHTING IS DARK. "
            "STEALTH MODE ENGAGED?"
        )

    if (
        get_state(e, "porch_light") == "on"
        and get_state(e, "porch_light_3") == "on"
    ):
        options.append(
            "BOTH PORCH LIGHTS ARE ON. "
            "EXPECTING THE REBEL ALLIANCE?"
        )

    if get_state(e, "mudroom_light") == "on":
        options.append(
            "MUDROOM LIGHT IS ON. "
            "I ASSUME SOMEONE HAS A VALID REASON."
        )

    for name, low, high in [
        ("home_temperature", 65, 78),
        ("home_humidity", 25, 65),
    ]:
        value = get_state(e, name)

        try:
            number = float(value)
        except (ValueError, TypeError):
            continue

        if name == "home_temperature":
            if number < low:
                options.append(
                    "THE HOUSE IS GETTING COLD. "
                    "I WAS NOT BUILT FOR HOTH."
                )
            elif number > high:
                options.append(
                    "HOUSE TEMPERATURE IS RUNNING WARM. "
                    "IS THIS TATOOINE?"
                )
        else:
            if number < low:
                options.append(
                    "INDOOR HUMIDITY IS LOW. "
                    "EVEN MY CIRCUITS ARE THIRSTY."
                )
            elif number > high:
                options.append(
                    "INDOOR HUMIDITY IS HIGH. "
                    "DAGOBAH SIMULATION ACTIVE?"
                )

    if get_state(e, "basement_ap") == "on":
        options.append(
            "BASEMENT ACCESS POINT REPORTS ONLINE. "
            "THE NETWORK BEHAVES. FOR NOW."
        )

    if get_state(e, "main_pihole") == "on":
        options.append(
            "MAIN PI-HOLE REPORTS ONLINE. "
            "ADVERTISEMENT BLOCKADE HOLDING."
        )

    if (
        get_state(e, "pihole_core_update") == "on"
        or get_state(e, "pihole_ftl_update") == "on"
    ):
        options.append(
            "PI-HOLE HAS UPDATES AVAILABLE. "
            "ADDING THAT TO YOUR TASK LIST."
        )

    # Deliberately exclude bedrooms, cameras, smoke,
    # and CO from casual personality observations.

    excluded = set(recent or [])

    if previous:
        excluded.add(previous)

    choices = [x for x in options if x not in excluded]

    return random.choice(choices) if choices else None


if __name__ == "__main__":
    print("V-XN // HOME ASSISTANT AWARENESS TEST")

    monitor_changes()

    report = load_status()

    if report is None:
        print("No fresh Home Assistant data.")
    else:
        print(
            "Fresh status available:",
            len(report["entities"]),
            "entities"
        )

        recent = []

        for i in range(5):
            message = get_observation(recent=recent)

            if message is None:
                print("No additional distinct observations.")
                break

            print(f"{i + 1}. {message}")
            recent.append(message)

        memory = load_memory()
        print(
            "Pending status-change events:",
            len(memory.get("events", []))
        )
