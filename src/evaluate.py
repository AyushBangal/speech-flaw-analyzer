import json
from detect import detect

BASE = "labels/test_features.json"
CASES = ["rushed", "pause", "volume"]

def iou(a_start, a_end, b_start, b_end):
    inter = max(0.0, min(a_end, b_end) - max(a_start, b_start))
    union = (a_end - a_start) + (b_end - b_start) - inter
    return inter / union if union > 0 else 0.0

def evaluate():
    rows, false_alarms = [], []
    for c in CASES:
        label = json.load(open(f"labels/test_{c}.json"))
        det = detect(BASE, f"labels/test_{c}_features.json")
        injected = label["injected_flaws"]
        for fl in injected:
            same = [r for r in det if r["type"] == fl["flaw_type"]]
            best = max((iou(fl["modified_start_sec"], fl["modified_end_sec"],
                            r["start"], r["end"]) for r in same), default=0.0)
            rows.append({"case": c, "flaw_type": fl["flaw_type"],
                         "injected": [fl["modified_start_sec"], fl["modified_end_sec"]],
                         "iou": round(best, 3), "detected": best > 0.3})
        for r in det:
            hit = any(r["type"] == fl["flaw_type"] and
                      iou(fl["modified_start_sec"], fl["modified_end_sec"], r["start"], r["end"]) > 0
                      for fl in injected)
            if not hit:
                false_alarms.append({"case": c, "type": r["type"],
                                     "start": round(r["start"], 2), "end": round(r["end"], 2)})
    return {"rows": rows, "false_alarms": false_alarms}

if __name__ == "__main__":
    first = evaluate()
    second = evaluate()
    same = json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    for r in first["rows"]:
        print(f'{r["case"]:8} {r["flaw_type"]:12} injected {r["injected"]}  IoU={r["iou"]}  detected={r["detected"]}')
    print("false alarms:", len(first["false_alarms"]), first["false_alarms"])
    print("deterministic (2 runs identical):", same)
    json.dump(first, open("labels/eval_results.json", "w"), indent=2)