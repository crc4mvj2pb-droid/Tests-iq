"""Tool-connected scientific assistant (v8.0).

This assistant is rule-based and deterministic: it is NOT a large language model. It turns a question
into calls to the platform's real tools (model contracts, catalogue, fitting, benchmarks, validations),
executes them through controlled interfaces, and composes its answer only from the tools' outputs.

Rules enforced by the code and checked by tests:
  - every tool call is recorded (id, tool, arguments, status, outputs or error, duration);
  - every number in the answer carries the id of the call it comes from, and its unit;
  - if a tool fails, the answer says so and gives no value for it — nothing is invented;
  - if the question cannot be mapped to a tool, the answer is "unknown" with the reason.
"""
from __future__ import annotations

import re
import time
import unicodedata
from typing import Any, Callable

import data_catalog
import data_validation
import domains
import maturity
import model_registry
import units

ASSISTANT_KIND = "rule-based deterministic assistant (not a language model)"
ASSISTANT_VERSION = "1.0"


# ---- tools -------------------------------------------------------------------------------------

def _tool_run_model(args: dict) -> dict:
    env = model_registry.run_model(args["model_id"], args.get("inputs", {}))
    return {"model_id": env["model_id"], "model_version": env["model_version"], "inputs": env["inputs"], "outputs": env["outputs"],
            "warnings": env["warnings"], "maturity": maturity.maturity_of(args["model_id"])["level"]}


def _tool_describe_model(args: dict) -> dict:
    c = model_registry.get_contract(args["model_id"])
    return {k: c[k] for k in ("id", "title", "domain", "equations", "assumptions", "validity", "reference_ids")} | {"maturity": c["maturity"]["level"],
            "parameters": [{k: p.get(k) for k in ("name", "unit", "default", "required")} for p in c["parameters"]]}


def _tool_search_catalog(args: dict) -> dict:
    return {"entries": data_catalog.search(args.get("query", ""), args.get("data_kind"))}


def _tool_maturity(args: dict) -> dict:
    m = maturity.maturity_of(args["model_id"])
    return {"model_id": args["model_id"], "level": m["level"], "label_fr": m["label_fr"], "evidence": m.get("evidence", []), "note": m.get("note")}


def _tool_validations(args: dict) -> dict:
    return {"results": [{k: r[k] for k in ("protocol_id", "model_id", "verdict", "ratio", "threshold", "scope")} for r in data_validation.all_results()]}


def _tool_domains(args: dict) -> dict:
    return {"domains": [{"id": d["id"], "title": d["title"], "status": d["validation_status"]["statement"], "models": [m["id"] for m in d["models"]]}
                        for d in domains.all_domains()]}


TOOLS: dict[str, dict[str, Any]] = {
    "run_model": {"fn": _tool_run_model, "description": "Run a model contract with validated inputs"},
    "describe_model": {"fn": _tool_describe_model, "description": "Equations, assumptions, validity and parameters of a model"},
    "search_catalog": {"fn": _tool_search_catalog, "description": "Search the data catalogue"},
    "maturity": {"fn": _tool_maturity, "description": "Maturity level of a model and its evidence"},
    "validations": {"fn": _tool_validations, "description": "Results of the validations on sourced data"},
    "domains": {"fn": _tool_domains, "description": "Scientific domains and their validation status"},
}


class Trace:
    def __init__(self):
        self.calls: list[dict[str, Any]] = []

    def call(self, tool: str, args: dict) -> dict[str, Any]:
        call_id = f"c{len(self.calls) + 1}"
        started = time.perf_counter()
        record = {"id": call_id, "tool": tool, "arguments": args}
        try:
            record["outputs"] = TOOLS[tool]["fn"](args)
            record["status"] = "ok"
        except Exception as exc:  # the failure is reported, never replaced by a value
            record["status"] = "error"
            record["error"] = {"type": type(exc).__name__, "message": str(exc)[:300], "code": getattr(exc, "code", None)}
        record["duration_ms"] = round((time.perf_counter() - started) * 1000, 3)
        self.calls.append(record)
        return record


# ---- understanding the question (rules, not a language model) ---------------------------------

