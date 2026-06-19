from typing import List

from pydantic import BaseModel


class DisasterRequest(BaseModel):
    target_corridors: List[str]
    hour: int
    capacity_remaining_pct: float = 0.0


class RouteRequest(BaseModel):
    origin: str
    destination: str
    blocked_corridors: List[str]
    hour: int
    capacity_remaining_pct: float = 0.0
    red_threshold: float = 0.9


class PlaybookRequest(BaseModel):
    blocked_corridors: List[str]
    hour: int
    origin: str
    destination: str
    capacity_remaining_pct: float = 0.0
    red_threshold: float = 0.6
    n_officers: int = 3


class ForecastRequest(BaseModel):
    corridor: str
    timestamp: str  # ISO 8601, e.g. "2026-07-04T09:00:00Z"

class PlaybookRenderRequest(BaseModel):
    playbook: dict


class AdvisoryRequest(BaseModel):
    playbook: dict

class SMSDispatchRequest(BaseModel):
    playbook: dict
    advisory_text: str  
    recipients: list  

class BarricadeRequest(BaseModel):
    blocked_corridors: List[str]
    network_state: List[dict]


class SignalOverrideRequest(BaseModel):
    network_state: List[dict]


class IncidentCreateRequest(BaseModel):
    blocked_corridors: List[str]
    hour: int
    label: str = None


class IncidentUpdateRequest(BaseModel):
    status: str = None
    playbook: dict = None

class IncidentDeployRequest(BaseModel):
    deployments: List[dict]


class ScheduledEventRequest(BaseModel):
    label: str
    event_type: str
    affected_corridors: List[str]
    start_time: str
    end_time: str
    capacity_remaining_pct: float = 0.5


class ScheduledEventUpdateRequest(BaseModel):
    label: str = None
    status: str = None
    capacity_remaining_pct: float = None

