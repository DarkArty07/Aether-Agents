# Deliberately broken fixture
Run: python -m unittest tests/test_missing_import.py
tests/test_missing_import.py imports deliberately_missing_module. Diagnose only; do not hide the error.
