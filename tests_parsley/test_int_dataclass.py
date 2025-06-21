from typing import Literal
from parsley_coco import create_parsley

from dataclasses import dataclass


@dataclass
class TestDataClass:
    """Test dataclass for parsing."""

    first_attribute: int = 2


@dataclass
class TestDataClasswo:
    """Test dataclass for parsing."""

    discriminator: Literal["oo"]
    first_attributed: int = 2


@dataclass
class TestDataClasswu:
    """Test dataclass for parsing."""

    discriminator: Literal["uu"]
    first_attributef: int = 2


@dataclass
class TestDataClass2:
    """Test dataclass for parsing."""

    first_attribute: int | TestDataClass


@dataclass
class TestDataClass4:
    """Test dataclass for parsing."""

    first_attribute: TestDataClasswu | int | TestDataClasswo


@dataclass
class TestDataClass3:
    """Test dataclass for parsing."""

    first_attribute: int | str | TestDataClass


def test_creation():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(args_dataclass_name=TestDataClass2)
    args = parsley.parse_arguments(
        config_file_path="tests_parsley/yaml_files/test_int_dataclass1.yaml"
    )

    assert args == TestDataClass2(first_attribute=2)


def test_creation2():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(args_dataclass_name=TestDataClass2)
    args = parsley.parse_arguments(
        config_file_path="tests_parsley/yaml_files/test_int_dataclass2.yaml"
    )

    assert args == TestDataClass2(first_attribute=TestDataClass(first_attribute=4))


def test_creation3():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(args_dataclass_name=TestDataClass3)
    args = parsley.parse_arguments(
        config_file_path="tests_parsley/yaml_files/test_int_dataclass2.yaml"
    )

    assert args == TestDataClass3(first_attribute=TestDataClass(first_attribute=4))


def test_creation4():
    """Test the creation of the Parsley object."""
    parsley = create_parsley(args_dataclass_name=TestDataClass4)
    args = parsley.parse_arguments(
        config_file_path="tests_parsley/yaml_files/test_int_dataclass3.yaml"
    )

    assert args == TestDataClass4(
        first_attribute=TestDataClasswu(discriminator="uu", first_attributef=4)
    )


if __name__ == "__main__":
    test_creation()
    test_creation2()
    test_creation3()
    test_creation4()
    print("all tests passedd")
