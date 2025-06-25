"""Logger module for the Parsley application."""

# logger_module.py


import logging


# Setup shared logger and proxy
parsley_logger = logging.getLogger("parsley_app")
parsley_logger.setLevel(logging.INFO)


if not parsley_logger.handlers:
    handler = logging.StreamHandler()
    formatter = logging.Formatter("[%(levelname)s] %(message)s")
    handler.setFormatter(formatter)
    parsley_logger.addHandler(handler)
    parsley_logger.propagate = False


def get_parsley_logger() -> logging.Logger:
    return parsley_logger


def set_parsley_logger(new_logger: logging.Logger) -> None:
    global parsley_logger
    parsley_logger = new_logger


def set_verbosity(level: int) -> None:
    parsley_logger = get_parsley_logger()
    parsley_logger.setLevel(level)
    for handler in parsley_logger.handlers:
        handler.setLevel(level)
