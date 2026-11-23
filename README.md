# Trends-Big-Data-Mng-Project

COMP 4900H, P6-a: corner-kick analytics on StatsBomb Open Data.

Phase 1 builds a validated dataset of corner kicks and their outcome sequences and sets the baseline for the question:

> Does a corner kick lead to a shot by the attacking team?

Rules and definitions: [METHODOLOGY.md](METHODOLOGY.md). Phase 1 status: [EXIT_CRITERIA.md](EXIT_CRITERIA.md).

## Results at a glance

- 115 matches (World Cup 2022: 64, Euro 2020: 51), 1,030 corners.
- 331 corners (32.1%) produce a shot within the sequence; 24 produce a goal.
- Audit of 100 stratified sequences: 100/100 pass all checks (95% CI 96.3-100%).
- Baseline to beat on test matches: log loss 0.651, Brier 0.229 (constant training shot rate 0.317).
- 558 corners have a 360 freeze frame; 534 pass the 80% penalty-area visibility filter.

## Repository layout

```
data/
  euro_2020/{events,matches,three-sixty}/
  world_cup_2022/{events,matches,three-sixty}/
outputs/                       generated, see below
available_competitions.csv     competition / season list
choosedataset.py               list StatsBomb competitions
download_data.py               download events + 360 for a competition/season
check_data.py                  count downloaded files
extract_corners.py             corners, delivery features, sequences, validation report
audit_corners.py               100-sequence audit against raw events
baseline.py                    match-level split + baselines
three_sixty.py                 360 availability + visible-area filter
METHODOLOGY.md
EXIT_CRITERIA.md
```

## Reproduce Phase 1

From the repo root (Python 3.10+):

```
pip install -r requirements.txt
python check_data.py
python extract_corners.py
python audit_corners.py
python baseline.py
python three_sixty.py
```

Every script is deterministic (seed 42).

## Outputs

| File | Contents |
|---|---|
| `corners.csv` | one row per corner: IDs, team, taker, side, technique, short flag, height, length, end location, target zone, delivery outcome |
| `corner_sequences.csv` | one row per corner: event/action counts, elapsed seconds, terminal event, reason, outcome, `shot`, `goal`, first-shot xG |
| `sequence_events_audit.csv` | every event in every sequence, with raw index and possession number |
| `validation_report.md` | counts, integrity checks, label and delivery distributions |
| `audit_sample.csv`, `audit_results.csv`, `audit_report.md`, `audit_sheet.md` | audit sample, per-corner checks, summary, human-readable sheet |
| `match_split.csv` | match -> train / validation / test |
| `model_dataset.csv` | corners + labels + split, ready for Phase 2 |
| `baseline_metrics.csv`, `baseline_report.md` | baseline results |
| `corner_360_features.csv`, `three_sixty_report.md` | 360 coverage, visible player counts, filter flag |

## Data source

[StatsBomb Open Data](https://github.com/statsbomb/open-data). Open Data contains selected matches, so counts describe this dataset, not full competitions. 360 frames show only players visible on the broadcast, so counts from them are lower bounds.
