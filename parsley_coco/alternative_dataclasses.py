"""Alternative dataclass utilities for handling optional paths and overwriting
dataclass fields."""

import types
from dataclasses import field, fields, is_dataclass, make_dataclass, MISSING
from types import UnionType
from typing import (
    Any,
    Dict,
    Optional,
    Type,
    Union,
    Literal,
    get_type_hints,
    get_origin,
    get_args,
)
from typing import Callable
from typing import List, Tuple

from parsley_coco.utils import is_or_contains_dataclass, print_dataclass_schema
from parsley_coco.sentinels import notfilled, _NotFilled


_partial_cache: Dict[Type[Any], Type[Any]] = {}


def replace_nested_types(tp: Any, transform_fn: Callable[[Any], Any]) -> Any:
    """Recursively replace dataclasses nested inside a type."""
    origin = get_origin(tp)
    args = get_args(tp)

    # Skip Literal types
    if origin is Literal:
        return tp

    # Base case: if it's a dataclass type, transform it
    if is_dataclass(tp):
        return transform_fn(tp)

    # Handle Union (typing.Union or new-style A | B)
    if origin in (Union, UnionType):
        return Union[tuple(replace_nested_types(arg, transform_fn) for arg in args)]

    # Handle generic containers: List[X], Dict[K, V], etc.
    if origin:
        new_args = tuple(replace_nested_types(arg, transform_fn) for arg in args)
        return origin[new_args]

    return tp


def make_dataclass_with_optional_paths_and_overwrite(
    cls: Type[Any], _processed: Dict[Type[Any], Type[Any]] | None = None
) -> Type[Any]:
    """Create a dataclass with optional paths and overwrite fields.
    This function takes a dataclass and creates a new dataclass with
    additional fields for optional paths and overwrite values.
    Args:
        cls (Type[Any]): The dataclass to process.
        _processed (Dict[Type[Any], Type[Any]] | None): A cache of processed dataclasses.
    Returns:
        Type[Any]: The new dataclass with optional paths and overwrite fields.
    Raises:
        ValueError: If the provided class is not a dataclass.
    """
    assert is_dataclass(cls), f"{cls} must be a dataclass"

    if _processed is None:
        _processed = {}

    if cls in _processed:
        return _processed[cls]

    hints = get_type_hints(cls)
    required_fields: List[Tuple[str, Any, Any]] = []
    optional_fields: List[Tuple[str, Any, Any]] = []

    for f in fields(cls):
        original_type = hints[f.name]
        transformed_type = replace_nested_types(
            original_type,
            lambda subcls: make_dataclass_with_optional_paths_and_overwrite(
                subcls, _processed
            ),
        )

        if is_or_contains_dataclass(original_type):
            if all(f.name != existing[0] for existing in optional_fields):
                optional_fields.append(
                    (f.name, Optional[transformed_type], field(default=None))
                )
                optional_fields.append(
                    (f"{f.name}_path_to_yaml_file", Optional[str], field(default=None))
                )
                optional_fields.append(
                    (
                        f"{f.name}_overwrite",
                        Optional[transformed_type],
                        field(default=None),
                    )
                )
        else:
            if f.default is not MISSING:
                if all(f.name != existing[0] for existing in optional_fields):
                    optional_fields.append(
                        (f.name, transformed_type, field(default=f.default))
                    )
            elif f.default_factory is not MISSING:
                if all(f.name != existing[0] for existing in optional_fields):
                    optional_fields.append(
                        (
                            f.name,
                            transformed_type,
                            field(default_factory=f.default_factory),
                        )
                    )
            else:
                if all(f.name != existing[0] for existing in required_fields):
                    required_fields.append((f.name, transformed_type, field()))

    new_cls_name = cls.__name__ + "_WithOptionalPath"
    new_cls = make_dataclass(new_cls_name, required_fields + optional_fields)
    _processed[cls] = new_cls
    return new_cls


