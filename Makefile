PY ?= python3

PROJECTS := passgen todo-cli weather-cli disk-audit netcheck serveit

.PHONY: test $(PROJECTS:%=run-%)

test:
	$(PY) -m unittest discover -s passgen -v
	$(PY) -m unittest discover -s todo-cli -v
	$(PY) -m unittest discover -s weather-cli -v
	$(PY) -m unittest discover -s disk-audit -v
	$(PY) -m unittest discover -s netcheck -v
	$(PY) -m unittest discover -s serveit -v

run-passgen:
	$(PY) passgen/passgen.py

run-todo:
	$(PY) todo-cli/todo.py ls -a

run-weather:
	$(PY) weather-cli/weather.py

run-disk-audit:
	$(PY) disk-audit/audit.py

run-netcheck:
	$(PY) netcheck/netcheck.py ip

run-serveit:
	$(PY) serveit/serveit.py
