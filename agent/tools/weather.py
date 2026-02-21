"""
Weather lookup via wttr.in (no API key required).
"""
import urllib.parse
import requests


def get_weather(location: str) -> dict:
    """
    Return current weather conditions for a location.
    Returns: {condition, temp_c, feels_like_c, humidity, wind_kph, location}
    """
    encoded = urllib.parse.quote(location)
    url = f"https://wttr.in/{encoded}?format=j1"

    resp = requests.get(url, timeout=10, headers={"User-Agent": "free-agent/1.0"})
    resp.raise_for_status()

    data = resp.json()
    current = data["current_condition"][0]
    area = data.get("nearest_area", [{}])[0]
    area_name = (
        area.get("areaName", [{}])[0].get("value", location)
        if area else location
    )

    return {
        "location": area_name,
        "condition": current.get("weatherDesc", [{}])[0].get("value", ""),
        "temp_c": int(current.get("temp_C", 0)),
        "feels_like_c": int(current.get("FeelsLikeC", 0)),
        "humidity": int(current.get("humidity", 0)),
        "wind_kph": int(current.get("windspeedKmph", 0)),
    }


import json  # noqa: E402
from agent.tools.registry import tool  # noqa: E402


@tool({
    "name": "get_weather",
    "description": "Get current weather conditions for any location. No API key needed.",
    "input_schema": {
        "type": "object",
        "properties": {
            "location": {"type": "string", "description": "City name or location (e.g. 'London', 'New York')"},
        },
        "required": ["location"],
    },
})
def _handle(inputs: dict, **_) -> tuple[str, bool]:
    return json.dumps(get_weather(inputs["location"]), indent=2), False
