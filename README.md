# python-projects

![CI](https://github.com/navairgap/python-projects/actions/workflows/ci.yml/badge.svg)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![deps](https://img.shields.io/badge/dependencies-none-success)

Small, complete command-line projects in pure Python. **Standard library only —
zero pip installs, zero venv setup.** Each one is real enough to be useful and
small enough to read in one sitting.

## Requirements

- Python 3.9 or newer (`python3 --version`)

## Projects

| project | what it does | try it |
| --- | --- | --- |
| [passgen](passgen/) | password generator with entropy scoring | `python3 passgen/passgen.py -l 24 -v` |
| [todo-cli](todo-cli/) | json-backed todo list with priorities and stats | `python3 todo-cli/todo.py add "ship it"` |
| [weather-cli](weather-cli/) | current conditions via wttr.in | `python3 weather-cli/weather.py pune` |
| [disk-audit](disk-audit/) | find what's eating your disk | `python3 disk-audit/audit.py ~/Downloads` |
| [netcheck](netcheck/) | port / dns / http diagnostics | `python3 netcheck/netcheck.py port example.com 443` |
| [serveit](serveit/) | static file server (localhost; listings off by default) | `python3 serveit/serveit.py ~/share` |

Every project has tests. Every project's README fits on one screen.

## Running the tests

```bash
make test        # all six suites, verbose
# or individually:
python3 -m unittest discover -s passgen
python3 -m unittest discover -s todo-cli
python3 -m unittest discover -s weather-cli
python3 -m unittest discover -s disk-audit
python3 -m unittest discover -s netcheck
python3 -m unittest discover -s serveit
```

CI runs the same suites on Python 3.9 through 3.14 for every push and PR. The
Makefile is the single source of truth — if `make test` passes locally, CI
passes.

## House rules

- **stdlib only.** If it needs `pip`, it doesn't belong here.
- **every project ships with tests that pass** — enforced by CI, no network access.
- **readmes tell the truth.** No roadmap theater, no feature fiction.
- **small is the point.** One file of logic plus one file of tests; no classes
  where a function does it.
- **no web UI, no cloud sync, no plugin system.** When a project outgrows
  that, it graduates to its own repo.

## Design decisions

- **argparse over click** and **unittest over pytest** — stdlib parity; every
  suite runs on a stock Python with nothing installed.
- **six independent tools, not one package.** Each one clones, runs, and tests
  alone. A monorepo with packaging would couple their release cycles for no
  user benefit.
- **3.9 is the floor** because CI tests it and the code respects it — no match
  statements, no `X | Y` annotations. When 3.9 leaves the matrix, the syntax
  can modernize in one commit.

## Debugging

Run any tool with `python3 -X dev <tool>.py` for warnings-as-errors; every CLI
prints failures to stderr and exits non-zero. There are no log files — output
is the log.

## Contributing

Issues and PRs welcome. Keep it dependency-free, keep it tested, keep it honest.

## License

MIT (see [LICENSE](LICENSE))

## History

Born as python-basics, renamed when it became clear the repo wasn't about
learning syntax — it was about the discipline: stdlib only, tested, small.
