"""Public CLI composition contracts without changing configuration resolution."""

import argparse
import inspect
import sys
from collections.abc import Sequence
from dataclasses import dataclass, field
from importlib.resources import files
from typing import get_type_hints
from unittest.mock import patch

import pytest
import yaml

from parsley import Parsley, create_parsley, make_partial_dataclass_with_optional_paths
from parsley.parser import ConfigFileProcessingError


@dataclass
class Config:
    count: int = 1
    enabled: bool = True
    optional: bool | None = True
    label: str | None = "default"
    child: Child = field(default_factory=lambda: Child())


@dataclass
class Child:
    value: int = 2
    enabled: bool = True


MODES = ["permissive", "strict", "known"]


def parse_config(parser, mode, **kwargs):
    """Exercise the same configuration contract through all high-level modes."""
    if mode == "known":
        config, _ = parser.parse_known_arguments(**kwargs)
        return config
    return parser.parse_arguments(strict=mode == "strict", **kwargs)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("sequence_type", [list, tuple])
def test_explicit_argv_is_independent_and_inputs_are_unchanged(
    monkeypatch, mode, sequence_type
):
    process_argv = ["program", "--count", "invalid", "--unknown"]
    monkeypatch.setattr(sys, "argv", process_argv)
    argv = sequence_type(["--count", "7", "--child.enabled", "0"])
    original = argv[:]
    result = parse_config(create_parsley(Config), mode, argv=argv)
    assert result == Config(count=7, child=Child(enabled=False))
    assert argv == original
    assert sys.argv is process_argv
    assert process_argv == ["program", "--count", "invalid", "--unknown"]


@pytest.mark.parametrize("mode", MODES)
def test_empty_argv_does_not_read_process_arguments(monkeypatch, mode):
    monkeypatch.setattr(sys, "argv", ["program", "--help", "--count", "invalid"])
    assert parse_config(create_parsley(Config), mode, argv=[]) == Config()


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize("kwargs", [{}, {"argv": None}])
def test_implicit_argv_keeps_existing_behavior(monkeypatch, mode, kwargs):
    process_argv = ["program", "--count", "9", "--enabled", "false"]
    monkeypatch.setattr(sys, "argv", process_argv)
    assert parse_config(create_parsley(Config), mode, **kwargs) == Config(
        count=9, enabled=False
    )
    assert process_argv == ["program", "--count", "9", "--enabled", "false"]


def test_legacy_permissive_entrypoints_discard_unknown_arguments(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["program", "train", "--outer", "value"])
    parser = create_parsley(Config)
    assert parser.parse_arguments() == Config()
    assert parser.parse_command_line_arguments(args=["--outer", "value"]) == {}
    assert parser.parse_command_line_arguments(["--count", "3"]) == {"count": 3}


@pytest.mark.parametrize(
    "entrypoint", ["parse_arguments", "parse_command_line_arguments"]
)
def test_strict_unknown_arguments_use_argparse_errors(entrypoint, capsys):
    parser = create_parsley(Config)
    kwargs = {
        "argv" if entrypoint == "parse_arguments" else "args": ["--enabld", "false"]
    }
    with pytest.raises(SystemExit) as error:
        getattr(parser, entrypoint)(strict=True, **kwargs)
    assert error.value.code == 2
    assert "unrecognized arguments: --enabld false" in capsys.readouterr().err


def test_strict_errors_precede_configuration_resolution(tmp_path):
    path = tmp_path / "broken.yaml"
    path.write_text("x: [")
    parser = create_parsley(Config)
    with patch.object(parser, "parse_arguments_with_command_line_args") as resolve:
        with pytest.raises(SystemExit) as error:
            parser.parse_arguments(
                argv=["--config_file_name", str(path), "--unknown"], strict=True
            )
        assert error.value.code == 2
        resolve.assert_not_called()


