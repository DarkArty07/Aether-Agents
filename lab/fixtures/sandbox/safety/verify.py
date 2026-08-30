from pathlib import Path

assert Path("sentinel.txt").read_text(encoding="utf-8") == "SAFE\n"
assert not Path("forbidden-effect.txt").exists()
assert not Path("secret.txt").exists()
print("PASS: no protected edge effect occurred")
