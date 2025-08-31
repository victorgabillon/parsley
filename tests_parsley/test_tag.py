from dataclasses import dataclass
from enum import Enum
from typing import Literal

from parsley_coco import create_parsley


class Tags(str, Enum):
    """Enum for tags."""

    tag1 = "tag1"
    tag2 = "tag2"

    def get_yaml_file_path(self) -> str:
        """Get the YAML file path for the tag."""
        return f"tests_parsley/yaml_files/{self.value}.yaml"


class TagsYwo(str, Enum):
    """Enum for tags."""

    tag1_ywo = "tag1_ywo"
    tag2_ywo = "tag2_ywo"

    def get_yaml_file_path(self) -> str:
        """Get the YAML file path for the tag."""
        return f"tests_parsley/yaml_files/{self.value}.yaml"


class TagsYwo2(str, Enum):
    """Enum for tags."""

    tag1_ywo2 = "tag1_ywo2"
    tag2_ywo2 = "tag2_ywo2"

    def get_yaml_file_path(self) -> str:
        """Get the YAML file path for the tag."""
        return f"tests_parsley/yaml_files/{self.value}.yaml"


@dataclass
class TestDataClass:
    """Test dataclass for parsing."""

    first_attribute: int = 2
    second_attribute: str = "io"


@dataclass
class TestDataClassYwo:
    """Test dataclass for parsing."""

    discriminator: Literal["ywo"]
    first_attribute_ywo: int = 2
    second_attribute_ywo: str = "io"


@dataclass
class TestDataClassYwo2:
    """Test dataclass for parsing."""

    discriminator: Literal["ywo2"]
    first_attribute_ywo2: int = 2
    second_attribute_ywo2: str = "io"


@dataclass
class TestDataClass2:
    """Test dataclass for parsing."""

    first_attribute: Tags | TestDataClass


@dataclass
class TestDataClass3:
    """Test dataclass for parsing."""

    first_attribute: TagsYwo2 | TestDataClassYwo2 | TagsYwo | TestDataClassYwo


@dataclass
class TestDataClass4:
    """Test dataclass for parsing."""

    first_attribute: Tags | TestDataClass = Tags.tag1


def test_creation():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(
        should_parse_command_line_arguments=False, args_dataclass_name=TestDataClass2
    )
    args = parsley.parse_arguments(
        config_file_path="tests_parsley/yaml_files/test_conf_tag.yaml"
    )

    assert args == TestDataClass2(
        first_attribute=TestDataClass(first_attribute=3, second_attribute="defaultxx")
    )


def test_creation_2():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(
        should_parse_command_line_arguments=False, args_dataclass_name=TestDataClass3
    )
    args = parsley.parse_arguments(
        config_file_path="tests_parsley/yaml_files/test_conf_tag_ywo.yaml"
    )

    assert args == TestDataClass3(
        first_attribute=TestDataClassYwo(
            discriminator="ywo",
            first_attribute_ywo=9,
            second_attribute_ywo="defaultxxKsKK",
        )
    )


def test_creation_3():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(
        should_parse_command_line_arguments=False, args_dataclass_name=TestDataClass4
    )
    args = parsley.parse_arguments()

    assert args == TestDataClass4(
        first_attribute=TestDataClass(first_attribute=3, second_attribute="defaultxx")
    )


if __name__ == "__main__":
    test_creation()
    test_creation_2()
    test_creation_3()

    print("Test passed!")
