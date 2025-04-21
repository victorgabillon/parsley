from dataclasses import fields, Field, make_dataclass, is_dataclass
from typing import Optional, List, Tuple, Any, Type, get_type_hints

from dacite import from_dict
from enum import Enum
import yaml
import dacite


def make_dataclass_with_optional_paths_ii(cls: Type[Any]) -> Type[Any]:
    assert is_dataclass(cls), f"{cls} must be a dataclass"

    new_fields: List[Tuple[str, Any, Field[Any]]] = []
    hints = get_type_hints(cls)

    for field in fields(cls):
        field_type = hints[field.name]

        # Always add the original field (make optional if it's a dataclass)
        if is_dataclass(field_type):
            new_fields.append((field.name, Optional[field_type], field))
            new_fields.append((f"{field.name}_path_to_yaml_file", Optional[str], field))
        else:
            new_fields.append((field.name, field_type, field))

    new_cls_name = cls.__name__ + "_with_potential_path"
    return make_dataclass(new_cls_name, new_fields)


def make_dataclass_with_optional_paths(cls: Type[Any]) -> Type[Any]:
    assert is_dataclass(cls), f"{cls} must be a dataclass"

    new_fields: List[Tuple[str, Any]] = []
    hints = get_type_hints(cls)

    for f in fields(cls):
        field_type = hints[f.name]

        # If it's a dataclass, add both the field and its '_path_to_yaml_file' sibling
        if is_dataclass(field_type):
            new_fields.append((f.name, Optional[field_type]))
            new_fields.append((f"{f.name}_path_to_yaml_file", Optional[str]))
        else:
            new_fields.append((f.name, field_type))

    new_cls_name = cls.__name__ + "_with_potential_path"
    return make_dataclass(new_cls_name, new_fields)


def resolve_yaml_to_base(yaml_path: str, base_cls: Type[Any]) -> Any:
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


def resolve_extended_object(extended_obj: Any, base_cls: Type[Any]) -> Any:
    resolved_data = {}

    for field in fields(base_cls):
        base_field_type = field.type
        val = getattr(extended_obj, field.name, None)

        if is_dataclass(base_field_type):
            path_val = getattr(extended_obj, f"{field.name}_path_to_yaml_file", None)

            if path_val and not val:
                assert isinstance(base_field_type, type)
                resolved_val = resolve_yaml_to_base(path_val, base_field_type)
            elif val and not path_val:
                assert isinstance(base_field_type, type)
                resolved_val = resolve_extended_object(val, base_field_type)
            else:
                raise ValueError(
                    f"Exactly one of the fields {field.name} or {field.name}_path_to_yaml_file must be given, not none of them, not both"
                )

            resolved_data[field.name] = resolved_val

        else:
            resolved_data[field.name] = val

    return from_dict(
        data_class=base_cls, data=resolved_data, config=dacite.Config(cast=[Enum])
    )
