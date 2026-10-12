"""Multi-model experiments (v5.8): steps linked by unit-checked bindings, with per-step provenance.

A pipeline is a list of steps. A step runs a registered model (model_registry, contract-validated)
or an adapter (small explicit physical relation). A binding copies an output of an earlier step
into an input of a later one, converting units with units.py and refusing any dimension mismatch.
Every intermediate input, output, unit conversion, warning and maturity level is kept, and the
pipeline's maturity is the lowest of its steps: combining models never hides a weak link.
"""
from __future__ import annotations

import copy
import math
from typing import Any

import maturity
import model_registry
import units
from constants import GAS_CONSTANT
from contracts import ContractError, resolve_path

ENGINE_ID = "multi_model_pipeline"
ENGINE_VERSION = "1.0"
MAX_STEPS = 10


class PipelineError(ValueError):
    def __init__(self, message: str, code: str = "invalid_pipeline", **params):
        super().__init__(message)
        self.code = code
        self.params = params


def _number(params: dict, key: str, unit: str, *, positive: bool = True) -> float:
    value = params.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or (positive and value <= 0):
        raise PipelineError(f"{key} ({unit}) must be a finite number{' > 0' if positive else ''}.", "invalid_parameter", name=key)
    return float(value)


def _lumped_heating(params: dict) -> dict:
    """Steady temperature of a heated body: T = T_amb + P·R_th; reached with the time constant τ = R_th·C_th."""
    p = _number(params, "power_w", "W", positive=False)
    t_amb = _number(params, "ambient_temperature_k", "K")
    r_th = _number(params, "thermal_resistance_k_per_w", "K/W")
    c_th = _number(params, "thermal_capacitance_j_per_k", "J/K")
    return {"temperature_k": t_amb + p * r_th, "thermal_time_constant_s": r_th * c_th, "timescale_s": r_th * c_th}


def _beer_lambert(params: dict) -> dict:
    c = _number(params, "concentration_mol_l", "mol/L", positive=False)
    eps = _number(params, "epsilon_l_per_mol_cm", "L/(mol·cm)")
    path = _number(params, "path_length_cm", "cm")
    absorbance = eps * path * c
    return {"absorbance": absorbance, "linear_range_ok": absorbance <= 2.0}


ADAPTERS: dict[str, dict[str, Any]] = {
    "lumped_steady_heating": {
        "title": "Échauffement stationnaire d'un corps (modèle à une capacité thermique)", "function": _lumped_heating,
        "inputs": {"power_w": "W", "ambient_temperature_k": "K", "thermal_resistance_k_per_w": "K/W", "thermal_capacitance_j_per_k": "J/K"},
        "outputs": {"temperature_k": "K", "thermal_time_constant_s": "s"},
        "equations": ["T = T_amb + P·R_th", "τ_th = R_th·C_th"],
        "assumptions": ["Uniform body temperature (lumped capacitance)", "Steady state: valid only for durations ≫ τ_th"],
        "maturity": {"level": "computable", "evidence": [], "note": "Relation simple non vérifiée contre une référence indépendante (prévu en v7.1)."},
    },
    "beer_lambert": {
        "title": "Absorbance par la loi de Beer–Lambert", "function": _beer_lambert,
        "inputs": {"concentration_mol_l": "mol/L", "epsilon_l_per_mol_cm": "L/(mol·cm)", "path_length_cm": "cm"},
        "outputs": {"absorbance": "1"},
        "equations": ["A = ε·l·c"], "assumptions": ["Dilute solution, monochromatic light, linear range (A ≲ 2)"],
        "maturity": {"level": "verified", "evidence": [{"kind": "analytical", "test": "tests/test_v47_linked_instruments.py::test_spectrophotometer_reads_kinetics_concentration_through_beer_lambert",
                                                       "description": "A = ε·l·c", "tolerance": "1e-12"}]},
    },
}


