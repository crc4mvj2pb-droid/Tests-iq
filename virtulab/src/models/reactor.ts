import { rk45 } from '../core/ode';
import { argMax, maxOf, type Model, type Params, type SimOutput } from './types';

const R = 8.314; // J/(mol·K)
const RHO_CP = 4.18; // kJ/(L·K), phase aqueuse

function rateConstants(p: Params, TK: number): [number, number] {
  return [
    10 ** p.logA1 * Math.exp((-p.ea1 * 1000) / (R * TK)),
    10 ** p.logA2 * Math.exp((-p.ea2 * 1000) / (R * TK)),
  ];
}

function simulate(p: Params): SimOutput {
  const Tc = p.tc + 273.15;
  const ua = p.ua / 1000; // W/(L·K) -> kJ/(s·L·K)
  const tEnd = p.duration * 60;
  const res = rk45(
    (_t, y, out) => {
      const [ca, cb, , T] = y;
      const [k1, k2] = rateConstants(p, T);
      const r1 = k1 * ca;
      const r2 = k2 * cb;
      out[0] = -r1;
      out[1] = r1 - r2;
      out[2] = r2;
      out[3] = (-p.dh1 * r1 - p.dh2 * r2 - ua * (T - Tc)) / RHO_CP;
    },
    [p.a0, 0, 0, p.t0 + 273.15],
    {
      t0: 0, t1: tEnd, rtol: 1e-7, atol: 1e-10, samples: 500, maxSteps: 400_000,
      clamp: (y) => { for (let i = 0; i < 3; i++) if (y[i] < 0) y[i] = 0; },
    },
  );
  const [ca, cb, cc, T] = res.y;
  const raw = res.raw.y;
  const n = ca.length - 1;
  const iB = argMax(raw[1]);
  const tC = T.map((v) => v - 273.15);
  const tMax = maxOf(raw[3]) - 273.15;
  const formed = cb[n] + cc[n];
  return {
    t: res.t.map((s) => s / 60),
    series: { ca, cb, cc, temp: tC },
    metrics: {
      bMax: raw[1][iB],
      tBMax: res.raw.t[iB] / 60,
      yieldB: (100 * cb[n]) / p.a0,
      conversion: (100 * (p.a0 - ca[n])) / p.a0,
      selectivity: formed > 0 ? (100 * cb[n]) / formed : 0,
      tMax,
      dTMax: tMax - p.tc,
      runaway: tMax - p.tc > 25 ? 1 : 0,
    },
  };
}

const base: Params = {
  a0: 1, t0: 60, tc: 60, ea1: 70, logA1: 7.5, ea2: 90, logA2: 9.5, dh1: -90, dh2: -40, ua: 1.5, duration: 240,
};

