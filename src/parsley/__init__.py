"""Imports the main class from the parlsey module."""

from parsley.alternative_dataclasses import (
    make_partial_dataclass_with_optional_paths,
)
from parsley.factory import create_parsley
from parsley.parser import Parsley
from parsley.recursive_dataclass_with_path_to_yaml import (
    resolve_extended_object,
    resolve_yaml_file_to_base_dataclass,
)

__all__ = [
    "Parsley",
    "create_parsley",
    "make_partial_dataclass_with_optional_paths",
    "resolve_extended_object",
    "resolve_yaml_file_to_base_dataclass",
]