def _set_path(target: dict, path: str, value: Any) -> None:
    parts = path.replace("]", "").split(".")
    current = target
    for i, part in enumerate(parts):
        key, _, index = part.partition("[")
        last = i == len(parts) - 1
        if index:
            seq = current.get(key)
            if not isinstance(seq, list) or not 0 <= int(index) < len(seq):
                raise PipelineError(f"Binding target '{path}': index {index} does not exist.", "invalid_binding", path=path)
            if last:
                seq[int(index)] = value
            else:
                current = seq[int(index)]
        elif last:
            current[key] = value
        else:
            if not isinstance(current.get(key), dict):
                raise PipelineError(f"Binding target '{path}' does not exist.", "invalid_binding", path=path)
            current = current[key]


def _target_unit(step: dict, inputs: dict, path: str) -> str | None:
    """Unit expected by a step input, including the derived unit of a kinetics rate constant."""
    if "adapter" in step:
        return ADAPTERS[step["adapter"]]["inputs"].get(path)
    contract = model_registry.get_contract(step["model"])
    spec = next((p for p in contract["parameters"] if p["name"] == path), None)
    if spec is not None:
        return spec.get("unit") or (inputs.get(spec["unit_from"]) if spec.get("unit_from") else None)
    if step["model"] == "mass_action_kinetics" and path.startswith("reactions[") and path.endswith("].rate_constant"):
        index = int(path[len("reactions["):path.index("]")])
        reactions = inputs.get("reactions", [])
        if not 0 <= index < len(reactions):
            raise PipelineError(f"Binding target '{path}': reaction {index} does not exist.", "invalid_binding", path=path)
        order = sum(reactions[index].get("reactants", {}).values())
        cu = inputs.get("concentration_unit", "mol/L")
        return "1/s" if order == 1 else f"({cu})^{1 - order}/s"
    if step["model"] == "mass_action_kinetics" and path.startswith("species[") and path.endswith("].initial_concentration"):
        return inputs.get("concentration_unit", "mol/L")
    raise PipelineError(f"Binding target '{path}' is not a known input of {step['model']}.", "invalid_binding", path=path)


def _source(step_results: dict, ref: str) -> tuple[Any, str]:
    """Value and unit of 'step.output' (declared output) or 'step.result:path|unit' (any result field, unit stated)."""
    step_id, _, rest = ref.partition(".")
    if step_id not in step_results:
        raise PipelineError(f"Binding source '{ref}': step '{step_id}' has not run before this step.", "invalid_binding", source=ref)
    record = step_results[step_id]
    if rest.startswith("result:"):
        path, _, unit = rest[len("result:"):].partition("|")
        if not unit:
            raise PipelineError(f"Binding source '{ref}' must state its unit after '|'.", "invalid_binding", source=ref)
        try:
            return resolve_path(record["result"], path), unit.replace("{concentration_unit}", record["inputs"].get("concentration_unit", "mol/L"))
        except (KeyError, IndexError, TypeError):
            raise PipelineError(f"Binding source '{ref}' not found in the result of '{step_id}'.", "invalid_binding", source=ref) from None
    if rest not in record["outputs"]:
        raise PipelineError(f"Binding source '{ref}': '{step_id}' has no output '{rest}'.", "invalid_binding", source=ref)
    return record["outputs"][rest]["value"], record["outputs"][rest]["unit"]


