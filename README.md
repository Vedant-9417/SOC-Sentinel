# SOC Sentinel — Real-Time Security Operations Center

An advanced, defensive SOC (Security Operations Center) lab project for a college/project environment.

## Main features

- JWT authentication with Argon2 password hashing
- React + TypeScript dashboard
- FastAPI backend
- PostgreSQL persistent database
- Redis service for caching / future event-queue expansion
- Real-time WebSocket alert/event updates
- Security event ingestion API
- Built-in detection engine
- Detection rules for:
  - Brute-force authentication
  - Suspicious PowerShell
  - SQL injection indicators
  - Port scanning indicators
  - Malware/hash indicators
- Alert severity, acknowledgement and status workflow
- Incident management
- Analyst notes
- Search/filter security events
- Dashboard metrics
- Synthetic SOC event simulator
- Optional external IP reputation/geolocation lookup
- Docker Compose deployment
- OpenAPI/Swagger API documentation
- Health checks
- Seeded demo account and demo data

## Architecture

Browser
  |
  v
React/TypeScript + Vite
  |
  | REST + WebSocket
  v
FastAPI
  | \
  |  \--> Redis
  |
  +----> Detection Engine
  |
  +----> PostgreSQL

Optional external integration:
FastAPI --> AbuseIPDB API (only when ABUSEIPDB_API_KEY is configured)

## Default demo credentials

Username: admin
Password: Admin@12345

CHANGE THIS PASSWORD for any real deployment.

## Requirements

Recommended:
- Windows 10/11 + Docker Desktop, OR
- Ubuntu/Debian + Docker Engine + Docker Compose, OR
- macOS + Docker Desktop

You do NOT need to install Node.js or PostgreSQL locally when using Docker.

## Start

1. Copy `.env.example` to `.env`.
2. Change SECRET_KEY and POSTGRES_PASSWORD.
3. Run:

```bash
docker compose up --build
```

4. Open:
   - SOC UI: http://localhost:5173
   - API docs: http://localhost:8000/docs
   - API health: http://localhost:8000/health

5. Login with the demo account.

## Generate live demo events

From another terminal:

```bash
docker compose exec backend python scripts/simulate_events.py --count 30 --delay 1
```

You will see events, alerts and metrics update in the UI.

## Test event ingestion manually

```bash
curl -X POST http://localhost:8000/api/events/ingest \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "source":"linux-auth",
    "event_type":"authentication",
    "severity":"medium",
    "source_ip":"203.0.113.10",
    "username":"root",
    "message":"Failed password for root from 203.0.113.10"
  }'
```

Use the browser's developer tools or Swagger UI to obtain a token.

## Useful endpoints

- POST `/api/auth/login`
- GET `/api/dashboard/summary`
- GET `/api/events`
- POST `/api/events/ingest`
- GET `/api/alerts`
- POST `/api/alerts/{id}/ack`
- POST `/api/alerts/{id}/close`
- GET `/api/incidents`
- POST `/api/incidents`
- GET `/api/rules`
- GET `/api/threat-intel/ip/{ip}`
- WS `/ws/live`

## Project structure

```text
soc-sentinel/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── auth.py
│   │   ├── detection.py
│   │   ├── websocket.py
│   │   └── routers/
│   ├── scripts/
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   ├── vite.config.ts
│   └── Dockerfile
├── detections/
│   └── rules.yaml
├── docker-compose.yml
├── .env.example
└── README.md
```

## Detection engine

The engine evaluates each ingested event against rules in `detections/rules.yaml`.

A rule has:
- id
- name
- severity
- conditions
- description

The starter rules are deliberately designed for a safe lab. They detect suspicious indicators; they do not exploit anything.

## Connecting real logs

For a real lab, send normalized JSON events to:

`POST http://localhost:8000/api/events/ingest`

Example:

```json
{
  "source": "windows",
  "event_type": "process",
  "severity": "medium",
  "source_ip": "192.168.1.20",
  "username": "student",
  "hostname": "LAB-PC",
  "message": "powershell.exe -EncodedCommand ...",
  "raw_log": "original log line here"
}
```

For production-grade deployment, place a log collector such as Wazuh/Elastic/Fluent Bit in front of the SOC API and map its output into this schema.

## Important security note

This project is intended for authorized defensive security testing and education. Do not connect it to systems you do not own or administer.

The included `203.0.113.0/24` and `198.51.100.0/24` examples are documentation-only TEST-NET ranges.
