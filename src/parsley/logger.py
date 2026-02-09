"""Logger module for the Parsley application."""

import logging

_parsley_logger: logging.Logger = logging.getLogger("parsley_app")
_parsley_logger.setLevel(logging.INFO)

if not _parsley_logger.handlers:
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    stream_handler.setFormatter(formatter)
    _parsley_logger.addHandler(stream_handler)

_parsley_logger.propagate = False


def get_parsley_logger() -> logging.Logger:
    """Return the shared Parsley logger instance."""
    return _parsley_logger


def set_parsley_logger(new_logger: logging.Logger) -> None:
    """Update the shared logger configuration using another logger.

    The logger identity stays the same, but its level and handlers
    are replaced.
    """
    logger = get_parsley_logger()

    logger.handlers.clear()
    for handler in new_logger.handlers:
        logger.addHandler(handler)

    logger.setLevel(new_logger.level)


def set_verbosity(level: int) -> None:
    """Set verbosity level of the shared Parsley logger."""
    logger = get_parsley_logger()
    logger.setLevel(level)

    for handler in logger.handlers:
        handler.setLevel(level)
