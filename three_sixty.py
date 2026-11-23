"""360 availability check and visible-area filter for corner freeze frames.

For every corner, look up its StatsBomb 360 freeze frame (matched on event UUID) and compute:
  has_360                 a freeze frame exists for this corner event
  box_coverage            share of the attacking penalty area (x >= 102, 18 <= y <= 62)
                          inside the frame's visible_area polygon
  six_yard_coverage       same for the six-yard box (x >= 114, 30 <= y <= 50)
  visible_attackers_box   visible attacking players (teammate = true) inside the penalty area
  visible_defenders_box   visible defending players inside the penalty area (incl. goalkeeper)
  keeper_visible          defending goalkeeper appears in the frame
  passes_filter           has_360 and box_coverage >= COVERAGE_THRESHOLD

Player counts only describe VISIBLE players. A low count in a poorly covered frame
does not mean players were absent, which is why the filter is applied before clustering.

Outputs:
  outputs/corner_360_features.csv
  outputs/three_sixty_report.md
Requires: shapely  (pip install shapely)
Run:  python three_sixty.py
"""

import csv
import json
from collections import Counter
from pathlib import Path

from shapely.geometry import Point, Polygon, box

BASE_DIR = Path(__file__).resolve().parent
OUT = BASE_DIR / "outputs"
FOLDERS = {"World Cup 2022": BASE_DIR / "data" / "world_cup_2022" / "three-sixty",
           "Euro 2020": BASE_DIR / "data" / "euro_2020" / "three-sixty"}
COVERAGE_THRESHOLD = 0.80
SENSITIVITY = [0.50, 0.60, 0.70, 0.80, 0.90]
PENALTY_AREA = box(102, 18, 120, 62)
SIX_YARD = box(114, 30, 120, 50)


def polygon(flat):
    pts = list(zip(flat[0::2], flat[1::2]))
    poly = Polygon(pts)
    return poly if poly.is_valid else poly.buffer(0)


def main():
    corners = list(csv.DictReader(open(OUT / "corners.csv", encoding="utf-8")))
    frames, files = {}, Counter()
    for comp, folder in FOLDERS.items():
        for path in folder.glob("*.json"):
            files[comp] += 1
            for fr in json.load(open(path, encoding="utf-8")):
                frames[fr["event_uuid"]] = fr

    rows = []
    for c in corners:
        fr = frames.get(c["event_id"])
        r = {"corner_id": c["corner_id"], "competition": c["competition"], "match_id": c["match_id"],
             "has_360": int(fr is not None), "box_coverage": "", "six_yard_coverage": "",
             "visible_players": "", "visible_attackers_box": "", "visible_defenders_box": "",
             "keeper_visible": "", "passes_filter": 0}
        if fr:
            va = polygon(fr["visible_area"])
            att = dfd = 0
            keeper = 0
            for p in fr["freeze_frame"]:
                x, y = p["location"]
                inside = PENALTY_AREA.covers(Point(x, y))
                if p["teammate"]:
                    att += inside
                else:
                    dfd += inside
                    keeper |= int(p.get("keeper", False))
            cov = va.intersection(PENALTY_AREA).area / PENALTY_AREA.area
            r.update(box_coverage=round(cov, 4),
                     six_yard_coverage=round(va.intersection(SIX_YARD).area / SIX_YARD.area, 4),
                     visible_players=len(fr["freeze_frame"]), visible_attackers_box=att,
                     visible_defenders_box=dfd, keeper_visible=keeper,
                     passes_filter=int(cov >= COVERAGE_THRESHOLD))
        rows.append(r)

    with open(OUT / "corner_360_features.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=rows[0].keys())
        w.writeheader()
        w.writerows(rows)

    with_360 = [r for r in rows if r["has_360"]]
    lines = ["# 360 availability and visible-area filter", "",
             f"360 files: {dict(files)}. Corners: {len(rows)}. "
             f"Corners with a freeze frame: {len(with_360)} ({len(with_360) / len(rows):.1%}).", "",
             "## Availability by competition", "", "| Competition | Corners | With 360 | Pass filter |",
             "|---|---:|---:|---:|"]
    for comp in FOLDERS:
        cr = [r for r in rows if r["competition"] == comp]
        lines.append(f"| {comp} | {len(cr)} | {sum(r['has_360'] for r in cr)} | "
                     f"{sum(r['passes_filter'] for r in cr)} |")
    lines += ["", "## Filter definition", "",
              f"A corner enters 360-based clustering only if it has a freeze frame and the frame's "
              f"`visible_area` polygon covers at least **{COVERAGE_THRESHOLD:.0%}** of the attacking penalty "
              "area (x >= 102, 18 <= y <= 62 on the 120 x 80 StatsBomb pitch). Player counts use visible "
              "players only; unseen players are treated as unknown, not absent.", "",
              "## Threshold sensitivity", "", "| Threshold | Corners kept | Share of 360 corners |",
              "|---:|---:|---:|"]
    for t in SENSITIVITY:
        k = sum(1 for r in with_360 if r["box_coverage"] >= t)
        lines.append(f"| {t:.0%} | {k} | {k / len(with_360):.1%} |")
    kept = [r for r in with_360 if r["passes_filter"]]
    if kept:
        avg = lambda key: sum(r[key] for r in kept) / len(kept)
        lines += ["", "## Kept frames (summary)", "",
                  f"- Mean penalty-area coverage: {avg('box_coverage'):.1%}",
                  f"- Mean visible attackers in box: {avg('visible_attackers_box'):.1f}",
                  f"- Mean visible defenders in box: {avg('visible_defenders_box'):.1f}",
                  f"- Goalkeeper visible: {sum(r['keeper_visible'] for r in kept) / len(kept):.1%}"]
    (OUT / "three_sixty_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
