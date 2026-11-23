# Baseline report

Target: `shot` (1 = attacking-team shot within the corner sequence). Seed 42.

## Split (by match, stratified by competition)

| Split | Matches | Corners | Shot rate |
|---|---:|---:|---:|
| train | 81 | 747 | 31.7% |
| validation | 18 | 138 | 31.2% |
| test | 16 | 145 | 35.2% |

Training shot rate: **0.3173**. Majority class: **no shot**.

## Metrics

| Split | Baseline | Accuracy | Balanced acc. | Log loss | Brier | ROC AUC |
|---|---|---:|---:|---:|---:|---:|
| train | majority_class | 0.683 | 0.500 | 10.958 | 0.317 | 0.50 |
| train | training_shot_rate | 0.683 | 0.500 | 0.625 | 0.217 | 0.50 |
| validation | majority_class | 0.688 | 0.500 | 10.762 | 0.312 | 0.50 |
| validation | training_shot_rate | 0.688 | 0.500 | 0.620 | 0.214 | 0.50 |
| test | majority_class | 0.648 | 0.500 | 12.148 | 0.352 | 0.50 |
| test | training_shot_rate | 0.648 | 0.500 | 0.651 | 0.229 | 0.50 |

## Bar for Phase 2

A Phase 2 model is useful only if, on the **test** split, it beats `training_shot_rate` on log loss and Brier score (and has ROC AUC above 0.5). The majority-class baseline sets the accuracy floor; its log loss is very large because it assigns probability 0 to every shot.

The test split must not be used for model selection; use validation for that.
