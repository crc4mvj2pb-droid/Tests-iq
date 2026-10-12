"""Scientific domains (v7.0): limited scope, common interfaces, benchmark and explicit validation status.

A domain groups model contracts (units and parameters come from the contracts), catalogue datasets,
benchmark cases (benchmarks/independent_suite.py) and plot specifications. Rules checked by tests:
  - every model contract belongs to exactly one domain;
  - every domain states what it covers and what it excludes;
  - every domain has at least one independent benchmark case;
  - its validation status is derived from the maturity of its models, never typed by hand;
  - every plot specification names fields that exist in the model's result.
"""
from __future__ import annotations

from typing import Any

import maturity
import model_registry

DOMAINS: list[dict[str, Any]] = [
    {"id": "electrical_circuits", "title": "Circuits électriques linéaires",
     "scope": "Réseaux résistifs en courant continu ; régimes transitoires du premier ordre (RC, RL) ; RLC série (échelon, sinusoïdal, balayage).",
     "excluded": "Composants non linéaires (diodes, transistors), lignes à constantes réparties, simulation SPICE.",
     "models": ["dc_resistive_network", "workbench_dc_circuit", "rc_rl_step_response", "series_rlc_ac", "series_rlc_frequency_sweep",
                "series_rlc_step_response", "workbench_rc_rl_transient"],
     "datasets": [], "plots": [{"model": "rc_rl_step_response", "rows": "points", "x": "time_s", "y": ["capacitor_voltage_v"]},
                                {"model": "series_rlc_step_response", "rows": "points", "x": "time_s", "y": ["capacitor_voltage_v", "current_a"]}]},
    {"id": "chemical_kinetics", "title": "Cinétique et stœchiométrie chimiques",
     "scope": "Lois d'action de masse en système fermé et isotherme ; dépendance d'Arrhenius ; bilans stœchiométriques.",
     "excluded": "Transport, mélange non idéal, thermodynamique d'équilibre complète, cinétique hétérogène.",
     "models": ["mass_action_kinetics", "stoichiometry", "arrhenius_reaction", "first_order_reaction"],
     "datasets": [], "plots": [{"model": "arrhenius_reaction", "rows": "rows", "x": "time_s", "y": ["A", "B"]}]},
    {"id": "physical_chemistry", "title": "Physicochimie des solutions",
     "scope": "Équilibres acide–base en solution aqueuse diluée à 25 °C par bilan de charges exact ; courbes de titrage par une base forte.",
     "excluded": "Coefficients d'activité, précipitation, complexation, échanges gazeux (CO2), autres températures.",
     "models": ["aqueous_acid_base", "aqueous_titration"], "datasets": ["pka_aqueous_25c"],
     "plots": [{"model": "aqueous_titration", "rows": "rows", "x": "titrant_ml", "y": ["ph"]}]},
    {"id": "thermal_transfer", "title": "Thermique et transferts",
     "scope": "Diffusion thermique 1D dans un milieu homogène ; corps à une capacité thermique (Bi < 0,1) ; conduction stationnaire dans un mur composite.",
     "excluded": "Convection détaillée, rayonnement, changement de phase, géométries 2D/3D.",
     "models": ["heat_diffusion_1d", "lumped_thermal_transient", "plane_wall_conduction"], "datasets": [],
     "plots": [{"model": "lumped_thermal_transient", "rows": "rows", "x": "time_s", "y": ["temperature_k"]}]},
    {"id": "quantitative_biology", "title": "Biologie quantitative",
     "scope": "Cinétique enzymatique de Michaelis–Menten ; croissance logistique ; dynamique proie–prédateur de Lotka–Volterra.",
     "excluded": "Réseaux de régulation, stochasticité, structure spatiale ou d'âge.",
     "models": ["enzyme_kinetics", "logistic_growth", "lotka_volterra"], "datasets": ["puromycin_treloar_1974"],
     "plots": [{"model": "logistic_growth", "rows": "rows", "x": "time", "y": ["population"]}, {"model": "lotka_volterra", "rows": "rows", "x": "time", "y": ["prey", "predators"]}]},
    {"id": "computational_neuroscience", "title": "Neurosciences computationnelles",
     "scope": "Modèles mathématiques classiques et délimités de neurone unique : intègre-et-tire, Hodgkin–Huxley (axone géant de calmar, 1952), FitzHugh–Nagumo.",
     "excluded": "Réseaux de neurones biologiques, morphologie, plasticité ; aucun « jumeau » du cerveau humain.",
     "models": ["leaky_integrate_fire", "hodgkin_huxley", "fitzhugh_nagumo"], "datasets": [],
     "plots": [{"model": "leaky_integrate_fire", "rows": "rows", "x": "time_ms", "y": ["membrane_voltage_mv"]},
               {"model": "hodgkin_huxley", "rows": "rows", "x": "time_ms", "y": ["membrane_voltage_mv"]}, {"model": "fitzhugh_nagumo", "rows": "rows", "x": "time", "y": ["v", "w"]}]},
    {"id": "exploratory_biomedical", "title": "Modèles biomédicaux exploratoires",
     "scope": "Modèles pédagogiques : épidémie SIR homogène, pharmacocinétique à un compartiment.",
     "excluded": "Toute prédiction clinique, choix de dose, décision de santé publique ou conseil médical.",
     "models": ["sir_epidemic", "one_compartment_pk"], "datasets": [],
     "plots": [{"model": "sir_epidemic", "rows": "rows", "x": "x", "y": ["susceptible", "infectious", "recovered"]}],
     "disclaimer": "Résultats exploratoires : ni conseil médical, ni prédiction clinique validée."},
    {"id": "environmental_processes", "title": "Processus environnementaux",
     "scope": "Élimination du premier ordre dans un compartiment bien mélangé.",
     "excluded": "Transport, sources, adsorption, plusieurs compartiments, paramètres de site.",
     "models": ["environmental_decay"], "datasets": ["bod_marske_1967"], "plots": []},
]


