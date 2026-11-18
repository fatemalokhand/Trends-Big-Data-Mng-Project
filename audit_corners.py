"""This script audits extracted StatsBomb corner sequences against the original match event JSON files.
It verifies that the extracted sequences match the original data, checks timestamps, and recalculates outcomes"""
import csv
import json
import random
import argparse
from pathlib import Path
from datetime import datetime
from collections import Counter, defaultdict


# CONFIGURATION

BASE_DIR = Path(__file__).resolve().parent

OUTPUT_DIR = BASE_DIR / "outputs"

CORNER_FILE = OUTPUT_DIR / "corner_sequences.csv"
EVENT_AUDIT_FILE = OUTPUT_DIR / "sequence_events_audit.csv"

DATASETS = {
    "World Cup 2022": BASE_DIR / "data" / "world_cup_2022" / "events",
    "Euro 2020": BASE_DIR / "data" / "euro_2020" / "events",
}

SAMPLE_SIZE = 100
RANDOM_SEED = 42

MAX_SECONDS = 15
MAX_EVENTS = 10


# GENERAL HELPERS

def get_nested_name(event, *keys):
    """Safely retrieve a nested StatsBomb name."""

    value = event

    for key in keys:
        if not isinstance(value, dict):
            return ""

        value = value.get(key)

    if isinstance(value, dict):
        return value.get("name", "")

    return value if value is not None else ""


def parse_timestamp(timestamp):
    """Convert a StatsBomb timestamp into a datetime."""

    try:
        return datetime.fromisoformat(
            timestamp.replace("Z", "+00:00")
        )
    except (ValueError, AttributeError):
        return None


def event_id(event):
    return str(event.get("id", ""))


def event_period(event):
    return str(event.get("period", ""))


def event_type(event):
    return get_nested_name(event, "type")


def event_team(event):
    return get_nested_name(event, "team")


def is_corner(event):
    return (
        event_type(event) == "Pass"
        and get_nested_name(event, "pass", "type") == "Corner"
    )


def get_shot_outcome(event):
    return get_nested_name(event, "shot", "outcome")


# --------------------------------------------------
# LOAD CSV FILES
# --------------------------------------------------

