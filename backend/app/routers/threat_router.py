import os
import ipaddress
import httpx
from fastapi import APIRouter, Depends, HTTPException
from ..auth import current_user
from ..models import User

router = APIRouter(prefix="/api/threat-intel", tags=["Threat Intelligence"])

@router.get("/ip/{ip}")
async def ip_lookup(ip: str, user: User = Depends(current_user)):
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        raise HTTPException(400, "Invalid IP address")

    result = {
        "ip": ip,
        "private": addr.is_private,
        "version": addr.version,
        "abuseipdb": None,
        "geolocation": None,
    }

    if addr.is_private or addr.is_loopback:
        return result

    key = os.getenv("ABUSEIPDB_API_KEY", "")
    if key:
        async with httpx.AsyncClient(timeout=8) as client:
            response = await client.get(
                "https://api.abuseipdb.com/api/v2/check",
                params={"ipAddress": ip, "maxAgeInDays": 90},
                headers={"Key": key, "Accept": "application/json"},
            )
            if response.is_success:
                result["abuseipdb"] = response.json().get("data")

    try:
        async with httpx.AsyncClient(timeout=5) as client:
            response = await client.get(f"https://ipapi.co/{ip}/json/")
            if response.is_success:
                data = response.json()
                result["geolocation"] = {
                    "country": data.get("country_name"),
                    "region": data.get("region"),
                    "city": data.get("city"),
                    "asn": data.get("asn"),
                    "org": data.get("org"),
                }
    except Exception:
        pass

    return result
