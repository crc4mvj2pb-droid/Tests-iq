"""Transparent local scientific copilot: intent routing to implemented solvers.
It is not a generative foundation model and never claims unimplemented simulations ran.
"""
from __future__ import annotations
import re
from models import execute_model, MODEL_CATALOG

ROUTES = [
 ("arrhenius_reaction", ("arrhenius", "activation energy", "énergie d'activation", "temperature-dependent reaction", "réaction dépendante de la température", "température et vitesse de réaction")),
 ("first_order_reaction", ("first-order reaction", "réaction du premier ordre", "concentration over time", "concentration au cours du temps", "a → b", "a -> b", "reaction kinetics", "cinétique chimique")),
 ("enzyme_kinetics", ("enzyme", "enzym", "michaelis", "substrate concentration", "concentration de substrat")),
 ("leaky_integrate_fire", ("neuron", "neurone", "membrane potential", "potentiel membranaire", "spike", "potentiel d'action")),
 ("lotka_volterra", ("predator", "prey", "proie", "prédateur", "lotka", "population interactions")),
 ("logistic_growth", ("logistic growth", "croissance logistique", "population growth", "croissance d'une population", "carrying capacity", "capacité de charge")),
 ("sir_epidemic", ("sir model", "épidémie", "epidemic", "infectious", "infectieux", "susceptible")),
 ("heat_diffusion_1d", ("heat diffusion", "diffusion thermique", "temperature along", "température le long", "thermal gradient", "gradient thermique")),
 ("environmental_decay", ("environmental decay", "pollutant decay", "dégradation d'un polluant", "décroissance environnementale", "contaminant")),
 ("one_compartment_pk", ("pharmacokinetic", "pharmacocinétique", "drug concentration", "concentration médicamenteuse", "one-compartment", "demi-vie")),
]

DEFAULTS = {
 "arrhenius_reaction": {"A": 1.0, "Ea": 50000.0, "temperature_c": 25.0, "initial_concentration": 1.0, "duration": 10.0, "points": 51},
 "first_order_reaction": {"k": 0.25, "a0": 1.0, "duration": 10.0, "points": 51},
 "enzyme_kinetics": {"vmax": 1.0, "km": 2.0, "s_max": 10.0, "points": 51},
 "leaky_integrate_fire": {"input_current": 1.5, "duration": 100.0, "dt": 0.1},
 "lotka_volterra": {"prey0": 40.0, "predator0": 9.0, "alpha": 1.1, "beta": 0.04, "delta": 0.02, "gamma": 0.7, "duration": 30.0, "dt": 0.05},
 "logistic_growth": {"r": 0.3, "k": 100.0, "n0": 5.0, "duration": 30.0, "points": 51},
 "sir_epidemic": {"population": 10000, "beta": 0.3, "gamma": 0.1, "initial_infected": 10, "days": 160, "dt": 0.1},
 "heat_diffusion_1d": {"length": 1.0, "nx": 21, "duration": 10.0, "dt": 0.01, "initial_temperature": 20.0, "left_temperature": 100.0, "right_temperature": 20.0, "diffusivity": 0.01},
 "environmental_decay": {"initial_load": 100.0, "decay_rate": 0.1, "duration": 30.0, "points": 51},
 "one_compartment_pk": {"dose": 100.0, "volume": 10.0, "elimination_rate": 0.2, "duration": 24.0, "points": 49},
}

PARAM_PATTERNS = {
 "k": [r"\bk\s*[=:]\s*([0-9.eE+-]+)", r"rate constant\s*[=:]\s*([0-9.eE+-]+)", r"constante\s+de\s+vitesse\s*[=:]\s*([0-9.eE+-]+)"],
 "a0": [r"a0\s*[=:]\s*([0-9.eE+-]+)", r"initial concentration\s*[=:]\s*([0-9.eE+-]+)", r"concentration initiale\s*[=:]\s*([0-9.eE+-]+)"],
 "temperature_c": [r"(?:temperature|température)\s*[=:]\s*([0-9.eE+-]+)"],
 "vmax": [r"vmax\s*[=:]\s*([0-9.eE+-]+)"], "km": [r"\bkm\s*[=:]\s*([0-9.eE+-]+)"],
 "duration": [r"(?:duration|durée)\s*[=:]\s*([0-9.eE+-]+)"], "r": [r"\br\s*[=:]\s*([0-9.eE+-]+)"], "k": [r"\bk\s*[=:]\s*([0-9.eE+-]+)"],
}

