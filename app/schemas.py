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
    playbook: dict  # The full /playbook-stream final payload
    advisory_text: str  # From /advisory endpoint
    recipients: list  # E.g., ["+919xxxxxxxxx", "+919yyyyyyyyy"]
