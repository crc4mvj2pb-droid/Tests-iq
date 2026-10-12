"""Registry of model contracts (v5.0) and the standard execution envelope.

Every scientific engine of the platform is declared here with its contract (contracts.py),
its runner and an example input. `run_model` is the single standardized way to execute a
model: contract validation → engine → envelope with declared outputs, units and provenance.
The legacy endpoints keep working unchanged; they call the same engines.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Callable

import chemical_kinetics
import electrical_advanced
import electrical_circuits
import reaction_stoichiometry
import workbench_circuit
from contracts import CONTRACT_VERSION, ContractError, check_contract, output, param, resolve_path, validate_inputs
from models import execute_model
from version import APP_VERSION

MODELS_ENGINE_VERSION = "1.0"
TEXT = param  # alias for readability below


def _contract(id, version, title, domain, engine, parameters, outputs, assumptions, validity, error_codes, references, equations=()):
    return {"id": id, "version": version, "contract_version": CONTRACT_VERSION, "title": title, "domain": domain, "engine": engine,
            "parameters": parameters, "outputs": outputs, "assumptions": list(assumptions), "validity": list(validity),
            "error_codes": list(error_codes), "references": list(references), "equations": list(equations)}


AU = "a.u."  # arbitrary / model units: not convertible to any physical unit

REGISTRY: dict[str, dict[str, Any]] = {}


def register(contract: dict[str, Any], runner: Callable[[dict], dict], example: dict | None) -> None:
    REGISTRY[contract["id"]] = {"contract": contract, "runner": runner, "example": example}


# ---- electrical -------------------------------------------------------------------------------

register(_contract(
    "dc_resistive_network", electrical_circuits.ENGINE_VERSION, "Réseau résistif CC — analyse nodale", "electrical", electrical_circuits.ENGINE_ID,
    [param("source_voltage", "number", unit="V", minimum=-1e6, maximum=1e6, default=9.0, description="Ideal source voltage between source_node and ground"),
     param("ground", "string", default="0", description="Name of the reference node (0 V)"),
     param("source_node", "string", default="S", description="Node held at source_voltage"),
     param("resistors", "array", required=True, description="[{id, a, b, resistance_ohm}] with 0 < R ≤ 1e15 Ω")],
    [output("source_current", "source_current_a", "A", "Current leaving the + terminal"),
     output("total_resistor_power", "total_resistor_power_w", "W"),
     output("power_balance_error", "power_balance_error_w", "W")],
    ["DC steady state", "Ideal voltage source, ideal wires", "Linear ohmic resistors"],
    ["One ideal DC source", "0 < R ≤ 1e15 Ω", "Up to 200 resistors"],
    ["invalid_parameter", "singular_network"],
    ["Kirchhoff's current law; nodal analysis (e.g. Nilsson & Riedel, Electric Circuits)"],
    ["G·v = i (conductance matrix, ground at 0 V)", "I = (Va − Vb)/R", "P = V·I"]),
    lambda p: electrical_circuits.solve_dc_circuit(p),
    {"source_voltage": 12.0, "resistors": [{"id": "R1", "a": "S", "b": "N", "resistance_ohm": 1000}, {"id": "R2", "a": "N", "b": "0", "resistance_ohm": 2000}]})

register(_contract(
    "workbench_dc_circuit", f"{workbench_circuit.ENGINE_VERSION}+{electrical_circuits.ENGINE_VERSION}", "Circuit CC câblé sur la paillasse", "electrical", workbench_circuit.ENGINE_ID,
    [param("components", "array", required=True, description="[{instanceId, id, displayName, qty}] — qty in V for sources, Ω for resistors"),
     param("connections", "array", required=True, description="[{a, pinA, b, pinB}] ideal wires between terminals"),
     param("name", "string", default="", description="Experiment title"), param("question", "string", default="", description="Scientific question")],
    [output("source_current", "source_current_a", "A"), output("total_resistor_power", "total_resistor_power_w", "W")],
    ["Graphical wires are ideal conductors", "One ideal DC source, one ground, linear resistors"],
    ["Capacitors, inductors and nonlinear devices are refused when wired"],
    ["invalid_resistance", "invalid_voltage", "terminal_unwired", "source_short", "resistor_bypassed", "floating_network", "unsupported_connected", "source_count", "ground_count"],
    ["Union-find net extraction + nodal analysis"]),
    lambda p: workbench_circuit.solve_workbench_circuit(p),
    {"components": [{"instanceId": "s", "id": "dc-source", "displayName": "S", "qty": 9}, {"instanceId": "r", "id": "resistor", "displayName": "R", "qty": 1000},
                    {"instanceId": "g", "id": "ground", "displayName": "G", "qty": 0}],
     "connections": [{"a": "s", "pinA": "P", "b": "r", "pinB": "A"}, {"a": "r", "pinA": "B", "b": "g", "pinB": "GND"}, {"a": "s", "pinA": "N", "b": "g", "pinB": "GND"}]})

register(_contract(
    "rc_rl_step_response", electrical_advanced.ENGINE_VERSION, "Réponse indicielle RC / RL idéale", "electrical", electrical_advanced.ENGINE_ID,
    [param("kind", "enum", choices=["RC", "RL"], default="RC"),
     param("source_voltage_v", "number", unit="V", minimum=-1e6, maximum=1e6, default=5.0),
     param("resistance_ohm", "number", unit="Ω", minimum=1e-9, maximum=1e12, default=1000.0),
     param("capacitance_f", "number", unit="F", minimum=1e-15, maximum=1e6, default=1e-6),
     param("inductance_h", "number", unit="H", minimum=1e-15, maximum=1e6, default=1e-6),
     param("duration_s", "number", unit="s", minimum=1e-12, maximum=1e9, default=0.01),
     param("points", "integer", unit="1", minimum=2, maximum=2001, default=101),
     param("initial_voltage_v", "number", unit="V", minimum=-1e9, maximum=1e9, default=0.0),
     param("initial_current_a", "number", unit="A", minimum=-1e9, maximum=1e9, default=0.0)],
    [output("time_constant", "time_constant_s", "s"), output("first_time", "points[0].time_s", "s")],
    ["Ideal step source", "Linear R, C or L; no parasitics"], ["Single first-order series circuit"], ["invalid_parameter"],
    ["First-order linear ODE, analytical solution"], ["τ = R·C (RC) or L/R (RL)", "x(t) = x∞ + (x0 − x∞)·e^(−t/τ)"]),
    lambda p: electrical_advanced.simulate_first_order_step(p), {})

_RLC_PARAMS = [param("source_voltage_rms_v", "number", unit="V", minimum=0, maximum=1e6, default=5.0),
               param("resistance_ohm", "number", unit="Ω", minimum=1e-9, maximum=1e12, default=100.0),
               param("inductance_h", "number", unit="H", minimum=0, maximum=1e6, default=0.01),
               param("capacitance_f", "number", unit="F", minimum=1e-15, maximum=1e6, default=1e-6)]
register(_contract(
    "series_rlc_ac", electrical_advanced.ENGINE_VERSION, "RLC série en régime sinusoïdal", "electrical", electrical_advanced.ENGINE_ID,
    _RLC_PARAMS + [param("frequency_hz", "number", unit="Hz", minimum=1e-9, maximum=1e12, default=1000.0)],
    [output("impedance_magnitude", "impedance_magnitude_ohm", "Ω"), output("current_rms", "current_rms_a", "A"),
     output("real_power", "real_power_w", "W"), output("power_factor", "power_factor", "1")],
    ["Sinusoidal steady state", "RMS phasors"], ["Linear ideal R, L, C in series"], ["invalid_parameter"],
    ["Phasor analysis"], ["Z = R + j(ωL − 1/(ωC))", "I = V/|Z|"]),
    lambda p: electrical_advanced.solve_series_rlc_ac(p), {})

register(_contract(
    "series_rlc_frequency_sweep", electrical_advanced.ENGINE_VERSION, "Balayage fréquentiel RLC série", "electrical", electrical_advanced.ENGINE_ID,
    _RLC_PARAMS + [param("start_frequency_hz", "number", unit="Hz", minimum=1e-9, maximum=1e12, default=10.0),
                   param("stop_frequency_hz", "number", unit="Hz", minimum=1e-9, maximum=1e12, default=1e6),
                   param("points", "integer", unit="1", minimum=2, maximum=2001, default=101)],
    [output("first_frequency", "points[0].frequency_hz", "Hz"), output("peak_current_sampled", "peak_current_sampled.current_rms_a", "A")],
    ["Each point is an independent steady-state solve"], ["Logarithmic spacing"], ["invalid_parameter"], ["Phasor analysis"]),
    lambda p: electrical_advanced.sweep_series_rlc_frequency(p), {})

# ---- chemistry --------------------------------------------------------------------------------

register(_contract(
    "mass_action_kinetics", chemical_kinetics.ENGINE_VERSION, "Cinétique de réseau de réactions (action de masse)", "chemistry", chemical_kinetics.ENGINE_ID,
    [param("species", "array", required=True, description="[{id, initial_concentration, atoms?}] — consistent concentration unit"),
     param("reactions", "array", required=True, description="[{id, reactants, products, rate_constant, activation_energy_j_mol?, reference_temperature_k?}]"),
     param("duration", "number", unit="s", minimum=0, exclusive_minimum=True, maximum=1e6, required=True),
     param("dt", "number", unit="s", minimum=0, exclusive_minimum=True, maximum=1e6, required=True),
     param("temperature_k", "number", unit="K", minimum=0, exclusive_minimum=True, maximum=1e5, default=298.15),
     param("allow_unbalanced", "boolean", default=False),
     param("name", "string", default=""), param("question", "string", default="")],
    [output("integration_steps", "summary.integration_steps", "1"), output("temperature", "temperature_k", "K")],
    ["Well-mixed, constant volume", "Elementary mass-action rate laws", "Constant temperature"], ["Fixed-step RK4; error estimated by step doubling"],
    ["invalid_parameter", "negative_concentration", "unbalanced_reaction"],
    ["Guldberg & Waage (mass action); Arrhenius (1889); Butcher, Numerical Methods for ODEs (RK4)"],
    ["d[X]/dt = Σ ν·k·Π[R]^ν", "k(T) = k_ref·exp(−Ea/R·(1/T − 1/T_ref))"]),
    lambda p: chemical_kinetics.simulate_reaction_network(p),
    {"species": [{"id": "A", "initial_concentration": 1.0}, {"id": "B", "initial_concentration": 0.0}],
     "reactions": [{"id": "r", "reactants": {"A": 1}, "products": {"B": 1}, "rate_constant": 0.5}], "duration": 4.0, "dt": 0.01})

register(_contract(
    "stoichiometry", reaction_stoichiometry.ENGINE_VERSION, "Stœchiométrie et réactif limitant", "chemistry", reaction_stoichiometry.ENGINE_ID,
    [param("reaction_id", "string", default="custom_reaction"), param("reaction_name", "string", default=""),
     param("reactants", "object", required=True, description="{species_id: integer coefficient}"),
     param("products", "object", required=True), param("species", "array", required=True, description="[{id, amount_mol, formula?}]"),
     param("name", "string", default=""), param("question", "string", default="")],
    [output("reaction_extent", "reaction_extent_mol", "mol")],
    ["One irreversible batch step, complete conversion of the limiting reactant"], ["Atom balance checked when formulas are given"],
    ["not_atom_balanced", "unknown_element", "invalid_parameter"], ["Lavoisier mass conservation; IUPAC element symbols"],
    ["ξ = min(n_i/ν_i)", "n_j = n_j0 + ν_j·ξ"]),
    lambda p: reaction_stoichiometry.calculate_stoichiometry(p),
    {"reactants": {"H2": 2, "O2": 1}, "products": {"H2O": 2},
     "species": [{"id": "H2", "amount_mol": 4, "formula": "H2"}, {"id": "O2", "amount_mol": 1, "formula": "O2"}, {"id": "H2O", "amount_mol": 0, "formula": "H2O"}]})

# ---- catalogue models (models.py) -----------------------------------------------------------

def _catalogue(model_id, title, domain, parameters, outputs, assumptions, validity, references, equations, example=None):
    register(_contract(model_id, MODELS_ENGINE_VERSION, title, domain, "model_catalog", parameters, outputs, assumptions, validity,
                       ["invalid_parameter", "numerical_instability"], references, equations),
             lambda p, m=model_id: execute_model(m, p), example or {})


_catalogue("enzyme_kinetics", "Cinétique enzymatique — Michaelis–Menten", "biology",
           # vmax, km and s_max have no default in the engine (run_enzyme requires them): the contract says so.
           [param("vmax", "number", unit=AU, minimum=0, exclusive_minimum=True, required=True), param("km", "number", unit=AU, minimum=0, exclusive_minimum=True, required=True),
            param("s_max", "number", unit=AU, minimum=0, exclusive_minimum=True, required=True), param("points", "integer", unit="1", minimum=3, maximum=501, default=21)],
           [output("max_rate", "summary.max_rate_calculated", AU)], ["Quasi-steady state, single substrate"], ["Arbitrary units"],
           ["Michaelis & Menten (1913); Johnson & Goody (2011) translation"], ["v = Vmax·S/(Km + S)"], {"vmax": 1.2, "km": 0.8, "s_max": 6.4})
_catalogue("sir_epidemic", "Épidémie SIR", "medicine",
           [param("population", "number", unit="1", minimum=0, exclusive_minimum=True, default=10000.0), param("beta", "number", unit="1/d", minimum=0, default=0.3),
            param("gamma", "number", unit="1/d", minimum=0, default=0.1), param("initial_infected", "number", unit="1", minimum=0, exclusive_minimum=True, default=10.0),
            param("days", "number", unit="d", minimum=0, exclusive_minimum=True, maximum=1000, default=160.0), param("dt", "number", unit="d", minimum=0.001, maximum=1, default=0.1)],
           [output("peak_infectious", "summary.peak_infectious", "1"), output("peak_time", "summary.peak_time_days", "d")],
           ["Homogeneous mixing", "Constant β and γ"], ["Explicit Euler; illustrative only"], ["Kermack & McKendrick (1927)"],
           ["dS/dt = −βSI/N", "dI/dt = βSI/N − γI", "dR/dt = γI"])
_catalogue("heat_diffusion_1d", "Diffusion thermique 1D", "physics",
           [param("length_m", "number", unit="m", minimum=0, exclusive_minimum=True, default=1.0), param("diffusivity_m2_s", "number", unit="m^2/s", minimum=0, exclusive_minimum=True, default=1e-5),
            param("left_temp_c", "number", unit="°C", minimum=-273.15, default=100.0), param("right_temp_c", "number", unit="°C", minimum=-273.15, default=20.0),
            param("initial_temp_c", "number", unit="°C", minimum=-273.15, default=20.0), param("nodes", "integer", unit="1", minimum=5, maximum=201, default=21),
            param("dt_s", "number", unit="s", minimum=0, exclusive_minimum=True, default=1.0), param("total_time_s", "number", unit="s", minimum=0, exclusive_minimum=True, default=1000.0)],
           [output("final_midpoint_temperature", "summary.final_midpoint_temp_c", "°C"), output("fourier_number", "summary.fourier_number", "1")],
           ["Homogeneous material, constant diffusivity", "Dirichlet boundaries"], ["Explicit FTCS, stable for α·dt/dx² ≤ 0.5"],
           ["Fourier (1822); Crank, The Mathematics of Diffusion"], ["∂T/∂t = α·∂²T/∂x²"])
_catalogue("logistic_growth", "Croissance logistique", "biology",
           [param("initial_population", "number", unit=AU, minimum=0, exclusive_minimum=True, default=10.0), param("carrying_capacity", "number", unit=AU, minimum=0, exclusive_minimum=True, default=1000.0),
            param("growth_rate", "number", unit=AU, minimum=0, default=0.2), param("duration", "number", unit=AU, minimum=0, exclusive_minimum=True, maximum=10000, default=30.0),
            param("points", "integer", unit="1", minimum=3, maximum=1001, default=61)],
           [output("final_population", "summary.final_population", AU)], ["Constant r and K"], ["Analytical solution"], ["Verhulst (1838)"],
           ["N(t) = K/(1 + ((K − N0)/N0)·e^(−rt))"])
_catalogue("first_order_reaction", "Réaction du premier ordre A → B", "chemistry",
           [param("initial_A", "number", unit=AU, minimum=0, default=1.0), param("rate_constant", "number", unit=AU, minimum=0, default=0.2),
            param("duration", "number", unit=AU, minimum=0, exclusive_minimum=True, maximum=100000, default=10.0), param("points", "integer", unit="1", minimum=3, maximum=1001, default=51)],
           [output("final_A", "summary.final_A", AU)], ["Irreversible first-order kinetics"], ["Analytical solution"], ["Atkins, Physical Chemistry"], ["[A] = [A]0·e^(−kt)"])
_catalogue("environmental_decay", "Décroissance environnementale du premier ordre", "environment",
           [param("initial_load", "number", unit=AU, minimum=0, default=100.0), param("removal_rate", "number", unit=AU, minimum=0, default=0.05),
            param("duration", "number", unit=AU, minimum=0, exclusive_minimum=True, maximum=1e7, default=100.0), param("points", "integer", unit="1", minimum=3, maximum=1001, default=51)],
           [output("final_load", "summary.final_load", AU)], ["Single well-mixed compartment"], ["Analytical solution"], ["First-order removal kinetics"], ["C = C0·e^(−kt)"])
_catalogue("one_compartment_pk", "Pharmacocinétique à un compartiment (pédagogique)", "medicine",
           [param("input_amount", "number", unit=AU, minimum=0, default=100.0), param("distribution_volume", "number", unit=AU, minimum=0, exclusive_minimum=True, default=10.0),
            param("clearance", "number", unit=AU, minimum=0, default=1.0), param("duration", "number", unit=AU, minimum=0, exclusive_minimum=True, maximum=100000, default=24.0),
            param("points", "integer", unit="1", minimum=3, maximum=1001, default=49)],
           [output("final_concentration", "summary.final_concentration", AU)], ["IV bolus, first-order elimination"], ["Teaching model; not for dosing"],
           ["Gibaldi & Perrier, Pharmacokinetics"], ["C(t) = (D/V)·e^(−(CL/V)t)"])
_catalogue("lotka_volterra", "Proies–prédateurs (Lotka–Volterra)", "biology",
           [param("initial_prey", "number", unit=AU, minimum=0, exclusive_minimum=True, default=40.0), param("initial_predators", "number", unit=AU, minimum=0, exclusive_minimum=True, default=9.0),
            param("prey_growth", "number", unit=AU, minimum=0, default=1.0), param("predation_rate", "number", unit=AU, minimum=0, default=0.1),
            param("predator_growth", "number", unit=AU, minimum=0, default=0.075), param("predator_decay", "number", unit=AU, minimum=0, default=1.5),
            param("duration", "number", unit=AU, minimum=0, exclusive_minimum=True, maximum=1000, default=20.0), param("dt", "number", unit=AU, minimum=0, exclusive_minimum=True, maximum=0.1, default=0.01)],
           [output("final_prey", "summary.final_prey", AU)], ["Deterministic, no carrying capacity"], ["Fixed-step RK4"], ["Lotka (1925); Volterra (1926)"],
           ["dx/dt = αx − βxy", "dy/dt = δxy − γy"])
_catalogue("leaky_integrate_fire", "Neurone intègre-et-tire à fuite", "neuroscience",
           [param("v_rest_mv", "number", unit="mV", default=-65.0), param("v_reset_mv", "number", unit="mV", default=-70.0), param("v_threshold_mv", "number", unit="mV", default=-50.0),
            param("initial_voltage_mv", "number", unit="mV", default=-65.0), param("tau_ms", "number", unit="ms", minimum=0, exclusive_minimum=True, default=10.0),
            param("resistance_mohm", "number", unit="MΩ", minimum=0, default=10.0), param("current_na", "number", unit="nA", minimum=0, default=2.0),
            param("duration_ms", "number", unit="ms", minimum=0, exclusive_minimum=True, maximum=10000, default=100.0), param("dt_ms", "number", unit="ms", minimum=0, exclusive_minimum=True, default=0.1)],
           [output("spike_count", "summary.spike_count", "1"), output("equilibrium_voltage", "summary.equilibrium_voltage_mv", "mV")],
           ["Single compartment, constant current", "No refractory period"], ["Exact exponential update between spikes"], ["Lapicque (1907); Gerstner et al., Neuronal Dynamics"],
           ["τ·dV/dt = −(V − V_rest) + R·I"])
_catalogue("arrhenius_reaction", "Réaction du premier ordre avec loi d'Arrhenius", "chemistry",
           [param("initial_A", "number", unit=AU, minimum=0, default=1.0), param("pre_exponential_s_inv", "number", unit="1/s", minimum=0, default=1.0),
            param("activation_energy_j_mol", "number", unit="J/mol", minimum=0, default=40000.0), param("temperature_k", "number", unit="K", minimum=1, default=298.15),
            param("duration_s", "number", unit="s", minimum=0, exclusive_minimum=True, maximum=100000, default=10.0), param("points", "integer", unit="1", minimum=3, maximum=1001, default=51)],
           [output("rate_constant", "summary.rate_constant_s_inv", "1/s")], ["Constant temperature"], ["Analytical solution"], ["Arrhenius (1889)"],
           ["k = A·exp(−Ea/(R·T))", "[A] = [A]0·e^(−kt)"])


# ---- standard execution ---------------------------------------------------------------------

def list_contracts() -> list[dict[str, Any]]:
    return [entry["contract"] for entry in REGISTRY.values()]


def get_contract(model_id: str) -> dict[str, Any]:
    if model_id not in REGISTRY:
        raise ContractError(f"Unknown model '{model_id}'.", "unknown_model", model_id=model_id)
    return REGISTRY[model_id]["contract"]


def run_model(model_id: str, inputs: Any, converter=None) -> dict[str, Any]:
    """Validate inputs against the contract, run the engine and return the standard envelope."""
    contract = get_contract(model_id)
    normalized = validate_inputs(contract, inputs, converter=converter)
    result = REGISTRY[model_id]["runner"](dict(normalized))
    outputs = {}
    for out in contract["outputs"]:
        try:
            outputs[out["name"]] = {"value": resolve_path(result, out["path"]), "unit": out["unit"]}
        except (KeyError, IndexError, TypeError):
            outputs[out["name"]] = {"value": None, "unit": out["unit"], "missing": True}
    return {"model_id": model_id, "model_version": contract["version"], "contract_version": contract["contract_version"],
            "inputs": normalized, "outputs": outputs, "result": result,
            "warnings": result.get("warnings", []) if isinstance(result, dict) else [],
            "assumptions": contract["assumptions"], "limitations": result.get("limitations", []) if isinstance(result, dict) else [],
            "provenance": {"engine": contract["engine"], "engine_version": contract["version"], "app_version": APP_VERSION,
                           "computed_at": datetime.now(timezone.utc).isoformat(timespec="seconds")}}


def contract_problems() -> dict[str, list[str]]:
    return {mid: check_contract(entry["contract"]) for mid, entry in REGISTRY.items() if check_contract(entry["contract"])}
