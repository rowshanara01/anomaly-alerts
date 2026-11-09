"""14 din x 1-minute server metrics (requests, latency, error rate, cpu) + injected incident + benign traffic surge.
Prothom 7 din = training (kono label chhara), porer 7 din = test."""
import json

import numpy as np
import pandas as pd

rng = np.random.default_rng(3)
N, DAY = 14 * 1440, 1440
t = np.arange(N)
m = t % DAY
weekday = (t // DAY) % 7

# ---- Traffic (daily pattern + shukro/shonibar kom + noise) ----
requests = (500 + 300 * np.sin(2 * np.pi * (m / DAY - 0.35))) * np.where(np.isin(weekday, (4, 5)), 0.8, 1.0)
requests *= rng.lognormal(0, 0.05, N)


def at(day, hhmm):
    return day * DAY + int(hhmm[:2]) * 60 + int(hhmm[3:])


events = [  # (kind, start, minutes, label, strength)
    ("flash_sale", at(9, "20:00"), 40, 0, 2.0), ("flash_sale", at(12, "18:00"), 30, 0, 1.8),   # BENIGN: traffic bare, kintu eta incident na
    ("latency_spike", at(2, "11:00"), 20, 1, 4.0), ("error_burst", at(5, "15:00"), 15, 1, 0.15),   # training e lukano incident
    ("latency_spike", at(7, "12:00"), 20, 1, 4.0), ("error_burst", at(8, "03:00"), 15, 1, 0.15),
    ("traffic_drop", at(8, "19:00"), 25, 1, 0.15), ("cpu_leak", at(9, "14:00"), 150, 1, 45.0),
    ("latency_spike", at(10, "08:00"), 12, 1, 2.2), ("error_burst", at(11, "20:30"), 10, 1, 0.08),
    ("traffic_drop", at(12, "02:00"), 30, 1, 0.15), ("latency_spike", at(13, "10:00"), 25, 1, 4.0),
]
for kind, s, d, _, k in events:           # traffic-related event age (latency/cpu shei onujayi bodlabe)
    if kind in ("flash_sale", "traffic_drop"):
        requests[s:s + d] *= k

# ---- Baki metric traffic er upor nirbhor (latency/cpu load er sathe bare) ----
latency = 120 + 0.12 * requests + rng.normal(0, 6, N)
cpu = 20 + 0.05 * requests + rng.normal(0, 2.5, N)
error = np.clip(0.005 + rng.normal(0, 0.0015, N), 0, None)
label = np.zeros(N, int)
for kind, s, d, lab, k in events:
    sl = slice(s, s + d)
    if kind == "latency_spike":
        latency[sl] *= k
    elif kind == "error_burst":
        error[sl] += k
    elif kind == "cpu_leak":
        cpu[sl] += np.linspace(0, k, d)          # dhire dhire bare (memory leak er moto)
        cpu[s + d:s + d + 30] += np.linspace(k, 0, 30)
    label[sl] |= lab

df = pd.DataFrame({"minute": t, "minute_of_day": m, "requests": requests.round(1), "latency_ms": latency.round(1),
                   "error_rate": error.round(4), "cpu": cpu.round(1), "incident": label})
df.to_csv("data/metrics.csv", index=False)
json.dump([{"kind": k, "start": int(s), "end": int(s + d), "incident": bool(l)} for k, s, d, l, _ in events],
          open("data/events.json", "w"), indent=1)
print(f"rows={N} | incident minutes={label.sum()} | events={len(events)} (benign flash_sale: 2)")
