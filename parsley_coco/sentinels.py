"""Sentinel values for indicating unfilled or missing data."""

# sentinels.py


from typing import Any


class _NotFilled:
    """A sentinel object to indicate that a value has not been filled."""

    def __repr__(self) -> str:
        """Return a string representation of the sentinel."""
        return f"<notfilled> at {hex(id(self))}"


def is_notfilled(value: Any) -> bool:
    """Check if the value is the sentinel indicating not filled."""
    return isinstance(value, _NotFilled)


notfilled = _NotFilled()
