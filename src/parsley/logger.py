"""Logger module for the Parsley application."""

# logger_module.py

import logging

_logger_holder: dict[str, logging.Logger] = {
    "logger": logging.getLogger("parsley_app")
}
_logger_holder["logger"].setLevel(logging.INFO)
if not _logger_holder["logger"].handlers:
    stream_handler = logging.StreamHandler()
    stream_handler.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    stream_handler.setFormatter(formatter)
    _logger_holder["logger"].addHandler(stream_handler)
_logger_holder["logger"].propagate = False

for handler in _logger_holder["logger"].handlers:
    handler.setLevel(logging.INFO)


def get_parsley_logger() -> logging.Logger:
    """Get the shared Parsley logger.

    Returns:
        logging.Logger: The shared Parsley logger instance.

    """
    return _logger_holder["logger"]


def set_parsley_logger(new_logger: logging.Logger) -> None:
    """Set a new shared Parsley logger.

    Args:
        new_logger (logging.Logger): The new Parsley logger instance.

    """
    _logger_holder["logger"] = new_logger


def set_verbosity(level: int) -> None:
    """Set the verbosity level of the shared Parsley logger.

    Args:
        level (int): The logging level to set (e.g., logging.DEBUG, logging.INFO).

    """
    logger = get_parsley_logger()
    logger.setLevel(level)
    for handler in logger.handlers:
        handler.setLevel(level)
