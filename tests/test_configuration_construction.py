"""Compose configuration before running user constructors or needed factories."""

from collections import Counter
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

import pytest
from dacite import MissingValueError, WrongTypeError

from parsley import create_parsley, make_partial_dataclass_with_optional_paths
from parsley.construction import UnresolvedDefaultError
from parsley.parser import ArgsDataclassDefaultsError
from parsley.recursive_dataclass_with_path_to_yaml import (
    resolve_dict_to_base_dataclass,
    resolve_extended_object,
    resolve_yaml_file_to_base_dataclass,
)
from parsley.utils import FieldUnionParsingError


@pytest.mark.parametrize("source", ["cli", "known", "yaml", "extra", "dict"])
def test_required_root_field_from_each_source(tmp_path, source):
    @dataclass
    class Required:
        x: int

    parser = create_parsley(Required)
    if source == "cli":
        result = parser.parse_arguments(argv=["--x", "3"], strict=True)
    elif source == "known":
        result, remaining = parser.parse_known_arguments(argv=["--x", "3", "--outer"])
        assert remaining == ["--outer"]
    elif source == "yaml":
        path = tmp_path / "required.yaml"
        path.write_text("x: 3\n")
        result = parser.parse_arguments(argv=[], config_file_path=str(path))
    elif source == "extra":
        partial = make_partial_dataclass_with_optional_paths(Required)
        result = parser.parse_arguments(argv=[], extra_args=partial(x=3))
    else:
        result = parser.parse_arguments_with_command_line_args(
            args_command_line={"x": 3}
        )
    assert isinstance(result, Required)
    assert result.x == 3


def test_required_nested_fields_can_be_combined_across_sources(tmp_path):
    @dataclass
    class Child:
        x: int
        y: int
        z: int

    @dataclass
    class Root:
        child: Child

    path = tmp_path / "config.yaml"
    path.write_text("child:\n  x: 1\n  y: 2\n")
    partial_child = make_partial_dataclass_with_optional_paths(Child)
    partial_root = make_partial_dataclass_with_optional_paths(Root)
    result = create_parsley(Root).parse_arguments(
        argv=["--child.x", "3", "--child.z", "4"],
        config_file_path=str(path),
        extra_args=partial_root(child=partial_child(z=5)),
    )
    assert (result.child.x, result.child.y, result.child.z) == (3, 2, 5)


@pytest.mark.parametrize(
    "data, expected_path", [({}, "child"), ({"child": {}}, "child.x")]
)
def test_missing_required_values_have_field_context(data, expected_path):
    @dataclass
    class Child:
        x: int

    @dataclass
    class Root:
        child: Child

    with pytest.raises(MissingValueError) as error:
        create_parsley(Root).parse_arguments_with_command_line_args(
            args_command_line=data
        )
    assert error.value.field_path == expected_path
    assert expected_path in str(error.value)
    # The old exception import remains available, but missing data uses dacite's error.
    assert issubclass(ArgsDataclassDefaultsError, ValueError)


@pytest.mark.parametrize("with_yaml", [False, True])
def test_required_nullable_field_distinguishes_omission_from_null(tmp_path, with_yaml):
    @dataclass
    class Config:
        x: int | None

    parser = create_parsley(Config)
    path = tmp_path / "config.yaml"
    path.write_text("{}")
    kwargs = {"config_file_path": str(path)} if with_yaml else {}
    with pytest.raises(MissingValueError) as error:
        parser.parse_arguments(argv=[], **kwargs)
    assert error.value.field_path == "x"
    partial = make_partial_dataclass_with_optional_paths(Config)
    assert (
        parser.parse_arguments(argv=[], extra_args=partial(x=None), **kwargs).x is None
    )


