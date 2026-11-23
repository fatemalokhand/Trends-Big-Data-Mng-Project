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

## Baseline (Phase 1 result)

Produced by `baseline.py`; full output in `outputs/baseline_report.md` and `outputs/baseline_metrics.csv`.

**Target.** `shot = 1` if the attacking team takes at least one shot within the corner sequence (15 s / 10 on-ball actions, or earlier terminal event), else `0`. A goal counts as a shot. All 1,030 corners are eligible.

**Split.** By match, not by corner, so corners from one game never appear in two splits. Matches are shuffled with seed 42 inside each competition and assigned 70 / 15 / 15. The assignment is saved in `outputs/match_split.csv` and the `split` column of `outputs/model_dataset.csv`.

| Split | Matches | Corners | Shot rate |
|---|---:|---:|---:|
| train | 81 | 747 | 31.7% |
| validation | 18 | 138 | 31.2% |
| test | 16 | 145 | 35.2% |

**Baselines.** Both are fit on the training split only.

- `majority_class`: always predict "no shot" (the training majority).
- `training_shot_rate`: predict P(shot) = **0.3173** for every corner.

| Split | Baseline | Accuracy | Balanced acc. | Log loss | Brier | ROC AUC |
|---|---|---:|---:|---:|---:|---:|
| validation | majority_class | 0.688 | 0.500 | 10.762 | 0.312 | 0.50 |
| validation | training_shot_rate | 0.688 | 0.500 | 0.620 | 0.214 | 0.50 |
| test | majority_class | 0.648 | 0.500 | 12.148 | 0.352 | 0.50 |
| test | training_shot_rate | 0.648 | 0.500 | **0.651** | **0.229** | 0.50 |

The majority-class log loss is huge because it gives probability 0 to every shot. It is only an accuracy floor. The number to beat is the `training_shot_rate` row.

**Success bar for Phase 2.** A model adds value only if, on the test split, it has log loss below **0.651**, Brier below **0.229**, and ROC AUC above **0.50**, with a bootstrap 95% interval reported. Accuracy alone is not enough: always guessing "no shot" already scores 65-69%.

## Phase 2 handoff

### Phase 2 scope (from the P6-a spec)

1. Cluster static corner setups (delivery + 360 snapshot).
2. Estimate per-team delivery and outcome distributions.
3. Train an outcome model and compare it with the baselines above.
4. Build the scouting-dossier skeleton and the first descriptive write-up.

No tracking data is needed. Runs, marking schemes, and defensive optimization belong to P6-b / P6-c.

### Files to start from

| File | Use | Join key |
|---|---|---|
| `outputs/model_dataset.csv` | main table: one row per corner with features, labels, split | `corner_id` |
| `outputs/corner_360_features.csv` | 360 coverage, visible player counts, `passes_filter` | `corner_id` |
| `outputs/sequence_events_audit.csv` | every event in every sequence, if you need sequence-level detail | `corner_id` |
| `outputs/match_split.csv` | match to split mapping | `competition`, `match_id` |

Regenerate everything with the commands in "Reproduce Phase 1". Do not hand-edit outputs.

### Which columns are safe as model inputs

Only use information known at the moment of delivery. Anything describing what happened afterwards leaks the label.

| Allowed features | Do **not** use as features (leak the outcome) |
|---|---|
| `corner_side`, `technique`, `delivery_type`, `is_short`, `pass_height`, `body_part`, `pass_length`, `end_x`, `end_y`, `target_zone`, `period`, `minute`, `competition`, `attacking_team` (with shrinkage) | `outcome`, `terminal_reason`, `shot`, `goal`, `sequence_action_count`, `elapsed_seconds`, `delivery_outcome`, `delivery_completed`, `led_to_shot_assist` |
| 360 (only where `passes_filter = 1`): `box_coverage`, `six_yard_coverage`, `visible_attackers_box`, `visible_defenders_box`, `keeper_visible` | `first_shot_xg` (in `corner_sequences.csv`) |

