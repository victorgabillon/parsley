from dataclasses import dataclass
from parsley_coco.recursive_dataclass_with_path_to_yaml import (
    resolve_yaml_file_to_base_dataclass,
)


@dataclass
class C:
    x: int
    y: str


@dataclass
class A:
    a: int
    roo: C


@dataclass
class HOP:
    i: int
    b: C


@dataclass
class BIM:
    i: int
    hop: HOP


@dataclass
class C:
    x: int
    y: str


@dataclass
class A2:
    a: int
    roo: C
    bim: BIM


def test_resolve_dataclass_from_yaml():
    final_result = resolve_yaml_file_to_base_dataclass(
        "tests/yaml_files/test_a.yaml", A
    )
    print(final_result)


def test_resolve_dataclass_from_yaml_2():
    final_result = resolve_yaml_file_to_base_dataclass(
        "tests/yaml_files/test_a2.yaml", A2
    )
    print(final_result)


if __name__ == "__main__":
    test_resolve_dataclass_from_yaml()
    test_resolve_dataclass_from_yaml_2()
