import { rk45 } from '../core/ode';
import { maxOf, minOf, type Model, type Params, type SimOutput } from './types';

function simulate(p: Params): SimOutput {
  const q = p.harvest / 100;
  const res = rk45(
    (_t, y, out) => {
      const [N, P] = y;
      const f = (p.attack * N) / (1 + p.attack * p.handling * N); // réponse fonctionnelle de Holling II
      out[0] = p.r * N * (1 - N / p.k) - f * P - q * N;
      out[1] = p.efficiency * f * P - p.mortality * P;
    },
    [p.n0, p.p0],
    { t0: 0, t1: p.duration, rtol: 1e-8, atol: 1e-8, samples: 1000, hmax: 0.25,
      clamp: (y) => { if (y[0] < 0) y[0] = 0; if (y[1] < 0) y[1] = 0; } },
  );
  const [N, P] = res.y;
  const half = Math.floor(N.length / 2);
  const lateN = N.slice(half), lateP = P.slice(half), lateT = res.t.slice(half);
  // Période des cycles : intervalle moyen entre maxima locaux de la proie.
  const peaks: number[] = [];
  const amp = maxOf(lateN) - minOf(lateN);
  for (let i = 1; i < lateN.length - 1; i++) {
    if (lateN[i] > lateN[i - 1] && lateN[i] >= lateN[i + 1] && amp > 1e-3 * Math.max(1, maxOf(lateN))) peaks.push(lateT[i]);
  }
  const period = peaks.length >= 2 ? (peaks[peaks.length - 1] - peaks[0]) / (peaks.length - 1) : 0;
  const minP = minOf(lateP);
  const n = N.length - 1;
  return {
    t: res.t,
    series: { N, P },
    metrics: {
      preyMean: lateN.reduce((s, v) => s + v, 0) / lateN.length,
      preyMin: minOf(lateN),
      preyMax: maxOf(lateN),
      predatorMean: lateP.reduce((s, v) => s + v, 0) / lateP.length,
      predatorMin: minP,
      period,
      coexistence: N[n] > 1 && P[n] > 1 && minP > 0.5 ? 1 : 0,
      harvestYield: q * (lateN.reduce((s, v) => s + v, 0) / lateN.length),
    },
  };
}

const base: Params = {
  r: 1, k: 400, attack: 0.02, handling: 0.1, efficiency: 0.3, mortality: 0.2, n0: 200, p0: 10, harvest: 0, duration: 200,
};

