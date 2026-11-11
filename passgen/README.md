# passgen

small password generator. stdlib only — no pip install, no excuses.

```bash
python3 passgen.py              # one 16-char password
python3 passgen.py -l 24 -n 5   # five 24-char passwords
python3 passgen.py --no-symbols # letters + digits only
```

uses `secrets`, guarantees at least one character from every selected set,
shuffles so the first chars aren't predictable.

run tests: `python3 -m unittest discover -s passgen -v`

## passphrases

`--passphrase --words 6` generates word-based passwords (`--count` works too). Words come from a fixed built-in list — no dictionary file needed.


## flags worth knowing

- `--exclude abc` — never use specific characters (site policies, legacy systems)
- `--passphrase --words 6` — word-based passwords for things you read aloud
- `-v` — entropy rating next to every password
