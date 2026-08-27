from app import greet
from normalize import normalize_name
from render import render_greeting

assert normalize_name("  aLEX  ") == "Alex"
assert render_greeting("Alex") == "Hola, Alex!"
assert greet("  aLEX  ") == "Hola, Alex!"
print("PASS: two-component greeting feature")
