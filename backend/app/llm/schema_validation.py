"""Small JSON Schema validator for model outputs and tool arguments."""

from __future__ import annotations

from typing import Any


def validate_schema_value(
    value: Any,
    schema: dict[str, Any],
    path: str = "$",
    *,
    error_prefix: str = "Structured output violates schema",
) -> None:
    """Validate the JSON Schema subset used by ResolveAI."""
    if "anyOf" in schema:
        for option in schema["anyOf"]:
            try:
                validate_schema_value(
                    value,
                    option,
                    path,
                    error_prefix=error_prefix,
                )
                return
            except ValueError:
                continue
        raise ValueError(f"{error_prefix} at {path}")

    expected = schema.get("type")
    type_checks = {
        "object": isinstance(value, dict),
        "array": isinstance(value, list),
        "string": isinstance(value, str),
        "number": isinstance(value, int | float) and not isinstance(value, bool),
        "integer": isinstance(value, int) and not isinstance(value, bool),
        "boolean": isinstance(value, bool),
        "null": value is None,
    }
    valid_type = type_checks.get(expected, True) if isinstance(expected, str) else True
    if not valid_type:
        raise ValueError(f"{error_prefix} at {path}")

    if "enum" in schema and value not in schema["enum"]:
        raise ValueError(f"{error_prefix} at {path}")
    if isinstance(value, int | float) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ValueError(f"{error_prefix} at {path}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ValueError(f"{error_prefix} at {path}")
    if isinstance(value, dict):
        for required in schema.get("required", []):
            if required not in value:
                raise ValueError(f"{error_prefix} at {path}")
        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                validate_schema_value(
                    item,
                    properties[key],
                    f"{path}.{key}",
                    error_prefix=error_prefix,
                )
            elif schema.get("additionalProperties") is False:
                raise ValueError(f"{error_prefix} at {path}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            validate_schema_value(
                item,
                schema["items"],
                f"{path}[{index}]",
                error_prefix=error_prefix,
            )
