"""Test command line parsing."""

from dataclasses import dataclass, field

from parsley_coco import create_parsley
from parsley_coco.logger import get_parsley_logger


parsley_logger = get_parsley_logger()


@dataclass
class C:
    """Test dataclass for parsing."""

    x: int = 4578
    y: str = "uio"


@dataclass
class A:
    """Test dataclass for parsing."""

    a: int
    roo: C


@dataclass
class HOP:
    """Test dataclass for parsing."""

    i: int = 789
    b: C = field(default_factory=C)


@dataclass
class BIM:
    """Test dataclass for parsing."""

    i: int = 159
    hop: HOP = field(default_factory=HOP)


@dataclass
class A2:
    """Test dataclass for parsing."""

    a: int = 56
    roo: C = field(default_factory=C)
    bim: BIM = field(default_factory=BIM)


def test_cli_nested_dict_output():
    """Test dataclass for parsing."""
    parsley = create_parsley(
        should_parse_command_line_arguments=True, args_dataclass_name=A
    )

    args = parsley.parse_command_line_arguments(
        args=[
            "--config_file_name",
            "tests_parsley/yaml_files/test_conf_2.yaml",
            "--gg",
            "5",
        ]
    )

    assert args == {"config_file_name": "tests_parsley/yaml_files/test_conf_2.yaml"}


def test_cli_nested_dict_output_2():
    """Test dataclass for parsing."""
    parsley = create_parsley(
        should_parse_command_line_arguments=True, args_dataclass_name=A
    )

    args = parsley.parse_command_line_arguments(
        args=[
            "--config_file_name",
            "tests_parsley/yaml_files/test_conf_2.yaml",
            "--a",
            "5",
        ]
    )

    assert args == {
        "config_file_name": "tests_parsley/yaml_files/test_conf_2.yaml",
        "a": 5,
    }


def test_cli_nested_dict_output_3():
    parsley = create_parsley(
        should_parse_command_line_arguments=True, args_dataclass_name=A
    )

    args = parsley.parse_command_line_arguments(
        args=[
            "--config_file_name",
            "tests_parsley/yaml_files/test_conf_2.yaml",
            "--a",
            "5",
            "--roo.x",
            "5",
        ]
    )

    assert args == {
        "config_file_name": "tests_parsley/yaml_files/test_conf_2.yaml",
        "a": 5,
        "roo": {"x": 5},
    }


def test_cli_nested_dict_output_4():
    """Test dataclass for parsing."""
    parsley = create_parsley(
        should_parse_command_line_arguments=True, args_dataclass_name=A
    )

    args = parsley.parse_command_line_arguments(
        args=[
            "--config_file_name",
            "tests_parsley/yaml_files/test_conf_2.yaml",
            "--a",
            "5",
            "--roo_path_to_yaml_file",
            "tests_parsley/yaml_files/test_b.yaml",
        ]
    )

    assert args == {
        "config_file_name": "tests_parsley/yaml_files/test_conf_2.yaml",
        "a": 5,
        "roo": {"x": 10, "y": "hello"},
    }


def test_cli_nested_dict_output_5():
    """Test dataclass for parsing."""
    parsley = create_parsley(
        should_parse_command_line_arguments=True, args_dataclass_name=A
    )

    args = parsley.parse_command_line_arguments(
        args=[
            "--config_file_name",
            "tests_parsley/yaml_files/test_conf_2.yaml",
            "--a",
            "5",
            "--roo_path_to_yaml_file",
            "tests_parsley/yaml_files/test_b.yaml",
            "--roo_overwrite.y",
            "hellii",
        ]
    )

    assert args == {
        "config_file_name": "tests_parsley/yaml_files/test_conf_2.yaml",
        "a": 5,
        "roo": {"x": 10, "y": "hellii"},
    }


@dataclass
class Config:
    """Test dataclass for parsing."""

    x: int = 42
    y: str = "default"


def test_empty_command_line():
    """Test empty command line arguments."""
    parsley = create_parsley(
        should_parse_command_line_arguments=True, args_dataclass_name=Config
    )

    args = parsley.parse_command_line_arguments(args=["--script_name", "one_match"])

    assert not args  # Expecting empty dict as no arguments provided


if __name__ == "__main__":
    test_empty_command_line()
    test_cli_nested_dict_output()
    test_cli_nested_dict_output_2()
    test_cli_nested_dict_output_3()
    test_cli_nested_dict_output_4()
    test_cli_nested_dict_output_5()

    parsley_logger.info("All tests passed.")
