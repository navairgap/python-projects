# todo-cli

a json-backed todo list. stdlib only.

```bash
python3 todo.py add "write tests"
python3 todo.py ls            # open items
python3 todo.py ls -a         # everything, done included
python3 todo.py done 2
python3 todo.py undone 2
python3 todo.py pri 1 high    # high / normal / low
python3 todo.py rm 1
python3 todo.py stats
```

state lives in `todo.json` next to the script. it's json — diff it, back it
up, whatever. not cloud, not a startup, just a file.

`ls` shows each item's creation timestamp, and tags anything whose priority
isn't `normal`. priority updates survive restarts.

run tests: `python3 -m unittest discover -s todo-cli -v`
