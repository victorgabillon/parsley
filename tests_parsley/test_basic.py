from dataclasses import dataclass

from parsley_coco import create_parsley


@dataclass
class TestDataClass:
    """Test dataclass for parsing."""

    first_attribute: int = 2


def test_creation():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(
        should_parse_command_line_arguments=False, args_dataclass_name=TestDataClass
    )
    args = parsley.parse_arguments(extra_args=None)

    assert args == TestDataClass()


if __name__ == "__main__":
    test_creation()