def run_pipeline(spec: dict) -> dict:
    steps = spec.get("steps") if isinstance(spec, dict) else None
    if not isinstance(steps, list) or not 2 <= len(steps) <= MAX_STEPS:
        raise PipelineError(f"A multi-model experiment needs between 2 and {MAX_STEPS} steps.")
    results: dict[str, dict] = {}
    trace, warnings, timescales = [], [], []
    upstream: dict[str, set[str]] = {}  # step -> every earlier step it depends on (through bindings)
    for position, step in enumerate(steps, start=1):
        if not isinstance(step, dict) or not isinstance(step.get("id"), str) or step["id"] in results:
            raise PipelineError(f"Step {position} needs a unique id.")
        if ("model" in step) == ("adapter" in step):
            raise PipelineError(f"Step '{step['id']}' must name exactly one model or one adapter.")
        if "adapter" in step and step["adapter"] not in ADAPTERS:
            raise PipelineError(f"Unknown adapter '{step['adapter']}'.", "unknown_adapter")
        inputs = copy.deepcopy(step.get("inputs", {}))
        if not isinstance(inputs, dict) or not isinstance(step.get("bind", []), list):
            raise PipelineError(f"Step '{step['id']}': inputs must be an object and bind a list.")
        conversions = []
        depends: set[str] = set()
        for binding in step.get("bind", []):
            if not isinstance(binding, dict):
                raise PipelineError(f"Step '{step['id']}': each binding is an object {{from, to}}.", "invalid_binding")
            value, src_unit = _source(results, str(binding.get("from", "")))
            source_id = str(binding["from"]).partition(".")[0]
            depends |= {source_id} | upstream[source_id]
            target = binding.get("to", "")
            dst_unit = _target_unit(step, inputs, target)
            if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
                raise PipelineError(f"Binding {binding.get('from')} → {target}: the source value is not a finite number.", "invalid_binding")
            if dst_unit is None:
                raise PipelineError(f"Binding target '{target}' has no declared unit: refusing an unchecked transfer.", "invalid_binding")
            try:
                converted = units.convert(value, src_unit, dst_unit)
            except units.UnitError as exc:
                raise PipelineError(f"Incompatible variables {binding.get('from')} [{src_unit}] → {step['id']}.{target} [{dst_unit}]: {exc}",
                                    "incompatible_variables", source=binding.get("from"), target=target, source_unit=src_unit, target_unit=dst_unit) from exc
            _set_path(inputs, target, converted)
            conversions.append({"from": binding["from"], "to": target, "value": value, "unit": src_unit, "converted_value": converted, "converted_unit": dst_unit})
        try:
            if "model" in step:
                env = model_registry.run_model(step["model"], inputs)
                record = {"kind": "model", "model_id": step["model"], "model_version": env["model_version"], "inputs": env["inputs"], "outputs": env["outputs"],
                          "result": env["result"], "warnings": env["warnings"], "assumptions": env["assumptions"], "provenance": env["provenance"],
                          "maturity": model_registry.get_contract(step["model"])["maturity"]}
            else:
                adapter = ADAPTERS[step["adapter"]]
                out = adapter["function"](inputs)
                record = {"kind": "adapter", "adapter": step["adapter"], "inputs": inputs, "result": out,
                          "outputs": {k: {"value": out[k], "unit": u} for k, u in adapter["outputs"].items()}, "warnings": [],
                          "assumptions": adapter["assumptions"], "equations": adapter["equations"],
                          "maturity": {**adapter["maturity"], "label_fr": next(l["label_fr"] for l in maturity.LEVELS if l["id"] == adapter["maturity"]["level"])}}
                if out.get("linear_range_ok") is False:
                    warnings.append({"code": "absorbance_out_of_linear_range", "step": step["id"], "message": "Absorbance above ~2: Beer–Lambert linearity is doubtful."})
                if "timescale_s" in out:
                    timescales.append((step["id"], out["timescale_s"]))
        except (ContractError, ValueError) as exc:
            raise PipelineError(f"Step '{step['id']}' failed: {exc}", getattr(exc, "code", "step_failed"), step=step["id"]) from exc
        record["conversions"] = conversions
        upstream[step["id"]] = depends
        # A stationary value (reached after ~τ) feeding a dynamic step of comparable duration is inconsistent.
        # Only a duration stated in the step (not a model default) describes the experiment being chained.
        duration = (inputs.get("duration") or inputs.get("duration_s")) if record["kind"] == "model" else None
        for source_step, tau in timescales:
            if source_step in depends and isinstance(duration, (int, float)) and tau > 0.1 * duration:
                warnings.append({"code": "timescale_mismatch", "step": step["id"], "source": source_step,
                                 "message": f"The time scale of '{source_step}' ({tau:.3g} s) is not small compared with the duration of '{step['id']}' ({duration:.3g} s): "
                                            "the stationary assumption passed downstream is not valid."})
        results[step["id"]] = record
        trace.append({"step": step["id"], "position": position, **{k: record[k] for k in record if k != "result"}})
    ranks = {l["id"]: l["rank"] for l in maturity.LEVELS}
    lowest = min(trace, key=lambda r: ranks[r["maturity"]["level"]])["maturity"]["level"]
    limiting = [r["step"] for r in trace if r["maturity"]["level"] == lowest]
    report = spec.get("report") or [f"{trace[-1]['step']}.{name}" for name in trace[-1]["outputs"]]
    if not isinstance(report, list):
        raise PipelineError("report must be a list of step outputs.")
    final_outputs = {}
    for ref in report:
        value, unit = _source(results, str(ref))
        final_outputs[str(ref)] = {"value": value, "unit": unit}
    return {"pipeline": {"name": spec.get("name", "multi-model experiment"), "steps": len(trace)}, "engine": {"id": ENGINE_ID, "version": ENGINE_VERSION},
            "steps": trace, "final_outputs": final_outputs, "warnings": warnings,
            "maturity": {"level": lowest, "label_fr": next(l["label_fr"] for l in maturity.LEVELS if l["id"] == lowest), "limiting_steps": limiting,
                         "rule": "lowest maturity of the steps: combining models never raises the level of the weakest one"},
            "limitations": ["Each step keeps its own assumptions and limits (see steps[].assumptions).",
                            "Uncertainty is not propagated through the chain in this version (see analyses)."]}