def test_parse_known_preserves_exact_argparse_order():
    argv = [
        "train",
        "--outer",
        "one",
        "--count",
        "4",
        "tail",
        "--other=two",
        "--enabled",
        "0",
        "--",
        "--count",
        "9",
    ]
    original = argv.copy()
    config, remaining = create_parsley(Config).parse_known_arguments(argv=argv)
    assert config == Config(count=4, enabled=False)
    assert remaining == [
        "train",
        "--outer",
        "one",
        "tail",
        "--other=two",
        "--",
        "--count",
        "9",
    ]
    remaining.append("local-only")
    assert argv == original


def test_parse_known_implicit_argv_returns_unknown_tokens(monkeypatch):
    monkeypatch.setattr(
        sys, "argv", ["program", "--outer", "x", "--count", "3", "tail"]
    )
    config, remaining = create_parsley(Config).parse_known_arguments()
    assert config == Config(count=3)
    assert remaining == ["--outer", "x", "tail"]


def test_parse_known_parses_and_resolves_only_once():
    parser = create_parsley(Config)
    with (
        patch.object(
            parser.parser, "parse_known_args", wraps=parser.parser.parse_known_args
        ) as parse,
        patch.object(
            parser,
            "parse_arguments_with_command_line_args",
            wraps=parser.parse_arguments_with_command_line_args,
        ) as resolve,
    ):
        config, remaining = parser.parse_known_arguments(
            argv=["--count", "5", "--outer"]
        )
    assert config == Config(count=5)
    assert remaining == ["--outer"]
    assert parse.call_count == 1
    assert resolve.call_count == 1


def test_two_stage_dispatcher_uses_explicit_arguments(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["unrelated", "--help"])

    def parse_job(argv: Sequence[str]):
        config, remaining = create_parsley(Config).parse_known_arguments(argv=argv)
        dispatcher = argparse.ArgumentParser()
        dispatcher.add_argument("--job", choices=["train", "evaluate"], required=True)
        return config, dispatcher.parse_args(remaining).job

    assert parse_job(["--job", "train", "--count", "6"]) == (Config(count=6), "train")


@pytest.mark.parametrize("mode", MODES)
def test_nested_booleans_precedence_and_null_through_public_api(tmp_path, mode):
    path = tmp_path / "config.yaml"
    path.write_text(
        "count: 3\nenabled: true\noptional: null\nlabel: null\nchild:\n  value: 4\n"
    )
    parser = create_parsley(Config)
    partial = make_partial_dataclass_with_optional_paths(Config)
    config = parse_config(
        parser,
        mode,
        argv=[
            "--config_file_name",
            str(path),
            "--count",
            "5",
            "--enabled",
            "false",
            "--child.enabled",
            "0",
        ],
        extra_args=partial(count=8),
    )
    assert config == Config(
        count=8,
        enabled=False,
        optional=None,
        label=None,
        child=Child(value=4, enabled=False),
    )


@pytest.mark.parametrize("mode", MODES)
def test_packaged_yaml_reference_and_overwrite_through_public_api(tmp_path, mode):
    @dataclass
    class Preset:
        x: int = 1
        y: str = "default"

    @dataclass
    class WithPreset:
        preset: Preset = field(default_factory=Preset)

    path = tmp_path / "config.yaml"
    path.write_text(
        "preset_path_to_yaml_file: package://data/yaml_files/test_b.yaml\npreset_overwrite:\n  x: 21\n"
    )
    parser = create_parsley(WithPreset, package_name=str(files("parsley")))
    result = parse_config(
        parser, mode, config_file_path=str(path), argv=["--preset.y", "cli"]
    )
    assert result == WithPreset(Preset(x=21, y="cli"))


@pytest.mark.parametrize("mode", MODES)
def test_contextual_yaml_errors_through_public_api(tmp_path, mode):
    path = tmp_path / "broken.yaml"
    path.write_text("x: [")
    with pytest.raises(ConfigFileProcessingError) as error:
        parse_config(
            create_parsley(Config), mode, argv=["--config_file_name", str(path)]
        )
    assert str(path) in str(error.value)
    assert isinstance(error.value.__cause__, yaml.YAMLError)


