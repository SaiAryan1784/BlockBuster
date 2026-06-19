"""
In-memory store for planned disruptions -- roadwork, VIP movements,
anything known in advance rather than reacted to live. Reuses the
existing, tested stress_test_plan() for impact preview; no new traffic
logic, just a different data model framing around it.
"""
import itertools
from datetime import datetime, timezone

from .simulation import stress_test_plan

_events = {}
_id_counter = itertools.count(1)


def create_event(label, event_type, affected_corridors, start_time, end_time, capacity_remaining_pct=0.5):
    event_id = next(_id_counter)
    event = {
        "id": event_id,
        "label": label,
        "event_type": event_type,  # "roadwork" | "vip_movement" | "other"
        "affected_corridors": affected_corridors,
        "start_time": start_time,
        "end_time": end_time,
        "capacity_remaining_pct": capacity_remaining_pct,
        "status": "SCHEDULED",
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _events[event_id] = event
    return event


def list_events(upcoming_only=False):
    events = list(_events.values())
    if upcoming_only:
        now = datetime.now(timezone.utc).isoformat()
        events = [e for e in events if e["end_time"] > now]
    return events


def get_event(event_id):
    return _events.get(event_id)


def update_event(event_id, **fields):
    event = _events.get(event_id)
    if event is None:
        return None
    event.update(fields)
    return event


def delete_event(event_id):
    return _events.pop(event_id, None) is not None


def preview_event_impact(event_id, hour):
    event = _events.get(event_id)
    if event is None:
        return None
    state, result = stress_test_plan(event["affected_corridors"], hour, event["capacity_remaining_pct"])
    return {"network_state": state.to_dict("records"), "stress_test": result}