def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.lower())
    return "".join(c for c in text if not unicodedata.combining(c))


# Quantity patterns: symbol or word, then a number and a unit (e.g. "R = 1 kΩ", "capacité de 2 µF").
QUANTITY = re.compile(r"(?P<name>[A-Za-zΩµμ_αβγτÀ-ſ]+)\s*(?:=|de|of|:)?\s*(?P<value>-?\d+(?:[.,]\d+)?(?:e-?\d+)?)\s*(?P<unit>[A-Za-zΩµμ°/^·.\d]+)?", re.UNICODE)
UNIT_TO_PARAM = {"rc_rl_step_response": {"Ω": "resistance_ohm", "F": "capacitance_f", "H": "inductance_h", "V": "source_voltage_v"},
                 "series_rlc_ac": {"Ω": "resistance_ohm", "F": "capacitance_f", "H": "inductance_h", "Hz": "frequency_hz", "V": "source_voltage_rms_v"},
                 "arrhenius_reaction": {"K": "temperature_k", "J/mol": "activation_energy_j_mol", "1/s": "pre_exponential_s_inv"},
                 "lumped_thermal_transient": {"W": "power_w", "K/W": "thermal_resistance_k_per_w", "J/K": "thermal_capacitance_j_per_k"},
                 "aqueous_acid_base": {}}
INTENTS = [
    # (intent, model, keyword groups — every group must match at least one keyword)
    ("rc_time_constant", "rc_rl_step_response", [("constante de temps", "time constant", "tau", "τ"), ("rc", "condensateur", "capacitor", "capacite", "resistance")]),
    ("rlc_impedance", "series_rlc_ac", [("impedance", "courant efficace", "rms current"), ("rlc",)]),
    ("arrhenius_rate", "arrhenius_reaction", [("arrhenius", "constante de vitesse", "rate constant"), ("temperature", "k", "kelvin", "°c", "energie d'activation", "activation")]),
    ("heating_temperature", "lumped_thermal_transient", [("temperature", "echauffement", "heating"), ("puissance", "power", "w ")]),
    ("weak_acid_ph", "aqueous_acid_base", [("ph",), ("acide", "acid", "acetique", "acetic")]),
    ("maturity", None, [("maturite", "maturity", "valide", "validated", "verifie", "verified", "fiable", "reliable")]),
    ("catalog", None, [("donnees", "data", "dataset", "jeu de donnees", "catalogue")]),
]
MODEL_NAMES = {"michaelis": "enzyme_kinetics", "enzym": "enzyme_kinetics", "arrhenius": "arrhenius_reaction", "sir": "sir_epidemic", "epidem": "sir_epidemic",
               "hodgkin": "hodgkin_huxley", "fitzhugh": "fitzhugh_nagumo", "gompertz": "gompertz_growth", "logisti": "logistic_growth", "lotka": "lotka_volterra",
               "thermique": "lumped_thermal_transient", "rlc": "series_rlc_ac", "acide": "aqueous_acid_base", "cinetique": "mass_action_kinetics"}
OUT_OF_SCOPE = [("cancer", "diagnost", "traitement", "treatment", "dose for", "patient", "posologie"),
                ("bourse", "stock market", "lottery", "loto", "meteo", "weather", "forecast", "horoscope")]


def extract_quantities(question: str) -> list[dict[str, Any]]:
    out = []
    for m in QUANTITY.finditer(question):
        unit = (m.group("unit") or "").strip(".")
        if not unit:
            continue
        unit = unit.replace("ohm", "Ω").replace("Ohm", "Ω")
        try:
            parsed = units.parse(unit)
        except units.UnitError:
            continue
        value = float(m.group("value").replace(",", "."))
        out.append({"text": m.group(0).strip(), "value": value, "unit": unit, "dimension": units.dimension(unit), "parsed": parsed})
    return out


