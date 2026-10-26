import json
import unittest
from unittest.mock import patch

import weather


SAMPLE = {
    "current_condition": [{
        "temp_C": "28", "FeelsLikeC": "31", "humidity": "62",
        "windspeedKmph": "14",
        "weatherDesc": [{"value": "Haze"}],
        "lang_en": [{"value": "Haze"}],
    }],
    "nearest_area": [{
        "areaName": [{"value": "Pune"}],
        "region": [{"value": "Maharashtra"}],
    }],
}


class TestWeather(unittest.TestCase):
    def test_summarise(self):
        info = weather.summarise(SAMPLE)
        self.assertEqual(info["place"], "Pune, Maharashtra")
        self.assertEqual(info["temp_c"], "28")
        self.assertEqual(info["desc"], "Haze")

    def test_summarise_falls_back_to_weather_desc(self):
        sample = json.loads(json.dumps(SAMPLE))
        sample["current_condition"][0]["lang_en"] = []
        self.assertEqual(weather.summarise(sample)["desc"], "Haze")

    def test_render_text(self):
        info = weather.summarise(SAMPLE)
        with patch("builtins.print") as p:
            weather.render(info)
        out = "\n".join(c.args[0] for c in p.call_args_list)
        self.assertIn("28°C", out)
        self.assertIn("Pune", out)

    def test_render_json(self):
        info = weather.summarise(SAMPLE)
        with patch("builtins.print") as p:
            weather.render(info, as_json=True)
        parsed = json.loads(p.call_args.args[0])
        self.assertEqual(parsed["humidity"], "62")

    def test_network_error_raises(self):
        from urllib.error import URLError
        with patch.object(weather.urllib.request, "urlopen", side_effect=URLError("down")):
            with self.assertRaises(URLError):
                weather.fetch("pune")

    def test_main_reports_malformed_json_without_traceback(self):
        import sys
        malformed = json.JSONDecodeError("invalid JSON", "{", 0)
        with patch.object(sys, "argv", ["weather.py", "pune"]):
            with patch.object(weather, "fetch", side_effect=malformed):
                with self.assertRaisesRegex(SystemExit, "unexpected response from wttr.in"):
                    weather.main()

    def test_main_reports_invalid_utf8_without_traceback(self):
        import sys
        error = UnicodeDecodeError("utf-8", b"\\xff", 0, 1, "invalid start byte")
        with patch.object(sys, "argv", ["weather.py", "pune"]):
            with patch.object(weather, "fetch", side_effect=error):
                with self.assertRaisesRegex(SystemExit, "unexpected response from wttr.in"):
                    weather.main()

    def test_unsupported_units_rejected_before_network(self):
        with patch.object(weather.urllib.request, "urlopen") as open_url:
            with self.assertRaises(ValueError):
                weather.fetch("pune", units="kelvin")
        open_url.assert_not_called()


if __name__ == "__main__":
    unittest.main()


class TestDefaultCity(unittest.TestCase):
    def test_env_override(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {"WEATHER_CITY": "pune"}):
            self.assertEqual(weather.default_city(), "pune")

    def test_empty_by_default(self):
        import os
        from unittest.mock import patch
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(weather.default_city(), "")


if __name__ == "__main__":
    unittest.main()

class TestUnits(unittest.TestCase):
    def test_units_flag_in_url(self):
        from unittest.mock import patch
        import weather
        with patch.object(weather.urllib.request, "urlopen") as m:
            m.return_value.__enter__.return_value.read.return_value = b"{}"
            weather.fetch("pune", units="u")
        self.assertIn("format=j1u", m.call_args.args[0])

    def test_place_slash_is_percent_encoded(self):
        with patch.object(weather.urllib.request, "urlopen") as m:
            m.return_value.__enter__.return_value.read.return_value = b"{}"
            weather.fetch("north/south")
        self.assertIn("north%2Fsouth", m.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
