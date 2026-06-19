"""
In-memory officer deployment tracking. Marks specific officers as
deployed/busy when assigned to an incident, and frees them when it
resolves. Does NOT mutate data.officer_roster (the already-loaded,
already-tested dataframe) -- this is purely additive bookkeeping
layered on top of it, in its own module.
"""
from .data_loader import data

_deployed_officer_ids = set()


def deploy_officers(station_name, count):
    """Pick up to `count` currently-available officers from a station
    and mark them deployed. Returns the list of officer_ids deployed."""
    station_officers = data.officer_roster[
        (data.officer_roster["police_station"] == station_name)
        & (data.officer_roster["status"] == "available")
    ]
    eligible = [oid for oid in station_officers["officer_id"] if oid not in _deployed_officer_ids]
    chosen = eligible[:count]
    _deployed_officer_ids.update(chosen)
    return chosen


def release_officers(officer_ids):
    for oid in officer_ids:
        _deployed_officer_ids.discard(oid)


def deployed_count_for_station(station_name):
    station_ids = set(
        data.officer_roster[data.officer_roster["police_station"] == station_name]["officer_id"]
    )
    return len(station_ids & _deployed_officer_ids)