from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class EventIn(BaseModel):
    source: str = Field(min_length=1, max_length=80)
    event_type: str = Field(min_length=1, max_length=80)
    severity: str = "low"
    source_ip: str | None = None
    destination_ip: str | None = None
    username: str | None = None
    hostname: str | None = None
    message: str = Field(min_length=1)
    raw_log: str | None = None
    timestamp: datetime | None = None


class EventOut(EventIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    timestamp: datetime


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    event_id: int | None
    rule_id: str
    title: str
    severity: str
    status: str
    description: str
    created_at: datetime
    acknowledged_at: datetime | None


class IncidentIn(BaseModel):
    title: str = Field(min_length=1, max_length=220)
    severity: str = "medium"
    description: str = Field(min_length=1)
    priority: str = "medium"
    assigned_to: str | None = None
    due_date: datetime | None = None


class IncidentUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=220)
    severity: str | None = None
    priority: str | None = None
    assigned_to: str | None = None
    due_date: datetime | None = None
    description: str | None = None
    resolution: str | None = None


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    severity: str
    status: str
    description: str
    priority: str = "medium"
    assigned_to: str | None = None
    due_date: datetime | None = None
    resolution: str | None = None
    closed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class NoteIn(BaseModel):
    note: str = Field(min_length=1, max_length=5000)


class NoteOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    incident_id: int
    author: str
    note: str
    created_at: datetime


class EvidenceIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    evidence_url: str = Field(min_length=1, max_length=1000)
    description: str = Field(default="", max_length=5000)


class EvidenceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    incident_id: int
    title: str
    evidence_url: str
    description: str
    added_by: str
    created_at: datetime


class ActivityOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    incident_id: int
    actor: str
    action: str
    details: str
    created_at: datetime


class RuleOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    rule_id: str
    name: str
    severity: str
    description: str
    enabled: bool
