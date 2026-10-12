"""Scientific reports generated from saved dossiers (v6.5).

A report is built only from the dossier, the catalogue, the bibliography and the event journal:
nothing is typed or invented. It keeps four kinds of statements apart:
  Observations     data that were measured or imported (with their source and nature);
  Calculations     values computed by an engine (with units, uncertainties, engine version);
  Interpretation   rule-based statements derived from the checks (labelled as such);
  Conclusions      left to the researcher — the platform does not write scientific conclusions.
Formats: Markdown and a self-contained HTML page (inline SVG charts, no external resource).
"""
from __future__ import annotations

import html
import json
import math
from typing import Any

import history
import model_registry
import references
import trace_package

KIND_FR = {"experimental": "mesure expérimentale publiée", "imported": "données importées (origine déclarée par l'utilisateur)",
           "reference": "valeur de référence", "computed": "valeur calculée", "simulated": "sortie de modèle simulée"}
CONTRACT_FOR = {"chemical_kinetics_network": "mass_action_kinetics", "chemical_stoichiometry": "stoichiometry", "electrical_workbench_dc": "workbench_dc_circuit",
                "electrical_workbench_transient": "workbench_rc_rl_transient"}


# Model forms of the fitting engine and their sources (method: nonlinear regression as in Bates & Watts, 1988).
FIT_REFERENCES = {"michaelis_menten": ["michaelis_menten_1913"], "arrhenius": ["arrhenius_1889"], "logistic": ["verhulst_1838"],
                  "first_order_rise": ["atkins_depaula_2014"], "exponential_decay": ["atkins_depaula_2014"]}


class ReportError(ValueError):
    def __init__(self, message: str, code: str = "report_error"):
        super().__init__(message)
        self.code = code


def _num(v: Any) -> str:
    if isinstance(v, bool) or v is None:
        return str(v)
    if isinstance(v, (int, float)):
        return f"{v:.6g}" if math.isfinite(v) else str(v)
    return str(v)


def _contract(model_id: str) -> dict[str, Any] | None:
    try:
        return model_registry.get_contract(CONTRACT_FOR.get(model_id, model_id))
    except Exception:
        return None


def _series(dossier: dict[str, Any]) -> tuple[str, list[str], list[dict[str, Any]]] | None:
    """(x key, y keys, rows) of the main sampled result, when the dossier has one."""
    if dossier.get("model_id") == "model_fit" and dossier.get("residuals"):
        return "x", ["observed", "fitted"], dossier["residuals"]
    rows = dossier.get("rows") or dossier.get("points")
    if not isinstance(rows, list) or len(rows) < 2 or not isinstance(rows[0], dict):
        return None
    keys = [k for k, v in rows[0].items() if isinstance(v, (int, float)) and not isinstance(v, bool)]
    if len(keys) < 2:
        return None
    x = next((k for k in ("time", "time_s", "x", "time_ms", "frequency_hz") if k in keys), keys[0])
    return x, [k for k in keys if k != x][:4], rows


