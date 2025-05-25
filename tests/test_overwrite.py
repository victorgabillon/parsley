from parsley_coco import create_parsley

from dataclasses import dataclass


@dataclass
class TestDataClass:
    """Test dataclass for parsing."""

    first_attribute: int = 2


@dataclass
class TestDataClass4:
    """Test dataclass for parsing."""

    first_attribute: int = 2
    second_attribute: str = "default"


@dataclass
class TestDataClass2:
    """Test dataclass for parsing."""

    first_attribute_o: TestDataClass


@dataclass
class TestDataClass3:
    """Test dataclass for parsing."""

    first_attribute_o: TestDataClass4


def test_overwrite_2():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(
        should_parse_command_line_arguments=False, args_dataclass_name=TestDataClass2
    )
    args = parsley.parse_arguments(config_file_path="tests/yaml_files/test_conf_2.yaml")

    print("args", args)
    assert args == TestDataClass2(first_attribute_o=TestDataClass(first_attribute=9))


def test_overwrite_3():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(
        should_parse_command_line_arguments=False, args_dataclass_name=TestDataClass3
    )
    args = parsley.parse_arguments(config_file_path="tests/yaml_files/test_conf_3.yaml")

    print("args", args)
    assert args == TestDataClass3(
        first_attribute_o=TestDataClass4(
            first_attribute=11, second_attribute="defaultxx"
        )
    )


if __name__ == "__main__":
    # test_overwrite_2()
    test_overwrite_3()
