"""Conservative SBML Level 2/3 subset simulator.

Supports fixed compartments, constant stoichiometry, initial species amounts or
concentrations, global/local parameters, and a safe subset of MathML kinetic laws.
It intentionally rejects events, rules, functions, algebraic constructs, and unsupported
MathML instead of pretending to simulate them.

v5.6 (engine 2.0): the compatibility analysis detects unsupported features with their real
SBML tag names (assignmentRule, rateRule, algebraicRule, …) — v5.5 and earlier looked for a
"rule" tag that does not exist and silently ignored rules on constant parameters. Units are
read from unitDefinitions and kinetic laws are checked dimensionally; Level 3 values without
a default are refused instead of being set to 0 or 1; adaptive integrators are available.
"""
from __future__ import annotations
import hashlib, json, math, xml.etree.ElementTree as ET
import numerics
import units
from pathlib import Path
from typing import Any, Callable

BASE = Path(__file__).resolve().parent
ASSET_DIR = BASE / "scientific_library" / "imported_assets"
MAX_STEPS = 50000
MAX_OUTPUT_POINTS = 501

class SBMLSimulationError(ValueError):
    pass

def _local(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]

def _children(el, name):
    return [x for x in list(el) if _local(x.tag) == name]

def _first(el, name):
    return next((x for x in el.iter() if _local(x.tag) == name), None)

def _num(text, label):
    if isinstance(text, bool):
        raise SBMLSimulationError(f"Missing or invalid numeric value for {label}.")
    try:
        value = float(text)
    except (TypeError, ValueError):
        raise SBMLSimulationError(f"Missing or invalid numeric value for {label}.") from None
    if not math.isfinite(value):
        raise SBMLSimulationError(f"Non-finite numeric value for {label}.")
    return value

def _mathml(node, env):
    tag = _local(node.tag)
    if tag == "math":
        if len(node) != 1:
            raise SBMLSimulationError("MathML <math> must contain exactly one expression.")
        return _mathml(node[0], env)
    if tag == "ci":
        name = (node.text or "").strip()
        if name not in env:
            raise SBMLSimulationError(f"Unknown symbol in kinetic law: {name}")
        return env[name]
    if tag == "cn":
        raw = "".join(node.itertext()).strip()
        # SBML real values may use scientific notation or a separate <sep/> token.
        if "<sep" in raw:
            raise SBMLSimulationError("Unsupported MathML numeric format.")
        return _num(raw, "MathML number")
    if tag == "true": return 1.0
    if tag == "false": return 0.0
    if tag == "pi": return math.pi
    if tag in ("exponentiale", "e"): return math.e
    if tag == "csymbol":
        raise SBMLSimulationError("MathML csymbol time/avogadro symbols are not yet supported.")
    if tag != "apply":
        raise SBMLSimulationError(f"Unsupported MathML element: {tag}")
    if len(node) == 0:
        raise SBMLSimulationError("Empty MathML apply expression.")
    op = _local(node[0].tag)
    args = [_mathml(child, env) for child in list(node)[1:]]
    try:
        if op == "plus" and len(args) >= 1: value = sum(args)
        elif op == "times" and len(args) >= 1:
            value = 1.0
            for x in args: value *= x
        elif op == "minus" and len(args) == 1: value = -args[0]
        elif op == "minus" and len(args) == 2: value = args[0] - args[1]
        elif op == "divide" and len(args) == 2: value = args[0] / args[1]
        elif op == "power" and len(args) == 2: value = args[0] ** args[1]
        elif op == "root" and len(args) in (1,2):
            degree = args[0] if len(args) == 1 else args[1]
            radicand = args[-1] if len(args) == 1 else args[0]
            value = radicand ** (1.0 / degree)
        elif op == "exp" and len(args) == 1: value = math.exp(args[0])
        elif op == "ln" and len(args) == 1: value = math.log(args[0])
        elif op == "log" and len(args) == 1: value = math.log10(args[0])
        elif op == "abs" and len(args) == 1: value = abs(args[0])
        elif op == "floor" and len(args) == 1: value = math.floor(args[0])
        elif op == "ceiling" and len(args) == 1: value = math.ceil(args[0])
        elif op == "sin" and len(args) == 1: value = math.sin(args[0])
        elif op == "cos" and len(args) == 1: value = math.cos(args[0])
        elif op == "tan" and len(args) == 1: value = math.tan(args[0])
        elif op == "sinh" and len(args) == 1: value = math.sinh(args[0])
        elif op == "cosh" and len(args) == 1: value = math.cosh(args[0])
        elif op == "tanh" and len(args) == 1: value = math.tanh(args[0])
        elif op == "eq" and len(args) == 2: value = float(args[0] == args[1])
        elif op == "neq" and len(args) == 2: value = float(args[0] != args[1])
        elif op == "lt" and len(args) == 2: value = float(args[0] < args[1])
        elif op == "leq" and len(args) == 2: value = float(args[0] <= args[1])
        elif op == "gt" and len(args) == 2: value = float(args[0] > args[1])
        elif op == "geq" and len(args) == 2: value = float(args[0] >= args[1])
        elif op == "and" and len(args) >= 2: value = float(all(args))
        elif op == "or" and len(args) >= 2: value = float(any(args))
        elif op == "not" and len(args) == 1: value = float(not args[0])
        else: raise SBMLSimulationError(f"Unsupported MathML operator or arity: {op}/{len(args)}")
    except (ZeroDivisionError, ValueError, OverflowError) as exc:
        raise SBMLSimulationError(f"Kinetic law evaluation failed at operator {op}: {exc}") from None
    if isinstance(value, complex) or not math.isfinite(float(value)):
        raise SBMLSimulationError(f"Kinetic law produced a non-finite/non-real result at {op}.")
    return float(value)