def _svg(series) -> str:
    x, ys, rows = series
    w, h, p = 640, 260, 44
    xs = [r[x] for r in rows]
    vals = [r[k] for r in rows for k in ys if isinstance(r.get(k), (int, float))]
    if not vals:
        return ""
    x0, x1, y0, y1 = min(xs), max(xs), min(vals), max(vals)
    sx = lambda v: p + (w - 2 * p) * (v - x0) / ((x1 - x0) or 1)
    sy = lambda v: h - p - (h - 2 * p) * (v - y0) / ((y1 - y0) or 1)
    colours = ["#1f4e6b", "#b5562b", "#3c7a3a", "#6b4a8f"]
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" style="max-width:{w}px" role="img" aria-label="Graphique {html.escape(", ".join(ys))} en fonction de {html.escape(x)}">',
             f'<line x1="{p}" y1="{h - p}" x2="{w - p}" y2="{h - p}" stroke="#526268"/><line x1="{p}" y1="{p}" x2="{p}" y2="{h - p}" stroke="#526268"/>',
             f'<text x="{w / 2}" y="{h - 8}" font-size="12" text-anchor="middle" fill="#24333c">{html.escape(x)}</text>',
             f'<text x="{p}" y="{p - 10}" font-size="11" fill="#24333c">{_num(y1)}</text><text x="{p}" y="{h - p + 14}" font-size="11" fill="#24333c">{_num(y0)}</text>']
    for i, k in enumerate(ys):
        pts = " ".join(f"{sx(r[x]):.1f},{sy(r[k]):.1f}" for r in rows if isinstance(r.get(k), (int, float)))
        parts.append(f'<polyline fill="none" stroke="{colours[i % 4]}" stroke-width="2" points="{pts}"/>')
        parts.append(f'<text x="{w - p - 150}" y="{p + 14 * i}" font-size="12" fill="{colours[i % 4]}">— {html.escape(k)}</text>')
    parts.append("</svg>")
    return "".join(parts)