@pytest.mark.parametrize("x", [None, 7])
@pytest.mark.parametrize(
    "entrypoint", ["main", "known", "dict", "yaml", "direct", "extended"]
)
def test_root_and_nested_hooks_run_once_with_final_values(tmp_path, x, entrypoint):
    calls = Counter()

    @dataclass
    class Child:
        x: int = 0
        text: str = " child "
        derived: int = field(init=False, default=-1)

        def __post_init__(self):
            calls["child"] += 1
            self.x += 1
            self.text = self.text.strip()
            self.derived = self.x * 2

    @dataclass
    class Root:
        x: int = 0
        child: Child = field(default_factory=Child)

        def __post_init__(self):
            calls["root"] += 1
            self.x += 1
            assert self.child.derived == self.child.x * 2

    data = {} if x is None else {"x": x, "child": {"x": x}}
    argv = [] if x is None else ["--x", str(x), "--child.x", str(x)]
    parser = create_parsley(Root)
    if entrypoint == "main":
        result = parser.parse_arguments(argv=argv)
    elif entrypoint == "known":
        result, rest = parser.parse_known_arguments(argv=[*argv, "--outer"])
        assert rest == ["--outer"]
    elif entrypoint == "dict":
        result = parser.parse_arguments_with_command_line_args(args_command_line=data)
    elif entrypoint == "yaml":
        path = tmp_path / "config.yaml"
        path.write_text("{}" if x is None else f"x: {x}\nchild:\n  x: {x}\n")
        result = resolve_yaml_file_to_base_dataclass(str(path), Root)
    elif entrypoint == "direct":
        result = resolve_dict_to_base_dataclass(data, Root)
    else:
        partial = make_partial_dataclass_with_optional_paths(Root)
        child_partial = make_partial_dataclass_with_optional_paths(Child)
        extra = partial() if x is None else partial(x=x, child=child_partial(x=x))
        result = resolve_extended_object(extra, Root)
    assert result.x == (1 if x is None else 8)
    assert result.child.x == (1 if x is None else 8)
    assert result.child.text == "child"
    assert result.child.derived == result.child.x * 2
    assert calls == {"root": 1, "child": 1}


def test_lower_level_cli_resolution_does_not_construct_user_dataclasses():
    calls = []

    @dataclass
    class Child:
        x: int

        def __post_init__(self):
            calls.append(self.x)

    @dataclass
    class Root:
        child: Child

    assert create_parsley(Root).parse_command_line_arguments(["--child.x", "3"]) == {
        "child": {"x": 3}
    }
    assert calls == []


@pytest.mark.parametrize("supplied", [False, True])
def test_factories_are_needed_once_and_mutables_do_not_leak(supplied):
    calls = Counter()

    def values_factory():
        calls["factory"] += 1
        return [1]

    @dataclass
    class Config:
        values: list[int] = field(default_factory=values_factory)

        def __post_init__(self):
            calls["hook"] += 1
            self.values.append(9)

    inputs = {"values": [3]} if supplied else {}
    parser = create_parsley(Config)
    first = parser.parse_arguments_with_command_line_args(args_command_line=inputs)
    second = parser.parse_arguments_with_command_line_args(args_command_line=inputs)
    expected = [3, 9] if supplied else [1, 9]
    assert first.values == second.values == expected
    first.values.append(100)
    assert second.values == expected
    assert inputs == ({"values": [3]} if supplied else {})
    assert calls["factory"] == (0 if supplied else 2)
    assert calls["hook"] == 2


@pytest.mark.parametrize("source", ["cli", "yaml", "dict", "extra"])
def test_nested_mapping_uses_type_defaults_without_invoking_parent_factory(
    tmp_path, source
):
    calls = Counter()

    @dataclass
    class Child:
        x: int = 0
        y: int = 2

        def __post_init__(self):
            calls["child"] += 1
            self.x += 1

    def custom_factory():
        calls["factory"] += 1
        return Child(x=10, y=20)

    @dataclass
    class Root:
        child: Child = field(default_factory=custom_factory)

    parser = create_parsley(Root)
    if source == "cli":
        result = parser.parse_arguments(argv=["--child.x", "7"])
    elif source == "yaml":
        path = tmp_path / "config.yaml"
        path.write_text("child:\n  x: 7\n")
        result = parser.parse_arguments(argv=[], config_file_path=str(path))
    elif source == "dict":
        result = parser.parse_arguments_with_command_line_args(
            args_command_line={"child": {"x": 7}}
        )
    else:
        partial = make_partial_dataclass_with_optional_paths(Root)
        child_partial = make_partial_dataclass_with_optional_paths(Child)
        result = parser.parse_arguments(
            argv=[], extra_args=partial(child=child_partial(x=7))
        )
    assert (result.child.x, result.child.y) == (8, 2)
    assert calls == {"child": 1}
    calls.clear()
    result = parser.parse_arguments(argv=[])
    assert (result.child.x, result.child.y) == (11, 20)
    assert calls == {"factory": 1, "child": 1}