def _load_model(asset_id: str) -> dict:
    if not isinstance(asset_id, str) or not asset_id.startswith("sbml_") or "/" in asset_id or "\\" in asset_id:
        raise SBMLSimulationError("Invalid SBML asset ID.")
    index_path = ASSET_DIR / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    rec = next((x for x in index.get("assets", []) if x.get("id") == asset_id and x.get("type") == "sbml_model"), None)
    if not rec:
        raise SBMLSimulationError("SBML model is not in the imported library.")
    path = (BASE / rec["stored_path"]).resolve()
    if not path.is_relative_to(BASE.resolve()) or not path.is_file():
        raise SBMLSimulationError("Stored SBML path is invalid or missing.")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != rec.get("sha256"):
        raise SBMLSimulationError("Stored SBML file hash mismatch; file may have changed.")
    return {"record": rec, "xml": raw}

ENGINE_ID = "sbml_subset_simulator"
ENGINE_VERSION = "2.0"
import re
_PACKAGE_NS = re.compile(r"\{http://www\.sbml\.org/sbml/level3/version\d+/([a-z]+)/version\d+\}")
# Features with semantics this engine does not implement: refusing is the only honest option.
UNSUPPORTED_ELEMENTS = {
    "assignmentRule": "assignment rules", "rateRule": "rate rules", "algebraicRule": "algebraic rules", "event": "events",
    "functionDefinition": "function definitions", "initialAssignment": "initial assignments", "constraint": "constraints",
    "stoichiometryMath": "variable stoichiometry (stoichiometryMath)", "piecewise": "piecewise MathML", "delay": "delay",
}
IGNORABLE_PACKAGES = {"layout", "render"}  # graphical information only: ignored with a warning
SBML_UNIT_KINDS = {"mole": "mol", "litre": "L", "liter": "L", "second": "s", "metre": "m", "meter": "m", "gram": "g", "kilogram": "kg",
                   "dimensionless": "1", "item": "1", "ampere": "A", "kelvin": "K", "joule": "J", "hertz": "Hz", "newton": "N", "pascal": "Pa",
                   "volt": "V", "watt": "W", "coulomb": "C", "farad": "F", "ohm": "Ω", "siemens": "S", "henry": "H", "radian": "1", "steradian": "1"}


