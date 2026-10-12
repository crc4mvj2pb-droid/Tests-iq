"""Equipment-aware calculation adapters for the virtual laboratory.

These models are intentionally simple and explicitly labelled as illustrative.
They connect declared material transfers and instrument specifications to
calculations without claiming vendor-certified digital twins.
"""
from __future__ import annotations
import math, hashlib, random, json
from typing import Any
from lab_designer import EQUIPMENT, COMPONENTS
from models import execute_model

def apply_material_flow_model(request: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
    flows = request.get("material_flows", [])
    role_flows = [f for f in flows if isinstance(f, dict) and f.get("role") in {"stock", "diluent"}]
    if not role_flows:
        if flows:
            results["material_flow_audit"] = {
                "status": "recorded_not_connected_to_solver",
                "flows": flows,
                "note": "Generic transfers are recorded, but only explicitly supported flow roles alter a numerical calculation."
            }
        return results
    if request.get("workflow_id") != "solution_dilution":
        results["material_flow_audit"] = {
            "status": "recorded_not_connected_to_solver",
            "flows": flows,
            "note": "This workflow does not yet have a solver adapter for role-labelled material flows."
        }
        return results
    stock = [f for f in role_flows if f.get("role") == "stock"]
    diluent = [f for f in role_flows if f.get("role") == "diluent"]
    if not stock or not diluent:
        raise ValueError("Dilution flow calculation requires at least one stock flow and one diluent flow.")
    for flow in role_flows:
        if flow.get("unit") != "mL":
            raise ValueError("Dilution stock and diluent flows must use mL.")
    stock_volume = sum(float(f["amount"]) for f in stock)
    diluent_volume = sum(float(f["amount"]) for f in diluent)
    if not math.isfinite(stock_volume + diluent_volume) or stock_volume <= 0 or diluent_volume < 0:
        raise ValueError("Dilution flow volumes must be finite, with positive stock volume and non-negative diluent volume.")
    params = request.get("parameters", {})
    c_stock = float(params.get("stock_concentration_mM", 0))
    if not math.isfinite(c_stock) or c_stock <= 0:
        raise ValueError("Stock concentration must be positive to calculate flow-driven dilution.")
    total = stock_volume + diluent_volume
    concentration = c_stock * stock_volume / total
    # First-order uncertainty propagation for C = C_stock * Vs / (Vs + Vd).
    var_vs = 0.0
    var_vd = 0.0
    transfer_records = []
    for role, role_items in (("stock", stock), ("diluent", diluent)):
        for flow in role_items:
            eid = flow.get("transfer_equipment_id")
            if eid not in EQUIPMENT:
                raise ValueError("Every stock/diluent transfer must name selected transfer equipment.")
            instrument = EQUIPMENT[eid]
            sigma = float(instrument.get("transfer_uncertainty_sd_ml", 0.0))
            if role == "stock": var_vs += sigma**2
            else: var_vd += sigma**2
            transfer_records.append({
                "role":role,"component_id":flow["component_id"],"amount_ml":float(flow["amount"]),
                "transfer_equipment_id":eid,"transfer_equipment":instrument["name"],
                "transfer_uncertainty_sd_ml":sigma
            })
    dcdvs = c_stock * diluent_volume / (total**2)
    dcdvd = -c_stock * stock_volume / (total**2)
    sigma_c = math.sqrt((dcdvs**2)*var_vs + (dcdvd**2)*var_vd)
    # Mutate the calculator's result to use the explicitly supplied material flows.
    results.update({
        "calculation":"C_final = C_stock × V_stock / (V_stock + V_diluent), using declared material transfers",
        "stock_concentration_mM":c_stock,
        "stock_volume_ml":stock_volume,
        "diluent_volume_ml":diluent_volume,
        "final_volume_ml":total,
        "final_concentration_mM":concentration,
        "material_flow_model":{
            "status":"connected_to_dilution_solver",
            "transfer_records":transfer_records,
            "uncertainty_method":"first-order independent uncertainty propagation",
            "final_concentration_standard_uncertainty_mM":sigma_c,
            "approximate_95_percent_interval_mM":[max(0.0,concentration-1.96*sigma_c), concentration+1.96*sigma_c],
            "assumptions":[
                "All stock flows are treated as the same stock concentration provided in workflow parameters.",
                "Volumes are additive; no reaction, evaporation, density or non-ideal mixing.",
                "Transfer uncertainties are independent, one-sigma catalogue estimates.",
                "Instrument uncertainty values are illustrative and not manufacturer-certified."
            ]
        },
        "assumptions":[
            "Material flow roles explicitly determine the stock and diluent volumes.",
            "All stock flows use the configured stock concentration.",
            "Ideal additive volumes; no reaction, evaporation or non-ideal solution effects.",
            "Transfer uncertainty propagation is first-order and uses illustrative independent one-sigma instrument uncertainties."
        ],
        "computed_scientific_result":True
    })
    return results

def validate_equipment_operating_range(request: dict[str, Any]) -> list[dict[str, str]]:
    issues = []
    selected = request.get("equipment", [])
    eq_ids = {x.get("id") if isinstance(x,dict) else x for x in selected}
    workflow = request.get("workflow_id")
    params = request.get("parameters", {})
    if workflow == "materials_heating":
        eid = "thermal_chamber" if "thermal_chamber" in eq_ids else None
        if eid:
            e = EQUIPMENT[eid]
            lo, hi = float(e.get("temperature_min_c",-273.15)), float(e.get("temperature_max_c",1e9))
            for key in ("left_temp_c","right_temp_c","initial_temp_c"):
                val = params.get(key)
                if isinstance(val,(int,float)) and not isinstance(val,bool) and math.isfinite(val) and not lo <= val <= hi:
                    issues.append({"severity":"error","code":"equipment_temperature_range","message":f"{key}={val:g} °C is outside the selected {e['name']} range ({lo:g} to {hi:g} °C)."})
    return issues

def apply_equipment_operating_effects(request: dict[str, Any], results: dict[str, Any]) -> dict[str, Any]:
    """Apply a simple, deterministic control-error model to thermal-chamber runs."""
    if request.get("workflow_id") != "materials_heating":
        return results
    selected = request.get("equipment", [])
    eq_ids = {x.get("id") if isinstance(x,dict) else x for x in selected}
    if "thermal_chamber" not in eq_ids or not results.get("rows"):
        return results
    instrument = EQUIPMENT["thermal_chamber"]
    sigma = float(instrument.get("temperature_control_uncertainty_sd_c", 0.0))
    params = request.get("parameters", {})
    # Stable seed: same protocol/configuration gives the same virtual chamber deviations.
    seed_text = json.dumps({
        "workflow_id":request.get("workflow_id"),
        "parameters":params,
        "equipment":sorted(eq_ids),
        "material_flows":request.get("material_flows",[])
    }, sort_keys=True, separators=(",", ":"), allow_nan=False)
    seed = int(hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16],16)
    rng = random.Random(seed)
    left_offset = rng.gauss(0.0,sigma)
    right_offset = rng.gauss(0.0,sigma)
    effective = {
        "length_m":params.get("length_m",1.0),
        "diffusivity_m2_s":params.get("diffusivity_m2_s",1e-5),
        "left_temp_c":float(params.get("left_temp_c",100.0))+left_offset,
        "right_temp_c":float(params.get("right_temp_c",20.0))+right_offset,
        "initial_temp_c":params.get("initial_temp_c",20.0),
        "nodes":params.get("nodes",21),
        "dt_s":params.get("dt_s",1.0),
        "total_time_s":params.get("total_time_s",1000.0)
    }
    # Do not silently run outside the declared device operating range.
    lo,hi=float(instrument["temperature_min_c"]),float(instrument["temperature_max_c"])
    if not (lo <= effective["left_temp_c"] <= hi and lo <= effective["right_temp_c"] <= hi):
        raise ValueError("Simulated thermal-chamber control deviation places a boundary setpoint outside the selected equipment range; adjust the setpoint or review the illustrative uncertainty model.")
    rerun = execute_model("heat_diffusion_1d", effective)
    for key in ("rows","columns","checks","summary","model_id","validation_level"):
        if key in rerun: results[key]=rerun[key]
    results["equipment_effect_model"] = {
        "equipment_id":"thermal_chamber",
        "equipment_name":instrument["name"],
        "status":"applied_to_solver_inputs",
        "model":"deterministic Gaussian setpoint deviations",
        "temperature_control_uncertainty_sd_c":sigma,
        "left_boundary_offset_c":left_offset,
        "right_boundary_offset_c":right_offset,
        "effective_parameters":effective,
        "random_seed_fingerprint":hashlib.sha256(seed_text.encode("utf-8")).hexdigest()[:16],
        "note":"Illustrative control-error model; not a calibrated chamber digital twin or measured performance."
    }
    results.setdefault("assumptions",[])
    results["assumptions"].append("Thermal chamber boundary setpoints include deterministic Gaussian control deviations based on illustrative catalogue uncertainty.")
    return results
