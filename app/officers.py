"""
Aggregate view of the officer roster -- city-wide totals and per-station
breakdown. Pure aggregation over data already loaded at startup. Kept
separate from judging.py's get_station_capacity so nothing existing is
modified or re-used in a way that risks behavior change there.
"""
from .data_loader import data


def get_officer_summary():
    roster = data.officer_roster
    total = len(roster)
    available = int((roster["status"] == "available").sum())

    by_station = []
    for station, group in roster.groupby("police_station"):
        by_station.append({
            "police_station": station,
            "total": int(len(group)),
            "available": int((group["status"] == "available").sum()),
        })

    return {
        "total_officers": total,
        "available_officers": available,
        "by_station": sorted(by_station, key=lambda r: r["police_station"]),
    }