def _sbml_unit(definition) -> "units.Unit":
    total = units.ONE
    for u in (x for x in definition.iter() if _local(x.tag) == "unit"):
        kind = u.attrib.get("kind")
        if kind not in SBML_UNIT_KINDS:
            raise SBMLSimulationError(f"Unsupported SBML unit kind '{kind}'.")
        base = units.parse(SBML_UNIT_KINDS[kind])
        exponent = _num(u.attrib.get("exponent", "1"), "unit exponent")
        scale = _num(u.attrib.get("scale", "0"), "unit scale")
        multiplier = _num(u.attrib.get("multiplier", "1"), "unit multiplier")
        if not float(exponent).is_integer():
            raise SBMLSimulationError("Non-integer unit exponents are not supported.")
        scaled = units.Unit((multiplier * 10 ** scale) * base.factor, base.dims)
        total = total * (scaled ** int(exponent))
    return total


def _unit_ref(ref, unit_defs):
    """Unit for an SBML 'units' attribute: a unitDefinition id or a base kind; None when undeclared."""
    if not ref:
        return None
    if ref in unit_defs:
        return unit_defs[ref]
    if ref in SBML_UNIT_KINDS:
        return units.parse(SBML_UNIT_KINDS[ref])
    raise SBMLSimulationError(f"Unknown unit reference '{ref}'.")


def _mathml_units(node, env):
    """Dimension of a MathML expression; None means 'unknown' (an undeclared unit somewhere)."""
    tag = _local(node.tag)
    if tag == "math":
        return _mathml_units(node[0], env)
    if tag == "ci":
        return env.get((node.text or "").strip())
    if tag == "cn":
        return units.ONE if node.attrib.get("{http://www.sbml.org/sbml/level3/version1/core}units") == "dimensionless" else "number"
    if tag in ("pi", "exponentiale", "true", "false"):
        return units.ONE
    if tag != "apply":
        return None
    op = _local(node[0].tag)
    args = [_mathml_units(c, env) for c in list(node)[1:]]
    known = [a for a in args if isinstance(a, units.Unit)]
    if op in ("plus", "minus"):
        if any(a is None for a in args):
            return None
        if known and any(k.dims != known[0].dims for k in known):
            raise _UnitMismatch(f"'{op}' combines {', '.join(sorted({_dims(k) for k in known}))}")
        return known[0] if known else "number"
    if op in ("times", "divide"):
        if any(a is None or a == "number" for a in args):  # an undeclared number makes the result unknown
            return None if any(a is None for a in args) or op == "times" and args.count("number") else None
        result = args[0]
        for a in args[1:]:
            result = result * a if op == "times" else result / a
        return result
    if op == "power":
        if not isinstance(args[0], units.Unit):
            return None
        exponent_node = list(node)[2]
        if _local(exponent_node.tag) == "cn":
            value = float("".join(exponent_node.itertext()).strip())
            if value.is_integer():
                return args[0] ** int(value)
        return None if args[0].dims != units.ONE.dims else units.ONE
    if op in ("exp", "ln", "log", "sin", "cos", "tan", "sinh", "cosh", "tanh"):
        if isinstance(args[0], units.Unit) and args[0].dims != units.ONE.dims:
            raise _UnitMismatch(f"'{op}' applied to a quantity with dimension {_dims(args[0])}")
        return units.ONE
    return None


class _UnitMismatch(Exception):
    pass


def _dims(u) -> str:
    parts = [f"{b}^{e}" if e != 1 else b for b, e in zip(units.BASE, u.dims) if e]
    return "·".join(parts) or "1"


