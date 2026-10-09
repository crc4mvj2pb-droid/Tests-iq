import { getProgress, launch, navigate, onProgress } from '../app';
import {
  anova2, bestPoint, evaluateCriterion, fmt, fmtP, impact, pct, pointStats, refinedOptimum, sensitivity, variedFactors, type PointStats,
} from '../engine/analysis';
import { levels } from '../engine/plan';
import { store } from '../engine/store';
import { DESIGN_LABELS, type Experiment, type ExperimentResult, type ExperimentSpec } from '../engine/types';
import { histogram, ols, summarize } from '../core/stats';
import { getModel } from '../models';
import type { Model, PlotDef, SimOutput } from '../models/types';
import { heatmap, histogramChart, lineChart, PALETTE, scatterChart, tornado, viridis, type LineSeries } from '../ui/charts';
import { dateTime, downloadFile, euros, h, hours, toast } from '../ui/dom';
import { card, empty, kpi, metricLabel, metricSelect, pageHeader, paramLabel, statusBadge, table } from './common';

function seriesLabel(model: Model, key: string): string {
  return model.series.find((s) => s.key === key)?.label ?? key;
}

function plotOutput(model: Model, plot: PlotDef, out: SimOutput): HTMLElement {
  const xs = plot.x === 't' ? out.t : out.series[plot.x];
  const series: LineSeries[] = plot.ys.map((k, i) => ({
    name: seriesLabel(model, k), x: xs, y: out.series[k], color: PALETTE[i % PALETTE.length],
    dashed: ['capacity', 'mec', 'mtc'].includes(k),
  }));
  return h('div', null, h('h3', null, plot.title), lineChart(series, { xLabel: plot.xLabel, yLabel: plot.yLabel }));
}

/** Superpose une courbe par point du plan (couleur = niveau du facteur). */
function overlayTraces(model: Model, plot: PlotDef, traces: ExperimentResult['traces'], spaghetti = false): HTMLElement {
  const key = plot.ys[0];
  const n = traces.length;
  const series: LineSeries[] = traces.map((tr, i) => ({
    name: tr.label, x: plot.x === 't' ? tr.output.t : tr.output.series[plot.x], y: tr.output.series[key],
    color: spaghetti ? PALETTE[0] : viridis(n > 1 ? i / (n - 1) : 0.5), width: spaghetti ? 1 : 1.6,
    opacity: spaghetti ? 0.35 : 1, quiet: spaghetti || n > 10,
  }));
  return h('div', null, h('h3', null, `${plot.title} — ${seriesLabel(model, key)}`), lineChart(series, { xLabel: plot.xLabel, yLabel: plot.yLabel }));
}

function metricsTable(model: Model, p: PointStats, replicated: boolean): HTMLElement {
  return table(
    replicated ? ['Indicateur', 'Moyenne', 'Écart-type', 'IC 95 %', 'CV'] : ['Indicateur', 'Valeur'],
    model.metrics.map((m) => {
      const s = p.metrics[m.key];
      const label = `${m.label}${m.unit !== '—' ? ` (${m.unit})` : ''}`;
      return replicated
        ? [label, fmt(s.mean), fmt(s.sd), `[${fmt(s.ciLow)} ; ${fmt(s.ciHigh)}]`, Number.isFinite(s.cv) ? pct(s.cv) : '—']
        : [label, fmt(s.mean)];
    }),
    { numeric: replicated ? [1, 2, 3, 4] : [1] });
}

function paramsList(model: Model, spec: ExperimentSpec, params: Record<string, number>, onlyVaried = true): HTMLElement {
  const keys = onlyVaried ? variedFactors(spec) : model.params.map((p) => p.key);
  return h('dl', { class: 'param-list' }, keys.flatMap((k) => [h('dt', null, paramLabel(model, k)), h('dd', null, fmt(params[k]))]));
}

