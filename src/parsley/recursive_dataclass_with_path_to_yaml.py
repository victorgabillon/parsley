"""Resolve a YAML file to a dataclass object with optional paths and overwrite fields."""

import logging
import os
import types
from dataclasses import Field, asdict, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, NoReturn, Protocol, Union, cast, get_args, get_origin

import dacite
import yaml
from dacite import DaciteError, UnionMatchError, from_dict

from parsley.alternative_dataclasses import (
    make_partial_dataclass_notfilled,
    make_partial_dataclass_with_optional_paths,
)
from parsley.logger import get_parsley_logger
from parsley.sentinels import is_notfilled, notfilled
from parsley.utils import (
    FieldUnionParsingError,
    UnionParsingError,
    IsDataclass,
    extract_union_types,
    from_dict_with_union_handling,
    is_or_contains_dataclass,
    merge_nested_dicts,
    remove_notfilled_values,
    resolve_type,
)

parsley_logger = get_parsley_logger()


parsley_logger.setLevel(logging.DEBUG)
for h in parsley_logger.handlers:
    h.setLevel(logging.DEBUG)


class _HasYamlFilePath(Protocol):
    def get_yaml_file_path(self) -> str:
        """Return the YAML file path for the configuration."""


class PackageRootRequiredError(ValueError):
    """Raised when a package root is required but not provided."""

    def __init__(self, path: str) -> None:
        """Initialize the error with the unresolved package path."""
        super().__init__(
            f"'package://' path used ({path}), but no package_root was provided."
        )


class YamlFileReadError(FileNotFoundError):
    """Raised when a YAML file cannot be read."""

    def __init__(self, yaml_path: str) -> None:
        """Initialize the error with the YAML path."""
        super().__init__(f"Could not read file: {yaml_path}")


class PathValueTypeError(TypeError):
    """Raised when a YAML path value is not a string."""

    def __init__(self, actual_type: type[Any]) -> None:
        """Initialize the error with the offending value type."""
        super().__init__(f"path_val must be a str, got {actual_type}")


class DataclassUnionResolutionError(LookupError):
    """Raised when a dataclass union cannot be resolved."""

    def __init__(self, field: Field[Any], value: Any) -> None:
        """Initialize the error with the field and value."""
        super().__init__(
            f"Could not resolve dataclass union for field {field} with value {value}"
        )


class MissingYamlPathProviderError(TypeError):
    """Raised when a YAML path provider object is missing the required method."""

    def __init__(self, field_name: str, actual_type: type[Any]) -> None:
        """Initialize the error with the field name and value type."""
        super().__init__(
            "Expected dataclass or object with get_yaml_file_path for field "
            f"{field_name}, got {actual_type}"
        )


class NotFilledYamlPathError(TypeError):
    """Raised when a notfilled value is used where a YAML path is required."""

    def __init__(self, field_name: str) -> None:
        """Initialize the error with the field name."""
        super().__init__(f"Field {field_name}: notfilled has no yaml path")


class YamlBackedUnionResolutionError(LookupError):
    """Raised when a YAML-backed union cannot be resolved."""

    def __init__(self, field: Field[Any], value: Any) -> None:
        """Initialize the error with the field and value."""
        super().__init__(
            f"Could not resolve YAML-backed union for field {field} with value {value}"
        )


class OverwriteValueTypeError(TypeError):
    """Raised when an overwrite value is not a dataclass."""

    def __init__(self, field_name: str, actual_type: type[Any]) -> None:
        """Initialize the error with the field name and value type."""
        super().__init__(
            f"overwrite_val must be a dataclass for field {field_name}, got {actual_type}"
        )


class OverwriteUnionResolutionError(LookupError):
    """Raised when an overwrite union cannot be resolved."""

    def __init__(self, field: Field[Any], value: Any) -> None:
        """Initialize the error with the field and value."""
        super().__init__(
            f"Could not resolve overwrite union for field {field} with value {value}"
        )


class MissingValueOrPathError(ValueError):
    """Raised when neither a value nor a YAML path is provided for a field."""

    def __init__(self, field_name: str) -> None:
        """Initialize the error with the field name."""
        super().__init__(
            f"Exactly one of '{field_name}' or '{field_name}_path_to_yaml_file' must be provided."
        )


