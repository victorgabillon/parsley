from dataclasses import is_dataclass
from typing import Any
from typing import ClassVar, Protocol
from typing import Union, get_origin, get_args


def unflatten(dictionary: dict[Any, Any]) -> dict[Any, Any]:
    result_dict: dict[Any, Any] = dict()
    for key, value in dictionary.items():
        parts = key.split(".")
        d = result_dict
        for part in parts[:-1]:
            if part not in d:
                d[part] = dict()
            d = d[part]
        d[parts[-1]] = value
    return result_dict


class IsDataclass(Protocol):
    """
    Protocol to represent a dataclass.

    This protocol is used to check if an object is a dataclass by checking
    for the presence of the `__dataclass_fields__` attribute.
    """

    __dataclass_fields__: ClassVar[dict[Any, Any]]


def remove_none(d: dict[str, Any]) -> dict[str, Any]:
    if isinstance(d, dict):
        return {k: remove_none(v) for k, v in d.items() if v is not None}
    elif isinstance(d, list):
        return [remove_none(item) for item in d]
    else:
        return d


def is_or_contains_dataclass(t: type) -> bool:
    """Check if a type is a dataclass or a Union including a dataclass."""
    if is_dataclass(t):
        return True
    if get_origin(t) is Union:
        return any(is_dataclass(arg) for arg in get_args(t))
    return False
