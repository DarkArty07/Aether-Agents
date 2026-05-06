"""Olympus v2 Soul-to-System Converter — transforms SOUL.md into Pi Agent SYSTEM.md format.

Strips kawaii personality overlays and decorative elements from SOUL.md files,
keeping only the functional role definition, protocols, and output format.

This is used by config_loader to build the --system-prompt argument for Pi Agent,
since Pi Agent uses plain system prompts rather than the ACP personality overlay system.
"""

from __future__ import annotations

import re
from pathlib import Path


# Patterns to strip — kawaii/decorative elements that don't belong in a Pi system prompt
KAWAII_PATTERNS = [
    # Kaomoji/emoticons (Japanese-style emoticons)
    re.compile(r'[\(（]^\.{1,3}[\)）]'),         # (^_^), (^.^)
    re.compile(r'[\(（].*?[°ロ•ᴗ◡◕ᐛ◞ω∇▽∀].*?[\)）]'),  # Various kaomoji parts
    re.compile(r'◝ᴗ◝|◕ᴗ◕|ᕙᐛᕗ|ᕕᐛᕗ|¯\\_?\(ツ\)_?/¯'),  # Known kaomoji faces
    re.compile(r'⌐□_□|ヽ\(>∀<☆\)☆'),            # More kaomoji
    # Emoji patterns (common decorative emoji)
    re.compile(r'[\U0001F300-\U0001F9FF]'),     # Unicode emoji range
    re.compile(r'[\U00002600-\U000027BF]'),     # Misc symbols
    # Decorative dividers that are purely aesthetic
    re.compile(r'^[═━─▸▹★☆✓✗▶▶➤→↳◆◇♦•◇]+$', re.MULTILINE),
]

# Lines to remove entirely (content that's purely personality/decorative)
PERSONALITY_LINE_PATTERNS = [
    re.compile(r'^\s*[★☆✨⚡🔥💫🌙🌟💎🎵🎶💕💖✅❗]+(?:\s+[★☆✨⚡🔥💫🌙🌟💎🎵🎶💕💖✅❗]+)*\s*$'),
]

# Sections that are personality overlays (not functional) — strip entire sections
PERSONALITY_SECTIONS = [
    re.compile(r'^##\s+(?:personality|persona|vibe|flavor|style guide|communication style)\s*$', re.IGNORECASE),
]


def soul_to_system(soul_content: str) -> str:
    """Convert SOUL.md content to a clean SYSTEM.md format.

    Strips kawaii personality overlays while preserving:
    - Role definition
    - Execution context
    - Protocols
    - Limits
    - Output format
    - Sub-agent templates
    - Role catalog

    Args:
        soul_content: Raw content of a SOUL.md file.

    Returns:
        Cleaned system prompt content suitable for Pi Agent's --system-prompt.
    """
    lines = soul_content.split('\n')
    result_lines: list[str] = []
    skip_section = False
    skip_count = 0

    for line in lines:
        # Check if we're in a personality section to skip
        if skip_section:
            # Check if this is a new section header (starts the next section)
            if line.startswith('## ') or line.startswith('# '):
                skip_section = False
            else:
                continue

        # Check if this line starts a personality section to skip
        if any(pattern.match(line) for pattern in PERSONALITY_SECTIONS):
            skip_section = True
            continue

        # Skip purely decorative lines
        if any(pattern.match(line) for pattern in PERSONALITY_LINE_PATTERNS):
            continue

        # Apply kawaii pattern stripping to remaining lines
        cleaned = line
        for pattern in KAWAII_PATTERNS:
            cleaned = pattern.sub('', cleaned)

        # Skip empty lines that resulted from stripping
        if not cleaned.strip() and not line.strip():
            # Keep intentional blank lines
            result_lines.append('')
            continue

        # Skip lines that are now empty after kawaii stripping but weren't before
        if not cleaned.strip() and line.strip():
            continue

        result_lines.append(cleaned)

    # Collapse multiple consecutive blank lines into at most two
    result = '\n'.join(result_lines)
    result = re.sub(r'\n{3,}', '\n\n', result)

    # Strip leading/trailing whitespace
    return result.strip()


def load_soul_as_system(soul_path: Path) -> str:
    """Load a SOUL.md file and convert it to system prompt format.

    Args:
        soul_path: Path to the SOUL.md file.

    Returns:
        Cleaned system prompt content as a string.

    Raises:
        FileNotFoundError: If the SOUL.md file doesn't exist.
    """
    if not soul_path.exists():
        # Fall back to .pi/SYSTEM.md if it exists (Pi-native format)
        system_path = soul_path.parent / ".pi" / "SYSTEM.md"
        if system_path.exists():
            return system_path.read_text(encoding="utf-8")

        raise FileNotFoundError(
            f"No SOUL.md or SYSTEM.md found at {soul_path.parent}"
        )

    content = soul_path.read_text(encoding="utf-8")
    return soul_to_system(content)


def find_system_prompt(agent_dir: Path) -> str | None:
    """Find and load the system prompt for a Daimon.

    Search order:
    1. .pi/SYSTEM.md inside agent_dir (Pi-native format, takes priority)
    2. SOUL.md in agent_dir itself (converted via soul_to_system)

    Args:
        agent_dir: Path to the agent's directory.

    Returns:
        System prompt content, or None if no prompt file is found.
    """
    # Priority 1: Pi-native SYSTEM.md
    pi_system = agent_dir / ".pi" / "SYSTEM.md"
    if pi_system.exists():
        logger.debug(f"Using Pi-native system prompt: {pi_system}")
        return pi_system.read_text(encoding="utf-8")

    # Priority 2: Convert SOUL.md
    soul_file = agent_dir / "SOUL.md"
    if soul_file.exists():
        logger.debug(f"Converting SOUL.md to system prompt: {soul_file}")
        return soul_to_system(soul_file.read_text(encoding="utf-8"))

    logger.warning(f"No system prompt found in {agent_dir}")
    return None


# Lazy import-safe logging
import logging
logger = logging.getLogger("olympus_v2.soul_to_system")