def _choose_model(question: str):
 q=question.casefold()
 matches=[]
 for model_id, keys in ROUTES:
  score=sum(1 for key in keys if key in q)
  if score: matches.append((score, model_id))
 return sorted(matches, reverse=True)[0][1] if matches else None

def _parameters(model_id, question, supplied):
 params=dict(DEFAULTS[model_id]); params.update(supplied or {})
 q=question.casefold()
 for name, patterns in PARAM_PATTERNS.items():
  if name not in params: continue
  for pat in patterns:
   m=re.search(pat,q,re.I)
   if m:
    try: params[name]=float(m.group(1))
    except ValueError: pass
    break
 return params

def ask_scientific_copilot(question: str, supplied_parameters=None):
 if not isinstance(question,str) or not question.strip(): raise ValueError("Enter a scientific question or experiment objective.")
 if len(question)>8000: raise ValueError("Question is too long (maximum 8000 characters).")
 model_id=_choose_model(question)
 if not model_id:
  return {"assistant":"Virtual Lab Scientific Copilot","mode":"local_expert_router","status":"needs_model_selection","answer":"I could not map this question confidently to an implemented numerical solver. I will not invent a simulation. Choose a supported model or narrow the question to a defined mathematical system.","question":question,"suggested_models":[{"id":m["id"],"name":m["name"],"domain":m["domain"],"validation_level":m["validation_level"],"status":m["status"]} for m in MODEL_CATALOG],"process":[{"step":1,"title":"Operationalize the question","detail":"Define state variables, units, parameters, initial conditions, boundary conditions and an observable."},{"step":2,"title":"Choose a model","detail":"Select a documented model whose assumptions match the question."},{"step":3,"title":"Validate inputs and reference data","detail":"Supply source data and benchmark cases before interpreting scientific significance."}],"limitations":["This assistant is a local, deterministic research copilot, not a trained generative AI model.","No simulation was run because no supported model could be selected."]}
 params=_parameters(model_id, question, supplied_parameters)
 result=execute_model(model_id,params)
 model=next(m for m in MODEL_CATALOG if m["id"]==model_id)
 rows=result.get("rows",[])
 numeric_rows=[r for r in rows if isinstance(r,dict)]
 summary=result.get("summary",{})
 # Derive concise output summaries from actual solver rows.
 series={}
 if numeric_rows:
  keys=[k for k,v in numeric_rows[0].items() if k not in ("x","t","time") and isinstance(v,(int,float))]
  for key in keys:
   vals=[float(r[key]) for r in numeric_rows if isinstance(r.get(key),(int,float))]
   if vals: series[key]={"initial":vals[0],"final":vals[-1],"minimum":min(vals),"maximum":max(vals),"n":len(vals)}
 steps=[
  {"step":1,"title":"Question translated into a model","detail":f"Mapped to {model['name']} ({model_id}); domain={model['domain']}."},
  {"step":2,"title":"Parameters and assumptions","detail":"Run used the parameter set below. Values not explicitly supplied were filled from clearly labelled illustrative defaults."},
  {"step":3,"title":"Numerical calculation","detail":f"The local solver returned {len(rows)} output rows. Model checks: {result.get('checks',{})}."},
  {"step":4,"title":"Inspect and challenge the result","detail":"Compare against independent reference data, vary parameters, inspect residuals and perform sensitivity/uncertainty analysis before drawing research conclusions."}
 ]
 return {"assistant":"Virtual Lab Scientific Copilot","mode":"local_expert_router","status":result.get("status","computed"),"question":question,"model":{"id":model_id,"name":model["name"],"domain":model["domain"],"validation_level":model["validation_level"],"caveat":model["caveat"]},"answer":"A supported model was selected and executed. The figures below are solver output under the stated assumptions, not empirical observations or a claim of real-world validation.","parameters_used":params,"summary":summary,"series_summary":series,"checks":result.get("checks",{}),"process":steps,"limitations":result.get("limitations",[model["caveat"]]),"rows":rows[:250],"row_count":len(rows),"full_result":result,"ai_disclosure":"This is a deterministic local scientific copilot that routes questions to existing solvers. It is not a trained generative AI and does not have live literature retrieval. Unmatched questions are not fabricated."}
