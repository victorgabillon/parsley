from parsley_coco import create_parsley

from dataclasses import dataclass


@dataclass
class TestDataClass:
    """Test dataclass for parsing."""

    first_attribute: int = 2


def test_extra_args():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(
        should_parse_command_line_arguments=False, args_dataclass_name=TestDataClass
    )
    args = parsley.parse_arguments(extra_args=TestDataClass(first_attribute=5))

    assert args == TestDataClass(first_attribute=5)


if __name__ == "__main__":
    test_extra_args()
