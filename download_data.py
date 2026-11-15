"""This script downloads event and 360 data for a given competition and season. """

import requests
import json
import os
import pandas as pd
from pathlib import Path

BASE_URL = (
    "https://raw.githubusercontent.com/"
    "hudl/open-data/master/data"
)

# STEP 1: Load available competitions

url = f"{BASE_URL}/competitions.json"

response = requests.get(url)
response.raise_for_status()

competitions = pd.DataFrame(response.json())

print("\nAVAILABLE COMPETITIONS\n")

print(
    competitions[
        [
            "competition_id",
            "competition_name",
            "season_id",
            "season_name",
            "match_available_360"
        ]
    ].to_string(index=False)
)

# STEP 2: Choose competition and season

competition_id = input(
    "\nEnter competition ID: "
).strip()

season_id = input(
    "Enter season ID: "
).strip()

# STEP 3: Download matches for that season

matches_url = (
    f"{BASE_URL}/matches/"
    f"{competition_id}/{season_id}.json"
)

response = requests.get(matches_url)
response.raise_for_status()

matches = response.json()

print(f"\nNumber of matches: {len(matches)}")

# STEP 4: Create folders

events_folder = Path("data/events")
frames_folder = Path("data/three-sixty")
matches_folder = Path("data/matches")

events_folder.mkdir(parents=True, exist_ok=True)
frames_folder.mkdir(parents=True, exist_ok=True)
matches_folder.mkdir(parents=True, exist_ok=True)

# Save match list

with open(
    matches_folder / f"{competition_id}_{season_id}.json",
    "w",
    encoding="utf-8"
) as file:
    json.dump(matches, file, indent=2)

# STEP 5: Download event and 360 data for each match

for match in matches:

    match_id = match["match_id"]

    print(f"Downloading match {match_id}...")

    # Download events
    event_url = (
        f"{BASE_URL}/events/{match_id}.json"
    )

    event_response = requests.get(event_url)
    event_response.raise_for_status()

    with open(
        events_folder / f"{match_id}.json",
        "w",
        encoding="utf-8"
    ) as file:
        json.dump(event_response.json(), file)

    # Download 360 data if available
    frames_url = (
        f"{BASE_URL}/three-sixty/{match_id}.json"
    )

    frames_response = requests.get(frames_url)

    if frames_response.status_code == 200:

        with open(
            frames_folder / f"{match_id}.json",
            "w",
            encoding="utf-8"
        ) as file:
            json.dump(frames_response.json(), file)

print("\nDOWNLOAD COMPLETE!")