export const reactor: Model = {
  id: 'reactor',
  name: 'Réacteur chimique fermé exothermique',
  discipline: 'Chimie',
  icon: '⚗️',
  summary: 'Réactions consécutives A → B → C avec loi d\'Arrhenius, bilan thermique et risque d\'emballement.',
  description:
    "Réacteur discontinu refroidi par une double enveloppe. Le produit d'intérêt B se dégrade en sous-produit C. " +
    "La chaleur dégagée accélère les réactions (Arrhenius), ce qui peut provoquer un emballement thermique. " +
    "Permet d'optimiser température et durée pour maximiser le rendement en B, et de cartographier les zones " +
    "dangereuses sans jamais les tester physiquement.",
  equations: [
    'dCA/dt = −k₁·CA',
    'dCB/dt = k₁·CA − k₂·CB',
    'dCC/dt = k₂·CB',
    'kᵢ = Aᵢ·exp(−Eaᵢ / RT)',
    'ρcp·dT/dt = (−ΔH₁)·k₁·CA + (−ΔH₂)·k₂·CB − (UA/V)·(T − Tc)',
  ],
  assumptions: [
    'Mélange parfait, volume constant, phase liquide aqueuse (ρcp = 4,18 kJ/L/K)',
    'Cinétiques du premier ordre',
    'Température de la double enveloppe constante',
  ],
  references: ['Levenspiel, Chemical Reaction Engineering', 'Stoessel, Thermal Safety of Chemical Processes'],
  timeUnit: 'min',
  params: [
    { key: 'tc', label: 'Température de refroidissement', unit: '°C', min: 20, max: 120, default: base.tc, kind: 'control' },
    { key: 't0', label: 'Température initiale', unit: '°C', min: 20, max: 120, default: base.t0, kind: 'control' },
    { key: 'a0', label: 'Concentration initiale A', unit: 'mol/L', min: 0.1, max: 5, default: base.a0, step: 0.05, kind: 'control' },
    { key: 'ua', label: 'Coefficient de refroidissement UA/V', unit: 'W/(L·K)', min: 0, max: 10, default: base.ua, step: 0.1, kind: 'control' },
    { key: 'duration', label: 'Durée du lot', unit: 'min', min: 10, max: 1440, default: base.duration, kind: 'control' },
    { key: 'ea1', label: 'Énergie d\'activation A→B', unit: 'kJ/mol', min: 40, max: 120, default: base.ea1, kind: 'property' },
    { key: 'logA1', label: 'log₁₀ facteur pré-exp. A→B', unit: 'log(1/s)', min: 3, max: 14, default: base.logA1, step: 0.1, kind: 'property' },
    { key: 'ea2', label: 'Énergie d\'activation B→C', unit: 'kJ/mol', min: 40, max: 120, default: base.ea2, kind: 'property' },
    { key: 'logA2', label: 'log₁₀ facteur pré-exp. B→C', unit: 'log(1/s)', min: 3, max: 14, default: base.logA2, step: 0.1, kind: 'property' },
    { key: 'dh1', label: 'Enthalpie de réaction A→B', unit: 'kJ/mol', min: -250, max: 0, default: base.dh1, kind: 'property' },
    { key: 'dh2', label: 'Enthalpie de réaction B→C', unit: 'kJ/mol', min: -250, max: 0, default: base.dh2, kind: 'property' },
  ],
  metrics: [
    { key: 'bMax', label: 'Concentration max. en B', unit: 'mol/L', digits: 3, noise: 0.02 },
    { key: 'tBMax', label: 'Instant du maximum de B', unit: 'min', digits: 1, noise: 0.03 },
    { key: 'yieldB', label: 'Rendement final en B', unit: '%', digits: 1, noise: 0.02 },
    { key: 'conversion', label: 'Conversion de A', unit: '%', digits: 1, noise: 0.01 },
    { key: 'selectivity', label: 'Sélectivité en B', unit: '%', digits: 1, noise: 0.02 },
    { key: 'tMax', label: 'Température maximale', unit: '°C', digits: 1, noise: 0.005 },
    { key: 'dTMax', label: 'Échauffement max. (T − Tc)', unit: 'K', digits: 1, noise: 0.02 },
    { key: 'runaway', label: 'Emballement (ΔT > 25 K)', unit: '0/1', digits: 0, noise: 0 },
  ],
  series: [
    { key: 'ca', label: '[A]', unit: 'mol/L' },
    { key: 'cb', label: '[B]', unit: 'mol/L' },
    { key: 'cc', label: '[C]', unit: 'mol/L' },
    { key: 'temp', label: 'Température', unit: '°C' },
  ],
  plots: [
    { title: 'Concentrations', x: 't', xLabel: 'Temps (min)', ys: ['ca', 'cb', 'cc'], yLabel: 'mol/L' },
    { title: 'Température du réacteur', x: 't', xLabel: 'Temps (min)', ys: ['temp'], yLabel: '°C' },
  ],
  physical: { costPerRun: 3200, hoursPerRun: 10, note: 'Lot en réacteur pilote : réactifs, analyses HPLC, calorimétrie, sécurité' },
  simulate,
  validation: [
    {
      name: 'Maximum de l\'intermédiaire (isotherme)',
      reference: 'CB,max = CA₀·(k₁/k₂)^(k₂/(k₂−k₁)) — solution analytique de Bateman',
      tolerance: 1e-4,
      run: () => {
        const p: Params = { ...base, dh1: 0, dh2: 0, duration: 1440 };
        const [k1, k2] = rateConstants(p, p.tc + 273.15);
        return { expected: p.a0 * (k1 / k2) ** (k2 / (k2 - k1)), obtained: simulate(p).metrics.bMax };
      },
    },
    {
      name: 'Élévation adiabatique de température',
      reference: 'ΔT_ad = CA₀·(−ΔH₁)/ρcp pour conversion totale, sans refroidissement',
      tolerance: 1e-3,
      run: () => {
        const p: Params = { ...base, ua: 0, dh2: 0, tc: 40, t0: 40, duration: 1440 };
        return { expected: (p.a0 * -p.dh1) / RHO_CP, obtained: simulate(p).metrics.dTMax };
      },
    },
  ],
};
