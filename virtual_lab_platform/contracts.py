"""Common model contract (v5.0): what every scientific engine declares and how inputs are checked.

A contract is plain data so it can be served by the API, tested and documented:
  id, version, title, domain, engine, parameters[], outputs[], assumptions[], validity[],
  error_codes[], references[], equations[], maturity (v5.7) and validation evidence.

`validate_inputs` applies the contract before any calculation: unknown parameters are
refused (a typo is never silently ignored), types, bounds and enumerations are checked,
defaults are filled in, and every error carries a stable code.
"""
from __future__ import annotations

import math
from typing import Any

CONTRACT_VERSION = "1.0"
PARAMETER_TYPES = {"number", "integer", "string", "boolean", "enum", "array", "object"}
REQUIRED_FIELDS = ("id", "version", "title", "domain", "parameters", "outputs", "assumptions", "validity", "error_codes", "references")


class ContractError(ValueError):
    """Input refused by a model contract (stable code + parameters, like WorkbenchCircuitError)."""

    def __init__(self, message: str, code: str = "invalid_parameter", **params):
        super().__init__(message)
        self.code = code
        self.params = params


def param(name: str, ptype: str, *, unit: str | None = None, minimum: float | None = None, maximum: float | None = None,
          exclusive_minimum: bool = False, default: Any = None, required: bool = False, choices: list | None = None,
          description: str = "") -> dict[str, Any]:
    """Build one parameter specification."""
    if ptype not in PARAMETER_TYPES:
        raise ValueError(f"unknown parameter type {ptype}")
    spec = {"name": name, "type": ptype, "description": description, "required": required}
    if unit is not None:
        spec["unit"] = unit
    if minimum is not None:
        spec["minimum"] = minimum
        spec["exclusive_minimum"] = exclusive_minimum
    if maximum is not None:
        spec["maximum"] = maximum
    if default is not None:
        spec["default"] = default
    if choices is not None:
        spec["choices"] = choices
    return spec


def output(name: str, path: str, unit: str, description: str = "") -> dict[str, str]:
    """One declared output; `path` locates it in the engine result (dots, `[0]` for list items)."""
    return {"name": name, "path": path, "unit": unit, "description": description}


def check_contract(contract: dict[str, Any]) -> list[str]:
    """Return the list of problems in a contract definition (empty list = well formed)."""
    problems = [f"missing field '{f}'" for f in REQUIRED_FIELDS if f not in contract]
    names = set()
    for p in contract.get("parameters", []):
        if p.get("type") not in PARAMETER_TYPES:
            problems.append(f"parameter {p.get('name')}: invalid type {p.get('type')!r}")
        if p.get("name") in names:
            problems.append(f"parameter {p.get('name')}: duplicated")
        names.add(p.get("name"))
        if p.get("type") in ("number", "integer") and not p.get("unit"):
            problems.append(f"parameter {p['name']}: numeric parameter without unit")
        if p.get("type") == "enum" and not p.get("choices"):
            problems.append(f"parameter {p['name']}: enum without choices")
        if "default" in p and p.get("type") in ("number", "integer"):
            try:
                _check_value(p, p["default"])
            except ContractError as exc:
                problems.append(f"parameter {p['name']}: default violates its own bounds ({exc})")
    for o in contract.get("outputs", []):
        if not o.get("unit"):
            problems.append(f"output {o.get('name')}: missing unit")
    return problems


def _check_value(spec: dict[str, Any], value: Any) -> Any:
    name, ptype = spec["name"], spec["type"]
    if ptype in ("number", "integer"):
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ContractError(f"{name} must be a finite number ({spec.get('unit', '')}).", "invalid_type", name=name, expected="number")
        if ptype == "integer" and (not isinstance(value, int) and not float(value).is_integer()):
            raise ContractError(f"{name} must be an integer.", "invalid_type", name=name, expected="integer")
        if ptype == "integer":
            value = int(value)
        low = spec.get("minimum")
        if low is not None and (value < low or (spec.get("exclusive_minimum") and value == low)):
            relation = ">" if spec.get("exclusive_minimum") else "≥"
            raise ContractError(f"{name} must be {relation} {low} {spec.get('unit', '')}.".strip(), "out_of_range", name=name, minimum=low)
        high = spec.get("maximum")
        if high is not None and value > high:
            raise ContractError(f"{name} must be ≤ {high} {spec.get('unit', '')}.".strip(), "out_of_range", name=name, maximum=high)
        return value
    if ptype == "boolean":
        if not isinstance(value, bool):
            raise ContractError(f"{name} must be true or false.", "invalid_type", name=name, expected="boolean")
        return value
    if ptype == "string":
        if not isinstance(value, str):
            raise ContractError(f"{name} must be a string.", "invalid_type", name=name, expected="string")
        return value
    if ptype == "enum":
        if value not in spec["choices"]:
            raise ContractError(f"{name} must be one of {', '.join(map(str, spec['choices']))}.", "invalid_choice", name=name, choices=spec["choices"])
        return value
    if ptype == "array":
        if not isinstance(value, list):
            raise ContractError(f"{name} must be a list.", "invalid_type", name=name, expected="array")
        return value
    if not isinstance(value, dict):
        raise ContractError(f"{name} must be an object.", "invalid_type", name=name, expected="object")
    return value


def validate_inputs(contract: dict[str, Any], inputs: Any, *, converter=None) -> dict[str, Any]:
    """Check inputs against the contract and return the normalized inputs (defaults filled in).

    `converter(value, from_unit, to_unit)` is used for quantities given as {"value": x, "unit": "..."}
    (v5.1); without it such quantities are refused.
    """
    if not isinstance(inputs, dict):
        raise ContractError("Model inputs must be a JSON object.", "invalid_request")
    specs = {p["name"]: p for p in contract["parameters"]}
    unknown = sorted(set(inputs) - set(specs))
    if unknown:
        raise ContractError(f"Unknown parameter(s) for {contract['id']}: {', '.join(unknown)}. Accepted: {', '.join(sorted(specs))}.",
                            "unknown_parameter", names=unknown, accepted=sorted(specs))
    normalized: dict[str, Any] = {}
    for name, spec in specs.items():
        if name not in inputs:
            if spec.get("required"):
                raise ContractError(f"Missing required parameter {name}.", "missing_parameter", name=name)
            if "default" in spec:
                normalized[name] = spec["default"]
            continue
        value = inputs[name]
        if isinstance(value, dict) and set(value) == {"value", "unit"} and spec["type"] in ("number", "integer"):
            if converter is None:
                raise ContractError(f"{name}: quantities with units are not accepted here.", "invalid_type", name=name)
            value = converter(value["value"], value["unit"], spec["unit"], name)
        normalized[name] = _check_value(spec, value)
    return normalized


def resolve_path(result: Any, path: str) -> Any:
    """Follow a dotted path such as 'summary.final_A' or 'rows[0].time' inside a result."""
    current = result
    for part in path.replace("]", "").split("."):
        key, _, index = part.partition("[")
        if key:
            if not isinstance(current, dict) or key not in current:
                raise KeyError(path)
            current = current[key]
        if index:
            current = current[int(index)]
    return current
