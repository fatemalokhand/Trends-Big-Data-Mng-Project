"""This script extracts corner kick sequences from StatsBomb event data.
It identifies corner kicks, tracks the subsequent events, and determines the outcome of each sequence.
The results are saved to CSV files for further analysis."""

import json
import csv
from pathlib import Path
from datetime import datetime

# DATASET LOCATIONS

DATASETS = {
    "World Cup 2022": Path("data/world_cup_2022"),
    "Euro 2020": Path("data/euro_2020")
}

OUTPUT_FOLDER = Path("outputs")
OUTPUT_FOLDER.mkdir(exist_ok=True)

# Proposed safety cutoffs from team members
MAX_SECONDS = 15
MAX_EVENTS = 10

# HELPER FUNCTIONS

def get_name(value):
    """Safely extract a StatsBomb name."""
    if isinstance(value, dict):
        return value.get("name", "")
    return ""


def get_timestamp(event):
    """Convert event timestamp into seconds."""
    timestamp = event.get("timestamp")

    if not timestamp:
        return None

    try:
        parsed = datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )

        return (
            parsed.hour * 3600
            + parsed.minute * 60
            + parsed.second
            + parsed.microsecond / 1_000_000
        )

    except ValueError:
        return None


def get_shot_outcome(event):
    shot = event.get("shot", {})
    return get_name(shot.get("outcome"))


def get_event_description(event):
    event_type = get_name(event.get("type"))

    if event_type == "Shot":
        outcome = get_shot_outcome(event)
        return f"Shot: {outcome or 'Unknown outcome'}"

    return event_type


# Let's define a function to determine if an event is a corner kick.

def is_corner(event):

    if get_name(event.get("type")) != "Pass":
        return False

    pass_data = event.get("pass", {})

    return get_name(pass_data.get("type")) == "Corner"


# define when a sequence ends

def find_sequence(events, corner_index):

    corner = events[corner_index]

    attacking_team = get_name(corner.get("team"))
    corner_period = corner.get("period")
    corner_time = get_timestamp(corner)

    sequence_events = []
    terminal_label = None
    terminal_reason = None

    for event in events[corner_index + 1:]:

        # Do not continue into another period
        if event.get("period") != corner_period:
            terminal_label = "no_clear_terminal_outcome"
            terminal_reason = "Period ended"
            break

        # Apply 15-second time cutoff
        event_time = get_timestamp(event)

        if corner_time is not None and event_time is not None:
            elapsed = event_time - corner_time

            if elapsed > MAX_SECONDS:
                terminal_label = "no_clear_terminal_outcome"
                terminal_reason = "15-second cutoff"
                break

        sequence_events.append(event)

        event_type = get_name(event.get("type"))

        # A goal is a shot with a Goal outcome
        if event_type == "Shot":

            outcome = get_shot_outcome(event)

            if outcome == "Goal":
                terminal_label = "goal"
            else:
                terminal_label = "shot_no_goal"

            terminal_reason = (
                f"First shot: {outcome or 'Unknown outcome'}"
            )
            break

        # Foul or offside
        if event_type in ["Foul Committed", "Offside"]:
            terminal_label = "foul_or_offside"
            terminal_reason = event_type
            break

        # Another restart
        if event_type == "Pass":

            restart_type = get_name(
                event.get("pass", {}).get("type")
            )

            if restart_type in [
                "Goal Kick",
                "Throw-in",
                "Free Kick",
                "Corner"
            ]:
                terminal_label = "another_restart"
                terminal_reason = restart_type
                break

        # Ball out of play, if explicitly recorded
        if event_type in ["Ball Out", "Out"]:
            terminal_label = "ball_out_of_play"
            terminal_reason = event_type
            break

        # Detect possession changing to the defending team
        possession_team = get_name(
            event.get("possession_team")
        )

        if (
            possession_team
            and possession_team != attacking_team
        ):
            terminal_label = "possession_loss"
            terminal_reason = (
                f"Possession changed to {possession_team}"
            )
            break

        # Maximum 10 subsequent events
        if len(sequence_events) >= MAX_EVENTS:
            terminal_label = "no_clear_terminal_outcome"
            terminal_reason = "10-event cutoff"
            break

    if terminal_label is None:
        terminal_label = "no_clear_terminal_outcome"
        terminal_reason = "No terminal event found"

    return sequence_events, terminal_label, terminal_reason


# Now from all downloaded matches, extract corners

corner_rows = []
audit_rows = []

for competition, folder in DATASETS.items():

    events_folder = folder / "events"

    if not events_folder.exists():
        print(f"Missing folder: {events_folder}")
        continue

    event_files = list(events_folder.glob("*.json"))

    print(f"\nProcessing {competition}")
    print(f"Matches found: {len(event_files)}")

    for file_path in event_files:

        match_id = file_path.stem

        with open(file_path, "r", encoding="utf-8") as file:
            events = json.load(file)

        for index, event in enumerate(events):

            if not is_corner(event):
                continue

            corner_team = get_name(event.get("team"))

            sequence, label, reason = find_sequence(
                events, index
            )

            corner_id = (
                f"{competition}_{match_id}_"
                f"{event.get('id', index)}"
            )

            corner_rows.append({
                "corner_id": corner_id,
                "competition": competition,
                "match_id": match_id,
                "period": event.get("period"),
                "corner_timestamp": event.get("timestamp"),
                "attacking_team": corner_team,
                "corner_x": event.get("location", [None, None])[0],
                "corner_y": event.get("location", [None, None])[1],
                "sequence_event_count": len(sequence),
                "outcome": label,
                "terminal_reason": reason
            })

            # Save the individual events for manual auditing
            audit_rows.append({
                "corner_id": corner_id,
                "competition": competition,
                "match_id": match_id,
                "event_id": event.get("id"),
                "event_number": 0,
                "event_type": "Corner",
                "team": corner_team,
                "timestamp": event.get("timestamp"),
                "description": "Corner kick"
            })

            for number, sequence_event in enumerate(
                sequence, start=1
            ):

                audit_rows.append({
                    "corner_id": corner_id,
                    "competition": competition,
                    "match_id": match_id,
                    "event_id": sequence_event.get("id"),
                    "event_number": number,
                    "event_type": get_name(
                        sequence_event.get("type")
                    ),
                    "team": get_name(
                        sequence_event.get("team")
                    ),
                    "timestamp": sequence_event.get("timestamp"),
                    "description": get_event_description(
                        sequence_event
                    )
                })


# --------------------------------------------------
# 6. EXPORT RESULTS
# --------------------------------------------------

if corner_rows:

    with open(
        OUTPUT_FOLDER / "corner_sequences.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=corner_rows[0].keys()
        )

        writer.writeheader()
        writer.writerows(corner_rows)

    with open(
        OUTPUT_FOLDER / "sequence_events_audit.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=audit_rows[0].keys()
        )

        writer.writeheader()
        writer.writerows(audit_rows)

    print("\nEXTRACTION COMPLETE")
    print("Total corners:", len(corner_rows))

    print("\nOUTCOME SUMMARY")

    counts = {}

    for row in corner_rows:
        outcome = row["outcome"]
        counts[outcome] = counts.get(outcome, 0) + 1

    for outcome, count in counts.items():
        print(f"{outcome}: {count}")

else:
    print("\nNo corners were extracted.")
