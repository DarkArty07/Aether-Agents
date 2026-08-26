from normalize import normalize_name
from render import render_greeting


def greet(value: str) -> str:
    return render_greeting(normalize_name(value))
