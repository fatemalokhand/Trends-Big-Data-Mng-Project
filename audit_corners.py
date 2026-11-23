"""Audit a reproducible sample of corner sequences against the raw StatsBomb events.

For each sampled corner this script re-reads the original match JSON and checks,
using logic written independently of extract_corners.py:

  1. corner_found        the event ID exists in the raw file and is a corner pass
  2. membership_ok       the extracted event IDs equal the raw events between the
                         corner and the stopping point
  3. order_ok            extracted events are in raw `index` order, no gaps
  4. terminal_ok         the recorded terminal event / reason is what the raw data show
  5. outcome_ok          the outcome label and the binary `shot` label are correct
  6. cutoff_ok           elapsed time <= 15 s and on-ball actions <= 10, and when a
                         cutoff fired, the next raw event really is past the limit
  7. no_missed_shot      no attacking-team shot occurs in the same possession within
                         15 s after the stopping point (flags labels the cutoff hides)

Outputs:
  outputs/audit_sample.csv   the sampled corner IDs (fixed seed)
  outputs/audit_results.csv  one row per audited corner with every check
  outputs/audit_sheet.md     human-readable event listing for manual sign-off
  outputs/audit_report.md    summary with 95% confidence intervals

Run:  python audit_corners.py [--sample-size 100]
"""

import argparse
import csv
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
OUT = BASE_DIR / "outputs"
FOLDERS = {"World Cup 2022": BASE_DIR / "data" / "world_cup_2022" / "events",
           "Euro 2020": BASE_DIR / "data" / "euro_2020" / "events"}
SEED = 42
LIMIT_S, LIMIT_A = 15.0, 10
BOOKKEEPING = {"Ball Receipt*", "Pressure", "Substitution", "Tactical Shift", "Injury Stoppage",
               "Player Off", "Player On", "Bad Behaviour", "Starting XI", "Half Start"}
RESTARTS = {"Goal Kick", "Throw-in", "Free Kick", "Corner", "Kick Off"}


def nm(d, *path):
    for k in path:
        d = d.get(k, {}) if isinstance(d, dict) else {}
    return d.get("name", "") if isinstance(d, dict) else ""


def secs(ts):
    h, m, s = ts.split(":")
    return int(h) * 3600 + int(m) * 60 + float(s)


def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p = k / n
    d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0, c - h), min(1, c + h))


def expected(raw, ci):
    """Independent re-derivation of the stopping point. Returns dict."""
    c = raw[ci]
    team, poss, per, t0 = nm(c, "team"), c["possession"], c["period"], secs(c["timestamp"])
    ids, actions, j = [], 0, ci + 1
    while j < len(raw):
        e = raw[j]
        k, et = nm(e, "type"), nm(e, "team")
        ptype = nm(e, "pass", "type")
        if e["period"] != per or k == "Half End":
            return dict(ids=ids, reason="period_end", term=None, label="no_shot", stop=j)
        if k == "Pass" and ptype in RESTARTS:
            return dict(ids=ids, reason="restart", term=e, label="restart", stop=j)
        if secs(e["timestamp"]) - t0 > LIMIT_S:
            return dict(ids=ids, reason="time_cutoff", term=None, label="no_shot", stop=j)
        ids.append(e["id"])
        if k not in BOOKKEEPING:
            actions += 1
        label = None
        if k == "Shot":
            label = ("goal" if nm(e, "shot", "outcome") == "Goal" else "shot_no_goal") if et == team \
                else "possession_loss"
        elif k == "Own Goal For":
            label = "own_goal" if et == team else "possession_loss"
        elif k == "Own Goal Against":
            label = "own_goal" if et != team else "possession_loss"
        elif k == "Foul Committed":
            label = "foul_by_attack" if et == team else "foul_by_defence"
        elif k == "Offside" or nm(e, "pass", "outcome") == "Pass Offside":
            label = "offside"
        elif k == "Referee Ball-Drop":
            label = "restart"
        elif e["possession"] != poss:
            label = "possession_loss"
        if label:
            return dict(ids=ids, reason=k, term=e, label=label, stop=j + 1)
        if actions >= LIMIT_A:
            return dict(ids=ids, reason="action_cutoff", term=None, label="no_shot", stop=j + 1)
        j += 1
    return dict(ids=ids, reason="end_of_file", term=None, label="no_shot", stop=j)


