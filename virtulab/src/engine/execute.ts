import { Rng } from '../core/rng';
import { getModel } from '../models';
import type { ExperimentResult, ExperimentSpec, Run } from './types';
import { buildPlan } from './plan';

const MAX_TRACES = 24;

/**
 * Exécute un plan d'expériences complet. Fonction pure et déterministe pour une
 * graine donnée ; utilisée par le Web Worker et par les tests.
 */
export function executeExperiment(spec: ExperimentSpec, onProgress?: (done: number, total: number) => void): ExperimentResult {
  const t0 = performance.now();
  const model = getModel(spec.modelId);
  const plan = buildPlan(model, spec);
  const reps = Math.max(1, Math.round(spec.replicates));
  const total = plan.length * reps;
  const rng = new Rng(spec.seed);
  const runs: Run[] = [];
  const traces: ExperimentResult['traces'] = [];
  const traceEvery = Math.max(1, Math.ceil(plan.length / MAX_TRACES));
  let failures = 0;
  let done = 0;
  let lastReport = 0;

  plan.forEach((pt, i) => {
    let out;
    try {
      out = model.simulate(pt.params);
    } catch {
      failures++;
      done += reps;
      return;
    }
    if (i % traceEvery === 0) traces.push({ point: i, label: pt.label, output: out });
    for (let r = 0; r < reps; r++) {
      const noisy: Record<string, number> = {};
      const rr = rng.fork(i * 1000 + r);
      for (const m of model.metrics) {
        const v = out.metrics[m.key];
        let x = spec.measurementNoise && m.noise > 0 ? v * (1 + rr.normal(0, m.noise)) : v;
        if (m.unit === '%') x = Math.min(100, Math.max(0, x)); // un instrument ne lit pas 103 %
        noisy[m.key] = x;
      }
      runs.push({ point: i, replicate: r, params: pt.params, metrics: noisy });
      done++;
    }
    const now = performance.now();
    if (onProgress && (now - lastReport > 50 || done === total)) {
      lastReport = now;
      onProgress(done, total);
    }
  });

  return { runs, traces, durationMs: performance.now() - t0, completedAt: Date.now(), failures };
}
