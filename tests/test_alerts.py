import json
from datetime import datetime, timedelta

import pandas as pd
from fastapi.testclient import TestClient

import detect as D
from app.main import app

client = TestClient(app)
DF = pd.read_csv("data/metrics.csv")
T0 = datetime(2026, 1, 5, 0, 0)


def send(service, rows, start_minute_of_day=0, mutate=None):
    out = []
    for i, (_, r) in enumerate(rows.iterrows()):
        r = r.copy()
        if mutate:
            mutate(r)
        out.append(client.post("/ingest", json={
            "service": service, "timestamp": (T0 + timedelta(minutes=start_minute_of_day + i)).isoformat(),
            "requests": r.requests, "latency_ms": r.latency_ms, "error_rate": r.error_rate, "cpu": r.cpu}).json())
    return out


def normal_rows(n, day=3, minute=720):
    s = day * 1440 + minute
    return DF.iloc[s:s + n].assign(minute_of_day=lambda d: d.minute_of_day)


def test_normal_traffic_no_alert():
    assert not any(x["alert"] for x in send("svc-normal", normal_rows(120), 720))


def test_latency_spike_alerts_once_on_third_minute_with_reason():
    def spike(r): r.latency_ms *= 4
    res = send("svc-spike", normal_rows(10), 720, spike)
    alerts = [i for i, x in enumerate(res) if x["alert"]]
    assert alerts == [2]
    assert res[2]["reason"] == "latency"


def test_dedupe_and_cooldown_realert():
    def spike(r): r.latency_ms *= 4
    res = send("svc-long", normal_rows(40), 720, spike)
    assert [i for i, x in enumerate(res) if x["alert"]] == [2, 33]


def test_flash_sale_is_not_an_incident():
    start = 9 * 1440 + 20 * 60   # benign traffic surge (data te label=0)
    rows = DF.iloc[start:start + 40]
    assert rows.incident.sum() == 0
    assert not any(x["alert"] for x in send("svc-sale", rows, 1200))
    base = D.Baseline().fit(DF[DF.minute < 7 * 1440])
    assert D.score_seasonal(rows, base).max() > 6   # seasonal method eta ke vul kore incident dhore


def test_services_have_independent_state():
    def spike(r): r.latency_ms *= 4
    send("svc-a", normal_rows(2), 720, spike)       # 2 minute flag
    res = send("svc-b", normal_rows(1), 722, spike)  # b er prothom flag, alert hobe na
    assert not res[0]["alert"]


def test_validation():
    bad = {"service": "x", "timestamp": T0.isoformat(), "requests": 1, "latency_ms": 1, "error_rate": 5, "cpu": 10}
    assert client.post("/ingest", json=bad).status_code == 422


def test_method_comparison_expectations():
    m = json.load(open("model/metrics.json"))["methods"]
    la, st, se, iso = m["load_aware_robust"], m["static_threshold"], m["seasonal_robust"], m["isolation_forest"]
    assert la["recall"] >= 0.8 and la["precision"] >= 0.9
    assert st["recall"] < la["recall"]
    assert se["false_alarms_per_day"] > la["false_alarms_per_day"]
    assert iso["recall"] >= la["recall"] and iso["false_alarms_per_day"] > la["false_alarms_per_day"]
