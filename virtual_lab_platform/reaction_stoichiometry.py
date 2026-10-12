"""Verified stoichiometric batch-reaction calculator.

Calculates a theoretical limiting-reactant extent from user-supplied amounts.
It is not a kinetic, equilibrium, yield, or process-safety model.
"""
from __future__ import annotations

import math
import re
from typing import Any


class StoichiometryError(ValueError):
    """Invalid or chemically inconsistent stoichiometric request."""


_TOKEN = re.compile(r"([A-Z][a-z]?|\(|\)|\d+)")


def parse_formula(formula: str) -> dict[str, int]:
    """Parse simple chemical formulae, including nested groups and integer subscripts."""
    if not isinstance(formula, str) or not formula.strip():
        raise StoichiometryError("A non-empty molecular formula is required.")
    tokens = _TOKEN.findall(formula)
    if "".join(tokens) != formula:
        raise StoichiometryError(f"Unsupported molecular formula syntax: {formula!r}.")
    pos = 0

    def parse_group(nested: bool = False) -> dict[str, int]:
        nonlocal pos
        counts: dict[str, int] = {}
        while pos < len(tokens):
            token = tokens[pos]
            if token == ")":
                if not nested:
                    raise StoichiometryError(f"Unexpected ')' in formula {formula!r}.")
                pos += 1
                return counts
            if token == "(":
                pos += 1
                group = parse_group(True)
                multiplier = 1
                if pos < len(tokens) and tokens[pos].isdigit():
                    multiplier = int(tokens[pos])
                    pos += 1
                if multiplier < 1:
                    raise StoichiometryError("Formula subscripts must be positive integers.")
                for element, amount in group.items():
                    counts[element] = counts.get(element, 0) + amount * multiplier
                continue
            if not re.fullmatch(r"[A-Z][a-z]?", token):
                raise StoichiometryError(f"Expected an element symbol in formula {formula!r}.")
            element = token
            pos += 1
            multiplier = 1
            if pos < len(tokens) and tokens[pos].isdigit():
                multiplier = int(tokens[pos])
                pos += 1
            if multiplier < 1:
                raise StoichiometryError("Formula subscripts must be positive integers.")
            counts[element] = counts.get(element, 0) + multiplier
        if nested:
            raise StoichiometryError(f"Unclosed '(' in formula {formula!r}.")
        return counts

    parsed = parse_group()
    if not parsed:
        raise StoichiometryError(f"Could not parse formula {formula!r}.")
    return parsed


