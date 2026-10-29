"""Each partial-schema mode has an independent, repeatable cache identity."""

from annotationlib import Format, get_annotations
from dataclasses import dataclass, field, fields
from typing import get_type_hints

import pytest

from parsley import create_parsley
from parsley.alternative_dataclasses import (
    make_partial_dataclass,
    make_partial_dataclass_notfilled,
)
from parsley.sentinels import notfilled
from parsley.utils import extract_dataclass_types


@pytest.mark.parametrize("none_first", [True, False])
def test_partial_cache_modes_are_independent(none_first: bool):
    @dataclass
    class Child:
        value: int = 7
        label: str | None = "original"

    @dataclass
    class Parent:
        child: Child = field(default_factory=Child)
        optional_child: Child | None = None
        enabled: bool = True

    originals = {
        cls: (
            get_type_hints(cls),
            get_annotations(cls, format=Format.STRING),
            [(f.type, f.default, f.default_factory) for f in fields(cls)],
        )
        for cls in (Parent, Child)
    }
    factories = [make_partial_dataclass, make_partial_dataclass_notfilled]
    if not none_first:
        factories.reverse()
    generated = {factory: factory(Parent) for factory in factories}
    assert (
        generated[make_partial_dataclass]
        is not generated[make_partial_dataclass_notfilled]
    )

    for factory, expected in (
        (make_partial_dataclass, None),
        (make_partial_dataclass_notfilled, notfilled),
    ):
        partial_parent = generated[factory]
        for _ in range(3):
            assert factory(Parent) is partial_parent
            assert all(
                getattr(partial_parent(), f.name) is expected
                for f in fields(partial_parent)
            )
            for name in ("child", "optional_child"):
                (nested,) = extract_dataclass_types(
                    get_type_hints(partial_parent)[name]
                )
                assert nested is factory(Child)
                assert all(
                    getattr(nested(), f.name) is expected for f in fields(nested)
                )

    for cls, (hints, annotations, original_fields) in originals.items():
        assert get_type_hints(cls) == hints
        assert get_annotations(cls, format=Format.STRING) == annotations
        assert [
            (f.type, f.default, f.default_factory) for f in fields(cls)
        ] == original_fields
    assert Parent() == Parent(Child(7, "original"), None, True)


@pytest.mark.parametrize("none_first", [True, False])
def test_warmed_partial_caches_preserve_parser_omission_and_null(none_first: bool):
    @dataclass
    class Config:
        value: int = 7
        label: str | None = "original"

    factories = [make_partial_dataclass, make_partial_dataclass_notfilled]
    if not none_first:
        factories.reverse()
    for factory in factories:
        factory(Config)
    parser = create_parsley(Config)
    assert parser.parse_command_line_arguments([]) == {}
    assert parser.parse_arguments_with_command_line_args() == Config()
    assert parser.parse_arguments_with_command_line_args(
        extra_args=make_partial_dataclass_notfilled(Config)(label=None)
    ) == Config(label=None)
