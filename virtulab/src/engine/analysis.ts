import {
  fCdf, mean, ols, oneSampleTTest, spearman, studentTCdf, summarize, wilson, type Summary,
} from '../core/stats';
import type { Model, Params } from '../models/types';
import { buildPlan } from './plan';
import type { Criterion, ExperimentResult, ExperimentSpec, Run } from './types';

export interface PointStats {
  point: number;
  label: string;
  params: Params;
  metrics: Record<string, Summary>;
}

export interface CriterionVerdict {
  status: 'supported' | 'rejected' | 'inconclusive';
  headline: string;
  detail: string;
}

export interface Sensitivity {
  factor: string;
  src: number;
  spearman: number;
}

export interface AnovaRow {
  source: string;
  ss: number;
  df: number;
  share: number;
  f?: number;
  p?: number;
}

export interface Impact {
  virtualRuns: number;
  physicalRecommended: number;
  avoidedRuns: number;
  costAvoided: number;
  hoursAvoided: number;
  computeSeconds: number;
}

/** Facteurs que le plan fait varier. */
export function variedFactors(spec: ExperimentSpec): string[] {
  const d = spec.design;
  switch (d.kind) {
    case 'single': return [];
    case 'sweep': return [d.factor.key];
    case 'factorial': return d.factors.map((f) => f.key);
    case 'montecarlo': return d.uncertain.map((u) => u.key);
    case 'lhs': return d.factors.map((f) => f.key);
  }
}

export function pointStats(model: Model, spec: ExperimentSpec, result: ExperimentResult): PointStats[] {
  const plan = buildPlan(model, spec);
  const byPoint = new Map<number, Run[]>();
  for (const r of result.runs) {
    if (!byPoint.has(r.point)) byPoint.set(r.point, []);
    byPoint.get(r.point)!.push(r);
  }
  return [...byPoint.entries()].sort((a, b) => a[0] - b[0]).map(([point, runs]) => ({
    point,
    label: plan[point]?.label ?? `Point ${point + 1}`,
    params: runs[0].params,
    metrics: Object.fromEntries(model.metrics.map((m) => [m.key, summarize(runs.map((r) => r.metrics[m.key]))])),
  }));
}

export function bestPoint(points: PointStats[], metric: string, goal: 'max' | 'min'): PointStats | undefined {
  let best: PointStats | undefined;
  for (const p of points) {
    const v = p.metrics[metric]?.mean;
    if (!Number.isFinite(v)) continue;
    if (!best || (goal === 'max' ? v > best.metrics[metric].mean : v < best.metrics[metric].mean)) best = p;
  }
  return best;
}

/** Optimum interpolé d'un balayage par parabole sur le meilleur niveau et ses voisins. */
export function refinedOptimum(xs: number[], ys: number[], goal: 'max' | 'min'): { x: number; y: number } | undefined {
  if (xs.length < 3) return undefined;
  let i = 0;
  for (let k = 1; k < ys.length; k++) if (goal === 'max' ? ys[k] > ys[i] : ys[k] < ys[i]) i = k;
  if (i === 0 || i === xs.length - 1) return undefined; // optimum en bordure : élargir la plage
  const [x0, x1, x2] = [xs[i - 1], xs[i], xs[i + 1]];
  const [y0, y1, y2] = [ys[i - 1], ys[i], ys[i + 1]];
  const den = (x0 - x1) * (x0 - x2) * (x1 - x2);
  const a = (x2 * (y1 - y0) + x1 * (y0 - y2) + x0 * (y2 - y1)) / den;
  const b = (x2 * x2 * (y0 - y1) + x1 * x1 * (y2 - y0) + x0 * x0 * (y1 - y2)) / den;
  if (a === 0) return undefined;
  const xv = -b / (2 * a);
  if (xv < x0 || xv > x2) return undefined;
  const c = y1 - a * x1 * x1 - b * x1;
  return { x: xv, y: a * xv * xv + b * xv + c };
}

const opText = (c: Criterion) => (c.op === '>' ? 'supérieur à' : 'inférieur à');

