import { maxOf, minOf, type Model, type Params, type SimOutput } from './types';

const NODES = 41;

/** Résolution d'un système tridiagonal (algorithme de Thomas). */
function thomas(a: number[], b: number[], c: number[], d: number[]): number[] {
  const n = d.length;
  const cp = new Array(n), dp = new Array(n), x = new Array(n);
  cp[0] = c[0] / b[0];
  dp[0] = d[0] / b[0];
  for (let i = 1; i < n; i++) {
    const m = b[i] - a[i] * cp[i - 1];
    cp[i] = c[i] / m;
    dp[i] = (d[i] - a[i] * dp[i - 1]) / m;
  }
  x[n - 1] = dp[n - 1];
  for (let i = n - 2; i >= 0; i--) x[i] = dp[i] - cp[i] * x[i + 1];
  return x;
}

export function uValue(p: Params): number {
  return 1 / (1 / p.hIn + p.thickness / 100 / p.k + 1 / p.hOut);
}

function simulate(p: Params): SimOutput {
  const L = p.thickness / 100;
  const dx = L / (NODES - 1);
  const rc = p.density * p.cp;
  const tEnd = p.duration * 3600;
  const steps = Math.max(2000, Math.ceil(tEnd / 60));
  const dt = tEnd / steps;
  const tExt = (time: number) => p.tOut + p.swing * Math.sin((2 * Math.PI * (time / 3600 - 9)) / 24); // max vers 15 h

  let T = new Array(NODES).fill(p.tInit);
  const a = new Array(NODES).fill(0), b = new Array(NODES).fill(0), c = new Array(NODES).fill(0), d = new Array(NODES).fill(0);
  const fo = (p.k * dt) / (rc * dx * dx);
  const every = Math.max(1, Math.floor(steps / 1000));
  const t: number[] = [0], sIn: number[] = [T[0]], sOut: number[] = [T[NODES - 1]], mid: number[] = [T[(NODES - 1) / 2]];
  const ext: number[] = [tExt(0)], flux: number[] = [p.hIn * (p.tIn - T[0])];
  let energy = 0;

  for (let s = 1; s <= steps; s++) {
    const time = s * dt;
    const te = tExt(time);
    // Nœud 0 (surface intérieure, demi-maille) : convection avec l'ambiance intérieure.
    const bi = (2 * p.hIn * dt) / (rc * dx);
    b[0] = 1 + 2 * fo + bi; c[0] = -2 * fo; d[0] = T[0] + bi * p.tIn;
    for (let i = 1; i < NODES - 1; i++) { a[i] = -fo; b[i] = 1 + 2 * fo; c[i] = -fo; d[i] = T[i]; }
    const be = (2 * p.hOut * dt) / (rc * dx);
    a[NODES - 1] = -2 * fo; b[NODES - 1] = 1 + 2 * fo + be; d[NODES - 1] = T[NODES - 1] + be * te;
    T = thomas(a, b, c, d);
    const q = p.hIn * (p.tIn - T[0]); // W/m² entrant dans la paroi depuis l'intérieur = pertes
    energy += q * dt;
    if (s % every === 0 || s === steps) {
      t.push(time / 3600);
      sIn.push(T[0]); sOut.push(T[NODES - 1]); mid.push(T[(NODES - 1) / 2]);
      ext.push(te); flux.push(q);
    }
  }

  // Analyse du dernier cycle de 24 h : flux moyen, amortissement et déphasage.
  const last = t.findIndex((h) => h >= t[t.length - 1] - 24);
  const win = (xs: number[]) => xs.slice(last);
  const wt = win(t), wIn = win(sIn), wExt = win(ext), wFlux = win(flux);
  const avgFlux = wFlux.reduce((acc, v) => acc + v, 0) / wFlux.length;
  const amp = (xs: number[]) => (maxOf(xs) - minOf(xs)) / 2;
  const tPeak = (xs: number[]) => wt[xs.indexOf(minOf(xs))];
  let lag = p.swing > 0 ? tPeak(wIn) - tPeak(wExt) : 0;
  if (lag < 0) lag += 24;

  return {
    t,
    series: { sIn, sOut, mid, ext, flux },
    metrics: {
      avgFlux,
      uValue: uValue(p),
      heatLoss: energy / 3.6e6,
      minSurface: minOf(wIn),
      decrement: p.swing > 0 ? amp(wIn) / p.swing : 0,
      timeLag: lag,
    },
  };
}

const base: Params = {
  thickness: 20, k: 1.75, density: 2300, cp: 880, tIn: 20, tOut: 2, swing: 6, hIn: 7.7, hOut: 25, tInit: 15, duration: 120,
};

