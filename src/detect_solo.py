import json, sys
from statistics import median

def detect_solo(feats_path, W=8, merge_gap=1.0):
    rows = json.load(open(feats_path))
    if len(rows) < W + 2:
        return []
    flagged = []
    for r in rows:
        gs = r["start"] - r["gap_before"]
        if r["gap_before"] > 1.2 and gs > 0.05:
            flagged.append({"type": "long_pause", "start": gs, "end": r["start"],
                            "why": f"pause of {r['gap_before']:.2f}s"})
    wins = [rows[i:i + W] for i in range(len(rows) - W + 1)]
    rates = [W / max(w[-1]["end"] - w[0]["start"], 1e-3) for w in wins]
    med_rate = median(rates)
    rng = [[x["f0_st_range"] for x in w if x["f0_st_range"] is not None and x["f0_st_range"] < 12] for w in wins]
    rng_mean = [sum(v) / len(v) if v else None for v in rng]
    valid = [v for v in rng_mean if v is not None]
    med_rng = median(valid) if valid else None
    for w, rate, rm in zip(wins, rates, rng_mean):
        s, e = w[0]["start"], w[-1]["end"]
        has_gap = any(x["gap_before"] > 1.2 for x in w[1:])
        if rate > 1.8 * med_rate:
            flagged.append({"type": "rushed_pace", "start": s, "end": e,
                            "why": f"{rate / med_rate:.2f}x this speaker's usual pace"})
        elif rate < 0.6 * med_rate and not has_gap:
            flagged.append({"type": "dragging_pace", "start": s, "end": e,
                            "why": f"{rate / med_rate:.2f}x this speaker's usual pace"})
        avg_z = sum(x["energy_z"] for x in w) / W
        if avg_z < -0.8:
            flagged.append({"type": "volume_drop", "start": s, "end": e,
                            "why": f"{W}-word loudness {avg_z:.2f} SD below this speaker's average"})
        if med_rng and rm is not None and rm < 0.2 * med_rng:
            flagged.append({"type": "monotone", "start": s, "end": e,
                            "why": f"pitch movement {rm:.1f} semitones vs usual {med_rng:.1f}"})
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
    for r in detect_solo(sys.argv[1]):
        print(f'{r["type"]}: {r["start"]:.2f}-{r["end"]:.2f} s | {r["why"][0]}')