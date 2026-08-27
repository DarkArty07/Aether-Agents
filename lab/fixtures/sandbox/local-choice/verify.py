from formatter import format_label

assert format_label("  alpha beta  ") == "Alpha Beta"
assert format_label("gamma") == "Gamma"
print("PASS: formatter behavior")
