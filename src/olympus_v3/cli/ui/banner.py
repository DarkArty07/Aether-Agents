"""ASCII art helpers for the Aether CLI — banner, section headers, and colored output."""

from __future__ import annotations

from typing import Any

try:
    from rich.console import Console
    from rich.text import Text

    _HAS_RICH = True
except ImportError:  # pragma: no cover
    _HAS_RICH = False


BANNER = """
.___________________________________________________________________________.
|                                                                           |
|    |####|   |####|   |####|   |####|   |####|   |####|    O L Y M P U S  |
|    |#  #|   |#  #|   |#  #|   |#  #|   |#  #|   |#  #|                  |
|    |#  #|   |#  #|   |#  #|   |#  #|   |#  #|   |#  #|    T H E         |
|    |#  #|   |#  #|   |#  #|   |#  #|   |#  #|   |#  #|                  |
|    |####|   |####|   |####|   |####|   |####|   |####|    F O R G E     |
|                                                                           |
|    ___________________________________________________________________   |
|   |                                                                   |  |
|   |           A E T H E R   A G E N T S   v 0 . 1 5                  |  |
|   |           =====================================                   |  |
|   |                                                                   |  |
|   |              Forge your Daimons on Olympus                        |  |
|   |___________________________________________________________________|  |
|                                                                           |
'___________________________________________________________________________'
"""


def section(title: str) -> str:
    """Return a boxed section header.

    Args:
        title: The section title text.

    Returns:
        A multi-line string with a box frame around the title.
    """
    width = 60
    inner = width - 2
    pad = inner - len(title)
    left = pad // 2
    right = pad - left
    lines = [
        f".{'-' * inner}.",
        f"| {' ' * left}{title}{' ' * right} |",
        f"'{'-' * inner}'",
    ]
    return "\n".join(lines)


def _color(text: str, style: str) -> str:
    """Apply a rich style to text if rich is available."""
    if _HAS_RICH:
        console = Console()
        styled = Text(text, style=style)
        with console.capture() as capture:
            console.print(styled, end="")
        return capture.get()
    return text


def ok(msg: Any) -> None:
    """Print a green checkmark message.

    Args:
        msg: The message to display.
    """
    print(_color(f"  v {msg}", "bold green"))


def warn(msg: Any) -> None:
    """Print a yellow warning message.

    Args:
        msg: The warning message to display.
    """
    print(_color(f"  ! {msg}", "bold yellow"))


def fail(msg: Any) -> None:
    """Print a red failure message.

    Args:
        msg: The failure message to display.
    """
    print(_color(f"  x {msg}", "bold red"))


def info(msg: Any) -> None:
    """Print a blue info message.

    Args:
        msg: The info message to display.
    """
    print(_color(f"  i {msg}", "bold blue"))


def step(n: int, msg: Any) -> None:
    """Print a cyan step indicator.

    Args:
        n: Step number.
        msg: Description of this step.
    """
    print(_color(f"  [{n}] {msg}", "bold cyan"))
