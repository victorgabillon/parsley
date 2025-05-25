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
