"""Experiment lifecycle shared by the API: run → schema-2 dossier → save → verify → replay → export/import.

Each saving endpoint goes through this module so that every record uses the same dossier
format (see dossier.py). Replay is available only for models registered in REPLAYERS: the
saved configuration is re-run with the current engine, and the new results are compared
with the recorded ones within the published numerical uncertainties.
"""
from __future__ import annotations

import math
from datetime import datetime, timezone
from typing import Any, Callable

import chemical_kinetics
import electrical_circuits
import reaction_stoichiometry
import engine as model_engine
import history
import lab_designer
import linked_measurements
import data_catalog
import fitting
import pipelines
import trace_package
import protocol_engine
import workbench_circuit
import workbench_transient
from dossier import build_dossier, dossier_content_hash, legacy_model_id, verify_dossier
from equipment_models import apply_equipment_operating_effects, apply_material_flow_model
from version import APP_VERSION

EXPORT_FORMAT_DOSSIER = "virtual-lab-dossier"
EXPORT_FORMAT_HISTORY = "virtual-lab-history"
EXPORT_FORMAT_VERSION = 1
MAX_IMPORT_RECORDS = 500


class ServiceError(ValueError):
    """Request refused by the lifecycle (with an HTTP status code)."""

    def __init__(self, message: str, status: int = 400, **details):
        super().__init__(message)
        self.status = status
        self.details = details


def _save(dossier: dict[str, Any]) -> dict[str, Any]:
    dossier["history_record"] = history.save_experiment(dossier)
    # v6.4: event journal (model, engine, configuration hash, seeds) for the traceability package.
    trace_package.log_event(dossier["history_record"]["id"], "saved", model_id=dossier.get("model_id"), engine=dossier.get("engine"),
                            app_version=dossier.get("app_version"), configuration_hash=dossier.get("configuration_hash"),
                            dossier_hash=dossier.get("dossier_hash"), seeds=trace_package.seeds(dossier.get("configuration", {})),
                            replay_of=dossier.get("replay_of"))
    return dossier


# ---- running and saving ----------------------------------------------------------------------

WORKBENCH_ENGINE = ("workbench_dc", f"topology-{workbench_circuit.ENGINE_VERSION}+nodal-{electrical_circuits.ENGINE_VERSION}")


def _workbench_configuration(request: dict[str, Any]) -> dict[str, Any]:
    return {"components": request.get("components", []), "connections": request.get("connections", [])}


def run_workbench(request: dict[str, Any]) -> dict[str, Any]:
    result = workbench_circuit.solve_workbench_circuit(request)
    dossier = build_dossier(result, model_id="electrical_workbench_dc", title=request.get("name") or "Circuit CC — paillasse virtuelle",
                            question=request.get("question") or "", configuration=_workbench_configuration(request),
                            engine_id=WORKBENCH_ENGINE[0], engine_version=WORKBENCH_ENGINE[1])
    return _save(dossier)


def run_protocol(request: dict[str, Any]) -> dict[str, Any]:
    result = protocol_engine.execute_protocol(request)
    configuration = {k: request.get(k) for k in ("name", "workflow_id", "components", "equipment", "protocol_steps", "material_flows", "measurements") if k in request}
    dossier = build_dossier(result, model_id="structured_protocol", title=request.get("name") or "Structured protocol",
                            configuration=configuration, engine_id=protocol_engine.ENGINE_ID, engine_version=protocol_engine.ENGINE_VERSION,
                            data_status="protocol_trace")
    return _save(dossier)


