from dataclasses import is_dataclass
from typing import Any
from typing import ClassVar, Protocol
from typing import Union, get_origin, get_args
import types


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


def is_or_contains_dataclass(t: Any) -> bool:
    """Check if the input is a dataclass or a Union that includes a dataclass."""
    origin = get_origin(t)

    # Handle typing.Union and PEP 604 (Python 3.10+) unions
    if origin is Union or isinstance(t, types.UnionType):
        return any(is_or_contains_dataclass(arg) for arg in get_args(t))
    return isinstance(t, type) and is_dataclass(t)


def merge_nested_dicts(d1: dict[Any, Any], d2: dict[Any, Any]) -> dict[Any, Any]:
    result = d1.copy()
    for key, val in d2.items():
        if key in result and isinstance(result[key], dict) and isinstance(val, dict):
            result[key] = merge_nested_dicts(result[key], val)
        else:
            result[key] = val
    return result


def is_optional_type(t: Any) -> bool:
    """Check if the type `t` is a Union that includes None (i.e., Optional)."""
    origin = get_origin(t)
    args = get_args(t)

    return (origin is Union or isinstance(t, types.UnionType)) and type(None) in args
