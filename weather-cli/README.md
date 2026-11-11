# weather-cli

current conditions from [wttr.in](https://wttr.in). stdlib only — urllib,
no requests.

```bash
python3 weather.py            # auto-detect by ip
python3 weather.py london
python3 weather.py pune --json
```

honest error messages when the network's down or the place name is garbage.

run tests: `python3 -m unittest discover -s weather-cli -v`

set `WEATHER_CITY=pune` in your environment to skip typing the city every run.


## units

`--units u` switches to USCS (°F, mph); the default is metric (°C, km/h).
