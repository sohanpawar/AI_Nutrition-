"""System prompt loader — versioned artifacts under `prompts/`."""

from functools import lru_cache
from pathlib import Path

_PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"

# Active prompt version for Milestone 1 Phase 5.
ACTIVE_PROMPT_VERSION = "v1"


@lru_cache
def get_system_prompt(version: str | None = None) -> str:
    ver = version or ACTIVE_PROMPT_VERSION
    path = _PROMPTS_DIR / f"{ver}.md"
    if path.exists():
        return path.read_text(encoding="utf-8").strip()
    # Fallback if file missing
    return (
        "You are a food, nutrition, and food-safety assistant. "
        "Answer clearly and concisely. Extract atomic factual claims. "
        "Set every claim source to null. Do not invent citations. "
        "Do not give calorie/weight targets or medical advice; decline those requests."
    )


def clear_prompt_cache() -> None:
    """Test helper after swapping prompt files."""
    get_system_prompt.cache_clear()
