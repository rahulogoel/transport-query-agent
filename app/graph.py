# app/graph.py
# LangGraph nodes + build_app + run_agent_query

import json
from typing import Optional

from langgraph.graph import StateGraph, END

from .state import AgentState
from .config import llm
from .tools import (
    get_bus_arrivals,
    get_bus_services,
    get_traffic_incidents,
)


def planner_node(state: AgentState) -> AgentState:
    user_query = state["user_query"]

    prompt = f"""
You are an intent classification and parameter extraction assistant for a Singapore public transport agent.

The user can ask about:
- BUS ARRIVALS at a bus stop
- BUS SERVICE INFO (route/frequency details for a service number)
- TRAFFIC INCIDENTS (accidents, breakdowns, jams, diversions)
- or general chit-chat.

Your job:
1. Choose ONE intent from:
   - "bus_arrival"
   - "bus_service_info"
   - "traffic_incidents"
   - "chit_chat"
2. Extract parameters:
   - bus_stop_code: numeric string like "20251" (only for bus_arrival)
   - bus_service: service number like "176", "30" (for bus_arrival or bus_service_info)
   - traffic_filter: OPTIONAL string (road/expressway/area) to filter incidents, or null

Decide if we need to call an API:
- "bus_arrival" → true
- "bus_service_info" → true
- "traffic_incidents" → true
- "chit_chat" → false

Respond ONLY with STRICT JSON in this format:

{{
  "intent": "<bus_arrival|bus_service_info|traffic_incidents|chit_chat>",
  "bus_stop_code": "<string or null>",
  "bus_service": "<string or null>",
  "traffic_filter": "<string or null>",
  "needs_api_call": <true or false>
}}

Examples:

User: "When is the next bus arriving at stop 20251?"
→ {{
  "intent": "bus_arrival",
  "bus_stop_code": "20251",
  "bus_service": null,
  "traffic_filter": null,
  "needs_api_call": true
}}

User: "How often does bus 176 run?"
→ {{
  "intent": "bus_service_info",
  "bus_stop_code": null,
  "bus_service": "176",
  "traffic_filter": null,
  "needs_api_call": true
}}

User: "Any accidents on the PIE right now?"
→ {{
  "intent": "traffic_incidents",
  "bus_stop_code": null,
  "bus_service": null,
  "traffic_filter": "PIE",
  "needs_api_call": true
}}

User: "Hi, thanks for your help!"
→ {{
  "intent": "chit_chat",
  "bus_stop_code": null,
  "bus_service": null,
  "traffic_filter": null,
  "needs_api_call": false
}}

User query: "{user_query}"
"""

    response = llm.invoke(prompt)

    try:
        parsed = json.loads(response.content)
    except json.JSONDecodeError:
        parsed = {
            "intent": "chit_chat",
            "bus_stop_code": None,
            "bus_service": None,
            "traffic_filter": None,
            "needs_api_call": False,
        }

    state["intent"] = parsed.get("intent", "chit_chat")
    state["bus_stop_code"] = parsed.get("bus_stop_code")
    state["bus_service"] = parsed.get("bus_service")
    state["traffic_filter"] = parsed.get("traffic_filter")
    state["needs_api_call"] = bool(parsed.get("needs_api_call", False))

    return state


# ---------------------------
# Bus arrivals node (existing)
# ---------------------------
def call_lta_node(state: AgentState) -> AgentState:
    """
    Node for bus arrivals (BusArrivalv2).
    """
    bus_stop_code = state.get("bus_stop_code")
    bus_service: Optional[str] = state.get("bus_service")

    if not bus_stop_code:
        state["api_raw_response"] = None
        state["api_parsed_summary"] = (
            "No bus stop code was provided, so the LTA BusArrival API could not be called."
        )
        return state

    try:
        result = get_bus_arrivals(bus_stop_code, bus_service)
        state["api_raw_response"] = result

        services = result.get("services", [])

        if not services:
            base_msg = (
                f"The LTA BusArrival API returned no upcoming services for bus stop {bus_stop_code}."
            )
            if bus_service:
                base_msg += f" This includes service {bus_service}."
            base_msg += (
                " This may mean the stop code is invalid, the stop is inactive, "
                "this service does not operate here, or there are currently no buses in the near future."
            )
            state["api_parsed_summary"] = base_msg
            return state

        lines = [f"Bus arrivals for stop {bus_stop_code}:"]
        for svc in services:
            s_no = svc.get("service_no")
            arrivals = svc.get("next_arrivals", [])
            if not arrivals:
                lines.append(f"  - Service {s_no}: no estimated arrivals.")
                continue

            eta_descriptions = []
            for arr in arrivals:
                mins = arr.get("est_wait_minutes")
                if mins is None:
                    eta_descriptions.append("ETA unknown")
                elif mins <= 0:
                    eta_descriptions.append("arriving now")
                else:
                    eta_descriptions.append(f"in {mins} minutes")

            joined_eta = ", ".join(eta_descriptions)
            lines.append(f"  - Service {s_no}: {joined_eta}")

        state["api_parsed_summary"] = "\n".join(lines)

    except Exception as e:
        state["api_raw_response"] = None
        state["api_parsed_summary"] = f"Error while calling LTA BusArrival API: {e}"

    return state


