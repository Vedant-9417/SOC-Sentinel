import os
from contextlib import asynccontextmanager
from pathlib import Path

import yaml
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from .database import Base, engine, SessionLocal
from .models import User, DetectionRule
from .auth import hash_password
from .websocket import manager
from .routers import (
    auth_router,
    events_router,
    alerts_router,
    incidents_router,
    dashboard_router,
    rules_router,
    threat_router,
)


# Project root:
# soc_sentinel/
# ├── backend/
# │   └── app/
# └── detections/
#     └── rules.yaml
RULES_FILE = Path(__file__).resolve().parents[2] / "detections" / "rules.yaml"


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    seed_database()
    yield


def seed_database():
    db = SessionLocal()

    try:
        # Create default admin user if it does not exist
        if not db.query(User).filter(User.username == "admin").first():
            db.add(
                User(
                    username="admin",
                    password_hash=hash_password("Admin@12345"),
                    role="admin",
                )
            )

        # Load detection rules from the Windows project path
        if RULES_FILE.exists():
            data = yaml.safe_load(RULES_FILE.read_text(encoding="utf-8")) or {}

            for rule in data.get("rules", []):
                existing_rule = (
                    db.query(DetectionRule)
                    .filter(DetectionRule.rule_id == rule["id"])
                    .first()
                )

                if not existing_rule:
                    db.add(
                        DetectionRule(
                            rule_id=rule["id"],
                            name=rule["name"],
                            severity=rule["severity"],
                            description=rule["description"],
                            enabled=rule.get("enabled", True),
                        )
                    )

        db.commit()

    finally:
        db.close()


app = FastAPI(
    title="SOC Sentinel API",
    version="1.0.0",
    description="Real-time defensive Security Operations Center API",
    lifespan=lifespan,
)


# CORS
origins = [
    x.strip()
    for x in os.getenv(
        "CORS_ORIGINS",
        "http://localhost:5173",
    ).split(",")
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API routers
app.include_router(auth_router.router)
app.include_router(events_router.router)
app.include_router(alerts_router.router)
app.include_router(incidents_router.router)
app.include_router(dashboard_router.router)
app.include_router(rules_router.router)
app.include_router(threat_router.router)


@app.get("/health")
def health():
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))

    return {
        "status": "ok",
        "service": "soc-sentinel",
    }


@app.websocket("/ws/live")
async def live_socket(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            await websocket.receive_text()

    except WebSocketDisconnect:
        manager.disconnect(websocket)

    except Exception:
        manager.disconnect(websocket)