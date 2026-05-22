"""Central time helpers — single source of truth for UTC now."""

from datetime import UTC, datetime


def utcnow() -> datetime:
    """Return current UTC datetime as a naive datetime (consistent with DB storage)."""
    return datetime.now(UTC).replace(tzinfo=None)