def _parse(raw: bytes, parameter_overrides: dict | None = None) -> dict:
    """Parse and check an SBML document; returns the model or a list of blocking problems."""
    try:
        doc = ET.fromstring(raw)
    except ET.ParseError:
        raise SBMLSimulationError("Imported XML is no longer parseable.") from None
    level = doc.attrib.get("level")
    model = next((e for e in doc.iter() if _local(e.tag) == "model"), None)
    if model is None:
        raise SBMLSimulationError("No SBML model element.")
    blocking, warnings = [], []
    present = sorted({UNSUPPORTED_ELEMENTS[_local(e.tag)] for e in doc.iter() if _local(e.tag) in UNSUPPORTED_ELEMENTS})
    blocking += [f"not supported: {name}" for name in present]
    for e in doc.iter():
        if _local(e.tag) == "csymbol" and "delay" in e.attrib.get("definitionURL", ""):
            blocking.append("not supported: delay")
        if _local(e.tag) == "reaction" and e.attrib.get("fast", "false").casefold() == "true":
            blocking.append(f"not supported: fast reaction {e.attrib.get('id', '?')}")
        if "conversionFactor" in e.attrib:
            blocking.append("not supported: conversion factors")
    packages = set()
    for e in doc.iter():
        for name in [e.tag] + list(e.attrib):
            match = _PACKAGE_NS.match(name)
            if match and match.group(1) != "core":
                packages.add(match.group(1))
    for package in sorted(packages):
        if package in IGNORABLE_PACKAGES:
            warnings.append(f"SBML package '{package}' (graphical information) ignored.")
        else:
            blocking.append(f"not supported: SBML package '{package}'")
    unit_defs = {}
    for ud in (e for e in model.iter() if _local(e.tag) == "unitDefinition"):
        try:
            unit_defs[ud.attrib.get("id")] = _sbml_unit(ud)
        except SBMLSimulationError as exc:
            blocking.append(str(exc))
    substance = _unit_ref(model.attrib.get("substanceUnits"), unit_defs) if model.attrib.get("substanceUnits") else (units.parse("mol") if level == "2" else None)
    time_unit = _unit_ref(model.attrib.get("timeUnits"), unit_defs) if model.attrib.get("timeUnits") else (units.parse("s") if level == "2" else None)
    extent = _unit_ref(model.attrib.get("extentUnits"), unit_defs) if model.attrib.get("extentUnits") else substance
    volume_default = _unit_ref(model.attrib.get("volumeUnits"), unit_defs) if model.attrib.get("volumeUnits") else (units.parse("L") if level == "2" else None)
    if level == "2":  # Level 2 lets models redefine the built-in units by id
        substance = unit_defs.get("substance", substance); time_unit = unit_defs.get("time", time_unit); volume_default = unit_defs.get("volume", volume_default); extent = substance

    comps, comp_units = {}, {}
    for el in (e for e in model.iter() if _local(e.tag) == "compartment"):
        cid = el.attrib.get("id")
        if not cid:
            blocking.append("compartment without id"); continue
        if el.attrib.get("constant", "true").casefold() == "false":
            blocking.append(f"not supported: variable size of compartment {cid}")
        if "size" in el.attrib:
            comps[cid] = _num(el.attrib["size"], f"compartment {cid} size")
        elif level == "2":
            comps[cid] = 1.0; warnings.append(f"Compartment {cid}: no size given, SBML Level 2 default 1 used.")
        else:
            blocking.append(f"compartment {cid} has no size (SBML Level 3 has no default)"); comps[cid] = float("nan")
        if comps.get(cid, 1) <= 0:
            blocking.append(f"compartment {cid} size must be positive")
        try:
            comp_units[cid] = _unit_ref(el.attrib.get("units"), unit_defs) or volume_default
        except SBMLSimulationError as exc:
            blocking.append(str(exc)); comp_units[cid] = None

    list_of_parameters = next((e for e in model if _local(e.tag) == "listOfParameters"), None)
    globals_, param_units = {}, {}
    for el in (list(list_of_parameters) if list_of_parameters is not None else []):
        if _local(el.tag) != "parameter":
            continue
        pid = el.attrib.get("id")
        if el.attrib.get("constant", "true").casefold() == "false":
            blocking.append(f"not supported: variable parameter {pid}")
        if "value" not in el.attrib:
            blocking.append(f"parameter {pid} has no value"); continue
        globals_[pid] = _num(el.attrib["value"], f"parameter {pid}")
        try:
            param_units[pid] = _unit_ref(el.attrib.get("units"), unit_defs)
        except SBMLSimulationError as exc:
            blocking.append(str(exc))
        if param_units.get(pid) is None:
            warnings.append(f"Parameter {pid}: units not declared; dimensional checks involving it are skipped.")
    overrides = parameter_overrides or {}
    if not isinstance(overrides, dict) or len(overrides) > 30:
        raise SBMLSimulationError("Parameter overrides must be an object with at most 30 entries.")
    for pid, value in overrides.items():
        if pid not in globals_:
            raise SBMLSimulationError(f"Unknown or non-global model parameter: {pid}")
        globals_[pid] = _num(value, f"override for parameter {pid}")

    species, state0, species_units = [], [], {}
    for el in (e for e in model.iter() if _local(e.tag) == "species"):
        sid = el.attrib.get("id")
        comp = el.attrib.get("compartment")
        if not sid or comp not in comps:
            blocking.append(f"species {sid or '?'} has no id or refers to a missing compartment"); continue
        fixed = el.attrib.get("boundaryCondition", "false").casefold() == "true" or el.attrib.get("constant", "false").casefold() == "true"
        has_only = el.attrib.get("hasOnlySubstanceUnits", "false").casefold() == "true"
        if "initialAmount" in el.attrib:
            amount = _num(el.attrib["initialAmount"], sid + " initialAmount")
        elif "initialConcentration" in el.attrib:
            amount = _num(el.attrib["initialConcentration"], sid + " initialConcentration") * comps[comp]
        elif level == "2":
            amount = 0.0; warnings.append(f"Species {sid}: no initial value, 0 used.")
        else:
            blocking.append(f"species {sid} has no initial amount or concentration (SBML Level 3 has no default)"); amount = 0.0
        if amount < 0:
            blocking.append(f"species {sid} starts with a negative amount")
        try:
            su = _unit_ref(el.attrib.get("substanceUnits"), unit_defs) or substance
        except SBMLSimulationError as exc:
            blocking.append(str(exc)); su = None
        cu = comp_units.get(comp)
        species_units[sid] = su if has_only else (su / cu if su is not None and cu is not None else None)
        species.append({"id": sid, "name": el.attrib.get("name", sid), "compartment": comp, "fixed": fixed, "has_only_amount": has_only})
        state0.append(amount)
    ids = [s["id"] for s in species]
    if not species:
        blocking.append("no species")
    if len(set(ids)) != len(ids):
        blocking.append("duplicate species IDs")
    index = {sid: i for i, sid in enumerate(ids)}

    reactions, unit_checks = [], []
    for reaction in (e for e in model.iter() if _local(e.tag) == "reaction"):
        rid = reaction.attrib.get("id", f"reaction_{len(reactions)+1}")
        stoich = [0.0] * len(species)
        for lst in (e for e in reaction if _local(e.tag) in ("listOfReactants", "listOfProducts")):
            for ref in (e for e in lst if _local(e.tag) == "speciesReference"):
                sid = ref.attrib.get("species")
                if sid not in index:
                    blocking.append(f"reaction {rid} references unknown species {sid}"); continue
                if ref.attrib.get("constant", "true").casefold() == "false":
                    blocking.append(f"not supported: variable stoichiometry in {rid}")
                n = _num(ref.attrib.get("stoichiometry", "1"), "stoichiometry")
                stoich[index[sid]] += n if _local(lst.tag) == "listOfProducts" else -n
        for mod in (e for e in reaction.iter() if _local(e.tag) == "modifierSpeciesReference"):
            if mod.attrib.get("species") not in index:
                blocking.append(f"reaction {rid} references unknown modifier {mod.attrib.get('species')}")
        kl = next((e for e in reaction.iter() if _local(e.tag) == "kineticLaw"), None)
        math_node = next((e for e in kl if _local(e.tag) == "math"), None) if kl is not None else None
        if math_node is None:
            blocking.append(f"reaction {rid} has no MathML kinetic law"); continue
        local_params, local_units = {}, {}
        for el in kl.iter():
            if _local(el.tag) in ("localParameter", "parameter") and el.attrib.get("id") and "value" in el.attrib:
                local_params[el.attrib["id"]] = _num(el.attrib["value"], "local parameter")
                try:
                    local_units[el.attrib["id"]] = _unit_ref(el.attrib.get("units"), unit_defs)
                except SBMLSimulationError as exc:
                    blocking.append(str(exc))
        reactions.append({"id": rid, "stoich": stoich, "math": math_node, "local_params": local_params})
        expected = (extent / time_unit) if extent is not None and time_unit is not None else None
        env = {**{c: comp_units.get(c) for c in comps}, **param_units, **species_units, **local_units}
        try:
            got = _mathml_units(math_node, env)
            if expected is None or not isinstance(got, units.Unit):
                unit_checks.append({"reaction": rid, "status": "unchecked", "reason": "a unit is undeclared (parameter, number or model units)"})
            elif got.dims == expected.dims:
                unit_checks.append({"reaction": rid, "status": "consistent", "dimension": _dims(got)})
            else:
                unit_checks.append({"reaction": rid, "status": "inconsistent", "dimension": _dims(got), "expected": _dims(expected)})
                warnings.append(f"Kinetic law of {rid} has dimension {_dims(got)}, expected {_dims(expected)} (extent/time).")
        except _UnitMismatch as exc:
            unit_checks.append({"reaction": rid, "status": "inconsistent", "reason": str(exc)})
            warnings.append(f"Kinetic law of {rid}: {exc}.")
    if not reactions and not blocking:
        blocking.append("no reactions (this engine simulates reaction networks only)")
    return {"level": level, "version": doc.attrib.get("version"), "blocking": sorted(set(blocking)), "warnings": warnings, "comps": comps,
            "globals": globals_, "species": species, "state0": state0, "reactions": reactions, "unit_checks": unit_checks,
            "units": {"substance": _dims(substance) if substance else None, "time": _dims(time_unit) if time_unit else None,
                      "extent": _dims(extent) if extent else None}}


