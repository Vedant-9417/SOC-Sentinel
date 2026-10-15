from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from ..auth import current_user
from ..database import get_db
from ..models import Alert, User
from ..schemas import AlertOut
from ..websocket import manager

router = APIRouter(prefix="/api/alerts", tags=["Alerts"])

@router.get("", response_model=list[AlertOut])
def alerts(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.query(Alert).order_by(Alert.created_at.desc()).limit(200).all()

@router.post("/{alert_id}/ack", response_model=AlertOut)
async def acknowledge(alert_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(alert)
    await manager.broadcast({"type": "alert_update", "alert_id": alert.id, "status": alert.status})
    return alert

@router.post("/{alert_id}/close", response_model=AlertOut)
async def close(alert_id: int, db: Session = Depends(get_db), user: User = Depends(current_user)):
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, "Alert not found")
    alert.status = "closed"
    db.commit()
    db.refresh(alert)
    await manager.broadcast({"type": "alert_update", "alert_id": alert.id, "status": alert.status})
    return alert