def build(experiment_id: int) -> dict[str, Any]:
    """Structured report (sections as lists of lines) for one saved experiment."""
    record = history.get_experiment_record(int(experiment_id))
    if record is None:
        raise ReportError("Experiment not found.", "not_found")
    d = record["dossier"]
    contract = _contract(str(d.get("model_id")))
    bib = references.sources()
    cited: list[str] = list(contract.get("reference_ids", [])) if contract else []
    if d.get("model_id") == "model_fit":
        cited += ["bates_watts_1988"] + FIT_REFERENCES.get(d.get("model"), [])
    sections: list[tuple[str, list[str]]] = []

    sections.append(("Question et objet", [f"Titre : {d.get('title', '')}", f"Question : {d.get('question') or 'non précisée'}",
                                           f"Statut des données : {d.get('data_status', 'non précisé')}"]))
    method = [f"Modèle : `{d.get('model_id')}` — moteur `{(d.get('engine') or {}).get('id')}` version {(d.get('engine') or {}).get('version')} ; application {d.get('app_version')}."]
    if contract:
        method += [f"Équation : {e}" for e in contract.get("equations", [])]
        method += [f"Validité : {v}" for v in contract.get("validity", [])]
        maturity = contract.get("maturity") or {}
        if maturity:
            method.append(f"Maturité du modèle : {maturity.get('label_fr', maturity.get('level'))}.")
    if d.get("equation"):
        method.append(f"Équation ajustée : {d['equation']} ; méthode : {(d.get('optimizer') or {}).get('method', '')}.")
    sections.append(("Méthode", method))

    params = []
    configuration = d.get("configuration") or {}
    spec = {p["name"]: p for p in (contract or {}).get("parameters", [])}
    for k, v in configuration.items():
        if isinstance(v, (int, float, str, bool)) or v is None:
            unit = spec.get(k, {}).get("unit", "")
            label = spec.get(k, {}).get("default_provenance", {}).get("status")
            note = " (valeur par défaut illustrative)" if label and v == spec.get(k, {}).get("default") else ""
            params.append(f"{k} = {_num(v)} {unit}{note}".rstrip())
        else:
            params.append(f"{k} = {json.dumps(v, ensure_ascii=False)[:300]}")
    sections.append(("Paramètres", params or ["(aucun paramètre enregistré)"]))

    observations = []
    data = d.get("data")
    if isinstance(data, dict):
        observations.append(f"Jeu de données `{data.get('id')}` v{data.get('version')} — nature : {KIND_FR.get(data.get('data_kind'), data.get('data_kind'))} ; "
                            f"{data.get('rows_used')} lignes utilisées ; empreinte du contenu {str(data.get('content_sha256'))[:16]}….")
        if data.get("where"):
            observations.append(f"Sous-ensemble : {json.dumps(data['where'], ensure_ascii=False)}.")
        if data.get("rows_dropped_missing"):
            observations.append(f"Lignes exclues pour valeur manquante : {data['rows_dropped_missing']}.")
        cited += [s for s in data.get("source_ids", []) if s not in cited]
    sections.append(("Observations (données mesurées ou importées)", observations or ["Aucune donnée observée : ce dossier ne contient que des calculs."]))

    calc = []
    if isinstance(d.get("parameters"), dict):
        for name, p in d["parameters"].items():
            calc.append(f"{name} = {_num(p['value'])} ± {_num(p['standard_error'])} {p['unit']} (erreur type ; IC 95 % [{_num(p['ci95'][0])} ; {_num(p['ci95'][1])}])")
        calc.append(f"Erreur résiduelle : {_num(d.get('residual_standard_error'))} {d.get('y_unit', '')} ; {d.get('degrees_of_freedom')} degrés de liberté ; R² {_num(d.get('r_squared'))}.")
    summary = d.get("summary") if isinstance(d.get("summary"), dict) else {}
    for k, v in summary.items():
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            calc.append(f"{k} = {_num(v)}")
        elif isinstance(v, dict) and all(isinstance(x, (int, float)) for x in v.values()):
            calc.append(f"{k} : " + ", ".join(f"{a} = {_num(b)}" for a, b in v.items()))
    for k in ("final_outputs", "outputs"):
        if isinstance(d.get(k), dict):
            for name, o in d[k].items():
                if isinstance(o, dict) and "value" in o:
                    calc.append(f"{name} = {_num(o['value'])} {o.get('unit', '')}")
    if isinstance(d.get("reading"), dict):
        r = d["reading"]
        calc.append(f"Lecture simulée : {_num(r.get('displayed_value'))} {r.get('unit', '')} (incertitude élargie {_num(r.get('expanded_uncertainty'))})")
    sections.append(("Calculs (valeurs produites par le moteur)", calc or ["Voir les valeurs détaillées du dossier JSON."]))

    uncertainty = []
    for k in ("estimated_final_error", "error_estimate", "uncertainty", "numerical_uncertainty"):
        if d.get(k) is not None or (summary.get(k) is not None):
            uncertainty.append(f"{k} : {json.dumps(d.get(k, summary.get(k)), ensure_ascii=False, default=str)[:400]}")
    if isinstance(d.get("parameters"), dict):
        uncertainty.append("Les intervalles des paramètres viennent de l'approximation linéaire s²(JᵀJ)⁻¹ ; ils supposent des erreurs indépendantes et de variance constante.")
    sections.append(("Incertitudes", uncertainty or ["Aucune incertitude numérique n'est publiée par ce moteur pour ce dossier ; ne pas en déduire qu'elle est nulle."]))

    hyp = [f"Hypothèse : {a}" for a in (d.get("assumptions") or (contract or {}).get("assumptions") or [])]
    hyp += [f"Limite : {l}" for l in d.get("limitations", [])]
    sections.append(("Hypothèses et limites", hyp or ["Non précisées dans le dossier."]))

    interpretation = ["Les phrases ci-dessous sont produites par des règles fixes à partir des contrôles enregistrés ; elles ne remplacent pas l'analyse du chercheur."]
    checks = d.get("checks") if isinstance(d.get("checks"), dict) else {}
    failed = [k for k, v in checks.items() if v is False]
    if checks:
        interpretation.append("Tous les contrôles internes enregistrés sont satisfaits." if not failed else f"Contrôles non satisfaits : {', '.join(failed)}.")
    if isinstance(d.get("validation"), dict):
        ratio = d["validation"].get("rmse_over_residual_standard_error")
        interpretation.append(f"Sur {d['validation']['points']} points non utilisés pour l'ajustement, l'erreur de prédiction vaut {_num(ratio)} fois l'erreur résiduelle de l'ajustement.")
    rt = (d.get("diagnostics") or {}).get("runs_test") or {}
    if rt.get("z") is not None:
        interpretation.append("Le test des suites ne montre pas de structure systématique des résidus (|z| ≤ 2)." if abs(rt["z"]) <= 2
                              else f"Le test des suites indique une structure des résidus (z = {_num(rt['z'])}) : forme du modèle à revoir.")
    for w in d.get("warnings", []) or []:
        if isinstance(w, dict) and w.get("message"):
            interpretation.append(f"Avertissement du moteur : {w['message']}")
    sections.append(("Interprétation (règles automatiques, à vérifier)", interpretation))
    sections.append(("Conclusions", ["À rédiger par le chercheur. La plateforme ne formule pas de conclusion scientifique : elle fournit les éléments ci-dessus et leurs limites."]))

    refs = [f"[{sid}] {bib[sid]['citation']}" + (f" doi:{bib[sid]['doi']}" if bib[sid].get("doi") else "") for sid in cited if sid in bib]
    sections.append(("Références", refs or ["Aucune référence associée à ce modèle."]))
    journal = trace_package.events(int(experiment_id))
    trace = [f"Empreinte de la configuration : {d.get('configuration_hash')}", f"Empreinte du dossier : {d.get('dossier_hash')}",
             f"Créé le : {d.get('created_at_utc')}"] + [f"{e['at_utc']} — {e['event']}" for e in journal]
    sections.append(("Traçabilité", trace))
    return {"experiment_id": int(experiment_id), "title": d.get("title", ""), "sections": sections, "series": _series(d), "cited_source_ids": cited}