function analysisSection(model: Model, exp: Experiment, metric: string, points: PointStats[]): HTMLElement {
  const spec = exp.spec;
  const res = exp.result!;
  const d = spec.design;
  const crit = spec.criterion?.metric === metric ? spec.criterion : undefined;
  const mLabel = metricLabel(model, metric);
  const out = h('div', { class: 'stack' });

  if (d.kind === 'single') {
    const replicated = spec.replicates > 1 && spec.measurementNoise;
    out.append(card('Mesures', metricsTable(model, points[0], replicated),
      replicated ? h('p', { class: 'muted' }, `${spec.replicates} réplicats avec bruit instrumental simulé ; IC 95 % calculé avec la loi de Student.`) : null));
    if (res.traces[0]) out.append(card('Évolution temporelle', h('div', { class: 'charts' }, model.plots.map((pl) => plotOutput(model, pl, res.traces[0].output)))));
    return out;
  }

  if (d.kind === 'sweep') {
    const key = d.factor.key;
    const xs = points.map((p) => p.params[key]);
    const ys = points.map((p) => p.metrics[metric].mean);
    const opt = spec.objective.metric === metric ? refinedOptimum(xs, ys, spec.objective.goal) : undefined;
    const replicated = spec.replicates > 1;
    out.append(card(`Courbe de réponse — ${mLabel}`,
      lineChart([{
        name: mLabel, x: xs, y: ys, markers: true,
        lo: replicated ? points.map((p) => p.metrics[metric].ciLow) : undefined,
        hi: replicated ? points.map((p) => p.metrics[metric].ciHigh) : undefined,
      }], {
        xLabel: paramLabel(model, key), yLabel: mLabel, xLog: d.factor.scale === 'log',
        hline: crit ? { y: crit.threshold, label: `Critère ${crit.op} ${crit.threshold}` } : undefined,
        vline: opt ? { x: opt.x, label: `Optimum ≈ ${fmt(opt.x, 3)}` } : undefined,
      }),
      replicated ? h('p', { class: 'muted' }, 'Barres : intervalle de confiance à 95 % de la moyenne des réplicats.') : null,
      opt ? h('p', { class: 'callout' }, `Optimum interpolé (ajustement parabolique local) : ${paramLabel(model, key)} ≈ ${fmt(opt.x)} → ${mLabel} ≈ ${fmt(opt.y)}.`) : null));
    const traceCharts = model.plots.slice(0, 2).map((pl) => overlayTraces(model, pl, res.traces));
    out.append(card('Comportement dynamique selon le niveau du facteur', h('p', { class: 'muted' }, 'Couleur : du niveau le plus bas (violet) au plus haut (jaune).'), h('div', { class: 'charts' }, traceCharts)));
    out.append(card('Tableau des niveaux', table(
      [paramLabel(model, key), `${mLabel} — moyenne`, replicated ? 'IC 95 %' : '', ...(crit ? ['Critère'] : [])].filter(Boolean),
      points.map((p) => {
        const s = p.metrics[metric];
        const ok = crit ? (crit.op === '>' ? s.mean > crit.threshold : s.mean < crit.threshold) : null;
        return [fmt(p.params[key]), fmt(s.mean), ...(replicated ? [`[${fmt(s.ciLow)} ; ${fmt(s.ciHigh)}]`] : []),
          ...(crit ? [h('span', { class: `badge ${ok ? 'good' : 'bad'}` }, ok ? 'Satisfait' : 'Non')] : [])];
      }), { numeric: [0, 1, 2] })));
    return out;
  }

  if (d.kind === 'factorial') {
    const [fa, fb] = d.factors;
    const la = levels(fa), lb = levels(fb);
    const byPoint = new Map(points.map((p) => [p.point, p]));
    const z = la.map((_, i) => lb.map((__, j) => byPoint.get(i * lb.length + j)?.metrics[metric].mean ?? NaN));
    const best = bestPoint(points, metric, spec.objective.metric === metric ? spec.objective.goal : 'max');
    const bi = best ? Math.floor(best.point / lb.length) : -1;
    const bj = best ? best.point % lb.length : -1;
    out.append(card(`Carte de réponse — ${mLabel}`,
      heatmap(la, lb, z, { xLabel: paramLabel(model, fa.key), yLabel: paramLabel(model, fb.key), zLabel: mLabel, best: best ? [bi, bj] : undefined }),
      best ? h('p', { class: 'muted' }, `Case encadrée : ${spec.objective.metric === metric ? 'meilleure configuration selon l\'objectif' : 'valeur maximale'}.`) : null));
    const rows = anova2(spec, res, metric, [paramLabel(model, fa.key, false), paramLabel(model, fb.key, false)]);
    out.append(card('Analyse de la variance (ANOVA à deux facteurs)',
      table(['Source', 'Somme des carrés', 'ddl', 'Part de variance', 'F', 'p'],
        rows.map((r) => [r.source, fmt(r.ss), String(r.df), h('span', { class: 'bar-cell' }, h('i', { style: `width:${(r.share * 100).toFixed(1)}%` }), pct(r.share)),
          r.f !== undefined ? fmt(r.f) : '—', r.p !== undefined ? fmtP(r.p) : '—']), { numeric: [1, 2, 4, 5] }),
      h('p', { class: 'muted' }, rows.some((r) => r.p !== undefined)
        ? 'Tests F calculés contre la variance résiduelle des réplicats (bruit de mesure). p < 0,05 : effet significatif.'
        : 'Sans réplicats bruités, l\'analyse se limite à la décomposition de la variance (résultats déterministes).')));
    const effect = (ls: number[], pick: (p: PointStats) => number) => ls.map((v) => {
      const sel = points.filter((p) => pick(p) === v);
      return sel.reduce((acc, p) => acc + p.metrics[metric].mean, 0) / sel.length;
    });
    out.append(card('Effets principaux', h('div', { class: 'charts' },
      lineChart([{ name: mLabel, x: la, y: effect(la, (p) => p.params[fa.key]), markers: true }], { xLabel: paramLabel(model, fa.key), yLabel: mLabel, height: 260, xLog: fa.scale === 'log' }),
      lineChart([{ name: mLabel, x: lb, y: effect(lb, (p) => p.params[fb.key]), markers: true, color: PALETTE[1] }], { xLabel: paramLabel(model, fb.key), yLabel: mLabel, height: 260, xLog: fb.scale === 'log' }))));
    return out;
  }

  // Monte Carlo et hypercube latin
  const values = res.runs.map((r) => r.metrics[metric]).filter(Number.isFinite);
  const s = summarize(values);
  const sens = sensitivity(spec, res, metric);
  if (d.kind === 'montecarlo') {
    out.append(card(`Distribution — ${mLabel}`,
      histogramChart(histogram(values, Math.min(40, Math.max(10, Math.round(Math.sqrt(values.length))))), {
        xLabel: mLabel,
        markers: [
          { x: s.p05, label: `P5 = ${fmt(s.p05)}`, color: PALETTE[3] },
          { x: s.mean, label: `Moyenne = ${fmt(s.mean)}`, color: PALETTE[2] },
          { x: s.p95, label: `P95 = ${fmt(s.p95)}`, color: PALETTE[3] },
          ...(crit ? [{ x: crit.threshold, label: `Seuil = ${crit.threshold}`, color: PALETTE[1] }] : []),
        ],
      }),
      h('div', { class: 'kpis compact' },
        kpi('Moyenne', fmt(s.mean), `IC 95 % [${fmt(s.ciLow)} ; ${fmt(s.ciHigh)}]`),
        kpi('Médiane', fmt(s.median)),
        kpi('Intervalle 90 %', `${fmt(s.p05)} – ${fmt(s.p95)}`),
        kpi('Coefficient de variation', Number.isFinite(s.cv) ? pct(s.cv) : '—'))));
  } else {
    const best = bestPoint(points, spec.objective.metric, spec.objective.goal);
    const top = [...points].filter((p) => Number.isFinite(p.metrics[spec.objective.metric].mean))
      .sort((a, b) => (spec.objective.goal === 'max' ? -1 : 1) * (a.metrics[spec.objective.metric].mean - b.metrics[spec.objective.metric].mean)).slice(0, 10);
    const lead = sens.rows[0]?.factor;
    if (lead) {
      const X = res.runs.map((r) => [r.params[lead]]);
      const reg = ols(X, res.runs.map((r) => r.metrics[metric]));
      out.append(card(`${mLabel} en fonction du facteur le plus influent`,
        scatterChart(res.runs.map((r) => ({ x: r.params[lead], y: r.metrics[metric], highlight: best?.point === r.point })),
          { xLabel: paramLabel(model, lead), yLabel: mLabel, trend: { intercept: reg.coefficients[0], slope: reg.coefficients[1] } })));
    }
    out.append(card(`Meilleures configurations — ${metricLabel(model, spec.objective.metric)} (${spec.objective.goal === 'max' ? 'maximisation' : 'minimisation'})`,
      table(['Rang', ...variedFactors(spec).map((k) => paramLabel(model, k)), metricLabel(model, spec.objective.metric)],
        top.map((p, i) => [String(i + 1), ...variedFactors(spec).map((k) => fmt(p.params[k])), h('strong', null, fmt(p.metrics[spec.objective.metric].mean))]),
        { numeric: [0, ...variedFactors(spec).map((_, i) => i + 1), variedFactors(spec).length + 1] })));
  }
  out.append(card('Analyse de sensibilité',
    sens.rows.length ? tornado(sens.rows.map((r) => ({ label: paramLabel(model, r.factor, false), value: r.spearman, secondary: r.src })), { valueLabel: 'Corrélation de rang (Spearman)', secondaryLabel: 'Coefficient de régression standardisé' }) : empty('Pas assez de données.'),
    h('p', { class: 'muted' }, `Facteurs classés par influence sur « ${mLabel} ». R² du modèle linéaire : ${Number.isFinite(sens.r2) ? pct(sens.r2) : '—'}`,
      sens.r2 < 0.7 ? ' — réponse fortement non linéaire ou avec interactions : se fier au classement de Spearman.' : '.')));
  if (d.kind === 'montecarlo') {
    out.append(card('Synthèse de tous les indicateurs', table(['Indicateur', 'Moyenne', 'Écart-type', 'P5', 'Médiane', 'P95'],
      model.metrics.map((m) => {
        const x = summarize(res.runs.map((r) => r.metrics[m.key]));
        return [metricLabel(model, m.key), fmt(x.mean), fmt(x.sd), fmt(x.p05), fmt(x.median), fmt(x.p95)];
      }), { numeric: [1, 2, 3, 4, 5] })));
  }
  if (model.plots[0]) out.append(card('Faisceau de trajectoires simulées', h('p', { class: 'muted' }, `${res.traces.length} trajectoires représentatives.`), overlayTraces(model, model.plots[0], res.traces, true)));
  return out;
}

