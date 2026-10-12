from __future__ import annotations
import math
from constants import GAS_CONSTANT
from typing import Any

MODEL_CATALOG = [
    {
        "id": "enzyme_kinetics",
        "name": "Enzyme kinetics — Michaelis–Menten",
        "domain": "biology",
        "status": "implemented_demo",
        "description": "Rate versus substrate concentration for a simple enzyme model.",
        "validation_level": "L1",
        "caveat": "Mathematical demo; not validated against experimental data."
    },
    {
        "id": "sir_epidemic",
        "name": "SIR epidemic dynamics",
        "domain": "medicine",
        "status": "implemented_demo",
        "description": "Simple susceptible–infectious–recovered compartment model.",
        "validation_level": "L1",
        "caveat": "Illustrative ODE model; not for public-health decisions or individual predictions."
    },
    {
        "id": "heat_diffusion_1d",
        "name": "1D heat diffusion",
        "domain": "physics",
        "status": "implemented_demo",
        "description": "Transient heat diffusion through a 1D bar with fixed end temperatures.",
        "validation_level": "L1",
        "caveat": "Simplified 1D homogeneous material model; not a substitute for validated engineering analysis."
    },
    {
        "id": "cosmetic_formulation",
        "name": "Cosmetic formulation screening",
        "domain": "cosmetics",
        "status": "workflow_template",
        "description": "Workflow specification only; no ingredient database or validated formulation solver connected.",
        "validation_level": "L0",
        "caveat": "No formulation, safety, stability, efficacy or regulatory result is calculated."
    },
    {
        "id": "disease_research",
        "name": "Disease mechanism research",
        "domain": "medicine",
        "status": "workflow_template",
        "description": "Workflow specification only; no disease-specific mechanistic model connected.",
        "validation_level": "L0",
        "caveat": "No disease or treatment prediction is calculated."
    },
    {
        "id": "environmental_system",
        "name": "Environmental system model",
        "domain": "environment",
        "status": "workflow_template",
        "description": "Workflow specification only; domain solver and reference benchmark not connected.",
        "validation_level": "L0",
        "caveat": "No environmental impact result is calculated."
    },
    {"id":"logistic_growth","name":"Logistic population growth","domain":"biology","status":"implemented_demo","description":"Analytical logistic growth curve with carrying capacity.","validation_level":"L1","caveat":"Idealized single-population model; parameters must be fitted and validated for real organisms."},
    {"id":"first_order_reaction","name":"First-order reaction A → B","domain":"chemistry","status":"implemented_demo","description":"Analytical irreversible first-order conversion with mass balance.","validation_level":"L1","caveat":"Idealized single reaction with constant rate coefficient; not a general chemistry solver."},
    {"id":"environmental_decay","name":"First-order environmental decay","domain":"environment","status":"implemented_demo","description":"Analytical decay/removal of a scalar load in a well-mixed compartment.","validation_level":"L1","caveat":"No transport, sources, partitioning or site-specific calibration."},
    {"id":"one_compartment_pk","name":"One-compartment concentration decay (PK teaching model)","domain":"medicine","status":"implemented_demo","description":"Analytical concentration-time curve after a single instantaneous input.","validation_level":"L1","caveat":"Teaching equation only; not dose advice, a patient model or clinical prediction."},
    {"id":"lotka_volterra","name":"Predator–prey dynamics (Lotka–Volterra)","domain":"environment","status":"implemented_demo","description":"Numerical two-population predator–prey system integrated with RK4.","validation_level":"L1","caveat":"Idealized deterministic model; no carrying capacity, seasonality, stochasticity or field calibration."},
    {"id":"leaky_integrate_fire","name":"Leaky integrate-and-fire neuron (teaching model)","domain":"neuroscience","status":"implemented_demo","description":"Exact subthreshold membrane-potential updates with threshold/reset spike events.","validation_level":"L1","caveat":"Highly simplified neuron model; no ion channels, morphology, synapses or biological calibration."},
    {"id":"arrhenius_reaction","name":"Temperature-dependent first-order reaction (Arrhenius)","domain":"chemistry","status":"implemented_demo","description":"Couples temperature to a first-order rate constant using the Arrhenius equation.","validation_level":"L1","caveat":"Single reaction at constant temperature; illustrative parameters and no thermal feedback or empirical validation."},
]


