"""Configuration contracts under Python 3.14 deferred annotations."""

import argparse
from annotationlib import Format, get_annotations
from dataclasses import dataclass, field, fields
from pathlib import Path
from types import UnionType
from typing import Union, get_origin, get_type_hints

import pytest
from dacite import WrongTypeError

from parsley import create_parsley
from parsley.alternative_dataclasses import make_partial_dataclass_with_optional_paths
from parsley.utils import (
    add_arguments_from_dataclass,
    extend_with_config,
    flatten_fields,
    from_dict_with_union_handling,
    is_optional_type,
)


@dataclass
class DeferredConfig:
    """A config declared before its nested type."""

    child: DeferredChild = field(default_factory=lambda: DeferredChild())
    label: str | None = None


@dataclass
class DeferredChild:
    """Nested scalar CLI options."""

    number: int = 3
    weights: list[int] = field(default_factory=list)


@dataclass
class RecursiveConfig:
    """Recursive values consumed by the existing dataclass converter."""

    value: int
    children: list[RecursiveConfig] = field(default_factory=list)


@dataclass
class Box[T]:
    """Generic nested configuration value."""

    value: T


@dataclass
class GenericConfig:
    """Concrete specialization of a generic field."""

    box: Box[int]
    choices: list[int]
    named: dict[str, int]
    pair: tuple[int, str]


def test_deferred_nested_yaml_and_cli(tmp_path: Path) -> None:
    """YAML and CLI overrides still construct the declared nested objects."""
    config_path = tmp_path / "config.yaml"
    config_path.write_text("child:\n  number: 7\n  weights: [2, 4]\nlabel: parsed\n")
    parser = create_parsley(DeferredConfig, should_parse_command_line_arguments=False)
    result = parser.parse_arguments_with_command_line_args(
        config_file_path=str(config_path), args_command_line={"child": {"number": 9}}
    )
    assert result == DeferredConfig(DeferredChild(9, [2, 4]), "parsed")
    assert isinstance(result.child, DeferredChild)


def test_raw_dataclass_cli_uses_resolved_fields_without_mutation() -> None:
    """A forward reference is resolved before argparse uses it as a callable."""
    original_type = fields(DeferredConfig)[0].type
    parser = argparse.ArgumentParser()
    add_arguments_from_dataclass(parser, DeferredConfig)
    assert vars(parser.parse_args(["--child.number", "11"]))["child.number"] == 11
    assert fields(DeferredConfig)[0].type is original_type
    assert flatten_fields(DeferredConfig)["child.number"].type is int
    assert get_type_hints(extend_with_config(DeferredConfig))["child"] is DeferredChild
    assert (
        get_annotations(DeferredConfig, format=Format.STRING)["child"]
        == "DeferredChild"
    )


def test_local_deferred_dataclass_and_default_factory() -> None:
    """Native deferred annotations retain a local type's lexical namespace."""

    @dataclass
    class Child:
        value: int = 5

    @dataclass
    class Config:
        child: Child = field(default_factory=Child)
        items: list[int] = field(default_factory=list)

    parser = create_parsley(Config, should_parse_command_line_arguments=False)
    first = parser.parse_arguments()
    second = parser.parse_arguments()
    assert first.child == Child(5)
    assert first.child is not second.child
    assert first.items is not second.items
    assert get_type_hints(Config)["child"] is Child


def test_stringified_annotations_still_resolve() -> None:
    """Existing future-annotation consumers keep fully resolved field types."""
    namespace: dict[str, object] = {}
    exec(
        "from __future__ import annotations\n"
        "from dataclasses import dataclass\n"
        "@dataclass\nclass Config:\n    count: int = 2\n",
        namespace,
    )
    cls = namespace["Config"]
    assert cls.__annotations__["count"] == "int"
    parser = argparse.ArgumentParser()
    add_arguments_from_dataclass(parser, cls)
    assert parser.parse_args(["--count", "4"]).count == 4


def test_recursive_dataclass_conversion() -> None:
    """The converter builds a finite recursive tree with native self references."""
    result = from_dict_with_union_handling(
        RecursiveConfig,
        {
            "value": 1,
            "children": [{"value": 2}, {"value": 3, "children": [{"value": 4}]}],
        },
    )
    assert result == RecursiveConfig(
        1, [RecursiveConfig(2), RecursiveConfig(3, [RecursiveConfig(4)])]
    )
    assert get_type_hints(RecursiveConfig)["children"] == list[RecursiveConfig]


def test_generic_collections_and_invalid_input() -> None:
    """Generic configuration values preserve successful and failing conversion."""
    result = from_dict_with_union_handling(
        GenericConfig,
        {
            "box": {"value": 5},
            "choices": [1, 2],
            "named": {"a": 3},
            "pair": (4, "four"),
        },
    )
    assert result == GenericConfig(Box(5), [1, 2], {"a": 3}, (4, "four"))
    with pytest.raises(WrongTypeError):
        from_dict_with_union_handling(RecursiveConfig, {"value": "invalid"})


def test_union_representations_are_unified() -> None:
    """Both existing union spellings have one runtime representation in 3.14."""
    assert Union is UnionType
    assert get_origin(Union[int, None]) is UnionType
    assert is_optional_type(Union[int, None])
    assert is_optional_type(int | None)
    assert not is_optional_type(int | str)


def test_recursive_cli_schema_keeps_existing_failure() -> None:
    """An infinitely expandable CLI schema remains unsupported, as before."""
    with pytest.raises(RecursionError):
        make_partial_dataclass_with_optional_paths(RecursiveConfig)
