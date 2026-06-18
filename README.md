BlockBuster Backend

AI-powered disaster response backend built with FastAPI, designed for real-time traffic disruption forecasting, network stress testing, and emergency route planning. The system integrates predictive analytics, traffic simulation, adversarial routing, and decision support into a single API for disaster management.

The backend is a production-ready port of the validated research notebook, preserving the original logic while exposing it through REST APIs.

---

Features

Layer 1: Risk Forecasting

- Predicts disruption risk for a given corridor and timestamp.
- Uses the validated predictive model without altering the original methodology.

Layer 2: Network Simulation

- Simulates disaster scenarios by blocking selected corridors.
- Updates traffic flow using the BPR congestion model.
- Computes Volume-to-Capacity (V/C) ratios for all corridors.

Critical Route Protection

- Automatically checks whether protected emergency corridors are affected.
- Performs rerouting when necessary to maintain network resilience.
- Returns simulation status:
  - "PASSED"
  - "PASSED_AFTER_REROUTE"
  - "FAILED_PROTECTED_ROUTE"

Layer 3: Intelligent Routing

- Generates diversion routes using a Proposer–Adversary framework.
- Estimates travel times for emergency responders.
- Identifies nearest available officers.

Decision Support

- Produces a complete operational playbook.
- Generates a Judging Panel checklist for rapid incident assessment.
- Consolidates network state, routing decisions, and approval recommendations.

---

Tech Stack

- FastAPI
- Python
- Pydantic
- NetworkX
- NumPy
- Pandas

---

Project Structure

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

---

Installation

Clone the repository and create a virtual environment:

git clone <repo-url>
cd blockbuster-backend

python3 -m venv venv

# Linux / macOS
source venv/bin/activate

# Windows
venv\Scripts\activate

pip install -r requirements.txt

---

Running the Server

Start the FastAPI application:

uvicorn app.main:app --reload --port 8000

API documentation is automatically available at:

http://localhost:8000/docs

Interactive Swagger UI allows every endpoint to be tested directly.

---

API Endpoints

Method| Endpoint| Description
GET| "/health"| Health check and corridor count
GET| "/corridors"| List all available traffic corridors
POST| "/forecast"| Generate disruption risk predictions
POST| "/simulate"| Simulate disaster impact on the network
POST| "/stress-test"| Run simulation with protected-route validation
POST| "/route"| Compute optimal diversion route and ETA
POST| "/playbook"| Execute the complete emergency response pipeline

---

Example: Full Playbook

curl -X POST http://localhost:8000/playbook \
-H "Content-Type: application/json" \
-d '{
  "blocked_corridors": [
    "Mysore Road",
    "Bellary Road 1"
  ],
  "hour": 18,
  "origin": "Tumkur Road",
  "destination": "Old Madras Road"
}'

Response includes:

- Network state
- Corridor congestion levels
- Stress test result
- Diversion route
- Estimated travel time
- Nearest emergency officers
- Decision panel recommendations

---

Example: Risk Forecast

curl -X POST http://localhost:8000/forecast \
-H "Content-Type: application/json" \
-d '{
  "corridor": "Mysore Road",
  "timestamp": "2026-07-04T09:00:00Z"
}'

---

Data Management

The backend loads model and network assets during startup:

data/blockbuster_export_final.json
data/blockbuster_panel.json
data/blockbuster_model.json

To update the system with newly generated outputs from the research notebook:

1. Replace the existing files.
2. Keep the filenames unchanged.
3. Restart the server.

No additional configuration is required.

---

Roadmap

Completed

- Risk forecasting
- Traffic simulation
- Protected-route stress testing
- Adversarial routing
- Officer ETA estimation
- Decision panel integration
- FastAPI REST endpoints

In Progress

- LLM-powered Playbook Renderer
- Public Advisory Generator
- WebSocket/SSE live event streaming
- Twilio SMS emergency notifications
- Real-time dashboard integration

---

Vision

BlockBuster aims to provide a unified AI-assisted disaster response platform capable of forecasting disruptions, protecting critical infrastructure, optimizing emergency mobility, and supporting rapid operational decision-making during urban crises.