# Additional discoverable model/workflow templates. These entries are intentionally
# L0: they document research directions but do not claim a solver exists.
_EXTRA_MODEL_TEMPLATES = [
("acid_base_equilibrium","Acid–base equilibrium","chemistry","Equilibrium speciation from pKa, activities and charge balance; this conceptual entry is not connected — the computing model is aqueous_acid_base (v7.2, without activity corrections)."),
("redox_electrochemistry","Redox and electrochemistry","chemistry","Electrode potentials and coupled redox equilibria; thermodynamic database and solver not connected."),
("chemical_equilibrium","General chemical equilibrium","chemistry","Equilibrium constants, activities and mass/charge balance; general equilibrium solver not connected."),
("reaction_diffusion","Reaction–diffusion system","physics","Coupled spatial transport and reaction kinetics; PDE solver not connected."),
("fluid_cfd","Computational fluid dynamics","fluid_mechanics","Navier–Stokes-based flow solver and validated boundary-condition library not connected."),
("finite_element_mechanics","Finite-element solid mechanics","engineering","Mesh-based elasticity/plasticity solver not connected."),
("beam_bending","Beam bending and deflection","engineering","Boundary-condition-aware structural solver not connected."),
("vibration_modes","Mechanical vibration modes","physics","Eigenfrequency and damping solver not connected."),
("wave_propagation","Wave propagation","physics","Acoustic/electromagnetic wave solver not connected."),
("quantum_chemistry","Quantum chemistry","chemistry","Electronic-structure calculations require a quantum chemistry engine not connected."),
("molecular_dynamics","Molecular dynamics","chemistry","Force fields, integrator and validated molecular parameter sets not connected."),
("protein_folding","Protein structure and folding","biology","Structure prediction engine and validated sequence/structure pipeline not connected."),
("gene_regulation","Gene regulatory network","genetics","Regulatory network model and curated parameters not connected."),
("population_genetics","Population genetics","genetics","Allele-frequency and demographic model suite not connected."),
("pharmacokinetics_pbpk","Physiologically based pharmacokinetics","medicine","Organ compartments, compound properties and validated PBPK solver not connected; not for dose decisions."),
("cardiac_electrophysiology","Cardiac electrophysiology","medicine","Validated ionic and tissue propagation models not connected; not for clinical decisions."),
("neural_network_dynamics","Neural network dynamics","neuroscience","Coupled neuron and synapse network simulator not connected."),
("ecosystem_food_web","Ecosystem food web","environment","Multi-species ecosystem model and field calibration not connected."),
("carbon_cycle","Carbon cycle and climate feedbacks","environment","Coupled carbon reservoirs and climate model not connected."),
("groundwater_transport","Groundwater transport","geoscience","Porous-media flow, dispersion and geochemical transport solver not connected."),
("weather_forecast","Numerical weather modelling","environment","Atmospheric dynamics, data assimilation and forecast validation not connected."),
("planetary_orbits","N-body orbital dynamics","astronomy","Gravitational N-body integration and ephemeris validation not connected."),
("stellar_evolution","Stellar evolution","astronomy","Stellar structure/evolution solver and opacity tables not connected."),
("solar_cell_physics","Photovoltaic device physics","energy","Semiconductor device and optical absorption solver not connected."),
("battery_degradation","Battery degradation and aging","energy","Electrochemical degradation model and cell-specific parameterization not connected."),
("combustion_kinetics","Combustion kinetics","engineering","Detailed chemical mechanism and stiff ODE solver not connected."),
("polymer_rheology","Polymer rheology","materials","Constitutive and molecular-weight-dependent rheology solver not connected."),
("crystal_growth","Crystal growth","materials","Nucleation, phase-field and transport solver not connected."),
("soil_crop_model","Soil–crop system","agriculture","Crop-specific growth, soil-water and nutrient coupling not connected."),
("food_shelf_life","Food stability and shelf-life","food_science","Validated spoilage kinetics, packaging and microbial data not connected."),
]
for _id, _name, _domain, _description in _EXTRA_MODEL_TEMPLATES:
    MODEL_CATALOG.append({
        "id": _id, "name": _name, "domain": _domain,
        "status": "workflow_template", "description": _description,
        "validation_level": "L0",
        "caveat": "Catalogue entry only: no domain solver is connected, so no scientific result is calculated."
    })

