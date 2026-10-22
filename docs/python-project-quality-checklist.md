# python project quality checklist

For each CLI project, validate user input at the boundary and produce actionable errors without tracebacks for expected mistakes. Cover empty input, malformed values, Unicode, missing files, permission errors, and large inputs. Use temporary directories and injected clocks/network clients for deterministic tests. Keep network tests mocked by default. Run the project's formatter, linter, and test suite before release; document supported Python versions.
