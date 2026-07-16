# Fixture task
Create `normalize.py` with pure `normalize(value)` for strings:
1. Strip surrounding whitespace.
2. Collapse each run of internal whitespace to one ASCII space.
3. Apply `str.casefold()`.

Create `tests/test_normalize.py` with focused tests, including:
`normalize("  HéLLo   WORLD  ") == "héllo world"`.

Use only the Python standard library and run:
`python -m unittest tests/test_normalize.py`.
