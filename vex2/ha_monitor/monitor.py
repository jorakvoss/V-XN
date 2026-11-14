
#!/usr/bin/env python3

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

# V-XN Ship Computer — Home Assistant Monitor

HA_URL = "http://192.168.10.96:8123"
TOKEN_FILE = Path.home() / ".config/vex/ha_token"
OUTPUT_FILE = Path(__file__).resolve().parent / "status.json"

ENTITIES = {
    # Environment
    "home_temperature": "sensor.home_current_temperature",
    "home_humidity": "sensor.home_current_humidity",
    "bedroom_temperature": "sensor.bedroom_temperature",

    # Lighting
    "mudroom_light": "light.mud_room",
    "porch_light": "light.porch_light",
    "porch_light_3": "light.porch_3",
    "desk_light": "light.office_light",
    "mandalore_strip": "light.office_mandalore_light_strip",
    "mandalore_strip_2": "light.office_mandalore_strip_lights_2",
    "bedroom_light": "light.bedroom_light",

    # Bedroom awareness
    "bedroom_motion": "binary_sensor.bedroom_motion",
    "bedroom_occupancy": "binary_sensor.bedroom_occupancy",

    # Basement safety
    "smoke_detector": (
        "binary_sensor.basement_smoke_co_detector_smoke_detected"
    ),
    "co_detector": (
        "binary_sensor.basement_smoke_co_detector_carbon_monoxide_detected"
    ),
    "safety_node": (
        "sensor.basement_smoke_co_detector_node_status"
    ),

    # Network infrastructure
    "main_pihole": "binary_sensor.main_pi_hole_status",
    "secondary_pihole": "binary_sensor.secondary_pi_hole_status",
    "basement_ap": "binary_sensor.192_168_10_105",

    # Pi-hole update availability
    "pihole_core_update": (
        "update.main_pi_hole_core_update_available"
    ),
    "pihole_ftl_update": (
        "update.main_pi_hole_ftl_update_available"
    ),
}


def main():
    try:
        token = TOKEN_FILE.read_text().strip()

        # Retrieve all entity states in one read-only request.
        response = requests.get(
            f"{HA_URL}/api/states",
            headers={"Authorization": f"Bearer {token}"},
            timeout=10,
        )
        response.raise_for_status()

        all_states = {
            entity["entity_id"]: entity
            for entity in response.json()
        }

        status = {}
        available = 0

        for name, entity_id in ENTITIES.items():
            entity = all_states.get(entity_id)

            if entity is None:
                status[name] = {
                    "state": None,
                    "unit": "",
                    "available": False,
                }
                continue

            state = str(entity.get("state", "unknown"))
            valid = state.lower() not in (
                "unknown",
                "unavailable",
                "none",
            )

            if valid:
                available += 1

            status[name] = {
                "state": state if valid else None,
                "unit": entity.get("attributes", {}).get(
                    "unit_of_measurement", ""
                ),
                "available": valid,
            }

        report = {
            "updated": datetime.now(
                timezone.utc
            ).isoformat(),
            "total": len(status),
            "available": available,
            "entities": status,
        }

        # Atomic replacement prevents partial JSON files.
        temp_file = OUTPUT_FILE.with_suffix(".json.tmp")
        temp_file.write_text(
            json.dumps(report, indent=2),
            encoding="utf-8",
        )
        temp_file.replace(OUTPUT_FILE)

        print(
            f"VEX HA MONITOR: Updated {len(status)} entities "
            f"({available} available).",
            flush=True,
        )

    except (
        requests.RequestException,
        OSError,
        ValueError,
        KeyError,
        TypeError,
    ) as error:
        print(
            f"VEX HA MONITOR: Update failed: {error}",
            file=sys.stderr,
            flush=True,
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
