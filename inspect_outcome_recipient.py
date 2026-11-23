
import json
import os
from collections import defaultdict

DATASETS = {
    "World Cup 2022": "data/world_cup_2022/events",
    "Euro 2020": "data/euro_2020/events"
}

results = defaultdict(lambda: {
    "total": 0,
    "recipient_present": 0,
    "recipient_missing": 0
})

for competition, folder in DATASETS.items():

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

            recipient = pass_data.get("recipient")

            results[label]["total"] += 1

            if recipient is None:
                results[label]["recipient_missing"] += 1
            else:
                results[label]["recipient_present"] += 1

print("\nCORNER OUTCOME AND RECIPIENT ANALYSIS")
print("=" * 55)

for outcome, counts in results.items():

    total = counts["total"]

    present = counts["recipient_present"]
    missing = counts["recipient_missing"]

    percentage = (present / total * 100) if total else 0

    print(f"\nOutcome: {outcome}")
    print(f"Total corners: {total}")
    print(f"Recipient recorded: {present}")
    print(f"Recipient missing: {missing}")
    print(f"Recipient availability: {percentage:.1f}%")
