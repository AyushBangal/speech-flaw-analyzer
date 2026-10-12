import json, sys
import numpy as np, librosa, parselmouth

def extract(wav, words_json, out):
    words = json.load(open(words_json))
    y, sr = librosa.load(wav, sr=22050, mono=True)
    hop = 256
    rms = librosa.feature.rms(y=y, hop_length=hop)[0]
    rms_db = 20 * np.log10(rms + 1e-6)
    rt = librosa.frames_to_time(np.arange(len(rms)), sr=sr, hop_length=hop)
    pitch = parselmouth.Sound(wav).to_pitch(time_step=0.01)
    f0, ft = pitch.selected_array["frequency"], pitch.xs()
    voiced = f0 > 0
    med = np.median(f0[voiced])
    st = np.where(voiced, 12 * np.log2(np.where(voiced, f0, 1) / med), np.nan)
    mu, sd = rms_db.mean(), rms_db.std() + 1e-6
    rows, prev_end = [], 0.0
    for w in words:
        m = (rt >= w["start"]) & (rt < w["end"])
        p = (ft >= w["start"]) & (ft < w["end"])
        pv = st[p][~np.isnan(st[p])]
        rows.append({**w,
            "dur": round(w["end"] - w["start"], 3),
            "gap_before": round(max(0, w["start"] - prev_end), 3),
            "energy_z": float((rms_db[m].mean() - mu) / sd) if m.any() else 0.0,
            "f0_st_med": float(np.median(pv)) if len(pv) else None,
            "f0_st_range": float(pv.max() - pv.min()) if len(pv) else None})
        prev_end = w["end"]
    json.dump(rows, open(out, "w"), indent=2)

if __name__ == "__main__":
    extract(sys.argv[1], sys.argv[2], sys.argv[3])