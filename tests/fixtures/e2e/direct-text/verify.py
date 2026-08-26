from pathlib import Path

value = Path("greeting.txt").read_text(encoding="utf-8")
if value != "Hola\n":
    raise SystemExit(f"FAIL: expected 'Hola\\n', got {value!r}")
print("PASS: greeting is Hola")
