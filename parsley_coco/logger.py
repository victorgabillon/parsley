"""Logger module for the Parsley application."""

# logger_module.py


import logging

# Initialize the default logger
parsley_logger = logging.getLogger("parsley_app")
parsley_logger.setLevel(logging.DEBUG)

if not parsley_logger.handlers:
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    console_handler.setFormatter(formatter)
    parsley_logger.addHandler(console_handler)
    parsley_logger.propagate = False


def set_parsley_logger(logger: logging.Logger) -> None:
    """Allow external injection of a logger."""
    global parsley_logger
    parsley_logger = logger
