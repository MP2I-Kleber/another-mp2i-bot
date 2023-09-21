from __future__ import annotations

from typing import TypedDict


class WeatherResponse(TypedDict):
    coord: WeatherCoord
    weather: list[Weather]
    base: str
    main: WeatherMain
    visibility: int
    wind: WeatherWind
    rain: WeatherRain
    snow: WeatherSnow
    dt: int
    sys: WeatherSys
    timezone: int
    id: int
    name: str
    cod: int


class WeatherCoord(TypedDict):
    lon: float
    lat: float


class Weather(TypedDict):
    id: int
    main: str
    description: str
    icon: str


class WeatherMain(TypedDict):
    temp: float
    feels_like: float
    temp_min: float
    temp_max: float
    pressure: int
    humidity: int
    sea_level: int
    grnd_level: int


class WeatherWind(TypedDict):
    speed: float
    deg: int
    gust: float


WeatherRain = TypedDict("WeatherRain", {"1h": float, "3h": float}, total=False)
WeatherSnow = TypedDict("WeatherSnow", {"1h": float, "3h": float}, total=False)


class WeatherSys(TypedDict):
    type: int
    id: int
    country: str
    sunrise: int
    sunset: int
