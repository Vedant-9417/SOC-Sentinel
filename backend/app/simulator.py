import asyncio
import random
from datetime import datetime, timezone

import httpx

API_URL = "http://127.0.0.1:8000"

EVENT_TEMPLATES = [
    {
        "source": "Windows",
        "event_type": "4624",
        "severity": "low",
        "username": "demo_user",
        "hostname": "SOC-DEMO-PC",
        "message": "Successful user logon",
        "raw_log": "Windows Security Event 4624 - successful logon",
    },
    {
        "source": "Windows",
        "event_type": "4625",
        "severity": "medium",
        "source_ip": "192.168.1.50",
        "username": "admin",
        "hostname": "SOC-DEMO-PC",
        "message": "Failed login attempt",
        "raw_log": "Windows Security Event 4625 - failed authentication",
    },
    {
        "source": "Windows",
        "event_type": "4688",
        "severity": "high",
        "source_ip": "192.168.1.100",
        "username": "demo_user",
        "hostname": "SOC-DEMO-PC",
        "message": "Suspicious powershell encodedcommand activity detected",
        "raw_log": "Windows Security Event 4688 - simulated powershell encodedcommand",
    },
    {
        "source": "Web Application",
        "event_type": "HTTP_REQUEST",
        "severity": "high",
        "source_ip": "10.0.0.25",
        "destination_ip": "10.0.0.10",
        "username": "anonymous",
        "hostname": "WEB-DEMO",
        "message": "Possible SQL injection: union select detected",
        "raw_log": "Simulated HTTP request containing union select indicator",
    },
    {
        "source": "Network",
        "event_type": "PORT_SCAN",
        "severity": "medium",
        "source_ip": "10.0.0.77",
        "destination_ip": "10.0.0.10",
        "username": "unknown",
        "hostname": "SOC-DEMO-NET",
        "message": "Network port scan detected",
        "raw_log": "Simulated multiple destination ports activity",
    },
    {
        "source": "Endpoint Security",
        "event_type": "MALWARE_ALERT",
        "severity": "critical",
        "source_ip": "10.0.0.90",
        "username": "demo_user",
        "hostname": "SOC-DEMO-PC",
        "message": "Malware indicator detected",
        "raw_log": "Simulated known_bad_hash malware indicator",
    },
]


def create_event():
    event = random.choice(EVENT_TEMPLATES).copy()
    event["timestamp"] = datetime.now(timezone.utc).isoformat()
    return event


async def run_simulator(interval=7):
    print("======================================")
    print(" SOC Sentinel Virtual AI Simulator")
    print("======================================")
    print("Safe virtual events only.")
    print(f"Generating one event every {interval} seconds.")
    print("Press CTRL+C to stop.")
    print()

    async with httpx.AsyncClient(timeout=10) as client:

        # Login
        login_response = await client.post(
            f"{API_URL}/api/auth/login",
            json={
                "username": "admin",
                "password": "Admin@12345",
            },
        )

        if login_response.status_code != 200:
            print("Login failed.")
            print(login_response.text)
            return

        token = login_response.json()["access_token"]
        headers = {
            "Authorization": f"Bearer {token}"
        }

        print("Simulator login successful.")
        print()

        # Generate events continuously
        while True:
            event = create_event()

            response = await client.post(
                f"{API_URL}/api/events/ingest",
                json=event,
                headers=headers,
            )

            if response.status_code in (200, 201):
                result = response.json()

                print(
                    f"[{datetime.now().strftime('%H:%M:%S')}] "
                    f"Event {result['event_type']} | "
                    f"Severity: {result['severity']} | "
                    f"{result['message']}"
                )
            else:
                print(
                    f"Event failed: "
                    f"{response.status_code} - {response.text}"
                )

            await asyncio.sleep(interval)


if __name__ == "__main__":
    try:
        asyncio.run(run_simulator(interval=7))
    except KeyboardInterrupt:
        print()
        print("Simulator stopped.")