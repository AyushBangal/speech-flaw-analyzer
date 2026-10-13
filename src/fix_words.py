import json, re, sys, difflib

def norm(t):
    return re.sub(r"[^a-z0-9']", "", t.lower())

def fix(txt_path, words_in, words_out):
    script = open(txt_path, encoding="utf-8").read().split()
    sn = [norm(t) for t in script]
    asr = json.load(open(words_in))
    an = [norm(w["word"]) for w in asr]
    out = []
    sm = difflib.SequenceMatcher(None, an, sn, autojunk=False)
    for op, i1, i2, j1, j2 in sm.get_opcodes():
        if j1 == j2:
            print("dropped ASR words:", [w["word"] for w in asr[i1:i2]])
            continue
        if i1 == i2:
            print("script words with no timing, skipped:", script[j1:j2])
            continue
        if (i2 - i1) == (j2 - j1):
            for k in range(j2 - j1):
                out.append({"word": sn[j1 + k], "display": script[j1 + k],
                            "start": asr[i1 + k]["start"], "end": asr[i1 + k]["end"]})
        else:
            t0, t1 = asr[i1]["start"], asr[i2 - 1]["end"]
            n = j2 - j1
            step = (t1 - t0) / n
            for k in range(n):
                out.append({"word": sn[j1 + k], "display": script[j1 + k],
                            "start": round(t0 + k * step, 3),
                            "end": round(t0 + (k + 1) * step, 3)})
    json.dump(out, open(words_out, "w"), indent=2)
    print(len(out), "words written, script has", len(script))

if __name__ == "__main__":
    fix(sys.argv[1], sys.argv[2], sys.argv[3])