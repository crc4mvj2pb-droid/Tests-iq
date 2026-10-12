"""Conservative SBML Level 2/3 subset simulator.

Supports fixed compartments, constant stoichiometry, initial species amounts or
concentrations, global/local parameters, and a safe subset of MathML kinetic laws.
It intentionally rejects events, rules, functions, algebraic constructs, and unsupported
MathML instead of pretending to simulate them.
"""
from __future__ import annotations
import hashlib, json, math, xml.etree.ElementTree as ET
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

def simulate_sbml(asset_id: str, duration: Any, dt: Any, method: str = "rk4", parameter_overrides: dict | None = None) -> dict:
    duration = _num(duration, "duration")
    dt = _num(dt, "dt")
    if duration <= 0 or dt <= 0: raise SBMLSimulationError("Duration and time step must be positive.")
    if method != "rk4": raise SBMLSimulationError("Only fixed-step RK4 is supported in this version.")
    steps_f = duration / dt
    steps = int(round(steps_f))
    if abs(steps_f - steps) > 1e-8: raise SBMLSimulationError("Duration must be divisible by dt.")
    if steps < 1 or steps > MAX_STEPS: raise SBMLSimulationError(f"Choose a duration/time step yielding 1–{MAX_STEPS} steps.")
    loaded = _load_model(asset_id)
    rec, raw = loaded["record"], loaded["xml"]
    try: doc = ET.fromstring(raw)
    except ET.ParseError: raise SBMLSimulationError("Imported XML is no longer parseable.") from None
    model = next((e for e in doc.iter() if _local(e.tag) == "model"), None)
    if model is None: raise SBMLSimulationError("No SBML model element.")
    unsupported = {"event", "rule", "functionDefinition", "initialAssignment", "constraint"}
    present = sorted({_local(e.tag) for e in model.iter()} & unsupported)
    if present:
        raise SBMLSimulationError("This SBML subset does not yet support: " + ", ".join(present))
    comps = {}
    for el in model.iter():
        if _local(el.tag) == "compartment":
            cid = el.attrib.get("id")
            if not cid: raise SBMLSimulationError("Compartment without id.")
            if el.attrib.get("spatialDimensions", "3") not in ("0", "1", "2", "3"):
                raise SBMLSimulationError("Unsupported compartment dimensions.")
            if el.attrib.get("constant", "true").casefold() == "false":
                raise SBMLSimulationError("Dynamic compartment sizes are not supported.")
            comps[cid] = _num(el.attrib.get("size", "1"), f"compartment {cid} size")
            if comps[cid] <= 0: raise SBMLSimulationError(f"Compartment {cid} size must be positive.")
    globals_ = {}
    for el in model.iter():
        if _local(el.tag) == "parameter":
            pid = el.attrib.get("id")
            if pid and "value" in el.attrib:
                if el.attrib.get("constant", "true").casefold() == "false":
                    raise SBMLSimulationError("Variable parameters/rules are not supported.")
                globals_[pid] = _num(el.attrib["value"], f"parameter {pid}")
    overrides = parameter_overrides or {}
    if not isinstance(overrides, dict) or len(overrides) > 30:
        raise SBMLSimulationError("Parameter overrides must be an object with at most 30 entries.")
    for pid, value in overrides.items():
        if pid not in globals_:
            raise SBMLSimulationError(f"Unknown or non-global model parameter: {pid}")
        parsed_value = _num(value, f"override for parameter {pid}")
        globals_[pid] = parsed_value
    species = []
    state0 = []
    for el in model.iter():
        if _local(el.tag) != "species": continue
        sid = el.attrib.get("id")
        if not sid: raise SBMLSimulationError("Species without id.")
        if el.attrib.get("boundaryCondition", "false").casefold() == "true" or el.attrib.get("constant", "false").casefold() == "true":
            fixed = True
        else: fixed = False
        comp = el.attrib.get("compartment")
        if comp not in comps: raise SBMLSimulationError(f"Species {sid} refers to missing compartment {comp}.")
        if "initialAmount" in el.attrib: amount = _num(el.attrib["initialAmount"], sid+" initialAmount")
        elif "initialConcentration" in el.attrib: amount = _num(el.attrib["initialConcentration"], sid+" initialConcentration") * comps[comp]
        else: amount = 0.0
        if amount < 0: raise SBMLSimulationError(f"Species {sid} starts with a negative amount.")
        species.append({"id":sid,"name":el.attrib.get("name",sid),"compartment":comp,
                        "fixed":fixed,"has_only_amount":el.attrib.get("hasOnlySubstanceUnits","false").casefold()=="true"})
        state0.append(amount)
    if not species: raise SBMLSimulationError("No species found in SBML model.")
    ids = [s["id"] for s in species]
    if len(set(ids)) != len(ids): raise SBMLSimulationError("Duplicate species IDs.")
    species_index = {sid:i for i,sid in enumerate(ids)}
    reactions = []
    for reaction in (e for e in model.iter() if _local(e.tag) == "reaction"):
        stoich = [0.0] * len(species)
        for ref in reaction.iter():
            if _local(ref.tag) not in ("speciesReference", "modifierSpeciesReference"): continue
            sid = ref.attrib.get("species")
            if sid not in species_index: raise SBMLSimulationError(f"Reaction references unknown species {sid}.")
            if _local(ref.tag) == "modifierSpeciesReference": continue
            if ref.attrib.get("constant", "true").casefold() == "false" or any(_local(x.tag)=="stoichiometryMath" for x in ref):
                raise SBMLSimulationError("Variable stoichiometry is not supported.")
            n = _num(ref.attrib.get("stoichiometry", "1"), "stoichiometry")
            parent_list = next((p for p in reaction.iter() if ref in list(p)), None)
            list_name = _local(parent_list.tag) if parent_list is not None else ""
            stoich[species_index[sid]] += n if list_name == "listOfProducts" else -n
        kl = next((e for e in reaction.iter() if _local(e.tag) == "kineticLaw"), None)
        if kl is None: raise SBMLSimulationError(f"Reaction {reaction.attrib.get('id','?')} has no kinetic law.")
        math_node = next((e for e in kl if _local(e.tag) == "math"), None)
        if math_node is None: raise SBMLSimulationError(f"Reaction {reaction.attrib.get('id','?')} has no MathML kinetic law.")
        local_params = {}
        for el in kl.iter():
            if _local(el.tag) in ("localParameter", "parameter") and el is not kl and el.attrib.get("id") and "value" in el.attrib:
                local_params[el.attrib["id"]] = _num(el.attrib["value"], "local parameter")
        reactions.append({"id":reaction.attrib.get("id",f"reaction_{len(reactions)+1}"),
                          "stoich":stoich,"math":math_node,"local_params":local_params})
    if not reactions: raise SBMLSimulationError("No reactions found; this engine currently supports reaction-network SBML only.")
    if any(not math.isfinite(x) for x in state0): raise SBMLSimulationError("Invalid initial state.")
    warnings = [
        "This engine supports only a subset of SBML Level 2/3.",
        "Units are not dimensionally reconciled automatically; confirm model units and time scale.",
        "A successful numerical run is not empirical validation."
    ]
    def rhs(state):
        env = dict(globals_)
        for s, amount in zip(species, state):
            val = amount if s["has_only_amount"] else amount / comps[s["compartment"]]
            env[s["id"]] = val
        rates = []
        deriv = [0.0] * len(species)
        for r in reactions:
            local_env = dict(env); local_env.update(r["local_params"])
            rate = _mathml(r["math"], local_env)
            rates.append(rate)
            for i, coeff in enumerate(r["stoich"]):
                if not species[i]["fixed"]: deriv[i] += coeff * rate
        if not all(math.isfinite(v) for v in deriv): raise SBMLSimulationError("Non-finite derivative.")
        return deriv, rates
    def add(a,b,factor):
        return [x+factor*y for x,y in zip(a,b)]
    state = state0[:]
    rows = []
    output_every = max(1, math.ceil(steps / (MAX_OUTPUT_POINTS - 1)))
    def row_at(t, st):
        row = {"time": round(t, 12)}
        for s, amount in zip(species, st):
            row[s["id"]+"_amount"] = amount
            row[s["id"]+"_concentration"] = amount / comps[s["compartment"]]
        return row
    rows.append(row_at(0.0,state))
    for n in range(steps):
        k1,_ = rhs(state)
        k2,_ = rhs(add(state,k1,dt/2))
        k3,_ = rhs(add(state,k2,dt/2))
        k4,_ = rhs(add(state,k3,dt))
        new = [y + dt*(a+2*b+2*c+d)/6 for y,a,b,c,d in zip(state,k1,k2,k3,k4)]
        if not all(math.isfinite(v) for v in new): raise SBMLSimulationError(f"Numerical solution diverged near t={(n+1)*dt:g}.")
        if min(new) < -1e-7:
            raise SBMLSimulationError(f"Negative species amount encountered near t={(n+1)*dt:g}; reduce dt or check model/kinetic law.")
        state = [max(0.0,v) if v > -1e-7 else v for v in new]
        if (n+1) % output_every == 0 or n == steps-1:
            rows.append(row_at((n+1)*dt,state))
    _, final_rates = rhs(state)
    return {
      "asset_id":asset_id,"model_name":rec.get("metadata",{}).get("model_name",asset_id),
      "model_sha256":rec.get("sha256"),"method":"fixed_step_RK4","duration":duration,"dt":dt,
      "steps":steps,"output_points":len(rows),"parameter_values":globals_,"species":[{"id":s["id"],"name":s["name"],"compartment":s["compartment"]} for s in species],
      "reaction_ids":[r["id"] for r in reactions],"rows":rows,
      "summary":{"initial_amounts":{s["id"]:state0[i] for i,s in enumerate(species)},
                 "final_amounts":{s["id"]:state[i] for i,s in enumerate(species)},
                 "final_reaction_rates":{r["id"]:final_rates[i] for i,r in enumerate(reactions)}},
      "checks":{"all_outputs_finite":all(math.isfinite(v) for row in rows for v in row.values()),
                "species_amounts_nonnegative":all(row[s["id"]+"_amount"] >= 0 for row in rows for s in species)},
      "validation_status":"numerically_executed_subset_not_benchmarked_against_reference",
      "warnings":warnings
    }
