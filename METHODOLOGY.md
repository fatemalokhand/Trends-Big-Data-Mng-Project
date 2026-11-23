# Phase 1 methodology (P6-a)

All rules below are implemented in `extract_corners.py` and re-implemented independently in `audit_corners.py`.

## Data

StatsBomb Open Data, FIFA World Cup 2022 (64 matches) and UEFA Euro 2020 (51 matches): 115 event files and 115 360 files. Coverage is whatever StatsBomb publishes, not an official competition total. Coordinates use the 120 x 80 StatsBomb pitch with the attacking team always moving toward x = 120.

## Corner identification

A corner is an event with `type.name == "Pass"` and `pass.type.name == "Corner"`. `corner_id = "<competition>_<match_id>_<event uuid>"`. Result: 1,030 corners (World Cup 569, Euro 461), all unique, every match contains at least one.

## Delivery features (`outputs/corners.csv`)

| Field | Definition |
|---|---|
| `corner_side` | `left` if the corner is taken from y < 40, else `right` |
| `technique` | `pass.technique`: Inswinging, Outswinging, Straight, or `Not recorded` |
| `is_short` | pass length < 25 and end location outside the penalty area |
| `delivery_type` | `short` if `is_short`, else the technique |
| `pass_height`, `body_part`, `pass_length`, `end_x`, `end_y` | from the pass object |
| `target_zone` | end location, mirrored so the corner is from the near side: `near_post`, `central_six_yard`, `far_post` (six-yard box split into thirds), `penalty_spot_area` (rest of box between the six-yard lines), `near_box_wide`, `far_box_wide`, `edge_of_box` (90 <= x < 102), `outside_box` |
| `delivery_outcome` / `delivery_completed` | StatsBomb omits `pass.outcome` for completed passes, so missing = `Complete`; otherwise the outcome name (Incomplete, Out, Pass Offside, Unknown) |

## Sequence reconstruction

Events are processed in raw `index` order starting immediately after the corner. For each next event, in this order:

1. **Period end**: a different period or a `Half End` event ends the sequence (`no_shot`, `period_end`).
2. **Restart**: a pass of type Goal Kick, Throw-in, Free Kick, Corner, or Kick Off ends the sequence (`restart`). This is checked before the time limit, so a clearance out of play followed by a throw-in 20 s later is labelled `restart`, not a cutoff. The restart itself is not part of the sequence.
3. **Time cutoff**: if the event is more than **15 s** after the corner timestamp, stop (`no_shot`, `time_cutoff`). The event is not included.
4. The event is added to the sequence. It counts as an **action** unless it is bookkeeping: `Ball Receipt*`, `Pressure`, `Substitution`, `Tactical Shift`, `Injury Stoppage`, `Player On/Off`, `Bad Behaviour`, `Starting XI`, `Half Start`.
5. **Terminal events** (included in the sequence):
   - Attacking-team `Shot` -> `goal` if `shot.outcome == Goal`, else `shot_no_goal`.
   - Defending-team `Shot` -> `possession_loss`.
   - `Own Goal For/Against` in the attacking team's favour -> `own_goal`.
   - `Foul Committed` -> `foul_by_attack` or `foul_by_defence`.
   - `Offside`, or a pass with outcome `Pass Offside` -> `offside`.
   - `Referee Ball-Drop` -> `restart`.
   - StatsBomb `possession` number different from the corner's -> `possession_loss`. Defensive clearances that do not win control keep the attacking possession number, so a header away does not end the sequence on its own.
6. **Action cutoff**: when the sequence reaches **10 actions** (corner not counted), stop (`no_shot`, `action_cutoff`).

The original version counted every event, including `Ball Receipt*` and `Pressure`, and labelled 344 corners (33%) `no_clear_terminal_outcome`. Counting only on-ball actions and treating cutoffs as a defined label resolved all of them.

## Labels

| Outcome | Count | `shot` |
|---|---:|---:|
| shot_no_goal | 307 | 1 |
| goal | 24 | 1 |
| no_shot (time / action / period cutoff) | 290 | 0 |
| restart | 212 | 0 |
| possession_loss | 119 | 0 |
| foul_by_attack | 51 | 0 |
| foul_by_defence | 17 | 0 |
| offside | 10 | 0 |

**Binary target:** `shot = 1` if the attacking team records at least one shot inside the sequence (331 corners, 32.1%). `goal` is also stored (24). Own goals score `goal = 1, shot = 0` (none occurred). Every corner is eligible: a cutoff means "no shot within the window", which is a defined negative under the rule. The cutoff sensitivity check in `audit_report.md` measures what the rule excludes.

Known limitation: a foul by the defence inside the box can produce a penalty; it is labelled `shot = 0` because the penalty is a new set piece.

## Audit

`audit_corners.py` samples 100 corners stratified by competition x outcome (seed 42) and checks, against the raw JSON with a separate implementation: corner found, event membership, event order (contiguous raw indices), terminal event, outcome label, binary label, and cutoff behaviour (elapsed <= 15 s, actions <= 10, and when a time cutoff fired, the next raw event really is past 15 s). It also flags any attacking shot in the same possession shortly after the stopping point. Results with Wilson 95% intervals are in `outputs/audit_report.md`; `outputs/audit_sheet.md` lists every sampled sequence with the next excluded event for human sign-off (`reviewer_ok` column in `audit_results.csv`).

## Split and baselines

Matches are shuffled (seed 42) within each competition and assigned 70/15/15 to train/validation/test (81/18/16 matches, 747/138/145 corners). All corners from a match share a split. Baselines are fit on train only:

- `majority_class`: always "no shot".
- `training_shot_rate`: P(shot) = 0.3173 for every corner.

Metrics: accuracy, balanced accuracy, log loss, Brier score, ROC AUC. Phase 2 models must beat `training_shot_rate` on test log loss (0.651) and Brier score (0.229). Validation is for model selection; test is touched once.

## 360 visible-area filter

Freeze frames are joined to corners by event UUID. 558 corners (54.2%) have one. A frame is kept for clustering if its `visible_area` polygon covers **at least 80%** of the attacking penalty area (x >= 102, 18 <= y <= 62): 534 corners. Player counts (`visible_attackers_box`, `visible_defenders_box`, `keeper_visible`) count visible players only; unseen players are unknown, not absent. Sensitivity from 50% to 90% is reported in `outputs/three_sixty_report.md` (90% would drop to 388).
