from pathlib import Path
import re
import yaml
from sqlalchemy.orm import Session
from .models import SecurityEvent, Alert

RULE_FILE = Path(__file__).resolve().parents[2] / "detections" / "rules.yaml"

def load_rules():
    if not RULE_FILE.exists():
        return []
    data = yaml.safe_load(RULE_FILE.read_text()) or {}
    return data.get("rules", [])

def text_of(event: SecurityEvent) -> str:
    return " ".join([
        event.message or "",
        event.raw_log or "",
        event.event_type or "",
        event.source or "",
    ]).lower()

def evaluate_event(db: Session, event: SecurityEvent) -> list[Alert]:
    text = text_of(event)
    created = []

    for rule in load_rules():
        if not rule.get("enabled", True):
            continue

        matched = False
        mode = rule.get("match", {}).get("type")

        if mode == "regex":
            patterns = rule["match"].get("patterns", [])
            matched = any(re.search(p, text, re.IGNORECASE) for p in patterns)

        elif mode == "fields":
            conditions = rule["match"].get("conditions", {})
            matched = all(str(getattr(event, k, "")).lower() == str(v).lower()
                          for k, v in conditions.items())

        elif mode == "failed_login_threshold":
            if event.source_ip:
                from datetime import datetime, timedelta, timezone
                cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
                count = (
                    db.query(SecurityEvent)
                    .filter(SecurityEvent.source_ip == event.source_ip)
                    .filter(SecurityEvent.timestamp >= cutoff)
                    .filter(SecurityEvent.message.ilike("%failed%"))
                    .count()
                )
                matched = count >= int(rule["match"].get("threshold", 5))

        if matched:
            alert = Alert(
                event_id=event.id,
                rule_id=rule["id"],
                title=rule["name"],
                severity=rule["severity"],
                status="open",
                description=rule["description"],
            )
            db.add(alert)
            created.append(alert)

    if created:
        db.commit()
    return created