def run_lab(request: dict[str, Any]) -> dict[str, Any]:
    validation = protocol_engine.validate_protocol(request)
    if not validation["valid"]:
        raise ServiceError("Protocol validation failed. Resolve protocol issues before running.", 400, validation=validation)
    result = lab_designer.run_lab_experiment(request)
    result["results"] = apply_material_flow_model(request, result.get("results", {}))
    result["results"] = apply_equipment_operating_effects(request, result.get("results", {}))
    result["protocol_trace"] = protocol_engine.execute_protocol(request, result.get("results"))
    configuration = {**result.get("configuration", {}), "workflow_id": result.get("workflow_id"),
                     "protocol_steps": request.get("protocol_steps", []), "material_flows": request.get("material_flows", []),
                     "measurements": request.get("measurements", [])}
    status = "completed" if result.get("results", {}).get("computed_scientific_result") is not False else "workflow_only"
    dossier = build_dossier(result, model_id=result.get("workflow_id", "virtual_lab_workflow"), title=result.get("name") or "Virtual lab experiment",
                            configuration=configuration, engine_id=lab_designer.ENGINE_ID, engine_version=lab_designer.ENGINE_VERSION, status=status)
    return _save(dossier)


def run_model_experiment(request: dict[str, Any]) -> dict[str, Any]:
    result = model_engine.run_experiment(request)
    dossier = build_dossier(result, model_id=result["model"]["id"], title=result.get("name"), question=result.get("question"),
                            configuration=result["configuration"], engine_id=model_engine.ENGINE_ID, engine_version=model_engine.ENGINE_VERSION,
                            data_status="model_output")
    return _save(dossier)


TRANSIENT_KEYS = ("components", "connections", "initial_voltage_v", "initial_current_a", "duration_s", "points")
TRANSIENT_ENGINE = (workbench_transient.ENGINE_ID, f"{workbench_transient.ENGINE_VERSION}+nodal-{electrical_circuits.ENGINE_VERSION}")


def run_workbench_transient(request: dict[str, Any]) -> dict[str, Any]:
    result = workbench_transient.solve_workbench_transient(request)
    configuration = {k: request[k] for k in TRANSIENT_KEYS if k in request}
    dossier = build_dossier(result, model_id="electrical_workbench_transient", title=request.get("name") or f"Transitoire — {result['element']['name']}",
                            question=request.get("question") or "", configuration=configuration, engine_id=TRANSIENT_ENGINE[0], engine_version=TRANSIENT_ENGINE[1])
    return _save(dossier)


KINETICS_KEYS = ("species", "reactions", "duration", "dt", "temperature_k", "allow_unbalanced", "concentration_unit", "method", "rtol", "atol", "max_steps")
STOICHIOMETRY_KEYS = ("reaction_id", "reaction_name", "reactants", "products", "species")


def run_kinetics(request: dict[str, Any]) -> dict[str, Any]:
    result = chemical_kinetics.simulate_reaction_network(request)
    configuration = {k: request[k] for k in KINETICS_KEYS if k in request}
    dossier = build_dossier(result, model_id="chemical_kinetics_network", title=request.get("name") or "Cinétique chimique — réseau de réactions",
                            question=request.get("question") or "", configuration=configuration,
                            engine_id=chemical_kinetics.ENGINE_ID, engine_version=chemical_kinetics.ENGINE_VERSION)
    return _save(dossier)


def run_stoichiometry(request: dict[str, Any]) -> dict[str, Any]:
    result = reaction_stoichiometry.calculate_stoichiometry(request)
    configuration = {k: request[k] for k in STOICHIOMETRY_KEYS if k in request}
    dossier = build_dossier(result, model_id="chemical_stoichiometry", title=request.get("name") or f"Stœchiométrie — {request.get('reaction_name') or request.get('reaction_id', 'réaction')}",
                            question=request.get("question") or "", configuration=configuration,
                            engine_id=reaction_stoichiometry.ENGINE_ID, engine_version=reaction_stoichiometry.ENGINE_VERSION)
    return _save(dossier)


PIPELINE_KEYS = ("name", "steps", "report")


def run_pipeline(request: dict[str, Any]) -> dict[str, Any]:
    """Multi-model experiment (v5.8): every step's inputs, conversions and outputs are kept in the dossier."""
    configuration = {k: request[k] for k in PIPELINE_KEYS if k in request}
    result = pipelines.run_pipeline(configuration)
    dossier = build_dossier(result, model_id="multi_model_pipeline", title=request.get("name") or "Expérience multi-modèles",
                            question=request.get("question") or "", configuration=configuration,
                            engine_id=pipelines.ENGINE_ID, engine_version=pipelines.ENGINE_VERSION)
    return _save(dossier)


