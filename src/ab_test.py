from detect import detect

regions = detect("labels/speech1_features.json", "labels/speech1_B_features.json")
print("regions flagged on two clean readings:", len(regions))
for r in regions:
    print(r)