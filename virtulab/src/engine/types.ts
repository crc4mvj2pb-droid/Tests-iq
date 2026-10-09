import type { Params, SimOutput } from '../models/types';

export interface FactorRange {
  key: string;
  from: number;
  to: number;
  levels: number;
  scale: 'lin' | 'log';
}

export type Design =
  | { kind: 'single' }
  | { kind: 'sweep'; factor: FactorRange }
  | { kind: 'factorial'; factors: [FactorRange, FactorRange] }
  | { kind: 'montecarlo'; samples: number; uncertain: { key: string; relSd: number }[] }
  | { kind: 'lhs'; samples: number; factors: { key: string; from: number; to: number }[] };

export type DesignKind = Design['kind'];

/** Critère de succès formulé avant l'expérience (hypothèse testable). */
export interface Criterion {
  metric: string;
  op: '>' | '<';
  threshold: number;
}

export interface ExperimentSpec {
  id: string;
  name: string;
  hypothesis: string;
  criterion?: Criterion;
  /** Métrique à optimiser et sens. */
  objective: { metric: string; goal: 'max' | 'min' };
  modelId: string;
  base: Params;
  design: Design;
  replicates: number;
  measurementNoise: boolean;
  seed: number;
  createdAt: number;
}

export interface Run {
  /** Indice du point du plan (les réplicats partagent le même indice). */
  point: number;
  replicate: number;
  params: Params;
  metrics: Record<string, number>;
}

export interface ExperimentResult {
  runs: Run[];
  /** Courbes conservées pour un sous-ensemble de runs (affichage). */
  traces: { point: number; label: string; output: SimOutput }[];
  durationMs: number;
  completedAt: number;
  failures: number;
}

export interface Experiment {
  spec: ExperimentSpec;
  result?: ExperimentResult;
  status: 'draft' | 'running' | 'done' | 'error';
  error?: string;
  notes?: string;
}

export const DESIGN_LABELS: Record<DesignKind, { name: string; description: string }> = {
  single: { name: 'Essai unique', description: 'Un point de fonctionnement, avec réplicats pour estimer la variabilité de mesure.' },
  sweep: { name: 'Balayage paramétrique', description: 'Variation d\'un facteur sur une plage pour obtenir une courbe de réponse.' },
  factorial: { name: 'Plan factoriel complet 2 facteurs', description: 'Grille de combinaisons de deux facteurs : effets principaux et interaction.' },
  montecarlo: { name: 'Propagation d\'incertitudes (Monte Carlo)', description: 'Paramètres incertains tirés aléatoirement : distribution des résultats et risques.' },
  lhs: { name: 'Exploration & optimisation (hypercube latin)', description: 'Échantillonnage stratifié de plusieurs facteurs : sensibilité et meilleur point.' },
};