def _finite_positive(value: Any, name: str, allow_zero: bool = False) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ValueError(f"{name} must be a finite number.")
    if value < 0 or (value == 0 and not allow_zero):
        qualifier = "non-negative" if allow_zero else "greater than zero"
        raise ValueError(f"{name} must be {qualifier}.")
    return float(value)

def run_enzyme(params: dict[str, Any]) -> dict[str, Any]:
    vmax = _finite_positive(params.get("vmax"), "vmax")
    km = _finite_positive(params.get("km"), "km")
    s_max = _finite_positive(params.get("s_max"), "s_max")
    points = params.get("points", 21)
    if not isinstance(points, int) or isinstance(points, bool) or not 3 <= points <= 501:
        raise ValueError("points must be an integer between 3 and 501.")
    rows = []
    for i in range(points):
        s = s_max * i / (points - 1)
        rate = vmax * s / (km + s)
        rows.append({"x": s, "y": rate})
    checks = {
        "all_rates_nonnegative": all(r["y"] >= 0 for r in rows),
        "rates_bounded_by_vmax": all(r["y"] <= vmax + 1e-12 for r in rows),
        "rate_monotonic_with_substrate": all(rows[i]["y"] <= rows[i+1]["y"] + 1e-12 for i in range(len(rows)-1))
    }
    return {
        "model_id": "enzyme_kinetics", "validation_level": "L1",
        "columns": {"x": "substrate concentration (arbitrary units)", "y": "reaction rate (arbitrary units)"},
        "rows": rows, "checks": checks,
        "summary": {"points": len(rows), "max_rate_calculated": rows[-1]["y"], "vmax_parameter": vmax},
        "limitations": ["Illustrative parameters unless supported by a source.", "No fitting to experimental data.", "Basic mathematical checks are not biological validation."]
    }

def run_sir(params: dict[str, Any]) -> dict[str, Any]:
    population = _finite_positive(params.get("population", 10000), "population")
    beta = _finite_positive(params.get("beta", 0.3), "beta", allow_zero=True)
    gamma = _finite_positive(params.get("gamma", 0.1), "gamma", allow_zero=True)
    initial_infected = _finite_positive(params.get("initial_infected", 10), "initial_infected")
    days = _finite_positive(params.get("days", 160), "days")
    dt = _finite_positive(params.get("dt", 0.1), "dt")
    if days > 1000 or dt > 1 or dt < 0.001:
        raise ValueError("days must be <=1000 and dt must be between 0.001 and 1.")
    if initial_infected >= population:
        raise ValueError("initial_infected must be smaller than population.")
    if abs(days / dt - round(days / dt)) > 1e-8:
        raise ValueError("days must be divisible by dt (e.g. days=160, dt=0.1).")
    steps = int(round(days / dt))
    if steps > 200000:
        raise ValueError("Too many time steps.")
    S, I, R = population - initial_infected, initial_infected, 0.0
    rows = [{"x": 0.0, "susceptible": S, "infectious": I, "recovered": R}]
    for n in range(steps):
        dS = -beta * S * I / population
        dI = beta * S * I / population - gamma * I
        dR = gamma * I
        S2, I2, R2 = S + dt*dS, I + dt*dI, R + dt*dR
        if min(S2, I2, R2) < -1e-7:
            raise ValueError("Numerical instability produced negative compartments; reduce dt or review parameters.")
        S, I, R = max(0.0, S2), max(0.0, I2), max(0.0, R2)
        if n % max(1, int(1/dt)) == 0 or n == steps-1:
            rows.append({"x": round((n+1)*dt, 5), "susceptible": S, "infectious": I, "recovered": R})
    checks = {
        "compartments_nonnegative": all(min(r["susceptible"], r["infectious"], r["recovered"]) >= 0 for r in rows),
        "population_approximately_conserved": all(abs(r["susceptible"] + r["infectious"] + r["recovered"] - population) < population*0.002 for r in rows)
    }
    peak = max(rows, key=lambda r: r["infectious"])
    return {
        "model_id": "sir_epidemic", "validation_level": "L1",
        "columns": {"x": "time (days)", "susceptible": "susceptible people (model units)", "infectious": "infectious people (model units)", "recovered": "recovered people (model units)"},
        "rows": rows, "checks": checks,
        "summary": {"population": population, "peak_infectious": peak["infectious"], "peak_time_days": peak["x"], "final_recovered": rows[-1]["recovered"]},
        "limitations": ["Illustrative compartment model, not fitted to data.", "Assumes homogeneous mixing and fixed beta/gamma.", "Not for public-health policy, diagnosis, treatment, or individual prediction."]
    }

