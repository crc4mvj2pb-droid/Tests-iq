from __future__ import annotations
from scientific_imports import import_sbml, import_dataset, list_assets
from sbml_engine import simulate_sbml, SBMLSimulationError
from lab_designer import CATALOG as LAB_CATALOG, validate_experiment as validate_lab_experiment, run_lab_experiment
from dataset_analysis import analyze_csv
from sbml_sweeps import sweep_sbml
from protocol_engine import validate_protocol, execute_protocol
from equipment_models import apply_material_flow_model, apply_equipment_operating_effects
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from pathlib import Path
import json, mimetypes, urllib.parse, hashlib, re, sys, traceback
from engine import run_experiment
from version import APP_VERSION
from models import MODEL_CATALOG
from validation import compare_to_reference
from planner import plan_enzyme_sweep
from history import save_experiment, list_experiments, get_experiment
from experiment_lifecycle import configuration_hash, verify_dossier_integrity
import experiment_service
from experiment_service import ServiceError
from analysis_tools import enzyme_uncertainty, enzyme_local_sensitivity
from models import get_solver_contract
from provenance import parse_xy_csv, create_provenance_record
from design import rank_enzyme_experiments
from research_tools import parameter_sweep, monte_carlo_uncertainty, compare_model_output, fit_model_parameters, run_software_validation_suite
from scientific_copilot import ask_scientific_copilot
from electrical_circuits import solve_dc_circuit, CircuitError
from electrical_advanced import simulate_first_order_step, solve_series_rlc_ac, sweep_series_rlc_frequency, ElectricalModelError
from workbench_circuit import solve_workbench_circuit, WorkbenchCircuitError
from chemical_kinetics import simulate_reaction_network, ChemicalKineticsError
from reaction_stoichiometry import calculate_stoichiometry, StoichiometryError
from virtual_instruments import simulate_instrument_measurement

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, content_type="application/json; charset=utf-8"):
        if isinstance(body, str):
            data = body.encode("utf-8")
        else:
            data = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/lab/catalog":
            return self._send(200, LAB_CATALOG)
        if parsed.path == "/api/models":
            return self._send(200, {"models": MODEL_CATALOG})
        if parsed.path == "/api/health":
            return self._send(200, {"status": "ok", "mode": "local-only", "version": APP_VERSION})
        if parsed.path == "/api/scientific-ai/capabilities":
            return self._send(200, {"mode":"local_expert_router", "generative_model_connected":False, "supported_models":[m["id"] for m in MODEL_CATALOG if m["status"] == "implemented_demo"], "disclosure":"Deterministic local research copilot; no generative foundation model or live literature retrieval connected."})
        if parsed.path == "/api/version":
            return self._send(200, {"version": APP_VERSION, "features": ["v4.5 save/restore: unified schema-2 dossiers with app/engine versions and full-dossier hash for every saving endpoint, three-level verification, replay with result comparison, SQLite schema migration with automatic backup, lossless history export/import refusing altered files, workspace file import", "v4.4 DC solver consistency: floating sub-networks detected and named before solving, no-current branches and ignored components reported, relative singularity threshold, mixed-precision iterative refinement with per-node and per-branch uncertainty, KCL/ground-return/power balance checked against propagated bounds, explicit sign conventions; verified against closed-form and exact rational references", "v4.3 reliable workbench state: one canonical save/export format, validated restore with cleanup report, recursive deletion of contents and wires, empty values flagged instead of becoming 0, duplication, visible marking of components the DC solver does not compute", "v4.2 browser-verified workbench path: Playwright end-to-end tests, single-submission solve, coded and translated circuit errors, robust JSON body handling and logged internal errors", "v4.1 reproducibility: verify saved configuration hashes and replay supported saved DC workbench circuits into new dossiers" , "v4.0 experiment lifecycle: workbench circuit runs are saved as traceable SQLite experiment dossiers with configuration hashes, results, assumptions, limitations and history IDs", "v3.9 accessibility: keyboard-operable workbench items, visible focus, category state announcements and live updates for library and properties", "v3.8 interface reliability: visible local API connection status, actionable offline guidance, explicit workspace restore and robust save errors", "v3.7 virtual instruments: seeded simulated readings, calibration correction, display resolution, uncertainty budget and comparison with theory; explicit non-experimental status", "v3.2 expanded multidisciplinary catalog: 18 disciplines, 58 components, 70 equipment entries, 42 experiment workflows, 43 model entries including 30 L0 templates; sequential A-to-B-to-C kinetics remains available", "v2.7 graphical pin-to-pin circuit connections translated into a netlist and solved by the DC nodal engine","analytical RC/RL step response", "series RLC AC phasor analysis", "logarithmic RLC frequency sweep", "bounded multi-parameter least-squares fitting with residual diagnostics", "cross-model software sanity validation suite", "seven additional numerical solvers", "generic multi-model parameter sweeps", "generic seeded Monte Carlo parameter uncertainty", "reference comparison with model output column mapping", "ten-stage scientific development roadmap", "interactive multilingual workbench, categorized draggable catalog and local JSON export", "v3.5 kinetic engine bridge: abstract A/B/C species concentrations can be loaded from the workbench into the RK4 reaction-network simulator; local request cancellation and result export", "v3.6 server-side stoichiometric batch solver with formula parsing, limiting-reactant calculation, atom-balance rejection and auditable material balance", "v2.6 sample containment inside equipment, equipment operation panel, thermal setpoint transfer, conceptual microscopy/PCR checks, Beer-Lambert absorbance with user-supplied parameters, and stoichiometric reactions inside a reactor", "ideal dilution balance in the new workbench", "DC resistive circuit solver using nodal analysis with node voltages, branch currents, equivalent resistance, power and numerical KCL/power-balance checks", "visual virtual-bench workspace and protocol designer", "equipment-aware material-flow calculations and instrument uncertainty models", "descriptive CSV profiling and exploratory correlations", "bounded global-parameter sweeps for supported SBML models", "heat diffusion and SIR solvers connected to virtual-lab workflows", "equipment compatibility checks", "solution dilution calculator", "enzyme assay workflow", "solver registry", "parameter sweeps", "reference-data comparison", "traceable experiment dossiers", "SQLite experiment history", "uncertainty propagation", "local sensitivity", "provenance records", "scientific library catalog", "expanded multidomain scientific knowledge base", "SI unit and dimension reference", "selected physical constants", "local SBML model intake", "CSV reference dataset registry with provenance", "SBML subset simulator using fixed-step RK4"]})
        if parsed.path == "/api/research/validation-suite":
            return self._send(200, run_software_validation_suite())
        if parsed.path == "/api/research/roadmap":
            path = BASE / "scientific_library" / "roadmap.json"
            return self._send(200, json.loads(path.read_text(encoding="utf-8")))
        if parsed.path == "/api/contract":
            return self._send(200, get_solver_contract())
        if parsed.path == "/api/library":
            catalog_path = BASE / "scientific_library" / "catalog.json"
            return self._send(200, json.loads(catalog_path.read_text(encoding="utf-8")))
        if parsed.path == "/api/units":
            path = BASE / "scientific_library" / "units_and_dimensions.json"
            return self._send(200, json.loads(path.read_text(encoding="utf-8")))
        if parsed.path == "/api/constants":
            path = BASE / "scientific_library" / "physical_constants.json"
            return self._send(200, json.loads(path.read_text(encoding="utf-8")))
        if parsed.path == "/api/imported-assets":
            return self._send(200, list_assets())
        if parsed.path == "/api/sources":
            sources_path = BASE / "scientific_library" / "sources.json"
            return self._send(200, json.loads(sources_path.read_text(encoding="utf-8")))
        if parsed.path == "/api/knowledge":
            knowledge_path = BASE / "scientific_library" / "knowledge_base.json"
            knowledge = json.loads(knowledge_path.read_text(encoding="utf-8"))
            query = urllib.parse.parse_qs(parsed.query).get("q", [""])[0].strip().casefold()
            domain = urllib.parse.parse_qs(parsed.query).get("domain", [""])[0].strip().casefold()
            entries = knowledge["entries"]
            if query:
                entries = [e for e in entries if query in " ".join(str(e.get(k, "")) for k in ("id", "title", "domain", "kind", "formula_or_rule", "meaning", "applicability_conditions", "limitations", "tags")).casefold()]
            if domain:
                entries = [e for e in entries if domain in e.get("domain", "").casefold() or any(domain in t.casefold() for t in e.get("tags", []))]
            return self._send(200, {"schema_version": knowledge["schema_version"], "library_name": knowledge["library_name"], "scope": knowledge["scope"], "total_entries": len(knowledge["entries"]), "matched_entries": len(entries), "entries": entries})
        if parsed.path.startswith("/api/library/"):
            entry_id = parsed.path.rsplit("/", 1)[1]
            catalog_path = BASE / "scientific_library" / "catalog.json"
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            for entry in catalog["entries"]:
                if entry["id"] == entry_id:
                    return self._send(200, entry)
            return self._send(404, {"error": "Library entry not found"})
        if parsed.path == "/api/history":
            return self._send(200, {"experiments": list_experiments()})
        if parsed.path == "/api/history/export":
            return self._send(200, experiment_service.export_all())
        if parsed.path == "/api/history/replayable":
            return self._send(200, {"models": experiment_service.replayable_models()})
        if parsed.path.startswith("/api/history/"):
            match = re.fullmatch(r"/api/history/(\d+)(/verify|/export)?", parsed.path)
            if not match:
                return self._send(400, {"error": "Experiment ID must be an integer; optional suffix: /verify or /export"})
            experiment_id = int(match.group(1))
            try:
                if match.group(2) == "/verify":
                    return self._send(200, experiment_service.verify(experiment_id))
                if match.group(2) == "/export":
                    return self._send(200, experiment_service.export_one(experiment_id))
            except ServiceError as exc:
                return self._send(exc.status, {"error": str(exc), **exc.details})
            dossier = get_experiment(experiment_id)
            if not dossier:
                return self._send(404, {"error": "Experiment not found"})
            return self._send(200, dossier)
        if parsed.path in ("/", "/index.html"):
            path = STATIC / "index.html"
            return self._send(200, path.read_text(encoding="utf-8"), "text/html; charset=utf-8")
        return self._send(404, {"error": "Not found"})

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        is_replay_path = re.fullmatch(r"/api/history/\d+/replay", parsed.path) is not None
        if parsed.path not in ("/api/experiments", "/api/validate", "/api/sweeps", "/api/uncertainty", "/api/sensitivity", "/api/import-csv", "/api/design", "/api/import-sbml", "/api/import-dataset", "/api/simulate-sbml", "/api/lab/validate", "/api/lab/run", "/api/analyze-dataset", "/api/sweep-sbml", "/api/protocol/validate", "/api/protocol/run", "/api/research/sweep", "/api/research/uncertainty", "/api/research/compare", "/api/research/fit", "/api/scientific-ai/ask", "/api/electrical/dc-solve", "/api/electrical/workbench-solve", "/api/electrical/workbench-run", "/api/electrical/transient", "/api/electrical/ac", "/api/electrical/ac-sweep", "/api/chemistry/kinetics", "/api/chemistry/stoichiometry", "/api/instruments/measure", "/api/history/import") and not is_replay_path:
            return self._send(404, {"error": "Not found"})
        try:
            length = int(self.headers.get("Content-Length", "0"))
            limit = 20_000_000 if parsed.path == "/api/history/import" else 1_000_000
            if length > limit:
                return self._send(413, {"error": f"Request body too large (maximum {limit:,} bytes)."})
            if length <= 0:
                # Replay needs no parameters; every other endpoint requires a JSON object.
                if not is_replay_path:
                    return self._send(400, {"error": "Request body missing: send a JSON object."})
                request = {}
            else:
                request = json.loads(self.rfile.read(length).decode("utf-8"))
            if not isinstance(request, dict):
                return self._send(400, {"error": "Request body must be a JSON object."})
            if is_replay_path:
                result = experiment_service.replay(int(parsed.path.split("/")[3]))
            elif parsed.path == "/api/history/import":
                result = experiment_service.import_bundle(request)
            elif parsed.path == "/api/instruments/measure":
                result = simulate_instrument_measurement(request)
            elif parsed.path == "/api/chemistry/kinetics":
                result = simulate_reaction_network(request)
            elif parsed.path == "/api/chemistry/stoichiometry":
                result = calculate_stoichiometry(request)
            elif parsed.path == "/api/electrical/dc-solve":
                result = solve_dc_circuit(request)
            elif parsed.path == "/api/electrical/workbench-solve":
                result = solve_workbench_circuit(request)
            elif parsed.path == "/api/electrical/workbench-run":
                result = experiment_service.run_workbench(request)
            elif parsed.path == "/api/electrical/transient":
                result = simulate_first_order_step(request)
            elif parsed.path == "/api/electrical/ac":
                result = solve_series_rlc_ac(request)
            elif parsed.path == "/api/electrical/ac-sweep":
                result = sweep_series_rlc_frequency(request)
            elif parsed.path == "/api/scientific-ai/ask":
                result = ask_scientific_copilot(request.get("question", ""), request.get("parameters", {}))
            elif parsed.path == "/api/research/sweep":
                result = parameter_sweep(request.get("model_id"), request.get("parameters", {}), request.get("parameter", ""), request.get("values", []), request.get("summary_key"))
            elif parsed.path == "/api/research/uncertainty":
                result = monte_carlo_uncertainty(request.get("model_id"), request.get("parameters", {}), request.get("uncertainty", {}), request.get("output_key", ""), request.get("samples", 300), request.get("seed", 7))
            elif parsed.path == "/api/research/compare":
                result = compare_model_output(request.get("model_id"), request.get("parameters", {}), request.get("reference", []), request.get("x_key", ""), request.get("y_key", ""))
            elif parsed.path == "/api/research/fit":
                result = fit_model_parameters(request.get("model_id"), request.get("parameters", {}), request.get("reference", []), request.get("x_key", ""), request.get("y_key", ""), request.get("bounds", {}), request.get("max_iterations", 120))
            elif parsed.path == "/api/protocol/validate":
                result = validate_protocol(request)
            elif parsed.path == "/api/protocol/run":
                result = experiment_service.run_protocol(request)
            elif parsed.path == "/api/analyze-dataset":
                result = analyze_csv(request.get("content", ""), preview_rows=request.get("preview_rows", 12))
            elif parsed.path == "/api/sweep-sbml":
                result = sweep_sbml(request.get("asset_id"), request.get("duration"), request.get("dt"), request.get("parameter_id"), request.get("values"))
            elif parsed.path == "/api/lab/validate":
                result = validate_lab_experiment(request)
            elif parsed.path == "/api/lab/run":
                result = experiment_service.run_lab(request)
            elif parsed.path == "/api/experiments":
                result = experiment_service.run_model_experiment(request)
            elif parsed.path == "/api/uncertainty":
                if request.get("model_id") != "enzyme_kinetics":
                    return self._send(400, {"error": "Uncertainty analysis currently supports enzyme_kinetics only."})
                result = enzyme_uncertainty(request.get("parameters", {}), request.get("uncertainty", {}), request.get("samples", 500), request.get("seed", 7))
            elif parsed.path == "/api/sensitivity":
                if request.get("model_id") != "enzyme_kinetics":
                    return self._send(400, {"error": "Sensitivity analysis currently supports enzyme_kinetics only."})
                result = enzyme_local_sensitivity(request.get("parameters", {}), request.get("relative_step", 0.01))
            elif parsed.path == "/api/import-csv":
                result = parse_xy_csv(request.get("csv", ""))
            elif parsed.path == "/api/design":
                if request.get("model_id") != "enzyme_kinetics":
                    return self._send(400, {"error": "Experiment design ranking currently supports enzyme_kinetics only."})
                result = rank_enzyme_experiments(
                    request.get("parameters", {}),
                    request.get("candidate_concentrations", []),
                    request.get("experiments_per_design", 3),
                    request.get("measurement_sd", 0.05),
                    request.get("top_n", 5)
                )
            elif parsed.path == "/api/validate":
                model_id = request.get("model_id")
                if model_id != "enzyme_kinetics":
                    return self._send(400, {"error": "Reference comparison currently supports enzyme_kinetics only."})
                params = request.get("parameters", {})
                from models import run_enzyme
                prediction = run_enzyme(params)
                reference = request.get("reference_data", [])
                result = {
                    "model_id": model_id,
                    "model_configuration": params,
                    "comparison": compare_to_reference(prediction["rows"], reference),
                    "model_limitations": prediction["limitations"]
                }
            elif parsed.path == "/api/import-sbml":
                result = import_sbml(request.get("filename"), request.get("content"), request.get("source_url", ""))
            elif parsed.path == "/api/import-dataset":
                result = import_dataset(request.get("filename"), request.get("content"), request.get("source_url", ""), request.get("description", ""))
            elif parsed.path == "/api/simulate-sbml":
                result = simulate_sbml(request.get("asset_id"), request.get("duration"), request.get("dt"), request.get("method", "rk4"))
            else:
                if request.get("model_id") != "enzyme_kinetics":
                    return self._send(400, {"error": "Parameter sweep currently supports enzyme_kinetics only."})
                result = plan_enzyme_sweep(request.get("parameters", {}), request.get("parameter", ""), request.get("values", []))
            return self._send(200, result)
        except ServiceError as exc:
            return self._send(exc.status, {"error": str(exc), **exc.details})
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError, SBMLSimulationError, CircuitError, ElectricalModelError, WorkbenchCircuitError, ChemicalKineticsError, StoichiometryError) as exc:
            body = {"error": str(exc)}
            if getattr(exc, "code", None):
                body["error_code"] = exc.code
                body["error_params"] = getattr(exc, "params", {})
            return self._send(400, body)
        except Exception:
            # Do not expose internal exception details through the HTTP API, but keep them in the terminal log.
            print(f"[VirtualLab] Internal error on POST {parsed.path}", file=sys.stderr)
            traceback.print_exc()
            return self._send(500, {"error": "Internal error. Check the local terminal logs."})

    def log_message(self, fmt, *args):
        print("[VirtualLab]", fmt % args)

if __name__ == "__main__":
    import os
    port = int(os.environ.get("VIRTUAL_LAB_PORT", "8765"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"Virtual Lab Platform running locally at http://127.0.0.1:{port}")
    print("Local-only server. Do not expose this prototype to the public internet.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Virtual Lab.")
    finally:
        server.server_close()