# ---------------------------
# Bus service info node (BusServices)
# ---------------------------
def call_bus_services_node(state: AgentState) -> AgentState:
    """
    Node to query bus service information (route, frequency, etc.) via BusServices API.
    """
    service_no = state.get("bus_service")

    try:
        result = get_bus_services(service_no)
        state["api_raw_response"] = result

        services = result.get("services", [])
        if not services:
            msg = "No bus service information was found."
            if service_no:
                msg = f"No information found for bus service {service_no}."
            state["api_parsed_summary"] = msg
            return state

        lines = []
        for svc in services[:5]:  # limit summary
            s_no = svc.get("ServiceNo")
            origin = svc.get("OriginCode")
            dest = svc.get("DestinationCode")
            cat = svc.get("Category")
            am_peak = svc.get("AM_Peak_Freq")
            am_off = svc.get("AM_Offpeak_Freq")
            pm_peak = svc.get("PM_Peak_Freq")
            pm_off = svc.get("PM_Offpeak_Freq")

            lines.append(
                f"Service {s_no} (Category: {cat}) goes from {origin} to {dest}. "
                f"Frequency (minutes): AM peak {am_peak}, AM off-peak {am_off}, "
                f"PM peak {pm_peak}, PM off-peak {pm_off}."
            )

        state["api_parsed_summary"] = "\n".join(lines)

    except Exception as e:
        state["api_raw_response"] = None
        state["api_parsed_summary"] = f"Error while calling BusServices API: {e}"

    return state


# ---------------------------
# Traffic incidents node
# ---------------------------
def call_traffic_incidents_node(state: AgentState) -> AgentState:
    """
    Node to query current traffic incidents (accidents, breakdowns, etc.).
    """
    filter_text = (state.get("traffic_filter") or "").lower().strip()

    try:
        result = get_traffic_incidents()
        state["api_raw_response"] = result

        incidents = result.get("incidents", [])
        if not incidents:
            state["api_parsed_summary"] = "There are currently no reported traffic incidents."
            return state

        # Optional filtering by road/area/message
        if filter_text:
            incidents = [
                inc
                for inc in incidents
                if filter_text in str(inc.get("RoadName", "")).lower()
                or filter_text in str(inc.get("Message", "")).lower()
            ]

        if not incidents:
            state["api_parsed_summary"] = (
                f"There are no reported traffic incidents matching '{filter_text}'."
            )
            return state

        lines = ["Current traffic incidents:"]

        for inc in incidents[:10]:  # avoid huge output
            msg = inc.get("Message") or ""
            road = inc.get("RoadName") or ""
            type_ = inc.get("Type") or ""
            lines.append(f"- [{type_}] on {road}: {msg}")

        state["api_parsed_summary"] = "\n".join(lines)

    except Exception as e:
        state["api_raw_response"] = None
        state["api_parsed_summary"] = f"Error while calling TrafficIncidents API: {e}"

    return state


# ---------------------------
# Responder node
# ---------------------------
def responder_node(state: AgentState) -> AgentState:
    intent = state.get("intent", "chit_chat")
    user_query = state["user_query"]
    api_summary = state.get("api_parsed_summary")

    if intent == "chit_chat" or not state.get("needs_api_call", False):
        prompt = f"""
You are a friendly Singapore public transport assistant.

The user asked: "{user_query}"

Their query does NOT require calling live transport APIs (it's probably a greeting
or a general question). Reply briefly and helpfully in 1–3 sentences.
"""
        response = llm.invoke(prompt)
        state["final_answer"] = response.content
        return state

    prompt = f"""
You are a Singapore public transport assistant.

The user asked:
"{user_query}"

Here is structured information from one or more transport APIs:

{api_summary}

Using ONLY this information:
- Answer the user's question clearly.
- Be concise (2–4 sentences).
- Refer to bus stops, services, or roads when relevant.
"""

    response = llm.invoke(prompt)
    state["final_answer"] = response.content
    return state


# ---------------------------
# Build graph
# ---------------------------
def build_app():
    graph = StateGraph(AgentState)

    graph.add_node("planner", planner_node)
    graph.add_node("call_lta", call_lta_node)                     # bus arrivals
    graph.add_node("bus_services", call_bus_services_node)        # bus service info
    graph.add_node("traffic_incidents", call_traffic_incidents_node)  # incidents
    graph.add_node("responder", responder_node)

    graph.set_entry_point("planner")

    def route_after_planner(state: AgentState) -> str:
        intent = state.get("intent", "chit_chat")
        if intent == "bus_arrival":
            return "call_lta"
        elif intent == "bus_service_info":
            return "bus_services"
        elif intent == "traffic_incidents":
            return "traffic_incidents"
        else:
            return "responder"

    graph.add_conditional_edges(
        "planner",
        route_after_planner,
        {
            "call_lta": "call_lta",
            "bus_services": "bus_services",
            "traffic_incidents": "traffic_incidents",
            "responder": "responder",
        },
    )

    graph.add_edge("call_lta", "responder")
    graph.add_edge("bus_services", "responder")
    graph.add_edge("traffic_incidents", "responder")
    graph.add_edge("responder", END)

    return graph.compile()


agent_app = build_app()


def run_agent_query(user_query: str) -> AgentState:
    state: AgentState = {
        "user_query": user_query,
        "intent": "",
        "bus_stop_code": None,
        "bus_service": None,
        "needs_api_call": False,
        "traffic_filter": None,
        "api_raw_response": None,
        "api_parsed_summary": None,
        "final_answer": None,
    }

    final_state: AgentState | None = None
    for s in agent_app.stream(state, stream_mode="values"):
        final_state = s

    if final_state is None:
        raise RuntimeError("Agent did not produce any state")

    return final_state