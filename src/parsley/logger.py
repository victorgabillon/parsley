"""Logger module for the Parsley application."""

# logger_module.py

import logging

parsley_logger: logging.Logger = logging.getLogger("parsley_app")
parsley_logger.setLevel(logging.INFO)
if not parsley_logger.handlers:
    handler = logging.StreamHandler()
    handler.setLevel(logging.INFO)
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    parsley_logger.addHandler(handler)
parsley_logger.propagate = False

for h in parsley_logger.handlers:
    h.setLevel(logging.INFO)


def get_parsley_logger() -> logging.Logger:
    """Get the shared Parsley logger.

    Returns:
        logging.Logger: The shared Parsley logger instance.

    """
    return parsley_logger


def set_parsley_logger(new_logger: logging.Logger) -> None:
    """Set a new shared Parsley logger.

    Args:
        new_logger (logging.Logger): The new Parsley logger instance.

    """
    global parsley_logger
    parsley_logger = new_logger


def set_verbosity(level: int) -> None:
    """Set the verbosity level of the shared Parsley logger.

    Args:
        level (int): The logging level to set (e.g., logging.DEBUG, logging.INFO).

    """
    parsley_logger = get_parsley_logger()
    parsley_logger.setLevel(level)
    for handler in parsley_logger.handlers:
        handler.setLevel(level)
