#### Anomaly Detection + Smart Alerts (AIOps) ####

## The Problem ##

Server latency suddenly increases, errors increase, or traffic drops unexpectedly. Humans cannot monitor servers 24/7.

However, using only fixed thresholds (e.g., "latency > 350") creates several problems:

- Gradual increases (memory leaks) may go undetected.
- Sudden traffic drops (outages) may go undetected.
- During a flash sale, traffic may double, causing false alarms.
- Over time, teams start ignoring alerts because they receive too many false notifications. This is known as alert fatigue.

The goal is to build an intelligent anomaly detection system that can identify unusual server behavior and generate meaningful alerts automatically.

## How to Run the Project ##

Install the dependencies:

pip install -r requirements.txt

Generate the dataset:

python generate_data.py

Generates 14 days of one-minute server metrics, including:
- 8 test incidents.
- 2 benign flash sale events.

Evaluate all detection methods:

python evaluate.py

Run automated tests:

pytest -q

Start the API:

uvicorn app.main:app --reload

### API Example ##

Send a POST request to:

POST /ingest

Request body:

{
  "service": "api",
  "timestamp": "2026-01-05T12:03:00",
  "requests": 520,
  "latency_ms": 900,
  "error_rate": 0.004,
  "cpu": 45
}

Example response:

{
  "score": "...",
  "flagged": "...",
  "alert": "...",
  "reason": "latency"
}

The API analyzes incoming server metrics and returns an anomaly score, detection status, alert status, and the reason behind the detection.

## The 5 Anomaly Detection Methods ##

### 1. Static Threshold

A traditional monitoring approach similar to Grafana's fixed threshold alerts.

Example:

If latency > 350 ms, trigger an alert.

Limitation:
It cannot effectively detect gradual changes or unexpected traffic drops.

### 2. Rolling Z-Score

Compares current server metrics against the previous 60 minutes.

It identifies unusual changes relative to recent behavior.

Limitation:
Gradual increases can eventually become part of the new normal, making slow memory leaks difficult to detect.

### 3. Seasonal Robust Detection

Uses the normal behavior of the same minute of the day as a baseline.

It applies robust Z-scores using Median and MAD (Median Absolute Deviation).

It accounts for:
- Morning vs. night traffic.
- Weekday vs. weekend behavior.
- Normal daily traffic patterns.

Limitation:
During flash sales, traffic may increase significantly and trigger false alarms.

### 4. Load-Aware Robust Detection

Adjusts expected latency and CPU usage based on incoming traffic.

Instead of directly checking whether latency is high, it calculates how much the actual latency differs from the expected latency at the current traffic level.

For example:

If traffic increases, latency may naturally increase as well.

The system understands this relationship and avoids treating every traffic-related increase as an incident.

This is the selected method for production serving in this project.

### 5. Isolation Forest

An unsupervised machine learning algorithm that analyzes multiple server metrics together.

It can detect unusual patterns involving:
- Latency.
- Error rate.
- CPU usage.
- Request volume.

Unlike simple threshold-based approaches, it considers multiple signals simultaneously.

## Technologies and Engineering Concepts Used

### 1. Seasonality and Baseline Modeling

Build a baseline of normal server behavior based on:
- Morning and night traffic.
- Weekday and weekend patterns.
- Time-based variations.

### 2. Robust Statistics

Use:
- Median.
- MAD (Median Absolute Deviation).
- Robust Z-score.

These methods are less sensitive to extreme outliers than traditional mean and standard deviation.

### 3. Load-Aware Residual Detection

Calculate the expected metric value based on traffic load.

Then compare:

Residual = Actual Value - Expected Value

This helps distinguish normal load-related increases from actual anomalies.

### 4. Alert Engineering

Implement practical alert management techniques:

- Sustained detection: An anomaly must continue for 3 minutes before triggering an alert.
- Deduplication: Avoid sending duplicate alerts for the same incident.
- Cooldown: Apply a 30-minute cooldown period.
- Reason-based alerts: Include the reason behind each alert.

### 5. Evaluation Metrics

Evaluate the system using operational metrics instead of relying only on accuracy.

Measure:

- Incident-level Recall: How many real incidents were detected?
- Alert Precision: How many generated alerts were actually valid?
- False Alarms per Day: How frequently does the system generate unnecessary alerts?
- Detection Delay: How long does it take to detect an incident?

### 6. Threshold Selection

Determine detection thresholds using training data without looking at incident labels.

Evaluate the final performance on test data only once.

This helps prevent data leakage and unrealistic performance estimates.

### 7. Stateful Streaming API

Implement:
- Stateful metric processing.
- Thread locking.
- Per-service state management.

This allows the system to process incoming metrics while maintaining separate monitoring states for different services.

## Understanding the Trade-offs

Run:

python evaluate.py

Compare the five detection methods.

Key observation:

**Isolation Forest:**
- Detects more incidents.
- Generates more false alarms.

**Load-Aware Robust Detection:**
- May miss some incidents.
- Generates more reliable alerts with fewer false positives.

Which one is better?

It depends on the engineering team's priorities.

For example:
- If missing a critical incident is extremely expensive, higher recall may be more important.
- If engineers receive too many false alerts, reducing false positives becomes essential.

The final decision depends on incident impact, alert fatigue, and operational requirements.

## Advanced Challenges

### 1. Multi-Service Correlation

Detect relationships between multiple services.

For example:

If Service A fails and Service B starts generating errors, identify the relationship.

Instead of generating separate alerts for every service, group related alerts and identify the possible root cause.

### 2. Alert Feedback System

Allow engineers to provide feedback on generated alerts.

For example:

- True Positive.
- False Positive.
- Expected Behavior.

Use this feedback to improve detection thresholds and reduce unnecessary alerts.

### 3. LSTM and Autoencoder-Based Detection

Implement deep learning-based anomaly detection using:

- LSTM.
- Autoencoders.

Compare their performance against Isolation Forest.

### 4. Detect Gradual Changes Using CUSUM and EWMA

Implement:

- CUSUM (Cumulative Sum Control Chart).
- EWMA (Exponentially Weighted Moving Average).

These techniques can help detect gradual changes, such as slowly increasing latency or memory usage.

### 5. Use Real-World Monitoring Data

Replace the generated dataset with real monitoring data exported from:

- Prometheus.
- Grafana.

Evaluate the system using actual production metrics.

### 6. Automatic Severity Classification

Assign severity levels to detected incidents.

For example:

- Low: Minor performance degradation.
- Medium: Noticeable service degradation.
- High: Critical service failure or major outage.

Use severity levels to prioritize alerts and help engineers respond to critical incidents first.

---

## Project Goal

Build an intelligent, production-oriented AIOps monitoring system that automatically detects unusual server behavior, understands normal traffic patterns, reduces false alarms, correlates incidents, and generates actionable alerts.

The goal is not just to detect anomalies but to build a smart monitoring system that helps engineering teams identify problems before they significantly impact users.
