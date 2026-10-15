from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..auth import current_user
from ..database import get_db
from ..models import (
    Incident,
    IncidentNote,
    IncidentEvidence,
    IncidentActivity,
    User,
)
from ..schemas import (
    IncidentIn,
    IncidentOut,
    IncidentUpdate,
    NoteIn,
    NoteOut,
    EvidenceIn,
    EvidenceOut,
    ActivityOut,
)

router = APIRouter(prefix="/api/incidents", tags=["Incidents"])

VALID_STATUSES = {"open", "investigating", "resolved", "closed"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}
VALID_PRIORITIES = {"low", "medium", "high", "critical"}


def get_incident_or_404(db: Session, incident_id: int):
    incident = db.get(Incident, incident_id)
    if incident is None:
        raise HTTPException(status_code=404, detail="Incident not found")
    return incident


def record_activity(
    db: Session,
    incident_id: int,
    actor: str,
    action: str,
    details: str = "",
):
    db.add(
        IncidentActivity(
            incident_id=incident_id,
            actor=actor,
            action=action,
            details=details,
        )
    )


@router.get("", response_model=list[IncidentOut])
def list_incidents(
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return (
        db.query(Incident)
        .order_by(Incident.updated_at.desc())
        .limit(200)
        .all()
    )


@router.post("", response_model=IncidentOut)
def create_incident(
    payload: IncidentIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if payload.severity not in VALID_SEVERITIES:
        raise HTTPException(400, "Invalid severity")
    if payload.priority not in VALID_PRIORITIES:
        raise HTTPException(400, "Invalid priority")

    incident = Incident(
        title=payload.title,
        severity=payload.severity,
        description=payload.description,
        priority=payload.priority,
        assigned_to=payload.assigned_to,
        due_date=payload.due_date,
        status="open",
    )

    try:
        db.add(incident)
        db.flush()
        record_activity(db, incident.id, user.username, "created", "Incident created")
        db.commit()
        db.refresh(incident)
        return incident
    except Exception:
        db.rollback()
        raise


@router.get("/{incident_id}", response_model=IncidentOut)
def get_incident(
    incident_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    return get_incident_or_404(db, incident_id)


@router.patch("/{incident_id}", response_model=IncidentOut)
def update_incident(
    incident_id: int,
    payload: IncidentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    incident = get_incident_or_404(db, incident_id)
    changes = payload.model_dump(exclude_unset=True)

    for field in ("severity", "priority"):
        if field in changes and changes[field] is not None:
            allowed = VALID_SEVERITIES if field == "severity" else VALID_PRIORITIES
            if changes[field] not in allowed:
                raise HTTPException(400, f"Invalid {field}")

    for field, value in changes.items():
        setattr(incident, field, value)

    incident.updated_at = datetime.now(timezone.utc)
    record_activity(
        db,
        incident.id,
        user.username,
        "updated",
        ", ".join(changes.keys()) or "No fields changed",
    )

    db.commit()
    db.refresh(incident)
    return incident


@router.patch("/{incident_id}/status", response_model=IncidentOut)
def update_status(
    incident_id: int,
    status: str,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    if status not in VALID_STATUSES:
        raise HTTPException(
            status_code=400,
            detail="Status must be open, investigating, resolved, or closed",
        )

    incident = get_incident_or_404(db, incident_id)
    previous_status = incident.status

    if status in {"resolved", "closed"} and not (incident.resolution or "").strip():
        raise HTTPException(
            status_code=400,
            detail="Add a resolution summary before resolving or closing this incident",
        )

    incident.status = status
    incident.updated_at = datetime.now(timezone.utc)

    if status == "closed":
        incident.closed_at = datetime.now(timezone.utc)
    elif previous_status == "closed":
        incident.closed_at = None

    record_activity(
        db,
        incident.id,
        user.username,
        "status_changed",
        f"{previous_status} -> {status}",
    )

    db.commit()
    db.refresh(incident)
    return incident


@router.get("/{incident_id}/notes", response_model=list[NoteOut])
def list_notes(
    incident_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    get_incident_or_404(db, incident_id)
    return (
        db.query(IncidentNote)
        .filter(IncidentNote.incident_id == incident_id)
        .order_by(IncidentNote.created_at.desc())
        .all()
    )


@router.post("/{incident_id}/notes", response_model=NoteOut)
def add_note(
    incident_id: int,
    payload: NoteIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    incident = get_incident_or_404(db, incident_id)

    note = IncidentNote(
        incident_id=incident_id,
        author=user.username,
        note=payload.note,
    )
    db.add(note)
    incident.updated_at = datetime.now(timezone.utc)
    record_activity(db, incident_id, user.username, "note_added", payload.note[:500])

    db.commit()
    db.refresh(note)
    return note


@router.get("/{incident_id}/evidence", response_model=list[EvidenceOut])
def list_evidence(
    incident_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    get_incident_or_404(db, incident_id)
    return (
        db.query(IncidentEvidence)
        .filter(IncidentEvidence.incident_id == incident_id)
        .order_by(IncidentEvidence.created_at.desc())
        .all()
    )


@router.post("/{incident_id}/evidence", response_model=EvidenceOut)
def add_evidence(
    incident_id: int,
    payload: EvidenceIn,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    get_incident_or_404(db, incident_id)

    # Evidence is recorded as a URL/reference; the server does not fetch it.
    evidence = IncidentEvidence(
        incident_id=incident_id,
        title=payload.title,
        evidence_url=payload.evidence_url,
        description=payload.description,
        added_by=user.username,
    )
    db.add(evidence)
    record_activity(
        db,
        incident_id,
        user.username,
        "evidence_added",
        payload.title,
    )

    db.commit()
    db.refresh(evidence)
    return evidence


@router.get("/{incident_id}/activity", response_model=list[ActivityOut])
def list_activity(
    incident_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    get_incident_or_404(db, incident_id)
    return (
        db.query(IncidentActivity)
        .filter(IncidentActivity.incident_id == incident_id)
        .order_by(IncidentActivity.created_at.desc())
        .limit(500)
        .all()
    )
