"""Structured protocol graph validation and execution trace.

This layer validates workflow structure, material transfers and measurement
instrument capabilities. It records protocol steps as a reproducible execution
trace; it does not pretend that a step without a connected solver was physically
simulated.
"""
from __future__ import annotations
from datetime import datetime, timezone
import hashlib, json, math
from typing import Any
from lab_designer import COMPONENTS, EQUIPMENT, validate_experiment

ENGINE_ID = "structured_protocol"
ENGINE_VERSION = "1.0"
MAX_STEPS = 40
MAX_FLOWS = 100
MEASUREMENT_CAPABILITIES = {
    "temperature": "measure_temperature",
    "absorbance": "measure_absorbance",
    "ph": "measure_ph",
    "mass": "measure_mass",
    "image": "image_sample",
    "volume": "measure_volume",
    "generic_observation": None,
}
MEASUREMENT_VARIABLE_PREFIXES = {
    "temperature": ("T", "left_temp_c", "right_temp_c", "initial_temp_c"),
    "absorbance": ("absorbance", "A"),
    "ph": ("pH", "ph"),
    "mass": ("mass",),
    "volume": ("volume",),
    "image": ("image",),
}

def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()

def _num(value: Any, label: str, minimum: float = 0.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value < minimum:
        raise ValueError(f"{label} must be a finite number >= {minimum}.")
    return float(value)

def validate_protocol(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ValueError("Protocol request must be an object.")
    steps = request.get("protocol_steps", [])
    flows = request.get("material_flows", [])
    measurements = request.get("measurements", [])
    selected_equipment = request.get("equipment", [])
    selected_components = request.get("components", [])
    if not isinstance(steps, list) or not 1 <= len(steps) <= MAX_STEPS:
        raise ValueError(f"Provide between 1 and {MAX_STEPS} protocol steps.")
    if not isinstance(flows, list) or len(flows) > MAX_FLOWS:
        raise ValueError(f"Material flows must be a list with at most {MAX_FLOWS} entries.")
    if not isinstance(measurements, list) or len(measurements) > MAX_STEPS:
        raise ValueError("Measurements must be a list with at most one per protocol step.")
    if not isinstance(selected_equipment, list) or not isinstance(selected_components, list):
        raise ValueError("Components and equipment must be lists.")
    eq_ids = {x.get("id") if isinstance(x, dict) else x for x in selected_equipment}
    comp_ids = {x.get("id") if isinstance(x, dict) else x for x in selected_components}
    issues: list[dict[str, str]] = []
    step_ids = []
    normalized_steps = []
    for index, step in enumerate(steps):
        if not isinstance(step, dict):
            issues.append({"severity":"error","code":"invalid_step","message":f"Step {index+1} must be an object."})
            continue
        sid = step.get("id", f"step_{index+1}")
        action = str(step.get("action", "")).strip()
        if not isinstance(sid, str) or not sid or len(sid) > 64 or sid in step_ids:
            issues.append({"severity":"error","code":"invalid_step_id","message":f"Step {index+1} has a missing, duplicate or invalid ID."})
            continue
        if not action or len(action) > 300:
            issues.append({"severity":"error","code":"invalid_step_action","message":f"Step {index+1} needs an action of 1–300 characters."})
        step_ids.append(sid)
        equipment_id = step.get("equipment_id") or None
        if equipment_id and equipment_id not in eq_ids:
            issues.append({"severity":"error","code":"step_equipment_not_selected","message":f"Step {index+1} uses equipment that is not selected: {equipment_id}."})
        try:
            duration = _num(step.get("duration_s", 0), f"Step {index+1} duration")
            if duration > 31_536_000:
                issues.append({"severity":"error","code":"duration_too_large","message":f"Step {index+1} duration exceeds one year."})
        except ValueError as exc:
            duration = 0
            issues.append({"severity":"error","code":"invalid_duration","message":str(exc)})
        normalized_steps.append({"id":sid,"action":action,"equipment_id":equipment_id,"duration_s":duration})
    if len(normalized_steps) != len(steps):
        # Avoid unsafe references after malformed IDs.
        pass
    ids = set(step_ids)
    edges = request.get("edges")
    if edges is None:
        edges = [{"from": step_ids[i], "to": step_ids[i+1]} for i in range(len(step_ids)-1)]
    if not isinstance(edges, list) or len(edges) > MAX_STEPS * 2:
        raise ValueError("Protocol edges must be a list with at most 80 entries.")
    normalized_edges = []
    adjacency = {sid: [] for sid in step_ids}
    indegree = {sid: 0 for sid in step_ids}
    seen_edges = set()
    for edge in edges:
        if not isinstance(edge, dict):
            issues.append({"severity":"error","code":"invalid_edge","message":"Each protocol edge must be an object."})
            continue
        source, target = edge.get("from"), edge.get("to")
        pair = (source, target)
        if source not in ids or target not in ids or source == target:
            issues.append({"severity":"error","code":"invalid_edge_reference","message":f"Invalid protocol dependency {source} → {target}."})
            continue
        if pair in seen_edges:
            issues.append({"severity":"warning","code":"duplicate_edge","message":f"Duplicate dependency {source} → {target}."})
            continue
        seen_edges.add(pair); adjacency[source].append(target); indegree[target] += 1
        normalized_edges.append({"from":source,"to":target})
    queue = [sid for sid in step_ids if indegree[sid] == 0]
    topo = []
    while queue:
        current = queue.pop(0); topo.append(current)
        for nxt in adjacency[current]:
            indegree[nxt] -= 1
            if indegree[nxt] == 0: queue.append(nxt)
    if len(topo) != len(step_ids):
        issues.append({"severity":"error","code":"protocol_cycle","message":"The protocol dependency graph contains a cycle."})
    for flow_i, flow in enumerate(flows):
        if not isinstance(flow, dict):
            issues.append({"severity":"error","code":"invalid_material_flow","message":f"Material flow {flow_i+1} must be an object."})
            continue
        cid = flow.get("component_id")
        source, target = flow.get("from_step"), flow.get("to_step")
        if cid not in comp_ids or cid not in COMPONENTS:
            issues.append({"severity":"error","code":"flow_component_missing","message":f"Material flow {flow_i+1} uses a component not selected in the inventory."})
        if source not in ids or target not in ids or source == target:
            issues.append({"severity":"error","code":"flow_step_invalid","message":f"Material flow {flow_i+1} must connect two distinct existing steps."})
        try:
            amount = _num(flow.get("amount"), f"Material flow {flow_i+1} amount", 0)
            if amount <= 0: raise ValueError(f"Material flow {flow_i+1} amount must be greater than zero.")
        except ValueError as exc:
            amount = 0
            issues.append({"severity":"error","code":"flow_amount_invalid","message":str(exc)})
        unit = str(flow.get("unit", "")).strip()
        if cid in COMPONENTS and unit and unit != COMPONENTS[cid]["unit"]:
            issues.append({"severity":"error","code":"flow_unit_mismatch","message":f"Material flow {flow_i+1} unit {unit} does not match catalog unit {COMPONENTS[cid]['unit']} for {COMPONENTS[cid]['name']}."})
        role = str(flow.get("role", "generic")).strip().lower()
        if role not in {"generic", "stock", "diluent"}:
            issues.append({"severity":"error","code":"flow_role_invalid","message":f"Material flow {flow_i+1} role must be generic, stock or diluent."})
        transfer_id = flow.get("transfer_equipment_id") or None
        if transfer_id:
            if transfer_id not in eq_ids or transfer_id not in EQUIPMENT:
                issues.append({"severity":"error","code":"flow_equipment_not_selected","message":f"Material flow {flow_i+1} uses transfer equipment that is not selected."})
            else:
                instrument = EQUIPMENT[transfer_id]
                if "transfer_liquid" not in instrument.get("capabilities", []):
                    issues.append({"severity":"error","code":"flow_equipment_incompatible","message":f"{instrument['name']} is not catalogued for liquid transfer."})
                if unit == "mL" and amount > float(instrument.get("max_volume_ml", 0)):
                    issues.append({"severity":"error","code":"flow_transfer_capacity","message":f"Transfer {flow_i+1} ({amount:g} mL) exceeds {instrument['name']} capacity ({instrument.get('max_volume_ml',0):g} mL). Split it into separately represented transfers or choose suitable equipment."})
        elif role in {"stock", "diluent"}:
            issues.append({"severity":"error","code":"flow_equipment_required","message":f"Flow {flow_i+1} has role {role}; select a liquid-transfer instrument so its capacity and uncertainty can be modeled."})
    if request.get("workflow_id") == "solution_dilution":
        labelled = [f for f in flows if isinstance(f,dict) and f.get("role") in {"stock","diluent"}]
        stock_count = sum(1 for f in labelled if f.get("role") == "stock")
        diluent_count = sum(1 for f in labelled if f.get("role") == "diluent")
        if labelled and (stock_count == 0 or diluent_count == 0):
            issues.append({"severity":"error","code":"dilution_flow_roles_incomplete","message":"Flow-driven dilution needs at least one stock flow and one diluent flow."})
        total_ml = sum(float(f.get("amount",0)) for f in labelled if f.get("unit") == "mL" and isinstance(f.get("amount"),(int,float)) and not isinstance(f.get("amount"),bool) and math.isfinite(f.get("amount")) and f.get("amount") >= 0)
        vessel_ids = [eid for eid in eq_ids if eid in EQUIPMENT and "hold_liquid" in EQUIPMENT[eid].get("capabilities",[])]
        if vessel_ids:
            max_vessel = max(float(EQUIPMENT[eid].get("max_volume_ml",0)) for eid in vessel_ids)
            if total_ml > max_vessel:
                issues.append({"severity":"error","code":"dilution_vessel_capacity","message":f"Declared stock/diluent total ({total_ml:g} mL) exceeds the largest selected liquid vessel capacity ({max_vessel:g} mL)."})
    # A material transfer is only structurally plausible if the protocol graph
    # contains a dependency path from its source step to its destination step.
    for flow_i, flow in enumerate(flows):
        if not isinstance(flow, dict):
            continue
        source, target = flow.get("from_step"), flow.get("to_step")
        if source in ids and target in ids and source != target:
            stack, visited = [source], set()
            while stack:
                node = stack.pop()
                if node == target:
                    break
                if node in visited:
                    continue
                visited.add(node)
                stack.extend(adjacency.get(node, []))
            else:
                issues.append({"severity":"error","code":"flow_without_dependency","message":f"Material flow {flow_i+1} has no dependency path from its source step to its destination step."})
    seen_measure_steps = set()
    normalized_measurements = []
    for m_i, measurement in enumerate(measurements):
        if not isinstance(measurement, dict):
            issues.append({"severity":"error","code":"invalid_measurement","message":f"Measurement {m_i+1} must be an object."}); continue
        sid = measurement.get("step_id")
        kind = measurement.get("kind")
        equipment_id = measurement.get("equipment_id")
        if sid not in ids:
            issues.append({"severity":"error","code":"measurement_step_missing","message":f"Measurement {m_i+1} references an unknown step."})
        if sid in seen_measure_steps:
            issues.append({"severity":"warning","code":"multiple_measurements","message":f"Step {sid} has multiple measurement definitions."})
        seen_measure_steps.add(sid)
        required = MEASUREMENT_CAPABILITIES.get(kind, "unsupported")
        if required == "unsupported":
            issues.append({"severity":"error","code":"measurement_kind_unsupported","message":f"Unsupported measurement type: {kind}."})
        elif required and (equipment_id not in eq_ids or equipment_id not in EQUIPMENT):
            issues.append({"severity":"error","code":"measurement_instrument_missing","message":f"Measurement {m_i+1} requires a selected instrument."})
        elif required and required not in EQUIPMENT[equipment_id].get("capabilities", []):
            issues.append({"severity":"error","code":"measurement_instrument_incompatible","message":f"Equipment {equipment_id} cannot perform {kind} measurement according to the catalogue."})
        label = str(measurement.get("label", kind or "measurement")).strip()
        if not label or len(label) > 120:
            issues.append({"severity":"error","code":"measurement_label_invalid","message":f"Measurement {m_i+1} needs a label of 1–120 characters."})
        target_variable = str(measurement.get("target_variable", "")).strip()
        sample_index = measurement.get("sample_index", -1)
        if isinstance(sample_index, bool) or not isinstance(sample_index, int) or sample_index < -1 or sample_index > 50000:
            issues.append({"severity":"error","code":"measurement_sample_index_invalid","message":f"Measurement {m_i+1} sample index must be -1 (last row) or an integer from 0 to 50000."})
        if kind and kind != "generic_observation" and not target_variable:
            issues.append({"severity":"warning","code":"measurement_target_missing","message":f"Measurement {m_i+1} has no solver output variable; it will remain a plan until a target variable is selected."})
        normalized_measurements.append({"step_id":sid,"kind":kind,"equipment_id":equipment_id,"label":label,"unit":str(measurement.get("unit","")).strip()[:32],"target_variable":target_variable,"sample_index":sample_index})
    errors = [x for x in issues if x["severity"] == "error"]
    return {
        "valid": not errors,
        "issues": issues,
        "steps": normalized_steps,
        "edges": normalized_edges,
        "material_flows": [
            {**flow, "role":str(flow.get("role","generic")).strip().lower(),
             "transfer_equipment_id":flow.get("transfer_equipment_id") or None}
            for flow in flows if isinstance(flow,dict)
        ],
        "measurements": normalized_measurements,
        "execution_order": topo if len(topo) == len(step_ids) else [],
        "summary": {"step_count":len(normalized_steps),"dependency_count":len(normalized_edges),"material_flow_count":len(flows),"measurement_count":len(normalized_measurements),"selected_component_count":len(comp_ids),"selected_equipment_count":len(eq_ids)},
        "protocol_sha256": _hash({"steps":normalized_steps,"edges":normalized_edges,"material_flows":flows,"measurements":normalized_measurements}),
        "interpretation": "Structural protocol validation only. Catalogue capabilities are indicative, not manufacturer certification or safety approval."
    }

def execute_protocol(request: dict[str, Any], solver_result: dict[str, Any] | None = None) -> dict[str, Any]:
    checked = validate_protocol(request)
    if not checked["valid"]:
        raise ValueError("Protocol cannot run: resolve all protocol validation errors first.")
    step_by_id = {step["id"]: step for step in checked["steps"]}
    flow_by_target = {}
    for flow in checked["material_flows"]:
        flow_by_target.setdefault(flow["to_step"], []).append(flow)
    elapsed = 0.0
    trace = []
    simulated_measurements = []
    solver_rows = solver_result.get("rows", []) if isinstance(solver_result, dict) else []
    solver_columns = set(solver_rows[0].keys()) if solver_rows and isinstance(solver_rows[0],dict) else set()
    seed_material = checked["protocol_sha256"]
    for measurement_index, measurement in enumerate(checked["measurements"]):
        target_variable = measurement.get("target_variable", "")
        equipment_id = measurement.get("equipment_id")
        if not target_variable or not solver_rows or target_variable not in solver_columns or measurement.get("kind") == "generic_observation":
            simulated_measurements.append({**measurement,"status":"plan_only_no_matching_solver_output","true_value":None,"observed_value":None,"uncertainty_sd":None})
            continue
        prefix = MEASUREMENT_VARIABLE_PREFIXES.get(measurement["kind"], ())
        if prefix and not any(target_variable.startswith(p) for p in prefix):
            simulated_measurements.append({**measurement,"status":"target_variable_incompatible_with_measurement_kind","true_value":None,"observed_value":None,"uncertainty_sd":None})
            continue
        sample_index = measurement.get("sample_index", -1)
        sample_index = len(solver_rows)-1 if sample_index == -1 else sample_index
        if sample_index < 0 or sample_index >= len(solver_rows):
            simulated_measurements.append({**measurement,"status":"sample_index_out_of_range","true_value":None,"observed_value":None,"uncertainty_sd":None})
            continue
        true_value = solver_rows[sample_index].get(target_variable)
        if isinstance(true_value,bool) or not isinstance(true_value,(int,float)) or not math.isfinite(true_value):
            simulated_measurements.append({**measurement,"status":"target_not_finite_numeric","true_value":None,"observed_value":None,"uncertainty_sd":None})
            continue
        instrument = EQUIPMENT[equipment_id]
        sigma = float(instrument.get("measurement_uncertainty_sd",0.0))
        # Deterministic per-protocol pseudo-noise makes the dossier reproducible.
        digest = hashlib.sha256(f"{seed_material}:{measurement_index}:{target_variable}:{sample_index}".encode()).digest()
        u1 = (int.from_bytes(digest[:8],"big")+1)/(2**64+1)
        u2 = (int.from_bytes(digest[8:16],"big")+1)/(2**64+1)
        z = math.sqrt(-2*math.log(u1))*math.cos(2*math.pi*u2)
        observed = float(true_value) + sigma*z
        simulated_measurements.append({
            **measurement,"status":"simulated_instrument_reading",
            "sample_index":sample_index,"true_value":float(true_value),
            "observed_value":observed,"uncertainty_sd":sigma,
            "instrument":instrument["name"],"instrument_model":"additive Gaussian noise; illustrative one-sigma uncertainty",
            "random_seed_fingerprint":digest.hex()[:16],
            "scientific_note":"Synthetic instrument reading from solver output, not an empirical measurement."
        })
    measurement_by_step = {}
    for item in simulated_measurements:
        measurement_by_step.setdefault(item["step_id"], []).append(item)
    for order, sid in enumerate(checked["execution_order"], start=1):
        step = step_by_id[sid]
        incoming = flow_by_target.get(sid, [])
        duration = step["duration_s"]
        started = elapsed
        elapsed += duration
        trace.append({
            "order":order,"step_id":sid,"action":step["action"],
            "status":"recorded_not_physically_executed",
            "equipment_id":step["equipment_id"],
            "start_offset_s":started,"end_offset_s":elapsed,"duration_s":duration,
            "incoming_materials":[{"component_id":f.get("component_id"),"amount":f.get("amount"),"unit":f.get("unit")} for f in incoming],
            "measurement_plan":measurement_by_step.get(sid,[]),
            "measurement_result":([m for m in measurement_by_step.get(sid,[]) if m.get("status")=="simulated_instrument_reading"] or None),
            "note":"Protocol step and timing recorded. No physical equipment was operated; readings, if present, are synthetic outputs of the declared measurement model."
        })
    return {
        "protocol_sha256":checked["protocol_sha256"],
        "status":"protocol_trace_recorded",
        "created_at_utc":datetime.now(timezone.utc).isoformat(),
        "total_planned_duration_s":elapsed,
        "execution_order":checked["execution_order"],
        "trace":trace,
        "validation":checked,
        "simulated_measurements":simulated_measurements,
        "limitations":[
            "This is a reproducible protocol trace, not a physical execution.",
            "Instrument readings use a simplified additive Gaussian error model and illustrative catalogue uncertainties; they are not calibrated metrology.",
            "Readings remain null when no compatible numerical solver variable is selected.",
            "Equipment metadata and material-flow units are catalogue checks, not laboratory safety or metrology certification."
        ]
    }
