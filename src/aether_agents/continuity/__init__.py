"""Aether-owned continuity database and hermes-agent hooks."""

from .database import (
    AetherDB,
    AetherDBSync,
    get_aether_db_path,
    resolve_aether_db,
    resolve_aether_dir,
)
from .hooks import register

__all__ = [
    "AetherDB",
    "AetherDBSync",
    "get_aether_db_path",
    "register",
    "resolve_aether_db",
    "resolve_aether_dir",
]