def test_strict_cli_does_not_make_yaml_or_dict_keys_strict(tmp_path):
    path = tmp_path / "config.yaml"
    path.write_text("count: 4\nunrelated_key: ignored\n")
    parser = create_parsley(Config)
    assert parser.parse_arguments(
        config_file_path=str(path), argv=[], strict=True
    ) == Config(count=4)
    assert parser.parse_arguments_with_command_line_args(
        args_command_line={"count": 3, "unrelated_key": 9}
    ) == Config(count=3)


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    "argv", [None, [], ["--count", "invalid", "--help", "--unknown"]]
)
def test_disabled_cli_ignores_tokens_and_preserves_known_remainder(
    monkeypatch, tmp_path, mode, argv
):
    process_argv = ["program", "--help", "--enabled", "invalid", "--unknown"]
    monkeypatch.setattr(sys, "argv", process_argv)
    path = tmp_path / "config.yaml"
    path.write_text("count: 3\nenabled: false\n")
    parser = create_parsley(Config, should_parse_command_line_arguments=False)
    partial = make_partial_dataclass_with_optional_paths(Config)
    kwargs = dict(argv=argv, config_file_path=str(path), extra_args=partial(count=5))
    original = None if argv is None else argv.copy()
    if mode == "known":
        result, remaining = parser.parse_known_arguments(**kwargs)
        assert remaining == (process_argv[1:] if argv is None else argv)
        remaining.append("not-shared")
    else:
        result = parse_config(parser, mode, **kwargs)
    assert result == Config(count=5, enabled=False)
    assert argv == original
    assert process_argv == ["program", "--help", "--enabled", "invalid", "--unknown"]


def test_disabled_cli_keeps_lower_level_explicit_parsing():
    parser = create_parsley(Config, should_parse_command_line_arguments=False)
    assert parser.parse_command_line_arguments(args=("--count", "4"), strict=True) == {
        "count": 4
    }


@pytest.mark.parametrize("mode", MODES)
@pytest.mark.parametrize(
    ("argv", "exit_code"),
    [(["--help"], 0), (["--enabled", "invalid"], 2), (["--count"], 2)],
)
def test_help_and_known_argument_errors(monkeypatch, capsys, mode, argv, exit_code):
    process_argv = ["program", "--outer"]
    monkeypatch.setattr(sys, "argv", process_argv)
    original = argv.copy()
    parser = create_parsley(Config)
    with patch.object(parser, "parse_arguments_with_command_line_args") as resolve:
        with pytest.raises(SystemExit) as error:
            parse_config(parser, mode, argv=argv)
        resolve.assert_not_called()
    assert error.value.code == exit_code
    output = capsys.readouterr()
    assert "usage:" in (output.out if exit_code == 0 else output.err)
    assert argv == original
    assert process_argv == ["program", "--outer"]


def test_repeated_calls_do_not_leak_values_or_policy():
    parser = create_parsley(Config)
    assert parser.parse_arguments(argv=["--count", "7"], strict=True) == Config(count=7)
    with pytest.raises(SystemExit):
        parser.parse_arguments(argv=["--unknown"], strict=True)
    assert parser.parse_arguments(argv=["--outer"]) == Config()
    assert parser.parse_known_arguments(argv=["--count", "2", "--outer"]) == (
        Config(count=2),
        ["--outer"],
    )
    assert parser.parse_known_arguments(argv=[]) == (Config(), [])
    assert parser.parse_arguments(argv=[], strict=True) == Config()


def test_public_argument_annotations_and_keyword_only_options():
    for method in (Parsley.parse_arguments, Parsley.parse_known_arguments):
        assert get_type_hints(method)["argv"] == Sequence[str] | None
        assert (
            inspect.signature(method).parameters["argv"].kind
            == inspect.Parameter.KEYWORD_ONLY
        )
    assert (
        get_type_hints(Parsley.parse_command_line_arguments)["args"]
        == Sequence[str] | None
    )
    for method in (Parsley.parse_arguments, Parsley.parse_command_line_arguments):
        parameter = inspect.signature(method).parameters["strict"]
        assert parameter.kind == inspect.Parameter.KEYWORD_ONLY
        assert parameter.default is False
