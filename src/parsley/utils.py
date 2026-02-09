"""Utility functions for various operations."""

import argparse
import types  # Import types to handle new-style Union
from collections.abc import Callable, Mapping
from dataclasses import (
    MISSING,
    field,
    fields,
    is_dataclass,
    make_dataclass,
)
from enum import Enum
from types import UnionType
from typing import (
    Any,
    ClassVar,
    Literal,
    Protocol,
    TypeVar,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
)

from dacite import Config, UnionMatchError, from_dict

from parsley.logger import get_parsley_logger
from parsley.sentinels import is_notfilled, notfilled

parsley_logger = get_parsley_logger()


class UnionParsingError(Exception):
    """Raised when data cannot be parsed into any union member."""

    def __init__(self, union_types: tuple[Any, ...], errors: list[str]) -> None:
        super().__init__(
            "Failed to parse data into any type of Union["
            + ", ".join(str(t) for t in union_types)
            + "].\n"
            + "\n".join(errors)
        )


class FieldUnionParsingError(Exception):
    """Raised when one or more fields fail union parsing."""

    def __init__(self, field_errors: list[str]) -> None:
        super().__init__("\n".join(field_errors))


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
    """Protocol to represent a dataclass.

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


def extract_union_types(tp: Any) -> Any | list[Any]:
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
    """Print the schema of a dataclass."""
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

    hints = get_type_hints(cls)

    for f in fields(cls):
        field_type = hints.get(f.name, f.type)
        type_str = get_pretty_type(field_type)

        if f.default is not MISSING:
            default_str = f" = {f.default!r}"
        elif f.default_factory is not MISSING:
            default_str = " = <factory>"
        else:
            default_str = ""

        print(f"{prefix}  - {f.name}: {type_str}{default_str}")

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

    if origin in {Union, types.UnionType}:
        return " | ".join(get_pretty_type(arg) for arg in args)

    if hasattr(origin, "__name__"):
        return f"{origin.__name__}[{', '.join(get_pretty_type(arg) for arg in args)}]"
    return str(tp)


def extract_dataclass_types(tp: Any) -> Any:
    """Yield all dataclass types contained within the given type."""
    origin = get_origin(tp)
    args = get_args(tp)

    if origin in {Union, types.UnionType} or origin in (list, tuple, set, dict):
        for arg in args:
            yield from extract_dataclass_types(arg)
    elif is_dataclass(tp):
        yield tp


T = TypeVar("T")


def from_dict_with_union_handling[T](
    data_class: type[T], data: Any, config: Config | None = None
) -> T:
    # --- Literal shim ---
    if get_origin(data_class) is Literal:
        allowed = get_args(data_class)
        for literal_value in allowed:
            if data == literal_value:
                return cast("T", data)
            if hasattr(literal_value, "value") and data == literal_value.value:
                return cast("T", data)
            if (
                hasattr(data, "value")
                and hasattr(literal_value, "value")
                and data.value == literal_value.value
            ):
                return cast("T", data)
        raise UnionMatchError(field_type=data_class, value=data)

    # --- Handle Union targets BEFORE calling dacite.from_dict ---
    if get_origin(data_class) in {Union, types.UnionType}:
        union_types = get_args(data_class)
        errors: list[str] = []
        for union_type in union_types:
            try:
                parsed = from_dict_with_union_handling(
                    data_class=cast("Any", union_type), data=data, config=config
                )
                return cast("T", parsed)
            except Exception as inner_error:
                errors.append(f"Failed with {union_type}: {inner_error}")

        raise UnionParsingError(union_types, errors) from None

    # --- Base cases for non-dataclass targets ---

    if data_class is Any:
        return cast("T", data)

    if data_class is type(None):
        if data is None:
            return cast("T", cast("object", None))
        raise UnionMatchError(field_type=data_class, value=data)

    if data_class is type(notfilled):
        if is_notfilled(data):
            return cast("T", data)
        raise UnionMatchError(field_type=data_class, value=data)

    # Enums
    try:
        if isinstance(data_class, type) and issubclass(data_class, Enum):
            if isinstance(data, data_class):
                return data
            if isinstance(data, str):
                return data_class(data)
            raise UnionMatchError(field_type=data_class, value=data)
    except TypeError:
        pass

    # Primitives / normal classes
    if isinstance(data_class, type) and not is_dataclass(data_class):
        if isinstance(data, data_class):
            return cast("T", cast("object", data))
        try:
            ctor = cast("Callable[[Any], Any]", data_class)
            return cast("T", ctor(data))
        except Exception:
            raise UnionMatchError(field_type=data_class, value=data) from None

    # dacite.from_dict expects a mapping for "data"
    if not isinstance(data, Mapping):
        raise UnionMatchError(field_type=data_class, value=data)

    data_dict: dict[Any, Any] = dict(data)

    try:
        return cast(
            "T",
            from_dict(
                data_class=cast("Any", data_class), data=data_dict, config=config
            ),
        )

    except UnionMatchError:
        if is_dataclass(data_class):
            field_errors: list[str] = []
            hints = get_type_hints(data_class)

            for field_name, field_type in hints.items():
                if field_name not in data_dict:
                    continue

                if get_origin(field_type) in {Union, types.UnionType}:
                    union_types = get_args(field_type)
                    field_union_errors: list[str] = []
                    matched = False

                    for union_type in union_types:
                        try:
                            parsed = from_dict_with_union_handling(
                                data_class=cast("Any", union_type),
                                data=data_dict[field_name],
                                config=config,
                            )
                            data_dict[field_name] = parsed
                            matched = True
                            break
                        except Exception as inner_error:
                            field_union_errors.append(
                                f"Failed with {union_type}: {inner_error}"
                            )

                    if not matched:
                        field_errors.append(
                            f"Failed to parse field '{field_name}' into any type of "
                            f"Union[{', '.join(str(t) for t in union_types)}].\n"
                            + "\n".join(field_union_errors)
                        )

                elif is_dataclass(field_type):
                    try:
                        value = data_dict[field_name]
                        if isinstance(value, Mapping):
                            data_dict[field_name] = from_dict_with_union_handling(
                                data_class=cast("Any", field_type),
                                data=dict(value),
                                config=config,
                            )
                    except Exception as inner_error:
                        field_errors.append(
                            f"Failed to parse nested dataclass field '{field_name}': {inner_error}"
                        )

            if field_errors:
                raise FieldUnionParsingError(field_errors) from None

            return cast(
                "T",
                from_dict(
                    data_class=cast("Any", data_class), data=data_dict, config=config
                ),
            )

        raise


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


def remove_notfilled_values(d: dict[Any, Any]) -> dict[Any, Any]:
    """Recursively remove keys with None values from a nested dictionary."""
    if not isinstance(d, dict):
        return d  # Leave non-dict values untouched

    result = {}
    for k, v in d.items():
        if isinstance(v, dict):
            nested = remove_notfilled_values(v)
            if nested:  # Only keep non-empty dicts
                result[k] = nested
        elif not is_notfilled(v):
            result[k] = v
    return result


def resolve_type(typ: Any) -> Any:
    origin = get_origin(typ)

    if origin in (Union, UnionType):
        args = [
            arg for arg in get_args(typ) if arg not in (type(None), type(notfilled))
        ]
        if len(args) == 1:
            return args[0]
        # Fallback if multiple types remain - assume str or raise
        return str
    return typ


# --- Helper to flatten dataclass fields ---
def flatten_fields(cls: type[Any], prefix: str = "") -> dict[str, Any]:
    flat_fields = {}
    for f in fields(cls):
        field_type = f.type
        full_name = f"{prefix}{f.name}" if prefix else f.name
        if is_or_contains_dataclass(field_type):
            for sub_type in extract_dataclass_types(field_type):
                flat_fields.update(flatten_fields(sub_type, prefix=full_name + "."))
        else:
            flat_fields[full_name] = f
    return flat_fields


# --- Add argparse arguments from flat fields ---
def add_arguments_from_dataclass(
    parser: argparse.ArgumentParser, cls: type[Any]
) -> None:
    flat_fields = flatten_fields(cls)
    for name, f in flat_fields.items():
        parser.add_argument(
            f"--{name}",
            type=resolve_type(f.type),
            default=None,
            help=(f.metadata.get("description", "to be written in dataclass metadata")),
        )


FieldTuple = (
    tuple[str, Any] | tuple[str, Any, Any]  # (name, type)  # (name, type, field spec)
)


def extend_with_config(cls: type[Any]) -> type[Any]:
    # Extract existing fields
    original_fields: list[FieldTuple] = []

    for f in fields(cls):
        if f.default is not MISSING or f.default_factory is not MISSING:
            original_fields.append(
                (
                    f.name,
                    f.type,
                    (
                        field(default=f.default)
                        if f.default is not MISSING
                        else field(default_factory=f.default_factory)
                    ),
                )
            )
        else:
            original_fields.append((f.name, f.type))  # non-default

    # Add the new one
    non_default_fields = [f for f in original_fields if len(f) == 2]
    default_fields = [f for f in original_fields if len(f) == 3]
    extended_fields = (
        non_default_fields
        + default_fields
        + [("config_file_name", str | None, field(default=None))]
    )

    # Create a new dataclass dynamically

    return make_dataclass(cls.__name__ + "WithConfig", extended_fields, bases=(cls,))
