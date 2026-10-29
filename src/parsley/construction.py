"""Plan configuration values without invoking user constructors speculatively."""

from collections.abc import Callable, Mapping
from copy import deepcopy
from dataclasses import MISSING, Field, dataclass, fields, is_dataclass
from enum import Enum
from typing import Any, cast, get_type_hints

import dacite
from dacite.exceptions import DaciteFieldError
from dacite.types import is_instance

from parsley.alternative_dataclasses import make_partial_dataclass_notfilled
from parsley.sentinels import is_notfilled
from parsley.utils import (
    extract_union_types,
    is_or_contains_dataclass,
)

type DefaultResolver = Callable[[dict[str, Any], type[Any]], dict[str, Any]]


class UnresolvedDefaultError(ValueError):
    """Raised for a constructed default that would need another construction."""

    def __init__(self, field_name: str) -> None:
        """Explain how to defer construction until YAML references are resolved."""
        super().__init__(
            f"Default for {field_name!r} contains an unresolved YAML preset. "
            "Use the dataclass type itself as default_factory, or return a "
            "fully resolved object from the factory."
        )


def _contains_provider(value: Any) -> bool:
    """Check constructed defaults for references requiring configuration changes."""
    if not is_dataclass(value) or isinstance(value, type):
        return False
    hints = get_type_hints(type(value))
    for f in fields(value):
        item = getattr(value, f.name)
        if _contains_provider(item):
            return True
        if is_or_contains_dataclass(hints[f.name]) and hasattr(
            item, "get_yaml_file_path"
        ):
            return True
    return False


@dataclass
class _Default:
    """A default evaluated only after a complete input branch has been selected."""

    schema: type[Any]
    field: Field[Any]
    field_type: Any

    def build(self, resolve: DefaultResolver) -> Any:
        """Evaluate a needed factory once, retaining already constructed results."""
        factory = self.field.default_factory
        if factory is not MISSING:
            if isinstance(factory, type) and is_dataclass(factory):
                return _plan(factory, {}).build(resolve)
            value = factory()
        else:
            value = self.field.default

        if is_dataclass(value) and not isinstance(value, type):
            if _contains_provider(value):
                raise UnresolvedDefaultError(self.field.name)
            return deepcopy(value)

        if hasattr(value, "get_yaml_file_path"):
            resolved = resolve({self.field.name: value}, self.schema)[self.field.name]
            planned = _plan_value(self.field_type, resolved)
            return planned.build(resolve) if isinstance(planned, _Plan) else planned
        return deepcopy(value)


@dataclass
class _Plan:
    """A selected user dataclass and its prepared constructor arguments."""

    schema: type[Any]
    values: dict[str, Any]

    def build(self, resolve: DefaultResolver) -> Any:
        """Construct each selected user object once, after composing its values."""
        values = {}
        hints = get_type_hints(self.schema)
        for name, value in self.values.items():
            try:
                values[name] = (
                    value.build(resolve)
                    if isinstance(value, _Plan | _Default)
                    else deepcopy(value)
                )
                if not is_instance(values[name], hints[name]):
                    raise dacite.WrongTypeError(
                        field_type=hints[name], value=values[name]
                    )
            except DaciteFieldError as exc:
                exc.update_path(name)
                raise
        return self.schema(**values)


def _plan_value(field_type: Any, value: Any) -> Any:
    """Choose a supported dataclass union arm without running user code."""
    candidates = [
        tp
        for tp in extract_union_types(field_type)
        if isinstance(tp, type) and is_dataclass(tp)
    ]
    if not isinstance(value, Mapping) or not candidates:
        return value

    errors: list[dacite.DaciteError] = []
    for candidate in candidates:
        try:
            return _plan(candidate, dict(value))
        except dacite.DaciteError as exc:
            errors.append(exc)
    if len(candidates) == 1:
        raise errors[0]
    missing = [exc for exc in errors if isinstance(exc, dacite.MissingValueError)]
    if len(missing) == 1:
        raise missing[0]
    raise dacite.UnionMatchError(field_type=field_type, value=value)


def _plan(schema: type[Any], data: dict[str, Any]) -> _Plan:
    """Validate provided values using method-free schemas and defer defaults."""
    validated = dacite.from_dict(
        data_class=make_partial_dataclass_notfilled(schema),
        data=data,
        config=dacite.Config(cast=[Enum]),
    )
    hints = get_type_hints(schema)
    values: dict[str, Any] = {}
    for f in fields(schema):
        if not f.init:
            continue
        field_type = hints[f.name]
        value = getattr(validated, f.name)
        if is_notfilled(value):
            if f.default is not MISSING or f.default_factory is not MISSING:
                values[f.name] = _Default(schema, f, field_type)
            else:
                raise dacite.MissingValueError(f.name)
        else:
            try:
                values[f.name] = _plan_value(field_type, data[f.name])
                if not isinstance(values[f.name], _Plan):
                    values[f.name] = value
            except DaciteFieldError as exc:
                exc.update_path(f.name)
                raise
    return _Plan(schema, values)


def build_configuration[T](
    schema: type[T], data: dict[str, Any], resolve_defaults: DefaultResolver
) -> T:
    """Compose defaults and construct user objects only after choosing a schema."""
    return cast("T", _plan(schema, data).build(resolve_defaults))
