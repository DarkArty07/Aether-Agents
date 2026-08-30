from calc import total

if total(2, 3) != 5 or total(-1, 1) != 0:
    raise SystemExit("FAIL: total must add both operands")
print("PASS: total adds operands")
