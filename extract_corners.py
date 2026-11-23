"""Phase 1 corner extraction for P6-a.

Reads StatsBomb event JSON for every downloaded match and writes:

  outputs/corners.csv               one row per corner: identifiers + delivery features
  outputs/corner_sequences.csv      one row per corner: sequence summary + outcome labels
  outputs/sequence_events_audit.csv one row per event in each sequence (for auditing)
  outputs/validation_report.md      counts and integrity checks

Sequence rules are documented in METHODOLOGY.md. Run from the repo root:
    python extract_corners.py
"""

import csv
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DATASETS = {
    "World Cup 2022": BASE_DIR / "data" / "world_cup_2022",
    "Euro 2020": BASE_DIR / "data" / "euro_2020",
}
OUT = BASE_DIR / "outputs"
OUT.mkdir(exist_ok=True)

MAX_SECONDS = 15   # time cutoff, measured from the corner's timestamp
MAX_ACTIONS = 10   # on-ball action cutoff (corner itself not counted)

# Events that do not count toward the 10-action cutoff. They are bookkeeping
# or off-ball records and would otherwise inflate the count (e.g. every pass is
# followed by a "Ball Receipt*").
NON_ACTION_TYPES = {
    "Ball Receipt*", "Pressure", "Substitution", "Tactical Shift",
    "Injury Stoppage", "Player Off", "Player On", "Bad Behaviour",
    "Starting XI", "Half Start",
}
RESTART_PASS_TYPES = {"Goal Kick", "Throw-in", "Free Kick", "Corner", "Kick Off"}

# StatsBomb pitch: 120 x 80. Penalty area: x >= 102, 18 <= y <= 62.
# Six-yard box: x >= 114, 30 <= y <= 50.


def name(value):
    return value.get("name", "") if isinstance(value, dict) else ""


def seconds(ts):
    try:
        t = datetime.strptime(ts, "%H:%M:%S.%f")
    except (TypeError, ValueError):
        return None
    return t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1e6


def is_corner(e):
    return name(e.get("type")) == "Pass" and name(e.get("pass", {}).get("type")) == "Corner"


# ----------------------------------------------------------------------------
# Delivery features
# ----------------------------------------------------------------------------

def in_box(x, y):
    return x >= 102 and 18 <= y <= 62


def target_zone(corner_y, end):
    """Zone of the delivery's end location, relative to the corner side."""
    if not end:
        return "unknown"
    x, y = end[0], end[1]
    # Mirror so the corner is always taken from y = 0 ("near" side = small y).
    if corner_y > 40:
        y = 80 - y
    if x >= 114 and 30 <= y <= 50:
        if y < 36.67:
            return "near_post"
        if y <= 43.33:
            return "central_six_yard"
        return "far_post"
    if in_box(x, y):
        if 30 <= y <= 50:
            return "penalty_spot_area"
        return "near_box_wide" if y < 30 else "far_box_wide"
    if 90 <= x < 102 and 18 <= y <= 62:
        return "edge_of_box"
    return "outside_box"


def delivery_features(e):
    p = e.get("pass", {})
    loc = e.get("location") or [None, None]
    end = p.get("end_location")
    length = p.get("length")
    zone = target_zone(loc[1] if loc[1] is not None else 0, end)
    short = bool(length is not None and length < 25 and zone in {"outside_box", "edge_of_box"})
    technique = name(p.get("technique")) or "Not recorded"
    return {
        "corner_side": "left" if (loc[1] or 0) < 40 else "right",  # from attacker's view toward goal at x=120
        "technique": technique,
        "is_short": int(short),
        "delivery_type": "short" if short else technique.lower().replace(" ", "_"),
        "pass_height": name(p.get("height")),
        "body_part": name(p.get("body_part")),
        "pass_length": round(length, 2) if length is not None else "",
        "end_x": end[0] if end else "",
        "end_y": end[1] if end else "",
        "target_zone": zone,
        # StatsBomb omits pass.outcome when the pass is completed.
        "delivery_outcome": name(p.get("outcome")) or "Complete",
        "delivery_completed": int(not p.get("outcome")),
        "led_to_shot_assist": int(bool(p.get("shot_assist") or p.get("goal_assist"))),
    }