export function evaluateCriterion(
  model: Model, spec: ExperimentSpec, result: ExperimentResult, points: PointStats[],
): CriterionVerdict | undefined {
  const c = spec.criterion;
  if (!c) return undefined;
  const def = model.metrics.find((m) => m.key === c.metric);
  if (!def) return undefined;
  const values = result.runs.map((r) => r.metrics[c.metric]).filter(Number.isFinite);
  const ok = (v: number) => (c.op === '>' ? v > c.threshold : v < c.threshold);
  const unit = def.unit === '—' || def.unit === '0/1' ? '' : ` ${def.unit}`;
  const target = `${def.label} ${opText(c)} ${c.threshold}${unit}`;

  if (spec.design.kind === 'single') {
    const s = summarize(values);
    if (values.length < 2 || s.sd === 0) {
      return ok(s.mean)
        ? { status: 'supported', headline: `Hypothèse soutenue : ${target}`, detail: `Valeur simulée ${fmt(s.mean)}${unit} (résultat déterministe, sans bruit de mesure).` }
        : { status: 'rejected', headline: `Hypothèse non soutenue : ${target}`, detail: `Valeur simulée ${fmt(s.mean)}${unit} (résultat déterministe).` };
    }
    const t = oneSampleTTest(values, c.threshold);
    // p unilatéral dans le sens de l'hypothèse.
    const pOne = c.op === '>' ? 1 - studentTCdf(t.t, t.df) : studentTCdf(t.t, t.df);
    const detail = `Moyenne ${fmt(s.mean)}${unit}, IC95 % [${fmt(s.ciLow)} ; ${fmt(s.ciHigh)}], n = ${s.n}, test t unilatéral p = ${fmtP(pOne)}.`;
    if (pOne < 0.05) return { status: 'supported', headline: `Hypothèse soutenue (p < 0,05) : ${target}`, detail };
    if (pOne > 0.95) return { status: 'rejected', headline: `Hypothèse rejetée : ${target}`, detail };
    return { status: 'inconclusive', headline: 'Résultat non concluant — augmenter le nombre de réplicats', detail };
  }

  if (spec.design.kind === 'montecarlo') {
    const k = values.filter(ok).length;
    const [lo, hi] = wilson(k, values.length);
    const prob = k / values.length;
    const detail = `Probabilité estimée ${pct(prob)} (IC95 % ${pct(lo)} – ${pct(hi)}) sur ${values.length} tirages.`;
    if (lo >= 0.95) return { status: 'supported', headline: `Critère satisfait avec une confiance ≥ 95 % : ${target}`, detail };
    if (hi < 0.5) return { status: 'rejected', headline: `Critère majoritairement non satisfait : ${target}`, detail };
    return { status: 'inconclusive', headline: `Critère satisfait dans ${pct(prob)} des cas : ${target}`, detail: `${detail} Risque résiduel non négligeable.` };
  }

  const good = points.filter((p) => ok(p.metrics[c.metric].mean));
  const share = good.length / points.length;
  const detail = `${good.length} configuration(s) sur ${points.length} satisfont le critère (${pct(share)} du domaine exploré).`;
  if (good.length === 0) return { status: 'rejected', headline: `Aucune configuration ne satisfait : ${target}`, detail };
  return { status: 'supported', headline: `Des configurations satisfont : ${target}`, detail };
}

export function sensitivity(spec: ExperimentSpec, result: ExperimentResult, metric: string): { rows: Sensitivity[]; r2: number } {
  const factors = variedFactors(spec);
  const runs = result.runs.filter((r) => Number.isFinite(r.metrics[metric]));
  if (!factors.length || runs.length < factors.length + 2) return { rows: [], r2: NaN };
  const X = runs.map((r) => factors.map((f) => r.params[f]));
  const y = runs.map((r) => r.metrics[metric]);
  const reg = ols(X, y);
  const rows = factors.map((f, j) => ({ factor: f, src: reg.standardized[j], spearman: spearman(X.map((row) => row[j]), y) }));
  rows.sort((a, b) => Math.abs(b.spearman) - Math.abs(a.spearman));
  return { rows, r2: reg.r2 };
}

