import json, sys, difflib

def load(p):
    return json.load(open(p))

def norm(w):
    return "".join(c for c in w.lower() if c.isalnum())

def detect(base_path, part_path, dur_thr=0.25, gap_thr=0.8, db_thr=6.0, merge_gap=1.5):
    base, part = load(base_path), load(part_path)
    sm = difflib.SequenceMatcher(
        None, [norm(w["word"]) for w in base], [norm(w["word"]) for w in part])
    flagged = []
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            b, p = base[blk.a + k], part[blk.b + k]
            ratio = p["dur"] / max(b["dur"], 1e-3)
            if ratio < 1 - dur_thr:
                flagged.append({"type": "rushed_pace", "start": p["start"], "end": p["end"],
                                "why": f"word duration {ratio:.2f}x baseline"})
            if p["gap_before"] - b["gap_before"] > gap_thr:
                flagged.append({"type": "long_pause", "start": p["start"] - p["gap_before"], "end": p["start"],
                                "why": f"pause of {p['gap_before']:.2f}s vs {b['gap_before']:.2f}s in baseline"})
            drop = b["energy_rel_db"] - p["energy_rel_db"]
            if db_thr < drop < 40:
                flagged.append({"type": "volume_drop", "start": p["start"], "end": p["end"],
                                "why": f"{drop:.1f} dB quieter than baseline"})
    regions = []
    for f in sorted(flagged, key=lambda x: x["start"]):
        same = [r for r in regions if r["type"] == f["type"]]
        last = same[-1] if same else None
        if last and f["start"] - last["end"] < merge_gap:
            last["end"] = max(last["end"], f["end"])
            last["why"].append(f["why"])
        else:
            regions.append({"type": f["type"], "start": f["start"], "end": f["end"], "why": [f["why"]]})
    return regions

if __name__ == "__main__":
    for r in detect(sys.argv[1], sys.argv[2]):
        print(f'{r["type"]}: {r["start"]:.2f}-{r["end"]:.2f} s | {r["why"][0]}')