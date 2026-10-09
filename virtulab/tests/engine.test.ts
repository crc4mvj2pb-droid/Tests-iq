import { describe, expect, it } from 'vitest';
import { anova2, bestPoint, evaluateCriterion, impact, pointStats, refinedOptimum, sensitivity } from '../src/engine/analysis';
import { executeExperiment } from '../src/engine/execute';
import { buildPlan, levels } from '../src/engine/plan';
import { TEMPLATES } from '../src/engine/templates';
import type { ExperimentSpec } from '../src/engine/types';
import { getModel } from '../src/models';
import { defaults } from '../src/models/types';

function spec(partial: Partial<ExperimentSpec>): ExperimentSpec {
  const model = getModel(partial.modelId ?? 'projectile');
  return {
    id: 't', name: 't', hypothesis: '', createdAt: 0, objective: { metric: model.metrics[0].key, goal: 'max' },
    modelId: model.id, base: defaults(model), design: { kind: 'single' }, replicates: 1, measurementNoise: false, seed: 1,
    ...partial,
  };
}

describe('plans d\'expériences', () => {
  it('niveaux linéaires et logarithmiques', () => {
    expect(levels({ key: 'a', from: 0, to: 10, levels: 3, scale: 'lin' })).toEqual([0, 5, 10]);
    const lg = levels({ key: 'a', from: 1, to: 100, levels: 3, scale: 'log' });
    expect(lg[1]).toBeCloseTo(10, 10);
  });

  it('factoriel complet = produit des niveaux', () => {
    const s = spec({ design: { kind: 'factorial', factors: [
      { key: 'angle', from: 20, to: 60, levels: 4, scale: 'lin' }, { key: 'v0', from: 10, to: 50, levels: 3, scale: 'lin' }] } });
    expect(buildPlan(getModel('projectile'), s)).toHaveLength(12);
  });

  it('hypercube latin : une valeur par strate pour chaque facteur', () => {
    const n = 20;
    const s = spec({ design: { kind: 'lhs', samples: n, factors: [{ key: 'angle', from: 10, to: 80 }, { key: 'v0', from: 10, to: 50 }] } });
    const plan = buildPlan(getModel('projectile'), s);
    const strata = plan.map((p) => Math.floor(((p.params.angle - 10) / 70) * n)).sort((a, b) => a - b);
    expect(strata).toEqual(Array.from({ length: n }, (_, i) => i));
  });

  it('Monte Carlo respecte l\'écart-type relatif demandé', () => {
    const s = spec({ modelId: 'pk', design: { kind: 'montecarlo', samples: 4000, uncertain: [{ key: 'cl', relSd: 0.2 }] } });
    const xs = buildPlan(getModel('pk'), s).map((p) => p.params.cl);
    const m = xs.reduce((a, b) => a + b, 0) / xs.length;
    const sd = Math.sqrt(xs.reduce((a, b) => a + (b - m) ** 2, 0) / (xs.length - 1));
    expect(m).toBeCloseTo(5, 0);
    expect(sd / m).toBeGreaterThan(0.18);
    expect(sd / m).toBeLessThan(0.22);
  });
});

describe('exécution et analyse', () => {
  it('reproductible à graine identique, différente sinon', () => {
    const s = spec({ replicates: 5, measurementNoise: true, seed: 123 });
    const a = executeExperiment(s).runs.map((r) => r.metrics.range);
    const b = executeExperiment(s).runs.map((r) => r.metrics.range);
    const c = executeExperiment({ ...s, seed: 124 }).runs.map((r) => r.metrics.range);
    expect(a).toEqual(b);
    expect(a).not.toEqual(c);
    expect(new Set(a).size).toBe(5);
  });

  it('balayage d\'angle : optimum interpolé sous 45° avec traînée', () => {
    const s = spec({ base: { ...defaults(getModel('projectile')), h0: 0 }, design: { kind: 'sweep', factor: { key: 'angle', from: 20, to: 60, levels: 21, scale: 'lin' } } });
    const res = executeExperiment(s);
    const pts = pointStats(getModel('projectile'), s, res);
    const opt = refinedOptimum(pts.map((p) => p.params.angle), pts.map((p) => p.metrics.range.mean), 'max');
    expect(opt).toBeDefined();
    expect(opt!.x).toBeGreaterThan(30);
    expect(opt!.x).toBeLessThan(45);
  });

  it('test d\'hypothèse sur réplicats bruités', () => {
    const s = spec({ replicates: 10, measurementNoise: true, criterion: { metric: 'range', op: '>', threshold: 30 } });
    const model = getModel('projectile');
    const res = executeExperiment(s);
    expect(evaluateCriterion(model, s, res, pointStats(model, s, res))?.status).toBe('supported');
    const s2 = { ...s, criterion: { metric: 'range', op: '>' as const, threshold: 80 } };
    expect(evaluateCriterion(model, s2, res, pointStats(model, s2, res))?.status).toBe('rejected');
  });

  it('ANOVA : décomposition complète de la variance', () => {
    const model = getModel('projectile');
    const s = spec({ replicates: 3, measurementNoise: true, design: { kind: 'factorial', factors: [
      { key: 'angle', from: 20, to: 70, levels: 4, scale: 'lin' }, { key: 'v0', from: 10, to: 50, levels: 3, scale: 'lin' }] } });
    const rows = anova2(s, executeExperiment(s), 'range', ['angle', 'v0']);
    expect(rows.reduce((a, r) => a + r.share, 0)).toBeCloseTo(1, 8);
    expect(rows.find((r) => r.source === 'v0')!.p!).toBeLessThan(1e-6);
    expect(bestPoint(pointStats(model, s, executeExperiment(s)), 'range', 'max')!.params.v0).toBe(50);
  });

  it('sensibilité : le facteur dominant est identifié', () => {
    const s = spec({ design: { kind: 'lhs', samples: 150, factors: [{ key: 'v0', from: 10, to: 60 }, { key: 'wind', from: -1, to: 1 }] } });
    const sens = sensitivity(s, executeExperiment(s), 'range');
    expect(sens.rows[0].factor).toBe('v0');
    expect(sens.rows[0].spearman).toBeGreaterThan(0.95);
  });

  it('chaque expérience type s\'exécute et produit un impact positif', () => {
    for (const t of TEMPLATES) {
      const built = t.build();
      const s: ExperimentSpec = { ...built, id: 't', createdAt: 0, seed: 1 };
      const model = getModel(s.modelId);
      const res = executeExperiment(s);
      expect(res.failures, t.title).toBe(0);
      expect(impact(model, s, res).costAvoided, t.title).toBeGreaterThan(0);
      expect(evaluateCriterion(model, s, res, pointStats(model, s, res)), t.title).toBeDefined();
    }
  }, 60_000);
});