def resolve_package_path(path: str | Path, package_root: str | None = None) -> str:
    """Replace 'package://' at the start of the path with the given package root.

    Args:
        path (str): The input path, possibly starting with 'package://'.
        package_root (Optional[str]): The base path to replace 'package://' with.

    Returns:
        str: The resolved path.

    Raises:
        ValueError: If path starts with 'package://' and package_root is None.

    """
    path = str(path)  # Ensure path is a string

    if path.startswith("package://"):
        if package_root is None:
            parsley_logger.debug(
                "Path starts with 'package://', but no package_root was provided."
            )
            raise PackageRootRequiredError(path)
        relative_path = path[len("package://") :]
        return os.path.join(package_root, relative_path)
    return path


def resolve_extended_dict_to_dict_allow_notfilled[TDataclass: IsDataclass](
    dicto: dict[str, Any],
    base_cls: type[TDataclass],
    raise_error_with_nones: bool = True,
    package_name: str | None = None,
) -> dict[str, Any]:
    """Resolve a YAML file to a dataclass object.

    Args:
        dicto (dict[str, Any]): Input dictionary to resolve.
        base_cls (Type[TDataclass]): The dataclass type to resolve to.
        raise_error_with_nones (bool): Whether to raise an error if None values are encountered.
        package_name (str | None): Optional package root name for resolving package paths.

    Returns:
        dict[str, Any]: The resolved dictionary.

    Raises:
        Exception: If the YAML file cannot be read.

    """
    if not dicto:
        return {}

    extended_cls = make_partial_dataclass_with_optional_paths(base_cls)

    extended_obj = from_dict_with_union_handling(
        data_class=extended_cls, data=dicto, config=dacite.Config(cast=[Enum])
    )

    resolved_data: dict[str, Any] = resolve_extended_object_to_dict(
        extended_obj=extended_obj,
        base_cls=make_partial_dataclass_notfilled(base_cls),
        raise_error_with_notfilled=raise_error_with_nones,
        package_name=package_name,
    )

    return resolved_data


def resolve_dict_to_base_dataclass[TDataclass: IsDataclass](
    dicto: dict[str, Any],
    base_cls: type[TDataclass],
    raise_error_with_nones: bool = True,
    package_name: str | None = None,
    level_of_recursion: int = 0,
) -> TDataclass:
    """Resolve a YAML file to a dataclass object.

    Args:
        dicto (dict[str, Any]): Input dictionary to resolve.
        base_cls (Type[TDataclass]): The dataclass type to resolve to.
        raise_error_with_nones (bool): Whether to raise an error if None values are encountered.
        package_name (str | None): Optional package root name for resolving package paths.
        level_of_recursion (int): Current recursion depth for logging.

    Returns:
        TDataclass: The resolved dataclass object.

    Raises:
        Exception: If the YAML file cannot be read.

    """
    extended_cls = make_partial_dataclass_with_optional_paths(base_cls)

    extended_obj = from_dict_with_union_handling(
        data_class=extended_cls, data=dicto, config=dacite.Config(cast=[Enum])
    )
    resolve_extended_object_: TDataclass = resolve_extended_object(
        extended_obj,
        base_cls,
        raise_error_with_nones=raise_error_with_nones,
        package_name=package_name,
        level_of_recursion=level_of_recursion,
    )

    return resolve_extended_object_


