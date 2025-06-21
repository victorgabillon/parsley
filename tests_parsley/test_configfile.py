from parsley_coco import create_parsley

from dataclasses import dataclass


@dataclass
class TestDataClass:
    """Test dataclass for parsing."""

    first_attribute: int = 2


def test_conffile():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(
        should_parse_command_line_arguments=False, args_dataclass_name=TestDataClass
    )
    args = parsley.parse_arguments(config_file_path="tests_parsley/yaml_files/test_conf_0.yaml")

    assert args == TestDataClass(first_attribute=3)


def test_conffile_2():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(
        should_parse_command_line_arguments=False, args_dataclass_name=TestDataClass
    )
    args = parsley.parse_arguments(
        extra_args=TestDataClass(first_attribute=5),
        config_file_path="tests_parsley/yaml_files/test_conf_0.yaml",
    )

    assert args == TestDataClass(first_attribute=5)


if __name__ == "__main__":
    test_conffile()
    test_conffile_2()