def missed_shot(raw, ci, stop):
    """Attacking shot in the same possession within 15 s *after* the stopping point."""
    c = raw[ci]
    t_stop = secs(raw[stop - 1]["timestamp"]) if stop - 1 > ci else secs(c["timestamp"])
    for e in raw[stop:]:
        if e["period"] != c["period"] or e["possession"] != c["possession"]:
            return ""
        if secs(e["timestamp"]) - t_stop > LIMIT_S:
            return ""
        if nm(e, "type") == "Shot" and nm(e, "team") == nm(c, "team"):
            return e["id"]
    return ""


def sample(seqs, n):
    """Stratified by competition x outcome, proportional allocation, fixed seed."""
    rng = random.Random(SEED)
    strata = defaultdict(list)
    for s in seqs:
        strata[(s["competition"], s["outcome"])].append(s)
    share = {k: n * len(v) / len(seqs) for k, v in strata.items()}
    quota = {k: max(1, int(v)) for k, v in share.items()}
    for k in sorted(share, key=lambda k: share[k] - int(share[k]), reverse=True):
        if sum(quota.values()) >= n:
            break
        quota[k] += 1
    picked = []
    for k in sorted(strata):
        picked += rng.sample(strata[k], min(quota[k], len(strata[k])))
    return sorted(picked, key=lambda s: s["corner_id"])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample-size", type=int, default=100)
    n = ap.parse_args().sample_size

    seqs = list(csv.DictReader(open(OUT / "corner_sequences.csv", encoding="utf-8")))
    events = defaultdict(list)
    for r in csv.DictReader(open(OUT / "sequence_events_audit.csv", encoding="utf-8")):
        events[r["corner_id"]].append(r)
    picked = sample(seqs, n)
    raw_cache, results, sheet = {}, [], ["# Corner audit sheet", "",
                                         "One block per sampled corner. Reviewer: tick `reviewer_ok` in "
                                         "`audit_results.csv` after reading the raw events below.", ""]
    for s in picked:
        key = (s["competition"], s["match_id"])
        if key not in raw_cache:
            raw = json.load(open(FOLDERS[s["competition"]] / f"{s['match_id']}.json", encoding="utf-8"))
            raw.sort(key=lambda e: e["index"])
            raw_cache[key] = raw
        raw = raw_cache[key]
        rows = sorted(events[s["corner_id"]], key=lambda r: int(r["event_number"]))
        corner_eid = s["corner_id"].rsplit("_", 1)[1]
        pos = {e["id"]: i for i, e in enumerate(raw)}
        res = {"corner_id": s["corner_id"], "competition": s["competition"], "match_id": s["match_id"],
               "extracted_outcome": s["outcome"], "extracted_reason": s["terminal_reason"]}
        ci = pos.get(corner_eid)
        res["corner_found"] = int(ci is not None and nm(raw[ci], "pass", "type") == "Corner")
        if not res["corner_found"]:
            res.update(audit_status="FAIL", notes="corner not found")
            results.append(res)
            continue
        exp = expected(raw, ci)
        got = [r["event_id"] for r in rows[1:]]
        idx = [pos.get(g, -1) for g in got]
        res["membership_ok"] = int(got == exp["ids"])
        res["order_ok"] = int(idx == list(range(ci + 1, ci + 1 + len(idx))))
        res["expected_outcome"] = exp["label"]
        res["outcome_ok"] = int(exp["label"] == s["outcome"])
        res["shot_label_ok"] = int(int(exp["label"] in {"shot_no_goal", "goal"}) == int(s["shot"]))
        exp_term = exp["term"]["id"] if exp["term"] else ""
        res["terminal_ok"] = int(exp_term == s["terminal_event_id"])
        el = float(s["elapsed_seconds"])
        n_act = int(s["sequence_action_count"])
        cut_ok = el <= LIMIT_S and n_act <= LIMIT_A
        if s["terminal_reason"] == "time_cutoff":
            nxt = raw[ci + 1 + len(got)] if ci + 1 + len(got) < len(raw) else None
            cut_ok &= nxt is not None and secs(nxt["timestamp"]) - secs(raw[ci]["timestamp"]) > LIMIT_S
        if s["terminal_reason"] == "action_cutoff":
            cut_ok &= n_act == LIMIT_A
        res["cutoff_ok"] = int(cut_ok)
        res["missed_shot_event_id"] = missed_shot(raw, ci, exp["stop"]) if s["shot"] == "0" else ""
        checks = ["membership_ok", "order_ok", "outcome_ok", "shot_label_ok", "terminal_ok", "cutoff_ok"]
        res["audit_status"] = "PASS" if all(res[c] for c in checks) else "FAIL"
        res["notes"] = "cutoff hides a later shot in same possession" if res["missed_shot_event_id"] else ""
        res["reviewer_ok"] = ""
        res["reviewer"] = ""
        results.append(res)

        sheet += [f"## {s['corner_id']}", "",
                  f"Team: {s['attacking_team']} | outcome: `{s['outcome']}` | reason: `{s['terminal_reason']}` "
                  f"| shot: {s['shot']} | {el:.1f} s, {n_act} actions | audit: {res['audit_status']}", "",
                  "| # | raw index | type | team | time | possession | detail |", "|---|---|---|---|---|---|---|"]
        for r in rows:
            sheet.append(f"| {r['event_number']} | {r['event_index']} | {r['event_type']} | {r['team']} | "
                         f"{r['timestamp']} | {r['possession']} | {r['detail']} |")
        nxt = raw[ci + 1 + len(got)] if ci + 1 + len(got) < len(raw) else None
        if nxt is not None:
            sheet.append(f"| next (not included) | {nxt['index']} | {nm(nxt, 'type')} | {nm(nxt, 'team')} | "
                         f"{nxt['timestamp']} | {nxt['possession']} | {nm(nxt, 'pass', 'type')} |")
        sheet.append("")

    with open(OUT / "audit_sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["corner_id"])
        w.writerows([[s["corner_id"]] for s in picked])
    fields = list(dict.fromkeys(k for r in results for k in r))
    with open(OUT / "audit_results.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(results)
    (OUT / "audit_sheet.md").write_text("\n".join(sheet) + "\n", encoding="utf-8")

    total = len(results)
    lines = ["# Audit report", "", f"Sample: {total} corners, stratified by competition x outcome, seed {SEED}.",
             "", "| Check | Passed | Rate | 95% CI (Wilson) |", "|---|---:|---:|---|"]
    for c in ["corner_found", "membership_ok", "order_ok", "terminal_ok", "outcome_ok",
              "shot_label_ok", "cutoff_ok"]:
        k = sum(int(r.get(c, 0)) for r in results)
        lo, hi = wilson(k, total)
        lines.append(f"| {c} | {k}/{total} | {k / total:.1%} | {lo:.1%} - {hi:.1%} |")
    k = sum(r["audit_status"] == "PASS" for r in results)
    lo, hi = wilson(k, total)
    lines += [f"| **all checks** | {k}/{total} | {k / total:.1%} | {lo:.1%} - {hi:.1%} |", "",
              "## Sample composition", "", "| Outcome | n |", "|---|---:|"]
    lines += [f"| {o} | {c} |" for o, c in Counter(r["extracted_outcome"] for r in results).most_common()]
    missed = [r for r in results if r.get("missed_shot_event_id")]
    lines += ["", "## Cutoff sensitivity", "",
              f"{len(missed)} of {sum(1 for s in picked if s['shot'] == '0')} sampled `shot = 0` corners have an "
              "attacking shot in the same possession shortly after the stopping point. These are correct under "
              "the pre-registered rule but show what the cutoff excludes.", ""]
    lines += [f"- {r['corner_id']} (shot event {r['missed_shot_event_id']})" for r in missed]
    fails = [r for r in results if r["audit_status"] != "PASS"]
    lines += ["", "## Failures", ""] + ([f"- {r['corner_id']}: {r}" for r in fails] or ["None."])
    (OUT / "audit_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
