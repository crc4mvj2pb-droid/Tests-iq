from __future__ import annotations
from scientific_imports import import_sbml, import_dataset, list_assets
from sbml_engine import simulate_sbml, analyze_sbml, SBMLSimulationError
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
import model_registry
import maturity
import analysis
import jobs
import pipelines
import domains
import data_catalog
import references
import data_import
import fitting
import trace_package
import reports
from contracts import ContractError
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
import workbench_transient  # noqa: F401  (engine loaded for the registry)
from chemical_kinetics import simulate_reaction_network, ChemicalKineticsError
from reaction_stoichiometry import calculate_stoichiometry, StoichiometryError
from virtual_instruments import simulate_instrument_measurement

BASE = Path(__file__).resolve().parent
STATIC = BASE / "static"

LOCAL_HOSTNAMES = {"127.0.0.1", "localhost", "::1"}
DEFAULT_ERROR_CODES = {400: "invalid_request", 403: "forbidden", 404: "not_found", 409: "conflict", 413: "payload_too_large", 500: "internal_error"}


class Handler(BaseHTTPRequestHandler):
    def _request_is_local(self) -> bool:
        """Refuse requests that do not come from this local application (v4.8).

        - Host must name the loopback interface on this server's port: blocks DNS-rebinding pages
          that resolve their own domain to 127.0.0.1 and then read the API.
        - Origin, when the browser sends one, must be this same local address: blocks cross-site
          form/fetch requests (CSRF) that would write to the history or import files.
        """
        port = self.server.server_address[1]

        def local(value: str, require_scheme: bool) -> bool:
            parsed = urllib.parse.urlsplit(value if require_scheme else "//" + value)
            if require_scheme and parsed.scheme != "http":
                return False
            try:
                return parsed.hostname in LOCAL_HOSTNAMES and (parsed.port or 80) == port
            except ValueError:
                return False

        host = self.headers.get("Host")
        if host is not None and not local(host, False):
            return False
        origin = self.headers.get("Origin")
        return origin is None or local(origin, True)

    def _refuse_foreign(self) -> bool:
        if self._request_is_local():
            return False
        self._send(403, {"error": "Request refused: this local server only accepts requests from its own page at 127.0.0.1 or localhost."})
        return True

    def _send(self, code, body, content_type="application/json; charset=utf-8", headers=None):
        if code >= 400 and isinstance(body, dict) and "error_code" not in body:
            # v5.0: one error format for the whole API — {error, error_code, error_params?}.
            body = {**body, "error_code": DEFAULT_ERROR_CODES.get(code, "request_refused")}
        if isinstance(body, bytes):
            data = body
        elif isinstance(body, str):
            data = body.encode("utf-8")
        else:
            data = json.dumps(body, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        for name, value in (headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        if self._refuse_foreign():
            return
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/lab/catalog":
            return self._send(200, LAB_CATALOG)
        if parsed.path == "/api/models":
            return self._send(200, {"models": [{**m, "maturity": maturity.maturity_of(m["id"], m["status"])} for m in MODEL_CATALOG]})
        if parsed.path == "/api/data/catalog" or parsed.path.startswith("/api/data/catalog/"):
            query = urllib.parse.parse_qs(parsed.query)
            first = lambda key: (query.get(key) or [None])[0]
            try:
                if parsed.path == "/api/data/catalog":
                    return self._send(200, {"schema_version": data_catalog.CATALOG_SCHEMA_VERSION, "data_kinds": list(data_catalog.DATA_KINDS),
                                            "entries": data_catalog.search(first("q") or "", first("kind"), first("type"), first("domain"))})
                entry_id = urllib.parse.unquote(parsed.path.rsplit("/", 1)[1])
                if entry_id.endswith(".csv"):
                    return self._send(200, data_catalog.export_csv(entry_id[:-4]), "text/csv; charset=utf-8")
                return self._send(200, data_catalog.get_entry(entry_id))
            except data_catalog.CatalogError as exc:
                return self._send(404 if exc.code == "unknown_entry" else 400, {"error": str(exc), "error_code": exc.code, "error_params": exc.params})
        if parsed.path == "/api/sources" or parsed.path.startswith("/api/sources/"):
            index = references.cited_by()
            known = references.sources()
            if parsed.path == "/api/sources":
                return self._send(200, {"sources": [{**s, "cited_by": index.get(sid, [])} for sid, s in known.items()], "problems": references.problems()})
            sid = urllib.parse.unquote(parsed.path.rsplit("/", 1)[1])
            if sid not in known:
                return self._send(404, {"error": f"Unknown source '{sid}'.", "error_code": "unknown_source"})
            return self._send(200, {**known[sid], "cited_by": index.get(sid, [])})
        if parsed.path == "/api/data/fit-models":
            return self._send(200, {"engine": {"id": fitting.ENGINE_ID, "version": fitting.ENGINE_VERSION},
                                    "models": {k: {"params": m["params"], "units": m["units"], "equation": m["equation"]} for k, m in fitting.MODELS.items()}})
        if parsed.path == "/api/domains":
            return self._send(200, {"domains": domains.all_domains(), "problems": domains.problems()})
        if parsed.path == "/api/benchmarks":
            from benchmarks.independent_suite import CASES as BENCHMARK_CASES
            report = STATIC.parent / "BENCHMARK_REPORT_FR.md"
            return self._send(200, {"cases": [{k: v for k, v in c.items() if k != "run"} for c in BENCHMARK_CASES],
                                    "report_file": report.name if report.is_file() else None,
                                    "how_to_run": "python scripts/run_benchmarks.py (about 35 s; regenerates BENCHMARK_REPORT_FR.md)"})
        if parsed.path == "/api/pipelines/examples":
            return self._send(200, {"engine": {"id": pipelines.ENGINE_ID, "version": pipelines.ENGINE_VERSION}, "examples": pipelines.example_pipelines(),
                                    "adapters": pipelines.adapter_catalogue()})
        if parsed.path == "/api/maturity":
            return self._send(200, maturity.summary())
        if parsed.path == "/api/health":
            return self._send(200, {"status": "ok", "mode": "local-only", "version": APP_VERSION})
        if parsed.path == "/api/scientific-ai/capabilities":
            return self._send(200, {"mode":"local_expert_router", "generative_model_connected":False, "supported_models":[m["id"] for m in MODEL_CATALOG if m["status"] == "implemented_demo"], "disclosure":"Deterministic local research copilot; no generative foundation model or live literature retrieval connected."})
        if parsed.path == "/api/version":
            return self._send(200, {"version": APP_VERSION, "features": ["v7.1: thermal models (lumped transient with Biot check, composite plane wall; verified against independent integration, finite differences and hand calculations; heating adapter verified, Joule chain fully verified)", "v7.0: domain architecture (7 limited-scope domains with exclusions, common interfaces, at least one independent benchmark case each, validation status derived from model maturity; 2 benchmark cases added after the check found a domain without one)", "v6.5: scientific reports (method, parameters, results with units, uncertainties, assumptions, limits, full references, base data and SVG chart; observations, calculations, rule-based interpretation and researcher conclusions kept apart; no invented number) — milestone C closed", "v6.4: complete traceability (event journal, environment without personal data, seeds, reproducible ZIP package with data, original files, bundled code, reproduce.py and SHA-256 manifest; third-party reproduction verified in an isolated process; altered packages refused)", "v6.3: model fitting (Levenberg-Marquardt, published Bates & Watts estimates reproduced, standard errors and CIs with verified coverage, residual diagnostics, separate validation data, extrapolation flagged, replayable fits tied to the dataset hash)", "v6.2: data import and quality (CSV/JSON preview, units from headers, schema check, missing values, duplicates and modified-z outliers reported without automatic removal, transformations listed, original file kept byte for byte)", "v6.1: sources and references (single bibliography without orphans, every contract/constant/adapter/unit cites its source, numeric defaults labelled illustrative, approximate values flagged, automatic reference check)", "v6.0: versioned data catalogue (one schema, five data kinds kept apart, sourced experimental datasets, SI/CODATA constants, version lock, search, filters, CSV export)", "v5.9: independent benchmark suite (33 cases, 15 engines, published and analytical references, negative results) and condition consistency in multi-model experiments", "v5.8: multi-model experiments (unit-checked bindings, time-scale checks, per-step provenance, weakest-link maturity, replay)", "v5.7 maturity levels: concept, computable, verified, validated on data with machine-checked evidence (validation fails if a cited test did not pass); 10 catalogue models verified against independent references; maturity badges; wrong template count corrected", "v5.6 SBML: compatibility analysis with correct detection of unsupported features (rules were silently ignored before), SBML packages, unit definitions and dimensional check of kinetic laws, Level 3 missing values refused, local vs global parameters, provenance, adaptive integrators", "v5.5 analyses: robust contract-based sweeps as cancellable background jobs with CSV export, local sensitivity verified on analytical elasticities, Monte Carlo with four distributions, bootstrap interval with tested coverage, separated uncertainty kinds, causal-interpretation warning", "v5.4 advanced circuits: exact first-order RC/RL transients of workbench circuits via Thevenin reduction, series RLC step response in three regimes, checked against hand formulas, independent numerical integration and energy balances, voltage/current plots", "v5.3 validated kinetics: 7 analytical cases with all three integrators, element conservation and positivity, generated convergence report documenting RK4 limits and error-estimate quality", "v5.2 numerics: explicit tolerances and stopping criteria, typed numerical errors with diagnostics, adaptive Dormand-Prince and extrapolated implicit Euler (stiff), Robertson reference reproduced, uncertainty kinds separated", "v5.1 units and constants: dimensional unit system with prefixes and compound expressions, incompatible dimensions refused, quantities with units accepted by the standard run, versioned sourced constants used by the engines, derived rate-constant units, dimensional tests of 18 equations", "v5.0 common model contracts: 17 machine-readable contracts (typed parameters with units and bounds, outputs with units, assumptions, validity, error codes, references), validation before computation, standard run envelope, single error format, layer separation", "v4.9 release candidate: archive verified in a clean directory, application started without third-party packages, suite run on several Python versions, consolidated installation guide, previous documents archived in docs/history", "v4.8 interface quality and local security: foreign Host (DNS rebinding) and foreign Origin (CSRF) requests refused, central handling of network and non-JSON errors, double-submission guard on calculation buttons, WCAG AA contrast fixes, zero critical/serious axe-core violations, keyboard-only circuit path, console free of errors", "v4.7 linked instruments: simulated readings of quantities from verified saved dossiers (circuit voltages/currents, kinetics concentrations via Beer-Lambert, stoichiometric amounts), explicit unit conversion, model numerical uncertainty in the budget, provenance and replayable reading dossiers", "v4.6 chemistry path: stoichiometry and kinetics saved as verifiable, replayable dossiers from the interface; RK4 step-doubling error estimate with coarse-step warning; unique reaction IDs; unbalanced reactions refused unless allowed; unknown chemical elements refused", "v4.5 save/restore: unified schema-2 dossiers with app/engine versions and full-dossier hash for every saving endpoint, three-level verification, replay with result comparison, SQLite schema migration with automatic backup, lossless history export/import refusing altered files, workspace file import", "v4.4 DC solver consistency: floating sub-networks detected and named before solving, no-current branches and ignored components reported, relative singularity threshold, mixed-precision iterative refinement with per-node and per-branch uncertainty, KCL/ground-return/power balance checked against propagated bounds, explicit sign conventions; verified against closed-form and exact rational references", "v4.3 reliable workbench state: one canonical save/export format, validated restore with cleanup report, recursive deletion of contents and wires, empty values flagged instead of becoming 0, duplication, visible marking of components the DC solver does not compute", "v4.2 browser-verified workbench path: Playwright end-to-end tests, single-submission solve, coded and translated circuit errors, robust JSON body handling and logged internal errors", "v4.1 reproducibility: verify saved configuration hashes and replay supported saved DC workbench circuits into new dossiers" , "v4.0 experiment lifecycle: workbench circuit runs are saved as traceable SQLite experiment dossiers with configuration hashes, results, assumptions, limitations and history IDs", "v3.9 accessibility: keyboard-operable workbench items, visible focus, category state announcements and live updates for library and properties", "v3.8 interface reliability: visible local API connection status, actionable offline guidance, explicit workspace restore and robust save errors", "v3.7 virtual instruments: seeded simulated readings, calibration correction, display resolution, uncertainty budget and comparison with theory; explicit non-experimental status", "v3.2 expanded multidisciplinary catalog: 18 disciplines, 58 components, 70 equipment entries, 42 experiment workflows, 43 model entries including 33 L0 templates; sequential A-to-B-to-C kinetics remains available", "v2.7 graphical pin-to-pin circuit connections translated into a netlist and solved by the DC nodal engine","analytical RC/RL step response", "series RLC AC phasor analysis", "logarithmic RLC frequency sweep", "bounded multi-parameter least-squares fitting with residual diagnostics", "cross-model software sanity validation suite", "seven additional numerical solvers", "generic multi-model parameter sweeps", "generic seeded Monte Carlo parameter uncertainty", "reference comparison with model output column mapping", "ten-stage scientific development roadmap", "interactive multilingual workbench, categorized draggable catalog and local JSON export", "v3.5 kinetic engine bridge: abstract A/B/C species concentrations can be loaded from the workbench into the RK4 reaction-network simulator; local request cancellation and result export", "v3.6 server-side stoichiometric batch solver with formula parsing, limiting-reactant calculation, atom-balance rejection and auditable material balance", "v2.6 sample containment inside equipment, equipment operation panel, thermal setpoint transfer, conceptual microscopy/PCR checks, Beer-Lambert absorbance with user-supplied parameters, and stoichiometric reactions inside a reactor", "ideal dilution balance in the new workbench", "DC resistive circuit solver using nodal analysis with node voltages, branch currents, equivalent resistance, power and numerical KCL/power-balance checks", "visual virtual-bench workspace and protocol designer", "equipment-aware material-flow calculations and instrument uncertainty models", "descriptive CSV profiling and exploratory correlations", "bounded global-parameter sweeps for supported SBML models", "heat diffusion and SIR solvers connected to virtual-lab workflows", "equipment compatibility checks", "solution dilution calculator", "enzyme assay workflow", "solver registry", "parameter sweeps", "reference-data comparison", "traceable experiment dossiers", "SQLite experiment history", "uncertainty propagation", "local sensitivity", "provenance records", "scientific library catalog", "expanded multidomain scientific knowledge base", "SI unit and dimension reference", "selected physical constants", "local SBML model intake", "CSV reference dataset registry with provenance", "SBML subset simulator using fixed-step RK4"]})
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
        job_match = re.fullmatch(r"/api/jobs/([0-9a-f]{12})(\.csv)?", parsed.path)
        if job_match:
            try:
                if job_match.group(2):
                    result = jobs.MANAGER.result(job_match.group(1))
                    if result is None:
                        return self._send(409, {"error": "The job has no completed result to export.", "error_code": "job_not_completed"})
                    return self._send(200, analysis.to_csv(result), "text/csv; charset=utf-8")
                return self._send(200, jobs.MANAGER.public(job_match.group(1)))
            except KeyError:
                return self._send(404, {"error": "Unknown or expired job.", "error_code": "unknown_job"})
        if parsed.path == "/api/contracts":
            return self._send(200, {"contract_version": model_registry.CONTRACT_VERSION, "contracts": model_registry.list_contracts()})
        if parsed.path.startswith("/api/contracts/"):
            try:
                return self._send(200, model_registry.get_contract(parsed.path.rsplit("/", 1)[1]))
            except ContractError as exc:
                return self._send(404, {"error": str(exc), "error_code": exc.code, "error_params": exc.params})
        if parsed.path == "/api/history/export":
            return self._send(200, experiment_service.export_all())
        if parsed.path == "/api/history/replayable":
            return self._send(200, {"models": experiment_service.replayable_models()})
        report_match = re.fullmatch(r"/api/history/(\d+)/report\.(md|html)", parsed.path)
        if report_match:
            try:
                report = reports.build(int(report_match.group(1)))
            except reports.ReportError as exc:
                return self._send(404, {"error": str(exc), "error_code": exc.code})
            if report_match.group(2) == "md":
                return self._send(200, reports.to_markdown(report), "text/markdown; charset=utf-8")
            return self._send(200, reports.to_html(report), "text/html; charset=utf-8")
        if parsed.path.startswith("/api/history/"):
            match = re.fullmatch(r"/api/history/(\d+)(/verify|/export|/quantities|/package|/events)?", parsed.path)
            if not match:
                return self._send(400, {"error": "Experiment ID must be an integer; optional suffix: /verify or /export"})
            experiment_id = int(match.group(1))
            try:
                if match.group(2) == "/verify":
                    return self._send(200, experiment_service.verify(experiment_id))
                if match.group(2) == "/export":
                    return self._send(200, experiment_service.export_one(experiment_id))
                if match.group(2) == "/quantities":
                    return self._send(200, experiment_service.quantities(experiment_id))
                if match.group(2) == "/events":
                    if get_experiment(experiment_id) is None:
                        return self._send(404, {"error": "Experiment not found"})
                    return self._send(200, {"experiment_id": experiment_id, "events": trace_package.events(experiment_id)})
                if match.group(2) == "/package":
                    try:
                        package, manifest = trace_package.build_package(experiment_id)
                    except trace_package.PackageError as exc:
                        return self._send(404 if exc.code == "not_found" else 409, {"error": str(exc), "error_code": exc.code})
                    return self._send(200, package, "application/zip",
                                      {"Content-Disposition": f'attachment; filename="experiment_{experiment_id}_package.zip"',
                                       "X-Manifest-SHA256": manifest["manifest_sha256"]})
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
        if self._refuse_foreign():
            return
        parsed = urllib.parse.urlparse(self.path)
        is_replay_path = re.fullmatch(r"/api/history/\d+/replay", parsed.path) is not None
        model_run = re.fullmatch(r"/api/models/([a-z0-9_]+)/run", parsed.path)
        job_cancel = re.fullmatch(r"/api/jobs/([0-9a-f]{12})/cancel", parsed.path)
        if parsed.path not in ("/api/experiments", "/api/validate", "/api/sweeps", "/api/uncertainty", "/api/sensitivity", "/api/import-csv", "/api/design", "/api/import-sbml", "/api/import-dataset", "/api/simulate-sbml", "/api/lab/validate", "/api/lab/run", "/api/analyze-dataset", "/api/sweep-sbml", "/api/protocol/validate", "/api/protocol/run", "/api/research/sweep", "/api/research/uncertainty", "/api/research/compare", "/api/research/fit", "/api/scientific-ai/ask", "/api/electrical/dc-solve", "/api/electrical/workbench-solve", "/api/electrical/workbench-run", "/api/electrical/transient", "/api/electrical/ac", "/api/electrical/ac-sweep", "/api/chemistry/kinetics", "/api/chemistry/stoichiometry", "/api/chemistry/kinetics-run", "/api/chemistry/stoichiometry-run", "/api/instruments/measure", "/api/instruments/measure-linked", "/api/history/import", "/api/electrical/workbench-transient-run", "/api/electrical/rlc-step", "/api/jobs", "/api/sbml/analyze", "/api/pipelines/run", "/api/data/catalog/validate", "/api/data/preview", "/api/data/import", "/api/data/fit") and not is_replay_path and not model_run and not job_cancel:
            return self._send(404, {"error": "Not found", "error_code": "not_found"})
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
            if parsed.path == "/api/jobs":
                result = jobs.submit_from_request(request)
            elif job_cancel:
                try:
                    result = jobs.MANAGER.cancel(job_cancel.group(1))
                except KeyError:
                    return self._send(404, {"error": "Unknown or expired job.", "error_code": "unknown_job"})
            elif model_run:
                result = model_registry.run_model(model_run.group(1), request.get("inputs", {}))
            elif is_replay_path:
                result = experiment_service.replay(int(parsed.path.split("/")[3]))
            elif parsed.path == "/api/history/import":
                result = experiment_service.import_bundle(request)
            elif parsed.path == "/api/electrical/workbench-transient-run":
                result = experiment_service.run_workbench_transient(request)
            elif parsed.path == "/api/sbml/analyze":
                result = analyze_sbml(request.get("asset_id"))
            elif parsed.path == "/api/electrical/rlc-step":
                result = model_registry.run_model("series_rlc_step_response", request)["result"]
            elif parsed.path == "/api/instruments/measure-linked":
                result = experiment_service.measure_linked(request)
            elif parsed.path == "/api/instruments/measure":
                result = simulate_instrument_measurement(request)
            elif parsed.path == "/api/data/fit":
                result = experiment_service.run_fit(request)
            elif parsed.path == "/api/data/preview":
                report = data_import.analyze(request.get("content"), request.get("filename") or "data.csv", request.get("format"))
                result = {k: v for k, v in report.items() if k != "rows"}
                result["schema_problems"] = data_import.check_schema(report, request["expected_schema"]) if isinstance(request.get("expected_schema"), list) else None
            elif parsed.path == "/api/data/import":
                metadata = request.get("metadata") if isinstance(request.get("metadata"), dict) else {}
                result = data_import.import_file(request.get("content"), request.get("filename") or "data.csv", metadata, request.get("format"))
            elif parsed.path == "/api/data/catalog/validate":
                data_catalog.validate_dataset(request)
                result = {"valid": True, "content_sha256": data_catalog.canonical_hash(request)}
            elif parsed.path == "/api/pipelines/run":
                result = experiment_service.run_pipeline(request)
            elif parsed.path == "/api/chemistry/kinetics-run":
                result = experiment_service.run_kinetics(request)
            elif parsed.path == "/api/chemistry/stoichiometry-run":
                result = experiment_service.run_stoichiometry(request)
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
        except ContractError as exc:
            return self._send(404 if exc.code == "unknown_model" else 400, {"error": str(exc), "error_code": exc.code, "error_params": exc.params})
        except (ValueError, json.JSONDecodeError, UnicodeDecodeError, SBMLSimulationError, CircuitError, ElectricalModelError, WorkbenchCircuitError, ChemicalKineticsError, StoichiometryError) as exc:
            # v5.0: every refused request carries a stable error_code (specific when the engine provides one).
            body = {"error": str(exc), "error_code": getattr(exc, "code", None) or ("invalid_json" if isinstance(exc, json.JSONDecodeError) else "invalid_request"),
                    "error_params": getattr(exc, "params", {})}
            return self._send(400, body)
        except Exception:
            # Do not expose internal exception details through the HTTP API, but keep them in the terminal log.
            print(f"[VirtualLab] Internal error on POST {parsed.path}", file=sys.stderr)
            traceback.print_exc()
            return self._send(500, {"error": "Internal error. Check the local terminal logs.", "error_code": "internal_error"})

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
