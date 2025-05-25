from parsley_coco import create_parsley, Parsley

from dataclasses import dataclass

from parsley_coco.alternative_dataclasses import (
    make_dataclass_with_optional_paths_and_overwrite,
    make_partial_dataclass_with_optional_paths,
)


@dataclass
class Config:
    x: int = 0
    y: str = "default"


def test_base():
    parser = create_parsley(Config)

    ExtendedConfig = make_partial_dataclass_with_optional_paths(Config)

    # Parse arguments
    config = parser.parse_arguments_with_command_line_args(
        config_file_path="tests/yaml_files/config.yaml",
        extra_args=ExtendedConfig(y="from_extra"),
        args_command_line={"x": 42},
    )

    print(config)

    assert config == Config(x=42, y="from_extra")


from dataclasses import dataclass
from parsley_coco import create_parsley, Parsley
from parsley_coco.alternative_dataclasses import (
    make_partial_dataclass_with_optional_paths,
)


@dataclass
class NestedConfig:
    z: int


@dataclass
class Config2:
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
        config_file_path="tests/yaml_files/readme_extra.yaml", extra_args=extra_args
    )

    print(config)
    assert config == Config2(x=20, y="hello", nested_config=NestedConfig(z=100))


if __name__ == "__main__":
    test_base()
    test_extra_args()
    print("all tests passed")