def calculate_stoichiometry(request: dict[str, Any]) -> dict[str, Any]:
    """Calculate theoretical reaction extent, limiting reactant and material balance.

    Request:
      {
        "reaction_id": "neutralization",
        "reactants": {"HCl": 1, "NaOH": 1},
        "products": {"NaCl": 1, "H2O": 1},
        "species": [
          {"id":"HCl", "amount_mol":0.1, "formula":"HCl"}, ...
        ]
      }
    """
    if not isinstance(request, dict):
        raise StoichiometryError("Request must be a JSON object.")
    reactants, products = request.get("reactants"), request.get("products")
    if not isinstance(reactants, dict) or not reactants:
        raise StoichiometryError("reactants must be a non-empty object.")
    if not isinstance(products, dict) or not products:
        raise StoichiometryError("products must be a non-empty object.")
    if set(reactants) & set(products):
        raise StoichiometryError("A species cannot be both a reactant and product in this one-way batch model.")

    def coefficients(side: dict[str, Any], side_name: str) -> dict[str, int]:
        parsed = {}
        for sid, value in side.items():
            if not isinstance(sid, str) or not sid.strip():
                raise StoichiometryError(f"{side_name} species IDs must be non-empty strings.")
            if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 100:
                raise StoichiometryError(f"{side_name} coefficients must be integers between 1 and 100.")
            parsed[sid] = value
        return parsed

    reactants = coefficients(reactants, "Reactant")
    products = coefficients(products, "Product")
    species_input = request.get("species")
    if not isinstance(species_input, list):
        raise StoichiometryError("species must be a list of amount records.")
    species: dict[str, dict[str, Any]] = {}
    for entry in species_input:
        if not isinstance(entry, dict):
            raise StoichiometryError("Each species record must be an object.")
        sid = entry.get("id")
        if not isinstance(sid, str) or not sid.strip() or sid in species:
            raise StoichiometryError("Species IDs must be non-empty and unique.")
        amount = entry.get("amount_mol")
        if isinstance(amount, bool) or not isinstance(amount, (int, float)) or not math.isfinite(amount) or amount < 0:
            raise StoichiometryError(f"{sid}: amount_mol must be finite and non-negative.")
        formula = entry.get("formula")
        species[sid] = {"amount_mol": float(amount), "formula": formula}
    required = set(reactants) | set(products)
    missing = sorted(required - set(species))
    if missing:
        raise StoichiometryError("Missing species amount records: " + ", ".join(missing))
    for sid in reactants:
        if species[sid]["amount_mol"] < 0:
            raise StoichiometryError(f"{sid}: amount cannot be negative.")

    extents = {sid: species[sid]["amount_mol"] / coeff for sid, coeff in reactants.items()}
    extent = min(extents.values())
    tol = max(1e-12, abs(extent) * 1e-10)
    limiting = sorted(sid for sid, candidate in extents.items() if abs(candidate - extent) <= tol)
    remaining = {
        sid: max(0.0, species[sid]["amount_mol"] - coeff * extent)
        for sid, coeff in reactants.items()
    }
    produced = {sid: coeff * extent for sid, coeff in products.items()}

    formula_available = all(
        isinstance(species[sid].get("formula"), str) and species[sid]["formula"].strip()
        for sid in required
    )
    atom_balance: dict[str, int] | None = None
    if formula_available:
        atom_balance = {}
        for sid, coeff in reactants.items():
            for element, count in parse_formula(species[sid]["formula"]).items():
                atom_balance[element] = atom_balance.get(element, 0) - coeff * count
        for sid, coeff in products.items():
            for element, count in parse_formula(species[sid]["formula"]).items():
                atom_balance[element] = atom_balance.get(element, 0) + coeff * count
        atom_balance = {element: count for element, count in atom_balance.items() if count}
        if atom_balance:
            detail = ", ".join(f"{el}: {delta:+d}" for el, delta in sorted(atom_balance.items()))
            raise StoichiometryError("The supplied equation is not atom-balanced (" + detail + "). Check formulas and coefficients.")

    return {
        "model_id": "theoretical_stoichiometric_batch_balance",
        "validation_level": "L1" if formula_available else "L0",
        "status": "computed",
        "reaction_id": str(request.get("reaction_id", "custom_reaction")),
        "reaction_name": str(request.get("reaction_name", "")),
        "reaction_extent_mol": extent,
        "limiting_reactants": limiting,
        "reactant_amounts_initial_mol": {sid: species[sid]["amount_mol"] for sid in reactants},
        "reactant_amounts_remaining_mol": remaining,
        "product_amounts_theoretical_mol": produced,
        "atom_balance": {
            "status": "balanced" if formula_available else "not_checked_missing_formula",
            "element_deltas": atom_balance,
        },
        "checks": {
            "nonnegative_amounts": all(v >= 0 for v in remaining.values()) and all(v >= 0 for v in produced.values()),
            "limiting_reactant_exhausted": all(remaining[sid] <= tol for sid in limiting),
            "equation_atom_balanced": True if formula_available else None,
        },
        "assumptions": [
            "One irreversible stoichiometric batch step; coefficients are user supplied.",
            "Theoretical complete conversion of the limiting reactant; no side reactions or yield losses.",
            "Amounts are in mol; no rate, equilibrium, temperature, pressure, solvent, or phase model is included.",
            "Molecular formula checking verifies atom balance only, not reaction plausibility or chemical safety.",
        ],
        "limitations": [
            "This is a material-balance calculation, not a kinetic or equilibrium prediction.",
            "A balanced equation is necessary but does not establish that a reaction proceeds under any particular conditions.",
        ],
    }