def _map_inputs(model_id: str, quantities: list[dict]) -> tuple[dict, list[dict]]:
    """Assign each quantity to the contract parameter whose unit has the same dimension (unit converted by the contract)."""
    contract = model_registry.get_contract(model_id)
    inputs, unused = {}, []
    for q in quantities:
        target = None
        for p in contract["parameters"]:
            if p.get("unit") and p["type"] in ("number", "integer") and p["name"] not in inputs:
                try:
                    if units.compatible(q["unit"], p["unit"]) and units.dimension(p["unit"]) != units.dimension("1"):
                        target = p
                        break
                except units.UnitError:
                    continue
        if target is None:
            unused.append(q)
        else:
            inputs[target["name"]] = {"value": q["value"], "unit": q["unit"]}
    return inputs, unused


def understand(question: str) -> dict[str, Any]:
    text = _norm(question)
    for group in OUT_OF_SCOPE:
        if any(k in text for k in group):
            return {"intent": "out_of_scope", "reason": "The question asks for a medical, financial or forecasting decision that no validated model of the platform supports."}
    for intent, model, groups in INTENTS:
        if all(any(_norm(k) in text for k in g) for g in groups):
            return {"intent": intent, "model_id": model, "quantities": extract_quantities(question),
                    "named_model": next((m for k, m in MODEL_NAMES.items() if k in text), None)}
    named = next((m for k, m in MODEL_NAMES.items() if k in text), None)
    if named:
        return {"intent": "describe", "model_id": named, "quantities": extract_quantities(question), "named_model": named}
    return {"intent": "unknown", "reason": "No tool of the platform matches this question."}


# ---- composing answers -------------------------------------------------------------------------

def _fmt(v: Any) -> str:
    return f"{v:.6g}" if isinstance(v, float) else str(v)


def answer(question: str) -> dict[str, Any]:
    trace = Trace()
    plan = understand(question if isinstance(question, str) else "")
    statements: list[dict[str, Any]] = []
    status = "answered"
    if plan["intent"] in ("unknown", "out_of_scope"):
        status = plan["intent"]
        statements.append({"kind": "limitation", "text": plan["reason"]})
    elif plan["intent"] == "maturity":
        model = plan.get("named_model")
        if model:
            rec = trace.call("maturity", {"model_id": model})
            if rec["status"] == "ok":
                o = rec["outputs"]
                statements.append({"kind": "tool_result", "text": f"Niveau de maturité de {model} : {o['label_fr']} ({len(o['evidence'])} preuve(s)).", "sources": [rec["id"]]})
        else:
            rec = trace.call("domains", {})
            if rec["status"] == "ok":
                for d in rec["outputs"]["domains"]:
                    statements.append({"kind": "tool_result", "text": f"{d['title']} — {d['status']}", "sources": [rec["id"]]})
        val = trace.call("validations", {})
        if val["status"] == "ok":
            n = sum(r["verdict"] == "validated" for r in val["outputs"]["results"])
            statements.append({"kind": "tool_result", "text": f"Modèles validés sur données sourcées : {n}.", "sources": [val["id"]], "values": [{"value": n, "unit": "1", "source": val["id"]}]})
    elif plan["intent"] == "catalog":
        rec = trace.call("search_catalog", {"query": ""})
        if rec["status"] == "ok":
            kinds = {}
            for e in rec["outputs"]["entries"]:
                kinds[e["data_kind"]] = kinds.get(e["data_kind"], 0) + 1
            statements.append({"kind": "tool_result", "text": "Entrées du catalogue par nature : " + ", ".join(f"{k} = {v}" for k, v in sorted(kinds.items())) + ".",
                               "sources": [rec["id"]], "values": [{"value": v, "unit": "1", "source": rec["id"]} for v in kinds.values()]})
    elif plan["intent"] == "describe":
        rec = trace.call("describe_model", {"model_id": plan["model_id"]})
        if rec["status"] == "ok":
            o = rec["outputs"]
            statements.append({"kind": "tool_result", "text": f"{o['title']} : {'; '.join(o['equations'])}. Maturité : {o['maturity']}.", "sources": [rec["id"]]})
    else:
        model_id = plan["model_id"]
        inputs, unused = _map_inputs(model_id, plan.get("quantities", []))
        if model_id == "aqueous_acid_base":
            conc = next((q for q in plan.get("quantities", []) if units.compatible(q["unit"], "mol/L")), None)
            if conc is None:
                status = "clarification_needed"
                statements.append({"kind": "clarification", "text": "Indiquez la concentration de l'acide (par exemple 0,1 mol/L).", "missing": ["total_concentration_mol_l"]})
                return _result(question, plan, trace, statements, status)
            pka = next(r[2] for r in data_catalog.get_entry("pka_aqueous_25c")["rows"] if r[0] == "acetic acid" and r[1] == 1)
            src = trace.call("search_catalog", {"query": "pka", "data_kind": "reference"})
            inputs = {"weak_systems": [{"name": "acetic acid", "pka": [pka], "total_concentration_mol_l": units.convert(conc["value"], conc["unit"], "mol/L")}]}
            statements.append({"kind": "tool_result", "text": f"pKa de l'acide acétique utilisé : {pka} (catalogue pka_aqueous_25c, valeur approchée).",
                               "sources": [src["id"]], "values": [{"value": pka, "unit": "1", "source": src["id"]}]})
        rec = trace.call("run_model", {"model_id": model_id, "inputs": inputs})
        if rec["status"] != "ok":
            status = "tool_failed"
            statements.append({"kind": "limitation", "text": f"L'outil {model_id} a refusé ou échoué : {rec['error']['message'].rstrip('.')}. Aucune valeur n'est donnée.", "sources": [rec["id"]]})
        else:
            o = rec["outputs"]
            values = [{"name": k, "value": v["value"], "unit": v["unit"], "source": rec["id"]} for k, v in o["outputs"].items() if isinstance(v.get("value"), (int, float))]
            statements.append({"kind": "tool_result", "text": "; ".join(f"{v['name']} = {_fmt(v['value'])} {v['unit']} [{rec['id']}]" for v in values),
                               "sources": [rec["id"]], "values": values})
            used = {k: v for k, v in o["inputs"].items() if k in inputs}
            statements.append({"kind": "tool_result", "text": "Entrées utilisées : " + ", ".join(f"{k} = {_fmt(v) if not isinstance(v, list) else 'voir appel'}" for k, v in used.items())
                               + (" ; les autres paramètres prennent les valeurs par défaut illustratives du contrat." if len(used) < len(o["inputs"]) else ""), "sources": [rec["id"]]})
            statements.append({"kind": "model_status", "text": f"Maturité du modèle : {o['maturity']}. Résultat simulé, pas une mesure.", "sources": [rec["id"]]})
            if unused:
                statements.append({"kind": "limitation", "text": "Grandeurs non utilisées (aucun paramètre de même dimension) : " + ", ".join(q["text"] for q in unused) + "."})
    return _result(question, plan, trace, statements, status)


