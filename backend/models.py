from datetime import datetime
from typing import List, Literal

from pydantic import BaseModel

Severity = Literal["SEV1", "SEV2", "SEV3", "SEV4"]
Status = Literal["open", "acknowledged", "resolved"]
LogLevel = Literal["DEBUG", "INFO", "WARN", "ERROR"]


class LogEntry(BaseModel):
    timestamp: datetime
    level: LogLevel
    service: str
    message: str


class TimelineEvent(BaseModel):
    timestamp: datetime
    type: str
    message: str


class Incident(BaseModel):
    id: str
    title: str
    description: str
    severity: Severity
    status: Status
    services: List[str]
    created_at: datetime
    logs: List[LogEntry]
    timeline: List[TimelineEvent]


class IncidentSummary(BaseModel):
    id: str
    title: str
    severity: Severity
    status: Status
    services: List[str]
    created_at: datetime


class Suggestion(BaseModel):
    cause: str
    confidence: float
    evidence: List[str]
    action: str
