# 360 availability and visible-area filter

360 files: {'World Cup 2022': 64, 'Euro 2020': 51}. Corners: 1030. Corners with a freeze frame: 558 (54.2%).

## Availability by competition

| Competition | Corners | With 360 | Pass filter |
|---|---:|---:|---:|
| World Cup 2022 | 569 | 300 | 294 |
| Euro 2020 | 461 | 258 | 240 |

## Filter definition

A corner enters 360-based clustering only if it has a freeze frame and the frame's `visible_area` polygon covers at least **80%** of the attacking penalty area (x >= 102, 18 <= y <= 62 on the 120 x 80 StatsBomb pitch). Player counts use visible players only; unseen players are treated as unknown, not absent.

## Threshold sensitivity

| Threshold | Corners kept | Share of 360 corners |
|---:|---:|---:|
| 50% | 557 | 99.8% |
| 60% | 554 | 99.3% |
| 70% | 546 | 97.8% |
| 80% | 534 | 95.7% |
| 90% | 388 | 69.5% |

## Kept frames (summary)

- Mean penalty-area coverage: 92.4%
- Mean visible attackers in box: 5.4
- Mean visible defenders in box: 9.7
- Goalkeeper visible: 98.7%
