# BlockBuster Backend

AI-powered disaster response backend built with **FastAPI**, designed for real-time traffic disruption forecasting, network stress testing, and emergency route planning.

The backend exposes the validated research pipeline through REST APIs while preserving the original model logic.

---

## Features

### Layer 1: Risk Forecasting
- Predict disruption risk for a corridor at a given timestamp.
- Uses the validated predictive model.

### Layer 2: Network Simulation
- Simulate disaster scenarios by blocking corridors.
- Update traffic flow using the BPR congestion model.
- Compute Volume-to-Capacity (V/C) ratios across the network.

### Critical Route Protection
- Monitor protected emergency corridors.
- Automatically reroute traffic when critical routes are threatened.
- Returns:
  - `PASSED`
  - `PASSED_AFTER_REROUTE`
  - `FAILED_PROTECTED_ROUTE`

### Layer 3: Intelligent Routing
- Generate diversion routes using a Proposer-Adversary framework.
- Estimate emergency response travel times.
- Identify nearest available officers.

### Decision Support
- Generate a complete operational playbook.
- Produce a judging panel checklist for rapid decision-making.
- Combine simulation, routing, and emergency planning into a single workflow.

---

## Tech Stack

- FastAPI
- Python
- Pydantic
- NumPy
- Pandas
- NetworkX

---

## Project Structure

```text
blockbuster-backend/
│
├── app/
│   ├── main.py
│   ├── data_loader.py
│   ├── routes/
│   ├── services/
│   └── models/
│
├── data/
│   ├── blockbuster_export_final.json
│   ├── blockbuster_panel.json
│   └── blockbuster_model.json
│
├── requirements.txt
└── README.md
```

---

## Setup

```bash
git clone <repo-url>
cd blockbuster-backend

python3 -m venv venv

# Linux/macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt
```

---

## Run Locally

```bash
uvicorn app.main:app --reload --port 8000
```

Interactive API documentation:

```
http://localhost:8000/docs
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check and corridor count |
| GET | `/corridors` | List all corridors |
| POST | `/forecast` | Layer 1 risk prediction |
| POST | `/simulate` | Disaster simulation |
| POST | `/stress-test` | Simulation with protected-route checks |
| POST | `/route` | Diversion route and ETA |
| POST | `/playbook` | Complete disaster response pipeline |

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

### Response Includes

- Network state
- Corridor congestion metrics
- Stress test result
- Diversion route
- Travel-time ETA
- Nearest officers
- Judging panel recommendations

---

## Example: Forecast

```bash
curl -X POST http://localhost:8000/forecast \
  -H "Content-Type: application/json" \
  -d '{
    "corridor": "Mysore Road",
    "timestamp": "2026-07-04T09:00:00Z"
  }'
```

---

## Data Files

The backend loads these files during startup:

```
data/blockbuster_export_final.json
data/blockbuster_panel.json
data/blockbuster_model.json
```

To update the backend:
1. Replace the existing files.
2. Keep the filenames unchanged.
3. Restart the server.

---

## Roadmap

### Completed
- Risk forecasting
- Traffic simulation
- Protected-route stress testing
- Intelligent routing
- Officer ETA estimation
- Judging panel integration
- FastAPI REST APIs

### Coming Next
- LLM Playbook Renderer
- Public Advisory Generator
- WebSocket/SSE live logs
- Twilio SMS dispatch
- Real-time dashboard integration

---

## Vision

BlockBuster is an AI-assisted disaster response platform that combines prediction, traffic simulation, emergency routing, and operational decision support to help authorities respond quickly and effectively during urban crises.
