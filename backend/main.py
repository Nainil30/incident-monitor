from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException

from data import seed_incidents
from models import Incident, IncidentSummary, Suggestion, TimelineEvent
from rca import suggest_root_causes

app = FastAPI(title="Incident Monitor")

# In-memory store; reset on restart.
store = seed_incidents()

SEVERITY_ORDER = {"SEV1": 0, "SEV2": 1, "SEV3": 2, "SEV4": 3}


def reset_store():
    global store
    store.clear()
    store.update(seed_incidents())


def get_or_404(incident_id: str) -> Incident:
    incident = store.get(incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail=f"Incident {incident_id} not found")
    return incident


@app.get("/api/incidents", response_model=List[IncidentSummary])
def list_incidents(status: Optional[str] = None, severity: Optional[str] = None):
    items = [
        i for i in store.values()
        if (status is None or i.status == status) and (severity is None or i.severity == severity)
    ]
    items.sort(key=lambda i: (i.status == "resolved", SEVERITY_ORDER[i.severity], -i.created_at.timestamp()))
    return items


@app.get("/api/incidents/{incident_id}", response_model=Incident)
def get_incident(incident_id: str):
    return get_or_404(incident_id)


@app.get("/api/incidents/{incident_id}/suggestions", response_model=List[Suggestion])
def get_suggestions(incident_id: str):
    return suggest_root_causes(get_or_404(incident_id))


def _transition(incident_id: str, allowed_from: set, new_status: str, message: str) -> Incident:
    incident = get_or_404(incident_id)
    if incident.status not in allowed_from:
        raise HTTPException(status_code=409, detail=f"Cannot {new_status[:-1]} incident in status '{incident.status}'")
    incident.status = new_status
    incident.timeline.append(
        TimelineEvent(timestamp=datetime.now(timezone.utc), type=new_status, message=message)
    )
    return incident


@app.post("/api/incidents/{incident_id}/acknowledge", response_model=Incident)
def acknowledge(incident_id: str):
    return _transition(incident_id, {"open"}, "acknowledged", "Acknowledged via dashboard")


@app.post("/api/incidents/{incident_id}/resolve", response_model=Incident)
def resolve(incident_id: str):
    return _transition(incident_id, {"open", "acknowledged"}, "resolved", "Resolved via dashboard")


@app.get("/api/stats")
def stats():
    by_status = {"open": 0, "acknowledged": 0, "resolved": 0}
    by_severity = {s: 0 for s in SEVERITY_ORDER}
    for i in store.values():
        by_status[i.status] += 1
        if i.status != "resolved":
            by_severity[i.severity] += 1
    return {"by_status": by_status, "active_by_severity": by_severity}
