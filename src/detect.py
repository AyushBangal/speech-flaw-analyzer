import json, sys, difflib

def load(p):
    return json.load(open(p))

def norm(w):
    return "".join(c for c in w.lower() if c.isalnum())

def detect(base_path, part_path, dur_thr=0.25, gap_thr=0.8, en_thr=1.0):
    base, part = load(base_path), load(part_path)
    sm = difflib.SequenceMatcher(
        None, [norm(w["word"]) for w in base], [norm(w["word"]) for w in part])
    flagged = []
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            b, p = base[blk.a + k], part[blk.b + k]
            reasons = []
            ratio = p["dur"] / max(b["dur"], 1e-3)
            if ratio < 1 - dur_thr:
                reasons.append(("rushed_pace", f"word duration {ratio:.2f}x baseline"))
            if p["gap_before"] - b["gap_before"] > gap_thr:
                reasons.append(("long_pause", f"pause before word {p['gap_before']:.2f}s vs {b['gap_before']:.2f}s baseline"))
            if b["energy_z"] - p["energy_z"] > en_thr:
                reasons.append(("volume_drop", f"energy z-score {p['energy_z']:.2f} vs {b['energy_z']:.2f} baseline"))
            for t, why in reasons:
                flagged.append({"type": t, "start": p["start"], "end": p["end"], "why": why})
    regions = []
    for f in sorted(flagged, key=lambda x: x["start"]):
        last = regions[-1] if regions else None
        if last and last["type"] == f["type"] and f["start"] - last["end"] < 1.0:
            last["end"] = f["end"]
            last["why"].append(f["why"])
        else:
            regions.append({"type": f["type"], "start": f["start"], "end": f["end"], "why": [f["why"]]})
    return regions

if __name__ == "__main__":
    for r in detect(sys.argv[1], sys.argv[2]):
        print(f'{r["type"]}: {r["start"]:.2f}-{r["end"]:.2f} s | {r["why"][0]}')