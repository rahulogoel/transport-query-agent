 # LTA API calls (get_bus_arrivals)# app/tools.py
from typing import Optional, Dict, Any
from datetime import datetime, timezone

import requests

from .config import LTA_ACCOUNT_KEY

BUS_ARRIVAL_URL = "https://datamall2.mytransport.sg/ltaodataservice/v3/BusArrival"
TRAFFIC_INCIDENTS_URL = "https://datamall2.mytransport.sg/ltaodataservice/TrafficIncidents"
BUS_SERVICES_URL = "https://datamall2.mytransport.sg/ltaodataservice/BusServices"


def get_bus_arrivals(
    bus_stop_code: str,
    bus_service: Optional[str] = None
) -> Dict[str, Any]:
    headers = {
        "AccountKey": LTA_ACCOUNT_KEY,
        "accept": "application/json"
    }
    params = {
        "BusStopCode": bus_stop_code
    }

    response = requests.get(BUS_ARRIVAL_URL, headers=headers, params=params, timeout=10)

    if response.status_code != 200:
        raise RuntimeError(
            f"BusArrival API call failed with status {response.status_code}: {response.text[:200]}"
        )

    data = response.json()
    services = data.get("Services", [])

    if bus_service:
        services = [s for s in services if s.get("ServiceNo") == bus_service]

    parsed_services = []

    now_utc = datetime.now(timezone.utc)

    for svc in services:
        service_no = svc.get("ServiceNo")
        arrivals = []
        for key in ["NextBus", "NextBus2", "NextBus3"]:
            bus_info = svc.get(key, {})
            est_arrival = bus_info.get("EstimatedArrival")
            if not est_arrival:
                continue

            try:
                eta_dt = datetime.fromisoformat(est_arrival.replace("Z", "+00:00"))
                wait_minutes = int((eta_dt - now_utc).total_seconds() // 60)
            except Exception:
                wait_minutes = None

            arrivals.append({
                "eta_iso": est_arrival,
                "est_wait_minutes": wait_minutes
            })

        parsed_services.append({
            "service_no": service_no,
            "next_arrivals": arrivals
        })

    return {
        "bus_stop_code": bus_stop_code,
        "services": parsed_services,
        "raw": data
    }

def get_traffic_incidents() -> Dict[str, Any]:
    """
    Call the LTA TrafficIncidents API and return all current incidents.
    """
    headers = {
        "AccountKey": LTA_ACCOUNT_KEY,
        "accept": "application/json"
    }

    resp = requests.get(TRAFFIC_INCIDENTS_URL, headers=headers, timeout=10)

    if resp.status_code != 200:
        raise RuntimeError(
            f"TrafficIncidents API call failed with status {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json()
    # LTA typically returns an "value" array for many endpoints; adjust if needed for TrafficIncidents
    incidents = data.get("value") or data.get("incidents") or []

    return {
        "raw": data,
        "incidents": incidents,
    }
    
def get_bus_services(service_no: Optional[str] = None) -> Dict[str, Any]:
    """
    Call the LTA BusServices API.
    If service_no is provided, filter to that service.
    """
    headers = {
        "AccountKey": LTA_ACCOUNT_KEY,
        "accept": "application/json"
    }

    resp = requests.get(BUS_SERVICES_URL, headers=headers, timeout=10)

    if resp.status_code != 200:
        raise RuntimeError(
            f"BusServices API call failed with status {resp.status_code}: {resp.text[:200]}"
        )

    data = resp.json()
    services = data.get("value") or data.get("Services") or []

    if service_no:
        services = [s for s in services if s.get("ServiceNo") == service_no]

    return {
        "raw": data,
        "services": services,
    }