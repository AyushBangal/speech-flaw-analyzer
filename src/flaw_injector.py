import json, sys
import numpy as np
import librosa, soundfile as sf

SR = 22050

def rush(y, start, end, factor):
    s, e = int(start * SR), int(end * SR)
    seg = librosa.effects.time_stretch(y[s:e], rate=factor)
    out = np.concatenate([y[:s], seg, y[e:]])
    return out, start + len(seg) / SR

if __name__ == "__main__":
    src, dst, lab = sys.argv[1], sys.argv[2], sys.argv[3]
    start, end, factor = float(sys.argv[4]), float(sys.argv[5]), float(sys.argv[6])
    y, _ = librosa.load(src, sr=SR, mono=True)
    out, new_end = rush(y, start, end, factor)
    sf.write(dst, out, SR)
    label = {
        "baseline_audio": src, "flawed_audio": dst,
        "injected_flaws": [{
            "flaw_type": "rushed_pace",
            "baseline_start_sec": start, "baseline_end_sec": end,
            "modified_start_sec": start, "modified_end_sec": round(new_end, 3),
            "params": {"speed_factor": factor}
        }]
    }
    json.dump(label, open(lab, "w"), indent=2)
    print("modified region:", start, "->", round(new_end, 3))