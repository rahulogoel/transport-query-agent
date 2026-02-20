# app/api.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from .graph import run_agent_query

app = FastAPI(
    title="Singapore Transport Query Agent",
    description="LangGraph + Groq LLaMA3-70B based agent for LTA BusArrival queries",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str


class QueryResponse(BaseModel):
    query: str
    answer: str
    intent: Optional[str] = None
    bus_stop_code: Optional[str] = None
    bus_service: Optional[str] = None


@app.post("/query", response_model=QueryResponse)
def query_transport(req: QueryRequest):
    state = run_agent_query(req.query)

    return QueryResponse(
        query=req.query,
        answer=state.get("final_answer") or "",
        intent=state.get("intent"),
        bus_stop_code=state.get("bus_stop_code"),
        bus_service=state.get("bus_service"),
    )