def transform_type_for_partial(tp: Any) -> Any:
    """Recursively transform types by replacing any dataclass with its partial version."""
    origin = get_origin(tp)
    args = get_args(tp)

    if origin is Literal:
        return Optional[tp]

    # Direct dataclass type
    if isinstance(tp, type) and is_dataclass(tp):
        return Optional[make_partial_dataclass(tp)]

    # Union[...] or A | B
    if origin in (Union, UnionType):
        new_args = []
        for arg in args:
            if isinstance(arg, type) and is_dataclass(arg):
                new_args.append(make_partial_dataclass(arg))
            else:
                new_args.append(arg)
        return Optional[Union[tuple(new_args)]]

    # Other types (List, Dict, etc.) — no recursion here unless needed
    return Optional[tp]


_partial_cache = {}


def make_partial_dataclass(cls: Type[Any]) -> Type[Any]:
    """Create a partial dataclass with all fields optional and defaulting to None, including nested dataclasses inside Unions."""
    if cls in _partial_cache:
        return _partial_cache[cls]

    if not is_dataclass(cls):
        raise ValueError(f"{cls} is not a dataclass")

    type_hints = get_type_hints(cls)
    partial_fields = []

    for f in fields(cls):
        field_type = type_hints[f.name]
        transformed_type = transform_type_for_partial(field_type)

        # Force all fields to default to None
        default_spec = field(default=None)

        partial_fields.append((f.name, transformed_type, default_spec))

    new_cls_name = f"Partial{cls.__name__}"
    partial_cls = make_dataclass(new_cls_name, partial_fields, kw_only=True)
    partial_cls.__module__ = cls.__module__

    _partial_cache[cls] = partial_cls
    return partial_cls


def transform_type_for_notfilled(tp: Any) -> Any:
    origin = get_origin(tp)
    args = get_args(tp)

    if origin is Literal:
        return Union[tp, _NotFilled]

    # If this is a dataclass type, return a Union of the partial version and notfilled
    if isinstance(tp, type) and is_dataclass(tp):
        return Union[make_partial_dataclass_notfilled(tp), _NotFilled]

    # If this is a Union, recurse on each arg and add _NotFilled to the mix
    if origin in (Union, UnionType):
        new_args = [transform_type_for_notfilled(arg) for arg in args]
        return Union[tuple(new_args + [_NotFilled])]

    # If this is a generic like List[X] or Dict[K, V], apply recursively to the args
    if origin:
        new_args = [transform_type_for_notfilled(arg) for arg in args]
        return origin[tuple(new_args)] | _NotFilled

    # Base case: primitive or unknown type — just allow Union[type, _NotFilled]
    return Union[tp, _NotFilled]


def make_partial_dataclass_notfilled(cls: Type[Any]) -> Type[Any]:
    """Create a partial dataclass where every field defaults to `notfilled`, recursively."""
    if cls in _partial_cache:
        return _partial_cache[cls]

    if not is_dataclass(cls):
        raise ValueError(f"{cls} is not a dataclass")

    type_hints = get_type_hints(cls)
    partial_fields = []

    for f in fields(cls):
        field_type = type_hints[f.name]
        transformed_type = transform_type_for_notfilled(field_type)

        # Default to `notfilled`
        default_spec = field(default=notfilled)

        partial_fields.append((f.name, transformed_type, default_spec))

    new_cls_name = f"Partial{cls.__name__}_NotFilled"
    partial_cls = make_dataclass(new_cls_name, partial_fields, kw_only=True)
    partial_cls.__module__ = cls.__module__

    _partial_cache[cls] = partial_cls
    return partial_cls


def make_partial_dataclass_with_optional_paths(cls: Type[Any]) -> Type[Any]:
    """Create a partial dataclass with optional paths from the given dataclass.
    This function combines the functionality of `make_partial_dataclass` and
    `make_dataclass_with_optional_paths_and_overwrite` to create a new dataclass
    that includes optional paths and overwrite fields.
    Args:
        cls (Type[Any]): The dataclass to create a partial version of.
    Returns:
        Type[Any]: The partial dataclass with optional paths.
    Raises:
        ValueError: If the provided class is not a dataclass.
    """

    optional_paths_class = make_dataclass_with_optional_paths_and_overwrite(cls=cls)

    partial_with_optional_paths_class = make_partial_dataclass_notfilled(
        cls=optional_paths_class
    )
    return partial_with_optional_paths_class
