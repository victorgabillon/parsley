from parsley_coco import create_parsley

from dataclasses import dataclass, field

from parsley_coco.alternative_dataclasses import (
    make_partial_dataclass_with_optional_paths,
)


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


@dataclass
class TestDataClass3:
    """Test dataclass for parsing."""

    first_attribute: int = 3
    second_attribute: str = "op"


@dataclass
class TestDataClass2:
    """Test dataclass for parsing."""

    second_attribute: TestDataClass3 = field(default_factory=TestDataClass3)
    first_attribute: int = 2


def test_extra_args_2():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(
        should_parse_command_line_arguments=False, args_dataclass_name=TestDataClass2
    )

    PartialOpTestDataClass2 = make_partial_dataclass_with_optional_paths(
        cls=TestDataClass2
    )
    PartialOpTestDataClass3 = make_partial_dataclass_with_optional_paths(
        cls=TestDataClass3
    )

    extra = PartialOpTestDataClass2(
        second_attribute=PartialOpTestDataClass3(second_attribute="ip")
    )

    args = parsley.parse_arguments(extra_args=extra)

    assert args == TestDataClass2(
        first_attribute=2,
        second_attribute=TestDataClass3(first_attribute=3, second_attribute="ip"),
    )


if __name__ == "__main__":
    test_extra_args()
    test_extra_args_2()
    print("all tests passed")
