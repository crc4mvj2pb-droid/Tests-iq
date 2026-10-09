export type Discipline =
  | 'Physique'
  | 'Chimie'
  | 'Épidémiologie'
  | 'Pharmacologie'
  | 'Ingénierie thermique'
  | 'Écologie'
  | 'Bio-procédés';

export type Params = Record<string, number>;

export interface ParamDef {
  key: string;
  label: string;
  unit: string;
  min: number;
  max: number;
  default: number;
  step?: number;
  /** Échelle logarithmique conseillée pour les balayages. */
  log?: boolean;
  /** Paramètre « de contrôle » (pilotable) vs propriété physique incertaine. */
  kind: 'control' | 'property';
  help?: string;
}

export interface MetricDef {
  key: string;
  label: string;
  unit: string;
  digits?: number;
  /** Bruit de mesure instrumental relatif (écart-type), appliqué si activé. */
  noise: number;
  help?: string;
}

export interface SeriesDef {
  key: string;
  label: string;
  unit: string;
}

export interface PlotDef {
  title: string;
  /** 't' pour le temps, sinon une clé de série. */
  x: string;
  xLabel: string;
  ys: string[];
  yLabel: string;
}

export interface SimOutput {
  t: number[];
  series: Record<string, number[]>;
  metrics: Record<string, number>;
}

export interface ValidationCase {
  name: string;
  /** Description de la référence (solution analytique, loi connue…). */
  reference: string;
  run(): { expected: number; obtained: number };
  /** Erreur relative tolérée. */
  tolerance: number;
}

export interface Model {
  id: string;
  name: string;
  discipline: Discipline;
  icon: string;
  summary: string;
  description: string;
  equations: string[];
  assumptions: string[];
  references: string[];
  timeUnit: string;
  params: ParamDef[];
  metrics: MetricDef[];
  series: SeriesDef[];
  plots: PlotDef[];
  /** Coût et durée estimés d'une expérience physique équivalente. */
  physical: { costPerRun: number; hoursPerRun: number; note: string };
  simulate(p: Params): SimOutput;
  validation: ValidationCase[];
}

export function defaults(model: Model): Params {
  return Object.fromEntries(model.params.map((p) => [p.key, p.default]));
}

export function argMax(xs: number[]): number {
  let best = 0;
  for (let i = 1; i < xs.length; i++) if (xs[i] > xs[best]) best = i;
  return best;
}

/** Max/min sans décomposition d'arguments (sûr pour les très longues séries). */
export function maxOf(xs: number[]): number {
  let m = -Infinity;
  for (const x of xs) if (x > m) m = x;
  return m;
}

export function minOf(xs: number[]): number {
  let m = Infinity;
  for (const x of xs) if (x < m) m = x;
  return m;
}
