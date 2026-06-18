# BlockBuster Backend

Plain FastAPI port of the validated Colab logic: Layer 1 prediction, Layer 2
simulation (BPR flow + critical-route stress test), Layer 3 routing
(Proposer/Adversary + travel-time officer ETA), and the Judging Panel
checklist. Every function here is a 1:1 port of what was already validated
against real output in the notebook \u2014 no new logic was introduced.

Not yet included (next steps): LLM Playbook Renderer, Public Advisory
Generator, websocket/SSE log streaming, Twilio SMS dispatch. Those come next.

## Setup

```bash
cd blockbuster-backend
python3 -m venv venv
source venv/bin/activate          # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

## Run locally

```bash
uvicorn app.main:app --reload --port 8000
```

Visit http://localhost:8000/docs for the interactive Swagger UI \u2014 every
endpoint below can be tested directly from the browser there.

## Endpoints

- `GET /health` \u2014 sanity check, returns corridor count
- `GET /corridors` \u2014 list all 21 corridor names
- `POST /forecast` \u2014 Layer 1 risk score for a corridor + timestamp
- `POST /simulate` \u2014 inject a disaster, get the resulting network state
- `POST /stress-test` \u2014 same as simulate, but also runs the critical-route
  protection check and re-solves if Bannerghata Road / CBD 1 are at risk
- `POST /route` \u2014 Proposer/Adversary diversion route with travel-time ETA
- `POST /playbook` \u2014 the full pipeline in one call: stress test, route,
  officer ETA, and the Judging Panel's Pending Approval checklist

## Example: full playbook request

```bash
curl -X POST http://localhost:8000/playbook \
  -H "Content-Type: application/json" \
  -d '{
    "blocked_corridors": ["Mysore Road", "Bellary Road 1"],
    "hour": 18,
    "origin": "Tumkur Road",
    "destination": "Old Madras Road"
  }'
```

Expect a JSON response containing `network_state` (21 corridors with V/C and
color), `stress_test` (PASSED / PASSED_AFTER_REROUTE / FAILED_PROTECTED_ROUTE),
`diversion` (the chosen route + ETA in minutes), `nearest_officers`, and
`judging_panel` (the Pending Approval checklist with APPROVE / REVIEW_REQUIRED).

## Example: forecast request

```bash
curl -X POST http://localhost:8000/forecast \
  -H "Content-Type: application/json" \
  -d '{"corridor": "Mysore Road", "timestamp": "2026-07-04T09:00:00Z"}'
```

## Data files

`data/blockbuster_export_final.json`, `data/blockbuster_panel.json`, and
`data/blockbuster_model.json` are loaded once at startup by
`app/data_loader.py`. If you regenerate any of these from the notebook,
just drop the new files in here with the same names and restart the server.
