"""Resolve a YAML file to a dataclass object with optional paths and overwrite fields."""

import types
from dataclasses import asdict
from dataclasses import is_dataclass, fields
from enum import Enum
from typing import Any, Type
from typing import Union, get_origin, get_args
from typing import cast

import dacite
import yaml
from dacite import from_dict

from parsley_coco.alternative_dataclasses import (
    make_dataclass_with_optional_paths_and_overwrite,
    make_partial_dataclass,
    make_partial_dataclass_notfilled,
    make_partial_dataclass_with_optional_paths,
)
from parsley_coco.utils import (
    IsDataclass,
    is_or_contains_dataclass,
    merge_nested_dicts,
    is_optional_type,
    from_dict_with_union_handling,
    extract_union_types,
    print_dataclass_schema,
    remove_none_values,
    remove_notfilled_values,
    resolve_type,
)
from parsley_coco.logger import parsley_logger

from parsley_coco.sentinels import notfilled


def resolve_extended_dict_to_dict_allow_notfilled[T_Dataclass: IsDataclass](
    dicto: dict[str, Any],
    base_cls: Type[T_Dataclass],
    raise_error_with_nones: bool = True,
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
    extended_cls = make_partial_dataclass_with_optional_paths(base_cls)

    extended_obj = from_dict_with_union_handling(
        data_class=extended_cls, data=dicto, config=dacite.Config(cast=[Enum])
    )
    # print_dataclass_schema(cls=extended_cls)

    resolved_data: dict[str, Any] = resolve_extended_object_to_dict(
        extended_obj=extended_obj,
        base_cls=make_partial_dataclass_notfilled(base_cls),
        raise_error_with_notfilled=raise_error_with_nones,
    )

    return resolved_data


def resolve_dict_to_base_dataclass[T_Dataclass: IsDataclass](
    dicto: dict[str, Any],
    base_cls: Type[T_Dataclass],
    raise_error_with_nones: bool = True,
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
        extended_obj, base_cls, raise_error_with_nones=raise_error_with_nones
    )

    return resolve_extended_object_


def resolve_yaml_file_to_base_dataclass[T_Dataclass: IsDataclass](
    yaml_path: str, base_cls: Type[T_Dataclass], raise_error_with_nones: bool = True
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

    try:
        with open(yaml_path, "r", encoding="utf-8") as f:
            yaml_data = yaml.safe_load(f)
    except IOError as exc:
        raise FileNotFoundError(f"Could not read file: {yaml_path}") from exc

    return resolve_dict_to_base_dataclass(
        dicto=yaml_data,
        base_cls=base_cls,
        raise_error_with_nones=raise_error_with_nones,
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
        base_field_type = field.type
        val = getattr(extended_obj, field.name, notfilled)
        path_val = getattr(extended_obj, f"{field.name}_path_to_yaml_file", notfilled)
        overwrite_val = getattr(extended_obj, f"{field.name}_overwrite", notfilled)

        # assert isinstance(base_field_type, type)
        value_base: bool = val is not notfilled
        value_base = (
            value_base
            and not is_dataclass(val)
            and not hasattr(val, "get_yaml_file_path")
        )

        if is_or_contains_dataclass(base_field_type) and not value_base:

            # assert dataclass_type is not None

            final_resolved_val: dict[str, Any] = {}
            if path_val is not notfilled:
                assert isinstance(
                    path_val, str
                ), f"path_val must be a str, got {type(path_val)}"
                resolved_val = asdict(
                    resolve_yaml_file_to_base_dataclass(
                        yaml_path=path_val,
                        base_cls=resolve_type(base_field_type),
                        raise_error_with_nones=raise_error_with_notfilled,
                    )
                )
                final_resolved_val = merge_nested_dicts(
                    final_resolved_val, resolved_val
                )

            if val is not notfilled:
                if is_dataclass(val):
                    dataclass_type_list = extract_union_types(base_field_type)

                    for dataclass_type in dataclass_type_list:

                        try:
                            resolved_val_temp = resolve_extended_object_to_dict(
                                extended_obj=cast(IsDataclass, val),
                                base_cls=resolve_type(dataclass_type),
                                raise_error_with_notfilled=raise_error_with_notfilled,
                            )

                            _ = from_dict(
                                data_class=dataclass_type, data=resolved_val_temp
                            )
                            resolved_val = resolved_val_temp

                        except Exception:
                            parsley_logger.debug(
                                f"fail {field.name} dataclass", dataclass_type, val
                            )
                    assert resolved_val is not None
                else:  # Non-dataclass value in a Union — allowed

                    assert hasattr(val, "get_yaml_file_path")
                    dataclass_type_list = extract_union_types(base_field_type)
                    for dataclass_type in dataclass_type_list:
                        if is_dataclass(dataclass_type) and isinstance(
                            dataclass_type, type
                        ):
                            try:
                                resolved_val_temp = asdict(
                                    resolve_yaml_file_to_base_dataclass(
                                        yaml_path=val.get_yaml_file_path(),
                                        base_cls=resolve_type(dataclass_type),
                                        raise_error_with_nones=raise_error_with_notfilled,
                                    )
                                )
                                _ = from_dict(
                                    data_class=dataclass_type, data=resolved_val_temp
                                )
                                resolved_val = resolved_val_temp
                            except Exception:
                                parsley_logger.debug(
                                    f"fail {field.name} yaml", dataclass_type, val
                                )
                    assert resolved_val is not None

                final_resolved_val = merge_nested_dicts(
                    final_resolved_val, resolved_val
                )

            if overwrite_val is not notfilled:
                assert is_dataclass(overwrite_val)
                dataclass_type_list = extract_union_types(base_field_type)
                for dataclass_type in dataclass_type_list:

                    try:

                        overwrite_resolved_val_temp = resolve_extended_object_to_dict(
                            extended_obj=cast(IsDataclass, overwrite_val),
                            base_cls=make_partial_dataclass_notfilled(dataclass_type),
                            raise_error_with_notfilled=False,
                        )

                        overwrite_resolved_val = remove_notfilled_values(
                            overwrite_resolved_val_temp
                        )

                    except Exception:
                        parsley_logger.debug(
                            f"fail {field.name} overwrite",
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

            resolved_data[field.name] = final_resolved_val

        else:
            assert val is not notfilled or not raise_error_with_notfilled
            resolved_data[field.name] = val

    return resolved_data


def resolve_extended_object[T_Dataclass: IsDataclass](
    extended_obj: Any, base_cls: Type[T_Dataclass], raise_error_with_nones: bool = True
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
    )

    result = from_dict_with_union_handling(
        data_class=base_cls, data=resolved_data, config=dacite.Config(cast=[Enum])
    )

    return result
