"""
Read-only analytics over the historical panel data already loaded at
startup, plus the locked validation metrics from model training. No
mutation, no interaction with the simulation engine.
"""
from .data_loader import data

MODEL_METRICS = {
    "auc_roc": 0.8112,
    "pr_auc": 0.4095,
    "random_baseline_pr_auc": 0.1509,
    "lift_over_baseline": round(0.4095 / 0.1509, 2),
}


def get_analytics_summary():
    panel = data.panel
    by_corridor = (
        panel.groupby("corridor")["event_count"]
        .sum()
        .sort_values(ascending=False)
        .reset_index()
        .rename(columns={"event_count": "total_historical_events"})
        .to_dict("records")
    )
    return {
        "model_metrics": MODEL_METRICS,
        "historical_data_range": {
            "start": str(panel["bin_start"].min()),
            "end": str(panel["bin_start"].max()),
            "total_rows": len(panel),
        },
        "corridors_by_historical_frequency": by_corridor,
    }


def get_corridor_history(corridor):
    rows = data.panel[data.panel["corridor"] == corridor].sort_values("bin_start")
    return [{"bin_start": str(r["bin_start"]), "event_count": int(r["event_count"])} for _, r in rows.iterrows()]