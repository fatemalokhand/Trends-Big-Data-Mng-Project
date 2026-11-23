
import json
from pathlib import Path
from collections import Counter

BASE_DIR = Path(__file__).resolve().parent

DATASETS = [
    BASE_DIR / "data" / "world_cup_2022" / "events",
    BASE_DIR / "data" / "euro_2020" / "events"
]

field_counts = Counter()
corner_field_counts = Counter()
corner_count = 0
example_corner = None

for folder in DATASETS:
    for file_path in folder.glob("*.json"):
        with open(file_path, "r", encoding="utf-8") as file:
            events = json.load(file)

        for event in events:
            # Check all event types
            if "under_pressure" in event:
                field_counts["under_pressure_present"] += 1

            if "pass" in event and isinstance(event["pass"], dict):
                if "cross" in event["pass"]:
                    field_counts["pass_cross_present"] += 1

            # Identify corner events
            pass_data = event.get("pass", {})

            if (
                event.get("type", {}).get("name") == "Pass"
                and pass_data.get("type", {}).get("name") == "Corner"
            ):
                corner_count += 1

                if "under_pressure" in event:
                    corner_field_counts["under_pressure_present"] += 1

                if "cross" in pass_data:
                    corner_field_counts["cross_present"] += 1

                if example_corner is None:
                    example_corner = event

print("=" * 55)
print("STATSBOMB RAW FIELD INSPECTION")
print("=" * 55)

print("\nAll events:")
print("under_pressure present:", field_counts["under_pressure_present"])
print("pass.cross present:", field_counts["pass_cross_present"])

print("\nCorner events:")
print("Total corners:", corner_count)
print("under_pressure present:", corner_field_counts["under_pressure_present"])
print("pass.cross present:", corner_field_counts["cross_present"])

if example_corner:
    print("\nExample corner event keys:")
    print(sorted(example_corner.keys()))

    print("\nExample corner pass keys:")
    print(sorted(example_corner.get("pass", {}).keys()))

    print("\nExample corner under_pressure value:")
    print(example_corner.get("under_pressure", "FIELD NOT PRESENT"))

    print("\nExample corner cross value:")
    print(example_corner.get("pass", {}).get("cross", "FIELD NOT PRESENT"))
