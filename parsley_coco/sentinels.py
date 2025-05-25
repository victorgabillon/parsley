"""Sentinel values for indicating unfilled or missing data."""

# sentinels.py


class _NotFilled:
    """A sentinel object to indicate that a value has not been filled."""

    def __repr__(self) -> str:
        """Return a string representation of the sentinel."""
        return "<notfilled>"


notfilled = _NotFilled()
