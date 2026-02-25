"""
anomaly.py - Anomaly Detection

Identifies unusual data points using multiple methods:
  - Z-score: how many standard deviations away from the mean?
  - IQR (Interquartile Range): values outside Q1 - 1.5*IQR to Q3 + 1.5*IQR
  - Isolation Forest: ML-based anomaly detection from scikit-learn
"""

import pandas as pd
import numpy as np
from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


def detect_anomalies(df: pd.DataFrame, columns: list = None, method: str = "all") -> dict:
    """
    Detect anomalies in numeric columns of the DataFrame.

    Args:
        df: cleaned DataFrame
        columns: specific columns to check (if None, checks all numeric)
        method: "zscore", "iqr", "isolation_forest", or "all"

    Returns:
        dict with anomaly results per column and an overall summary.
    """
    numeric_cols = columns or df.select_dtypes(include=[np.number]).columns.tolist()

    if not numeric_cols:
        return {
            "status": "no_numeric_columns",
            "message": "No numeric columns to analyze for anomalies.",
        }

    results = {
        "per_column": {},
        "isolation_forest": None,
        "summary": {},
    }

    # Per-column analysis (Z-score + IQR)
    total_anomalies = 0
    for col in numeric_cols:
        col_result = _detect_column_anomalies(df[col], col, method)
        if col_result:
            results["per_column"][col] = col_result
            total_anomalies += col_result.get("total_anomalies", 0)

    # Multi-variate Isolation Forest
    if method in ("all", "isolation_forest") and len(numeric_cols) >= 2:
        iso_result = _isolation_forest(df, numeric_cols)
        if iso_result:
            results["isolation_forest"] = iso_result
            total_anomalies += iso_result.get("anomaly_count", 0)

    # Summary
    cols_with_anomalies = sum(
        1 for v in results["per_column"].values()
        if v.get("total_anomalies", 0) > 0
    )
    results["summary"] = {
        "total_anomalies_found": total_anomalies,
        "columns_analyzed": len(numeric_cols),
        "columns_with_anomalies": cols_with_anomalies,
        "method": method,
    }
    results["status"] = "success"

    return results


def _detect_column_anomalies(series: pd.Series, col_name: str, method: str) -> dict | None:
    """Detect anomalies in a single column using Z-score and/or IQR."""
    s = series.dropna()
    if len(s) < 10:
        return None

    result = {
        "total_anomalies": 0,
    }

    # Z-score method
    if method in ("all", "zscore"):
        mean = float(s.mean())
        std = float(s.std())
        if std > 0:
            z_scores = ((s - mean) / std).abs()
            z_anomalies = z_scores > 3  # 3 standard deviations
            z_count = int(z_anomalies.sum())
            z_indices = s[z_anomalies].index.tolist()[:20]  # limit to 20

            # Get actual anomalous values
            z_values = []
            for idx in z_indices:
                z_values.append({
                    "index": int(idx),
                    "value": round(float(s[idx]), 4),
                    "z_score": round(float(z_scores[idx]), 2),
                })

            result["zscore"] = {
                "count": z_count,
                "pct": round(z_count / len(s) * 100, 2),
                "threshold": 3.0,
                "anomalies": z_values,
            }
            result["total_anomalies"] += z_count

    # IQR method
    if method in ("all", "iqr"):
        q1 = float(s.quantile(0.25))
        q3 = float(s.quantile(0.75))
        iqr = q3 - q1

        if iqr > 0:
            lower = q1 - 1.5 * iqr
            upper = q3 + 1.5 * iqr
            iqr_mask = (s < lower) | (s > upper)
            iqr_count = int(iqr_mask.sum())
            iqr_indices = s[iqr_mask].index.tolist()[:20]

            iqr_values = []
            for idx in iqr_indices:
                val = float(s[idx])
                iqr_values.append({
                    "index": int(idx),
                    "value": round(val, 4),
                    "deviation": "below" if val < lower else "above",
                })

            result["iqr"] = {
                "count": iqr_count,
                "pct": round(iqr_count / len(s) * 100, 2),
                "lower_bound": round(lower, 4),
                "upper_bound": round(upper, 4),
                "anomalies": iqr_values,
            }
            # Use max of zscore and iqr for total
            if "zscore" in result:
                result["total_anomalies"] = max(result["total_anomalies"], iqr_count)
            else:
                result["total_anomalies"] += iqr_count

    return result


def _isolation_forest(df: pd.DataFrame, numeric_cols: list) -> dict | None:
    """
    Multi-variate anomaly detection using Isolation Forest.

    Isolation Forest works by randomly partitioning data.
    Anomalies are isolated faster (fewer partitions needed),
    so they get shorter path lengths in the trees.
    """
    try:
        X = df[numeric_cols].dropna()
        if len(X) < 20:
            return None

        # Scale features
        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(X)

        # Fit Isolation Forest
        contamination = min(0.1, max(0.01, 5.0 / len(X)))  # adaptive contamination
        iso = IsolationForest(
            contamination=contamination,
            random_state=42,
            n_estimators=100,
        )
        predictions = iso.fit_predict(X_scaled)
        scores = iso.decision_function(X_scaled)

        # -1 = anomaly, 1 = normal
        anomaly_mask = predictions == -1
        anomaly_count = int(anomaly_mask.sum())

        # Get top anomalies (most anomalous first, by score)
        anomaly_indices = np.where(anomaly_mask)[0]
        anomaly_scores = scores[anomaly_mask]
        sorted_idx = np.argsort(anomaly_scores)  # most negative = most anomalous

        top_anomalies = []
        for i in sorted_idx[:15]:  # top 15
            row_idx = int(anomaly_indices[i])
            row_data = {col: round(float(X.iloc[row_idx][col]), 4) for col in numeric_cols[:6]}
            top_anomalies.append({
                "row_index": row_idx,
                "anomaly_score": round(float(anomaly_scores[i]), 4),
                "values": row_data,
            })

        return {
            "anomaly_count": anomaly_count,
            "total_rows": len(X),
            "anomaly_pct": round(anomaly_count / len(X) * 100, 2),
            "contamination": round(contamination, 4),
            "top_anomalies": top_anomalies,
        }

    except Exception as e:
        print(f"Isolation Forest failed: {e}")
        return None
