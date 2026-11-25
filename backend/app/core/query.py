"""Small helpers shared by repositories."""


def contains_pattern(text: str) -> str:
    """Build an ILIKE '%text%' pattern, escaping the user's own % and _ characters."""
    escaped = text.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"
