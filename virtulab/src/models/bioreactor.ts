import { rk45 } from '../core/ode';
import type { Model, Params, SimOutput } from './types';

function simulate(p: Params): SimOutput {
  const mu = (s: number) => (p.muMax * s) / (p.ks + s);
  const res = rk45(
    (_t, y, out) => {
      const [X, S, P] = y;
      const g = mu(S);
      out[0] = (g - p.dilution) * X;
      out[1] = p.dilution * (p.sIn - S) - (g * X) / p.yield;
      out[2] = (p.alpha * g + p.beta) * X - p.dilution * P;
    },
    [p.x0, p.s0, 0],
    { t0: 0, t1: p.duration, rtol: 1e-8, atol: 1e-9, samples: 600, hmax: 0.5,
      clamp: (y) => { for (let i = 0; i < 3; i++) if (y[i] < 0) y[i] = 0; } },
  );
  const [X, S, P] = res.y;
  const n = X.length - 1;
  const dCrit = (p.muMax * p.sIn) / (p.ks + p.sIn);
  return {
    t: res.t,
    series: { X, S, P },
    metrics: {
      biomass: X[n],
      substrate: S[n],
      product: P[n],
      productivity: p.dilution > 0 ? p.dilution * P[n] : P[n] / p.duration,
      substrateConversion: p.dilution > 0 ? (100 * (p.sIn - S[n])) / p.sIn : (100 * (p.s0 - S[n])) / Math.max(p.s0, 1e-9),
      washout: p.dilution > 0 && p.dilution >= dCrit ? 1 : 0,
      doublingTime: Math.LN2 / p.muMax,
    },
  };
}

const base: Params = {
  muMax: 0.45, ks: 0.25, yield: 0.5, alpha: 2.2, beta: 0.02, x0: 0.1, s0: 10, sIn: 20, dilution: 0.15, duration: 150,
};

export const bioreactor: Model = {
  id: 'bioreactor',
  name: 'Bioréacteur — culture microbienne (Monod)',
  discipline: 'Bio-procédés',
  icon: '🧫',
  summary: 'Croissance cellulaire, consommation de substrat et synthèse de produit en batch ou en chémostat.',
  description:
    'Culture d\'un micro-organisme limitée par un substrat selon la cinétique de Monod, avec production d\'un métabolite ' +
    '(modèle de Luedeking–Piret). En mode continu (D > 0), permet de trouver le taux de dilution qui maximise la ' +
    'productivité sans lessivage de la culture — optimisation qui nécessite normalement des semaines de fermentations.',
  equations: [
    'μ(S) = μmax·S / (Ks + S)',
    'dX/dt = (μ − D)·X',
    'dS/dt = D·(S_in − S) − μ·X / Y',
    'dP/dt = (α·μ + β)·X − D·P',
  ],
  assumptions: [
    'Réacteur parfaitement agité, volume constant',
    'Un seul substrat limitant, rendement constant',
    'Pas d\'inhibition par le produit ni par le substrat',
  ],
  references: ['Monod (1949), Annu. Rev. Microbiol.', 'Shuler & Kargi, Bioprocess Engineering'],
  timeUnit: 'h',
  params: [
    { key: 'dilution', label: 'Taux de dilution D (0 = batch)', unit: '1/h', min: 0, max: 1, default: base.dilution, step: 0.005, kind: 'control' },
    { key: 'sIn', label: 'Substrat alimenté S_in', unit: 'g/L', min: 1, max: 100, default: base.sIn, kind: 'control' },
    { key: 's0', label: 'Substrat initial S₀', unit: 'g/L', min: 0, max: 100, default: base.s0, kind: 'control' },
    { key: 'x0', label: 'Inoculum X₀', unit: 'g/L', min: 0.001, max: 5, default: base.x0, log: true, kind: 'control' },
    { key: 'duration', label: 'Durée de culture', unit: 'h', min: 5, max: 500, default: base.duration, kind: 'control' },
    { key: 'muMax', label: 'Taux de croissance max. μmax', unit: '1/h', min: 0.05, max: 2, default: base.muMax, step: 0.01, kind: 'property' },
    { key: 'ks', label: 'Constante d\'affinité Ks', unit: 'g/L', min: 0.001, max: 5, default: base.ks, log: true, kind: 'property' },
    { key: 'yield', label: 'Rendement biomasse/substrat Y', unit: 'g/g', min: 0.05, max: 0.9, default: base.yield, step: 0.01, kind: 'property' },
    { key: 'alpha', label: 'Production associée à la croissance α', unit: 'g/g', min: 0, max: 5, default: base.alpha, step: 0.05, kind: 'property' },
    { key: 'beta', label: 'Production non associée β', unit: 'g/(g·h)', min: 0, max: 0.5, default: base.beta, step: 0.005, kind: 'property' },
  ],
  metrics: [
    { key: 'biomass', label: 'Biomasse finale', unit: 'g/L', digits: 3, noise: 0.03 },
    { key: 'substrate', label: 'Substrat résiduel', unit: 'g/L', digits: 3, noise: 0.05 },
    { key: 'product', label: 'Titre en produit', unit: 'g/L', digits: 2, noise: 0.04 },
    { key: 'productivity', label: 'Productivité volumique', unit: 'g/(L·h)', digits: 3, noise: 0.04 },
    { key: 'substrateConversion', label: 'Conversion du substrat', unit: '%', digits: 1, noise: 0.01 },
    { key: 'washout', label: 'Lessivage de la culture', unit: '0/1', digits: 0, noise: 0 },
    { key: 'doublingTime', label: 'Temps de doublement min.', unit: 'h', digits: 2, noise: 0 },
  ],
  series: [
    { key: 'X', label: 'Biomasse', unit: 'g/L' },
    { key: 'S', label: 'Substrat', unit: 'g/L' },
    { key: 'P', label: 'Produit', unit: 'g/L' },
  ],
  plots: [{ title: 'Cinétique de culture', x: 't', xLabel: 'Temps (h)', ys: ['X', 'S', 'P'], yLabel: 'g/L' }],
  physical: { costPerRun: 2800, hoursPerRun: 150, note: 'Fermentation en bioréacteur de paillasse : milieux, stérilisation, analyses, opérateur' },
  simulate,
  validation: [
    {
      name: 'Régime permanent du chémostat',
      reference: 'S* = Ks·D / (μmax − D)',
      tolerance: 1e-4,
      run: () => {
        const p: Params = { ...base, beta: 0, duration: 500 };
        return { expected: (p.ks * p.dilution) / (p.muMax - p.dilution), obtained: simulate(p).metrics.substrate };
      },
    },
    {
      name: 'Bilan de masse en batch',
      reference: 'X∞ = X₀ + Y·S₀ (D = 0, épuisement du substrat)',
      tolerance: 1e-4,
      run: () => {
        const p: Params = { ...base, dilution: 0, duration: 200 };
        return { expected: p.x0 + p.yield * p.s0, obtained: simulate(p).metrics.biomass };
      },
    },
  ],
};