def test_omission_null_and_empty_mapping_have_distinct_factory_semantics():
    calls = []

    @dataclass
    class Child:
        value: int = 2

    def factory():
        calls.append("factory")
        return Child(9)

    @dataclass
    class Root:
        child: Child | None = field(default_factory=factory)

    parser = create_parsley(Root)
    assert parser.parse_arguments(argv=[]).child.value == 9
    assert (
        parser.parse_arguments_with_command_line_args(
            args_command_line={"child": None}
        ).child
        is None
    )
    assert (
        parser.parse_arguments_with_command_line_args(
            args_command_line={"child": {}}
        ).child.value
        == 2
    )
    assert calls == ["factory"]


def test_supplied_dataclass_and_its_mutable_values_are_not_mutated():
    @dataclass
    class Config:
        items: list[int] = field(default_factory=list)

        def __post_init__(self):
            self.items.append(9)

    partial = make_partial_dataclass_with_optional_paths(Config)
    extra = partial(items=[1])
    parser = create_parsley(Config)
    result = parser.parse_arguments(argv=[], extra_args=extra)
    assert extra.items == [1]
    assert result.items == [1, 9]
    constructed = Config([2])
    result = parser.parse_arguments(argv=[], extra_args=constructed)
    assert constructed.items == [2, 9]
    # Existing input instances contribute their current field values as overrides.
    assert result.items == [2, 9, 9]


@pytest.mark.parametrize("source", ["path", "preset", "default_preset"])
def test_nested_yaml_and_overwrites_construct_selected_union_only(tmp_path, source):
    calls = Counter()
    path = tmp_path / "preset.yaml"
    path.write_text("kind: b\nx: 7\n")

    class Preset(str, Enum):
        chosen = "chosen"

        def get_yaml_file_path(self):
            return str(path)

    @dataclass
    class A:
        x: int = 0
        kind: Literal["a"] = "a"

        def __post_init__(self):
            calls["a"] += 1

    @dataclass
    class B:
        x: int = 0
        kind: Literal["b"] = "b"

        def __post_init__(self):
            calls["b"] += 1
            self.x += 1

    @dataclass
    class WithPath:
        child: B

    @dataclass
    class WithPreset:
        child: A | B | Preset = Preset.chosen

    if source == "default_preset":
        result = create_parsley(WithPreset).parse_arguments(argv=[])
    else:
        config = tmp_path / "config.yaml"
        if source == "path":
            config.write_text(
                f"child_path_to_yaml_file: {path}\nchild_overwrite:\n  x: 9\n"
            )
            root = WithPath
        else:
            config.write_text("child: chosen\nchild_overwrite:\n  kind: b\n  x: 9\n")
            root = WithPreset
        result = create_parsley(root).parse_arguments(
            argv=[], config_file_path=str(config)
        )
    assert isinstance(result.child, B)
    assert result.child.x == (8 if source == "default_preset" else 10)
    assert calls == {"b": 1}


def test_constructor_validation_is_not_retried_as_another_union_branch():
    calls = Counter()

    @dataclass
    class A:
        kind: Literal["a"]
        x: int = 0

        def __post_init__(self):
            calls["a"] += 1

    @dataclass
    class B:
        kind: Literal["b"]
        x: int = 0

        def __post_init__(self):
            calls["b"] += 1
            raise ValueError("B's validation failed")

    @dataclass
    class Root:
        child: A | B

    with pytest.raises(ValueError, match="B's validation failed"):
        create_parsley(Root).parse_arguments_with_command_line_args(
            args_command_line={"child": {"kind": "b"}}
        )
    assert calls == {"b": 1}


def test_missing_discriminated_union_field_has_useful_path():
    @dataclass
    class A:
        kind: Literal["a"]
        x: int

    @dataclass
    class B:
        kind: Literal["b"]
        y: int

    @dataclass
    class Root:
        child: A | B

    with pytest.raises(MissingValueError) as error:
        create_parsley(Root).parse_arguments_with_command_line_args(
            args_command_line={"child": {"kind": "b"}}
        )
    assert error.value.field_path == "child.y"


