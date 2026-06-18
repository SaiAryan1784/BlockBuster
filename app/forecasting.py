"""
Layer 1 (Prediction). Direct port of predict_disruption_risk() from the
notebook - unchanged logic, just reading from the loaded data instance
instead of notebook globals.
"""
import pandas as pd

from .data_loader import data


def predict_disruption_risk(corridor: str, timestamp: pd.Timestamp) -> float:
    """
    Input:  corridor name, timestamp (any pandas-parseable datetime)
    Output: probability of an unplanned disruption in that corridor's 3-hour bin
    """
    bin_start = pd.Timestamp(timestamp).floor("3h")
    if bin_start.tzinfo is None:
        bin_start = bin_start.tz_localize("UTC")

    hist = data.panel[(data.panel["corridor"] == corridor) & (data.panel["bin_start"] < bin_start)]
    past_7d = hist[hist["bin_start"] > bin_start - pd.Timedelta(days=7)]["event_count"].sum()
    past_30d = hist[hist["bin_start"] > bin_start - pd.Timedelta(days=30)]["event_count"].sum()

    row = pd.DataFrame(
        [
            {
                "hour_of_day": bin_start.hour,
                "day_of_week": bin_start.dayofweek,
                "is_weekend": int(bin_start.dayofweek in [5, 6]),
                "month": bin_start.month,
                "past_7d_count": past_7d,
                "past_30d_count": past_30d,
            }
        ]
    )
    return float(data.model.predict_proba(row[data.model_feature_cols])[0, 1])