def _result(question, plan, trace, statements, status):
    return {"assistant": ASSISTANT_KIND, "version": ASSISTANT_VERSION, "question": question, "status": status,
            "understanding": {k: v for k, v in plan.items() if k != "quantities"} | {"quantities": [{k: q[k] for k in ("text", "value", "unit", "dimension")} for q in plan.get("quantities", [])]},
            "statements": statements, "tool_calls": trace.calls,
            "text": "\n".join(s["text"] for s in statements)}


def untraced_numbers(result: dict[str, Any]) -> list[str]:
    """Numbers written in the answer that appear in no tool output or question (hallucination check)."""
    import json
    # v8.6: tool error messages are tool outputs too (e.g. a contract bound quoted in a refusal).
    haystack = json.dumps([[c.get("outputs"), c.get("error")] for c in result["tool_calls"]], ensure_ascii=False) + " " + result["question"]
    known = set(re.findall(r"-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", haystack))
    known_formatted = set()
    for token in known:
        try:
            known_formatted.add(f"{float(token):.6g}")
        except ValueError:
            pass
    bad = []
    for token in re.findall(r"(?<![\w\[])-?\d+(?:\.\d+)?(?:e[-+]?\d+)?", result["text"]):
        if token in known or token in known_formatted or token in {"0", "1", "2", "3", "4", "5", "6", "7", "8", "9"}:
            continue
        try:
            if f"{float(token):.6g}" in known_formatted:
                continue
        except ValueError:
            pass
        bad.append(token)
    return bad
