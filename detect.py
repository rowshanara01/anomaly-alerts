"""Anomaly detection: 5 method. Sobgulo score return kore (boro = beshi sondehojonok)."""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from sklearn.linear_model import LinearRegression

MET = ["requests", "latency_ms", "error_rate", "cpu"]
MAD = 1.4826   # MAD ke standard deviation er moto banay


def robust_scale(x):
    return float(np.median(np.abs(x - np.median(x))) * MAD) or 1e-9


class Baseline:
    """Training data theke 'shadharon obostha' shikhe: (1) minute-of-day onujayi seasonal median, (2) load er upor latency/cpu er nirbhorota"""
    def fit(self, df):
        self.seasonal = {}
        for c in MET:
            by_min = df.groupby("minute_of_day")[c].median().reindex(range(1440)).interpolate().values
            pad = np.r_[by_min[-7:], by_min, by_min[:7]]                       # circular smoothing (15 min)
            self.seasonal[c] = np.convolve(pad, np.ones(15) / 15, "valid")
        self.scale = {c: robust_scale(df[c].values - self.seasonal[c][df.minute_of_day.values]) for c in MET}
        self.load = {c: LinearRegression().fit(df[["requests"]], df[c]) for c in ("latency_ms", "cpu")}
        self.load_scale = {c: robust_scale(df[c].values - self.load[c].predict(df[["requests"]])) for c in self.load}
        return self

    def z(self, df):
        """Signed robust z-score: seasonal baseline theke koto durey (z_*), ar load-aware (zl_*)"""
        m = df.minute_of_day.values
        out = pd.DataFrame(index=df.index)
        for c in MET:
            out[f"z_{c}"] = (df[c].values - self.seasonal[c][m]) / self.scale[c]
        for c in self.load:
            out[f"zl_{c}"] = (df[c].values - self.load[c].predict(df[["requests"]])) / self.load_scale[c]
        return out


def score_static(df):
    """Prochalito Grafana-style fixed threshold. 1 er upore = alert"""
    return np.maximum.reduce([df.latency_ms / 350, df.error_rate / 0.05, df.cpu / 85])


def score_rolling_z(df, window=60):
    """Gotokal-er 60 min er tulonay. Dhire dhire barle 'normal' hoye jay (blind spot)"""
    zs = []
    for c in MET:
        past = df[c].shift(1)
        zs.append(((df[c] - past.rolling(window).mean()) / (past.rolling(window).std() + 1e-9)).abs())
    return pd.concat(zs, axis=1).max(axis=1).fillna(0).values


def score_seasonal(df, base):
    """Shob metric 2-dike seasonal baseline theke. Flash sale (beshi traffic) ke-o vul kore dhore"""
    return base.z(df)[[f"z_{c}" for c in MET]].abs().max(axis=1).values


def load_aware_parts(z):
    """Load-aware: traffic bare gele latency/cpu barar kotha, tai load-adjusted dekhi. Shudhu 'kharap dik' (one-sided)."""
    return pd.DataFrame({"traffic_drop": -z.z_requests, "error_rate": z.z_error_rate,
                         "latency": z.zl_latency_ms, "cpu": z.zl_cpu})


def score_load_aware(df, base):
    return load_aware_parts(base.z(df)).max(axis=1).values


def iforest_features(df, base):
    z = base.z(df)
    parts = load_aware_parts(z)
    feats = pd.concat([parts, parts.rolling(15, min_periods=1).mean().add_suffix("_15m")], axis=1)
    feats["latency_per_req"] = (df.latency_ms / df.requests.clip(lower=1)).values
    return feats.fillna(0)


class IForest:
    def fit(self, df, base):
        self.m = IsolationForest(n_estimators=200, random_state=0).fit(iforest_features(df, base))
        return self

    def score(self, df, base):
        return -self.m.score_samples(iforest_features(df, base))


def sustained(flag, k=3):
    """Shudhu ekta point na, porpor k minute kharap hole tobei alert (noise kombe)"""
    return pd.Series(flag).rolling(k).sum().fillna(0).values >= k


def episodes(alert_minutes, gap=30):
    """Kachakachi alert gulo ke ekta 'alert' hishebe gone (dedupe)"""
    out, last = [], None
    for a in alert_minutes:
        if last is None or a - last > gap:
            out.append([a, a])
        else:
            out[-1][1] = a
        last = a
    return out
