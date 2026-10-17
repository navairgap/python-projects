#!/usr/bin/env python3
"""weather-cli - current conditions from wttr.in. stdlib only."""

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request

BASE = "https://wttr.in/{place}?format=j1{unit}"


def fetch(place, units="m"):
    if units not in ("m", "u"):
        raise ValueError("units must be 'm' (metric) or 'u' (USCS)")
    flag = "" if units == "m" else "u"
    url = BASE.format(place=urllib.parse.quote(place, safe=""), unit=flag)
    with urllib.request.urlopen(url, timeout=8) as r:
        return json.loads(r.read().decode())


def summarise(data):
    cur = data["current_condition"][0]
    area = data["nearest_area"][0]
    city = area["areaName"][0]["value"]
    region = area["region"][0]["value"]
    return {
        "place": f"{city}, {region}",
        "temp_c": cur["temp_C"],
        "feels_c": cur["FeelsLikeC"],
        "desc": cur["lang_en"][0]["value"] if cur.get("lang_en") else cur["weatherDesc"][0]["value"],
        "humidity": cur["humidity"],
        "wind_kmph": cur["windspeedKmph"],
    }


def render(info, as_json=False):
    if as_json:
        print(json.dumps(info, indent=2))
    else:
        print(f"{info['place']}")
        print(f"{info['desc']}, {info['temp_c']}°C (feels {info['feels_c']}°C)")
        print(f"humidity {info['humidity']}%  ·  wind {info['wind_kmph']} km/h")


def default_city():
    """WEATHER_CITY env override, else empty (auto-ip)."""
    import os
    return os.environ.get("WEATHER_CITY", "")


def main():
    ap = argparse.ArgumentParser(description="current weather via wttr.in")
    ap.add_argument("place", nargs="?", default=default_city(), help="city (default: auto-ip or $WEATHER_CITY)")
    ap.add_argument("--json", action="store_true", help="raw summary as json")
    ap.add_argument("--units", choices=["m", "u"], default="m", help="m=metric, u=uscs")
    a = ap.parse_args()
    try:
        render(summarise(fetch(a.place, a.units)), a.json)
    except urllib.error.URLError:
        sys.exit("couldn't reach wttr.in — check your connection and try again")
    except (KeyError, IndexError):
        sys.exit("unexpected response from wttr.in — maybe the place name?")


if __name__ == "__main__":
    main()
