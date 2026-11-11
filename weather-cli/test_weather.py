import json
import unittest
from unittest.mock import patch

import weather

SAMPLE = {
    "current_condition": [{
        "temp_C": "28", "temp_F": "82",
        "FeelsLikeC": "31", "FeelsLikeF": "88",
        "humidity": "62",
        "windspeedKmph": "14", "windspeedMiles": "9",
        "weatherDesc": [{"value": "Haze"}],
        "lang_en": [{"value": "Haze"}],
    }],
    "nearest_area": [{
        "areaName": [{"value": "Pune"}],
        "region": [{"value": "Maharashtra"}],
    }],
}


class TestSummarise(unittest.TestCase):
    def test_metric_fields(self):
        info = weather.summarise(SAMPLE)
        self.assertEqual(info["place"], "Pune, Maharashtra")
        self.assertEqual(info["temp"], "28")
        self.assertEqual(info["feels"], "31")
        self.assertEqual(info["wind"], "14")
        self.assertEqual(info["desc"], "Haze")
        self.assertEqual(info["degree"], "°C")

    def test_uscs_fields(self):
        info = weather.summarise(SAMPLE, units="u")
        self.assertEqual(info["temp"], "82")
        self.assertEqual(info["feels"], "88")
        self.assertEqual(info["wind"], "9")
        self.assertEqual(info["degree"], "°F")
        self.assertEqual(info["wind_unit"], "mph")

    def test_falls_back_to_weather_desc(self):
        sample = json.loads(json.dumps(SAMPLE))
        sample["current_condition"][0]["lang_en"] = []
        self.assertEqual(weather.summarise(sample)["desc"], "Haze")

    def test_unsupported_units_rejected(self):
        with self.assertRaises(ValueError):
            weather.summarise(SAMPLE, units="kelvin")


class TestRender(unittest.TestCase):
    def test_render_text_metric(self):
        info = weather.summarise(SAMPLE)
        with patch("builtins.print") as p:
            weather.render(info)
        out = "\n".join(c.args[0] for c in p.call_args_list)
        self.assertIn("28°C", out)
        self.assertIn("Pune", out)
        self.assertIn("wind 14 km/h", out)

    def test_render_text_uscs(self):
        info = weather.summarise(SAMPLE, units="u")
        with patch("builtins.print") as p:
            weather.render(info)
        out = "\n".join(c.args[0] for c in p.call_args_list)
        self.assertIn("82°F", out)
        self.assertIn("wind 9 mph", out)

    def test_render_json(self):
        info = weather.summarise(SAMPLE)
        with patch("builtins.print") as p:
            weather.render(info, as_json=True)
        parsed = json.loads(p.call_args.args[0])
        self.assertEqual(parsed["humidity"], "62")


class TestFetch(unittest.TestCase):
    def test_network_error_raises(self):
        from urllib.error import URLError

        with patch.object(weather.urllib.request, "urlopen", side_effect=URLError("down")):
            with self.assertRaises(URLError):
                weather.fetch("pune")

    def test_unsupported_units_rejected_before_network(self):
        with patch.object(weather.urllib.request, "urlopen") as open_url:
            with self.assertRaises(ValueError):
                weather.fetch("pune", units="kelvin")
        open_url.assert_not_called()

    def test_non_string_place_rejected_before_network(self):
        for place in (None, 42, [], {}):
            with self.subTest(place=place):
                with patch.object(weather.urllib.request, "urlopen") as open_url:
                    with self.assertRaisesRegex(ValueError, "place must be a string"):
                        weather.fetch(place)
                    open_url.assert_not_called()

    def test_whitespace_place_is_trimmed(self):
        with patch.object(weather.urllib.request, "urlopen") as open_url:
            open_url.return_value.__enter__.return_value.read.return_value = b"{}"
            weather.fetch("  Pune  ")
        self.assertIn("wttr.in/Pune?", open_url.call_args.args[0])

    def test_units_flag_is_a_separate_query_parameter(self):
        # Regression: "format=j1u" makes wttr.in return the literal text
        # "j1u" instead of JSON; the unit must travel in its own parameter.
        with patch.object(weather.urllib.request, "urlopen") as m:
            m.return_value.__enter__.return_value.read.return_value = b"{}"
            weather.fetch("pune", units="u")
        url = m.call_args.args[0]
        self.assertIn("format=j1", url)
        self.assertIn("&u", url)
        self.assertNotIn("j1u", url)

    def test_place_slash_is_percent_encoded(self):
        with patch.object(weather.urllib.request, "urlopen") as m:
            m.return_value.__enter__.return_value.read.return_value = b"{}"
            weather.fetch("north/south")
        self.assertIn("north%2Fsouth", m.call_args.args[0])

    def test_default_network_timeout_is_bounded(self):
        with patch.object(weather.urllib.request, "urlopen") as m:
            m.return_value.__enter__.return_value.read.return_value = b"{}"
            weather.fetch("Pune")
        self.assertEqual(m.call_args.kwargs["timeout"], 8)


class TestMain(unittest.TestCase):
    def test_main_reports_malformed_json_without_traceback(self):
        import sys

        malformed = json.JSONDecodeError("invalid JSON", "{", 0)
        with patch.object(sys, "argv", ["weather.py", "pune"]):
            with patch.object(weather, "fetch", side_effect=malformed):
                with self.assertRaisesRegex(SystemExit, "unexpected response from wttr.in"):
                    weather.main()

    def test_main_reports_invalid_utf8_without_traceback(self):
        import sys

        error = UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")
        with patch.object(sys, "argv", ["weather.py", "pune"]):
            with patch.object(weather, "fetch", side_effect=error):
                with self.assertRaisesRegex(SystemExit, "unexpected response from wttr.in"):
                    weather.main()

    def test_main_reports_http_errors_with_the_status_code(self):
        import sys
        from urllib.error import HTTPError

        with patch.object(sys, "argv", ["weather.py", "no-such-city"]):
            with patch.object(weather, "fetch",
                              side_effect=HTTPError("u", 404, "nf", {}, None)):
                with self.assertRaisesRegex(SystemExit, "HTTP 404"):
                    weather.main()

    def test_main_reports_connection_failures_without_traceback(self):
        import sys
        from urllib.error import URLError

        with patch.object(sys, "argv", ["weather.py", "pune"]):
            with patch.object(weather, "fetch", side_effect=URLError("down")):
                with self.assertRaisesRegex(SystemExit, "couldn't reach wttr.in"):
                    weather.main()

    def test_main_reports_read_timeouts_without_traceback(self):
        # socket timeouts surface as TimeoutError (OSError), not URLError.
        import sys

        with patch.object(sys, "argv", ["weather.py", "pune"]):
            with patch.object(weather, "fetch", side_effect=TimeoutError("timed out")):
                with self.assertRaisesRegex(SystemExit, "couldn't reach wttr.in"):
                    weather.main()


class TestDefaultCity(unittest.TestCase):
    def test_env_override(self):
        import os

        with patch.dict(os.environ, {"WEATHER_CITY": "pune"}):
            self.assertEqual(weather.default_city(), "pune")

    def test_empty_by_default(self):
        import os

        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(weather.default_city(), "")


if __name__ == "__main__":
    unittest.main()
