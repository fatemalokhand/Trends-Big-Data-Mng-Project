# Audit report

Sample: 100 corners, stratified by competition x outcome, seed 42.

| Check | Passed | Rate | 95% CI (Wilson) |
|---|---:|---:|---|
| corner_found | 100/100 | 100.0% | 96.3% - 100.0% |
| membership_ok | 100/100 | 100.0% | 96.3% - 100.0% |
| order_ok | 100/100 | 100.0% | 96.3% - 100.0% |
| terminal_ok | 100/100 | 100.0% | 96.3% - 100.0% |
| outcome_ok | 100/100 | 100.0% | 96.3% - 100.0% |
| shot_label_ok | 100/100 | 100.0% | 96.3% - 100.0% |
| cutoff_ok | 100/100 | 100.0% | 96.3% - 100.0% |
| **all checks** | 100/100 | 100.0% | 96.3% - 100.0% |

## Sample composition

| Outcome | n |
|---|---:|
| shot_no_goal | 30 |
| no_shot | 28 |
| restart | 20 |
| possession_loss | 11 |
| foul_by_attack | 5 |
| goal | 2 |
| foul_by_defence | 2 |
| offside | 2 |

## Cutoff sensitivity

1 of 68 sampled `shot = 0` corners have an attacking shot in the same possession shortly after the stopping point. These are correct under the pre-registered rule but show what the cutoff excludes.

- World Cup 2022_3869220_12ec4f13-1469-47c8-bcc3-bf5620a274bd (shot event 79542497-53b6-4d25-8a88-d0c18a6d453a)

## Failures

None.
