from dataclasses import fields, make_dataclass, is_dataclass
from typing import List, Tuple
from typing import Optional, get_type_hints, Dict, Type, Any

_partial_cache: Dict[Type[Any], Type[Any]] = {}


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


def make_partial_dataclass(cls: Type[Any]) -> Type[Any]:
    if cls in _partial_cache:
        return _partial_cache[cls]

    if not is_dataclass(cls):
        raise ValueError(f"{cls} is not a dataclass")

    type_hints = get_type_hints(cls)
    partial_fields = []

    for field in fields(cls):
        field_type = type_hints[field.name]

        # If it's a nested dataclass, recurse
        if is_dataclass(field_type):
            assert isinstance(field_type, type)
            partial_type = make_partial_dataclass(field_type)
        else:
            partial_type = field_type

        # Make the field optional
        partial_fields.append(
            (
                field.name,
                Optional[partial_type],
                field.default if field.default != field.default_factory else None,
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
    optional_paths_class = make_dataclass_with_optional_paths(cls=cls)
    partial_with_optional_paths_class = make_partial_dataclass(cls=optional_paths_class)
    return partial_with_optional_paths_class