FIT_KEYS = ("dataset_id", "x_column", "y_column", "where", "model", "start", "validation", "drop_missing", "x", "y", "x_unit", "y_unit")


def _fit_inputs(configuration: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any] | None]:
    """Fit request and data reference; data come from the catalogue (checked by content hash) or are given inline."""
    request = {k: configuration[k] for k in ("model", "start", "validation") if k in configuration}
    if not configuration.get("dataset_id"):
        request.update({k: configuration.get(k) for k in ("x", "y", "x_unit", "y_unit")})
        return request, None
    entry = data_catalog.get_entry(configuration["dataset_id"])
    expected = configuration.get("content_sha256")
    if expected and entry["content_sha256"] != expected:
        raise ServiceError("The dataset changed since this fit was saved (content hash differs); replay refused.", 409, error_code="dataset_changed")
    where = configuration.get("where") or {}
    xs = data_catalog.column_values(entry, configuration.get("x_column"), where)
    ys = data_catalog.column_values(entry, configuration.get("y_column"), where)
    dropped = [i for i, (x, y) in enumerate(zip(xs, ys)) if x is None or y is None]
    if dropped and not configuration.get("drop_missing"):
        raise ServiceError(f"{len(dropped)} row(s) have a missing x or y value; set drop_missing to exclude them explicitly.", 400, error_code="missing_values")
    keep = [i for i in range(len(xs)) if i not in dropped]
    columns = {c["name"]: c for c in entry["columns"]}
    request.update({"x": [xs[i] for i in keep], "y": [ys[i] for i in keep], "x_unit": columns[configuration["x_column"]].get("unit") or "1",
                    "y_unit": columns[configuration["y_column"]].get("unit") or "1"})
    data = {"id": entry["id"], "version": entry["version"], "content_sha256": entry["content_sha256"], "data_kind": entry["data_kind"],
            "source_ids": entry.get("source_ids", []), "x_column": configuration["x_column"], "y_column": configuration["y_column"], "where": where,
            "rows_used": len(keep), "rows_dropped_missing": dropped}
    return request, data


def _run_fit_configuration(configuration: dict[str, Any]) -> dict[str, Any]:
    request, data = _fit_inputs(configuration)
    result = fitting.fit(request)
    if data:
        result["data"] = data
    return result


def run_fit(request: dict[str, Any]) -> dict[str, Any]:
    """Fit a model to catalogue (or inline) data; the dossier records the dataset id, version and content hash."""
    configuration = {k: request[k] for k in FIT_KEYS if k in request}
    if configuration.get("dataset_id"):
        configuration["content_sha256"] = data_catalog.get_entry(configuration["dataset_id"])["content_sha256"]
    result = _run_fit_configuration(configuration)
    title = request.get("name") or f"Ajustement {result['model']} — {configuration.get('dataset_id', 'données saisies')}"
    dossier = build_dossier(result, model_id="model_fit", title=title, question=request.get("question") or "", configuration=configuration,
                            engine_id=fitting.ENGINE_ID, engine_version=fitting.ENGINE_VERSION, data_status="model_fit_to_data")
    return _save(dossier)


# ---- verification ----------------------------------------------------------------------------

def _record(experiment_id: int) -> dict[str, Any]:
    record = history.get_experiment_record(experiment_id)
    if not record:
        raise ServiceError("Experiment not found", 404)
    return record


def verify(experiment_id: int) -> dict[str, Any]:
    record = _record(experiment_id)
    result = {"experiment_id": experiment_id, **verify_dossier(record["dossier"], record["configuration_hash"], record["dossier_hash"])}
    trace_package.log_event(experiment_id, "verified", valid=result.get("valid"), level=result.get("level"))
    return result


# ---- instruments linked to saved results (v4.7) ----------------------------------------------

LINKED_KEYS = ("quantity", "instrument_id", "seed", "resolution", "instrument_bias", "calibration_offset", "calibration_gain",
               "calibration_uncertainty_sd", "epsilon_l_per_mol_cm", "path_length_cm")


