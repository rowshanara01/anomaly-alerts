"""Streaming alert API: prottek minute er metric pathao, 'alert' ashle bolbe (3 minute sustained + 30 min cooldown dedupe) ar KENO"""
import json
import threading
from collections import deque
from datetime import datetime

import joblib
import pandas as pd
from fastapi import FastAPI
from pydantic import BaseModel, Field

import detect as D

B = joblib.load("model/detector.joblib")
BASE, THRESHOLD, K = B["baseline"], B["threshold"], B["k"]
COOLDOWN_MIN = 30
states, lock = {}, threading.Lock()
app = FastAPI(title="Anomaly Alert API")


class Point(BaseModel):
    service: str = Field(min_length=1, max_length=50)
    timestamp: datetime
    requests: float = Field(ge=0)
    latency_ms: float = Field(ge=0)
    error_rate: float = Field(ge=0, le=1)
    cpu: float = Field(ge=0, le=100)


@app.get("/health")
def health():
    return {"status": "ok", "services_tracked": len(states)}


@app.get("/model-info")
def model_info():
    return json.load(open("model/metrics.json"))


@app.post("/admin/reset")
def reset():
    with lock:
        states.clear()
    return {"status": "reset"}


@app.post("/ingest")
def ingest(p: Point):
    ts = p.timestamp.replace(tzinfo=None)
    row = pd.DataFrame([{"minute_of_day": ts.hour * 60 + ts.minute, "requests": p.requests,
                         "latency_ms": p.latency_ms, "error_rate": p.error_rate, "cpu": p.cpu}])
    parts = D.load_aware_parts(BASE.z(row)).iloc[0]
    score, reason = float(parts.max()), str(parts.idxmax())
    flagged = score > THRESHOLD
    with lock:
        st = states.setdefault(p.service, {"flags": deque(maxlen=K), "last_alert": None})
        st["flags"].append(flagged)
        sustained = len(st["flags"]) == K and all(st["flags"])
        cooled = st["last_alert"] is None or (ts - st["last_alert"]).total_seconds() / 60 > COOLDOWN_MIN
        alert = bool(sustained and cooled)
        if alert:
            st["last_alert"] = ts
    return {"service": p.service, "score": round(score, 2), "flagged": bool(flagged), "alert": alert,
            "reason": reason if flagged else None, "details": {k: round(float(v), 2) for k, v in parts.items()}}
