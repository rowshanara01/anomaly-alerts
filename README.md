# Anomaly Detection + Smart Alerts (AIOps)

## Shomossha
Server e hothat latency barlo, error barlo, traffic kome gelo. Manush 24 ghonta dekhte pare na.
Kintu shudhu fixed threshold ("latency > 350") dile:
- dhire dhire bare (memory leak) -> dhora porhe na
- traffic kome jaoa (outage) -> dhora porhe na
- sale te traffic duno -> vul alarm (false alert), tarpor team alert dekhe ignore kora shuru kore

## Chalanor niyom
pip install -r requirements.txt
python generate_data.py       # 14 din, 1-min metrics + 8 test incident + 2 benign flash sale
python evaluate.py            # 5 method er comparison
pytest -q
uvicorn app.main:app --reload
  POST /ingest {"service":"api","timestamp":"2026-01-05T12:03:00","requests":520,"latency_ms":900,"error_rate":0.004,"cpu":45}
  -> {"score":..., "flagged":..., "alert":..., "reason":"latency"}

## 5ta method
1. static_threshold: Grafana style fixed limit
2. rolling_zscore: gotokal-er 60 min er tulonay (dhire barle 'normal' hoye jay)
3. seasonal_robust: ek minute of day er shadharon obostha theke robust z (MAD). Flash sale e false alarm
4. load_aware_robust: latency/cpu ke traffic er upor adjust kore (traffic bare bole latency bare, eta incident na). Serve kora hoy
5. isolation_forest: unsupervised ML, shob signal ekshathe

## Ja ja use hoy (ei project e ache)
- Seasonality (shokal/rat/weekend) baseline, robust statistics (median/MAD, outlier e kharap hoy na)
- Load-aware residual: "expected" bad diye dekha
- Alert engineering: sustained (3 min), dedupe/cooldown (30 min), reason soho alert
- Evaluation: incident-level recall, alert precision, false alarm/day, detection delay (accuracy na)
- Threshold training data theke (label dekhe na), test e ekbar-i report
- Stateful streaming API, thread lock, per-service state

## Tradeoff dekho (evaluate.py)
isolation_forest shob incident dhore kintu false alarm beshi. load_aware kom dhore kintu alert nirbhul.
Kon ta better? Seta team er alert-fatigue ar incident er khoti er upor nirbhor kore.

## Challenge
1. Multiple service er correlation (A fail korle B er alert alada kore dao, root cause group koro)
2. Alert feedback: engineer "false alarm" bolle threshold auto adjust
3. LSTM/autoencoder diye detect koro, iforest er sathe tulona
4. Dhire barar (drift) jonno CUSUM/EWMA add koro
5. Real data: Prometheus/Grafana export diye replace koro
6. Severity (low/high) assign koro
