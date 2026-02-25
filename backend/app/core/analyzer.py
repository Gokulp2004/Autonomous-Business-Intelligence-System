"""
analyzer.py - Statistical Analysis Engine

Performs automated analysis on cleaned data:
  - Descriptive statistics (mean, median, std, quartiles, etc.)
  - Correlation analysis (Pearson + strength classification)
  - Trend detection (linear regression on time-series)
  - Distribution analysis (skewness, kurtosis, normality test)
  - Categorical column profiling
  - Feature importance ranking (mutual information)
  - Segment analysis (group-by stats for top categorical columns)
"""

import pandas as pd
import numpy as np
from scipy import stats as sp_stats
from sklearn.feature_selection import mutual_info_regression


def run_analysis(df: pd.DataFrame) -> dict:
    """
    Run comprehensive statistical analysis on a cleaned DataFrame.

    Returns:
        dict with analysis results organized by category.
    """
    results = {}

    numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
    cat_cols = df.select_dtypes(include=["object", "category"]).columns.tolist()
    datetime_cols = df.select_dtypes(include=["datetime64"]).columns.tolist()

    # 1. Descriptive Statistics
    if numeric_cols:
        desc_rows = {}
        for col in numeric_cols:
            s = df[col].dropna()
            desc_rows[col] = {
                "count": int(s.count()),
                "mean": round(float(s.mean()), 4),
                "std": round(float(s.std()), 4),
                "min": round(float(s.min()), 4),
                "q1": round(float(s.quantile(0.25)), 4),
                "median": round(float(s.median()), 4),
                "q3": round(float(s.quantile(0.75)), 4),
                "max": round(float(s.max()), 4),
                "range": round(float(s.max() - s.min()), 4),
                "iqr": round(float(s.quantile(0.75) - s.quantile(0.25)), 4),
                "cv": round(float(s.std() / s.mean()), 4) if s.mean() != 0 else None,
            }
        results["descriptive_stats"] = desc_rows

    # 2. Correlation Matrix
    if len(numeric_cols) >= 2:
        corr_matrix = df[numeric_cols].corr()
        results["correlation_matrix"] = {
            col: {col2: round(float(v), 4) for col2, v in row.items()}
            for col, row in corr_matrix.to_dict().items()
        }

        strong = []
        for i in range(len(numeric_cols)):
            for j in range(i + 1, len(numeric_cols)):
                r = corr_matrix.iloc[i, j]
                if abs(r) > 0.7:
                    abs_r = abs(r)
                    strength = (
                        "very_strong" if abs_r > 0.9
                        else "strong" if abs_r > 0.7
                        else "moderate"
                    )
                    strong.append({
                        "col_a": numeric_cols[i],
                        "col_b": numeric_cols[j],
                        "correlation": round(float(r), 4),
                        "strength": strength,
                        "direction": "positive" if r > 0 else "negative",
                    })
        strong.sort(key=lambda x: abs(x["correlation"]), reverse=True)
        results["strong_correlations"] = strong

    # 3. Distribution Analysis
    distributions = {}
    for col in numeric_cols:
        s = df[col].dropna()
        if len(s) < 8:
            continue
        skew = float(s.skew())
        kurt = float(s.kurtosis())

        sample = s.sample(min(5000, len(s)), random_state=42)
        try:
            _, p_val = sp_stats.shapiro(sample)
            is_normal = p_val > 0.05
        except Exception:
            p_val = None
            is_normal = abs(skew) < 1

        if abs(skew) < 0.5:
            shape = "symmetric"
        elif skew > 0:
            shape = "right_skewed"
        else:
            shape = "left_skewed"

        distributions[col] = {
            "skewness": round(skew, 4),
            "kurtosis": round(kurt, 4),
            "shapiro_p": round(float(p_val), 6) if p_val is not None else None,
            "is_normal": is_normal,
            "shape": shape,
        }
    results["distributions"] = distributions

    # 4. Categorical Column Summary
    cat_summary = {}
    for col in cat_cols:
        vc = df[col].value_counts()
        cat_summary[col] = {
            "unique_count": int(df[col].nunique()),
            "top_values": {str(k): int(v) for k, v in vc.head(10).items()},
            "top_value": str(vc.index[0]) if len(vc) > 0 else None,
            "top_freq": int(vc.iloc[0]) if len(vc) > 0 else 0,
            "top_pct": round(float(vc.iloc[0] / len(df) * 100), 1) if len(vc) > 0 else 0,
        }
    results["categorical_summary"] = cat_summary

    # 5. Time-series Detection + Trends
    results["datetime_columns"] = datetime_cols
    results["is_timeseries"] = len(datetime_cols) > 0
    trends = {}

    if datetime_cols and numeric_cols:
        date_col = datetime_cols[0]
        df_sorted = df.sort_values(date_col).dropna(subset=[date_col])

        for col in numeric_cols[:8]:
            s = df_sorted[col].dropna()
            if len(s) < 4:
                continue
            x = np.arange(len(s))
            y = s.values.astype(float)

            slope, intercept, r_value, p_value, std_err = sp_stats.linregress(x, y)
            trends[col] = {
                "slope": round(float(slope), 6),
                "r_squared": round(float(r_value ** 2), 4),
                "p_value": round(float(p_value), 6),
                "direction": "increasing" if slope > 0 else "decreasing",
                "significant": p_value < 0.05,
                "start_val": round(float(y[0]), 4),
                "end_val": round(float(y[-1]), 4),
                "pct_change": round(float((y[-1] - y[0]) / y[0] * 100), 2) if y[0] != 0 else None,
            }
    results["trends"] = trends

    # 6. Feature Importance (Mutual Information)
    if len(numeric_cols) >= 2:
        fi = _compute_feature_importance(df, numeric_cols, cat_cols)
        if fi:
            results["feature_importance"] = fi

    # 7. Segment Analysis
    if cat_cols and numeric_cols:
        segments = _segment_analysis(df, cat_cols[:3], numeric_cols[:5])
        if segments:
            results["segments"] = segments

    # 8. Summary
    results["summary"] = {
        "total_rows": len(df),
        "total_columns": len(df.columns),
        "numeric_columns": len(numeric_cols),
        "categorical_columns": len(cat_cols),
        "datetime_columns": len(datetime_cols),
        "has_strong_correlations": len(results.get("strong_correlations", [])) > 0,
        "has_trends": len(trends) > 0,
        "normal_distributions": sum(1 for d in distributions.values() if d.get("is_normal")),
    }

    return results


