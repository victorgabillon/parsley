
from dataclasses import dataclass
import enum
from enum import Enum
from typing import Literal, Union

from dacite import Config

from parsley_coco.utils import from_dict_with_union_handling


StrEnum = getattr(enum, "StrEnum", None)


if StrEnum is None:

    class Kind(str, Enum):
        A = "A"
        B = "B"
else:

    class Kind(StrEnum):
        A = "A"
        B = "B"


@dataclass
class UsesLiteralEnumMember:
    kind: Union[Literal[Kind.A], Literal[Kind.B]]
    x: int


@dataclass
class OptionA:
    discriminator: Literal["A"]
    value: int


@dataclass
class OptionB:
    discriminator: Literal["B"]
    name: str


def test_literal_enum_member_accepts_string_value() -> None:
    cfg = Config(cast=[Enum])
    obj = from_dict_with_union_handling(
        UsesLiteralEnumMember, {"kind": "A", "x": 1}, config=cfg
    )
    assert obj.kind == "A"
    assert obj.x == 1


def test_literal_enum_member_rejects_unknown_string() -> None:
    cfg = Config(cast=[Enum])
    try:
        from_dict_with_union_handling(
            UsesLiteralEnumMember, {"kind": "C", "x": 1}, config=cfg
        )
    except Exception as exc:
        assert "Failed to parse" in str(exc) or "Union" in str(exc)
    else:
        raise AssertionError("Expected parsing to fail for unknown Literal value")


def test_union_selection_uses_discriminator() -> None:
    cfg = Config(cast=[Enum])
    obj = from_dict_with_union_handling(
        OptionA | OptionB, {"discriminator": "B", "name": "choice"}, config=cfg
    )
    assert isinstance(obj, OptionB)
    assert obj.name == "choice"


if __name__ == "__main__":
    test_literal_enum_member_accepts_string_value()
    test_literal_enum_member_rejects_unknown_string()
    test_union_selection_uses_discriminator()
    print("All tests passed.")