# ----------------------------------------------------------------------------
# Sequence reconstruction
# ----------------------------------------------------------------------------

def find_sequence(events, i):
    """Return (sequence_events, outcome, terminal_reason, terminal_event, elapsed, n_actions)."""
    corner = events[i]
    team = name(corner.get("team"))
    possession = corner.get("possession")
    period = corner.get("period")
    t0 = seconds(corner.get("timestamp"))
    seq, n_actions, elapsed = [], 0, 0.0

    def done(outcome, reason, ev=None):
        return seq, outcome, reason, ev, round(elapsed, 3), n_actions

    for e in events[i + 1:]:
        etype = name(e.get("type"))
        if e.get("period") != period or etype == "Half End":
            return done("no_shot", "period_end")
        # A restart ends the sequence even when it is taken after the time
        # window (e.g. ball cleared out, throw-in taken 20 s later).
        if etype == "Pass" and name(e.get("pass", {}).get("type")) in RESTART_PASS_TYPES:
            return done("restart", "restart_" + name(e["pass"]["type"]).lower().replace(" ", "_"), e)
        t = seconds(e.get("timestamp"))
        if t0 is not None and t is not None:
            if t - t0 > MAX_SECONDS:
                return done("no_shot", "time_cutoff")
            elapsed = max(elapsed, t - t0)

        seq.append(e)
        eteam = name(e.get("team"))
        if etype not in NON_ACTION_TYPES:
            n_actions += 1

        if etype == "Shot":
            if eteam == team:
                goal = name(e.get("shot", {}).get("outcome")) == "Goal"
                return done("goal" if goal else "shot_no_goal", "shot", e)
            return done("possession_loss", "opponent_shot", e)
        if etype in {"Own Goal Against", "Own Goal For"}:
            scored_for_attack = (etype == "Own Goal For") == (eteam == team)
            return done("own_goal" if scored_for_attack else "possession_loss", "own_goal", e)
        if etype == "Foul Committed":
            return done("foul_by_attack" if eteam == team else "foul_by_defence", "foul", e)
        if etype == "Offside" or name(e.get("pass", {}).get("outcome")) == "Pass Offside":
            return done("offside", "offside", e)
        if etype == "Referee Ball-Drop":
            return done("restart", "restart_drop_ball", e)
        if possession is not None and e.get("possession") != possession:
            return done("possession_loss", "possession_change", e)
        if n_actions >= MAX_ACTIONS:
            return done("no_shot", "action_cutoff")

    return done("no_shot", "end_of_file")


def main():
    corners, sequences, audit = [], [], []
    match_files = 0

    for competition, folder in DATASETS.items():
        files = sorted((folder / "events").glob("*.json"))
        match_files += len(files)
        for path in files:
            events = json.load(open(path, encoding="utf-8"))
            events.sort(key=lambda e: e.get("index", 0))
            match_id = path.stem
            for i, e in enumerate(events):
                if not is_corner(e):
                    continue
                cid = f"{competition}_{match_id}_{e['id']}"
                loc = e.get("location") or [None, None]
                base = {
                    "corner_id": cid,
                    "competition": competition,
                    "match_id": match_id,
                    "event_id": e["id"],
                    "period": e.get("period"),
                    "minute": e.get("minute"),
                    "corner_timestamp": e.get("timestamp"),
                    "attacking_team": name(e.get("team")),
                    "taker": name(e.get("player")),
                    "corner_x": loc[0],
                    "corner_y": loc[1],
                }
                corners.append({**base, **delivery_features(e)})

                seq, outcome, reason, term, elapsed, n_act = find_sequence(events, i)
                shot = int(outcome in {"shot_no_goal", "goal"})
                sequences.append({
                    "corner_id": cid,
                    "competition": competition,
                    "match_id": match_id,
                    "attacking_team": base["attacking_team"],
                    "sequence_event_count": len(seq),
                    "sequence_action_count": n_act,
                    "elapsed_seconds": elapsed,
                    "terminal_event_id": term["id"] if term else "",
                    "terminal_event_type": name(term.get("type")) if term else "",
                    "terminal_reason": reason,
                    "outcome": outcome,
                    "shot": shot,
                    "goal": int(outcome in {"goal", "own_goal"}),
                    "first_shot_xg": round(term["shot"].get("statsbomb_xg", 0), 4)
                    if term and name(term.get("type")) == "Shot" and shot else "",
                    "eligible": 1,  # every reconstructed corner has a defined label
                })
                audit.append({"corner_id": cid, "match_id": match_id, "event_number": 0,
                              "event_id": e["id"], "event_index": e.get("index"),
                              "event_type": "Corner", "team": base["attacking_team"],
                              "timestamp": e.get("timestamp"), "possession": e.get("possession"),
                              "detail": f"{corners[-1]['delivery_type']} -> {corners[-1]['target_zone']}"})
                for n, s in enumerate(seq, 1):
                    stype = name(s.get("type"))
                    detail = name(s.get("shot", {}).get("outcome")) if stype == "Shot" else \
                        name(s.get("pass", {}).get("type")) or name(s.get("pass", {}).get("outcome"))
                    audit.append({"corner_id": cid, "match_id": match_id, "event_number": n,
                                  "event_id": s["id"], "event_index": s.get("index"),
                                  "event_type": stype, "team": name(s.get("team")),
                                  "timestamp": s.get("timestamp"), "possession": s.get("possession"),
                                  "detail": detail})

    for fname, rows in [("corners.csv", corners), ("corner_sequences.csv", sequences),
                        ("sequence_events_audit.csv", audit)]:
        with open(OUT / fname, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=rows[0].keys())
            w.writeheader()
            w.writerows(rows)

    write_validation_report(match_files, corners, sequences, audit)
    print(f"Matches: {match_files}  Corners: {len(corners)}")
    print(Counter(s["outcome"] for s in sequences))


