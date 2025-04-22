from dataclasses import fields, asdict
from dataclasses import is_dataclass
from enum import Enum
from typing import Any, Type
from typing import Union, get_origin, get_args

import dacite
import yaml
from dacite import from_dict
from typing import cast

from parsley_coco.alternative_dataclasses import (
    make_dataclass_with_optional_paths_and_overwrite,
)
from parsley_coco.utils import IsDataclass, is_or_contains_dataclass


def resolve_yaml_to_base[T_Dataclass: IsDataclass](
    yaml_path: str, base_cls: Type[T_Dataclass]
) -> T_Dataclass:
    extended_cls = make_dataclass_with_optional_paths_and_overwrite(base_cls)

    try:
        with open(yaml_path, "r") as f:
            yaml_data = yaml.safe_load(f)
    except IOError:
        raise Exception("Could not read file:", yaml_path)

    extended_obj = from_dict(
        data_class=extended_cls, data=yaml_data, config=dacite.Config(cast=[Enum])
    )

    return resolve_extended_object(extended_obj, base_cls)


def extract_dataclass_type(t: type) -> type | None:
    """If t is a dataclass or Union containing one, return the dataclass type."""
    if is_dataclass(t):
        return t
    if get_origin(t) is Union:
        for arg in get_args(t):
            if isinstance(arg, type) and is_dataclass(arg):
                return arg
    return None


def resolve_extended_object_to_dict[T_Dataclass: IsDataclass](
    extended_obj: IsDataclass,
    base_cls: Type[T_Dataclass],
    raise_error_with_nones: bool = True,
) -> dict[str, Any]:
    resolved_data = {}

    assert is_dataclass(extended_obj)
    for field in fields(base_cls):
        base_field_type = field.type
        val = getattr(extended_obj, field.name, None)
        path_val = getattr(extended_obj, f"{field.name}_path_to_yaml_file", None)
        overwrite_val = getattr(extended_obj, f"{field.name}_overwrite", None)

        assert isinstance(base_field_type, type)
        if is_or_contains_dataclass(base_field_type):
            dataclass_type = extract_dataclass_type(base_field_type)
            if dataclass_type is None:
                raise TypeError(
                    f"Cannot resolve field '{field.name}': expected dataclass in type {base_field_type}"
                )

            final_resolved_val: dict[str, Any] = {}
            if path_val is not None:
                resolved_val = asdict(
                    resolve_yaml_to_base(yaml_path=path_val, base_cls=dataclass_type)
                )
                final_resolved_val = final_resolved_val | resolved_val
            if val is not None:
                if is_dataclass(val):
                    resolved_val = resolve_extended_object_to_dict(
                        extended_obj=cast(IsDataclass, val), base_cls=dataclass_type
                    )
                else:
                    assert hasattr(val, "get_yaml_file_path")
                    resolved_val = asdict(
                        resolve_yaml_to_base(
                            yaml_path=val.get_yaml_file_path(), base_cls=dataclass_type
                        )
                    )  # Non-dataclass value in a Union — allowed
                final_resolved_val = final_resolved_val | resolved_val
            if overwrite_val:
                assert is_dataclass(overwrite_val)
                overwrite_resolved_val = resolve_extended_object_to_dict(
                    cast(IsDataclass, overwrite_val), dataclass_type
                )
                final_resolved_val = final_resolved_val | overwrite_resolved_val

            if not val and not path_val:
                if raise_error_with_nones:
                    raise ValueError(
                        f"Exactly one of the fields '{field.name}' or '{field.name}_path_to_yaml_file' must be provided, not neither."
                    )

            resolved_data[field.name] = final_resolved_val

        else:
            # Not a dataclass or dataclass-union field — just assign as-is
            assert val is not None
            resolved_data[field.name] = val

    return resolved_data


def resolve_extended_object[T_Dataclass: IsDataclass](
    extended_obj: Any, base_cls: Type[T_Dataclass]
) -> T_Dataclass:
    resolved_data: dict[str, Any] = resolve_extended_object_to_dict(
        extended_obj=extended_obj, base_cls=base_cls
    )

    return from_dict(
        data_class=base_cls, data=resolved_data, config=dacite.Config(cast=[Enum])
    )