`end_x`, `end_y` and `target_zone` describe where the delivery was aimed or landed. Treat them as delivery features, and state that in the write-up.

### Recommended model and evaluation

- **Model.** L2-regularized logistic regression for `shot`. Tune the regularization strength on the validation split, and optionally compare a gradient-boosted tree.
- **Comparisons.**
  - The two Phase 1 baselines.
  - A **delivery-only** logistic model using `corner_side`, `delivery_type`, `pass_height` and `target_zone`.
  - The full model (delivery + 360 features), fit on the 360-filtered subset. Report the delivery-only model on that same subset too, so the comparison is fair.
- **Metrics.** Log loss and Brier (primary), ROC AUC, balanced accuracy, and a calibration curve. Report bootstrap 95% intervals resampled by match.
- **Rules.** Fit on train, select on validation, and evaluate on test **once**. Never compute rates, encodings or scalers on validation or test data.

### Descriptive starting points (training split only)

| Delivery type | Corners | Shot rate |
|---|---:|---:|
| outswinging | 278 | 39.2% |
| straight | 22 | 40.9% |
| inswinging | 307 | 29.0% |
| short | 110 | 22.7% |
| not recorded | 30 | 16.7% |

| Target zone | Corners | Shot rate |
|---|---:|---:|
| penalty_spot_area | 316 | 42.4% |
| near_post | 113 | 26.5% |
| outside_box | 138 | 21.0% |
| central_six_yard | 79 | 19.0% |
| near_box_wide | 52 | 21.2% |
| far_post | 20 | 15.0% |
| far_box_wide | 18 | 55.6% |
| edge_of_box | 11 | 45.5% |

Small groups (under ~30 corners) are unreliable; report them with intervals or merge them.

### Sample size per team

44 teams; median 20 corners per team (range 1-68). 22 teams have at least 20 corners, and 13 have at least 30. The most corners belong to Spain (68), Denmark (60), Switzerland (56), England (54) and France (53).

- For per-team distributions, shrink each team's rates toward the overall rate (for example a Beta prior centred on 0.317). Show the raw count next to every team figure.
- Pick dossier opponents from teams with 30 or more corners.

### Clustering plan

- **Features.** One-hot `corner_side`, `delivery_type`, `pass_height` and `target_zone`, plus standardized `pass_length`, `end_x` and `end_y`. On the 360 subset, add the visible-player counts. Never include outcome columns.
- **Data.** Delivery-only clustering can use all 1,030 corners. 360 clustering uses only the 534 corners with `passes_filter = 1`.
- **Method.** K-Means as the main method. Use Gower distance with hierarchical clustering or PAM as a robustness check.
- **Choosing k.** Try k = 2-10. Use silhouette (primary), Calinski-Harabasz, Davies-Bouldin and the elbow plot. Add bootstrap stability (adjusted Rand index across resamples), and require clusters to be tactically readable.
- **After clustering.** Attach shot rates per cluster, with intervals.

### 360 visible-area filter

A corner is used for 360 features only if its freeze frame exists and the `visible_area` polygon covers at least **80%** of the attacking penalty area (x >= 102, 18 <= y <= 62).

- 558 of 1,030 corners have a frame, and 534 pass the filter.
- Counts include visible players only. Unseen players are unknown, not absent.
- For sensitivity, the 90% threshold keeps 388 corners (see `outputs/three_sixty_report.md`).

### Known limitations to carry forward

- About 52% of corners have usable 360 data, so any 360 result applies to that subset.
- A defence foul in the box (possible penalty) is labelled `shot = 0`.
- The 15 s / 10-action window is a modelling choice. In the audit sample, 1 of 68 negative corners had a shot shortly after the cutoff.
- The audit cross-check is automated. The manual sign-off columns (`reviewer_ok`, `reviewer`) in `outputs/audit_results.csv` still need to be filled in.
- Open Data covers 2 tournaments and 115 matches, so team samples are small and results are associations, not causes.

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
