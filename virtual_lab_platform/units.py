"""Units, dimensions and conversions (v5.1).

A unit is (factor to SI, dimension exponents over L M T I Θ N J, affine offset). Expressions
such as "J/(mol·K)", "m^2/s", "L·mol⁻¹·cm⁻¹" or "mol/L" are parsed; conversion is refused when
dimensions differ (never a silent conversion). "a.u." (arbitrary/model units) only converts to
itself. Affine units (°C) are accepted alone, not inside compound expressions.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass

BASE = ("L", "M", "T", "I", "Θ", "N", "J")  # length, mass, time, current, temperature, amount, luminous intensity


class UnitError(ValueError):
    def __init__(self, message: str, code: str = "unknown_unit", **params):
        super().__init__(message)
        self.code = code
        self.params = params


@dataclass(frozen=True)
class Unit:
    factor: float
    dims: tuple
    offset: float = 0.0
    arbitrary: bool = False

    def __mul__(self, other: "Unit") -> "Unit":
        _no_affine(self, other)
        return Unit(self.factor * other.factor, tuple(a + b for a, b in zip(self.dims, other.dims)), 0.0, self.arbitrary or other.arbitrary)

    def __truediv__(self, other: "Unit") -> "Unit":
        _no_affine(self, other)
        return Unit(self.factor / other.factor, tuple(a - b for a, b in zip(self.dims, other.dims)), 0.0, self.arbitrary or other.arbitrary)

    def __pow__(self, n: int) -> "Unit":
        _no_affine(self)
        return Unit(self.factor ** n, tuple(a * n for a in self.dims), 0.0, self.arbitrary)

    @property
    def dimensionless(self) -> bool:
        return not any(self.dims) and not self.arbitrary


def _no_affine(*units: Unit) -> None:
    if any(u.offset for u in units):
        raise UnitError("Affine units such as °C cannot be combined in an expression; use K.", "affine_in_expression")


def _d(**kw) -> tuple:
    return tuple(kw.get(b, 0) for b in ("L", "M", "T", "I", "Th", "N", "J"))


ONE = Unit(1.0, _d())
# Symbols that accept SI prefixes, and their SI definition.
_PREFIXABLE = {
    "m": Unit(1.0, _d(L=1)), "g": Unit(1e-3, _d(M=1)), "s": Unit(1.0, _d(T=1)), "A": Unit(1.0, _d(I=1)), "K": Unit(1.0, _d(Th=1)),
    "mol": Unit(1.0, _d(N=1)), "cd": Unit(1.0, _d(J=1)), "Hz": Unit(1.0, _d(T=-1)), "N": Unit(1.0, _d(M=1, L=1, T=-2)),
    "Pa": Unit(1.0, _d(M=1, L=-1, T=-2)), "J": Unit(1.0, _d(M=1, L=2, T=-2)), "W": Unit(1.0, _d(M=1, L=2, T=-3)),
    "C": Unit(1.0, _d(I=1, T=1)), "V": Unit(1.0, _d(M=1, L=2, T=-3, I=-1)), "Ω": Unit(1.0, _d(M=1, L=2, T=-3, I=-2)),
    "S": Unit(1.0, _d(M=-1, L=-2, T=3, I=2)), "F": Unit(1.0, _d(M=-1, L=-2, T=4, I=2)), "H": Unit(1.0, _d(M=1, L=2, T=-2, I=-2)),
    "L": Unit(1e-3, _d(L=3)), "M": Unit(1e3, _d(N=1, L=-3)), "eV": Unit(1.602176634e-19, _d(M=1, L=2, T=-2)), "bar": Unit(1e5, _d(M=1, L=-1, T=-2)),
}
_PLAIN = {
    "1": ONE, "%": Unit(0.01, _d()), "AU": ONE, "rad": ONE, "sr": ONE, "min": Unit(60.0, _d(T=1)), "h": Unit(3600.0, _d(T=1)),
    "d": Unit(86400.0, _d(T=1)), "atm": Unit(101325.0, _d(M=1, L=-1, T=-2)), "°C": Unit(1.0, _d(Th=1), 273.15), "degC": Unit(1.0, _d(Th=1), 273.15),
    "a.u.": Unit(1.0, _d(), 0.0, True), "ohm": _PREFIXABLE["Ω"], "Ohm": _PREFIXABLE["Ω"], "l": Unit(1e-3, _d(L=3)), "Da": Unit(1.66053906660e-27, _d(M=1)),
}
_PREFIXES = {"Y": 1e24, "Z": 1e21, "E": 1e18, "P": 1e15, "T": 1e12, "G": 1e9, "M": 1e6, "k": 1e3, "h": 1e2, "da": 1e1, "d": 1e-1,
             "c": 1e-2, "m": 1e-3, "µ": 1e-6, "μ": 1e-6, "u": 1e-6, "n": 1e-9, "p": 1e-12, "f": 1e-15, "a": 1e-18}
_SUPERSCRIPTS = str.maketrans("⁰¹²³⁴⁵⁶⁷⁸⁹⁻⁺", "0123456789-+")


def _symbol(token: str) -> Unit:
    if token in _PLAIN:
        return _PLAIN[token]
    if token in _PREFIXABLE:
        return _PREFIXABLE[token]
    for prefix in sorted(_PREFIXES, key=len, reverse=True):
        if token.startswith(prefix) and token[len(prefix):] in _PREFIXABLE:
            base = _PREFIXABLE[token[len(prefix):]]
            return Unit(base.factor * _PREFIXES[prefix], base.dims)
    raise UnitError(f"Unknown unit '{token}'.", "unknown_unit", unit=token)


_TOKEN = re.compile(r"\s*(\(|\)|/|\*|·|\^-?\d+|a\.u\.|°C|[A-Za-zΩµμ%]+|1)\s*")


def parse(expression: str) -> Unit:
    """Parse a unit expression into a Unit (cached)."""
    if not isinstance(expression, str) or not expression.strip():
        raise UnitError("A unit expression is required.", "unknown_unit", unit=expression)
    return _parse_cached(expression.strip())


_cache: dict[str, Unit] = {}


def _parse_cached(expr: str) -> Unit:
    if expr in _cache:
        return _cache[expr]
    text = expr.replace("**", "^").translate(_SUPERSCRIPTS)
    text = re.sub(r"(?<=[A-Za-zΩ)])(-?\d+)\b", r"^\1", text)  # m2 → m^2, s-1 → s^-1, mol⁻¹ → mol^-1
    if text in _PLAIN:  # standalone units including affine ones
        _cache[expr] = _PLAIN[text]
        return _PLAIN[text]
    tokens, pos = [], 0
    while pos < len(text):
        m = _TOKEN.match(text, pos)
        if not m or m.end() == pos:
            raise UnitError(f"Cannot read unit expression '{expr}'.", "unknown_unit", unit=expr)
        tokens.append(m.group(1)); pos = m.end()
    index = 0

    def peek():
        return tokens[index] if index < len(tokens) else None

    def factor() -> Unit:
        nonlocal index
        tok = peek()
        if tok == "(":
            index += 1
            value = product()
            if peek() != ")":
                raise UnitError(f"Unbalanced parenthesis in '{expr}'.", "unknown_unit", unit=expr)
            index += 1
        elif tok is None or tok in (")", "/", "*", "·") or tok.startswith("^"):
            raise UnitError(f"Cannot read unit expression '{expr}'.", "unknown_unit", unit=expr)
        else:
            index += 1
            value = _symbol(tok)
        if peek() and peek().startswith("^"):
            value = value ** int(peek()[1:]); index += 1
        return value

    def product() -> Unit:
        nonlocal index
        value = factor()
        while peek() is not None and peek() != ")":
            tok = peek()
            if tok == "/":
                index += 1; value = value / factor()
            elif tok in ("*", "·"):
                index += 1; value = value * factor()
            else:  # implicit product: "N m", "mol L-1"
                value = value * factor()
        return value

    result = product()
    if index != len(tokens):
        raise UnitError(f"Cannot read unit expression '{expr}'.", "unknown_unit", unit=expr)
    _cache[expr] = result
    return result


def dimension(expression: str) -> str:
    u = parse(expression)
    if u.arbitrary:
        return "arbitrary"
    parts = [f"{b}^{e}" if e != 1 else b for b, e in zip(BASE, u.dims) if e]
    return "·".join(parts) or "1"


def compatible(a: str, b: str) -> bool:
    ua, ub = parse(a), parse(b)
    return ua.arbitrary == ub.arbitrary and ua.dims == ub.dims


def convert(value: float, from_unit: str, to_unit: str) -> float:
    """Convert a value; refuse incompatible dimensions and arbitrary↔physical conversions."""
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise UnitError("Quantity value must be a finite number.", "invalid_type")
    src, dst = parse(from_unit), parse(to_unit)
    if src.arbitrary or dst.arbitrary:
        if src.arbitrary and dst.arbitrary:
            return float(value)
        raise UnitError(f"Arbitrary units cannot be converted to or from '{to_unit if src.arbitrary else from_unit}'.", "incompatible_dimensions",
                        from_unit=from_unit, to_unit=to_unit)
    if src.dims != dst.dims:
        raise UnitError(f"Incompatible dimensions: {from_unit} [{dimension(from_unit)}] cannot be converted to {to_unit} [{dimension(to_unit)}].",
                        "incompatible_dimensions", from_unit=from_unit, to_unit=to_unit)
    si = (value + src.offset) * src.factor
    return si / dst.factor - dst.offset


def contract_converter(value, from_unit, to_unit, name):
    """Converter used by contracts.validate_inputs for {"value", "unit"} quantities."""
    from contracts import ContractError
    try:
        return convert(value, from_unit, to_unit)
    except UnitError as exc:
        raise ContractError(f"{name}: {exc}", exc.code, name=name, **exc.params) from exc
