# speech-flaw-analyzer

**Demo video:** [https://youtu.be/HCXbMniLnYU]

## What this does

Speech Flaw Analyzer compares a speech reading against a reference reading, finds the exact seconds where delivery goes wrong (rushed pace, long pause, volume drop), and explains each flag with measured numbers. It is a rule-based pipeline, so every flag can be traced to a feature difference.

## Setup

Requires Python and ffmpeg (ffmpeg must be on your PATH).

```
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

## How to run the dashboard

```
streamlit run app\app.py
```

## Pipeline scripts (in `src/`)

```
python src\align.py <audio.wav> <words.json>
python src\features.py <audio.wav> <words.json> <features.json>
python src\flaw_injector.py <in.wav> <out.wav> <label.json> <start> <end> <factor>
python src\evaluate.py
```

- `align.py`: word timestamps using faster-whisper
- `features.py`: pitch (semitones relative to the speaker's own median), loudness and word duration
- `flaw_injector.py`: creates flawed audio and writes its label file
- `detect.py`: compares a recording with the baseline word by word and flags regions
- `evaluate.py`: measures overlap (IoU) with the injected regions and counts false alarms

## Dataset

- **Baseline text:** the first two paragraphs of the Gettysburg Address (1863, public domain).
- **Audio:** self-recorded by the authors on a phone in a quiet room (speaker A and speaker B).
- **Labels:** every injected flaw has a label file with its start and end time on both the original timeline and the modified timeline, written automatically by `flaw_injector.py`.
- **Note:** the injected-flaw files (rushed, pause, volume) were made from the 15 s test clip, not from the Gettysburg readings.

| File | What it is | Transcript | Labels |
|---|---|---|---|
| data/baseline/speech1.wav | Speaker A, clean reading | data/baseline/speech1.txt | labels/speech1_words.json |
| data/baseline/speech1_B.wav | Speaker B, clean reading | data/baseline/speech1.txt | labels/speech1_B_words.json |
| data/real/test.wav | 15 s test clip | none (ASR only) | labels/test_words.json |
| data/flawed/test_rushed.wav | Rushed pace injected, 3.0-6.33 s | none (ASR only) | labels/test_rushed.json |
| data/flawed/test_pause.wav | 2.5 s pause injected | none (ASR only) | labels/test_pause.json |
| data/flawed/test_volume.wav | Volume drop injected, 3.0-8.0 s | none (ASR only) | labels/test_volume.json |

## Results

Detector sanity check on injected flaws (from `labels/eval_results.json`):

| Flaw | IoU with injected region | Detected |
|---|---|---|
| Rushed pace | [0.924,] | [True] |
| Long pause | [ 0.88,] | [True] |
| Volume drop | [0.943] | [True] |

- False alarms on injected-flaw files: [1]
- Two runs give identical output (deterministic): [True]
- Clean speaker B vs clean speaker A (false-alarm test): [9] regions flagged

## Limitations

- The injected-flaw test is the easiest case: baseline and flawed files come from the same recording.
- Word timing comes from speech recognition, so it is approximate (about 0.2 s in our spot-check).
- Free speech mode is experimental and not validated. The reference-comparison mode is the main result.