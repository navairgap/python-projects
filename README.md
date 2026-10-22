# python-projects

![CI](https://github.com/navairgap/python-projects/actions/workflows/ci.yml/badge.svg)
![python](https://img.shields.io/badge/python-3.9%2B-blue)
![deps](https://img.shields.io/badge/dependencies-none-success)

Small, complete command-line projects in pure Python. **Standard library only —
zero pip installs, zero venv setup.** Each one is real enough to be useful and
small enough to read in one sitting. Learning in public, done properly.

## Requirements

- Python 3.9 or newer (`python3 --version`)
- that's the whole list

## Projects

| project | what it does | try it |
| --- | --- | --- |
| [passgen](passgen/) | password generator with entropy scoring | `python3 passgen/passgen.py -l 24 -v` |
| [todo-cli](todo-cli/) | json-backed todo list with stats | `python3 todo-cli/todo.py add "ship it"` |
| [weather-cli](weather-cli/) | current conditions via wttr.in | `python3 weather-cli/weather.py pune` |
| [disk-audit](disk-audit/) | find what's eating your disk | `python3 disk-audit/audit.py ~/Downloads` |
| [netcheck](netcheck/) | port / dns / http diagnostics | `python3 netcheck/netcheck.py port example.com 443` |
| [serveit](serveit/) | static file server (localhost; listings off by default) | `python3 serveit/serveit.py ~/share` |

Every project has tests. Every project has a README that fits on one screen.

## Running the tests

```bash
make test        # all six suites
# or individually:
python3 -m unittest discover -s passgen
python3 -m unittest discover -s todo-cli
python3 -m unittest discover -s weather-cli
python3 -m unittest discover -s disk-audit
python3 -m unittest discover -s netcheck
python3 -m unittest discover -s serveit
```

CI runs the same suites on Python 3.9 through 3.12 on every push.

## House rules

- **stdlib only.** If it needs `pip`, it doesn't belong here.
- **every project ships with tests that pass** — enforced by CI.
- **readmes tell the truth.** No roadmap theater, no feature fiction.
- **small is the point.** Each project is one file of logic plus its tests.

## Contributing

Issues and PRs welcome. Keep it dependency-free, keep it tested, keep it honest.

## License

MIT (see [LICENSE](LICENSE))

## Versioning

no releases — `main` is always green (CI enforces it) and every project is invocable straight from a clone. if that ever changes, this file will say so loudly.

## Design decisions

- argparse over click — stdlib parity, zero installs
- unittest over pytest — same reason, suites stay runnable on a stock python
- one file of logic + one of tests per project — no classes where a function does it
- no network in CI: every external call is mocked

## CI

github actions runs `make test` on Python 3.9–3.12 for every push: six suites, zero network. the makefile is the single source of truth — if `make test` passes locally, ci passes.

## Non-goals

no web UI, no cloud sync, no plugin system — the repo stays a set of scripts you can read end to end. when a project outgrows that, it graduates to its own repo.

## Debugging

run any tool with `python3 -X dev <tool>.py` for warnings-as-errors; every cli prints failures to stderr and exits non-zero. there are no log files — output is the log.

## FAQ

**why not one package with a pyproject?** because the point is six independent tools — each one clones, runs, and tests alone. a monorepo with packaging would couple their release cycles to each other for no user benefit.

**will any project grow dependencies?** only if the problem genuinely can't be solved in stdlib. so far, nothing has qualified.

## Toolchain

python 3.9 is the floor because CI tests it and the code respects it — no match statements, no `X | Y` annotations. when 3.9 leaves the matrix, the syntax can modernize in one commit.

## History

born as python-basics, renamed when it became clear the repo wasn't about learning syntax — it was about the discipline: stdlib only, tested, small. the rename was the mission statement.


## Test expectations

Prefer deterministic unit tests with mocked network calls and temporary files. Cover invalid input, missing files, permission errors, Unicode, and boundary values; document supported Python versions for each CLI.
