#!/usr/bin/env python3
"""weather-cli - current conditions from wttr.in. stdlib only."""

import argparse
import http.client
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request

# wttr.in only recognises j1 on its own; the unit flag has to be a separate
# query parameter ("m" metric, "u" USCS), otherwise the response is not JSON.
BASE = "https://wttr.in/{place}?format=j1&{unit}"

UNIT_FIELDS = {
    "m": {"temp": "temp_C", "feels": "FeelsLikeC", "wind": "windspeedKmph",
          "degree": "°C", "wind_unit": "km/h"},
    "u": {"temp": "temp_F", "feels": "FeelsLikeF", "wind": "windspeedMiles",
          "degree": "°F", "wind_unit": "mph"},
}


def fetch(place, units="m"):
    if not isinstance(place, str):
        raise ValueError("place must be a string")
    place = place.strip()
    if units not in UNIT_FIELDS:
        raise ValueError("units must be 'm' (metric) or 'u' (USCS)")
    url = BASE.format(place=urllib.parse.quote(place, safe=""), unit=units)
    with urllib.request.urlopen(url, timeout=8) as r:
        return json.loads(r.read().decode())


def summarise(data, units="m"):
    if units not in UNIT_FIELDS:
        raise ValueError("units must be 'm' (metric) or 'u' (USCS)")
    fields = UNIT_FIELDS[units]
    cur = data["current_condition"][0]
    area = data["nearest_area"][0]
    city = area["areaName"][0]["value"]
    region = area["region"][0]["value"]
    return {
        "place": f"{city}, {region}",
        "temp": cur[fields["temp"]],
        "feels": cur[fields["feels"]],
        "desc": cur["lang_en"][0]["value"] if cur.get("lang_en") else cur["weatherDesc"][0]["value"],
        "humidity": cur["humidity"],
        "wind": cur[fields["wind"]],
        "degree": fields["degree"],
        "wind_unit": fields["wind_unit"],
    }


def render(info, as_json=False):
    if as_json:
        print(json.dumps(info, indent=2))
        return
    print(info["place"])
    print(f"{info['desc']}, {info['temp']}{info['degree']} (feels {info['feels']}{info['degree']})")
    print(f"humidity {info['humidity']}%  ·  wind {info['wind']} {info['wind_unit']}")


def default_city():
    """WEATHER_CITY env override, else empty (auto-ip)."""
    return os.environ.get("WEATHER_CITY", "")


def main():
    ap = argparse.ArgumentParser(description="current weather via wttr.in")
    ap.add_argument("place", nargs="?", default=default_city(), help="city (default: auto-ip or $WEATHER_CITY)")
    ap.add_argument("--json", action="store_true", help="raw summary as json")
    ap.add_argument("--units", choices=["m", "u"], default="m", help="m=metric, u=uscs")
    a = ap.parse_args()
    try:
        render(summarise(fetch(a.place, a.units), a.units), a.json)
    except urllib.error.HTTPError as e:
        sys.exit(f"wttr.in returned HTTP {e.code} for that place — maybe check the spelling")
    except (OSError, http.client.HTTPException):
        sys.exit("couldn't reach wttr.in — check your connection and try again")
    except (KeyError, IndexError, json.JSONDecodeError, UnicodeDecodeError):
        sys.exit("unexpected response from wttr.in — maybe the place name?")


if __name__ == "__main__":
    main()
