
"""
this code extracts features from the original StatsBomb corner events.
One row is generated for every detected corner.

Output:
outputs/corner_delivery_features.csv
"""

import json
import csv
from pathlib import Path
from collections import Counter


# --------------------------------------------------
# 1. CONFIGURATION
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

DATASETS = {
    "World Cup 2022": BASE_DIR / "data" / "world_cup_2022",
    "Euro 2020": BASE_DIR / "data" / "euro_2020"
}

OUTPUT_FOLDER = BASE_DIR / "outputs"
OUTPUT_FOLDER.mkdir(exist_ok=True)

OUTPUT_FILE = OUTPUT_FOLDER / "corner_delivery_features.csv"


# 2. HELPER FUNCTIONS

def get_name(value):
    """Extract a name from a StatsBomb dictionary."""

    if isinstance(value, dict):
        return value.get("name", "")

    return ""


def get_coordinate(location, index):
    """Safely retrieve an x or y coordinate."""

    if isinstance(location, list) and len(location) > index:
        return location[index]

    return ""


def is_corner(event):
    """Identify StatsBomb corner-kick events."""

    if get_name(event.get("type")) != "Pass":
        return False

    pass_data = event.get("pass", {})

    return get_name(pass_data.get("type")) == "Corner"


def get_corner_side(y):
    """
    Preserve the original StatsBomb y-coordinate side.

    This is not yet labelled as attacking left or right.
    """

    if y == "":
        return ""

    try:
        y = float(y)

        if y < 40:
            return "y_lower_half"

        if y > 40:
            return "y_upper_half"

        return "y_midpoint"

    except (ValueError, TypeError):
        return ""


# 3. EXTRACT FEATURES FROM ONE CORNER

def extract_features(event, competition, match_id):

    pass_data = event.get("pass", {})

    corner_location = event.get("location", [])
    pass_end_location = pass_data.get("end_location", [])

    corner_x = get_coordinate(corner_location, 0)
    corner_y = get_coordinate(corner_location, 1)

    end_x = get_coordinate(pass_end_location, 0)
    end_y = get_coordinate(pass_end_location, 1)

    # Player receiving the pass, if recorded.
    recipient = get_name(pass_data.get("recipient"))
    
    # Pass outcome may legitimately be missing.
    pass_outcome = get_name(pass_data.get("outcome"))
    
    if pass_outcome:
        delivery_completion_status = (
            pass_outcome.lower().replace(" ", "_")
        )
    elif recipient:
        delivery_completion_status = "recipient_recorded_outcome_missing"
    else:
        delivery_completion_status = "outcome_and_recipient_missing"

    # Pass height and technique.
    pass_height = get_name(pass_data.get("height"))
    pass_technique = get_name(pass_data.get("technique"))


    # Create the same corner ID format as extract_corners.py.
    corner_id = (
        f"{competition}_{match_id}_"
        f"{event.get('id', '')}"
    )


    return {

        "corner_id": corner_id,

        "competition": competition,

        "match_id": match_id,

        "team": get_name(event.get("team")),

        "player": get_name(event.get("player")),

        "period": event.get("period", ""),

        "timestamp": event.get("timestamp", ""),

        "corner_x": corner_x,

        "corner_y": corner_y,

        "corner_side_y": get_corner_side(corner_y),

        "pass_type": get_name(pass_data.get("type")),

        "pass_height": pass_height,

        "pass_technique": pass_technique,

        "pass_end_x": end_x,

        "pass_end_y": end_y,

        "pass_length": pass_data.get("length", ""),

        "pass_angle": pass_data.get("angle", ""),

        "pass_outcome": pass_outcome,

        "recipient": recipient,

        "delivery_completion_status": delivery_completion_status

    }


# 4. PROCESS BOTH COMPETITIONS

all_features = []

competition_counts = Counter()

match_counts = Counter()

seen_corner_ids = set()

print("=" * 55)
print("CORNER DELIVERY FEATURE EXTRACTION")
print("=" * 55)


for competition, folder in DATASETS.items():

    events_folder = folder / "events"

    if not events_folder.exists():

        print(f"\nMissing folder: {events_folder}")
        continue

    event_files = sorted(events_folder.glob("*.json"))

    print(f"\nProcessing {competition}")
    print(f"Matches found: {len(event_files)}")

    for file_path in event_files:

        match_id = file_path.stem

        try:

            with open(
                file_path,
                "r",
                encoding="utf-8"
            ) as file:

                events = json.load(file)

            if not isinstance(events, list):

                print(f"Invalid event format: {file_path}")
                continue

            for event in events:

                if not is_corner(event):
                    continue

                features = extract_features(
                    event,
                    competition,
                    match_id
                )

                corner_id = features["corner_id"]

                if corner_id in seen_corner_ids:

                    print(f"Duplicate corner skipped: {corner_id}")
                    continue

                seen_corner_ids.add(corner_id)

                all_features.append(features)

                competition_counts[competition] += 1

                match_counts[competition] += 1

        except (OSError, json.JSONDecodeError) as error:

            print(f"Could not process {file_path}: {error}")


# 5. EXPORT CSV

fieldnames = [
    "corner_id",
    "competition",
    "match_id",
    "team",
    "player",
    "period",
    "timestamp",
    "corner_x",
    "corner_y",
    "corner_side_y",
    "pass_type",
    "pass_height",
    "pass_technique",
    "pass_end_x",
    "pass_end_y",
    "pass_length",
    "pass_angle",
    "delivery_completion_status",
    "pass_outcome",
    "recipient"
]

with open(
    OUTPUT_FILE,
    "w",
    newline="",
    encoding="utf-8"
) as file:

    writer = csv.DictWriter(
        file,
        fieldnames=fieldnames
    )

    writer.writeheader()
    writer.writerows(all_features)


# 6. DISPLAY SUMMARY

print("\n" + "=" * 55)
print("EXTRACTION COMPLETE")
print("=" * 55)

print(f"Total delivery records: {len(all_features)}")

print("\nCOMPETITION SUMMARY")

for competition, count in competition_counts.items():

    print(f"{competition}: {count} corners")

print("\nFEATURE AVAILABILITY")

for field in fieldnames:

    if field in ["corner_id", "competition", "match_id"]:
        continue

    available = sum(
        1 for row in all_features
        if row[field] not in ("", None)
    )

    missing = len(all_features) - available

    print(
        f"{field}: "
        f"{available} available, "
        f"{missing} missing"
    )

print("\nOutput saved to:")
print(OUTPUT_FILE)

print("\nDelivery feature extraction finished.")
