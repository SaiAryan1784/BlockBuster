"""
In-memory incident store. Tracks which specific officers (by officer_id)
are deployed to each incident, so /officers/summary reflects real
availability, and releases them automatically on resolve/delete.
"""
import itertools
from datetime import datetime, timezone

from .officer_deployment import deploy_officers, release_officers

_incidents = {}
_id_counter = itertools.count(1)


def create_incident(blocked_corridors, hour, label=None):
    incident_id = next(_id_counter)
    incident = {
        "id": incident_id,
        "label": label or f"Incident on {', '.join(blocked_corridors)}",
        "blocked_corridors": blocked_corridors,
        "hour": hour,
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "playbook": None,
        "deployed_officer_ids": [],
    }
    _incidents[incident_id] = incident
    return incident


def list_incidents(status=None):
    incidents = list(_incidents.values())
    if status:
        incidents = [i for i in incidents if i["status"] == status]
    return incidents


def get_incident(incident_id):
    return _incidents.get(incident_id)


def update_incident(incident_id, **fields):
    incident = _incidents.get(incident_id)
    if incident is None:
        return None
    incident.update(fields)
    return incident


def deploy_to_incident(incident_id, deployments):
    """deployments: list of {"police_station": str, "count": int}."""
    incident = _incidents.get(incident_id)
    if incident is None:
        return None
    newly_deployed = []
    for d in deployments:
        newly_deployed.extend(deploy_officers(d["police_station"], d["count"]))
    incident["deployed_officer_ids"].extend(newly_deployed)
    incident["status"] = "ACTIVE"
    return incident


def resolve_incident(incident_id):
    incident = _incidents.get(incident_id)
    if incident is None:
        return None
    release_officers(incident["deployed_officer_ids"])
    incident["deployed_officer_ids"] = []
    incident["status"] = "RESOLVED"
    return incident


def delete_incident(incident_id):
    incident = _incidents.get(incident_id)
    if incident is None:
        return False
    release_officers(incident["deployed_officer_ids"])
    del _incidents[incident_id]
    return True