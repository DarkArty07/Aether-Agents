from config import OUTPUT_FORMAT

if OUTPUT_FORMAT != "json":
    raise SystemExit(f"FAIL: expected owner-selected json, got {OUTPUT_FORMAT!r}")
print("PASS: owner-selected output format is json")
