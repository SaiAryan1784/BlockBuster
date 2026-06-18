"""
Judging Panel module. Direct port of get_station_capacity and
generate_judging_checklist from the notebook.
"""
from .data_loader import data


def get_station_capacity(station_name):
    avail = data.officer_roster[
        (data.officer_roster["police_station"] == station_name) & (data.officer_roster["status"] == "available")
    ]
    return len(avail), avail["officer_id"].tolist()


def generate_judging_checklist(stress_result, route_result, officers_needed=2, nearest_stations_df=None):
    checks = []

    safety_ok = stress_result["status"] in ("PASSED", "PASSED_AFTER_REROUTE")
    safety_note = "No protected route degraded" if safety_ok else "Protected route still at risk after re-solve"
    if stress_result.get("resolved_by_reroute"):
        safety_note += f" (re-solved around {stress_result['violated_initially']})"
    checks.append({"check": "Safety", "passed": safety_ok, "detail": safety_note})

    route_ok = route_result["status"] in ("CLEAN", "BEST_AVAILABLE")
    notes = (
        [f"Diversion route found ({route_result['status']}), ETA {route_result['eta_minutes']} min"]
        if route_ok
        else ["No viable diversion route found"]
    )

    officer_ok = True
    if nearest_stations_df is not None:
        total_available = sum(get_station_capacity(r["police_station"])[0] for _, r in nearest_stations_df.iterrows())
        officer_ok = total_available >= officers_needed
        notes.append(f"{total_available} officers available across nearest stations (need {officers_needed})")

    feasible = route_ok and officer_ok
    checks.append({"check": "Feasibility", "passed": feasible, "detail": "; ".join(notes)})

    clarity_ok = route_result.get("bottleneck") is not None or route_result["status"] == "NO_PATH"
    clarity_note = (
        f"Bottleneck identified: {route_result.get('bottleneck')} at {route_result.get('bottleneck_vc')} V/C"
        if route_result.get("bottleneck")
        else "No bottleneck data (no-path case)"
    )
    checks.append({"check": "Clarity", "passed": clarity_ok, "detail": clarity_note})

    overall_passed = all(c["passed"] for c in checks)
    return {
        "state": "PENDING_APPROVAL",
        "overall_recommendation": "APPROVE" if overall_passed else "REVIEW_REQUIRED",
        "checks": checks,
        "requires_watch_commander_approval": True,
    }