def load_csv(path):

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with open(path, "r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


# --------------------------------------------------
# SELECT A RANDOM, REPRODUCIBLE SAMPLE
# --------------------------------------------------

def select_sample(corners, sample_size):

    if sample_size >= len(corners):
        return corners

    random.seed(RANDOM_SEED)

    outcomes = defaultdict(list)

    for corner in corners:
        outcomes[corner["outcome"]].append(corner)

    # Proportional allocation across outcome categories.
    allocations = {}

    for outcome, records in outcomes.items():
        allocations[outcome] = (
            sample_size * len(records) / len(corners)
        )

    quotas = {
        outcome: int(value)
        for outcome, value in allocations.items()
    }

    remaining = sample_size - sum(quotas.values())

    ranked = sorted(
        allocations,
        key=lambda outcome: allocations[outcome] - quotas[outcome],
        reverse=True
    )

    for outcome in ranked[:remaining]:
        quotas[outcome] += 1

    sample = []

    for outcome, records in outcomes.items():
        count = min(quotas[outcome], len(records))
        sample.extend(random.sample(records, count))

    return sample


# --------------------------------------------------
# LOAD ORIGINAL MATCH EVENTS
# --------------------------------------------------

def load_match_events(competition, match_id):

    folder = DATASETS.get(competition)

    if folder is None:
        raise ValueError(
            f"Unknown competition: {competition}"
        )

    path = folder / f"{match_id}.json"

    if not path.exists():
        raise FileNotFoundError(
            f"Original match file not found: {path}"
        )

    with open(path, "r", encoding="utf-8") as file:
        events = json.load(file)

    # StatsBomb event JSON is normally a list.
    if not isinstance(events, list):
        raise ValueError("Unexpected match JSON format")

    return events


# --------------------------------------------------
# INDEPENDENTLY RE-EVALUATE A CORNER SEQUENCE
# --------------------------------------------------

def find_corner_sequence(events, corner_index):

    corner = events[corner_index]

    attacking_team = get_nested_name(
        corner, "possession_team"
    )

    corner_timestamp = parse_timestamp(
        corner.get("timestamp")
    )

    sequence = []

    outcome = "no_clear_terminal_outcome"
    terminal_reason = "cutoff_or_no_terminal_event"

    for event in events[corner_index + 1:]:

        # Stop if the period changes.
        if event_period(event) != event_period(corner):
            terminal_reason = "period_change"
            break

        current_timestamp = parse_timestamp(
            event.get("timestamp")
        )

        # Apply the 15-second cutoff.
        if corner_timestamp and current_timestamp:

            elapsed = (
                current_timestamp - corner_timestamp
            ).total_seconds()

            if elapsed > MAX_SECONDS:
                terminal_reason = "15_second_cutoff"
                break

        sequence.append(event)

        kind = event_type(event)

        # First shot determines the shot outcome.
        if kind == "Shot":

            if get_shot_outcome(event) == "Goal":
                outcome = "goal"
            else:
                outcome = "shot_no_goal"

            terminal_reason = "shot"
            break

        # Foul or offside.
        if kind == "Foul Committed":
            outcome = "foul_or_offside"
            terminal_reason = "foul"
            break

        if kind == "Offside":
            outcome = "foul_or_offside"
            terminal_reason = "offside"
            break

        # Another restart.
        pass_type = get_nested_name(
            event, "pass", "type"
        )

        if pass_type in [
            "Goal Kick",
            "Throw-in",
            "Free Kick",
            "Corner"
        ]:
            outcome = "another_restart"
            terminal_reason = "another_restart"
            break

        # Ball out of play.
        if kind in ["Ball Out", "Out"]:
            outcome = "ball_out_of_play"
            terminal_reason = "ball_out"
            break

        # Possession changes to the opposing team.
        possession_team = get_nested_name(
            event, "possession_team"
        )

        if (
            possession_team
            and attacking_team
            and possession_team != attacking_team
        ):
            outcome = "possession_loss"
            terminal_reason = "possession_change"
            break

        # Apply the 10-event cutoff.
        if len(sequence) >= MAX_EVENTS:
            terminal_reason = "10_event_cutoff"
            break

    return sequence, outcome, terminal_reason


# --------------------------------------------------
# VALIDATE ONE CORNER
# --------------------------------------------------

def audit_corner(corner, audit_events):

    result = {
        "corner_id": corner.get("corner_id", ""),
        "match_id": corner.get("match_id", ""),
        "competition": corner.get("competition", ""),
        "original_outcome": corner.get("outcome", ""),
        "corner_found": "NO",
        "events_match": "NO",
        "event_order_match": "NO",
        "timestamp_check": "NOT CHECKED",
        "recalculated_outcome": "NOT CHECKED",
        "outcome_match": "NOT CHECKED",
        "terminal_reason": "",
        "audit_status": "FAIL",
        "notes": "",
    }

    try:

        match_id = corner["match_id"]
        competition = corner["competition"]

        events = load_match_events(
            competition, match_id
        )

        # Sort audit events by their recorded event number.
        audit_events = sorted(
            audit_events,
            key=lambda row: int(
                row.get("event_number") or 0
            )
        )

        if not audit_events:
            result["notes"] = "No audit events found"
            return result

        # The first audit event should be the corner itself.
        corner_event_id = audit_events[0].get("event_id", "")

        if not corner_event_id:
            result["notes"] = "Missing corner event ID"
            return result

        # Locate the corner in the original JSON.
        corner_index = next(
            (
                i for i, event in enumerate(events)
                if event_id(event) == str(corner_event_id)
            ),
            None
        )

        if corner_index is None:
            result["notes"] = "Corner ID not found in original JSON"
            return result

        original_corner = events[corner_index]

        if not is_corner(original_corner):
            result["notes"] = "Located event is not a corner"
            return result

        result["corner_found"] = "YES"

        # Extract original event IDs from the audit CSV.
        extracted_ids = [
            str(row.get("event_id", ""))
            for row in audit_events
        ]

        # Independently reconstruct the sequence.
        raw_sequence, new_outcome, reason = (
            find_corner_sequence(events, corner_index)
        )

        expected_ids = [
            event_id(original_corner)
        ] + [
            event_id(event) for event in raw_sequence
        ]

        result["events_match"] = (
            "YES" if set(extracted_ids) == set(expected_ids)
            else "NO"
        )

        result["event_order_match"] = (
            "YES" if extracted_ids == expected_ids
            else "NO"
        )

        # Compare the recorded and original timestamps.
        original_timestamp = original_corner.get("timestamp", "")
        recorded_timestamp = audit_events[0].get("timestamp", "")

        result["timestamp_check"] = (
            "YES" if original_timestamp == recorded_timestamp
            else "NO"
        )

        result["recalculated_outcome"] = new_outcome

        original_outcome = corner.get("outcome", "")

        result["outcome_match"] = (
            "YES" if original_outcome == new_outcome
            else "NO"
        )

        result["terminal_reason"] = reason

        # Decide the audit status.
        if (
            result["events_match"] == "YES"
            and result["event_order_match"] == "YES"
            and result["timestamp_check"] == "YES"
            and result["outcome_match"] == "YES"
        ):

            if new_outcome == "no_clear_terminal_outcome":
                result["audit_status"] = "REVIEW"
                result["notes"] = (
                    "Unresolved sequence requires human review"
                )
            else:
                result["audit_status"] = "PASS"
                result["notes"] = "Automated checks agree"

        else:
            result["audit_status"] = "FAIL"
            result["notes"] = (
                "One or more automated checks disagree"
            )

    except Exception as error:

        result["audit_status"] = "FAIL"
        result["notes"] = str(error)

    return result


# --------------------------------------------------
# MAIN AUDIT PROCESS
# --------------------------------------------------

def main():

    parser = argparse.ArgumentParser(
        description="Audit extracted StatsBomb corner sequences"
    )

    parser.add_argument(
        "--sample-size",
        type=int,
        default=SAMPLE_SIZE
    )

    args = parser.parse_args()

    print("=" * 55)
    print("STATSBOMB CORNER SEQUENCE AUDIT")
    print("=" * 55)

    corners = load_csv(CORNER_FILE)
    audit_rows = load_csv(EVENT_AUDIT_FILE)

    # Group event rows by corner ID.
    grouped_events = defaultdict(list)

    for row in audit_rows:
        grouped_events[row["corner_id"]].append(row)

    print(f"\nTotal extracted corners: {len(corners)}")
    print(f"Audit event records: {len(audit_rows)}")

    sample = select_sample(
        corners,
        args.sample_size
    )

    print(f"Selected sample: {len(sample)}")

    results = []

    for number, corner in enumerate(sample, start=1):

        corner_id = corner.get("corner_id", "")

        print(
            f"Auditing {number}/{len(sample)}: {corner_id}"
        )

        result = audit_corner(
            corner,
            grouped_events.get(corner_id, [])
        )

        results.append(result)

    # Save detailed results.
    results_path = OUTPUT_DIR / "audit_results.csv"

    fieldnames = list(results[0].keys()) if results else []

    with open(
        results_path,
        "w",
        encoding="utf-8",
        newline=""
    ) as file:

        writer = csv.DictWriter(
            file,
            fieldnames=fieldnames
        )

        writer.writeheader()
        writer.writerows(results)

    # Summary.
    statuses = Counter(
        result["audit_status"]
        for result in results
    )

    print("\n" + "=" * 55)
    print("AUDIT SUMMARY")
    print("=" * 55)

    print(f"Total audited: {len(results)}")
    print(f"PASS: {statuses['PASS']}")
    print(f"REVIEW: {statuses['REVIEW']}")
    print(f"FAIL: {statuses['FAIL']}")

    print("\nOutcome comparison:")

    for outcome, count in Counter(
        result["original_outcome"]
        for result in results
    ).items():

        print(f"{outcome}: {count}")

    print("\nResults saved to:")
    print(results_path)

    print("\nAudit completed.")


if __name__ == "__main__":
    main()
