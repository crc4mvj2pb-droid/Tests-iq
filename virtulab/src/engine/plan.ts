import { Rng } from '../core/rng';
import type { Model, Params } from '../models/types';
import type { ExperimentSpec, FactorRange } from './types';

export interface PlanPoint {
  params: Params;
  label: string;
}

export function levels(f: FactorRange): number[] {
  const n = Math.max(2, Math.round(f.levels));
  return Array.from({ length: n }, (_, i) => {
    const u = i / (n - 1);
    return f.scale === 'log' && f.from > 0 && f.to > 0
      ? Math.exp(Math.log(f.from) + u * (Math.log(f.to) - Math.log(f.from)))
      : f.from + u * (f.to - f.from);
  });
}

function clampToModel(model: Model, p: Params): Params {
  for (const def of model.params) {
    if (p[def.key] < def.min) p[def.key] = def.min;
    if (p[def.key] > def.max) p[def.key] = def.max;
    if (def.step === 1) p[def.key] = Math.round(p[def.key]);
  }
  return p;
}

/** Génère les points d'un plan d'expériences (sans les réplicats). */
export function buildPlan(model: Model, spec: ExperimentSpec): PlanPoint[] {
  const d = spec.design;
  const base = spec.base;
  const fmt = (key: string, v: number) => `${model.params.find((p) => p.key === key)?.label ?? key} = ${+v.toPrecision(4)}`;
  switch (d.kind) {
    case 'single':
      return [{ params: { ...base }, label: 'Point nominal' }];
    case 'sweep':
      return levels(d.factor).map((v) => ({ params: clampToModel(model, { ...base, [d.factor.key]: v }), label: fmt(d.factor.key, v) }));
    case 'factorial': {
      const [f1, f2] = d.factors;
      const out: PlanPoint[] = [];
      for (const a of levels(f1)) for (const b of levels(f2)) {
        out.push({ params: clampToModel(model, { ...base, [f1.key]: a, [f2.key]: b }), label: `${fmt(f1.key, a)} · ${fmt(f2.key, b)}` });
      }
      return out;
    }
    case 'montecarlo': {
      const rng = new Rng(spec.seed ^ 0x51ed);
      return Array.from({ length: d.samples }, (_, i) => {
        const p = { ...base };
        // Loi log-normale : garde les grandeurs physiques positives, écart-type relatif ≈ relSd.
        for (const u of d.uncertain) {
          const s = Math.sqrt(Math.log(1 + u.relSd ** 2));
          const v = base[u.key] === 0 ? rng.normal(0, u.relSd) : base[u.key] * Math.exp(rng.normal(-0.5 * s * s, s));
          p[u.key] = v;
        }
        return { params: clampToModel(model, p), label: `Tirage ${i + 1}` };
      });
    }
    case 'lhs': {
      const rng = new Rng(spec.seed ^ 0x1a7e);
      const n = d.samples;
      const columns = d.factors.map((f) => {
        const strata = Array.from({ length: n }, (_, i) => (i + rng.next()) / n);
        for (let i = n - 1; i > 0; i--) {
          const j = Math.floor(rng.next() * (i + 1));
          [strata[i], strata[j]] = [strata[j], strata[i]];
        }
        return strata.map((u) => f.from + u * (f.to - f.from));
      });
      return Array.from({ length: n }, (_, i) => {
        const p = { ...base };
        d.factors.forEach((f, j) => (p[f.key] = columns[j][i]));
        return { params: clampToModel(model, p), label: `Échantillon ${i + 1}` };
      });
    }
  }
}

export function totalRuns(model: Model, spec: ExperimentSpec): number {
  return buildPlan(model, spec).length * Math.max(1, spec.replicates);
}