def run_heat(params: dict[str, Any]) -> dict[str, Any]:
    length = _finite_positive(params.get("length_m", 1.0), "length_m")
    diffusivity = _finite_positive(params.get("diffusivity_m2_s", 1e-5), "diffusivity_m2_s")
    left_temp = params.get("left_temp_c", 100.0)
    right_temp = params.get("right_temp_c", 20.0)
    initial_temp = params.get("initial_temp_c", 20.0)
    for name, val in [("left_temp_c", left_temp), ("right_temp_c", right_temp), ("initial_temp_c", initial_temp)]:
        if not isinstance(val, (int, float)) or isinstance(val, bool) or not math.isfinite(val):
            raise ValueError(f"{name} must be a finite number.")
    nodes = params.get("nodes", 21)
    dt = _finite_positive(params.get("dt_s", 1.0), "dt_s")
    total_time = _finite_positive(params.get("total_time_s", 1000.0), "total_time_s")
    if not isinstance(nodes, int) or isinstance(nodes, bool) or not 5 <= nodes <= 201:
        raise ValueError("nodes must be an integer between 5 and 201.")
    dx = length / (nodes - 1)
    r = diffusivity * dt / (dx * dx)
    if r > 0.5:
        raise ValueError(f"Explicit heat solver unstable: alpha*dt/dx^2 = {r:.4g} > 0.5. Reduce dt_s or increase nodes spacing.")
    if total_time / dt > 200000:
        raise ValueError("Too many time steps.")
    steps = int(total_time / dt)
    temps = [float(initial_temp)] * nodes
    temps[0], temps[-1] = float(left_temp), float(right_temp)
    rows = [{"x": 0.0, **{f"T{i}": t for i,t in enumerate(temps)}}]
    for step in range(steps):
        old = temps[:]
        for i in range(1, nodes-1):
            temps[i] = old[i] + r * (old[i-1] - 2*old[i] + old[i+1])
        temps[0], temps[-1] = float(left_temp), float(right_temp)
        if (step+1) % max(1, int(steps/100)) == 0 or step == steps-1:
            row = {"x": round((step+1)*dt, 6)}
            row.update({f"T{i}": v for i,v in enumerate(temps)})
            rows.append(row)
    checks = {
        "stability_condition_satisfied": r <= 0.5,
        "temperatures_finite": all(math.isfinite(v) for row in rows for k,v in row.items() if k != "x"),
        "temperature_within_initial_boundary_extrema": all(min(float(initial_temp), float(left_temp), float(right_temp))-1e-8 <= v <= max(float(initial_temp), float(left_temp), float(right_temp))+1e-8 for row in rows for k,v in row.items() if k != "x")
    }
    return {
        "model_id": "heat_diffusion_1d", "validation_level": "L1",
        "columns": {"x": "time (seconds)", "T0..Tn": "temperature at equally spaced nodes (°C)"},
        "rows": rows, "checks": checks,
        "summary": {"nodes": nodes, "time_steps": steps, "fourier_number": r, "final_midpoint_temp_c": temps[nodes//2]},
        "limitations": ["Simplified 1D homogeneous material with constant diffusivity.", "No convection, radiation, phase change or material heterogeneity.", "Not validated for engineering design."]
    }


def run_logistic_growth(params: dict[str, Any]) -> dict[str, Any]:
    n0=_finite_positive(params.get("initial_population",10),"initial_population")
    cap=_finite_positive(params.get("carrying_capacity",1000),"carrying_capacity")
    rate=_finite_positive(params.get("growth_rate",0.2),"growth_rate",allow_zero=True)
    duration=_finite_positive(params.get("duration",30),"duration")
    points=params.get("points",61)
    if cap<n0: raise ValueError("carrying_capacity must be at least initial_population.")
    if duration>10000 or not isinstance(points,int) or isinstance(points,bool) or not 3<=points<=1001: raise ValueError("duration must be <=10000 and points an integer from 3 to 1001.")
    rows=[]
    for i in range(points):
        t=duration*i/(points-1)
        n=n0 if rate==0 or n0==cap else cap/(1+((cap-n0)/n0)*math.exp(-rate*t))
        rows.append({"time":t,"population":n})
    checks={"population_nonnegative":all(r["population"]>=0 for r in rows),"population_not_above_capacity":all(r["population"]<=cap+1e-9 for r in rows),"population_monotonic":all(rows[i]["population"]<=rows[i+1]["population"]+1e-9 for i in range(len(rows)-1))}
    return {"model_id":"logistic_growth","validation_level":"L1","columns":{"time":"time (model units)","population":"population (model units)"},"rows":rows,"checks":checks,"summary":{"initial_population":n0,"final_population":rows[-1]["population"],"carrying_capacity":cap,"growth_rate":rate},"limitations":["Analytical logistic equation with constant growth rate and carrying capacity.","No stochasticity, age structure, resource dynamics or fitted data.","Mathematical checks are not biological validation."]}


def run_first_order_reaction(params: dict[str, Any]) -> dict[str, Any]:
    a0=_finite_positive(params.get("initial_A",1.0),"initial_A",allow_zero=True); k=_finite_positive(params.get("rate_constant",0.2),"rate_constant",allow_zero=True)
    duration=_finite_positive(params.get("duration",10),"duration"); points=params.get("points",51)
    if duration>100000 or not isinstance(points,int) or isinstance(points,bool) or not 3<=points<=1001: raise ValueError("duration must be <=100000 and points an integer from 3 to 1001.")
    rows=[]
    for i in range(points):
        t=duration*i/(points-1); a=a0*math.exp(-k*t); rows.append({"time":t,"A":a,"B":a0-a,"total_A_plus_B":a0})
    checks={"concentrations_nonnegative":all(r["A"]>=-1e-12 and r["B"]>=-1e-12 for r in rows),"mass_balance_preserved":all(abs(r["A"]+r["B"]-a0)<1e-9*max(1,a0) for r in rows),"A_nonincreasing":all(rows[i]["A"]>=rows[i+1]["A"]-1e-12 for i in range(len(rows)-1))}
    return {"model_id":"first_order_reaction","validation_level":"L1","columns":{"time":"time (model units)","A":"reactant A (initial amount units)","B":"product B (initial amount units)","total_A_plus_B":"total amount (initial amount units)"},"rows":rows,"checks":checks,"summary":{"initial_A":a0,"final_A":rows[-1]["A"],"final_B":rows[-1]["B"],"rate_constant":k,"half_life":math.log(2)/k if k else None},"limitations":["Single irreversible A→B reaction with first-order kinetics.","Constant volume and rate coefficient; no side reactions or thermal coupling.","Analytical behaviour does not validate a specific real reaction."]}


def run_environmental_decay(params: dict[str, Any]) -> dict[str, Any]:
    c0=_finite_positive(params.get("initial_load",100.0),"initial_load",allow_zero=True); k=_finite_positive(params.get("removal_rate",0.05),"removal_rate",allow_zero=True); duration=_finite_positive(params.get("duration",100),"duration"); points=params.get("points",51)
    if duration>1e7 or not isinstance(points,int) or isinstance(points,bool) or not 3<=points<=1001: raise ValueError("duration must be <=1e7 and points an integer from 3 to 1001.")
    rows=[{"time":duration*i/(points-1),"remaining_load":c0*math.exp(-k*duration*i/(points-1)),"removed_or_decayed":c0*(1-math.exp(-k*duration*i/(points-1)))} for i in range(points)]
    checks={"load_nonnegative":all(r["remaining_load"]>=0 for r in rows),"mass_balance":all(abs(r["remaining_load"]+r["removed_or_decayed"]-c0)<1e-8*max(1,c0) for r in rows),"load_nonincreasing":all(rows[i]["remaining_load"]>=rows[i+1]["remaining_load"]-1e-12 for i in range(len(rows)-1))}
    return {"model_id":"environmental_decay","validation_level":"L1","columns":{"time":"time (model units)","remaining_load":"remaining load (input units)","removed_or_decayed":"removed/decayed load (input units)"},"rows":rows,"checks":checks,"summary":{"initial_load":c0,"final_load":rows[-1]["remaining_load"],"fraction_remaining":rows[-1]["remaining_load"]/c0 if c0 else 0,"removal_rate":k,"half_life":math.log(2)/k if k else None},"limitations":["Single well-mixed compartment with first-order removal.","No sources, transport, adsorption, multiple compartments or site-specific parameters.","Not an environmental impact assessment."]}


def run_one_compartment_pk(params: dict[str, Any]) -> dict[str, Any]:
    dose=_finite_positive(params.get("input_amount",100.0),"input_amount",allow_zero=True); volume=_finite_positive(params.get("distribution_volume",10.0),"distribution_volume"); clearance=_finite_positive(params.get("clearance",1.0),"clearance",allow_zero=True); duration=_finite_positive(params.get("duration",24.0),"duration"); points=params.get("points",49)
    if duration>100000 or not isinstance(points,int) or isinstance(points,bool) or not 3<=points<=1001: raise ValueError("duration must be <=100000 and points an integer from 3 to 1001.")
    k=clearance/volume; rows=[{"time":duration*i/(points-1),"concentration":(dose/volume)*math.exp(-k*duration*i/(points-1))} for i in range(points)]
    checks={"concentration_nonnegative":all(r["concentration"]>=0 for r in rows),"concentration_nonincreasing":all(rows[i]["concentration"]>=rows[i+1]["concentration"]-1e-12 for i in range(len(rows)-1)),"initial_concentration_matches_input_over_volume":abs(rows[0]["concentration"]-dose/volume)<1e-12}
    return {"model_id":"one_compartment_pk","validation_level":"L1","columns":{"time":"time (model units)","concentration":"concentration (input amount / volume units)"},"rows":rows,"checks":checks,"summary":{"initial_concentration":rows[0]["concentration"],"final_concentration":rows[-1]["concentration"],"elimination_rate_constant":k,"half_life":math.log(2)/k if k else None},"limitations":["Teaching model for a single instantaneous input and first-order elimination.","No absorption, multi-compartment distribution, individual variability or real compound parameters.","Not for dose selection, patient care or clinical prediction."]}


def run_lotka_volterra(params: dict[str, Any]) -> dict[str, Any]:
    x0=_finite_positive(params.get("initial_prey",40),"initial_prey"); z0=_finite_positive(params.get("initial_predators",9),"initial_predators"); alpha=_finite_positive(params.get("prey_growth",1.0),"prey_growth",allow_zero=True); beta=_finite_positive(params.get("predation_rate",0.1),"predation_rate",allow_zero=True); delta=_finite_positive(params.get("predator_growth",0.075),"predator_growth",allow_zero=True); gamma=_finite_positive(params.get("predator_decay",1.5),"predator_decay",allow_zero=True); duration=_finite_positive(params.get("duration",20),"duration"); dt=_finite_positive(params.get("dt",0.01),"dt")
    if duration>1000 or dt>0.1 or duration/dt>100000 or abs(duration/dt-round(duration/dt))>1e-8: raise ValueError("duration must be <=1000, dt <=0.1, duration/dt must be an integer, and steps <=100000.")
    def deriv(y):
        x,z=y; return (alpha*x-beta*x*z,delta*x*z-gamma*z)
    x,z=x0,z0; rows=[{"time":0.0,"prey":x,"predators":z}]; steps=int(round(duration/dt)); sample=max(1,steps//500)
    for i in range(steps):
        k1=deriv((x,z)); k2=deriv((x+dt*k1[0]/2,z+dt*k1[1]/2)); k3=deriv((x+dt*k2[0]/2,z+dt*k2[1]/2)); k4=deriv((x+dt*k3[0],z+dt*k3[1])); x+=dt*(k1[0]+2*k2[0]+2*k3[0]+k4[0])/6; z+=dt*(k1[1]+2*k2[1]+2*k3[1]+k4[1])/6
        if not math.isfinite(x+z) or min(x,z)<0: raise ValueError("Numerical integration became non-finite or negative; reduce dt or review parameters.")
        if (i+1)%sample==0 or i==steps-1: rows.append({"time":round((i+1)*dt,8),"prey":x,"predators":z})
    checks={"populations_nonnegative":all(r["prey"]>=0 and r["predators"]>=0 for r in rows),"populations_finite":all(math.isfinite(r["prey"]) and math.isfinite(r["predators"]) for r in rows)}
    return {"model_id":"lotka_volterra","validation_level":"L1","columns":{"time":"time (model units)","prey":"prey population (model units)","predators":"predator population (model units)"},"rows":rows,"checks":checks,"summary":{"final_prey":x,"final_predators":z,"steps":steps,"dt":dt},"limitations":["Classical deterministic Lotka–Volterra equations integrated with fixed-step RK4.","No carrying capacity, spatial structure, stochasticity or field calibration.","Long runs may accumulate numerical error; test convergence by reducing dt."]}


def run_leaky_integrate_fire(params: dict[str, Any]) -> dict[str, Any]:
    v_rest=params.get("v_rest_mv",-65.0); v_reset=params.get("v_reset_mv",-70.0); v_threshold=params.get("v_threshold_mv",-50.0); v0=params.get("initial_voltage_mv",-65.0)
    for key,val in (("v_rest_mv",v_rest),("v_reset_mv",v_reset),("v_threshold_mv",v_threshold),("initial_voltage_mv",v0)):
        if isinstance(val,bool) or not isinstance(val,(int,float)) or not math.isfinite(val): raise ValueError(f"{key} must be a finite number.")
    tau=_finite_positive(params.get("tau_ms",10.0),"tau_ms"); resistance=_finite_positive(params.get("resistance_mohm",10.0),"resistance_mohm",allow_zero=True); current=_finite_positive(params.get("current_na",2.0),"current_na",allow_zero=True); duration=_finite_positive(params.get("duration_ms",100.0),"duration_ms"); dt=_finite_positive(params.get("dt_ms",0.1),"dt_ms")
    if v_reset>=v_threshold or v_rest>=v_threshold: raise ValueError("v_reset_mv and v_rest_mv must be below v_threshold_mv.")
    if duration>10000 or dt>tau*0.2 or duration/dt>100000 or abs(duration/dt-round(duration/dt))>1e-8: raise ValueError("duration must be <=10000 ms; dt must divide duration, be <=0.2*tau, and use <=100000 steps.")
    v=float(v0); rows=[{"time_ms":0.0,"membrane_voltage_mv":v,"spike":0}]; spikes=[]; steps=int(round(duration/dt)); sample=max(1,steps//1000); sample_spike=0; equilibrium=float(v_rest)+resistance*current
    for i in range(steps):
        v_next=equilibrium+(v-equilibrium)*math.exp(-dt/tau); spike=0
        if v_next>=v_threshold:
            spike=1; sample_spike=1; spikes.append(round((i+1)*dt,8)); v=float(v_reset)
        else: v=v_next
        if (i+1)%sample==0 or i==steps-1:
            rows.append({"time_ms":round((i+1)*dt,8),"membrane_voltage_mv":v,"spike":sample_spike})
            sample_spike=0
    checks={"voltage_finite":all(math.isfinite(r["membrane_voltage_mv"]) for r in rows),"reset_below_threshold":all(r["membrane_voltage_mv"]<v_threshold+1e-12 for r in rows),"spike_times_in_range":all(0<t<=duration for t in spikes)}
    return {"model_id":"leaky_integrate_fire","validation_level":"L1","columns":{"time_ms":"time (ms)","membrane_voltage_mv":"membrane potential (mV)","spike":"spike event indicator at sampled time"},"rows":rows,"checks":checks,"summary":{"spike_count":len(spikes),"spike_times_ms":spikes[:500],"equilibrium_voltage_mv":equilibrium,"final_voltage_mv":v,"time_steps":steps},"limitations":["Single-compartment leaky integrate-and-fire neuron with constant input current.","No ion-channel dynamics, synapses, refractory period, morphology or biological calibration.","Not a validated neuroscience model for experimental or clinical conclusions."]}


def run_arrhenius_reaction(params: dict[str, Any]) -> dict[str, Any]:
    a0=_finite_positive(params.get("initial_A",1.0),"initial_A",allow_zero=True); pre=_finite_positive(params.get("pre_exponential_s_inv",1.0),"pre_exponential_s_inv",allow_zero=True); ea=_finite_positive(params.get("activation_energy_j_mol",40000.0),"activation_energy_j_mol",allow_zero=True); temp=_finite_positive(params.get("temperature_k",298.15),"temperature_k"); duration=_finite_positive(params.get("duration_s",10.0),"duration_s"); points=params.get("points",51)
    if temp<1 or duration>100000 or not isinstance(points,int) or isinstance(points,bool) or not 3<=points<=1001: raise ValueError("temperature must be >=1 K, duration <=100000 and points an integer from 3 to 1001.")
    gas_constant=GAS_CONSTANT; exponent=-ea/(gas_constant*temp); k=pre*math.exp(exponent)
    rows=[]
    for i in range(points):
        t=duration*i/(points-1); a=a0*math.exp(-k*t); rows.append({"time_s":t,"A":a,"B":a0-a,"total_A_plus_B":a0})
    checks={"concentrations_nonnegative":all(r["A"]>=-1e-12 and r["B"]>=-1e-12 for r in rows),"mass_balance_preserved":all(abs(r["A"]+r["B"]-a0)<1e-8*max(1,a0) for r in rows),"A_nonincreasing":all(rows[i]["A"]>=rows[i+1]["A"]-1e-12 for i in range(len(rows)-1))}
    return {"model_id":"arrhenius_reaction","validation_level":"L1","columns":{"time_s":"time (s)","A":"reactant A (initial amount units)","B":"product B (initial amount units)","total_A_plus_B":"total amount (initial amount units)"},"rows":rows,"checks":checks,"summary":{"rate_constant_s_inv":k,"temperature_k":temp,"initial_A":a0,"final_A":rows[-1]["A"],"final_B":rows[-1]["B"],"half_life_s":math.log(2)/k if k>0 else None},"assumptions":["k(T) = A exp(-Ea/(R T)) at constant temperature.","Irreversible first-order A→B with constant volume and no side reactions."],"limitations":["Demonstrates a temperature-to-kinetics coupling; no thermal feedback or multi-step chemistry.","Rate parameters are user-supplied and illustrative unless independently sourced.","No empirical validation for a specific chemical system."]}

SOLVERS = {
    "enzyme_kinetics": run_enzyme,
    "sir_epidemic": run_sir,
    "heat_diffusion_1d": run_heat,
    "logistic_growth": run_logistic_growth,
    "first_order_reaction": run_first_order_reaction,
    "environmental_decay": run_environmental_decay,
    "one_compartment_pk": run_one_compartment_pk,
    "lotka_volterra": run_lotka_volterra,
    "leaky_integrate_fire": run_leaky_integrate_fire,
    "arrhenius_reaction": run_arrhenius_reaction,
}

def execute_model(model_id: str, params: dict[str, Any]) -> dict[str, Any]:
    if model_id not in MODEL_CATALOG_BY_ID:
        raise ValueError("Unknown model_id.")
    model = MODEL_CATALOG_BY_ID[model_id]
    if model["status"] != "implemented_demo":
        return {
            "model_id": model_id, "validation_level": "L0",
            "status": "not_simulated",
            "message": "This workflow is not simulated because no domain solver has been connected.",
            "checks": {}, "rows": [],
            "limitations": [model["caveat"], "No scientific calculation was performed."]
        }
    result = SOLVERS[model_id](params)
    result["status"] = "computed_basic_checks_passed" if all(result["checks"].values()) else "computed_checks_failed"
    return result

MODEL_CATALOG_BY_ID = {m["id"]: m for m in MODEL_CATALOG}


# Public, inspectable solver contract for adapters and automated tooling.
SOLVER_CONTRACT_VERSION = "0.5"

def get_solver_contract() -> dict:
    return {
        "contract_version": SOLVER_CONTRACT_VERSION,
        "required_model_metadata": ["id", "name", "discipline", "description", "validation_level", "limitations"],
        "required_input_metadata": ["name", "type", "unit", "minimum", "maximum", "default"],
        "required_output_metadata": ["name", "unit", "description"],
        "execution_requirements": [
            "validate inputs before execution",
            "return machine-readable rows and metadata",
            "record model and configuration versions",
            "document limitations and validation evidence",
            "never silently extrapolate beyond reference-data range"
        ]
    }