def _compute_feature_importance(df, numeric_cols, cat_cols):
    """Rank feature importance using mutual information."""
    if len(numeric_cols) < 2:
        return None
    try:
        target_col = numeric_cols[-1]
        feature_cols = [c for c in numeric_cols if c != target_col]
        if not feature_cols:
            return None

        X = df[feature_cols].fillna(0)
        y = df[target_col].fillna(0)

        mi_scores = mutual_info_regression(X, y, random_state=42)

        importance = []
        for col, score in sorted(zip(feature_cols, mi_scores), key=lambda x: x[1], reverse=True):
            importance.append({
                "feature": col,
                "importance": round(float(score), 4),
                "target": target_col,
            })
        return importance[:10]
    except Exception:
        return None


def _segment_analysis(df, cat_cols, numeric_cols):
    """Group-by analysis: how do numeric columns differ across categories?"""
    segments = {}
    for cat_col in cat_cols:
        if df[cat_col].nunique() > 20 or df[cat_col].nunique() < 2:
            continue

        seg = {}
        for num_col in numeric_cols:
            try:
                grouped = df.groupby(cat_col)[num_col].agg(["mean", "median", "std", "count"])
                grouped = grouped.dropna()
                if len(grouped) < 2:
                    continue
                seg[num_col] = {
                    str(idx): {
                        "mean": round(float(row["mean"]), 4),
                        "median": round(float(row["median"]), 4),
                        "std": round(float(row["std"]), 4) if not np.isnan(row["std"]) else 0,
                        "count": int(row["count"]),
                    }
                    for idx, row in grouped.iterrows()
                }
            except Exception:
                continue

        if seg:
            segments[cat_col] = seg

    return segments
