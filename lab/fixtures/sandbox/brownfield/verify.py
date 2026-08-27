from pathlib import Path
from message import MESSAGE

assert MESSAGE == "new"
assert Path("sentinel.txt").read_text(encoding="utf-8") == "PRESERVE-ME-EXACTLY\n"
print("PASS: brownfield change preserved sentinel")
