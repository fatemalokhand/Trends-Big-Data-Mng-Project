# Phase 1 exit criteria and status

| # | Criterion | Status | Evidence |
|---|---|---|---|
| 1 | Dataset selected and downloaded (World Cup 2022, Euro 2020) | Met | `data/`, `available_competitions.csv`, `check_data.py` |
| 2 | 115 match files identified; 1,030 unique corners, each linked to its raw event | Met | `outputs/validation_report.md` |
| 3 | Exactly one delivery record per corner; completion status derived and documented | Met | `outputs/corners.csv`, METHODOLOGY.md |
| 4 | Every corner has a sequence with start, included events, terminal event, elapsed time, label, and reason | Met | `outputs/corner_sequences.csv`, `outputs/sequence_events_audit.csv` |
| 5 | Termination rules and 15 s / 10-action cutoff documented and enforced | Met | METHODOLOGY.md; validation checks "no sequence exceeds 15 s / 10 actions" pass |
| 6 | At least 100 sequences audited for membership, order, terminal event, outcome, and cutoff | Met (automated); human sign-off pending | `outputs/audit_report.md`: 100/100 on all checks (95% CI 96.3-100%) |
| 7 | Binary target and eligibility finalized | Met | `shot`: 331 / 1,030 = 32.1%; all corners eligible |
| 8 | Match-level train/validation/test split saved | Met | `outputs/match_split.csv` |
| 9 | Majority-class and training shot-rate baselines computed on train, reported on validation and test | Met | `outputs/baseline_report.md` |
| 10 | 360 availability assessed and visible-area filter defined | Met | `outputs/three_sixty_report.md`, `outputs/corner_360_features.csv` |
| 11 | Clean modelling dataset saved | Met | `outputs/model_dataset.csv` (+ join `corner_360_features.csv` on `corner_id`) |
| 12 | README and methodology complete; outputs regenerate from commands | Met | README.md, METHODOLOGY.md |

## Remaining team action

- Two teammates each read about half of `outputs/audit_sheet.md` against the raw events and fill `reviewer_ok` / `reviewer` in `outputs/audit_results.csv`. Phase 1 is formally closed when this is done.

## Out of scope for Phase 1

Clustering, the predictive model, and the scouting dossier start in Phase 2 using `model_dataset.csv` and the 360 filter above.
