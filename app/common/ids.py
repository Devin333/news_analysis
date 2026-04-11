"""ID generation utilities."""

from uuid import uuid4


def generate_id(prefix: str | None = None) -> str:
    """Generate string ID with optional prefix."""
    raw = uuid4().hex
    return f"{prefix}_{raw}" if prefix else raw
