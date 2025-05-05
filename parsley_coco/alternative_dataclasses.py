"""Alternative dataclass utilities for handling optional paths and overwriting
dataclass fields."""

from dataclasses import fields, field, make_dataclass, is_dataclass, MISSING
from types import UnionType
from typing import Any, Callable, Union, get_origin, get_args
from typing import Dict, List, Optional, Tuple, Type, get_type_hints

from parsley_coco.utils import is_or_contains_dataclass

_partial_cache: Dict[Type[Any], Type[Any]] = {}


def replace_nested_types(tp: Any, transform_fn: Callable[[Any], Any]) -> Any:
    """Recursively replace dataclasses nested inside a type."""
    origin = get_origin(tp)
    args = get_args(tp)

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
            optional_fields.append(
                (f.name, Optional[transformed_type], field(default=None))
            )
            optional_fields.append(
                (f"{f.name}_path_to_yaml_file", Optional[str], field(default=None))
            )
            optional_fields.append(
                (f"{f.name}_overwrite", Optional[transformed_type], field(default=None))
            )
        else:
            if f.default is not MISSING:
                optional_fields.append(
                    (f.name, transformed_type, field(default=f.default))
                )
            elif f.default_factory is not MISSING:
                optional_fields.append(
                    (f.name, transformed_type, field(default_factory=f.default_factory))
                )
            else:
                required_fields.append((f.name, transformed_type, field()))

    new_cls_name = cls.__name__ + "_WithOptionalPath"
    new_cls = make_dataclass(new_cls_name, required_fields + optional_fields)
    _processed[cls] = new_cls
    return new_cls


def make_partial_dataclass(cls: Type[Any]) -> Type[Any]:
    """Create a partial dataclass from the given dataclass.
    A partial dataclass allows for optional fields, making it easier to
    work with incomplete data.
    Args:
        cls (Type[Any]): The dataclass to create a partial version of.
    Returns:
        Type[Any]: The partial dataclass.
    Raises:
        ValueError: If the provided class is not a dataclass.
    """
    if cls in _partial_cache:
        return _partial_cache[cls]

    if not is_dataclass(cls):
        raise ValueError(f"{cls} is not a dataclass")

    type_hints = get_type_hints(cls)
    partial_fields = []

    for field_ in fields(cls):
        field_type = type_hints[field_.name]

        # If it's a nested dataclass, recurse
        if is_dataclass(field_type):
            assert isinstance(field_type, type)
            partial_type = make_partial_dataclass(field_type)
        else:
            partial_type = field_type

        # Make the field optional
        partial_fields.append(
            (
                field_.name,
                Optional[partial_type],
                field_.default if field_.default != field_.default_factory else None,
            )
        )

    # Create the new Partial dataclass
    partial_cls_name = f"Partial{cls.__name__}"

    annotations = {name: typ for name, typ, *_ in partial_fields}
    partial_cls = make_dataclass(
        partial_cls_name, partial_fields, namespace={"__annotations__": annotations}
    )

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
    partial_with_optional_paths_class = make_partial_dataclass(cls=optional_paths_class)
    return partial_with_optional_paths_class
