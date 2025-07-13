import os
import tempfile
from dataclasses import dataclass, field
from enum import Enum
from typing import Literal, Optional, Union

import dacite
import yaml

from parsley_coco import create_parsley
from parsley_coco.alternative_dataclasses import (
    make_partial_dataclass_with_optional_paths,
)

# --- Setup: Enums and dataclasses ---


class Preset(Enum):
    small = "small"
    large = "large"

    def get_yaml_file_path(self) -> str:
        return f"{self.value}_preset.yaml"


@dataclass
class SubConfigA:
    discriminator: Literal["A"]
    value: int
    flag: bool = False


@dataclass
class SubConfigB:
    discriminator: Literal["B"]
    name: str
    extra: Optional[str] = None


@dataclass
class DeepConfig:

    preset: Preset | Union[SubConfigA, SubConfigB]
    sub: Union[SubConfigA, SubConfigB] = field(
        default_factory=lambda: SubConfigA(discriminator="A", value=78945)
    )
    threshold: float = 0.5


@dataclass
class RootConfig:
    deep: DeepConfig
    count: int = 1
    tag: Optional[str] = None


# --- Test function ---


def test_all_features(tmp_path):
    # --- Create YAML files for enum presets ---
    small_preset = {"discriminator": "A", "value": 42}
    large_preset = {"discriminator": "B", "name": "biggy", "extra": "yes"}

    small_preset_path = tmp_path / "small_preset.yaml"
    large_preset_path = tmp_path / "large_preset.yaml"
    with open(small_preset_path, "w") as f:
        yaml.safe_dump(small_preset, f)
    with open(large_preset_path, "w") as f:
        yaml.safe_dump(large_preset, f)

    # --- Main config YAML referencing the enum and a union ---
    main_config = {
        "deep": {
            "preset": "large",  # Will trigger loading large_preset.yaml
            "sub": {"discriminator": "A", "value": 7, "flag": True},
            "threshold": 0.8,
        },
        "count": 3,
        "tag": "main",
    }
    main_config_path = tmp_path / "main_config.yaml"
    with open(main_config_path, "w") as f:
        yaml.safe_dump(main_config, f)

    # --- extra_args to overwrite nested fields ---
    @dataclass
    class ExtraDeep:
        preset: Preset = Preset.small  # Will trigger loading small_preset.yaml
        threshold: float = 0.2

    @dataclass
    class ExtraArgs:
        deep: ExtraDeep = field(default_factory=ExtraDeep)
        count: int = 99

    PartialOpTestRootConfig = make_partial_dataclass_with_optional_paths(cls=RootConfig)
    PartialOpTestDeepConfig = make_partial_dataclass_with_optional_paths(cls=DeepConfig)

    extra_args: PartialOpTestRootConfig = PartialOpTestRootConfig(
        deep=PartialOpTestDeepConfig(preset=Preset.small, threshold=0.2), count=99
    )

    # --- Command-line arguments to override YAML but not extra_args ---
    cli_args = {
        "count": 123,
        "deep": {"threshold": 0.99, "sub": {"discriminator": "B", "name": "cli_name"}},
    }

    # --- Create parser and parse ---clear

    parser = create_parsley(RootConfig)

    import os

    # Save the current working directory
    original_dir = os.getcwd()
    os.chdir(tmp_path)
    config = parser.parse_arguments_with_command_line_args(
        config_file_path=str(main_config_path),
        extra_args=extra_args,
        args_command_line=cli_args,
    )

    # --- Assertions ---
    # extra_args should win for count and deep.preset, deep.threshold
    assert config.count == 99
    assert config.deep.threshold == 0.2
    assert config.deep.preset == SubConfigA(
        discriminator="A", value=42, flag=False
    )  # loaded from small_preset.yaml
    # extra_args does not set deep.sub, so command-line wins for deep.sub
    assert isinstance(config.deep.sub, SubConfigB)
    assert config.deep.sub.discriminator == "B"
    assert config.deep.sub.name == "cli_name"
    # YAML should win for tag (not set in extra_args or CLI)
    assert config.tag == "main"

    # Now test recursive YAML loading via enum
    # (simulate what would happen if only preset is set)
    only_enum_config = {"deep": {"preset": "large"}}
    only_enum_config_path = tmp_path / "only_enum.yaml"
    with open(only_enum_config_path, "w") as f:
        yaml.safe_dump(only_enum_config, f)

    config2 = parser.parse_arguments(config_file_path=str(only_enum_config_path))
    assert config2.deep.preset == SubConfigB(
        discriminator="B", name="biggy", extra="yes"
    )  # loaded from large_preset.yaml
    assert config2.deep.sub == SubConfigA(discriminator="A", value=78945)

    assert config2.deep.threshold == 0.5

    # Test default values
    assert config2.count == 1
    assert config2.tag is None

    # Return to the original directory
    os.chdir(original_dir)
    print("All features test passed.")


if __name__ == "__main__":
    import pytest

    pytest.main([__file__])
