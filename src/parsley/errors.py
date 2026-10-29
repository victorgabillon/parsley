"""Configuration errors shared by the parser and YAML resolvers."""

from typing import Any


class ConfigFileProcessingError(ValueError):
    """Raised when a config file cannot be processed for a dataclass."""

    def __init__(self, config_file_path: str, dataclass_type: type[Any]) -> None:
        """Initialize the error with the file path and dataclass type."""
        super().__init__(
            f"Could not process file {config_file_path} as {dataclass_type}."
        )
