"""
BlockBuster API. Wires the Core Engine (forecasting, simulation, routing,
stress test), the Judging Panel checklist, and the Gemini-backed rendering
layer (plain-English playbook + public advisory draft) into REST endpoints
the frontend (and later, the live log stream / SMS dispatch) will call.
"""
import pandas as pd
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .data_loader import data
from .forecasting import predict_disruption_risk
from .judging import generate_judging_checklist
from .llm import generate_public_advisory, render_playbook_text
from .routing import build_travel_time_graph, find_safe_route, nearest_police_stations_by_time
from .schemas import (
    AdvisoryRequest,
    DisasterRequest,
    ForecastRequest,
    PlaybookRenderRequest,
    PlaybookRequest,
    RouteRequest,
)
from .simulation import inject_disaster, stress_test_plan
from .utils import sanitize_floats
from fastapi import HTTPException
import json
from fastapi.responses import StreamingResponse
from .routing import find_safe_route_stream
from .simulation import stress_test_plan_stream

from .sms import send_public_advisory
from .schemas import SMSDispatchRequest

app = FastAPI(title="BlockBuster API")

# Loosen this to your actual frontend origin before deploying for real
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health():
    return {"status": "ok", "corridors_loaded": len(data.corridors)}


@app.get("/corridors")
def get_corridors():
    return {"corridors": data.corridors}


@app.post("/forecast")
def forecast(req: ForecastRequest):
    ts = pd.Timestamp(req.timestamp)
    risk = predict_disruption_risk(req.corridor, ts)
    return {"corridor": req.corridor, "timestamp": req.timestamp, "risk": risk}


@app.post("/simulate")
def simulate(req: DisasterRequest):
    state, _, unresolved = inject_disaster(req.target_corridors, req.hour, req.capacity_remaining_pct)
    return sanitize_floats({"network_state": state.to_dict("records"), "unresolved_excess": round(unresolved, 1)})


@app.post("/stress-test")
def stress_test(req: DisasterRequest):
    state, result = stress_test_plan(req.target_corridors, req.hour, req.capacity_remaining_pct)
    return sanitize_floats({"network_state": state.to_dict("records"), "result": result})


@app.post("/route")
def route(req: RouteRequest):
    state, _, _ = inject_disaster(req.blocked_corridors, req.hour, req.capacity_remaining_pct)
    result = find_safe_route(req.origin, req.destination, state, req.blocked_corridors, red_threshold=req.red_threshold)
    return sanitize_floats(result)


@app.post("/playbook")
def playbook(req: PlaybookRequest):
    """The full pipeline: stress test -> route -> officer ETA -> judging checklist."""
    state, stress_result = stress_test_plan(req.blocked_corridors, req.hour, req.capacity_remaining_pct)
    route_result = find_safe_route(
        req.origin, req.destination, state, req.blocked_corridors, red_threshold=req.red_threshold
    )

    G_time = build_travel_time_graph(state)
    nearest = nearest_police_stations_by_time(req.blocked_corridors[0], G_time, n=req.n_officers + 2)

    checklist = generate_judging_checklist(
        stress_result, route_result, officers_needed=req.n_officers, nearest_stations_df=nearest
    )

    return sanitize_floats({
        "disaster": {"blocked_corridors": req.blocked_corridors, "hour": req.hour},
        "network_state": state.to_dict("records"),
        "stress_test": stress_result,
        "diversion": route_result,
        "nearest_officers": nearest.to_dict("records"),
        "judging_panel": checklist,
    })


@app.post("/render-playbook")
def render_playbook_endpoint(req: PlaybookRenderRequest):
    """LLM rendering layer only -- takes the already-computed /playbook JSON
    and turns it into a plain-English briefing. No decision-making here."""
    try:
        narrative = render_playbook_text(req.playbook)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM renderer unavailable: {e}")
    return {"narrative": narrative}


@app.post("/advisory")
def advisory_endpoint(req: AdvisoryRequest):
    """Draft-only public advisory, hard-capped at 160 chars. Not broadcast
    by this endpoint -- on-screen draft for a human to approve and send."""
    try:
        text = generate_public_advisory(req.playbook)
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"LLM advisory unavailable: {e}")
    return {"advisory": text, "char_count": len(text), "note": "draft only, not broadcast"}


def _sse_event(event: dict) -> str:
    return f"data: {json.dumps(sanitize_floats(event))}\n\n"


@app.post("/playbook-stream")
def playbook_stream(req: PlaybookRequest):
    """Same pipeline as /playbook, but streamed live over SSE: stress
    test -> route negotiation -> officer lookup -> judging checklist.
    Each step is emitted as it's computed, not replayed after the fact."""
    def event_generator():
        state = None
        stress_result = None
        for event in stress_test_plan_stream(req.blocked_corridors, req.hour, req.capacity_remaining_pct):
            if event["type"] == "result":
                state = event["state"]
                stress_result = event["result"]
            else:
                yield _sse_event(event)

        route_result = None
        for event in find_safe_route_stream(
            req.origin, req.destination, state, req.blocked_corridors, red_threshold=req.red_threshold
        ):
            if event["type"] == "result":
                route_result = event["data"]
            else:
                yield _sse_event(event)

        G_time = build_travel_time_graph(state)
        nearest = nearest_police_stations_by_time(req.blocked_corridors[0], G_time, n=req.n_officers + 2)
        yield _sse_event({"type": "log", "stage": "officers", "message": f"Identified nearest {req.n_officers + 2} stations by travel time."})

        checklist = generate_judging_checklist(
            stress_result, route_result, officers_needed=req.n_officers, nearest_stations_df=nearest
        )
        yield _sse_event({"type": "log", "stage": "judging", "message": "Judging Panel checklist evaluated."})

        final_payload = sanitize_floats({
            "disaster": {"blocked_corridors": req.blocked_corridors, "hour": req.hour},
            "network_state": state.to_dict("records"),
            "stress_test": stress_result,
            "diversion": route_result,
            "nearest_officers": nearest.to_dict("records"),
            "judging_panel": checklist,
        })
        yield f"data: {json.dumps({'type': 'done', 'data': final_payload})}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")

@app.post("/sms-dispatch")
def sms_dispatch(req: SMSDispatchRequest):
    """
    Dispatch the public advisory SMS, but ONLY if Judging Panel approved it.
    This is a manual action triggered by Watch Commander, never automatic.
    """
    judging = req.playbook.get("judging_panel", {})
    
    # Safety gate: never send unless explicitly approved
    if judging.get("overall_recommendation") != "APPROVE":
        return {
            "status": "rejected",
            "reason": "Judging Panel did not recommend APPROVE",
            "panel_state": judging.get("state")
        }
    
    if judging.get("state") != "PENDING_APPROVAL":
        return {
            "status": "rejected",
            "reason": f"Panel state is {judging.get('state')}, not PENDING_APPROVAL",
        }
    
    # Send it
    try:
        result = send_public_advisory(req.advisory_text, req.recipients)
        return {
            "status": "dispatched",
            "sms_results": result["sms_results"],
            "message": "Advisory sent to all recipients",
            "note": "This is a real dispatch. Keep a pre-recorded fallback video ready in case Twilio times out."
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "note": "Use fallback video / manual SMS if this fails"
        }