# AgentState definition
# app/state.py
from typing import TypedDict, Optional, Dict, Any

class AgentState(TypedDict):
    user_query: str

    intent: str
    bus_stop_code: Optional[str]
    bus_service: Optional[str]
    needs_api_call: bool

    traffic_filter: Optional[str]  # e.g. road name / expressway, optional
    
    api_raw_response: Optional[Dict[str, Any]]
    api_parsed_summary: Optional[str]

    final_answer: Optional[str]