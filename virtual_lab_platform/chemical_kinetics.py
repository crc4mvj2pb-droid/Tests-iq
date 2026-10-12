"""Small, explicit mass-action reaction-network simulator.

Educational/engineering prototype: parameters are user supplied; this is not a
general-purpose quantum chemistry or thermodynamic equilibrium solver.
"""
from __future__ import annotations
import math

R_GAS = 8.31446261815324
# 1.0: v2.8–v4.5. 2.0 (v4.6): unique reaction IDs, unbalanced reactions refused unless allowed,
# step-doubling (Richardson) estimate of the RK4 global error with an accuracy warning.
ENGINE_ID = "mass_action_rk4"
ENGINE_VERSION = "2.0"
# The error estimate repeats the run at dt/2; skipped above this work budget (steps × equations).
ERROR_ESTIMATE_WORK_LIMIT = 2_000_000
DISPLAY_RELATIVE_PRECISION = 1e-6  # final concentrations are displayed with 6 significant digits


class ChemicalKineticsError(ValueError):
    """Invalid reaction network or unsupported simulation request."""


def _finite_number(value, name, *, minimum=None, strictly_positive=False):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ChemicalKineticsError(f"{name} must be a finite number.")
    value = float(value)
    if minimum is not None and value < minimum:
        raise ChemicalKineticsError(f"{name} must be >= {minimum}.")
    if strictly_positive and value <= 0:
        raise ChemicalKineticsError(f"{name} must be greater than zero.")
    return value


