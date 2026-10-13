import json, sys, difflib
from statistics import median

def load(p):
    return json.load(open(p))

def norm(w):
    return "".join(c for c in w.lower() if c.isalnum())

def detect(base_path, part_path, dur_thr=0.25, gap_thr=0.8, db_thr=9.0,
           merge_gap=1.5, min_rushed_words=3, vol_window=6):
    base, part = load(base_path), load(part_path)
    sm = difflib.SequenceMatcher(
        None, [norm(w["word"]) for w in base], [norm(w["word"]) for w in part])
    pairs = []
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            pairs.append((base[blk.a + k], part[blk.b + k]))
    if not pairs:
        return []

    # Speaker-agnostic step: measure this recording's own overall tempo and level
    ratios = [p["dur"] / max(b["dur"], 1e-3) for b, p in pairs
              if b["dur"] >= 0.05 and p["dur"] >= 0.05]
    tempo = median(ratios) if ratios else 1.0
    level = median([b["energy_rel_db"] - p["energy_rel_db"] for b, p in pairs])

    flagged = []
    drops = []
    for b, p in pairs:
        ratio = (p["dur"] / max(b["dur"], 1e-3)) / tempo
        if ratio < 1 - dur_thr:
            flagged.append({"type": "rushed_pace", "start": p["start"], "end": p["end"],
                            "why": f"word duration {ratio:.2f}x of this speaker's usual pace"})
        gap_start = p["start"] - p["gap_before"]
        if gap_start > 0.05 and p["gap_before"] - b["gap_before"] > gap_thr:
            flagged.append({"type": "long_pause", "start": gap_start, "end": p["start"],
                            "why": f"pause of {p['gap_before']:.2f}s vs {b['gap_before']:.2f}s in baseline"})
        drops.append(((b["energy_rel_db"] - p["energy_rel_db"]) - level, p))

    # Volume is judged over a window of words, because single-word loudness is noisy
    W = vol_window
    for i in range(0, max(len(drops) - W + 1, 0)):
        win = drops[i:i + W]
        avg = sum(d for d, _ in win) / W
        if db_thr < avg < 40:
            flagged.append({"type": "volume_drop",
                            "start": win[0][1]["start"], "end": win[-1][1]["end"],
                            "why": f"{avg:.1f} dB quieter than this speaker's usual level ({W}-word average)"})

    regions = []
    for f in sorted(flagged, key=lambda x: x["start"]):
        same = [r for r in regions if r["type"] == f["type"]]
        last = same[-1] if same else None
        if last and f["start"] - last["end"] < merge_gap:
            last["end"] = max(last["end"], f["end"])
            last["why"].append(f["why"])
        else:
            regions.append({"type": f["type"], "start": f["start"], "end": f["end"], "why": [f["why"]]})
    # A single fast word is noise (word timings are noisy), so require a run
    regions = [r for r in regions
               if r["type"] != "rushed_pace" or len(r["why"]) >= min_rushed_words]
    return regions

if __name__ == "__main__":
    for r in detect(sys.argv[1], sys.argv[2]):
        print(f'{r["type"]}: {r["start"]:.2f}-{r["end"]:.2f} s | {r["why"][0]}')