def analyze_sbml(asset_id: str) -> dict:
    """Compatibility report: what this engine can and cannot simulate in the imported model."""
    loaded = _load_model(asset_id)
    parsed = _parse(loaded["xml"])
    rec = loaded["record"]
    return {"asset_id": asset_id, "engine": {"id": ENGINE_ID, "version": ENGINE_VERSION}, "simulatable": not parsed["blocking"],
            "blocking_problems": parsed["blocking"], "warnings": parsed["warnings"], "sbml_level": parsed["level"], "sbml_version": parsed["version"],
            "species": [s["id"] for s in parsed["species"]], "parameters": parsed["globals"], "reactions": [r["id"] for r in parsed["reactions"]],
            "unit_checks": parsed["unit_checks"], "model_units": parsed["units"],
            "provenance": {"sha256": rec.get("sha256"), "source_url": rec.get("source_url"), "license": rec.get("license"), "imported_at": rec.get("imported_at"),
                           "filename": rec.get("filename")}}


def simulate_sbml(asset_id: str, duration: Any, dt: Any, method: str = "rk4", parameter_overrides: dict | None = None) -> dict:
    duration = _num(duration, "duration")
    dt = _num(dt, "dt")
    if duration <= 0 or dt <= 0: raise SBMLSimulationError("Duration and time step must be positive.")
    if method not in ("rk4", "dopri5", "implicit_euler"): raise SBMLSimulationError("method must be rk4, dopri5 or implicit_euler.")
    steps_f = duration / dt
    steps = int(round(steps_f))
    if abs(steps_f - steps) > 1e-8: raise SBMLSimulationError("Duration must be divisible by dt.")
    if steps < 1 or steps > MAX_STEPS: raise SBMLSimulationError(f"Choose a duration/time step yielding 1–{MAX_STEPS} steps.")
    loaded = _load_model(asset_id)
    rec = loaded["record"]
    parsed = _parse(loaded["xml"], parameter_overrides)
    if parsed["blocking"]:
        raise SBMLSimulationError("This model cannot be simulated by this SBML subset: " + "; ".join(parsed["blocking"]) + ".")
    comps, globals_, species, reactions, state0 = parsed["comps"], parsed["globals"], parsed["species"], parsed["reactions"], parsed["state0"]
    warnings = ["This engine supports only a subset of SBML Level 2/3 (see the compatibility analysis).",
                "A successful numerical run is not empirical validation."] + parsed["warnings"]

    def rhs(state):
        env = dict(globals_)
        env.update(comps)
        for s, amount in zip(species, state):
            env[s["id"]] = amount if s["has_only_amount"] else amount / comps[s["compartment"]]
        rates, deriv = [], [0.0] * len(species)
        for r in reactions:
            local_env = dict(env); local_env.update(r["local_params"])
            rate = _mathml(r["math"], local_env)
            rates.append(rate)
            for i, coeff in enumerate(r["stoich"]):
                if not species[i]["fixed"]:
                    deriv[i] += coeff * rate
        if not all(math.isfinite(v) for v in deriv): raise SBMLSimulationError("Non-finite derivative.")
        return deriv, rates

    output_every = max(1, math.ceil(steps / (MAX_OUTPUT_POINTS - 1)))
    times = [min(duration, k * dt) for k in range(0, steps + 1, output_every)]
    if times[-1] != duration:
        times.append(duration)
    diagnostics = None
    if method == "rk4":
        def add(a, b, factor):
            return [x + factor * y for x, y in zip(a, b)]
        state, states = state0[:], [state0[:]]
        for n in range(steps):
            k1, _ = rhs(state); k2, _ = rhs(add(state, k1, dt / 2)); k3, _ = rhs(add(state, k2, dt / 2)); k4, _ = rhs(add(state, k3, dt))
            new = [y + dt * (a + 2 * b + 2 * c + d) / 6 for y, a, b, c, d in zip(state, k1, k2, k3, k4)]
            if not all(math.isfinite(v) for v in new): raise SBMLSimulationError(f"Numerical solution diverged near t={(n+1)*dt:g}.")
            if min(new) < -1e-7:
                raise SBMLSimulationError(f"Negative species amount encountered near t={(n+1)*dt:g}; reduce dt or check model/kinetic law.")
            state = [max(0.0, v) if v > -1e-7 else v for v in new]
            if (n + 1) % output_every == 0 or n == steps - 1:
                states.append(state[:])
        times = [0.0] + [min(duration, (n + 1) * dt) for n in range(steps) if (n + 1) % output_every == 0 or n == steps - 1]
    else:
        solver = numerics.dopri5 if method == "dopri5" else numerics.implicit_euler
        try:
            states, diagnostics = solver(lambda t, y: rhs(y)[0], 0.0, state0, duration, times, numerics.Tolerances(rtol=1e-8 if method == "dopri5" else 1e-6, atol=1e-12))
        except numerics.NumericalError as exc:
            raise SBMLSimulationError(f"{exc} [{exc.code}]") from None
        if min(min(s) for s in states) < -1e-7:
            raise SBMLSimulationError("Negative species amount beyond the solver tolerance.")
        states = [[max(0.0, v) for v in s] for s in states]

    def row_at(t, st):
        row = {"time": round(t, 12)}
        for s, amount in zip(species, st):
            row[s["id"] + "_amount"] = amount
            row[s["id"] + "_concentration"] = amount / comps[s["compartment"]]
        return row
    rows = [row_at(t, st) for t, st in zip(times, states)]
    state = states[-1]
    _, final_rates = rhs(state)
    return {
        "asset_id": asset_id, "model_name": rec.get("metadata", {}).get("model_name", asset_id), "model_sha256": rec.get("sha256"),
        "engine": {"id": ENGINE_ID, "version": ENGINE_VERSION}, "method": "fixed_step_RK4" if method == "rk4" else method, "diagnostics": diagnostics,
        "duration": duration, "dt": dt, "steps": steps, "output_points": len(rows), "parameter_values": globals_,
        "species": [{"id": s["id"], "name": s["name"], "compartment": s["compartment"]} for s in species], "reaction_ids": [r["id"] for r in reactions], "rows": rows,
        "summary": {"initial_amounts": {s["id"]: state0[i] for i, s in enumerate(species)}, "final_amounts": {s["id"]: state[i] for i, s in enumerate(species)},
                    "final_reaction_rates": {r["id"]: final_rates[i] for i, r in enumerate(reactions)}},
        "checks": {"all_outputs_finite": all(math.isfinite(v) for row in rows for v in row.values()),
                   "species_amounts_nonnegative": all(row[s["id"] + "_amount"] >= 0 for row in rows for s in species)},
        "unit_checks": parsed["unit_checks"], "model_units": parsed["units"],
        "provenance": {"sha256": rec.get("sha256"), "source_url": rec.get("source_url"), "license": rec.get("license"), "imported_at": rec.get("imported_at")},
        "validation_status": "numerically_executed_subset_not_benchmarked_against_reference", "warnings": warnings,
    }
