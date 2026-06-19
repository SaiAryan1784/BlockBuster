# BlockBuster Backend

AI-assisted traffic disaster response backend for the Bengaluru Traffic Police, built for the MapMyIndia x ASTraM hackathon. A 3-layer "Honest AI" system — deterministic prediction, simulation, and routing logic, with an LLM layer used **only** to render the already-computed JSON into plain English. The LLM never makes a decision.

**Live deployment:** `https://blockbuster-615636980270.europe-west1.run.app`
**Interactive docs:** append `/docs` to the URL above, or to `http://localhost:8000` when running locally.

---

## Architecture

- **Layer 1 — Prediction:** XGBoost model forecasting disruption risk per corridor/timestamp (validated AUC-ROC 0.8112, PR-AUC 0.4095 — ~2.7x lift over random baseline).
- **Layer 2 — Simulation:** Deterministic BPR-based flow engine. Injects a disaster (blocked corridors), redistributes spillover demand across the network, computes live V/C ratios.
- **Layer 3 — Prescription:** Deterministic Proposer/Adversary routing (negotiates a diversion route, transparently rejecting/accepting candidate paths), officer ETA by real travel time, and a Judging Panel checklist (Safety/Feasibility/Clarity).
- **Layer 3.5 — Rendering only:** Groq/Llama turns the finished JSON into a plain-English watch-commander briefing and a 160-character public advisory draft. Zero decision-making happens here — it only describes numbers that already exist.
- **Dispatch:** Twilio SMS, gated server-side behind Judging Panel approval (`APPROVE` + `PENDING_APPROVAL`) — never fires automatically.

---

## Tech Stack

- FastAPI, Pydantic, Uvicorn
- Pandas, NetworkX, XGBoost, scikit-learn
- Groq (LLM rendering), Twilio (SMS dispatch)
- Deployed on Google Cloud Run

---

## Project Structure

```text
blockbuster-backend/
│
├── app/
│   ├── main.py                 - all REST endpoints
│   ├── data_loader.py          - loads the 3 data exports + model at startup
│   ├── forecasting.py          - Layer 1: predict_disruption_risk()
│   ├── simulation.py           - Layer 2: inject_disaster, BPR engine, stress_test_plan
│   ├── routing.py              - Layer 3: find_safe_route, officer ETA, haversine
│   ├── judging.py              - Judging Panel checklist
│   ├── llm.py                  - Groq-backed playbook narrative + advisory draft
│   ├── sms.py                  - Twilio dispatch, gated by Judging Panel approval
│   ├── utils.py                - sanitize_floats() (inf/NaN -> JSON null)
│   ├── schemas.py              - Pydantic request models
│   ├── stations.py             - police station locations (map data)
│   ├── corridor_geo.py         - corridor centroids + adjacency graph (map data)
│   ├── officers.py             - officer roster aggregation (Marshals)
│   ├── officer_deployment.py   - in-memory deploy/release tracking
│   ├── incidents.py            - in-memory incident store (create/list/deploy/resolve)
│   ├── scheduled_events.py     - in-memory planned events (Roadwork / Pre-Event Calendar / alerts)
│   ├── network_status.py       - baseline (no-disaster) network state
│   ├── signals_overview.py     - city-wide signal-override recommendations
│   ├── signals.py              - deterministic signal-override formula
│   ├── barricades.py           - deterministic barricade recommendations
│   └── analytics.py            - historical panel stats + locked model metrics
│
├── data/
│   ├── blockbuster_export_final.json   - corridors, graph, stations, officer roster, etc.
│   ├── blockbuster_panel.json          - historical incident panel (25,557 rows)
│   └── blockbuster_model.json          - trained XGBoost model (native format)
│
├── requirements.txt
├── Dockerfile
└── README.md
```

---

## Setup

```bash
git clone https://github.com/Khushicodes15/BlockBuster
cd blockbuster-backend

python -m venv venv

# Windows
venv\Scripts\Activate.ps1
# Linux/macOS
source venv/bin/activate

pip install -r requirements.txt
```

Create a `.env` file in the project root (same level as `app/`, never committed):
GROQ_API=your_groq_key

TWILIO_ACCOUNT_SID=your_twilio_sid

TWILIO_AUTH_TOKEN=your_twilio_auth_token

TWILIO_TRIAL_NUMBER=your_twilio_number

## Run Locally
```bash
uvicorn app.main:app --reload --port 8000
```
Docs at `http://localhost:8000/docs`.