def _verified_source(experiment_id: Any, expected_hash: str | None = None) -> dict[str, Any]:
    if isinstance(experiment_id, bool) or not isinstance(experiment_id, int):
        raise ServiceError("source_experiment_id must be an integer.")
    record = _record(experiment_id)
    integrity = verify_dossier(record["dossier"], record["configuration_hash"], record["dossier_hash"])
    if not integrity["valid"] or integrity["level"] != "full":
        raise ServiceError("The source dossier must pass a full integrity check before it can be measured.", 409, integrity=integrity)
    if expected_hash is not None and record["dossier"].get("dossier_hash") != expected_hash:
        raise ServiceError("The source dossier differs from the one originally measured; replay refused.", 409)
    return record["dossier"]


def quantities(experiment_id: int) -> dict[str, Any]:
    dossier = _record(experiment_id)["dossier"]
    found = linked_measurements.measurable_quantities(dossier)
    units = sorted({q["unit"] for q in found})
    return {"experiment_id": experiment_id, "model_id": dossier.get("model_id"), "quantities": found,
            "instruments_by_unit": {u: linked_measurements.instruments_for_unit(u) for u in units}}


def _linked_run(configuration: dict[str, Any]) -> dict[str, Any]:
    source = _verified_source(configuration.get("source_experiment_id"), configuration.get("source_dossier_hash"))
    try:
        return linked_measurements.measure(source, configuration)
    except linked_measurements.MeasurementError as exc:
        raise ServiceError(str(exc)) from exc


def measure_linked(request: dict[str, Any]) -> dict[str, Any]:
    source = _verified_source(request.get("source_experiment_id"))
    configuration = {"source_experiment_id": request["source_experiment_id"], "source_dossier_hash": source.get("dossier_hash"),
                     **{k: request[k] for k in LINKED_KEYS if k in request}}
    result = _linked_run(configuration)
    title = f"Mesure simulée — {result['linked_quantity']['label']} ({result['instrument']['name']})"
    dossier = build_dossier(result, model_id="instrument_reading", title=title, configuration=configuration,
                            engine_id=linked_measurements.ENGINE_ID, engine_version=linked_measurements.ENGINE_VERSION,
                            data_status="simulated_measurement")
    return _save(dossier)


def _compare_reading(original: dict[str, Any], replayed: dict[str, Any]) -> dict[str, Any]:
    budget_o, budget_r = original.get("uncertainty_budget", {}), replayed.get("uncertainty_budget", {})
    return _compare_values([("indicated reading", original.get("indicated_reading"), replayed.get("indicated_reading")),
                            ("combined standard uncertainty", budget_o.get("combined_standard_uncertainty"), budget_r.get("combined_standard_uncertainty")),
                            ("reference value", original.get("theoretical_value"), replayed.get("theoretical_value"))])


# ---- replay ----------------------------------------------------------------------------------

def _close(a: float, b: float, tolerance: float) -> bool:
    return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= tolerance


def _compare_workbench(original: dict[str, Any], replayed: dict[str, Any]) -> dict[str, Any]:
    """Compare node voltages, branch currents and source current within the published uncertainties."""
    differences, compared, max_diff = [], 0, 0.0
    o_unc, r_unc = original.get("node_voltage_uncertainty_v") or {}, replayed.get("node_voltage_uncertainty_v") or {}

    def check(name, a, b, uncertainty):
        nonlocal compared, max_diff
        compared += 1
        diff = abs(a - b)
        max_diff = max(max_diff, diff)
        # Pre-v4.5 dossiers publish no uncertainty: a relative tolerance of 1e-9 is used instead.
        tolerance = max(4 * uncertainty, 1e-9 * max(abs(a), abs(b)), 1e-15)
        if not _close(a, b, tolerance):
            differences.append({"quantity": name, "original": a, "replay": b, "difference": diff, "tolerance": tolerance})

    for node, value in (original.get("node_voltages_v") or {}).items():
        if node not in (replayed.get("node_voltages_v") or {}):
            differences.append({"quantity": f"V({node})", "original": value, "replay": None})
            continue
        check(f"V({node})", value, replayed["node_voltages_v"][node], o_unc.get(node, 0.0) + r_unc.get(node, 0.0))
    replay_branches = {b["id"]: b for b in replayed.get("branches", [])}
    for branch in original.get("branches", []):
        other = replay_branches.get(branch["id"])
        if other is None:
            differences.append({"quantity": f"I({branch['id']})", "original": branch["current_a"], "replay": None})
            continue
        unc = branch.get("current_rounding_uncertainty_a", 0.0) + other.get("current_rounding_uncertainty_a", 0.0)
        check(f"I({branch.get('display_name', branch['id'])})", branch["current_a"], other["current_a"], unc)
    check("I(source)", original.get("source_current_a", 0.0), replayed.get("source_current_a", 0.0), 0.0)
    return {"identical_within_tolerance": not differences, "compared_values": compared, "max_abs_difference": max_diff,
            "differences": differences[:20]}


