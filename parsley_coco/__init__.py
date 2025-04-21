"""Imports the main class from the parlsey module."""

from parsley_coco.parser import Parsley
from parsley_coco.factory import create_parsley
from parsley_coco.alternative_dataclasses import (
    make_partial_dataclass_with_optional_paths,
)


___all__ = ["Parlsey", "create_parsley", "make_partial_dataclass_with_optional_paths"]
