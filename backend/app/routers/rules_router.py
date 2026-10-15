from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from ..auth import current_user
from ..database import get_db
from ..models import DetectionRule, User
from ..schemas import RuleOut

router = APIRouter(prefix="/api/rules", tags=["Detection Rules"])

@router.get("", response_model=list[RuleOut])
def rules(db: Session = Depends(get_db), user: User = Depends(current_user)):
    return db.query(DetectionRule).order_by(DetectionRule.id).all()
