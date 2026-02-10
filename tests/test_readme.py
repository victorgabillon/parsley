"""Test the base configuration parsing."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from parsley import Parsley, create_parsley
from parsley.alternative_dataclasses import (
    make_partial_dataclass_with_optional_paths,
)


@dataclass
class Config:
    """Configuration for the application."""

    x: int = 0
    y: str = "default"


def test_base():
    """Test the base configuration parsing."""
    parser = create_parsley(Config)

    ExtendedConfig = make_partial_dataclass_with_optional_paths(Config)

    # Parse arguments
    config = parser.parse_arguments_with_command_line_args(
        config_file_path="tests/yaml_files/config.yaml",
        extra_args=ExtendedConfig(y="from_extra"),
        args_command_line={"x": 42},
    )

    assert config == Config(x=42, y="from_extra")


@dataclass
class NestedConfig:
    """Configuration for the nested part of the application."""

    z: int


@dataclass
class Config2:
    """Configuration for the application."""

    x: int
    y: str
    nested_config: NestedConfig


def test_extra_args() -> None:
    PartialConfig = make_partial_dataclass_with_optional_paths(Config2)

    # Create the parser
    parser: Parsley[Config2] = create_parsley(Config2)

    # Define extra arguments using the extended dataclass
    extra_args = PartialConfig(
        x=20,  # Override the value of x
        nested_config_overwrite=NestedConfig(
            z=100
        ),  # Override the nested configuration
    )

    # Parse arguments with extra_args
    config = parser.parse_arguments(
        config_file_path="tests/yaml_files/readme_extra.yaml",
        extra_args=extra_args,
    )

    assert config == Config2(x=20, y="hello", nested_config=NestedConfig(z=100))


@dataclass
class Config3:
    x: int = 0
    y: str = "default"


def test_precedence() -> None:
    # creating an extented config dataclass that allows more flexibility (more later in the readme)
    ExtendedConfig = make_partial_dataclass_with_optional_paths(Config3)

    # Create the parser
    parser: Parsley[Config3] = create_parsley(Config3)

    # Define extra arguments using the extended dataclass
    extra_args = ExtendedConfig(
        y="from_extra",  # Override the value of y
    )

    # Parse arguments with extra_args
    config = parser.parse_arguments_with_command_line_args(
        config_file_path="tests/yaml_files/config2.yaml",
        extra_args=extra_args,
        args_command_line={"x": 42},  # Override the value of x from command line
    )

    assert config == Config3(x=42, y="from_extra")


@dataclass
class OptionA:
    discriminator: Literal["A"]
    value: int


@dataclass
class OptionB:
    discriminator: Literal["B"]
    name: str


@dataclass
class Config4:
    option: OptionA | OptionB | int = 0


def test_discriminator() -> None:
    # Create the parser
    parser: Parsley[Config4] = create_parsley(Config4)

    # Parse arguments with extra_args
    config = parser.parse_arguments_with_command_line_args(
        config_file_path="tests/yaml_files/discriminator.yaml"
    )

    assert config == Config4(option=OptionB(discriminator="B", name="hello"))


def test_discriminator2() -> None:
    # Create the parser
    parser: Parsley[Config4] = create_parsley(Config4)

    # Parse arguments with extra_args
    config = parser.parse_arguments_with_command_line_args(
        config_file_path="tests/yaml_files/discriminator2.yaml"
    )

    assert config == Config4(option=42)


@dataclass
class NestedConfig2:
    z: int


@dataclass
class Config6:
    x: int
    y: str
    nested_config: NestedConfig2


def test_recursive_yaml() -> None:
    # Create the parser
    parser: Parsley[Config6] = create_parsley(Config6)

    # Parse arguments with extra_args
    config = parser.parse_arguments(config_file_path="tests/yaml_files/nested_1.yaml")

    assert config == Config6(x=10, y="hello", nested_config=NestedConfig2(z=42))


class ModelPreset(str, Enum):
    small = "small"
    large = "large"

    def get_yaml_file_path(self) -> str:
        return f"tests/yaml_files/preset_{self.value}.yaml"


@dataclass
class PresetDataConfig:
    layers: int
    hidden_size: int


@dataclass
class AppConfig:
    model: ModelPreset | PresetDataConfig


def test_yaml_path_method() -> None:
    # Create the parser
    logger = logging.getLogger("my_logger")
    logger.setLevel(logging.INFO)
    parser: Parsley[AppConfig] = create_parsley(AppConfig, logger=logger)

    # Parse arguments with extra_args
    config = parser.parse_arguments(
        config_file_path="tests/yaml_files/config_model.yaml"
    )

    assert config == AppConfig(model=PresetDataConfig(layers=24, hidden_size=1024))


if __name__ == "__main__":
    test_base()
    test_extra_args()
    test_precedence()
    test_discriminator()
    test_discriminator2()
    test_recursive_yaml()
    test_yaml_path_method()
    print("all tests passed")