def _compare_values(pairs, relative=1e-12):
    """Compare (name, original, replay) triples; deterministic engines must reproduce to round-off."""
    differences, max_diff = [], 0.0
    for name, a, b in pairs:
        if not isinstance(a, (int, float)) or not isinstance(b, (int, float)):
            if a != b:
                differences.append({"quantity": name, "original": a, "replay": b})
            continue
        diff = abs(a - b); max_diff = max(max_diff, diff)
        tolerance = max(relative * max(abs(a), abs(b)), 1e-15)
        if diff > tolerance:
            differences.append({"quantity": name, "original": a, "replay": b, "difference": diff, "tolerance": tolerance})
    return {"identical_within_tolerance": not differences, "compared_values": len(pairs), "max_abs_difference": max_diff,
            "differences": differences[:20]}


def _compare_kinetics(original: dict[str, Any], replayed: dict[str, Any]) -> dict[str, Any]:
    pairs = [(f"[{sid}](t_final)", original["summary"]["final_concentrations"].get(sid), value)
             for sid, value in replayed["summary"]["final_concentrations"].items()]
    for i, (row_o, row_r) in enumerate(zip(original.get("rows", []), replayed.get("rows", []))):
        pairs += [(f"[{sid}](t={row_r['time']:g})", row_o.get(sid), row_r[sid]) for sid in replayed["species_ids"]]
    if len(original.get("rows", [])) != len(replayed.get("rows", [])):
        pairs.append(("number of sampled rows", len(original.get("rows", [])), len(replayed.get("rows", []))))
    return _compare_values(pairs)


def _compare_stoichiometry(original: dict[str, Any], replayed: dict[str, Any]) -> dict[str, Any]:
    pairs = [("reaction extent (mol)", original.get("reaction_extent_mol"), replayed.get("reaction_extent_mol")),
             ("limiting reactants", original.get("limiting_reactants"), replayed.get("limiting_reactants"))]
    for key in ("reactant_amounts_remaining_mol", "product_amounts_theoretical_mol"):
        pairs += [(f"{key}[{sid}]", (original.get(key) or {}).get(sid), value) for sid, value in (replayed.get(key) or {}).items()]
    return _compare_values(pairs)


def _compare_transient(original: dict[str, Any], replayed: dict[str, Any]) -> dict[str, Any]:
    pairs = [(k, original.get(k), replayed.get(k)) for k in ("time_constant_s", "thevenin_voltage_v", "thevenin_resistance_ohm", "final_value")]
    pairs += [(f"{key}(t={rr['time_s']:.3g})", ro.get(key), rr[key]) for ro, rr in zip(original.get("rows", []), replayed.get("rows", []))
              for key in ("element_voltage_v", "element_current_a")]
    return _compare_values(pairs, relative=1e-9)


def _compare_pipeline(original: dict[str, Any], replayed: dict[str, Any]) -> dict[str, Any]:
    pairs = [(f"final {name}", (original.get("final_outputs") or {}).get(name, {}).get("value"), out["value"])
             for name, out in replayed["final_outputs"].items()]
    original_steps = {s["step"]: s for s in original.get("steps", [])}
    for step in replayed["steps"]:
        before = original_steps.get(step["step"], {}).get("outputs", {})
        pairs += [(f"{step['step']}.{name}", (before.get(name) or {}).get("value"), out["value"]) for name, out in step["outputs"].items()]
    pairs.append(("pipeline maturity", (original.get("maturity") or {}).get("level"), replayed["maturity"]["level"]))
    return _compare_values(pairs, relative=1e-9)