def _benchmark_cases(models: list[str]) -> list[dict[str, str]]:
    from benchmarks.independent_suite import CASES
    return [{"id": c["id"], "model": c["model"], "expectation": c["expectation"]} for c in CASES if c["model"] in models]


def validation_status(models: list[str]) -> dict[str, Any]:
    """Derived from the models' maturity: the domain is as mature as its least mature model."""
    levels = {m: maturity.maturity_of(m) for m in models}
    ranks = {l["id"]: l["rank"] for l in maturity.LEVELS}
    lowest = min(levels.values(), key=lambda e: ranks[e["level"]])["level"]
    highest = max(levels.values(), key=lambda e: ranks[e["level"]])["level"]
    counts = {l["id"]: sum(e["level"] == l["id"] for e in levels.values()) for l in maturity.LEVELS}
    label = next(l["label_fr"] for l in maturity.LEVELS if l["id"] == lowest)
    return {"lowest_level": lowest, "highest_level": highest, "counts": counts, "label_fr": label,
            "statement": f"Niveau du domaine : {label} (le plus bas de ses {len(models)} modèle(s)) ; validés sur données : {counts['validated_on_data']}."}


def describe(domain: dict[str, Any]) -> dict[str, Any]:
    contracts = {c["id"]: c for c in model_registry.list_contracts()}
    models = [{"id": m, "title": contracts[m]["title"], "maturity": maturity.maturity_of(m)["level"],
               "units": sorted({p.get("unit") for p in contracts[m]["parameters"] if p.get("unit")} | {o["unit"] for o in contracts[m]["outputs"]})}
              for m in domain["models"]]
    return {**domain, "models": models, "benchmark_cases": _benchmark_cases(domain["models"]), "validation_status": validation_status(domain["models"])}


def all_domains() -> list[dict[str, Any]]:
    return [describe(d) for d in DOMAINS]


def problems() -> list[str]:
    import data_catalog
    out = []
    contract_ids = {c["id"] for c in model_registry.list_contracts()}
    owner: dict[str, list[str]] = {}
    for d in DOMAINS:
        for key in ("id", "title", "scope", "excluded", "models"):
            if not d.get(key):
                out.append(f"domain {d.get('id')}: missing {key}")
        for m in d["models"]:
            owner.setdefault(m, []).append(d["id"])
            if m not in contract_ids:
                out.append(f"domain {d['id']}: unknown model {m}")
        if not _benchmark_cases(d["models"]):
            out.append(f"domain {d['id']}: no independent benchmark case")
        for ds in d.get("datasets", []):
            try:
                data_catalog.get_entry(ds)
            except data_catalog.CatalogError:
                out.append(f"domain {d['id']}: unknown dataset {ds}")
    out += [f"model {m}: in no domain" for m in sorted(contract_ids - set(owner))]
    out += [f"model {m}: in several domains {ds}" for m, ds in owner.items() if len(ds) > 1]
    return out


def plot_problems() -> list[str]:
    """Each plot specification must name fields present in the model's example result."""
    out = []
    for d in DOMAINS:
        for spec in d.get("plots", []):
            example = model_registry.REGISTRY[spec["model"]]["example"] or {}
            result = model_registry.run_model(spec["model"], example)["result"]
            rows = result.get(spec["rows"])
            if not isinstance(rows, list) or not rows:
                out.append(f"plot {spec['model']}: no rows '{spec['rows']}'")
                continue
            missing = [k for k in [spec["x"], *spec["y"]] if k not in rows[0]]
            if missing:
                out.append(f"plot {spec['model']}: missing fields {missing}")
    return out