function toCsv(model: Model, res: ExperimentResult): string {
  const pk = model.params.map((p) => p.key);
  const mk = model.metrics.map((m) => m.key);
  const head = ['point', 'replicat', ...pk.map((k) => `${k} [${model.params.find((p) => p.key === k)!.unit}]`), ...mk.map((k) => `${k} [${model.metrics.find((m) => m.key === k)!.unit}]`)];
  const lines = res.runs.map((r) => [r.point + 1, r.replicate + 1, ...pk.map((k) => r.params[k]), ...mk.map((k) => r.metrics[k])].join(';'));
  return [head.join(';'), ...lines].join('\n');
}

export function experimentView(id: string): HTMLElement {
  const root = h('div', { class: 'page' });
  let metric = '';
  let lastStatus = '';

  const draw = () => {
    const exp = store.get(id);
    if (!exp) { root.replaceChildren(empty('Expérience introuvable.', h('a', { class: 'btn', href: '#/experiments' }, 'Retour au cahier'))); return; }
    lastStatus = exp.status;
    const model = getModel(exp.spec.modelId);
    const spec = exp.spec;
    if (!metric) metric = spec.objective.metric;

    const actions = [
      h('a', { class: 'btn', href: `#/new?from=${spec.id}` }, 'Créer une variante'),
      exp.status === 'done' ? h('button', { class: 'btn', onclick: () => downloadFile(`${spec.name}.csv`, toCsv(model, exp.result!), 'text/csv') }, 'Export CSV') : null,
      h('button', { class: 'btn', onclick: () => downloadFile(`${spec.name}.json`, JSON.stringify({ format: 'virtulab/1', spec, runs: exp.result?.runs }, null, 1), 'application/json') }, 'Export JSON'),
      exp.status === 'done' ? h('button', { class: 'btn', onclick: () => window.print() }, 'Rapport PDF') : null,
      h('button', { class: 'btn danger', onclick: async () => {
        if (!confirm('Supprimer définitivement cette expérience ?')) return;
        getProgress(id)?.cancel();
        await store.remove(id);
        navigate('#/experiments');
      } }, 'Supprimer'),
    ];

    const header = pageHeader(spec.name, undefined, ...actions);
    const meta = card(null,
      h('div', { class: 'meta-grid' },
        h('div', null, h('span', { class: 'kpi-label' }, 'Modèle'), h('a', { href: `#/models/${model.id}` }, `${model.icon} ${model.name}`)),
        h('div', null, h('span', { class: 'kpi-label' }, 'Plan'), h('span', null, DESIGN_LABELS[spec.design.kind].name)),
        h('div', null, h('span', { class: 'kpi-label' }, 'Statut'), statusBadge(exp)),
        h('div', null, h('span', { class: 'kpi-label' }, 'Créée le'), h('span', null, dateTime(spec.createdAt))),
        h('div', null, h('span', { class: 'kpi-label' }, 'Reproductibilité'), h('span', null, `graine ${spec.seed} · ${spec.replicates} réplicat(s) · bruit ${spec.measurementNoise ? 'activé' : 'désactivé'}`))),
      spec.hypothesis ? h('blockquote', null, h('strong', null, 'Hypothèse : '), spec.hypothesis) : null,
      h('details', null, h('summary', null, 'Conditions nominales'), paramsList(model, spec, spec.base, false)));

    const parts: (HTMLElement | null)[] = [header, meta];

    if (exp.status === 'running') {
      const p = getProgress(id);
      parts.push(card('Exécution en cours',
        h('div', { class: 'progress' }, h('i', { id: 'prog-bar', style: `width:${p ? (100 * p.done) / p.total : 0}%` })),
        h('p', { class: 'muted', id: 'prog-text' }, p ? `${p.done.toLocaleString('fr-FR')} / ${p.total.toLocaleString('fr-FR')} simulations` : 'Préparation…'),
        h('button', { class: 'btn', onclick: () => getProgress(id)?.cancel() }, 'Annuler')));
    } else if (exp.status === 'error' || exp.status === 'draft') {
      parts.push(card(exp.status === 'error' ? 'L\'exécution a échoué' : 'Expérience non exécutée',
        exp.error ? h('p', { class: 'muted' }, exp.error) : h('p', { class: 'muted' }, 'Aucun résultat enregistré (exécution interrompue ou importée).'),
        h('button', { class: 'btn primary', onclick: () => launch(spec) }, 'Exécuter maintenant')));
    } else if (exp.result) {
      const res = exp.result;
      const points = pointStats(model, spec, res);
      const verdict = evaluateCriterion(model, spec, res, points);
      const imp = impact(model, spec, res);
      const best = bestPoint(points, spec.objective.metric, spec.objective.goal);

      parts.push(h('div', { class: 'grid-2' },
        card('Conclusion',
          verdict ? h('div', { class: `verdict ${verdict.status}` }, h('strong', null, verdict.headline), h('p', null, verdict.detail))
            : h('p', { class: 'muted' }, 'Aucun critère de succès formulé.'),
          best && spec.design.kind !== 'single' && spec.design.kind !== 'montecarlo'
            ? h('div', { class: 'best' },
              h('span', { class: 'kpi-label' }, `Meilleure configuration — ${spec.objective.goal === 'max' ? 'max.' : 'min.'} ${metricLabel(model, spec.objective.metric, false)}`),
              h('strong', null, `${fmt(best.metrics[spec.objective.metric].mean)} ${model.metrics.find((m) => m.key === spec.objective.metric)!.unit}`),
              paramsList(model, spec, best.params))
            : null),
        card('Impact de la campagne virtuelle',
          h('div', { class: 'kpis compact' },
            kpi('Simulations', imp.virtualRuns.toLocaleString('fr-FR'), `en ${imp.computeSeconds.toLocaleString('fr-FR', { maximumFractionDigits: 2 })} s de calcul`),
            kpi('Essais physiques recommandés', String(imp.physicalRecommended), 'confirmation au point retenu'),
            kpi('Coût évité', euros(imp.costAvoided), `${imp.avoidedRuns.toLocaleString('fr-FR')} essais × ${euros(model.physical.costPerRun)}`, 'good'),
            kpi('Temps de laboratoire évité', hours(imp.hoursAvoided), undefined, 'good')),
          h('p', { class: 'muted' }, `Référence : ${model.physical.note}. `, res.failures ? `${res.failures} simulation(s) en échec exclue(s).` : ''))));

      const analysisBox = h('div');
      const renderAnalysis = () => analysisBox.replaceChildren(analysisSection(model, exp, metric, points));
      parts.push(h('div', { class: 'analysis-bar' }, metricSelect(model, metric, (v) => { metric = v; renderAnalysis(); })));
      renderAnalysis();
      parts.push(analysisBox);

      const shown = res.runs.slice(0, 200);
      const varied = variedFactors(spec);
      parts.push(card('Données brutes',
        h('details', null, h('summary', null, `Afficher ${shown.length} des ${res.runs.length.toLocaleString('fr-FR')} simulations`),
          table(['#', 'Rép.', ...varied.map((k) => paramLabel(model, k)), ...model.metrics.map((m) => metricLabel(model, m.key))],
            shown.map((r) => [String(r.point + 1), String(r.replicate + 1), ...varied.map((k) => fmt(r.params[k])), ...model.metrics.map((m) => fmt(r.metrics[m.key]))]),
            { numeric: Array.from({ length: 2 + varied.length + model.metrics.length }, (_, i) => i), className: 'dense' }))));
    }

    const notes = h('textarea', { rows: 4, placeholder: 'Observations, interprétation, décisions, essais physiques à programmer…' }, exp.notes ?? '');
    notes.addEventListener('change', async () => {
      const cur = store.get(id);
      if (cur) { await store.save({ ...cur, notes: notes.value }); toast('Notes enregistrées'); }
    });
    parts.push(card('Notes du cahier de laboratoire', notes));
    root.replaceChildren(...parts.filter(Boolean) as HTMLElement[]);
  };

  draw();
  const unsubStore = store.subscribe(() => {
    const e = store.get(id);
    if (!e || e.status !== lastStatus) draw();
  });
  const unsubProg = onProgress((pid) => {
    if (pid !== id) return;
    const p = getProgress(id);
    const bar = root.querySelector<HTMLElement>('#prog-bar');
    const text = root.querySelector<HTMLElement>('#prog-text');
    if (p && bar && text) {
      bar.style.width = `${(100 * p.done) / p.total}%`;
      text.textContent = `${p.done.toLocaleString('fr-FR')} / ${p.total.toLocaleString('fr-FR')} simulations`;
    }
  });
  return Object.assign(root, { cleanup: () => { unsubStore(); unsubProg(); } });
}
