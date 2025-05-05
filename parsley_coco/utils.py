"""Utility functions for various operations."""

import types  # Import types to handle new-style Union
from dataclasses import fields
from dataclasses import is_dataclass
from types import UnionType
from typing import Any, Type, Union, get_args, get_origin
from typing import ClassVar, Protocol
from typing import get_type_hints

from dacite import from_dict, Config, UnionMatchError


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
    """Recursively remove keys with None values from a dictionary.
    Args:
        d (dict): The input dictionary.
    Returns:
        dict: A new dictionary with None values removed.
    """
    result_: dict[str, Any] = {}
    if isinstance(d, dict):
        result_ = {k: remove_none(v) for k, v in d.items() if v is not None}
    elif isinstance(d, list):
        result_ = [remove_none(item) for item in d]
    else:
        result_ = d
    return result_


def is_or_contains_dataclass(tp: Any) -> bool:
    origin = get_origin(tp)
    args = get_args(tp)

    if is_dataclass(tp):
        return True

    if origin in (Union, UnionType):
        return any(is_or_contains_dataclass(arg) for arg in args)

    if origin in (list, tuple, set, dict):
        return any(is_or_contains_dataclass(arg) for arg in args)

    return False


def extract_union_types(tp: Any) -> Union[Any, list[Any]]:
    origin = get_origin(tp)

    if origin in (Union, UnionType):
        return list(get_args(tp))

    return [tp]


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


def print_dataclass_schema(cls: Any, indent: int = 0, seen: Any = None) -> None:
    if seen is None:
        seen = set()

    prefix = "    " * indent

    if cls in seen:
        print(f"{prefix}{cls.__name__} (already seen)")
        return
    seen.add(cls)

    if not is_dataclass(cls):
        print(f"{prefix}{get_pretty_type(cls)} (not a dataclass)")
        return

    print(f"{prefix}{cls.__name__}:")
    hints = get_type_hints(cls)

    for field in fields(cls):
        field_type = hints.get(field.name, field.type)
        type_str = get_pretty_type(field_type)
        print(f"{prefix}  - {field.name}: {type_str}")

        # Recurse into all dataclass components in this field
        for sub_type in extract_dataclass_types(field_type):
            print_dataclass_schema(sub_type, indent + 1, seen)


def get_pretty_type(tp: Any) -> str:
    """Return a human-readable version of the type."""
    origin = get_origin(tp)
    args = get_args(tp)

    if origin is None:
        if isinstance(tp, type):
            return tp.__name__
        return str(tp)

    if origin is {Union, types.UnionType}:
        return " | ".join(get_pretty_type(arg) for arg in args)

    if hasattr(origin, "__name__"):
        return f"{origin.__name__}[{', '.join(get_pretty_type(arg) for arg in args)}]"
    return str(tp)


def extract_dataclass_types(tp: Any) -> Any:
    """Yield all dataclass types contained within the given type."""
    origin = get_origin(tp)
    args = get_args(tp)

    if origin is {Union, types.UnionType}:
        for arg in args:
            yield from extract_dataclass_types(arg)
    elif origin in (list, tuple, set, dict):
        for arg in args:
            yield from extract_dataclass_types(arg)
    elif is_dataclass(tp):
        yield tp


def from_dict_with_union_handling[Dataclass: IsDataclass](
    data_class: Type[Dataclass], data: dict[Any, Any], config: Config | None = None
) -> Dataclass:
    """
    Wrapper around dacite.from_dict to handle Union types more gracefully, including nested dictionaries.

    Args:
        data_class (Type[Any]): The target data class.
        data (dict): The dictionary to parse.
        config (Config, optional): dacite configuration.

    Returns:
        Any: An instance of the data class.

    Raises:
        Exception: If parsing fails for all types in the Union.
    """
    print_dataclass_schema(data_class)
    try:
        # Attempt to parse normally
        a = from_dict(data_class=data_class, data=data, config=config)
        return a
    except UnionMatchError as e:
        # Handle UnionMatchError
        print(f"Handling UnionMatchError for {data_class}")
        if get_origin(data_class) in {
            Union,
            types.UnionType,
        }:  # Check for both old and new Union
            union_types = get_args(data_class)  # Extract types from the Union
            errors = []
            for union_type in union_types:
                try:
                    # Try parsing with each type in the Union
                    print(f"Trying to parse with union type: {union_type}")
                    _ = from_dict_with_union_handling(union_type, data, config)
                except Exception as inner_error:
                    # Collect errors for debugging
                    errors.append(f"Failed with {union_type}: {inner_error}")

            # If all attempts fail, raise a clean error message
            error_message = f"Failed to parse data into any type of Union[{', '.join(str(t) for t in union_types)}].\n"
            error_message += "\n".join(errors)
            raise Exception(error_message) from None
        # If it's a dataclass, recursively handle nested fields
        elif is_dataclass(data_class):
            print(f"Handling dataclass: {data_class.__name__}")
            field_errors = []
            for field in data_class.__annotations__:
                field_type = data_class.__annotations__[field]
                print(
                    f"Processing field: {field} of type {field_type}, is"
                    f" Union: {get_origin(field_type) in {Union, types.UnionType}}"
                )
                if get_origin(field_type) in {
                    Union,
                    types.UnionType,
                }:  # Check for both old and new Union
                    # Extract types from the Union
                    union_types = get_args(field_type)
                    errors = []
                    for union_type in union_types:
                        try:
                            # Try parsing with each type in the Union
                            print(f"Trying to parse with union type: {union_type}")
                            _ = from_dict_with_union_handling(
                                union_type, data[field], config
                            )
                        except Exception as inner_error:
                            # Collect errors for debugging
                            errors.append(f"Failed with {union_type}: {inner_error}")

                    # If all attempts fail, raise a clean error message
                    error_message = f"Failed to parse data into any type of Union[{', '.join(str(t) for t in union_types)}].\n"
                    error_message += "\n".join(errors)

                # Check if the field is a nested dataclass
                elif is_dataclass(field_type):
                    try:
                        # Recursively parse the nested dataclass
                        print(f"Recursively parsing nested dataclass field '{field}'")
                        data[field] = from_dict_with_union_handling(
                            field_type, data[field], config
                        )
                    except Exception as inner_error:
                        field_errors.append(
                            f"Failed to parse nested dataclass field '{field}': {inner_error}"
                        )
            if field_errors:
                raise Exception("\n".join(field_errors)) from None
            else:
                raise e  # Re-raise if no specific Union handling was needed
        else:
            # Re-raise the original exception if it's not a Union or dataclass
            raise e
    except Exception as e:
        # Handle other exceptions
        print(f"An error occurred: {e}")
        raise Exception(f"An error occurred: {e}") from None


def remove_none_values(d: dict[Any, Any]) -> dict[Any, Any]:
    """Recursively remove keys with None values from a nested dictionary."""
    if not isinstance(d, dict):
        return d  # Leave non-dict values untouched

    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            nested = remove_none_values(v)
            if nested:  # Only keep non-empty dicts
                result[k] = nested
        elif v is not None:
            result[k] = v

    return result
