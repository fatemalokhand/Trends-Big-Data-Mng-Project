"""Match-level split and baselines for the binary target `shot`.

Target: shot = 1 if the attacking team records at least one shot within the
corner sequence (see METHODOLOGY.md), else 0.

Split: matches (not corners) are assigned 70 / 15 / 15 to train / validation /
test, separately within each competition, with a fixed seed. All corners from
one match stay in one split.

Baselines (fit on TRAIN only, evaluated on validation and test):
  - majority_class: always predicts the most frequent training label;
    as a probability it predicts 1.0 for that class (log loss is then
    clipped, which shows why a constant label is a poor probabilistic model)
  - training_shot_rate: predicts P(shot) = training-set shot rate for every corner

Outputs:
  outputs/match_split.csv
  outputs/model_dataset.csv     corners + labels + split, ready for Phase 2
  outputs/baseline_metrics.csv
  outputs/baseline_report.md
Run:  python baseline.py
"""

import csv
import math
import random
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUT = BASE_DIR / "outputs"
SEED = 42
FRACTIONS = (0.70, 0.15, 0.15)
EPS = 1e-15


def read(name):
    return list(csv.DictReader(open(OUT / name, encoding="utf-8")))


def split_matches(seqs):
    by_comp = defaultdict(set)
    for s in seqs:
        by_comp[s["competition"]].add(s["match_id"])
    rng = random.Random(SEED)
    assign = {}
    for comp in sorted(by_comp):
        ids = sorted(by_comp[comp])
        rng.shuffle(ids)
        n_tr = round(len(ids) * FRACTIONS[0])
        n_va = round(len(ids) * FRACTIONS[1])
        for i, m in enumerate(ids):
            assign[(comp, m)] = "train" if i < n_tr else "validation" if i < n_tr + n_va else "test"
    return assign


def metrics(y, p):
    n = len(y)
    pc = [min(max(q, EPS), 1 - EPS) for q in p]
    pred = [int(q >= 0.5) for q in p]
    tp = sum(a == b == 1 for a, b in zip(y, pred))
    tn = sum(a == b == 0 for a, b in zip(y, pred))
    pos = sum(y)
    return {
        "n": n,
        "shot_rate": round(pos / n, 4),
        "accuracy": round((tp + tn) / n, 4),
        "balanced_accuracy": round(0.5 * (tp / pos if pos else 0) + 0.5 * (tn / (n - pos) if n - pos else 0), 4),
        "log_loss": round(-sum(a * math.log(q) + (1 - a) * math.log(1 - q) for a, q in zip(y, pc)) / n, 4),
        "brier": round(sum((q - a) ** 2 for a, q in zip(y, p)) / n, 4),
        "roc_auc": 0.5,  # constant predictors cannot rank corners
    }


def main():
    seqs = read("corner_sequences.csv")
    corners = {c["corner_id"]: c for c in read("corners.csv")}
    assign = split_matches(seqs)

    with open(OUT / "match_split.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["competition", "match_id", "split"])
        for (c, m), s in sorted(assign.items()):
            w.writerow([c, m, s])

    rows = []
    for s in seqs:
        if s["eligible"] != "1":
            continue
        rows.append({**corners[s["corner_id"]],
                     **{k: s[k] for k in ["outcome", "terminal_reason", "shot", "goal",
                                          "sequence_action_count", "elapsed_seconds"]},
                     "split": assign[(s["competition"], s["match_id"])]})
    with open(OUT / "model_dataset.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    data = defaultdict(list)
    for r in rows:
        data[r["split"]].append(int(r["shot"]))
    train_rate = sum(data["train"]) / len(data["train"])
    majority = int(train_rate >= 0.5)

    results = []
    for split in ["train", "validation", "test"]:
        y = data[split]
        for name, p in [("majority_class", [float(majority)] * len(y)),
                        ("training_shot_rate", [train_rate] * len(y))]:
            results.append({"split": split, "baseline": name, **metrics(y, p)})

    with open(OUT / "baseline_metrics.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=results[0].keys())
        w.writeheader()
        w.writerows(results)

    n_matches = defaultdict(int)
    for v in assign.values():
        n_matches[v] += 1
    lines = ["# Baseline report", "",
             f"Target: `shot` (1 = attacking-team shot within the corner sequence). Seed {SEED}.", "",
             "## Split (by match, stratified by competition)", "",
             "| Split | Matches | Corners | Shot rate |", "|---|---:|---:|---:|"]
    for s in ["train", "validation", "test"]:
        lines.append(f"| {s} | {n_matches[s]} | {len(data[s])} | {sum(data[s]) / len(data[s]):.1%} |")
    lines += ["", f"Training shot rate: **{train_rate:.4f}**. Majority class: "
              f"**{'shot' if majority else 'no shot'}**.", "",
              "## Metrics", "",
              "| Split | Baseline | Accuracy | Balanced acc. | Log loss | Brier | ROC AUC |",
              "|---|---|---:|---:|---:|---:|---:|"]
    for r in results:
        lines.append(f"| {r['split']} | {r['baseline']} | {r['accuracy']:.3f} | {r['balanced_accuracy']:.3f} | "
                     f"{r['log_loss']:.3f} | {r['brier']:.3f} | {r['roc_auc']:.2f} |")
    lines += ["", "## Bar for Phase 2", "",
              "A Phase 2 model is useful only if, on the **test** split, it beats `training_shot_rate` on "
              "log loss and Brier score (and has ROC AUC above 0.5). The majority-class baseline sets the "
              "accuracy floor; its log loss is very large because it assigns probability 0 to every shot.",
              "", "The test split must not be used for model selection; use validation for that."]
    (OUT / "baseline_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
