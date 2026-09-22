"""Map geocoding and route estimates with bounded public APIs."""
import asyncio
import os
from typing import Optional

import httpx
from pydantic import BaseModel, Field


class RouteStop(BaseModel):
    name: str = Field(min_length=1, max_length=160)
    latitude: Optional[float] = Field(default=None, ge=-90, le=90)
    longitude: Optional[float] = Field(default=None, ge=-180, le=180)


class RouteRequest(BaseModel):
    destination: str = Field(min_length=1, max_length=100)
    stops: list[RouteStop] = Field(min_length=2, max_length=12)


async def _geocode(client, stop: RouteStop, destination: str):
    if stop.latitude is not None and stop.longitude is not None:
        return {"name": stop.name, "latitude": stop.latitude, "longitude": stop.longitude, "source": "provided"}
    query = f"{stop.name}, {destination}"
    response = await client.get(
        "https://nominatim.openstreetmap.org/search",
        params={"q": query, "format": "jsonv2", "limit": 1, "accept-language": "zh-CN"},
        headers={"User-Agent": "smart-travel-agent/0.3 (route-planning-demo)"},
    )
    response.raise_for_status()
    rows = response.json()
    if not rows:
        return {"name": stop.name, "status": "unresolved"}
    return {"name": stop.name, "latitude": float(rows[0]["lat"]), "longitude": float(rows[0]["lon"]), "source": "Nominatim"}


async def calculate_route(request: RouteRequest) -> dict:
    """Resolve stops and ask OSRM for a driving/walking-friendly estimate."""
    report = {"status": "unavailable", "stops": [], "source": "OpenStreetMap / OSRM"}
    trust_env = os.getenv("ROUTE_TRUST_ENV", "false").lower() == "true"
    try:
        async with httpx.AsyncClient(timeout=8, trust_env=trust_env) as client:
            stops = await asyncio.wait_for(
                asyncio.gather(*(_geocode(client, stop, request.destination) for stop in request.stops)), 12
            )
            report["stops"] = list(stops)
            if any("latitude" not in stop for stop in stops):
                report["status"] = "partial"
                report["message"] = "部分地点未找到坐标，请修正地点名称后重试。"
                return report
            coordinates = ";".join(f"{s['longitude']},{s['latitude']}" for s in stops)
            response = await client.get(
                f"https://router.project-osrm.org/route/v1/driving/{coordinates}",
                params={"overview": "false", "steps": "false"},
            )
            response.raise_for_status()
            data = response.json()
            route = (data.get("routes") or [None])[0]
            if not route:
                report["status"] = "partial"
                report["message"] = "路线服务未返回可行路线。"
                return report
            report.update(
                status="ok", distance_km=round(route["distance"] / 1000, 1),
                duration_min=round(route["duration"] / 60),
                message="路线耗时为道路估算，步行、公交和实时拥堵需出发前再次确认。",
            )
            return report
    except (httpx.HTTPError, asyncio.TimeoutError, ValueError, KeyError, TypeError, IndexError):
        report.update(status="unavailable", stops=[], message="地图路线服务暂不可用，本次不提供已验证耗时。")
        return report