def resolve_yaml_file_to_dict_allow_notfilled[TDataclass: IsDataclass](
    yaml_path: str,
    base_cls: type[TDataclass],
    raise_error_with_nones: bool = True,
    package_name: str | None = None,
) -> dict[str, Any]:
    """Resolve a YAML file to a dataclass object.

    Args:
        yaml_path (str): The path to the YAML file.
        base_cls (Type[TDataclass]): The dataclass type to resolve to.
        raise_error_with_nones (bool): Whether to raise an error if None values are encountered.
        package_name (str | None): Optional package root name for resolving package paths.

    Returns:
        TDataclass: The resolved dataclass object.

    Raises:
        Exception: If the YAML file cannot be read.

    """
    yaml_path_resolved = resolve_package_path(path=yaml_path, package_root=package_name)
    try:
        with open(yaml_path_resolved, encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
    except OSError as exc:
        raise YamlFileReadError(yaml_path) from exc

    return resolve_extended_dict_to_dict_allow_notfilled(
        dicto=yaml_data,
        base_cls=base_cls,
        raise_error_with_nones=raise_error_with_nones,
        package_name=package_name,
    )


def resolve_yaml_file_to_base_dataclass[TDataclass: IsDataclass](
    yaml_path: str,
    base_cls: type[TDataclass],
    raise_error_with_nones: bool = True,
    package_name: str | None = None,
    level_of_recursion: int = 0,
) -> TDataclass:
    """Resolve a YAML file to a dataclass object.

    Args:
        yaml_path (str): The path to the YAML file.
        base_cls (Type[TDataclass]): The dataclass type to resolve to.
        raise_error_with_nones (bool): Whether to raise an error if None values are encountered.
        package_name (str | None): Optional package root name for resolving package paths.
        level_of_recursion (int): Current recursion depth for logging.

    Returns:
        TDataclass: The resolved dataclass object.

    Raises:
        Exception: If the YAML file cannot be read.

    """
    indent: str = " " * level_of_recursion * 2
    try:
        yaml_path_resolved = resolve_package_path(
            path=yaml_path, package_root=package_name
        )
    except ValueError:
        parsley_logger.debug(
            "%s%s: Could not resolve package path: %s",
            indent,
            level_of_recursion,
            yaml_path,
        )
        raise
    try:
        with open(yaml_path_resolved, encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
    except OSError as exc:
        parsley_logger.debug(
            "%s%s: Could not read file: %s", indent, level_of_recursion, yaml_path
        )
        raise YamlFileReadError(yaml_path) from exc

    return resolve_dict_to_base_dataclass(
        dicto=yaml_data,
        base_cls=base_cls,
        raise_error_with_nones=raise_error_with_nones,
        package_name=package_name,
        level_of_recursion=level_of_recursion,
    )


def extract_dataclass_type(t: Any) -> type | None:
    """If t is a dataclass or Union containing one, return the dataclass type."""
    if is_dataclass(t):
        assert isinstance(t, type)
        return t
    origin = get_origin(t)
    # Handle typing.Union and PEP 604 (Python 3.10+) unions
    if origin is Union or isinstance(t, types.UnionType):
        for arg in get_args(t):
            if isinstance(arg, type) and is_dataclass(arg):
                return arg
    return None


def resolve_extended_object_to_dict[TDataclass: IsDataclass](
    extended_obj: IsDataclass,
    base_cls: type[TDataclass],
    raise_error_with_notfilled: bool = True,
    history_of_recursive_fields: list[str] | None = None,
    package_name: str | None = None,
    level_of_recursion: int = 0,
) -> dict[str, Any]:
    """Resolve an extended object to a dictionary.

    Args:
        extended_obj (IsDataclass): The extended object to resolve.
        base_cls (Type[TDataclass]): The base class type to resolve to.
        raise_error_with_notfilled (bool): Whether to raise an error if notfilled values are encountered.
        history_of_recursive_fields (list[str] | None): Field ancestry for recursion tracking.
        package_name (str | None): Optional package root name for resolving package paths.
        level_of_recursion (int): Current recursion depth for logging.

    Returns:
        dict[str, Any]: The resolved dictionary.

    """
    # it looks like we do not allow any attribute to be a union of dataclassa and int for instance, think if desired in the long run
    # should we handle list and dict and tupl in a specific way in combination with dataclass, think about it? no use cas yet
    assert is_dataclass(extended_obj)
    resolved_data: dict[str, Any] = {}

    for field in fields(base_cls):
        resolved_data[field.name] = resolve_extended_object_to_dict_one_field(
            extended_obj=extended_obj,
            raise_error_with_notfilled=raise_error_with_notfilled,
            field=field,
            history_of_recursive_fields=history_of_recursive_fields,
            package_name=package_name,
            level_of_recursion=level_of_recursion,
        )

    return resolved_data


def resolve_extended_object_to_dict_one_field[TDataclass: IsDataclass](
    extended_obj: IsDataclass,
    field: Field[Any],
    raise_error_with_notfilled: bool = True,
    history_of_recursive_fields: list[str] | None = None,
    package_name: str | None = None,
    level_of_recursion: int = 0,
) -> Any:
    """Resolve one field from an extended object into a base value.

    Args:
        extended_obj (IsDataclass): The extended object to resolve.
        field (Field[Any]): Dataclass field being resolved.
        raise_error_with_notfilled (bool): Whether to raise on notfilled values.
        history_of_recursive_fields (list[str] | None): Field ancestry for recursion tracking.
        package_name (str | None): Optional package root name for resolving package paths.
        level_of_recursion (int): Current recursion depth for logging.

    Returns:
        Any: The resolved field value.

    """

    def _raise_notfilled_yaml_path(field_name: str) -> NoReturn:
        raise NotFilledYamlPathError(field_name)

    indent: str = " " * level_of_recursion * 2
    indent_plus_one: str = " " * (level_of_recursion + 1) * 2
    parsley_logger.debug("%s%s: Resolving %s", indent, level_of_recursion, field.name)

    base_field_type = field.type
    val = getattr(extended_obj, field.name, notfilled)
    path_val = getattr(extended_obj, f"{field.name}_path_to_yaml_file", notfilled)
    overwrite_val = getattr(extended_obj, f"{field.name}_overwrite", notfilled)

    value_base = not is_notfilled(val)
    value_base = (
        value_base and not is_dataclass(val) and not hasattr(val, "get_yaml_file_path")
    )

    # Dataclass (or union containing dataclass) handling
    if is_or_contains_dataclass(base_field_type) and not value_base:
        final_resolved_val: dict[str, Any] = {}

        resolved_val: dict[str, Any] | None = None
        overwrite_resolved_val: dict[str, Any] | None = None

        # CASE 1: Path to YAML file provided
        if not is_notfilled(path_val):
            if not isinstance(path_val, str):
                raise PathValueTypeError(type(path_val))

            parsley_logger.debug(
                "%s%s: Resolving %s from YAML file: %s",
                indent,
                level_of_recursion,
                field.name,
                path_val,
            )

            resolved_val = asdict(
                resolve_yaml_file_to_base_dataclass(
                    yaml_path=path_val,
                    base_cls=resolve_type(base_field_type),
                    raise_error_with_nones=raise_error_with_notfilled,
                    package_name=package_name,
                    level_of_recursion=level_of_recursion + 1,
                )
            )
            final_resolved_val = merge_nested_dicts(final_resolved_val, resolved_val)

        # CASE 2: Direct value provided
        if not is_notfilled(val):
            # 2a: direct nested dataclass provided
            if is_dataclass(val):
                dataclass_type_list = extract_union_types(base_field_type)

                for dataclass_type in dataclass_type_list:
                    try:
                        parsley_logger.debug(
                            "%s%s: Attempting %s dataclass %s",
                            indent_plus_one,
                            level_of_recursion + 1,
                            field.name,
                            dataclass_type,
                        )

                        new_history = (
                            [field.name]
                            if history_of_recursive_fields is None
                            else [*history_of_recursive_fields, field.name]
                        )

                        resolved_val_temp = resolve_extended_object_to_dict(
                            extended_obj=cast("IsDataclass", val),
                            base_cls=resolve_type(dataclass_type),
                            raise_error_with_notfilled=raise_error_with_notfilled,
                            history_of_recursive_fields=new_history,
                            package_name=package_name,
                            level_of_recursion=level_of_recursion + 1,
                        )

                        resolved_val_temp = remove_notfilled_values(resolved_val_temp)

                        _ = from_dict_with_union_handling(
                            data_class=dataclass_type,
                            data=resolved_val_temp,
                            config=dacite.Config(cast=[Enum]),
                        )

                        resolved_val = resolved_val_temp
                        parsley_logger.debug(
                            "%s%s: Success %s dataclass %s",
                            indent_plus_one,
                            level_of_recursion + 1,
                            field.name,
                            dataclass_type,
                        )
                        break  # first successful match wins
                    except (
                        DaciteError,
                        FieldUnionParsingError,
                        TypeError,
                        UnionMatchError,
                        UnionParsingError,
                        ValueError,
                    ):
                        parsley_logger.debug(
                            "%s%s: Fail %s dataclass %s",
                            indent_plus_one,
                            level_of_recursion + 1,
                            field.name,
                            dataclass_type,
                        )

                if resolved_val is None:
                    raise DataclassUnionResolutionError(field, val)

            # 2b: object with get_yaml_file_path provided
            else:
                # Narrow type: this must not be the notfilled sentinel, and must have method
                if not hasattr(val, "get_yaml_file_path"):
                    raise MissingYamlPathProviderError(field.name, type(val))

                dataclass_type_list = extract_union_types(base_field_type)
                for dataclass_type in dataclass_type_list:
                    if isinstance(dataclass_type, type) and is_dataclass(
                        dataclass_type
                    ):
                        try:
                            if val is notfilled:
                                _raise_notfilled_yaml_path(field.name)

                            provider = cast("_HasYamlFilePath", val)
                            data_class_resolved = resolve_yaml_file_to_base_dataclass(
                                yaml_path=provider.get_yaml_file_path(),
                                base_cls=resolve_type(dataclass_type),
                                raise_error_with_nones=raise_error_with_notfilled,
                                package_name=package_name,
                                level_of_recursion=level_of_recursion + 1,
                            )

                            resolved_val_temp = asdict(data_class_resolved)

                            _ = from_dict(
                                data_class=dataclass_type,
                                data=resolved_val_temp,
                            )

                            resolved_val = resolved_val_temp
                            break
                        except (
                            DaciteError,
                            TypeError,
                            UnionMatchError,
                            ValueError,
                        ):
                            parsley_logger.debug(
                                "fail %s yaml %s %s",
                                field.name,
                                dataclass_type,
                                val,
                            )

                if resolved_val is None:
                    raise YamlBackedUnionResolutionError(field, val)

            final_resolved_val = merge_nested_dicts(final_resolved_val, resolved_val)

        # CASE 3: Overwrite value provided
        if not is_notfilled(overwrite_val):
            if not is_dataclass(overwrite_val):
                raise OverwriteValueTypeError(field.name, type(overwrite_val))

            dataclass_type_list = extract_union_types(base_field_type)
            for dataclass_type in dataclass_type_list:
                try:
                    new_history = (
                        [field.name]
                        if history_of_recursive_fields is None
                        else [*history_of_recursive_fields, field.name]
                    )

                    overwrite_resolved_val_temp = resolve_extended_object_to_dict(
                        extended_obj=cast("IsDataclass", overwrite_val),
                        base_cls=make_partial_dataclass_notfilled(dataclass_type),
                        raise_error_with_notfilled=False,
                        history_of_recursive_fields=new_history,
                        package_name=package_name,
                        level_of_recursion=level_of_recursion + 1,
                    )

                    overwrite_resolved_val = remove_notfilled_values(
                        overwrite_resolved_val_temp
                    )
                    break
                except (
                    DaciteError,
                    FieldUnionParsingError,
                    TypeError,
                    UnionMatchError,
                    UnionParsingError,
                    ValueError,
                ):
                    parsley_logger.debug(
                        "fail %s overwrite %s %s",
                        field.name,
                        dataclass_type,
                        overwrite_val,
                    )

            if overwrite_resolved_val is None:
                raise OverwriteUnionResolutionError(field, overwrite_val)

            final_resolved_val = merge_nested_dicts(
                final_resolved_val, overwrite_resolved_val
            )

        # If neither provided, optionally error
        if val is notfilled and path_val is notfilled and raise_error_with_notfilled:
            raise MissingValueOrPathError(field.name)

        return final_resolved_val

    # Non-dataclass or base-case field
    assert not is_notfilled(val) or not raise_error_with_notfilled
    return val


def resolve_extended_object[TDataclass: IsDataclass](
    extended_obj: Any,
    base_cls: type[TDataclass],
    raise_error_with_nones: bool = True,
    package_name: str | None = None,
    level_of_recursion: int = 0,
) -> TDataclass:
    """Resolve an extended object to a dataclass object.

    Args:
        extended_obj (Any): The extended object to resolve.
        base_cls (Type[TDataclass]): The base class type to resolve to.
        raise_error_with_nones (bool): Whether to raise an error if None values are encountered.
        package_name (str | None): Optional package root name for resolving package paths.
        level_of_recursion (int): Current recursion depth for logging.

    Returns:
        TDataclass: The resolved dataclass object.

    """
    resolved_data: dict[str, Any] = resolve_extended_object_to_dict(
        extended_obj=extended_obj,
        base_cls=base_cls,
        raise_error_with_notfilled=raise_error_with_nones,
        package_name=package_name,
        level_of_recursion=level_of_recursion,
    )

    resolved_data = remove_notfilled_values(resolved_data)

    return from_dict_with_union_handling(
        data_class=base_cls, data=resolved_data, config=dacite.Config(cast=[Enum])
    )
