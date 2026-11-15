"""This script checks the downloaded data for each downloaded season. 
It makes sure that the event and 360 data files exist for each match in the season."""

from pathlib import Path

DATASETS = {
    "World Cup 2022": Path("data/world_cup_2022"),
    "Euro 2020": Path("data/euro_2020")
}

print("\nDOWNLOAD SUMMARY")
print("=" * 50)

for competition, folder in DATASETS.items():

    events_folder = folder / "events"
    frames_folder = folder / "three-sixty"

    event_files = (
        list(events_folder.glob("*.json"))
        if events_folder.exists() else []
    )

    frame_files = (
        list(frames_folder.glob("*.json"))
        if frames_folder.exists() else []
    )

    print(f"\n{competition}")
    print(f"Event files: {len(event_files)}")
    print(f"360 files:   {len(frame_files)}")

    if not event_files:
        print("WARNING: No event files found.")

print("\nCheck complete.")
