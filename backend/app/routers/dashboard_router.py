from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session
from ..auth import current_user
from ..database import get_db
from ..models import Alert, Incident, SecurityEvent, User

router = APIRouter(prefix="/api/dashboard", tags=["Dashboard"])

@router.get("/summary")
def summary(db: Session = Depends(get_db), user: User = Depends(current_user)):
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    event_count = db.query(SecurityEvent).filter(SecurityEvent.timestamp >= cutoff).count()
    open_alerts = db.query(Alert).filter(Alert.status == "open").count()
    critical_alerts = db.query(Alert).filter(Alert.severity == "critical", Alert.status != "closed").count()
    incidents = db.query(Incident).filter(Incident.status != "resolved").count()

    severity_rows = (
        db.query(SecurityEvent.severity, func.count(SecurityEvent.id))
        .filter(SecurityEvent.timestamp >= cutoff)
        .group_by(SecurityEvent.severity)
        .all()
    )

    return {
        "events_24h": event_count,
        "open_alerts": open_alerts,
        "critical_alerts": critical_alerts,
        "active_incidents": incidents,
        "severity": {k: v for k, v in severity_rows},
    }
