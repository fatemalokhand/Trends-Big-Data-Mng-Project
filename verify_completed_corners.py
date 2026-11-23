
import csv
import json
import os
import random

DELIVERY_FILE = "outputs/corner_delivery_features.csv"

DATASETS = {
    "World Cup 2022": "data/world_cup_2022/events",
    "Euro 2020": "data/euro_2020/events"
}

# Load extracted corner delivery records
with open(DELIVERY_FILE, "r", encoding="utf-8-sig") as file:
    deliveries = list(csv.DictReader(file))

# Select corners with missing outcomes and recorded recipients
candidates = [
    row for row in deliveries
    if not row["pass_outcome"].strip()
    and row["recipient"].strip()
]

# Select up to 20 reproducible examples
random.seed(42)
sample = random.sample(candidates, min(20, len(candidates)))

print("=" * 65)
print("VERIFYING CORNER DELIVERIES WITH MISSING PASS OUTCOMES")
print("=" * 65)

# Build a lookup for match files
match_files = {}

for competition, folder in DATASETS.items():
    for filename in os.listdir(folder):
        if filename.endswith(".json"):
            match_id = filename.replace(".json", "")
            match_files[(competition, match_id)] = os.path.join(folder, filename)

for number, row in enumerate(sample, start=1):

    competition = row["competition"]
    match_id = row["match_id"]
    player = row["player"]
    recipient = row["recipient"]

    path = match_files.get((competition, match_id))

    print(f"\nSAMPLE {number}")
    print("-" * 50)
    print(f"Competition: {competition}")
    print(f"Match: {match_id}")
    print(f"Corner taker: {player}")
    print(f"Recorded recipient: {recipient}")

    if path is None:
        print("Raw match file not found.")
        continue

    with open(path, "r", encoding="utf-8") as file:
        events = json.load(file)

    corner_index = None

    for i, event in enumerate(events):
        if (
            event.get("id") == row["corner_id"].split("_")[-1]
            and event.get("type", {}).get("name") == "Pass"
            and event.get("pass", {}).get("type", {}).get("name") == "Corner"
        ):
            corner_index = i
            break

    if corner_index is None:
        print("Corner event not found.")
        continue

    print("Following events:")

    for event in events[corner_index + 1:corner_index + 6]:

        event_type = event.get("type", {}).get("name")
        event_player = event.get("player", {}).get("name")
        event_team = event.get("team", {}).get("name")
        event_possession = event.get("possession_team", {}).get("name")

        print(
            f"  Event: {event_type} | "
            f"Player: {event_player} | "
            f"Team: {event_team} | "
            f"Possession team: {event_possession}"
        )

