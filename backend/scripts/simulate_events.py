import argparse
import random
import time
import requests

parser = argparse.ArgumentParser()
parser.add_argument("--count", type=int, default=30)
parser.add_argument("--delay", type=float, default=1)
parser.add_argument("--url", default="http://localhost:8000")
parser.add_argument("--token", default="")
args = parser.parse_args()

token = args.token
if not token:
    login = requests.post(
        f"{args.url}/api/auth/login",
        json={"username": "admin", "password": "Admin@12345"},
        timeout=10,
    )
    login.raise_for_status()
    token = login.json()["access_token"]

headers = {"Authorization": f"Bearer {token}"}

normal = [
    {
        "source": "windows",
        "event_type": "authentication",
        "severity": "low",
        "source_ip": "192.168.1.50",
        "username": "student",
        "hostname": "LAB-PC",
        "message": "Successful user authentication",
    },
    {
        "source": "linux",
        "event_type": "process",
        "severity": "low",
        "source_ip": "192.168.1.51",
        "username": "analyst",
        "hostname": "SOC-LAB",
        "message": "Process started: nginx",
    },
]

suspicious = [
    {
        "source": "windows",
        "event_type": "process",
        "severity": "high",
        "source_ip": "203.0.113.44",
        "username": "student",
        "hostname": "LAB-PC",
        "message": "powershell.exe -EncodedCommand suspicious_script",
    },
    {
        "source": "web",
        "event_type": "http",
        "severity": "high",
        "source_ip": "198.51.100.77",
        "username": "anonymous",
        "hostname": "WEB-LAB",
        "message": "GET /search?q=' UNION SELECT password FROM users --",
    },
    {
        "source": "firewall",
        "event_type": "network",
        "severity": "medium",
        "source_ip": "203.0.113.99",
        "destination_ip": "192.168.1.10",
        "hostname": "FW-LAB",
        "message": "Port scan detected across multiple destination ports",
    },
]

for i in range(args.count):
    if i % 7 == 0:
        event = random.choice(suspicious).copy()
    else:
        event = random.choice(normal).copy()

    if "Failed" in event["message"]:
        event["source_ip"] = f"203.0.113.{random.randint(10,20)}"

    response = requests.post(
        f"{args.url}/api/events/ingest",
        json=event,
        headers=headers,
        timeout=10,
    )
    response.raise_for_status()
    result = response.json()
    print(f"#{i+1}: event_id={result['id']} {event['event_type']} {event['message'][:60]}")
    time.sleep(args.delay)
