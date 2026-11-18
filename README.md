# Trends-Big-Data-Mng-Project

COMP5118 P6-a: Corner-Kick Analytics
Project Overview
This project uses StatsBomb Open Data to study corner kicks in football (soccer). The Phase 1 objective is to build a reliable dataset of corner-kick sequences that can later support descriptive analysis and prediction.

The initial prediction question is:

Does a corner kick lead to a shot?

Phase 1 focuses on data acquisition, sequence extraction, outcome labeling, and manual validation—not on building the final predictive model yet.

corner_project/
├── data/
├── outputs/
├── available_competitions.csv
├── check_data.py
├── choose_dataset.py
├── download_data.py
├── extract_corners.py
└── README.md

corner_project/
├── data/
├── outputs/
├── available_competitions.csv
├── check_data.py
├── choose_dataset.py
├── download_data.py
├── extract_corners.py
└── README.md

The exact folder names must match the paths used in the Python scripts. Keep competitions separate during downloading and verification so that the source of each match remains identifiable.

The outputs/ folder is intended for generated datasets, audit samples, and analysis results.
Data Source
The project uses StatsBomb Open Data, which provides selected football match data in JSON format.

Two kinds of data are relevant:
- Event data: chronological match events, including passes, shots, fouls, possession information, and other actions.
- 360 data: snapshots of player and pitch positioning for certain events in selected matches. Availability of a 360 file does not guarantee that every event or corner has a usable 360 snapshot.
The Open Data repository contains selected matches, not necessarily every match in an official competition season. Therefore, downloaded match counts should be reported as actual dataset coverage rather than official competition totals.
Scripts and Their Responsibilities
1. choose_dataset.py
Purpose: Help identify available StatsBomb competitions and seasons.

What it does:
1. Retrieves the StatsBomb Open Data competition information.
2. Displays competition and season information.
3. Helps identify the competition ID and season ID needed by the downloader.
Output: Competition/season information for selecting datasets.

Important note: The competition listing alone does not establish how many match event files or usable 360 snapshots are available. Those counts must be checked separately.
2. available_competitions.csv
Purpose: Store competition information obtained during dataset selection.

What it contains: Competition and season metadata, such as IDs, names, countries, and available 360-related metadata when supplied by the source.

Use: Reference this file when selecting competition and season IDs for downloading.
3. download_data.py
Purpose: Download match data for a selected competition and season.

General workflow:
1. Ask for a competition ID and season ID.
2. Retrieve the match list for that competition/season.
3. Download each available match event JSON.
4. Attempt to download the corresponding 360 JSON.
5. Save downloaded files into local data folders.
Expected data products:
- One event JSON file per downloaded match.
- A 360 JSON file for matches where the corresponding file is available.
Important note: The script's actual destination folders determine where check_data.py must look. Confirm these paths before assuming that a download failed.
4. check_data.py
Purpose: Verify that downloaded data files exist locally.

What it is intended to do:
1. Locate the event-data folders.
2. Count event JSON files.
3. Locate the 360-data folders.
4. Count 360 JSON files.
5. Display a summary and warnings if files are missing.
Expected output: A download summary showing the number of event and 360 files for each competition.

Troubleshooting: If it reports zero files, check:
- The current working directory.
- The exact folder names.
- Whether the JSON files are nested one level deeper.
- Whether the script paths match the downloader's save paths.
A zero count does not necessarily mean that the files were not downloaded.
5. extract_corners.py
Purpose: Create an initial dataset of corner-kick sequences from event JSON files.