def write_validation_report(match_files, corners, sequences, audit):
    ids = [c["corner_id"] for c in corners]
    seq_ids = {s["corner_id"] for s in sequences}
    by_comp = Counter(c["competition"] for c in corners)
    matches_with_corners = len({(c["competition"], c["match_id"]) for c in corners})
    checks = [
        ("Corner IDs unique", len(ids) == len(set(ids))),
        ("Every corner has exactly one delivery record", len(corners) == len(set(ids))),
        ("Every corner has exactly one sequence record",
         len(sequences) == len(corners) and seq_ids == set(ids)),
        ("Every corner has a corner row in the event audit file",
         sum(1 for a in audit if a["event_number"] == 0) == len(corners)),
        ("No sequence exceeds 15 s", all(float(s["elapsed_seconds"]) <= MAX_SECONDS for s in sequences)),
        ("No sequence exceeds 10 actions", all(s["sequence_action_count"] <= MAX_ACTIONS for s in sequences)),
        ("Every corner has a label", all(s["outcome"] for s in sequences)),
    ]
    lines = ["# Phase 1 validation report", "",
             "Generated by `extract_corners.py`.", "",
             "## Counts", "",
             f"- Match event files: {match_files}",
             f"- Matches containing at least one corner: {matches_with_corners}",
             f"- Corners: {len(corners)} ({', '.join(f'{k}: {v}' for k, v in by_comp.items())})",
             f"- Sequence events (incl. corners): {len(audit)}", "",
             "## Integrity checks", "", "| Check | Result |", "|---|---|"]
    lines += [f"| {c} | {'PASS' if ok else 'FAIL'} |" for c, ok in checks]
    for title, key, rows in [("Outcome labels", "outcome", sequences),
                             ("Terminal reasons", "terminal_reason", sequences),
                             ("Delivery type", "delivery_type", corners),
                             ("Target zone", "target_zone", corners),
                             ("Delivery outcome", "delivery_outcome", corners)]:
        lines += ["", f"## {title}", "", "| Value | Count | Share |", "|---|---:|---:|"]
        for v, n in Counter(r[key] for r in rows).most_common():
            lines.append(f"| {v} | {n} | {n / len(rows):.1%} |")
    shots = sum(s["shot"] for s in sequences)
    lines += ["", "## Binary target", "",
              f"- `shot = 1`: {shots} ({shots / len(sequences):.1%})",
              f"- `shot = 0`: {len(sequences) - shots}",
              f"- Goals (incl. own goals): {sum(s['goal'] for s in sequences)}"]
    (OUT / "validation_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
