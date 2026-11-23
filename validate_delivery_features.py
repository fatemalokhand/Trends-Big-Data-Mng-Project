
import csv
from pathlib import Path
from collections import Counter

# FILE PATHS

OUTPUT_DIR = Path("outputs")

DELIVERY_FILE = OUTPUT_DIR / "corner_delivery_features.csv"
SEQUENCE_FILE = OUTPUT_DIR / "corner_sequences.csv"
REPORT_FILE = OUTPUT_DIR / "delivery_feature_validation_report.txt"

# StatsBomb pitch dimensions
MAX_X = 120
MAX_Y = 80

# Numeric fields to check
NUMERIC_FIELDS = [
    "corner_x",
    "corner_y",
    "pass_end_x",
    "pass_end_y",
    "pass_length",
    "pass_angle",
]

# Categorical fields to summarize
CATEGORICAL_FIELDS = [
    "competition",
    "pass_type",
    "pass_height",
    "pass_technique",
    "pass_outcome",
    "recipient",
    "team",
]


# HELPER FUNCTIONS

def load_csv(file_path):
    """Load a CSV file and return its rows as dictionaries."""

    if not file_path.exists():
        raise FileNotFoundError(
            f"File not found: {file_path}"
        )

    with open(file_path, "r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)

        if reader.fieldnames is None:
            raise ValueError(f"No header found in {file_path}")

        return reader.fieldnames, list(reader)


def is_blank(value):
    return value is None or str(value).strip() == ""


def to_number(value):
    """Convert a value to float, or return None if invalid."""

    if is_blank(value):
        return None

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def format_number(value):
    if value is None:
        return "N/A"
    return f"{value:.2f}"


# MAIN VALIDATION

def main():

    print("=" * 60)
    print("CORNER DELIVERY FEATURE VALIDATION")
    print("=" * 60)

    delivery_fields, delivery_rows = load_csv(DELIVERY_FILE)
    sequence_fields, sequence_rows = load_csv(SEQUENCE_FILE)

    report = []

    def log(message=""):
        print(message)
        report.append(message)

    # 1. BASIC FILE CHECKS
    log("\n1. FILE SUMMARY")
    log("-" * 40)

    log(f"Delivery feature records: {len(delivery_rows)}")
    log(f"Corner sequence records:  {len(sequence_rows)}")

    required_fields = [
        "corner_id",
        "competition",
        "match_id",
    ]

    missing_delivery_fields = [
        field for field in required_fields
        if field not in delivery_fields
    ]

    missing_sequence_fields = [
        field for field in required_fields
        if field not in sequence_fields
    ]

    if missing_delivery_fields or missing_sequence_fields:
        log("\nERROR: Required columns are missing.")

        if missing_delivery_fields:
            log(f"Delivery file missing: {missing_delivery_fields}")

        if missing_sequence_fields:
            log(f"Sequence file missing: {missing_sequence_fields}")

        REPORT_FILE.write_text("\n".join(report), encoding="utf-8")
        return

    # 2. UNIQUE CORNER ID CHECK

    log("\n2. CORNER ID CHECK")
    log("-" * 40)

    delivery_ids = [
        row["corner_id"].strip()
        for row in delivery_rows
        if not is_blank(row.get("corner_id"))
    ]

    sequence_ids = [
        row["corner_id"].strip()
        for row in sequence_rows
        if not is_blank(row.get("corner_id"))
    ]

    delivery_counts = Counter(delivery_ids)
    sequence_counts = Counter(sequence_ids)

    delivery_duplicates = [
        corner_id for corner_id, count in delivery_counts.items()
        if count > 1
    ]

    sequence_duplicates = [
        corner_id for corner_id, count in sequence_counts.items()
        if count > 1
    ]

    log(f"Delivery IDs: {len(delivery_ids)}")
    log(f"Unique delivery IDs: {len(set(delivery_ids))}")
    log(f"Duplicate delivery IDs: {len(delivery_duplicates)}")

    log(f"Sequence IDs: {len(sequence_ids)}")
    log(f"Unique sequence IDs: {len(set(sequence_ids))}")
    log(f"Duplicate sequence IDs: {len(sequence_duplicates)}")

    if delivery_duplicates:
        log(f"Example delivery duplicates: {delivery_duplicates[:5]}")

    if sequence_duplicates:
        log(f"Example sequence duplicates: {sequence_duplicates[:5]}")

    # 3. JOIN CHECK

    log("\n3. DELIVERY-TO-SEQUENCE JOIN CHECK")
    log("-" * 40)

    delivery_id_set = set(delivery_ids)
    sequence_id_set = set(sequence_ids)

    matched_ids = delivery_id_set & sequence_id_set
    delivery_only = delivery_id_set - sequence_id_set
    sequence_only = sequence_id_set - delivery_id_set

    log(f"Matching corner IDs: {len(matched_ids)}")
    log(f"Delivery IDs without a sequence: {len(delivery_only)}")
    log(f"Sequence IDs without delivery features: {len(sequence_only)}")

    if delivery_only:
        log(f"Example delivery-only IDs: {list(delivery_only)[:5]}")

    if sequence_only:
        log(f"Example sequence-only IDs: {list(sequence_only)[:5]}")

    # 4. COMPETITION AND MATCH ID CONSISTENCY
    log("\n4. MATCH AND COMPETITION CONSISTENCY")
    log("-" * 40)

    sequence_lookup = {
        row["corner_id"].strip(): row
        for row in sequence_rows
        if not is_blank(row.get("corner_id"))
    }

    mismatch_count = 0

    for row in delivery_rows:
        corner_id = row.get("corner_id", "").strip()

        if corner_id not in sequence_lookup:
            continue

        sequence_row = sequence_lookup[corner_id]

        competition_match = (
            row.get("competition", "").strip()
            == sequence_row.get("competition", "").strip()
        )

        match_id_match = (
            row.get("match_id", "").strip()
            == sequence_row.get("match_id", "").strip()
        )

        if not competition_match or not match_id_match:
            mismatch_count += 1

            if mismatch_count <= 5:
                log(f"Mismatch for corner: {corner_id}")
                log(
                    f"  Delivery: {row.get('competition')} / "
                    f"{row.get('match_id')}"
                )
                log(
                    f"  Sequence: {sequence_row.get('competition')} / "
                    f"{sequence_row.get('match_id')}"
                )

    log(f"Competition/match mismatches: {mismatch_count}")

    # 5. FEATURE AVAILABILITY
    log("\n5. FEATURE AVAILABILITY")
    log("-" * 40)

    for field in delivery_fields:

        available = sum(
            not is_blank(row.get(field))
            for row in delivery_rows
        )

        missing = len(delivery_rows) - available

        log(
            f"{field}: {available} available, "
            f"{missing} missing"
        )

    # 6. CONSTANT OR FULLY MISSING FEATURES
    log("\n6. CONSTANT AND FULLY MISSING FEATURES")
    log("-" * 40)

    for field in delivery_fields:

        values = [
            row.get(field, "").strip()
            for row in delivery_rows
            if not is_blank(row.get(field))
        ]

        unique_values = set(values)

        if len(values) == 0:
            log(f"{field}: FULLY MISSING")

        elif len(unique_values) == 1:
            log(
                f"{field}: CONSTANT "
                f"(only value: {next(iter(unique_values))})"
            )

    # 7. COORDINATE AND NUMERIC VALIDATION
    log("\n7. NUMERIC AND COORDINATE VALIDATION")
    log("-" * 40)

    for field in NUMERIC_FIELDS:

        if field not in delivery_fields:
            log(f"{field}: COLUMN NOT FOUND")
            continue

        values = []
        invalid_count = 0
        missing_count = 0

        for row in delivery_rows:

            raw_value = row.get(field, "")

            if is_blank(raw_value):
                missing_count += 1
                continue

            number = to_number(raw_value)

            if number is None:
                invalid_count += 1
            else:
                values.append(number)

        if values:
            log(
                f"{field}: min={format_number(min(values))}, "
                f"max={format_number(max(values))}, "
                f"invalid={invalid_count}, "
                f"missing={missing_count}"
            )
        else:
            log(
                f"{field}: no valid numeric values, "
                f"invalid={invalid_count}, "
                f"missing={missing_count}"
            )

    coordinate_checks = {
        "corner_x": (0, MAX_X),
        "corner_y": (0, MAX_Y),
        "pass_end_x": (0, MAX_X),
        "pass_end_y": (0, MAX_Y),
    }

    log("\nCoordinate values outside pitch boundaries:")

    for field, (minimum, maximum) in coordinate_checks.items():

        if field not in delivery_fields:
            continue

        invalid_coordinates = []

        for row in delivery_rows:
            value = to_number(row.get(field))

            if value is not None and not minimum <= value <= maximum:
                invalid_coordinates.append(
                    (row.get("corner_id"), value)
                )

        log(f"{field}: {len(invalid_coordinates)} outside boundaries")

        if invalid_coordinates:
            log(f"  Examples: {invalid_coordinates[:5]}")

    # 8. CATEGORICAL FEATURE DISTRIBUTIONS
    log("\n8. CATEGORICAL FEATURE DISTRIBUTIONS")
    log("-" * 40)

    for field in CATEGORICAL_FIELDS:

        if field not in delivery_fields:
            continue

        counts = Counter(
            row.get(field, "").strip()
            if not is_blank(row.get(field))
            else "[MISSING]"
            for row in delivery_rows
        )

        log(f"\n{field}:")

        for value, count in counts.most_common():
            log(f"  {value}: {count}")

    # 9. FINAL SUMMARY
    log("\n9. VALIDATION SUMMARY")
    log("-" * 40)

    checks = {
        "Expected delivery record count (1030)": len(delivery_rows) == 1030,
        "No duplicate delivery IDs": len(delivery_duplicates) == 0,
        "No duplicate sequence IDs": len(sequence_duplicates) == 0,
        "All delivery IDs have sequences": len(delivery_only) == 0,
        "All sequence IDs have delivery features": len(sequence_only) == 0,
        "No match/competition mismatches": mismatch_count == 0,
    }

    for description, passed in checks.items():
        status = "PASS" if passed else "REVIEW"
        log(f"{status}: {description}")

    log("\nImportant:")
    log("- Missing values are not automatically errors.")
    log("- A constant feature may not help distinguish outcomes.")
    log("- Coordinates outside the pitch boundaries need investigation.")
    log("- Passing these checks does not replace manual sequence auditing.")

    REPORT_FILE.write_text("\n".join(report), encoding="utf-8")

    log(f"\nReport saved to: {REPORT_FILE}")


if __name__ == "__main__":
    main()
