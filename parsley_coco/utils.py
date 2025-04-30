""" Utility functions for various operations."""
from dataclasses import is_dataclass
from typing import Any
from typing import ClassVar, Protocol
from typing import Union, get_origin, get_args
import types


def unflatten(dictionary: dict[Any, Any]) -> dict[Any, Any]:
    """Convert a flattened dictionary into a nested dictionary.
    Args:
        dictionary (dict): A dictionary with keys that are dot-separated strings.
    Returns:
        dict: A nested dictionary.
    """
    result_dict: dict[Any, Any] = {}
    for key, value in dictionary.items():
        parts = key.split(".")
        d = result_dict
        for part in parts[:-1]:
            if part not in d:
                d[part] = {}
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
    """ Recursively remove keys with None values from a dictionary.
    Args:
        d (dict): The input dictionary.
    Returns:
        dict: A new dictionary with None values removed.
    """
    result_ :dict = {}
    if isinstance(d, dict):
        result_ = {k: remove_none(v) for k, v in d.items() if v is not None}
    elif isinstance(d, list):
        result_ = [remove_none(item) for item in d]
    else:
        result_ = d
    return result_

def is_or_contains_dataclass(t: Any) -> bool:
    """Check if the input is a dataclass or a Union that includes a dataclass."""
    origin = get_origin(t)

    # Handle typing.Union and PEP 604 (Python 3.10+) unions
    if origin is Union or isinstance(t, types.UnionType):
        return any(is_or_contains_dataclass(arg) for arg in get_args(t))
    return isinstance(t, type) and is_dataclass(t)


def merge_nested_dicts(d1: dict[Any, Any], d2: dict[Any, Any]) -> dict[Any, Any]:
    """Recursively merge two nested dictionaries.
    Args:
        d1 (dict): The first dictionary.
        d2 (dict): The second dictionary.
    Returns:
        dict: A new dictionary that is the result of merging d1 and d2.
    """
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