Initial extraction logic:
1. Read match event JSON files.
2. Identify corner kicks using pass events whose pass type is Corner.
3. Record the corner's match, period, timestamp, team, and location.
4. Examine subsequent events to reconstruct the attacking sequence.
5. Stop the sequence according to the initial terminal-event and safety-cutoff rules.
6. Assign an outcome and terminal reason.
7. Write a corner-level dataset and an event-level audit file.
Initial sequence-ending rules:
- Shot: Stop at the first shot event, including a goal, saved shot, blocked shot, or off-target shot.
- Foul: Stop when a foul terminates the attacking sequence.
- Offside: Stop when an offside event terminates the sequence.
- Restart: Stop at a relevant restart, such as a goal kick, throw-in, free kick, or another corner.
- Possession loss: Stop when the defending team gains possession, subject to verification of the event fields used.
- Safety cutoff: Stop after 15 seconds of game time or 10 subsequent events, whichever comes first.
- No clear terminal outcome: Use this when the safety cutoff is reached without a clear terminal event.
Expected output files:
- outputs/corner_sequences.csv — one row per extracted corner sequence.
- outputs/sequence_events_audit.csv — event-level records used to inspect reconstructed sequences.
Important limitation: This is an initial implementation and must be tested against raw event JSON before it is treated as a validated extraction method. In particular, possession-loss detection, restart detection, event ordering, and cutoff handling require manual checks.
6. audit_corners.py (planned/next script)
Purpose: Support manual validation of extracted corner sequences.

Expected workflow:
1. Randomly select up to 100 extracted sequences.
2. Create a review file containing the selected sequences.
3. Add fields for the manually verified outcome, correctness, and notes.
4. Compare each sequence against the original match event JSON.
5. Record disagreements and correct the extraction logic.
Expected output:
- outputs/audit_sample_100.csv
The audit should verify both the events included in the sequence and the assigned terminal outcome.
Phase 1 Deliverables
The intended Phase 1 deliverables are:
1. A documented and reproducible dataset selection.
2. Downloaded and verified match event files.
3. A corner-level dataset with one row per corner.
4. An event-level sequence audit file.
5. Explicit terminal-outcome labels.
6. A manually audited sample of at least 100 sequences, where the dataset contains enough sequences.
7. A cleaned and finalized dataset suitable for descriptive analysis and modelling.
8. A documented baseline for the prediction question.
Prediction target
The initial binary target is:

Will this corner sequence produce a shot?

Proposed mapping:
Sequence outcome	Binary target
Goal	1
Shot without goal	1
No shot / possession loss	0
Ball out without shot	0
Foul or offside without shot	0
No clear terminal outcome before cutoff	Review; define treatment explicitly


The last category should not automatically be treated as a definite no-shot outcome without documenting the decision. It may be excluded from the initial binary analysis or handled according to a clearly stated rule.
Baseline and Evaluation Plan
Baseline calculations should be performed after sequence extraction, outcome labeling, and validation.

Recommended process:
1. Finalize the extracted corner dataset.
2. Split matches into training, validation, and test groups so that corners from the same match do not leak across splits.
3. Calculate baseline values using training data only.
4. Compare a simple baseline against a logistic regression model.
5. Evaluate final performance on held-out test matches.
Possible baselines:
- Majority-class baseline: always predict the most frequent outcome.
- Training-set shot-rate baseline: predict the training-set probability of a corner producing a shot.
Possible evaluation metrics include log loss, Brier score, and suitable classification metrics. The choice should be documented before reporting final results.
Current Progress
Based on the current project files and work completed:
- [x] Created project folders (data/ and outputs/).
- [x] Created competition-selection script.
- [x] Saved competition information to CSV.
- [x] Created data-download script.
- [x] Downloaded an initial competition dataset (La Liga 2020/21 was previously downloaded; reported coverage was 35 match event files and 35 360 files).
- [x] Created a data-checking script.
- [x] Created an initial corner-extraction script.
- [ ] Confirm folder paths and verify all selected competition files.
- [ ] Run and inspect the extraction output.
- [ ] Validate extracted sequences against raw events.
- [ ] Complete the manual audit.
- [ ] Correct and finalize the extraction logic.
- [ ] Finalize the clean corner dataset.
- [ ] Establish the baseline and document the evaluation split.


Immediate Next Steps
1. Inspect the contents of data/ and confirm the exact event/360 folder paths.
2. Update check_data.py to match those paths and run it.
3. Open extract_corners.py and confirm its input paths match the data folders.
4. Run the extraction script.
5. Inspect the first few rows of outputs/corner_sequences.csv.
6. Compare several extracted sequences with their original match event JSON.
7. Refine the extraction logic before running the 100-sequence audit.