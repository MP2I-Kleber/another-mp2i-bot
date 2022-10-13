from __future__ import annotations

from os import environ
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urljoin

import httpx

if TYPE_CHECKING:
    from .models import WeatherResponse


API_BASE_URL = "https://api.openweathermap.org"
APP_KEY = environ["OPENWEATHERMAP_API_KEY"]


async def _get(uri: str, params: dict[str, Any]) -> httpx.Response:
    if not uri.startswith(API_BASE_URL):
        uri = urljoin(API_BASE_URL, uri)
    params.setdefault("appid", APP_KEY)
    async with httpx.AsyncClient() as client:
        return await client.get(uri, params=params)


async def get_weather(
    coords: tuple[float, float], units: Literal["standard", "metric", "imperial"] = "metric", lang: str = "fr"
) -> WeatherResponse:
    params = {
        "lat": coords[0],
        "lon": coords[1],
        "units": units,
        "lang": lang,
    }
    result = await _get("/data/2.5/weather", params=params)
    return result.json()


def get_icon(code: str) -> str:
    return f"https://openweathermap.org/img/wn/{code}@4x.png"