export const ecology: Model = {
  id: 'ecology',
  name: 'Dynamique proies–prédateurs avec prélèvement',
  discipline: 'Écologie',
  icon: '🦊',
  summary: 'Modèle de Rosenzweig–MacArthur : cycles de populations, paradoxe de l\'enrichissement, pêche/chasse durable.',
  description:
    'Proies à croissance logistique, prédateurs à réponse fonctionnelle saturante (Holling II), prélèvement humain ' +
    'proportionnel sur les proies. Explore la stabilité des écosystèmes, l\'apparition de cycles et le risque ' +
    'd\'effondrement des prédateurs, et identifie un taux de prélèvement durable — questions qui demanderaient ' +
    'des décennies de suivi de terrain.',
  equations: [
    'dN/dt = r·N·(1 − N/K) − a·N·P/(1 + a·h·N) − q·N',
    'dP/dt = e·a·N·P/(1 + a·h·N) − m·P',
    'Équilibre : N* = m / (a·(e − m·h))',
  ],
  assumptions: [
    'Populations homogènes et non structurées (âge, espace)',
    'Environnement constant (pas de saisonnalité)',
    'Effort de prélèvement constant',
  ],
  references: ['Rosenzweig & MacArthur (1963), Am. Nat.', 'Rosenzweig (1971), Paradox of Enrichment, Science'],
  timeUnit: 'années',
  params: [
    { key: 'harvest', label: 'Taux de prélèvement des proies', unit: '%/an', min: 0, max: 100, default: base.harvest, kind: 'control' },
    { key: 'k', label: 'Capacité de charge K', unit: 'ind.', min: 50, max: 5000, default: base.k, log: true, kind: 'control', help: 'Ressources disponibles pour les proies (enrichissement)' },
    { key: 'r', label: 'Taux de croissance des proies r', unit: '1/an', min: 0.1, max: 4, default: base.r, step: 0.05, kind: 'property' },
    { key: 'attack', label: 'Taux d\'attaque a', unit: '1/(ind.·an)', min: 0.001, max: 0.1, default: base.attack, step: 0.001, log: true, kind: 'property' },
    { key: 'handling', label: 'Temps de manipulation h', unit: 'an', min: 0, max: 1, default: base.handling, step: 0.01, kind: 'property' },
    { key: 'efficiency', label: 'Efficacité de conversion e', unit: '—', min: 0.05, max: 1, default: base.efficiency, step: 0.01, kind: 'property' },
    { key: 'mortality', label: 'Mortalité des prédateurs m', unit: '1/an', min: 0.01, max: 1, default: base.mortality, step: 0.01, kind: 'property' },
    { key: 'n0', label: 'Proies initiales', unit: 'ind.', min: 1, max: 5000, default: base.n0, kind: 'property' },
    { key: 'p0', label: 'Prédateurs initiaux', unit: 'ind.', min: 0, max: 500, default: base.p0, kind: 'property' },
    { key: 'duration', label: 'Horizon', unit: 'années', min: 20, max: 1000, default: base.duration, kind: 'control' },
  ],
  metrics: [
    { key: 'preyMean', label: 'Proies (moyenne long terme)', unit: 'ind.', digits: 1, noise: 0.05 },
    { key: 'preyMin', label: 'Proies (minimum)', unit: 'ind.', digits: 1, noise: 0.08 },
    { key: 'preyMax', label: 'Proies (maximum)', unit: 'ind.', digits: 1, noise: 0.05 },
    { key: 'predatorMean', label: 'Prédateurs (moyenne long terme)', unit: 'ind.', digits: 1, noise: 0.05 },
    { key: 'predatorMin', label: 'Prédateurs (minimum)', unit: 'ind.', digits: 2, noise: 0.08 },
    { key: 'period', label: 'Période des cycles', unit: 'années', digits: 2, noise: 0.03 },
    { key: 'coexistence', label: 'Coexistence durable', unit: '0/1', digits: 0, noise: 0 },
    { key: 'harvestYield', label: 'Rendement du prélèvement', unit: 'ind./an', digits: 1, noise: 0.05 },
  ],
  series: [
    { key: 'N', label: 'Proies', unit: 'ind.' },
    { key: 'P', label: 'Prédateurs', unit: 'ind.' },
  ],
  plots: [
    { title: 'Populations', x: 't', xLabel: 'Années', ys: ['N', 'P'], yLabel: 'Individus' },
    { title: 'Portrait de phase', x: 'N', xLabel: 'Proies', ys: ['P'], yLabel: 'Prédateurs' },
  ],
  physical: { costPerRun: 120_000, hoursPerRun: 8760, note: 'Suivi de populations en milieu naturel ou mésocosme sur plusieurs années' },
  simulate,
  validation: [
    {
      name: 'Croissance logistique sans prédateur',
      reference: 'N(t) = K / (1 + (K − N₀)/N₀ · e^(−rt))',
      tolerance: 1e-5,
      run: () => {
        const p: Params = { ...base, p0: 0, n0: 5, duration: 8 };
        return {
          expected: p.k / (1 + ((p.k - p.n0) / p.n0) * Math.exp(-p.r * p.duration)),
          obtained: simulate(p).series.N.at(-1)!,
        };
      },
    },
    {
      name: 'Équilibre de coexistence stable',
      reference: 'N* = m / (a·(e − m·h)) (régime stable, K faible)',
      tolerance: 1e-3,
      run: () => {
        const p: Params = { ...base, k: 80, duration: 600 };
        return { expected: p.mortality / (p.attack * (p.efficiency - p.mortality * p.handling)), obtained: simulate(p).series.N.at(-1)! };
      },
    },
  ],
};
