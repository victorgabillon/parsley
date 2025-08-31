from dataclasses import dataclass
from typing import Literal

from parsley_coco import create_parsley


@dataclass
class TestDataClass4:
    """Test dataclass for parsing."""

    discriminator: Literal["dis_four"]
    first_attribute: int = 2
    second_attribute: str = "uu"


@dataclass
class TestDataClass5:
    """Test dataclass for parsing."""

    discriminator: Literal["dis_five"]
    first_attribute: int = 2
    second_attribute: str = "uu"


@dataclass
class TestDataClass3:
    """Test dataclass for parsing."""

    first_attribute: int = 2
    second_attribute: str = "uu"


@dataclass
class TestDataClass2:
    """Test dataclass for parsing."""

    first_attribute: int = 2
    second_attribute: TestDataClass3
    second_attribute: TestDataClass4 | TestDataClass5


@dataclass
class TestDataClass:
    """Test dataclass for parsing."""

    first_attribute: int = 2
    second_attribute: TestDataClass2
    third_attribute: int = 2
    fourth_attribute: int = 2


def test_conffile():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(
        should_parse_command_line_arguments=False, args_dataclass_name=TestDataClass
    )

    args = parsley.parse_arguments(
        extra_args=TestDataClass(first_attribute=5),
        config_file_path="tests_parsley/yaml_files/test_conf_0.yaml",
    )

    assert args == TestDataClass(first_attribute=3)


if __name__ == "__main__":
    test_conffile()
