from dataclasses import fields, is_dataclass, asdict
from enum import Enum
from typing import Any, Type

import dacite
import yaml
from dacite import from_dict

from parsley_coco.alternative_dataclasses import make_dataclass_with_optional_paths
from parsley_coco.utils import IsDataclass


def resolve_yaml_to_base[T_Dataclass: IsDataclass](
    yaml_path: str, base_cls: Type[T_Dataclass]
) -> T_Dataclass:
    extended_cls = make_dataclass_with_optional_paths(base_cls)

    try:
        with open(yaml_path, "r") as f:
            yaml_data = yaml.safe_load(f)
    except IOError:
        raise Exception("Could not read file:", yaml_path)

    extended_obj = from_dict(
        data_class=extended_cls, data=yaml_data, config=dacite.Config(cast=[Enum])
    )

    return resolve_extended_object(extended_obj, base_cls)


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

        if is_dataclass(base_field_type):
            path_val = getattr(extended_obj, f"{field.name}_path_to_yaml_file", None)

            if path_val and not val:
                assert isinstance(base_field_type, type)
                resolved_val = asdict(resolve_yaml_to_base(path_val, base_field_type))
            elif val and not path_val:
                assert isinstance(base_field_type, type)
                resolved_val = resolve_extended_object_to_dict(val, base_field_type)
            else:
                if raise_error_with_nones:
                    string = f"Exactly one of the fields {field.name} or {field.name}_path_to_yaml_file must be given, "
                    if not val and not path_val:
                        string += "not none of them"
                    elif val is not None and path_val is not None:
                        string += "not both"
                    raise ValueError(string)
                else:
                    resolved_val = None

            resolved_data[field.name] = resolved_val

        else:
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