def to_markdown(report: dict[str, Any]) -> str:
    lines = [f"# Rapport — {report['title']}", "", f"Expérience n° {report['experiment_id']}. Rapport généré automatiquement à partir du dossier enregistré.", ""]
    for title, items in report["sections"]:
        lines += [f"## {title}", ""] + [f"- {i}" for i in items] + [""]
    if report["series"]:
        x, ys, rows = report["series"]
        lines += ["## Données de base du graphique", "", "| " + " | ".join([x] + ys) + " |", "|" + "---|" * (len(ys) + 1)]
        lines += ["| " + " | ".join(_num(r.get(k)) for k in [x] + ys) + " |" for r in rows[:200]]
        if len(rows) > 200:
            lines.append(f"\n({len(rows) - 200} lignes supplémentaires dans le dossier JSON.)")
    return "\n".join(lines) + "\n"


def to_html(report: dict[str, Any]) -> str:
    esc = html.escape
    body = [f"<h1>Rapport — {esc(report['title'])}</h1>", f"<p>Expérience n° {report['experiment_id']}. Rapport généré automatiquement à partir du dossier enregistré.</p>"]
    for title, items in report["sections"]:
        body.append(f'<section data-section="{esc(title)}"><h2>{esc(title)}</h2><ul>' + "".join(f"<li>{esc(i)}</li>" for i in items) + "</ul></section>")
        if title.startswith("Calculs") and report["series"]:
            body.append(f'<figure>{_svg(report["series"])}<figcaption>Valeurs du dossier (aucune donnée ajoutée).</figcaption></figure>')
    if report["series"]:
        x, ys, rows = report["series"]
        body.append("<section><h2>Données de base du graphique</h2><table><thead><tr>" + "".join(f"<th>{esc(k)}</th>" for k in [x] + ys) + "</tr></thead><tbody>"
                    + "".join("<tr>" + "".join(f"<td>{esc(_num(r.get(k)))}</td>" for k in [x] + ys) + "</tr>" for r in rows[:500]) + "</tbody></table></section>")
    style = ("body{font-family:system-ui,sans-serif;max-width:900px;margin:24px auto;padding:0 16px;color:#24333c;background:#fff}"
             "h1{font-size:1.5rem}h2{font-size:1.15rem;margin-top:1.4em;border-bottom:1px solid #d9e1e3}table{border-collapse:collapse;font-size:12px}"
             "th,td{border:1px solid #d9e1e3;padding:3px 6px;text-align:right}th{background:#eef3f4}")
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f"<title>Rapport {report['experiment_id']}</title><style>{style}</style></head><body>{''.join(body)}</body></html>\n")