def test_factory_type_resolves_nested_preset_before_user_hooks(tmp_path):
    calls = Counter()
    path = tmp_path / "preset.yaml"
    path.write_text("x: 4")

    class Preset(str, Enum):
        chosen = "chosen"

        def get_yaml_file_path(self):
            return str(path)

    @dataclass
    class Leaf:
        x: int

        def __post_init__(self):
            calls["leaf"] += 1
            self.x += 1

    @dataclass
    class Child:
        leaf: Leaf | Preset = Preset.chosen

        def __post_init__(self):
            calls["child"] += 1
            assert isinstance(self.leaf, Leaf)
            assert self.leaf.x == 5

    @dataclass
    class Root:
        child: Child = field(default_factory=Child)

    result = create_parsley(Root).parse_arguments(argv=[])
    assert result.child.leaf.x == 5
    assert calls == {"child": 1, "leaf": 1}


def test_constructed_factory_objects_with_unresolved_presets_fail_explicitly(tmp_path):
    path = tmp_path / "preset.yaml"
    path.write_text("x: 4")

    class Preset(str, Enum):
        chosen = "chosen"

        def get_yaml_file_path(self):
            return str(path)

    @dataclass
    class Leaf:
        x: int

    @dataclass
    class Child:
        leaf: Leaf | Preset = Preset.chosen

    @dataclass
    class Root:
        child: Child = field(default_factory=lambda: Child())

    with pytest.raises(UnresolvedDefaultError, match="default_factory"):
        create_parsley(Root).parse_arguments(argv=[])


def test_invalid_types_still_fail_before_user_hook():
    calls = []

    @dataclass
    class Config:
        x: int

        def __post_init__(self):
            calls.append(self.x)

    with pytest.raises(FieldUnionParsingError, match="field 'x'"):
        create_parsley(Config).parse_arguments_with_command_line_args(
            args_command_line={"x": "invalid"}
        )
    assert calls == []


def test_invalid_factory_result_does_not_bypass_type_validation():
    calls = []

    @dataclass
    class Config:
        x: int = field(default_factory=lambda: "invalid")

        def __post_init__(self):
            calls.append(self.x)

    with pytest.raises(WrongTypeError) as error:
        create_parsley(Config).parse_arguments(argv=[])
    assert error.value.field_path == "x"
    assert calls == []


def test_factory_enum_values_are_not_references_without_dataclass_alternative():
    class Mode(str, Enum):
        chosen = "chosen"

        def get_yaml_file_path(self):
            raise AssertionError("An enum-only field is not a YAML-backed dataclass")

    @dataclass
    class Child:
        mode: Mode = Mode.chosen

    @dataclass
    class Root:
        child: Child = field(default_factory=lambda: Child())

    assert create_parsley(Root).parse_arguments(argv=[]).child.mode is Mode.chosen


def test_late_discriminator_does_not_construct_nested_objects_in_rejected_arms():
    calls = Counter()

    @dataclass
    class Leaf:
        x: int = 0

        def __post_init__(self):
            calls["leaf"] += 1
            self.x += 1

    @dataclass
    class A:
        leaf: Leaf
        kind: Literal["a"]

        def __post_init__(self):
            calls["a"] += 1

    @dataclass
    class B:
        leaf: Leaf
        kind: Literal["b"]

        def __post_init__(self):
            calls["b"] += 1

    @dataclass
    class Root:
        choice: A | B

    result = create_parsley(Root).parse_arguments_with_command_line_args(
        args_command_line={"choice": {"leaf": {"x": 7}, "kind": "b"}}
    )
    assert isinstance(result.choice, B)
    assert result.choice.leaf.x == 8
    assert calls == {"leaf": 1, "b": 1}


def test_partial_yaml_reference_can_be_completed_by_cli(tmp_path):
    calls = []

    @dataclass
    class Child:
        x: int
        y: int

        def __post_init__(self):
            calls.append((self.x, self.y))

    @dataclass
    class Root:
        child: Child

    path = tmp_path / "child.yaml"
    path.write_text("y: 4")
    config = tmp_path / "root.yaml"
    config.write_text(f"child_path_to_yaml_file: {path}\n")
    result = create_parsley(Root).parse_arguments(
        config_file_path=str(config), argv=["--child.x", "3"]
    )
    assert (result.child.x, result.child.y) == (3, 4)
    assert calls == [(3, 4)]
