"""5 method compare: incident-level recall, alert precision, false alarm/day, detection delay"""
import json

import joblib
import numpy as np
import pandas as pd

import detect as D

df = pd.read_csv("data/metrics.csv")
events = [e for e in json.load(open("data/events.json"))]
train, TEST0 = df[df.minute < 7 * 1440], 7 * 1440

base = D.Baseline().fit(train)
iso = D.IForest().fit(train, base)
iso_thr = float(np.quantile(iso.score(train, base), 0.99))   # threshold TRAINING data theke (label dekhe na)

methods = {  # method: (score, threshold)
    "static_threshold": (D.score_static(df), 1.0),
    "rolling_zscore": (D.score_rolling_z(df), 5.0),
    "seasonal_robust": (D.score_seasonal(df, base), 6.0),
    "load_aware_robust": (D.score_load_aware(df, base), 6.0),
    "isolation_forest": (iso.score(df, base), iso_thr),
}
incidents = [e for e in events if e["incident"] and e["start"] >= TEST0]
report = {}
print(f"{'method':18s} {'recall':>7s} {'precision':>9s} {'false/day':>9s} {'median delay(min)':>18s}")
for name, (score, thr) in methods.items():
    alert = np.where(D.sustained(score > thr))[0]
    alert = alert[alert >= TEST0]
    eps = D.episodes(alert)
    hit, delays = 0, []
    for e in incidents:
        w = alert[(alert >= e["start"]) & (alert <= e["end"] + 10)]
        if len(w):
            hit += 1
            delays.append(int(w[0] - e["start"]))
    good = sum(any(s <= i["end"] + 10 and en >= i["start"] for i in incidents) for s, en in eps)  # alert ta kono asol incident er shathe mile
    recall = hit / len(incidents)
    precision = good / len(eps) if eps else 0.0
    report[name] = {"recall": recall, "precision": precision, "alert_episodes": len(eps),
                    "false_alarms_per_day": (len(eps) - good) / 7,
                    "median_delay_min": float(np.median(delays)) if delays else None,
                    "f1": 2 * recall * precision / (recall + precision) if recall + precision else 0.0}
    r = report[name]
    print(f"{name:18s} {recall:7.0%} {precision:9.0%} {r['false_alarms_per_day']:9.2f} {str(r['median_delay_min']):>18s}")

joblib.dump({"baseline": base, "threshold": 6.0, "k": 3}, "model/detector.joblib")
json.dump({"test_incidents": len(incidents), "methods": report}, open("model/metrics.json", "w"), indent=2)
print("\nsaved model/detector.joblib (serving: load_aware_robust)")