def simulate_reaction_network(request: dict) -> dict:
    """Integrate a concentration-based reaction network using fixed-step RK4.

    Request shape:
      species: [{"id": "A", "initial_concentration": 1.0, "atoms": {"X": 1}}, ...]
      reactions: [{"id":"r1", "reactants":{"A":1}, "products":{"B":1},
                   "rate_constant":0.2,
                   "activation_energy_j_mol":0, "reference_temperature_k":298.15}]
      duration, dt, temperature_k (optional; units are user-defined except temperature)
    """
    if not isinstance(request, dict):
        raise ChemicalKineticsError("Request must be a JSON object.")
    species = request.get("species")
    reactions = request.get("reactions")
    if not isinstance(species, list) or not 1 <= len(species) <= 20:
        raise ChemicalKineticsError("species must contain between 1 and 20 species.")
    if not isinstance(reactions, list) or not 1 <= len(reactions) <= 20:
        raise ChemicalKineticsError("reactions must contain between 1 and 20 reactions.")

    ids, initial, atom_vectors = [], [], {}
    for item in species:
        if not isinstance(item, dict):
            raise ChemicalKineticsError("Each species must be an object.")
        sid = item.get("id")
        if not isinstance(sid, str) or not sid.strip() or sid in ids:
            raise ChemicalKineticsError("Species IDs must be non-empty and unique.")
        ids.append(sid)
        initial.append(_finite_number(item.get("initial_concentration"), f"{sid}.initial_concentration", minimum=0))
        atoms = item.get("atoms", {})
        if not isinstance(atoms, dict):
            raise ChemicalKineticsError(f"{sid}.atoms must be an object.")
        atom_vectors[sid] = {}
        for element, count in atoms.items():
            if not isinstance(element, str) or not element:
                raise ChemicalKineticsError(f"Invalid element key in {sid}.atoms.")
            atom_vectors[sid][element] = _finite_number(count, f"{sid}.atoms.{element}", minimum=0)

    index = {sid: i for i, sid in enumerate(ids)}
    parsed = []
    for n, reaction in enumerate(reactions, 1):
        if not isinstance(reaction, dict):
            raise ChemicalKineticsError("Each reaction must be an object.")
        rid = reaction.get("id", f"r{n}")
        if not isinstance(rid, str) or not rid.strip():
            raise ChemicalKineticsError("Reaction IDs must be non-empty strings.")
        if any(p["id"] == rid for p in parsed):
            raise ChemicalKineticsError(f"Reaction IDs must be unique: '{rid}' is used twice.")
        reactants, products = [], []
        for key, target in (("reactants", reactants), ("products", products)):
            side = reaction.get(key)
            if not isinstance(side, dict) or not side:
                raise ChemicalKineticsError(f"{rid}.{key} must be a non-empty object.")
            for sid, coeff in side.items():
                if sid not in index:
                    raise ChemicalKineticsError(f"{rid} references unknown species '{sid}'.")
                if isinstance(coeff, bool) or not isinstance(coeff, int) or coeff < 1 or coeff > 10:
                    raise ChemicalKineticsError(f"{rid} stoichiometric coefficients must be integers from 1 to 10.")
                target.append((index[sid], coeff))
        k = _finite_number(reaction.get("rate_constant"), f"{rid}.rate_constant", minimum=0)
        ea = _finite_number(reaction.get("activation_energy_j_mol", 0), f"{rid}.activation_energy_j_mol", minimum=0)
        tref = _finite_number(reaction.get("reference_temperature_k", 298.15), f"{rid}.reference_temperature_k", strictly_positive=True)
        parsed.append({"id": rid, "reactants": reactants, "products": products,
                       "k": k, "ea": ea, "tref": tref})

    duration = _finite_number(request.get("duration"), "duration", strictly_positive=True)
    dt = _finite_number(request.get("dt"), "dt", strictly_positive=True)
    temp = _finite_number(request.get("temperature_k", 298.15), "temperature_k", strictly_positive=True)
    if duration > 1e6 or dt > duration:
        raise ChemicalKineticsError("duration must be <= 1,000,000 and dt must not exceed duration.")
    ratio = duration / dt
    if abs(ratio - round(ratio)) > 1e-8:
        raise ChemicalKineticsError("duration must be divisible by dt.")
    steps = int(round(ratio))
    if steps > 20000:
        raise ChemicalKineticsError("Too many integration steps; use dt >= duration / 20000.")

    # Check element conservation only where every species has an atom formula.
    element_names = set().union(*(set(v) for v in atom_vectors.values()))
    atom_balance_checks = {}
    if element_names and all(atom_vectors[sid] for sid in ids):
        for reaction in parsed:
            deltas = {}
            for i, coeff in reaction["reactants"]:
                for el, count in atom_vectors[ids[i]].items():
                    deltas[el] = deltas.get(el, 0) - coeff * count
            for i, coeff in reaction["products"]:
                for el, count in atom_vectors[ids[i]].items():
                    deltas[el] = deltas.get(el, 0) + coeff * count
            atom_balance_checks[reaction["id"]] = all(abs(v) < 1e-12 for v in deltas.values())
    unbalanced = [rid for rid, ok in atom_balance_checks.items() if not ok]
    warnings = []
    if unbalanced:
        if request.get("allow_unbalanced") is not True:
            raise ChemicalKineticsError(
                f"Reaction(s) {', '.join(unbalanced)} are not atom-balanced with the supplied formulas. "
                "Fix the formulas or coefficients, or set allow_unbalanced to simulate anyway.")
        warnings.append({"code": "unbalanced_reaction", "params": {"reactions": ", ".join(unbalanced)},
                         "message": f"Simulated although not atom-balanced: {', '.join(unbalanced)}."})
    elif not atom_balance_checks:
        warnings.append({"code": "atom_balance_not_checked", "params": {},
                         "message": "Atom balance not checked: provide atom formulas for every species."})

    def rate_vector(conc):
        rates = []
        for rxn in parsed:
            k = rxn["k"] * math.exp((-rxn["ea"] / R_GAS) * (1.0 / temp - 1.0 / rxn["tref"]))
            rate = k
            for i, coeff in rxn["reactants"]:
                rate *= max(0.0, conc[i]) ** coeff
            rates.append(rate)
        deriv = [0.0] * len(ids)
        for rate, rxn in zip(rates, parsed):
            for i, coeff in rxn["reactants"]:
                deriv[i] -= coeff * rate
            for i, coeff in rxn["products"]:
                deriv[i] += coeff * rate
        return deriv, rates

    def add_scaled(y, terms, scale):
        return [max(-1e-12, y[i] + scale * terms[i]) for i in range(len(y))]

    def integrate(step_dt, n_steps, record):
        y = initial[:]
        rows = [{"time": 0.0, **dict(zip(ids, y))}] if record else None
        for step in range(n_steps):
            k1, _ = rate_vector(y)
            k2, _ = rate_vector(add_scaled(y, k1, step_dt / 2))
            k3, _ = rate_vector(add_scaled(y, k2, step_dt / 2))
            k4, _ = rate_vector(add_scaled(y, k3, step_dt))
            next_y = [y[i] + step_dt * (k1[i] + 2*k2[i] + 2*k3[i] + k4[i]) / 6 for i in range(len(y))]
            # A negative concentration beyond round-off signals an unstable step, not a valid result.
            if any(v < -1e-8 for v in next_y):
                raise ChemicalKineticsError(
                    f"Negative concentration encountered at t={(step+1)*step_dt:g}; reduce dt or check the kinetic model."
                )
            y = [0.0 if -1e-8 <= v < 0 else v for v in next_y]
            if record and (step == n_steps - 1 or (step + 1) % max(1, n_steps // 200) == 0):
                rows.append({"time": (step + 1) * step_dt, **dict(zip(ids, y))})
        return y, rows

    y, rows = integrate(dt, steps, True)
    # Step doubling: for RK4 the global error of the dt run is ≈ (y_dt − y_dt/2)·16/15.
    error_estimate = None
    if 2 * steps * (len(ids) + len(parsed)) <= ERROR_ESTIMATE_WORK_LIMIT:
        y_half, _ = integrate(dt / 2, 2 * steps, False)
        error_estimate = {sid: abs(a - b) * 16 / 15 for sid, a, b in zip(ids, y, y_half)}
        scale = max([abs(v) for v in initial] + [abs(v) for v in y] + [1e-300])
        coarse = [sid for sid, v in zip(ids, y)
                  if error_estimate[sid] > DISPLAY_RELATIVE_PRECISION * max(abs(v), 1e-9 * scale)]
        if coarse:
            worst = max(error_estimate[sid] / max(abs(v), 1e-9 * scale) for sid, v in zip(ids, y) if sid in coarse)
            warnings.append({"code": "coarse_time_step", "params": {"species": ", ".join(coarse), "relative_error": worst},
                             "message": f"Estimated RK4 error exceeds 6 significant digits for {', '.join(coarse)} "
                                        f"(up to {worst:.1e} relative): reduce dt."})
    else:
        warnings.append({"code": "error_not_estimated", "params": {},
                         "message": "Run too large for the step-doubling error estimate."})

    _, final_rates = rate_vector(y)
    initial_total = sum(initial)
    final_total = sum(y)
    return {
        "model_id": "mass_action_reaction_network",
        "validation_level": "L1",
        "method": "fixed_step_RK4",
        "temperature_k": temp,
        "species_ids": ids,
        "reaction_ids": [r["id"] for r in parsed],
        "rows": rows,
        "summary": {
            "duration": duration, "dt": dt, "integration_steps": steps,
            "initial_concentrations": dict(zip(ids, initial)),
            "final_concentrations": dict(zip(ids, y)),
            "final_rates": dict(zip([r["id"] for r in parsed], final_rates)),
            "nonnegative_concentrations": all(v >= 0 for v in y),
            "atom_balance_by_reaction": atom_balance_checks or None,
            "total_concentration_initial": initial_total,
            "total_concentration_final": final_total,
            "estimated_final_error": error_estimate,
            "error_estimate_method": "step doubling (dt vs dt/2), Richardson factor 16/15 for RK4" if error_estimate is not None else None
        },
        "warnings": warnings,
        "assumptions": [
            "Well-mixed, constant-volume system; concentrations use user-defined consistent units.",
            "Elementary mass-action rate law: rate = k × product(reactant concentration ** stoichiometric coefficient).",
            "Temperature is constant during a run; Arrhenius temperature scaling is used only when activation energy is supplied.",
            "No equilibrium, reverse reactions unless explicitly provided, transport, phase changes, or heat feedback."
        ],
        "limitations": [
            "User-supplied rate constants and activation energies require independent sourcing/calibration for real predictions.",
            "A mathematically integrated result is not by itself empirical scientific validation.",
            "This is a bounded educational reaction-network solver, not a universal chemistry engine."
        ]
    }
