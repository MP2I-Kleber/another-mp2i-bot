from __future__ import annotations

from os import environ
from typing import TYPE_CHECKING, Any
from urllib.parse import urljoin

import httpx

if TYPE_CHECKING:
    # TODO: maybe consider using pydantic ?
    from .models import ResponseLinesDiscoveryList, ResponseStopMonitoringList, ResponseStopPointsDiscoveryList

API_BASE_URL = "https://api.cts-strasbourg.eu"
CTS_TOKEN: str = environ["CTS_TOKEN"]


async def _get_request(uri: str, params: dict[str, Any] | None = None) -> httpx.Response:
    if not uri.startswith(API_BASE_URL):
        uri = urljoin(API_BASE_URL, uri)

    auth = (CTS_TOKEN, "")
    async with httpx.AsyncClient() as client:
        response = await client.get(uri, params=params, auth=auth)  # type: ignore # don't know why pyright complain about client.get
        # TODO: handle response status code
    return response


async def get_stops() -> ResponseStopPointsDiscoveryList:
    response = await _get_request("/v1/siri/2.0/stoppoints-discovery")
    return response.json()


async def get_lines() -> ResponseLinesDiscoveryList:
    response = await _get_request("/v1/siri/2.0/lines-discovery")
    return response.json()


async def get_stop_times(stop_ref: str) -> ResponseStopMonitoringList:
    params = {"MonitoringRef": stop_ref}
    response = await _get_request("/v1/siri/2.0/stop-monitoring", params=params)
    return response.json()