export const wall: Model = {
  id: 'wall',
  name: 'Transfert thermique dans une paroi de bâtiment',
  discipline: 'Ingénierie thermique',
  icon: '🧱',
  summary: 'Conduction transitoire 1D avec cycle jour/nuit : déperditions, inertie, déphasage thermique.',
  description:
    'Résout l\'équation de la chaleur dans l\'épaisseur d\'une paroi par différences finies implicites (inconditionnellement ' +
    'stables), avec échanges convectifs-radiatifs sur les deux faces et une température extérieure sinusoïdale. ' +
    'Compare des matériaux (béton, brique, bois, isolants) sur les pertes, le confort et l\'inertie, sans construire ' +
    'de cellules d\'essai en chambre climatique.',
  equations: [
    'ρ·cp·∂T/∂t = k·∂²T/∂x²',
    '−k·∂T/∂x|₀ = hᵢ·(Tᵢₙₜ − T(0)),  −k·∂T/∂x|L = hₑ·(T(L) − Tₑₓₜ(t))',
    'Tₑₓₜ(t) = T̄ₑₓₜ + A·sin(2π(t − 9 h)/24 h)',
    'U = 1 / (1/hᵢ + e/k + 1/hₑ)',
  ],
  assumptions: [
    'Paroi homogène, propriétés constantes, transfert unidimensionnel',
    'Coefficients d\'échange superficiels constants (Rsi, Rse normalisés)',
    'Pas de rayonnement solaire ni de transfert d\'humidité',
  ],
  references: ['Incropera, Fundamentals of Heat and Mass Transfer', 'NF EN ISO 13786 — Caractéristiques thermiques dynamiques'],
  timeUnit: 'h',
  params: [
    { key: 'thickness', label: 'Épaisseur', unit: 'cm', min: 2, max: 60, default: base.thickness, kind: 'control' },
    { key: 'k', label: 'Conductivité thermique λ', unit: 'W/(m·K)', min: 0.02, max: 50, default: base.k, log: true, step: 0.01, kind: 'control', help: 'Béton 1,75 · brique 0,8 · bois 0,13 · laine minérale 0,035' },
    { key: 'density', label: 'Masse volumique', unit: 'kg/m³', min: 15, max: 8000, default: base.density, log: true, kind: 'control' },
    { key: 'cp', label: 'Capacité thermique massique', unit: 'J/(kg·K)', min: 400, max: 2500, default: base.cp, kind: 'control' },
    { key: 'tIn', label: 'Température intérieure', unit: '°C', min: 10, max: 30, default: base.tIn, kind: 'control' },
    { key: 'tOut', label: 'Température extérieure moyenne', unit: '°C', min: -25, max: 40, default: base.tOut, kind: 'property' },
    { key: 'swing', label: 'Amplitude jour/nuit', unit: 'K', min: 0, max: 15, default: base.swing, kind: 'property' },
    { key: 'hIn', label: 'Coefficient d\'échange intérieur', unit: 'W/(m²·K)', min: 2, max: 25, default: base.hIn, step: 0.1, kind: 'property' },
    { key: 'hOut', label: 'Coefficient d\'échange extérieur', unit: 'W/(m²·K)', min: 5, max: 100, default: base.hOut, kind: 'property' },
    { key: 'tInit', label: 'Température initiale de la paroi', unit: '°C', min: -10, max: 30, default: base.tInit, kind: 'property' },
    { key: 'duration', label: 'Durée simulée', unit: 'h', min: 24, max: 720, default: base.duration, kind: 'control' },
  ],
  metrics: [
    { key: 'avgFlux', label: 'Flux moyen (dernières 24 h)', unit: 'W/m²', digits: 2, noise: 0.03 },
    { key: 'uValue', label: 'Coefficient U', unit: 'W/(m²·K)', digits: 3, noise: 0 },
    { key: 'heatLoss', label: 'Déperditions cumulées', unit: 'kWh/m²', digits: 2, noise: 0.03 },
    { key: 'minSurface', label: 'T surface intérieure min.', unit: '°C', digits: 2, noise: 0.002 },
    { key: 'decrement', label: 'Facteur d\'amortissement', unit: '—', digits: 3, noise: 0.03 },
    { key: 'timeLag', label: 'Déphasage thermique', unit: 'h', digits: 1, noise: 0.03 },
  ],
  series: [
    { key: 'ext', label: 'Air extérieur', unit: '°C' },
    { key: 'sOut', label: 'Surface extérieure', unit: '°C' },
    { key: 'mid', label: 'Cœur de paroi', unit: '°C' },
    { key: 'sIn', label: 'Surface intérieure', unit: '°C' },
    { key: 'flux', label: 'Flux de chaleur', unit: 'W/m²' },
  ],
  plots: [
    { title: 'Températures', x: 't', xLabel: 'Temps (h)', ys: ['ext', 'sOut', 'mid', 'sIn'], yLabel: '°C' },
    { title: 'Flux à travers la face intérieure', x: 't', xLabel: 'Temps (h)', ys: ['flux'], yLabel: 'W/m²' },
  ],
  physical: { costPerRun: 6500, hoursPerRun: 168, note: 'Échantillon de paroi en chambre climatique / boîte chaude gardée (NF EN ISO 8990)' },
  simulate,
  validation: [
    {
      name: 'Flux en régime permanent',
      reference: 'q = U·(Tᵢₙₜ − Tₑₓₜ) (loi de Fourier en série)',
      tolerance: 1e-3,
      run: () => {
        const p: Params = { ...base, swing: 0, duration: 400 };
        return { expected: uValue(p) * (p.tIn - p.tOut), obtained: simulate(p).metrics.avgFlux };
      },
    },
  ],
};
