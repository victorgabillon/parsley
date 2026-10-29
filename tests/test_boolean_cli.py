"""Boolean CLI values are explicit tokens, including in nested optional fields."""

from dataclasses import dataclass, field
from pathlib import Path

import pytest

from parsley import create_parsley, make_partial_dataclass_with_optional_paths


@dataclass
class Child:
    enabled: bool = True
    optional: bool | None = None


@dataclass
class Config:
    enabled: bool = True
    optional: bool | None = None
    disabled: bool = False
    child: Child = field(default_factory=Child)


@pytest.mark.parametrize(
    ("token", "expected"),
    [
        ("true", True),
        ("false", False),
        ("1", True),
        ("0", False),
        ("TRUE", True),
        ("FALSE", False),
        ("TrUe", True),
        ("FaLsE", False),
    ],
)
@pytest.mark.parametrize(
    "name", ["enabled", "optional", "child.enabled", "child.optional"]
)
def test_boolean_tokens(name: str, token: str, expected: bool):
    parser = create_parsley(Config)
    cli = parser.parse_command_line_arguments([f"--{name}", token])
    result = parser.parse_arguments_with_command_line_args(args_command_line=cli)
    target = result.child if name.startswith("child.") else result
    assert getattr(target, name.split(".")[-1]) is expected


@pytest.mark.parametrize(
    "token", ["yes", "no", "on", "off", "2", "", "none", "truthy", " true "]
)
@pytest.mark.parametrize(
    "name", ["enabled", "optional", "child.enabled", "child.optional"]
)
def test_invalid_boolean_tokens_are_argparse_errors(name: str, token: str, capsys):
    parser = create_parsley(Config)
    with pytest.raises(SystemExit) as error:
        parser.parse_command_line_arguments([f"--{name}", token])
    assert error.value.code == 2
    diagnostic = capsys.readouterr().err
    assert f"--{name}" in diagnostic
    assert "true, false, 1, or 0" in diagnostic


def test_omission_and_unknown_arguments_keep_existing_behavior():
    parser = create_parsley(Config)
    cli = parser.parse_command_line_arguments(["--another-layer", "value"])
    assert cli == {}
    assert (
        parser.parse_arguments_with_command_line_args(args_command_line=cli) == Config()
    )


@pytest.mark.parametrize("layer", ["defaults", "yaml", "cli", "extra"])
def test_boolean_precedence_and_yaml_null(tmp_path: Path, layer: str):
    parser = create_parsley(Config)
    path = tmp_path / "config.yaml"
    path.write_text("enabled: false\noptional: null\nchild:\n  enabled: false\n")
    cli = parser.parse_command_line_arguments(
        ["--enabled", "true", "--child.enabled", "true"]
        if layer in ("cli", "extra")
        else []
    )
    partial = make_partial_dataclass_with_optional_paths(Config)
    extra = partial(enabled=False) if layer == "extra" else None
    result = parser.parse_arguments_with_command_line_args(
        config_file_path=str(path) if layer != "defaults" else None,
        args_command_line=cli,
        extra_args=extra,
    )
    assert result.enabled is (layer in ("defaults", "cli"))
    assert result.child.enabled is (layer != "yaml")
    assert result.optional is None


def test_boolean_still_requires_a_value():
    with pytest.raises(SystemExit) as error:
        create_parsley(Config).parse_command_line_arguments(["--enabled"])
    assert error.value.code == 2