## Deploy (Cloud Run)
```bash
gcloud run deploy blockbuster-api \
  --source . \
  --region asia-south1 \
  --platform managed \
  --allow-unauthenticated \
  --port 8080 \
  --memory 1Gi \
  --set-secrets="GROQ_API=GROQ_API:latest,TWILIO_ACCOUNT_SID=TWILIO_ACCOUNT_SID:latest,TWILIO_AUTH_TOKEN=TWILIO_AUTH_TOKEN:latest,TWILIO_TRIAL_NUMBER=TWILIO_TRIAL_NUMBER:latest"
```
No auto-deploy on push is configured — redeploy manually after every merge that should go live.

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/health` | Health check, corridor count |
| GET | `/corridors` | List all 21 corridors |
| POST | `/forecast` | Layer 1 risk prediction |
| GET | `/network-status?hour=` | Baseline (no-disaster) network state |
| POST | `/simulate` | Disaster simulation, no routing |
| POST | `/stress-test` | Simulation + protected-route check/reroute |
| POST | `/route` | Diversion route + negotiation log |
| POST | `/playbook` | Full pipeline: stress test → route → officers → checklist |
| POST | `/playbook-stream` | Same pipeline, streamed live via SSE |
| POST | `/render-playbook` | LLM: playbook JSON → plain-English briefing |
| POST | `/advisory` | LLM: playbook JSON → 160-char public advisory draft |
| POST | `/sms-dispatch` | Twilio SMS, gated behind Judging Panel approval |
| GET | `/corridor-centroids` | Corridor lat/lon for map markers |
| GET | `/corridor-graph` | Corridor adjacency edges for map connector lines |
| GET | `/stations` | Police station lat/lon |
| GET | `/junctions` | Named junctions + historical frequency (no coordinates) |
| GET | `/nearest-corridor?lat=&lon=` | Nearest corridor to a coordinate |
| GET | `/officers/summary` | City-wide + per-station officer availability |
| POST | `/barricades` | Deterministic barricade placement recommendations |
| POST | `/signal-override` | Signal-timing recommendations for one incident |
| GET | `/signals/overview?hour=` | Same, city-wide, baseline conditions |
| POST | `/incidents` | Create an incident |
| GET | `/incidents?status=` | List incidents (optionally filter; `RESOLVED` = reports) |
| GET | `/incidents/{id}` | Get one incident |
| PATCH | `/incidents/{id}` | Update an incident |
| POST | `/incidents/{id}/deploy` | Mark specific officers deployed to an incident |
| POST | `/incidents/{id}/resolve` | Resolve incident, release its officers |
| DELETE | `/incidents/{id}` | Delete incident, release its officers |
| POST | `/scheduled-events` | Create a planned event (roadwork / VIP movement / other) |
| GET | `/scheduled-events?upcoming_only=` | List planned events |
| GET | `/scheduled-events/{id}` | Get one planned event |
| PATCH | `/scheduled-events/{id}` | Update a planned event |
| DELETE | `/scheduled-events/{id}` | Delete a planned event |
| GET | `/scheduled-events/{id}/impact?hour=` | Simulated impact preview for a planned event |
| GET | `/analytics/summary` | Locked model metrics + corridors ranked by historical frequency |
| GET | `/analytics/corridor/{corridor}/history` | Historical time series for one corridor |

---

## Example: Full Playbook
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
Returns network state, stress-test result, diversion route + negotiation log, nearest officers, and the Judging Panel checklist.

## Example: Forecast
```bash
curl -X POST http://localhost:8000/forecast \
  -H "Content-Type: application/json" \
  -d '{ "corridor": "Mysore Road", "timestamp": "2026-07-04T09:00:00Z" }'
```

---

## Known Limitations

- **No junction coordinates.** `/junctions` has names and historical frequency only — Mappls' Place Details API doesn't return coordinates on this account tier. Manual lookup needed for literal map pins.
- **No generic address search.** Mappls' Search/Geocode APIs only return an internal `eLoc`, never usable lat/lng, on this account. Frontend search should filter client-side over `/corridors`, `/stations`, `/junctions` instead of calling a live geocoder.
- **No Mappls Map Web SDK access.** The current Mappls key has zero SDK allocations (REST APIs only). Map rendering should use a different library (e.g. Leaflet) with this backend's data.
- **"Response Units"** (distinct from Marshals/officers) is not yet defined or backed by any data.
- **All in-memory stores** (Incidents, Scheduled Events, officer deployment status) reset on cold start / restart — fine for a single demo session, not for long-term persistence.

---

## Data Files
Loaded once at startup from `data/`. To update: replace the file contents, keep filenames unchanged, restart the server.

---

## Roadmap

### Completed
- Risk forecasting, traffic simulation, protected-route stress testing, intelligent routing, officer ETA
- Judging Panel checklist
- LLM playbook renderer + public advisory generator (Groq)
- Live SSE log streaming
- Twilio SMS dispatch, gated behind approval
- Cloud Run deployment
- Marshals/officer deployment tracking, Incidents (with Reports filter), Scheduled Events (Roadwork/Calendar/alerts), Analytics, Signals overview, map support data (centroids/graph/stations)

### Remaining
- Frontend dashboard (handed off to the frontend team)
- Manual junction coordinate lookup, if literal map pins are wanted
- Definition + backing data for "Response Units"
- Optional: Mappls support follow-up for Map SDK access; Cloud Build trigger for auto-deploy on push

---

## Vision
BlockBuster combines prediction, traffic simulation, emergency routing, and operational decision support — with full transparency at every step — to help Bengaluru Traffic Police respond faster and more accountably during urban disruptions.