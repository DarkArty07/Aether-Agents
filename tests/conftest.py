"""Test configuration — ensure src/ is on the Python path."""
import sys
from pathlib import Path

# Add the src directory to Python path so olympus modules are importable
_src = Path(__file__).resolve().parent.parent / "src"
if str(_src) not in sys.path:
    sys.path.insert(0, str(_src))
