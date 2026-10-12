import json, sys
import numpy as np
import librosa, soundfile as sf

SR = 22050

def rush(y, start, end, factor):
    s, e = int(start * SR), int(end * SR)
    seg = librosa.effects.time_stretch(y[s:e], rate=factor)
    out = np.concatenate([y[:s], seg, y[e:]])
    return out, start, end, start, start + len(seg) / SR, {"speed_factor": factor}

def pause(y, at, dur):
    s = int(at * SR)
    out = np.concatenate([y[:s], np.zeros(int(dur * SR)), y[s:]])
    return out, at, at, at, at + dur, {"pause_sec": dur}

def volume(y, start, end, gain):
    s, e = int(start * SR), int(end * SR)
    out = y.copy()
    out[s:e] = out[s:e] * gain
    return out, start, end, start, end, {"gain": gain}

if __name__ == "__main__":
    mode, src, dst, lab = sys.argv[1:5]
    a = [float(x) for x in sys.argv[5:]]
    y, _ = librosa.load(src, sr=SR, mono=True)
    if mode == "rushed":
        out, bs, be, ms, me, params = rush(y, *a); ftype = "rushed_pace"
    elif mode == "pause":
        out, bs, be, ms, me, params = pause(y, *a); ftype = "long_pause"
    elif mode == "volume":
        out, bs, be, ms, me, params = volume(y, *a); ftype = "volume_drop"
    else:
        sys.exit("mode must be rushed, pause or volume")
    sf.write(dst, out, SR)
    label = {"baseline_audio": src, "flawed_audio": dst,
             "injected_flaws": [{"flaw_type": ftype,
                 "baseline_start_sec": round(bs, 3), "baseline_end_sec": round(be, 3),
                 "modified_start_sec": round(ms, 3), "modified_end_sec": round(me, 3),
                 "params": params}]}
    json.dump(label, open(lab, "w"), indent=2)
    print(ftype, "modified region:", round(ms, 3), "->", round(me, 3))