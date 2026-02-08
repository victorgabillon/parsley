"""Utility functions for various operations."""

import argparse
from enum import Enum
import types  # Import types to handle new-style Union
from collections.abc import Mapping
from dataclasses import (
    MISSING,
    field,
    fields,
    is_dataclass,
    make_dataclass,
)
from types import UnionType
from typing import (
    Any,
    ClassVar,
    List,
    Protocol,
    Tuple,
    Type,
    Union,
    cast,
    get_args,
    get_origin,
    get_type_hints,
    Literal,
)

from dacite import Config, UnionMatchError, from_dict

from parsley_coco.sentinels import is_notfilled, notfilled

from parsley_coco.logger import get_parsley_logger

parsley_logger = get_parsley_logger()


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


    hints = get_type_hints(data_class)
    for field_, field_type in hints.items():
        type_str = get_pretty_type(field_type)
        # Include default value if available
        if field_.default is not MISSING:
            default_str = f" = {field_.default!r}"
        elif field_.default_factory is not MISSING:
            default_str = " = <factory>"
        else:
            default_str = ""

        print(f"{prefix}  - {field_.name}: {type_str}{default_str}")

        # Recurse into nested dataclasses
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

    if origin in {Union, types.UnionType}:
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

    # --- Literal shim ---
    if get_origin(data_class) is Literal:
        allowed = get_args(data_class)
        for literal_value in allowed:
            if data == literal_value:
                return cast(Any, data)
            if hasattr(literal_value, "value") and data == getattr(literal_value, "value"):
                return cast(Any, data)
            if (
                hasattr(data, "value")
                and hasattr(literal_value, "value")
                and data.value == literal_value.value
            ):
                return cast(Any, data)
        raise UnionMatchError(field_type=data_class, value=data)

    # --- IMPORTANT: handle Union targets BEFORE calling dacite.from_dict ---
    if get_origin(data_class) in {Union, types.UnionType}:
        union_types = get_args(data_class)
        errors = []
        for union_type in union_types:
            try:
                parsley_logger.debug("Trying to parse with union type: %r", union_type)
                parsed = from_dict_with_union_handling(union_type, data, config)
                return cast(Any, parsed)
            except Exception as inner_error:
                errors.append(f"Failed with {union_type}: {inner_error}")

        error_message = (
            f"Failed to parse data into any type of Union[{', '.join(str(t) for t in union_types)}].\n"
            + "\n".join(errors)
        )
        raise Exception(error_message) from None

    # --- Base cases for non-dataclass targets ---
    # When we probe Union branches, we may be asked to "parse" primitives like str/bool/int,
    # Enums, NoneType, Any, or your _NotFilled sentinel. These should not go through dacite.from_dict.

    # typing.Any accepts anything
    if data_class is Any:
        return cast(Any, data)

    # NoneType
    if data_class is type(None):
        if data is None:
            return cast(Any, None)
        raise UnionMatchError(field_type=data_class, value=data)

    # parsley sentinel
    if data_class is type(notfilled):  # _NotFilled class
        if is_notfilled(data):
            return cast(Any, data)
        raise UnionMatchError(field_type=data_class, value=data)

    # Enums (including StrEnum)
    try:
        if isinstance(data_class, type) and issubclass(data_class, Enum):
            if isinstance(data, data_class):
                return cast(Any, data)
            if isinstance(data, str):
                # interpret YAML string as Enum *value*
                return cast(Any, data_class(data))
            raise UnionMatchError(field_type=data_class, value=data)
    except TypeError:
        # data_class is not a class or not suitable for issubclass
        pass

    # Primitives / normal classes (str, bool, int, float, etc.)
    if isinstance(data_class, type) and not is_dataclass(data_class):
        if isinstance(data, data_class):
            return cast(Any, data)
        # Very conservative casting: only if it's a simple scalar and the cast works
        try:
            return cast(Any, data_class(data))
        except Exception:
            raise UnionMatchError(field_type=data_class, value=data)

    # --- Normal dacite parse ---
    try:
        return from_dict(data_class=data_class, data=data, config=config)

    except UnionMatchError as e:

        # Handle UnionMatchError
        parsley_logger.debug(
            "Handling UnionMatchError for %r with data %r", data_class, data
        )
        # --- IMPORTANT: handle Union targets *before* calling dacite.from_dict ---
        # dacite.from_dict may crash on PEP604 unions (A | B) on some Python versions.

        # If it's a dataclass, recursively handle nested fields
        if is_dataclass(data_class):
            parsley_logger.debug("Handling dataclass: %r", data_class.__name__)
            field_errors = []
            hints = get_type_hints(data_class)
            for field_, field_type in hints.items():

                parsley_logger.debug(
                    "Processing field: %r of type %r  Union: %r",
                    field_,
                    field_type,
                    get_origin(field_type) in {Union, types.UnionType},
                )
                if get_origin(field_type) in {
                    Union,
                    types.UnionType,
                }:  # Check for both old and new Union
                    if field_ not in data:
                        continue
                    # Extract types from the Union
                    union_types = get_args(field_type)
                    errors = []
                    matched = False
                    for union_type in union_types:
                        try:
                            # Try parsing with each type in the Union
                            parsley_logger.debug(
                                "Trying to parse with union type: %r", union_type
                            )
                            parsed = from_dict_with_union_handling(
                                union_type, data[field_], config
                            )
                            data[field_] = parsed
                            matched = True
                            break
                        except Exception as inner_error:
                            # Collect errors for debugging
                            errors.append(f"Failed with {union_type}: {inner_error}")

                    if not matched:
                        # If all attempts fail, raise a clean error message
                        error_message = f"Failed to parse data into any type of Union[{', '.join(str(t) for t in union_types)}].\n"
                        error_message += "\n".join(errors)
                        field_errors.append(error_message)

                # Check if the field_ is a nested dataclass
                elif is_dataclass(field_type):
                    try:
                        value = data[field_]
                        # Only re-parse if the value is a dict (raw data), not an already-parsed instance
                        if isinstance(value, Mapping):
                            parsley_logger.debug(
                                "Recursively parsing nested dataclass field_ '%r'",
                                field_,
                            )
                            data[field_] = from_dict_with_union_handling(
                                cast(type, field_type), dict(value), config
                            )
                    except Exception as inner_error:
                        field_errors.append(
                            f"Failed to parse nested dataclass field_ '{field_}': {inner_error}"
                        )
            if field_errors:
                raise Exception("\n".join(field_errors)) from None
            return from_dict(data_class=data_class, data=data, config=config)
        else:
            # Re-raise the original exception if it's not a Union or dataclass
            raise e
    except Exception as e:
        # Handle other exceptions
        parsley_logger.debug("An error occurred: %r", e)
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
        # Fallback if multiple types remain – assume str or raise
        return str
    return typ


# --- Helper to flatten dataclass fields ---
def flatten_fields(cls: Type[Any], prefix: str = "") -> dict[str, Any]:
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
    parser: argparse.ArgumentParser, cls: Type[Any]
) -> None:
    flat_fields = flatten_fields(cls)
    for name, f in flat_fields.items():
        parser.add_argument(
            f"--{name}",
            type=resolve_type(f.type),
            default=None,
            help=(
                f.metadata["description"]
                if "description" in f.metadata
                else "to be written in dataclass metadata"
            ),
        )


FieldTuple = Union[
    Tuple[str, Any], Tuple[str, Any, Any]  # (name, type)  # (name, type, field spec)
]


def extend_with_config(cls: Type[Any]) -> Type[Any]:
    # Extract existing fields
    original_fields: List[FieldTuple] = []

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
        + [("config_file_name", str, field(default=None))]
    )

    # Create a new dataclass dynamically

    return make_dataclass(cls.__name__ + "WithConfig", extended_fields, bases=(cls,))
