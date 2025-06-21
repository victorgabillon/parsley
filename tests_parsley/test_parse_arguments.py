from dataclasses import dataclass, field

from parsley_coco import create_parsley, Parsley


@dataclass
class C:
    """Test dataclass for parsing."""

    x: int = 4578
    y: str = "uio"


@dataclass
class A:
    """Test dataclass for parsing."""

    a: int
    roo: C


@dataclass
class HOP:
    """Test dataclass for parsing."""

    i: int = 789
    b: C = field(default_factory=C)


@dataclass
class BIM:
    """Test dataclass for parsing."""

    i: int = 159
    hop: HOP = field(default_factory=HOP)


@dataclass
class A2:
    """Test dataclass for parsing."""

    a: int = 56
    roo: C = field(default_factory=C)
    bim: BIM = field(default_factory=BIM)


def test_parse_arguments():
    """Test the parsing of command line arguments and config file arguments."""
    pars: Parsley[A2] = create_parsley(
        args_dataclass_name=A2, should_parse_command_line_arguments=False
    )
    a2 = pars.parse_arguments(extra_args=None)
    assert a2 == A2(
        a=56,
        roo=C(x=4578, y="uio"),
        bim=BIM(i=159, hop=HOP(i=789, b=C(x=4578, y="uio"))),
    )

    a2 = pars.parse_arguments(config_file_path="tests_parsley/yaml_files/test_a2.yaml")
    assert a2 == A2(
        a=42, roo=C(x=10, y="hello"), bim=BIM(i=42, hop=HOP(i=42, b=C(x=10, y="hello")))
    )


if __name__ == "__main__":
    test_parse_arguments()
