import { rk4 } from '../core/ode';
import { argMax, maxOf, type Model, type Params, type SimOutput } from './types';

function simulate(p: Params): SimOutput {
  const N = p.population;
  const sigma = 1 / p.incubation;
  const gamma = 1 / p.infectious;
  const beta0 = p.r0 * gamma;
  const ifr = p.ifr / 100;
  const hosp = p.hospRate / 100;
  const immune = (p.vaccination / 100) * (p.efficacy / 100);
  const i0 = Math.min(p.initialInfected, N);
  const s0 = Math.max(0, (N - i0) * (1 - immune));
  const r0 = N - i0 - s0;
  const tStart = p.npiStart;
  const tEnd = p.npiStart + p.npiDuration;

  const res = rk4(
    (t, y, out) => {
      const [S, E, I, H] = y;
      const reduction = t >= tStart && t < tEnd ? p.npiReduction / 100 : 0;
      const inf = (beta0 * (1 - reduction) * S * I) / N;
      out[0] = -inf;
      out[1] = inf - sigma * E;
      out[2] = sigma * E - gamma * I;
      out[3] = hosp * gamma * I - H / p.hospStay;
      out[4] = (1 - ifr) * gamma * I;
      out[5] = ifr * gamma * I;
    },
    [s0, 0, i0, 0, r0, 0],
    { t0: 0, t1: p.duration, dt: 0.05, samples: 730 },
  );
  const [S, E, I, H, Rr, D] = res.y;
  const n = S.length - 1;
  const iPeak = argMax(I);
  const capacity = (p.beds / 100_000) * N;
  let saturated = 0;
  for (let i = 1; i <= n; i++) if (H[i] > capacity) saturated += res.t[i] - res.t[i - 1];
  const infectedTotal = N - S[n] - r0; // personnes infectées au cours de l'épidémie (hors immunisés initiaux)

  return {
    t: res.t,
    series: { S, E, I, H, R: Rr, D, capacity: res.t.map(() => capacity) },
    metrics: {
      peakInfected: I[iPeak],
      peakDay: res.t[iPeak],
      attackRate: (100 * infectedTotal) / N,
      deaths: D[n],
      peakHosp: maxOf(H),
      saturationDays: saturated,
      reff0: (p.r0 * s0) / N,
    },
  };
}

const base: Params = {
  population: 1_000_000, r0: 2.5, incubation: 5, infectious: 7, initialInfected: 10,
  vaccination: 0, efficacy: 80, npiReduction: 0, npiStart: 30, npiDuration: 60,
  ifr: 0.5, hospRate: 3, hospStay: 10, beds: 30, duration: 365,
};

/** Taille finale théorique d'une épidémie SIR/SEIR : z = 1 − exp(−R₀·z). */
export function finalSize(r0: number): number {
  let z = 0.9;
  for (let i = 0; i < 500; i++) z = 1 - Math.exp(-r0 * z);
  return z;
}

