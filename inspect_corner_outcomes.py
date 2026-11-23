
import json
import os
from collections import Counter

DATASETS = {
    "World Cup 2022": "data/world_cup_2022/events",
    "Euro 2020": "data/euro_2020/events"
}

outcome_counts = Counter()
examples = {}

for competition, folder in DATASETS.items():

    print(f"\nProcessing {competition}")

    for filename in os.listdir(folder):

        if not filename.endswith(".json"):
            continue

        path = os.path.join(folder, filename)

        with open(path, "r", encoding="utf-8") as file:
            events = json.load(file)

        for event in events:

            if event.get("type", {}).get("name") != "Pass":
                continue

            pass_data = event.get("pass", {})

            if pass_data.get("type", {}).get("name") != "Corner":
                continue

            outcome = pass_data.get("outcome")

            if outcome is None:
                label = "MISSING"
            else:
                label = outcome.get("name", "UNKNOWN")

            outcome_counts[label] += 1

            if label not in examples:
                examples[label] = {
                    "match_file": filename,
                    "player": event.get("player", {}).get("name"),
                    "team": event.get("team", {}).get("name"),
                    "recipient": pass_data.get("recipient", {}).get("name"),
                    "end_location": pass_data.get("end_location"),
                    "pass_height": pass_data.get("height", {}).get("name"),
                    "pass_technique": pass_data.get("technique", {}).get("name")
                }

print("\n" + "=" * 55)
print("CORNER PASS OUTCOME INSPECTION")
print("=" * 55)

print("\nOutcome counts:")

for outcome, count in outcome_counts.items():
    print(f"{outcome}: {count}")

print("\nExample from each outcome category:")

for outcome, example in examples.items():
    print(f"\n{outcome}:")
    for key, value in example.items():
        print(f"  {key}: {value}")