def _compare_fit(original: dict[str, Any], replayed: dict[str, Any]) -> dict[str, Any]:
    pairs = []
    for name, p in replayed["parameters"].items():
        before = (original.get("parameters") or {}).get(name, {})
        pairs += [(f"{name}", before.get("value"), p["value"]), (f"SE({name})", before.get("standard_error"), p["standard_error"])]
    pairs.append(("residual standard error", original.get("residual_standard_error"), replayed["residual_standard_error"]))
    return _compare_values(pairs, relative=1e-9)


REPLAYERS: dict[str, tuple[Callable[[dict], dict], Callable[[dict, dict], dict], tuple[str, str]]] = {
    "electrical_workbench_transient": (workbench_transient.solve_workbench_transient, _compare_transient, TRANSIENT_ENGINE),
    "electrical_workbench_dc": (lambda config: workbench_circuit.solve_workbench_circuit(_workbench_configuration(config)), _compare_workbench, WORKBENCH_ENGINE),
    "chemical_kinetics_network": (chemical_kinetics.simulate_reaction_network, _compare_kinetics, (chemical_kinetics.ENGINE_ID, chemical_kinetics.ENGINE_VERSION)),
    "chemical_stoichiometry": (reaction_stoichiometry.calculate_stoichiometry, _compare_stoichiometry, (reaction_stoichiometry.ENGINE_ID, reaction_stoichiometry.ENGINE_VERSION)),
    "model_fit": (_run_fit_configuration, _compare_fit, (fitting.ENGINE_ID, fitting.ENGINE_VERSION)),
    "multi_model_pipeline": (pipelines.run_pipeline, _compare_pipeline, (pipelines.ENGINE_ID, pipelines.ENGINE_VERSION)),
    "instrument_reading": (lambda config: _linked_run(config), lambda o, r: _compare_reading(o, r), (linked_measurements.ENGINE_ID, linked_measurements.ENGINE_VERSION)),
}


def register_replayer(model_id: str, run: Callable[[dict], dict], compare: Callable[[dict, dict], dict], engine: tuple[str, str]) -> None:
    REPLAYERS[model_id] = (run, compare, engine)


def replayable_models() -> list[str]:
    return sorted(REPLAYERS)


def replay(experiment_id: int) -> dict[str, Any]:
    record = _record(experiment_id)
    original = record["dossier"]
    model_id = original.get("model_id") or legacy_model_id(original)
    if model_id not in REPLAYERS:
        raise ServiceError(f"Replay is not available for '{model_id}'. Replayable models: {', '.join(replayable_models())}.", 400)
    integrity = verify_dossier(original, record["configuration_hash"], record["dossier_hash"])
    if not integrity["valid"]:
        raise ServiceError("Saved dossier integrity check failed; replay refused.", 409, integrity=integrity)
    run, compare, engine = REPLAYERS[model_id]
    configuration = original.get("configuration", {})
    result = run(configuration)
    dossier = build_dossier(result, model_id=model_id, title=str(original.get("title", model_id))[:180] + " (replay)",
                            question=original.get("question", ""), configuration=configuration, engine_id=engine[0], engine_version=engine[1],
                            data_status=original.get("data_status", "simulated_calculation"))
    comparison = compare(original, result)
    comparison["engine_original"] = original.get("engine") or {"id": "unrecorded", "version": "pre-v4.5"}
    comparison["engine_replay"] = dossier["engine"]
    comparison["engine_changed"] = comparison["engine_original"] != comparison["engine_replay"]
    dossier["replay_of"] = experiment_id
    dossier["replay_comparison"] = comparison
    dossier["dossier_hash"] = dossier_content_hash(dossier)
    saved = _save(dossier)
    trace_package.log_event(experiment_id, "replayed", replay_id=saved["history_record"]["id"], identical=comparison.get("identical_within_tolerance"),
                            engine_changed=comparison.get("engine_changed"))
    return saved


