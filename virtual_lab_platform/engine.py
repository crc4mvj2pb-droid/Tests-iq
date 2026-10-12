from __future__ import annotations
import hashlib, json, platform, sys
from datetime import datetime, timezone
from typing import Any
from models import execute_model, MODEL_CATALOG_BY_ID

def canonical_hash(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

def run_experiment(request: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise ValueError("Request must be a JSON object.")
    name = request.get("name")
    question = request.get("question")
    model_id = request.get("model_id")
    params = request.get("parameters", {})
    if not isinstance(name, str) or not name.strip():
        raise ValueError("Experiment name is required.")
    if not isinstance(question, str) or not question.strip():
        raise ValueError("Scientific question is required.")
    if not isinstance(params, dict):
        raise ValueError("parameters must be a JSON object.")
    if model_id not in MODEL_CATALOG_BY_ID:
        raise ValueError("Unknown model_id.")
    model = MODEL_CATALOG_BY_ID[model_id]
    result = execute_model(model_id, params)
    config = {"name": name, "question": question, "model_id": model_id, "parameters": params}
    return {
        "experiment_id": "VL-" + canonical_hash({"config": config, "created": datetime.now(timezone.utc).isoformat()})[:12].upper(),
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "name": name.strip(),
        "question": question.strip(),
        "domain": model["domain"],
        "model": {"id": model_id, "name": model["name"], "catalog_status": model["status"]},
        "configuration": config,
        "configuration_sha256": canonical_hash(config),
        "runtime": {"python": sys.version.split()[0], "platform": platform.platform()},
        "result": result,
        "interpretation_policy": {
            "result_type": "model output",
            "not_equivalent_to": ["physical experiment", "clinical evidence", "cosmetic safety assessment", "regulatory approval"],
            "validation_level_meaning": {"L0": "workflow placeholder; no calculation", "L1": "calculation and basic checks only; no empirical validation"}
        }
    }