export const seir: Model = {
  id: 'seir',
  name: 'Épidémie SEIR avec vaccination et mesures',
  discipline: 'Épidémiologie',
  icon: '🦠',
  summary: 'Propagation d\'un agent infectieux, couverture vaccinale, mesures barrières et saturation hospitalière.',
  description:
    'Modèle compartimental Susceptibles – Exposés – Infectieux – Rétablis avec suivi des hospitalisations et des décès. ' +
    'Permet d\'évaluer des stratégies (vaccination, réduction des contacts, calendrier des mesures) en comparant le pic, ' +
    'la mortalité et les jours de saturation hospitalière — des scénarios impossibles à tester expérimentalement.',
  equations: [
    'dS/dt = −β(t)·S·I/N',
    'dE/dt = β(t)·S·I/N − σ·E',
    'dI/dt = σ·E − γ·I',
    'dH/dt = h·γ·I − H/τH',
    'β(t) = R₀·γ·(1 − réduction(t)),  σ = 1/incubation,  γ = 1/période infectieuse',
  ],
  assumptions: [
    'Population homogène et fermée (brassage uniforme, pas de démographie)',
    'Immunité acquise durable, vaccination effectuée avant l\'introduction',
    'Durées de séjour exponentielles',
  ],
  references: ['Anderson & May, Infectious Diseases of Humans', 'Keeling & Rohani, Modeling Infectious Diseases'],
  timeUnit: 'jours',
  params: [
    { key: 'vaccination', label: 'Couverture vaccinale', unit: '%', min: 0, max: 100, default: base.vaccination, kind: 'control' },
    { key: 'npiReduction', label: 'Réduction des contacts (mesures)', unit: '%', min: 0, max: 90, default: base.npiReduction, kind: 'control' },
    { key: 'npiStart', label: 'Début des mesures', unit: 'jour', min: 0, max: 365, default: base.npiStart, kind: 'control' },
    { key: 'npiDuration', label: 'Durée des mesures', unit: 'jours', min: 0, max: 365, default: base.npiDuration, kind: 'control' },
    { key: 'beds', label: 'Capacité hospitalière', unit: 'lits/100 000', min: 1, max: 200, default: base.beds, kind: 'control' },
    { key: 'population', label: 'Population', unit: 'hab.', min: 1000, max: 100_000_000, default: base.population, log: true, kind: 'property' },
    { key: 'r0', label: 'Nombre de reproduction R₀', unit: '—', min: 0.5, max: 10, default: base.r0, step: 0.05, kind: 'property' },
    { key: 'incubation', label: 'Période de latence', unit: 'jours', min: 0.5, max: 14, default: base.incubation, step: 0.1, kind: 'property' },
    { key: 'infectious', label: 'Période infectieuse', unit: 'jours', min: 1, max: 21, default: base.infectious, step: 0.1, kind: 'property' },
    { key: 'efficacy', label: 'Efficacité vaccinale', unit: '%', min: 0, max: 100, default: base.efficacy, kind: 'property' },
    { key: 'ifr', label: 'Létalité (IFR)', unit: '%', min: 0, max: 10, default: base.ifr, step: 0.05, kind: 'property' },
    { key: 'hospRate', label: 'Taux d\'hospitalisation', unit: '%', min: 0, max: 30, default: base.hospRate, step: 0.1, kind: 'property' },
    { key: 'hospStay', label: 'Durée moyenne d\'hospitalisation', unit: 'jours', min: 1, max: 40, default: base.hospStay, kind: 'property' },
    { key: 'initialInfected', label: 'Infectieux initiaux', unit: 'pers.', min: 1, max: 10000, default: base.initialInfected, log: true, kind: 'property' },
    { key: 'duration', label: 'Horizon de simulation', unit: 'jours', min: 30, max: 1500, default: base.duration, kind: 'control' },
  ],
  metrics: [
    { key: 'peakInfected', label: 'Pic d\'infectieux simultanés', unit: 'pers.', digits: 0, noise: 0.05 },
    { key: 'peakDay', label: 'Jour du pic', unit: 'jour', digits: 1, noise: 0.03 },
    { key: 'attackRate', label: 'Taux d\'attaque final', unit: '%', digits: 1, noise: 0.03 },
    { key: 'deaths', label: 'Décès', unit: 'pers.', digits: 0, noise: 0.05 },
    { key: 'peakHosp', label: 'Pic d\'hospitalisations', unit: 'lits', digits: 0, noise: 0.05 },
    { key: 'saturationDays', label: 'Jours de saturation hospitalière', unit: 'jours', digits: 1, noise: 0.03 },
    { key: 'reff0', label: 'R effectif initial', unit: '—', digits: 2, noise: 0 },
  ],
  series: [
    { key: 'S', label: 'Susceptibles', unit: 'pers.' },
    { key: 'E', label: 'Exposés', unit: 'pers.' },
    { key: 'I', label: 'Infectieux', unit: 'pers.' },
    { key: 'R', label: 'Rétablis', unit: 'pers.' },
    { key: 'H', label: 'Hospitalisés', unit: 'lits' },
    { key: 'capacity', label: 'Capacité', unit: 'lits' },
    { key: 'D', label: 'Décès cumulés', unit: 'pers.' },
  ],
  plots: [
    { title: 'Dynamique épidémique', x: 't', xLabel: 'Jours', ys: ['S', 'E', 'I', 'R'], yLabel: 'Personnes' },
    { title: 'Tension hospitalière', x: 't', xLabel: 'Jours', ys: ['H', 'capacity'], yLabel: 'Lits occupés' },
    { title: 'Mortalité cumulée', x: 't', xLabel: 'Jours', ys: ['D'], yLabel: 'Décès' },
  ],
  physical: { costPerRun: 250_000, hoursPerRun: 2000, note: 'Étude d\'intervention de terrain / essai communautaire (souvent impossible ou non éthique)' },
  simulate,
  validation: [
    {
      name: 'Taille finale de l\'épidémie',
      reference: 'Équation de Kermack-McKendrick z = 1 − exp(−R₀·z), R₀ = 2,5',
      tolerance: 2e-3,
      run: () => {
        const p: Params = { ...base, population: 10_000_000, initialInfected: 1, duration: 1500 };
        return { expected: 100 * finalSize(2.5), obtained: simulate(p).metrics.attackRate };
      },
    },
    {
      name: 'Taux de croissance initial',
      reference: 'r = [−(σ+γ) + √((σ−γ)² + 4σβ)] / 2 (linéarisation SEIR)',
      tolerance: 5e-3,
      run: () => {
        const p: Params = { ...base, population: 1e9, initialInfected: 1, duration: 80 };
        const out = simulate(p);
        const iAt = (day: number) => out.series.I[out.t.findIndex((t) => t >= day)];
        const sigma = 1 / p.incubation, gamma = 1 / p.infectious, beta = p.r0 * gamma;
        const expected = (-(sigma + gamma) + Math.sqrt((sigma - gamma) ** 2 + 4 * sigma * beta)) / 2;
        return { expected, obtained: Math.log(iAt(70) / iAt(40)) / 30 };
      },
    },
  ],
};
