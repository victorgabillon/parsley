"""Malformed YAML must retain its file context and original parser error."""

from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

import pytest
import yaml

from parsley import create_parsley
from parsley.parser import ConfigFileProcessingError
from parsley.recursive_dataclass_with_path_to_yaml import (
    resolve_yaml_file_to_base_dataclass,
    resolve_yaml_file_to_dict_allow_notfilled,
)


@dataclass
class Leaf:
    x: int = 42
    label: str | None = "default"


@dataclass
class Branch:
    leaf: Leaf = field(default_factory=Leaf)


@dataclass
class Root:
    branch: Branch = field(default_factory=Branch)


@pytest.mark.parametrize(
    "location", ["top", "path", "nested", "overwrite", "provider", "cli"]
)
def test_malformed_yaml_raises_with_path_and_cause(tmp_path: Path, location: str):
    bad_path = tmp_path / "malformed.yaml"
    bad_path.write_text("x: [", encoding="utf-8")
    config_path = tmp_path / "config.yaml"
    config_type = Root
    if location == "top":
        config_path = bad_path
    elif location == "path":
        config_path.write_text(f"branch_path_to_yaml_file: {bad_path}\n")
    elif location in ("nested", "overwrite"):
        key = "branch" if location == "nested" else "branch_overwrite"
        config_path.write_text(f"{key}:\n  leaf_path_to_yaml_file: {bad_path}\n")
    elif location == "provider":

        class Preset(str, Enum):
            broken = "broken"

            def get_yaml_file_path(self) -> str:
                return str(bad_path)

        @dataclass
        class WithPreset:
            leaf: Leaf | Preset = field(default_factory=Leaf)

        config_type = WithPreset
        config_path.write_text("leaf: broken\n")

    parser = create_parsley(config_type, should_parse_command_line_arguments=False)
    with pytest.raises(ConfigFileProcessingError) as error:
        if location == "cli":
            parser.parse_command_line_arguments(
                ["--branch.leaf_path_to_yaml_file", str(bad_path)]
            )
        else:
            parser.parse_arguments(config_file_path=str(config_path))
    assert str(bad_path) in str(error.value)
    assert isinstance(error.value.__cause__, yaml.YAMLError)


@pytest.mark.parametrize(
    "resolver",
    [resolve_yaml_file_to_base_dataclass, resolve_yaml_file_to_dict_allow_notfilled],
)
def test_malformed_packaged_yaml_reports_requested_path(tmp_path: Path, resolver):
    (tmp_path / "broken.yaml").write_text("x: [", encoding="utf-8")
    with pytest.raises(ConfigFileProcessingError) as error:
        resolver("package://broken.yaml", Leaf, package_name=str(tmp_path))
    assert "package://broken.yaml" in str(error.value)
    assert isinstance(error.value.__cause__, yaml.YAMLError)


@pytest.mark.parametrize("contents", [None, "", "{}", "x: 7\nlabel: null\n"])
def test_valid_yaml_and_no_config_keep_defaults_and_explicit_null(
    tmp_path: Path, contents: str | None
):
    parser = create_parsley(Leaf, should_parse_command_line_arguments=False)
    path = None
    if contents is not None:
        config_path = tmp_path / "valid.yaml"
        config_path.write_text(contents, encoding="utf-8")
        path = str(config_path)
    result = parser.parse_arguments(config_file_path=path)
    assert result == (Leaf(7, None) if contents and "x:" in contents else Leaf())


def test_missing_file_keeps_existing_error(tmp_path: Path):
    missing = tmp_path / "missing.yaml"
    parser = create_parsley(Leaf, should_parse_command_line_arguments=False)
    with pytest.raises(ConfigFileProcessingError) as error:
        parser.parse_arguments(config_file_path=str(missing))
    assert str(missing) in str(error.value)
    assert isinstance(error.value.__cause__, OSError)
