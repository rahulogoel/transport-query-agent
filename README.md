# LangGraph-Based Singapore Transport Query Agent

This project implements an **agentic workflow using LangGraph** that answers real-time user queries about **Singapore public transport** using the **LTA DataMall APIs**. The goal of this project is to demonstrate structured agent design, tool usage, state management, and multi-user simulation.

This project is developed to showcase:

- Agent workflow design  
- API integration  
- Multi-step orchestration using LangGraph  
- Multi-user simulation and response handling  

The application is exposed as a **FastAPI service** with **Swagger UI** for interactive testing.

 ---

##  Supported Capabilities

-  **Bus Arrivals** – Real-time ETA for buses at any stop  
-  **Bus Service Information** – Route and peak/off-peak frequency  
-  **Traffic Incidents** – Live accidents, breakdowns, road blocks, diversions  

---

## Architecture

```

User Query
↓
Planner Node (LLM)
↓
Intent + Parameter Extraction
↓
LangGraph Router
├── BusArrival Node → LTA BusArrival API
├── BusService Node → LTA BusServices API
└── TrafficIncident Node → LTA TrafficIncidents API
↓
Responder Node (LLM)
↓
Final Natural Language Answer

```

---

##  Project Structure

```

assignment/
├── app/
│   ├── api.py        # FastAPI routes
│   ├── graph.py      # LangGraph workflow
│   ├── tools.py      # LTA API calls
│   ├── state.py      # Agent state schema
│   └── config.py     # Environment + Groq config
│
├── notebooks/
│   └── transport_agent.ipynb   # Multi-user simulation
│
├── requirements.txt
├── .env
└── README.md

````

---

## Tech Stack

- Python 3.11+
- LangGraph
- LangChain + Groq (LLaMA 3 – 70B)
- FastAPI
- Uvicorn
- Singapore LTA DataMall APIs

---

## Environment Variables

Create a `.env` file in the project root:

```env
GROQ_API_KEY=your_groq_api_key
LTA_ACCOUNT_KEY=your_lta_datamall_key
````

---

## Installation & Run

```bash
python -m venv henv
source henv/bin/activate
pip install -r requirements.txt
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

---

## API Access

* **Base URL:**
  `http://localhost:8000`

* **Swagger UI (Primary Test Interface):**
  `http://localhost:8000/docs`

---

## Main Endpoint

### `POST /query`

#### Request

```json
{
  "query": "When is the next bus arriving at stop 20251?"
}
```

#### Response

```json
{
  "query": "...",
  "answer": "...",
  "intent": "bus_arrival",
  "bus_stop_code": "20251",
  "bus_service": null
}
```

---

# Example Queries

## Bus Arrivals (5 Examples)

1. `When is the next bus arriving at stop 20251?`
2. `Is bus 30 arriving soon at stop 45009?`
3. `Show me upcoming buses at stop 97029.`
4. `How long will I wait for bus 176 at stop 20251?`
5. `Are there any buses approaching stop 84009 right now?`

---

## Bus Service Information (5 Examples)

1. `Tell me about bus 176.`
2. `How often does bus 30 run?`
3. `What is the peak frequency of bus 78?`
4. `Give me details of bus service 97.`
5. `What route does bus 15 operate on?`

---

## Traffic Incidents (5 Examples)

1. `Any accidents on the PIE right now?`
2. `Are there any road blocks on AYE?`
3. `Show me current traffic incidents in Singapore.`
4. `Is there a vehicle breakdown on CTE?`
5. `What diversions are active right now?`

---

## Multi-User Simulation

The Jupyter notebook `notebooks/transport_agent.ipynb` contains:

* 10 simulated user queries
* Dynamic agent routing
* Real-time API responses
* Captured outputs for evaluation

---

## Deployment

The FastAPI backend is deployed on Render with:

* Public REST access
* Swagger UI enabled
* Secure environment variables

---

## Summary

This project demonstrates:

* Agentic AI orchestration using LangGraph
* Real-time government transport API integration
* LLM-powered intent extraction and reasoning
* Production-grade FastAPI backend deployment
