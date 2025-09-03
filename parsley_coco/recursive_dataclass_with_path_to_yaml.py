"""Resolve a YAML file to a dataclass object with optional paths and overwrite fields."""

import os
import types
from dataclasses import Field, asdict, fields, is_dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Type, Union, cast, get_args, get_origin
import logging

import dacite
import yaml
from dacite import from_dict

from parsley_coco.alternative_dataclasses import (
    make_partial_dataclass_notfilled,
    make_partial_dataclass_with_optional_paths,
)
from parsley_coco.logger import get_parsley_logger
from parsley_coco.sentinels import is_notfilled, notfilled
from parsley_coco.utils import (
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


def resolve_package_path(
    path: Union[str, Path], package_root: Optional[str] = None
) -> str:
    """
    Replace 'package://' at the start of the path with the given package root.

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
            raise ValueError(
                f"'package://' path used ({path}), but no package_root was provided."
            )
        relative_path = path[len("package://") :]
        return os.path.join(package_root, relative_path)
    return path


def resolve_extended_dict_to_dict_allow_notfilled[T_Dataclass: IsDataclass](
    dicto: dict[str, Any],
    base_cls: Type[T_Dataclass],
    raise_error_with_nones: bool = True,
    package_name: str | None = None,
) -> dict[str, Any]:
    """Resolve a YAML file to a dataclass object.
    Args:
        yaml_path (str): The path to the YAML file.
        base_cls (Type[T_Dataclass]): The dataclass type to resolve to.
        raise_error_with_nones (bool): Whether to raise an error if None values are encountered.
    Returns:
        T_Dataclass: The resolved dataclass object.
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


def resolve_dict_to_base_dataclass[T_Dataclass: IsDataclass](
    dicto: dict[str, Any],
    base_cls: Type[T_Dataclass],
    raise_error_with_nones: bool = True,
    package_name: str | None = None,
    level_of_recursion: int = 0,
) -> T_Dataclass:
    """Resolve a YAML file to a dataclass object.
    Args:
        yaml_path (str): The path to the YAML file.
        base_cls (Type[T_Dataclass]): The dataclass type to resolve to.
        raise_error_with_nones (bool): Whether to raise an error if None values are encountered.
    Returns:
        T_Dataclass: The resolved dataclass object.
    Raises:
        Exception: If the YAML file cannot be read.
    """

    extended_cls = make_partial_dataclass_with_optional_paths(base_cls)

    extended_obj = from_dict_with_union_handling(
        data_class=extended_cls, data=dicto, config=dacite.Config(cast=[Enum])
    )
    resolve_extended_object_ = resolve_extended_object(
        extended_obj,
        base_cls,
        raise_error_with_nones=raise_error_with_nones,
        package_name=package_name,
        level_of_recursion=level_of_recursion,
    )

    return resolve_extended_object_


def resolve_yaml_file_to_dict_allow_notfilled[T_Dataclass: IsDataclass](
    yaml_path: str,
    base_cls: Type[T_Dataclass],
    raise_error_with_nones: bool = True,
    package_name: str | None = None,
) -> dict[str, Any]:
    """Resolve a YAML file to a dataclass object.
    Args:
        yaml_path (str): The path to the YAML file.
        base_cls (Type[T_Dataclass]): The dataclass type to resolve to.
        raise_error_with_nones (bool): Whether to raise an error if None values are encountered.
    Returns:
        T_Dataclass: The resolved dataclass object.
    Raises:
        Exception: If the YAML file cannot be read.
    """

    yaml_path_resolved = resolve_package_path(path=yaml_path, package_root=package_name)
    try:
        with open(yaml_path_resolved, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
    except IOError as exc:
        raise FileNotFoundError(f"Could not read file: {yaml_path}") from exc

    return resolve_extended_dict_to_dict_allow_notfilled(
        dicto=yaml_data,
        base_cls=base_cls,
        raise_error_with_nones=raise_error_with_nones,
        package_name=package_name,
    )


def resolve_yaml_file_to_base_dataclass[T_Dataclass: IsDataclass](
    yaml_path: str,
    base_cls: Type[T_Dataclass],
    raise_error_with_nones: bool = True,
    package_name: str | None = None,
    level_of_recursion: int = 0,
) -> T_Dataclass:
    """Resolve a YAML file to a dataclass object.
    Args:
        yaml_path (str): The path to the YAML file.
        base_cls (Type[T_Dataclass]): The dataclass type to resolve to.
        raise_error_with_nones (bool): Whether to raise an error if None values are encountered.
    Returns:
        T_Dataclass: The resolved dataclass object.
    Raises:
        Exception: If the YAML file cannot be read.
    """
    indent: str = " " * level_of_recursion * 2
    try:
        yaml_path_resolved = resolve_package_path(
            path=yaml_path, package_root=package_name
        )
    except ValueError as exc:
        parsley_logger.debug(
            "%s%s: Could not resolve package path: %s",
            indent,
            level_of_recursion,
            yaml_path,
        )
        raise exc
    try:
        with open(yaml_path_resolved, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
    except IOError as exc:
        parsley_logger.debug(
            "%s%s: Could not read file: %s", indent, level_of_recursion, yaml_path
        )
        raise FileNotFoundError(f"Could not read file: {yaml_path}") from exc

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


def resolve_extended_object_to_dict[T_Dataclass: IsDataclass](
    extended_obj: IsDataclass,
    base_cls: Type[T_Dataclass],
    raise_error_with_notfilled: bool = True,
    history_of_recursive_fields: list[str] | None = None,
    package_name: str | None = None,
    level_of_recursion: int = 0,
) -> dict[str, Any]:
    """Resolve an extended object to a dictionary.
    Args:
        extended_obj (IsDataclass): The extended object to resolve.
        base_cls (Type[T_Dataclass]): The base class type to resolve to.
        raise_error_with_nones (bool): Whether to raise an error if None values are encountered.
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
            base_cls=base_cls,
            raise_error_with_notfilled=raise_error_with_notfilled,
            field=field,
            history_of_recursive_fields=history_of_recursive_fields,
            package_name=package_name,
            level_of_recursion=level_of_recursion,
        )

    return resolved_data


def resolve_extended_object_to_dict_one_field[T_Dataclass: IsDataclass](
    extended_obj: IsDataclass,
    base_cls: Type[T_Dataclass],
    field: Field[Any],
    raise_error_with_notfilled: bool = True,
    history_of_recursive_fields: list[str] | None = None,
    package_name: str | None = None,
    level_of_recursion: int = 0,
) -> Any:
    """Resolve an extended object to a dictionary.

    Raises:
        NameError: If the field name is not found in the extended object.
        NameError: If the field type is not found in the extended object.
        ValueError: If the field value is not valid.
    """

    result_val: Any
    indent: str = " " * level_of_recursion * 2
    indent_plus_one: str = " " * (level_of_recursion + 1) * 2
    parsley_logger.debug("%s%s: Resolving  %s", indent, level_of_recursion, field.name)
    base_field_type = field.type
    val = getattr(extended_obj, field.name, notfilled)
    path_val = getattr(extended_obj, f"{field.name}_path_to_yaml_file", notfilled)
    overwrite_val = getattr(extended_obj, f"{field.name}_overwrite", notfilled)

    # assert isinstance(base_field_type, type)
    value_base: bool = not is_notfilled(val)
    value_base = (
        value_base and not is_dataclass(val) and not hasattr(val, "get_yaml_file_path")
    )

    if is_or_contains_dataclass(base_field_type) and not value_base:
        # assert dataclass_type is not None

        final_resolved_val: dict[str, Any] = {}

        ###### CASE 1: Path to YAML file provided
        if not is_notfilled(path_val):
            assert isinstance(path_val, str), (
                f"path_val must be a str, got {type(path_val)}"
            )
            parsley_logger.debug(
                "%s%s: AAAAAtempt   %s from YAML file: %s",
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
            parsley_logger.debug(
                "%s%s: BBBBAAAAAtempt   %s from YAML file: %s",
                indent,
                level_of_recursion,
                field.name,
                path_val,
            )
            final_resolved_val = merge_nested_dicts(final_resolved_val, resolved_val)
            parsley_logger.debug(
                "%s%s: Resolved   %s from YAML file: %s",
                indent,
                level_of_recursion,
                field.name,
                path_val,
            )

        ###### CASE 2: Direct value provided
        if not is_notfilled(val):
            if is_dataclass(val):
                dataclass_type_list = extract_union_types(base_field_type)

                for dataclass_type in dataclass_type_list:
                    try:
                        parsley_logger.debug(
                            "%s%s: Attempting %s dataclass %s %s",
                            indent_plus_one,
                            level_of_recursion + 1,
                            field.name,
                            dataclass_type,
                            val,
                        )
                        if history_of_recursive_fields is None:
                            new_history__of_recursive_fields = [field.name]
                        else:
                            new_history__of_recursive_fields = (
                                history_of_recursive_fields + [field.name]
                            )

                        resolved_val_temp = resolve_extended_object_to_dict(
                            extended_obj=cast(IsDataclass, val),
                            base_cls=resolve_type(dataclass_type),
                            raise_error_with_notfilled=raise_error_with_notfilled,
                            history_of_recursive_fields=new_history__of_recursive_fields,
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
                            "%s%s: Success    %s dataclass %s",
                            indent_plus_one,
                            level_of_recursion + 1,
                            field.name,
                            dataclass_type,
                        )

                    except Exception as exc:
                        # TODO investigate why we can not at the moment use the (TypeError, dacite.exceptions.UnionMatchError) instead of Exception atm.
                        # problem then encoutnered when doing python chipiron/scripts/main_chipiron.py --script_name one_match
                        # where the error raised is Exception : An error occurred: wrong value type for field "type" - should be "Literal" instead of value "neural_network" of type "str" ,type: <class 'Exception'>
                        # so as it is of type Exception we need to catch it as is. Maybe lets try to generate a more pecific error
                        # at least generate a test that recreates this issue within parsley coco and not in chipiron
                        # except (TypeError, dacite.exceptions.UnionMatchError):

                        print(f"Exception : {exc} ,type: {type(exc)}")

                        parsley_logger.debug(
                            "%s%s: Fail       %s dataclass %s",
                            indent_plus_one,
                            level_of_recursion + 1,
                            field.name,
                            dataclass_type,
                        )
                try:
                    resolved_val
                    parsley_logger.debug(
                        "%s%s: Resolved   %s: %s",
                        indent,
                        level_of_recursion,
                        field.name,
                        resolved_val,
                    )
                except NameError as exc:
                    print(
                        f"Variable (print) resolved_val is not defined in field {field} {val}"
                    )
                    import traceback

                    traceback.print_exc()  # <-- This prints the full traceback
                    raise NameError(
                        f"Variable resolved_val is not defined in field {field} with value {val}"
                    ) from exc

                assert resolved_val is not None, (
                    f"resolved_val is None in field {field}"
                )
            else:  # Non-dataclass value in a Union — allowed
                assert hasattr(val, "get_yaml_file_path")
                dataclass_type_list = extract_union_types(base_field_type)
                for dataclass_type in dataclass_type_list:
                    if is_dataclass(dataclass_type) and isinstance(
                        dataclass_type, type
                    ):
                        try:
                            # print('Resolving YAML file for field:', field.name)
                            resolved_val_temp = asdict(
                                resolve_yaml_file_to_base_dataclass(
                                    yaml_path=val.get_yaml_file_path(),
                                    base_cls=resolve_type(dataclass_type),
                                    raise_error_with_nones=raise_error_with_notfilled,
                                    package_name=package_name,
                                    level_of_recursion=level_of_recursion + 1,
                                )
                            )
                            _ = from_dict(
                                data_class=dataclass_type, data=resolved_val_temp
                            )
                            resolved_val = resolved_val_temp
                        except Exception:
                            parsley_logger.debug(
                                "fail %s yaml %s %s", field.name, dataclass_type, val
                            )
                try:
                    resolved_val
                except NameError as exc:
                    print(
                        f"Variable resolved_val is not defined in field {field} {val}"
                    )
                    raise NameError(
                        f"Variable resolved_val is not defined in field {field}"
                    ) from exc
                assert resolved_val is not None

            final_resolved_val = merge_nested_dicts(final_resolved_val, resolved_val)

        ###### CASE 3: Overwrite value provided
        if not is_notfilled(overwrite_val):
            assert is_dataclass(overwrite_val)
            dataclass_type_list = extract_union_types(base_field_type)
            for dataclass_type in dataclass_type_list:
                try:
                    if history_of_recursive_fields is None:
                        new_history__of_recursive_fields = [field.name]
                    else:
                        new_history__of_recursive_fields = (
                            history_of_recursive_fields + [field.name]
                        )

                    overwrite_resolved_val_temp = resolve_extended_object_to_dict(
                        extended_obj=cast(IsDataclass, overwrite_val),
                        base_cls=make_partial_dataclass_notfilled(dataclass_type),
                        raise_error_with_notfilled=False,
                        history_of_recursive_fields=new_history__of_recursive_fields,
                        package_name=package_name,
                        level_of_recursion=level_of_recursion + 1,
                    )

                    overwrite_resolved_val = remove_notfilled_values(
                        overwrite_resolved_val_temp
                    )

                except Exception:
                    parsley_logger.debug(
                        "fail %s overwrite %s %s",
                        field.name,
                        dataclass_type,
                        overwrite_val,
                    )

            assert overwrite_resolved_val is not None

            final_resolved_val = merge_nested_dicts(
                final_resolved_val, overwrite_resolved_val
            )

        if val is notfilled and path_val is notfilled:
            if raise_error_with_notfilled:
                raise ValueError(
                    f"Exactly one of the fields '{field.name}' or '{field.name}_path_to_yaml_file' must be provided, not neither."
                )

        result_val = final_resolved_val

    else:
        assert not is_notfilled(val) or not raise_error_with_notfilled
        result_val = val

    return result_val


def resolve_extended_object[T_Dataclass: IsDataclass](
    extended_obj: Any,
    base_cls: Type[T_Dataclass],
    raise_error_with_nones: bool = True,
    package_name: str | None = None,
    level_of_recursion: int = 0,
) -> T_Dataclass:
    """Resolve an extended object to a dataclass object.
    Args:
        extended_obj (Any): The extended object to resolve.
        base_cls (Type[T_Dataclass]): The base class type to resolve to.
        raise_error_with_nones (bool): Whether to raise an error if None values are encountered.
    Returns:
        T_Dataclass: The resolved dataclass object.
    """

    resolved_data: dict[str, Any] = resolve_extended_object_to_dict(
        extended_obj=extended_obj,
        base_cls=base_cls,
        raise_error_with_notfilled=raise_error_with_nones,
        package_name=package_name,
        level_of_recursion=level_of_recursion,
    )

    resolved_data = remove_notfilled_values(resolved_data)

    result = from_dict_with_union_handling(
        data_class=base_cls, data=resolved_data, config=dacite.Config(cast=[Enum])
    )

    return result