/** ANOVA à deux facteurs sur un plan factoriel complet. */
export function anova2(spec: ExperimentSpec, result: ExperimentResult, metric: string, labels: [string, string]): AnovaRow[] {
  if (spec.design.kind !== 'factorial') return [];
  const [fa, fb] = spec.design.factors.map((f) => f.key);
  const runs = result.runs.filter((r) => Number.isFinite(r.metrics[metric]));
  const la = [...new Set(runs.map((r) => r.params[fa]))];
  const lb = [...new Set(runs.map((r) => r.params[fb]))];
  const y = runs.map((r) => r.metrics[metric]);
  const grand = mean(y);
  const meanWhere = (pred: (r: Run) => boolean) => mean(runs.filter(pred).map((r) => r.metrics[metric]));
  const ma = new Map(la.map((a) => [a, meanWhere((r) => r.params[fa] === a)]));
  const mb = new Map(lb.map((b) => [b, meanWhere((r) => r.params[fb] === b)]));
  const cell = new Map<string, number>();
  for (const a of la) for (const b of lb) cell.set(`${a}|${b}`, meanWhere((r) => r.params[fa] === a && r.params[fb] === b));
  let ssA = 0, ssB = 0, ssAB = 0, ssE = 0, ssT = 0;
  for (const r of runs) {
    const a = r.params[fa], b = r.params[fb], v = r.metrics[metric];
    const cm = cell.get(`${a}|${b}`)!;
    ssA += (ma.get(a)! - grand) ** 2;
    ssB += (mb.get(b)! - grand) ** 2;
    ssAB += (cm - ma.get(a)! - mb.get(b)! + grand) ** 2;
    ssE += (v - cm) ** 2;
    ssT += (v - grand) ** 2;
  }
  const dfA = la.length - 1, dfB = lb.length - 1, dfAB = dfA * dfB, dfE = runs.length - la.length * lb.length;
  const rows: AnovaRow[] = [
    { source: labels[0], ss: ssA, df: dfA, share: 0 },
    { source: labels[1], ss: ssB, df: dfB, share: 0 },
    { source: 'Interaction', ss: ssAB, df: dfAB, share: 0 },
  ];
  if (dfE > 0) rows.push({ source: 'Résidu (bruit de mesure)', ss: ssE, df: dfE, share: 0 });
  for (const row of rows) {
    row.share = ssT > 0 ? row.ss / ssT : 0;
    if (dfE > 0 && row.source !== 'Résidu (bruit de mesure)' && ssE > 0) {
      row.f = row.ss / row.df / (ssE / dfE);
      row.p = 1 - fCdf(row.f, row.df, dfE);
    }
  }
  return rows;
}

export function impact(model: Model, spec: ExperimentSpec, result: ExperimentResult): Impact {
  const virtualRuns = result.runs.length;
  // Les essais physiques restent nécessaires pour confirmer : 3 réplicats au point retenu,
  // + 2 essais de bordure lorsque le plan explore un domaine.
  const physicalRecommended = Math.min(virtualRuns, spec.design.kind === 'single' ? 3 : 5);
  const avoidedRuns = Math.max(0, virtualRuns - physicalRecommended);
  return {
    virtualRuns,
    physicalRecommended,
    avoidedRuns,
    costAvoided: avoidedRuns * model.physical.costPerRun,
    hoursAvoided: avoidedRuns * model.physical.hoursPerRun,
    computeSeconds: result.durationMs / 1000,
  };
}

export function fmt(v: number, digits = 4): string {
  if (!Number.isFinite(v)) return '—';
  if (v !== 0 && (Math.abs(v) >= 1e6 || Math.abs(v) < 1e-3)) return v.toExponential(2).replace('.', ',');
  return (+v.toPrecision(digits)).toLocaleString('fr-FR', { maximumFractionDigits: 6 });
}

export function fmtP(p: number): string {
  return p < 1e-4 ? '< 0,0001' : p.toFixed(4).replace('.', ',');
}

export function pct(x: number): string {
  return `${(100 * x).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %`;
}