# ---- export / import -------------------------------------------------------------------------

def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def export_one(experiment_id: int) -> dict[str, Any]:
    record = _record(experiment_id)
    trace_package.log_event(experiment_id, "exported", format=EXPORT_FORMAT_DOSSIER)
    return {"format": EXPORT_FORMAT_DOSSIER, "format_version": EXPORT_FORMAT_VERSION, "exported_at": _now(), "app_version": APP_VERSION,
            "record": {"id": record["id"], "created_at": record["created_at"]}, "dossier": record["dossier"]}


def export_all() -> dict[str, Any]:
    records = [history.get_experiment_record(i) for i in history.all_experiment_ids()]
    return {"format": EXPORT_FORMAT_HISTORY, "format_version": EXPORT_FORMAT_VERSION, "exported_at": _now(), "app_version": APP_VERSION,
            "record_count": len(records),
            "records": [{"id": r["id"], "created_at": r["created_at"], "dossier": r["dossier"]} for r in records]}


def import_bundle(bundle: dict[str, Any]) -> dict[str, Any]:
    """Import an exported dossier or history. All-or-nothing: any altered dossier rejects the whole file."""
    fmt = bundle.get("format")
    if fmt == EXPORT_FORMAT_DOSSIER:
        entries = [{"id": bundle.get("record", {}).get("id"), "created_at": bundle.get("record", {}).get("created_at"), "dossier": bundle.get("dossier")}]
    elif fmt == EXPORT_FORMAT_HISTORY:
        entries = bundle.get("records")
    else:
        raise ServiceError(f"Unknown export format {fmt!r}: expected '{EXPORT_FORMAT_DOSSIER}' or '{EXPORT_FORMAT_HISTORY}'.")
    if not isinstance(bundle.get("format_version"), int) or bundle["format_version"] > EXPORT_FORMAT_VERSION:
        raise ServiceError(f"Unsupported export format_version {bundle.get('format_version')!r} (this version reads up to {EXPORT_FORMAT_VERSION}).")
    if not isinstance(entries, list) or not entries or len(entries) > MAX_IMPORT_RECORDS:
        raise ServiceError(f"The file must contain between 1 and {MAX_IMPORT_RECORDS} dossiers.")
    checked, rejected = [], []
    for position, entry in enumerate(entries, start=1):
        dossier = entry.get("dossier") if isinstance(entry, dict) else None
        if not isinstance(dossier, dict):
            rejected.append({"position": position, "reason": "missing dossier object"}); continue
        integrity = verify_dossier(dossier)
        if not integrity["valid"] or integrity["level"] == "unverifiable":
            rejected.append({"position": position, "original_id": entry.get("id"), "reason": integrity["reason"]}); continue
        checked.append((entry, dossier, integrity["level"]))
    if rejected:
        raise ServiceError("Import refused: some dossiers fail their integrity check. Nothing was imported.", 409, rejected=rejected)
    existing = {history.get_experiment_record(i)["dossier"].get("dossier_hash") for i in history.all_experiment_ids()} - {None}
    imported, skipped = [], []
    for entry, dossier, level in checked:
        if dossier.get("dossier_hash") and dossier["dossier_hash"] in existing:
            skipped.append({"original_id": entry.get("id"), "reason": "already present (same dossier hash)"}); continue
        copy = dict(dossier)
        copy.pop("history_record", None)
        copy["imported_from"] = {"original_id": entry.get("id"), "original_created_at": entry.get("created_at"),
                                 "source_app_version": bundle.get("app_version"), "imported_at": _now(), "verification_level": level}
        saved = history.save_experiment(copy)
        trace_package.log_event(saved["id"], "imported", original_id=entry.get("id"), verification_level=level)
        existing.add(copy.get("dossier_hash"))
        imported.append({"original_id": entry.get("id"), "new_id": saved["id"], "verification_level": level})
    return {"imported": imported, "skipped": skipped, "imported_count": len(imported), "skipped_count": len(skipped)}