def adapter_catalogue() -> dict:
    """Adapters as plain data (without the Python function) for the API."""
    return {name: {k: v for k, v in a.items() if k != "function"} for name, a in ADAPTERS.items()}


def example_pipelines() -> dict:
    """Two documented experiments: verified engines only, and one with a computable thermal link."""
    kinetics_inputs = {"species": [{"id": "A", "initial_concentration": 0.002}, {"id": "B", "initial_concentration": 0.0}],
                       "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.0}], "duration": 600.0, "dt": 1.0}
    return {
        "temperature_kinetics_absorbance": {
            "name": "Température → Arrhenius → cinétique → absorbance",
            "steps": [{"id": "arrhenius", "model": "arrhenius_reaction", "inputs": {"pre_exponential_s_inv": 1.0e7, "activation_energy_j_mol": 60000.0, "temperature_k": 310.0}},
                      {"id": "kinetics", "model": "mass_action_kinetics", "inputs": kinetics_inputs,
                       "bind": [{"from": "arrhenius.rate_constant", "to": "reactions[0].rate_constant"}, {"from": "arrhenius.result:summary.temperature_k|K", "to": "temperature_k"}]},
                      {"id": "absorbance", "adapter": "beer_lambert", "inputs": {"epsilon_l_per_mol_cm": 500.0, "path_length_cm": 1.0},
                       "bind": [{"from": "kinetics.result:summary.final_concentrations.B|{concentration_unit}", "to": "concentration_mol_l"}]}],
            "report": ["arrhenius.rate_constant", "kinetics.result:summary.final_concentrations.B|{concentration_unit}", "absorbance.absorbance"]},
        "joule_heating_kinetics": {
            "name": "Circuit CC → échauffement → Arrhenius → cinétique",
            "steps": [{"id": "circuit", "model": "dc_resistive_network", "inputs": {"source_voltage": 12.0, "resistors": [{"id": "heater", "a": "S", "b": "0", "resistance_ohm": 48.0}]}},
                      {"id": "heating", "adapter": "lumped_steady_heating", "inputs": {"ambient_temperature_k": 298.15, "thermal_resistance_k_per_w": 4.0, "thermal_capacitance_j_per_k": 5.0},
                       "bind": [{"from": "circuit.total_resistor_power", "to": "power_w"}]},
                      {"id": "arrhenius", "model": "arrhenius_reaction", "inputs": {"pre_exponential_s_inv": 1.0e7, "activation_energy_j_mol": 60000.0},
                       "bind": [{"from": "heating.temperature_k", "to": "temperature_k"}]},
                      {"id": "kinetics", "model": "mass_action_kinetics", "inputs": kinetics_inputs,
                       "bind": [{"from": "arrhenius.rate_constant", "to": "reactions[0].rate_constant"}, {"from": "heating.temperature_k", "to": "temperature_k"}]}],
            "report": ["circuit.total_resistor_power", "heating.temperature_k", "heating.thermal_time_constant_s", "arrhenius.rate_constant",
                       "kinetics.result:summary.final_concentrations.B|{concentration_unit}"]},
    }
