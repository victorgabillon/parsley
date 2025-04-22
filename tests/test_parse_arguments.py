from dataclasses import dataclass, field

from parsley_coco import create_parsley, Parsley


@dataclass
class C:
    x: int = 4578
    y: str = "uio"


@dataclass
class A:
    a: int
    roo: C


@dataclass
class HOP:
    i: int = 789
    b: C = field(default_factory=C)


@dataclass
class BIM:
    i: int = 159
    hop: HOP = field(default_factory=HOP)


@dataclass
class C:
    x: int = 123
    y: str = "456"


@dataclass
class A2:
    a: int = 56
    roo: C = field(default_factory=C)
    bim: BIM = field(default_factory=BIM)


def test_parse_arguments():
    pars: Parsley[A2] = create_parsley(
        args_dataclass_name=A2, should_parse_command_line_arguments=False
    )
    a2 = pars.parse_arguments(extra_args=None)
    print(a2)

    a2 = pars.parse_arguments(config_file_path="tests/yaml_files/test_a2.yaml")
    print(a2)


if __name__ == "__main__":
    test_parse_arguments()
