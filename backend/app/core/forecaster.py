"""
forecaster.py - Time-Series Forecasting

Uses Facebook Prophet to forecast future values of numeric metrics.
Falls back to linear extrapolation if Prophet fails.

Prophet is great because:
  - It handles missing data well
  - It automatically detects seasonality (weekly, yearly patterns)
  - Easy to use: just give it dates and values
"""

import pandas as pd
import numpy as np
from scipy import stats as sp_stats


def generate_forecast(df, date_col: str, value_col: str, periods: int = 30) -> dict:
    """
    Generate a forecast for a numeric column.

    Tries Prophet first. If unavailable or fails, uses linear extrapolation.

    Args:
        df: DataFrame with at least a date column and a value column
        date_col: name of the datetime column
        value_col: name of the numeric column to forecast
        periods: how many future periods to predict

    Returns:
        dict with historical data, forecast data, confidence intervals, and method used.
    """
    # Prepare data
    data = df[[date_col, value_col]].dropna().sort_values(date_col).copy()
    data.columns = ["ds", "y"]

    if len(data) < 4:
        return {
            "status": "insufficient_data",
            "message": f"Need at least 4 data points, got {len(data)}.",
        }

    # Detect frequency
    freq = _detect_frequency(data["ds"])

    # Try Prophet first
    forecast = _prophet_forecast(data, periods, freq)
    if forecast is not None:
        return forecast

    # Fallback: linear extrapolation
    return _linear_forecast(data, periods, freq, value_col)


def generate_all_forecasts(df, date_col: str, numeric_cols: list, periods: int = 30) -> dict:
    """
    Generate forecasts for all numeric columns that have enough data.

    Returns:
        dict keyed by column name with forecast results.
    """
    forecasts = {}
    for col in numeric_cols[:5]:  # limit to 5 columns
        result = generate_forecast(df, date_col, col, periods)
        if result.get("status") != "insufficient_data":
            forecasts[col] = result
    return forecasts


def _detect_frequency(dates: pd.Series) -> str:
    """Detect the time frequency of the data."""
    if len(dates) < 2:
        return "D"

    diffs = dates.diff().dropna()
    median_diff = diffs.median()

    days = median_diff.days if hasattr(median_diff, "days") else 1

    if days <= 1:
        return "D"
    elif days <= 8:
        return "W"
    elif days <= 35:
        return "MS"
    elif days <= 100:
        return "QS"
    else:
        return "YS"


def _prophet_forecast(data: pd.DataFrame, periods: int, freq: str) -> dict | None:
    """Try to forecast using Prophet. Returns None if Prophet is unavailable."""
    try:
        from prophet import Prophet

        model = Prophet(
            yearly_seasonality="auto",
            weekly_seasonality="auto",
            daily_seasonality=False,
            changepoint_prior_scale=0.05,
        )
        model.fit(data)

        future = model.make_future_dataframe(periods=periods, freq=freq)
        forecast = model.predict(future)

        # Extract results
        historical = data.to_dict(orient="records")
        for row in historical:
            row["ds"] = row["ds"].isoformat() if hasattr(row["ds"], "isoformat") else str(row["ds"])

        forecast_records = []
        for _, row in forecast.tail(periods).iterrows():
            forecast_records.append({
                "ds": row["ds"].isoformat() if hasattr(row["ds"], "isoformat") else str(row["ds"]),
                "yhat": round(float(row["yhat"]), 4),
                "yhat_lower": round(float(row["yhat_lower"]), 4),
                "yhat_upper": round(float(row["yhat_upper"]), 4),
            })

        # Full timeline for plotting
        full_timeline = []
        for _, row in forecast.iterrows():
            full_timeline.append({
                "ds": row["ds"].isoformat() if hasattr(row["ds"], "isoformat") else str(row["ds"]),
                "yhat": round(float(row["yhat"]), 4),
                "yhat_lower": round(float(row["yhat_lower"]), 4),
                "yhat_upper": round(float(row["yhat_upper"]), 4),
            })

        return {
            "status": "success",
            "method": "prophet",
            "periods": periods,
            "frequency": freq,
            "historical": historical,
            "forecast": forecast_records,
            "full_timeline": full_timeline,
        }

    except ImportError:
        return None
    except Exception as e:
        print(f"Prophet failed: {e}")
        return None


def _linear_forecast(data: pd.DataFrame, periods: int, freq: str, col_name: str) -> dict:
    """Fallback linear extrapolation forecast."""
    x = np.arange(len(data))
    y = data["y"].values.astype(float)

    slope, intercept, r_value, p_value, std_err = sp_stats.linregress(x, y)

    # Generate future x values
    future_x = np.arange(len(data), len(data) + periods)
    future_y = slope * future_x + intercept

    # Confidence interval (rough: +/- 1.96 * std_err * sqrt(distance))
    residuals = y - (slope * x + intercept)
    rmse = float(np.sqrt(np.mean(residuals ** 2)))

    # Build future dates
    last_date = data["ds"].iloc[-1]
    future_dates = pd.date_range(start=last_date, periods=periods + 1, freq=freq)[1:]

    historical = data.to_dict(orient="records")
    for row in historical:
        row["ds"] = row["ds"].isoformat() if hasattr(row["ds"], "isoformat") else str(row["ds"])

    forecast_records = []
    for i, (date, yhat) in enumerate(zip(future_dates, future_y)):
        margin = 1.96 * rmse * np.sqrt(1 + (i + 1) / len(data))
        forecast_records.append({
            "ds": date.isoformat(),
            "yhat": round(float(yhat), 4),
            "yhat_lower": round(float(yhat - margin), 4),
            "yhat_upper": round(float(yhat + margin), 4),
        })

    # Full timeline
    fitted_y = slope * x + intercept
    full_timeline = []
    for date_val, yhat in zip(data["ds"].values, fitted_y):
        ds = pd.Timestamp(date_val)
        full_timeline.append({
            "ds": ds.isoformat(),
            "yhat": round(float(yhat), 4),
            "yhat_lower": round(float(yhat - rmse), 4),
            "yhat_upper": round(float(yhat + rmse), 4),
        })
    full_timeline.extend(forecast_records)

    return {
        "status": "success",
        "method": "linear_extrapolation",
        "periods": periods,
        "frequency": freq,
        "r_squared": round(float(r_value ** 2), 4),
        "slope": round(float(slope), 6),
        "rmse": round(rmse, 4),
        "historical": historical,
        "forecast": forecast_records,
        "full_timeline": full_timeline,
    }
