import { trapz } from '../core/ode';
import type { Model, Params, SimOutput } from './types';

/** Clairance et volume ajustés au poids (allométrie standard, référence 70 kg). */
function individual(p: Params): { cl: number; v: number; ke: number } {
  const cl = p.cl * (p.weight / 70) ** 0.75;
  const v = p.v * (p.weight / 70);
  return { cl, v, ke: cl / v };
}

/** Concentration plasmatique par superposition des solutions de Bateman (exacte). */
function concentration(p: Params, t: number): number {
  const { v, ke } = individual(p);
  const ka = Math.abs(p.ka - ke) < 1e-9 ? ke * (1 + 1e-6) : p.ka;
  const coef = (p.bioavailability * p.dose * ka) / (v * (ka - ke));
  let c = 0;
  for (let d = 0; d < p.doses; d++) {
    const td = t - d * p.interval;
    if (td <= 0) break;
    c += coef * (Math.exp(-ke * td) - Math.exp(-ka * td));
  }
  return c;
}

function simulate(p: Params): SimOutput {
  const tEnd = p.doses * p.interval + p.followUp;
  const npts = 1200;
  const t: number[] = [];
  const c: number[] = [];
  for (let i = 0; i <= npts; i++) {
    const ti = (tEnd * i) / npts;
    t.push(ti);
    c.push(concentration(p, ti));
  }
  // Raffinement local autour des pics pour une estimation précise de Cmax.
  let cMax = 0;
  for (let d = 0; d < p.doses; d++) {
    const t0 = d * p.interval;
    const span = Math.min(p.interval, tEnd - t0);
    for (let j = 1; j <= 400; j++) cMax = Math.max(cMax, concentration(p, t0 + (span * j) / 400));
  }
  const dosingEnd = p.doses * p.interval;
  // Les pourcentages portent sur la période de traitement (hors suivi après la dernière prise).
  let inWindow = 0, toxic = 0;
  for (let i = 1; i <= npts && t[i - 1] < dosingEnd; i++) {
    const dt = Math.min(t[i], dosingEnd) - t[i - 1];
    const cm = 0.5 * (c[i] + c[i - 1]);
    if (cm >= p.mec && cm <= p.mtc) inWindow += dt;
    if (cm > p.mtc) toxic += dt;
  }
  const { ke } = individual(p);
  return {
    t,
    series: { c, mec: t.map(() => p.mec), mtc: t.map(() => p.mtc) },
    metrics: {
      cMax,
      cTrough: concentration(p, dosingEnd - 1e-9),
      auc: trapz(t, c),
      timeInWindow: (100 * inWindow) / dosingEnd,
      timeToxic: (100 * toxic) / dosingEnd,
      halfLife: Math.LN2 / ke,
      accumulation: 1 / (1 - Math.exp(-ke * p.interval)),
    },
  };
}

const base: Params = {
  dose: 500, interval: 12, doses: 10, ka: 1.2, cl: 5, v: 50, bioavailability: 0.8, weight: 70, mec: 4, mtc: 16, followUp: 24,
};

export const pharmacokinetics: Model = {
  id: 'pk',
  name: 'Pharmacocinétique — administrations orales répétées',
  discipline: 'Pharmacologie',
  icon: '💊',
  summary: 'Concentration plasmatique d\'un médicament, fenêtre thérapeutique et ajustement posologique.',
  description:
    'Modèle mono-compartimental avec absorption d\'ordre 1, élimination linéaire et ajustement allométrique au poids. ' +
    'Évalue un schéma posologique (dose, intervalle) : temps passé dans la fenêtre thérapeutique, risque de toxicité, ' +
    'accumulation. Couplé au Monte Carlo, il reproduit la variabilité inter-individuelle d\'une population de patients ' +
    'et réduit le nombre de volontaires nécessaires en phase I.',
  equations: [
    'C(t) = Σₖ F·D·ka / (V·(ka − ke)) · [e^(−ke·(t−tₖ)) − e^(−ka·(t−tₖ))]',
    'ke = CL / V,  t½ = ln2 / ke',
    'CL = CL₇₀·(poids/70)^0,75,  V = V₇₀·(poids/70)',
  ],
  assumptions: [
    'Modèle mono-compartimental, cinétique linéaire',
    'Absorption d\'ordre 1 sans temps de latence',
    'Doses identiques à intervalles réguliers',
  ],
  references: ['Rowland & Tozer, Clinical Pharmacokinetics', 'Gabrielsson & Weiner, PK/PD Data Analysis'],
  timeUnit: 'h',
  params: [
    { key: 'dose', label: 'Dose par prise', unit: 'mg', min: 10, max: 2000, default: base.dose, kind: 'control' },
    { key: 'interval', label: 'Intervalle entre prises', unit: 'h', min: 2, max: 48, default: base.interval, kind: 'control' },
    { key: 'doses', label: 'Nombre de prises', unit: '—', min: 1, max: 30, default: base.doses, step: 1, kind: 'control' },
    { key: 'weight', label: 'Poids du patient', unit: 'kg', min: 30, max: 150, default: base.weight, kind: 'property' },
    { key: 'ka', label: 'Constante d\'absorption ka', unit: '1/h', min: 0.1, max: 5, default: base.ka, step: 0.05, kind: 'property' },
    { key: 'cl', label: 'Clairance (70 kg)', unit: 'L/h', min: 0.5, max: 50, default: base.cl, step: 0.1, log: true, kind: 'property' },
    { key: 'v', label: 'Volume de distribution (70 kg)', unit: 'L', min: 5, max: 300, default: base.v, log: true, kind: 'property' },
    { key: 'bioavailability', label: 'Biodisponibilité F', unit: '—', min: 0.05, max: 1, default: base.bioavailability, step: 0.01, kind: 'property' },
    { key: 'mec', label: 'Concentration minimale efficace', unit: 'mg/L', min: 0.1, max: 50, default: base.mec, step: 0.1, kind: 'property' },
    { key: 'mtc', label: 'Concentration toxique', unit: 'mg/L', min: 1, max: 200, default: base.mtc, step: 0.5, kind: 'property' },
    { key: 'followUp', label: 'Suivi après dernière prise', unit: 'h', min: 0, max: 96, default: base.followUp, kind: 'control' },
  ],
  metrics: [
    { key: 'cMax', label: 'Concentration maximale', unit: 'mg/L', digits: 2, noise: 0.06 },
    { key: 'cTrough', label: 'Concentration résiduelle (fin)', unit: 'mg/L', digits: 2, noise: 0.08 },
    { key: 'auc', label: 'Aire sous la courbe (AUC)', unit: 'mg·h/L', digits: 0, noise: 0.05 },
    { key: 'timeInWindow', label: 'Temps dans la fenêtre thérapeutique', unit: '%', digits: 1, noise: 0.03 },
    { key: 'timeToxic', label: 'Temps au-dessus du seuil toxique', unit: '%', digits: 1, noise: 0.03 },
    { key: 'halfLife', label: 'Demi-vie d\'élimination', unit: 'h', digits: 2, noise: 0.05 },
    { key: 'accumulation', label: 'Facteur d\'accumulation', unit: '—', digits: 2, noise: 0 },
  ],
  series: [
    { key: 'c', label: 'Concentration', unit: 'mg/L' },
    { key: 'mec', label: 'Seuil efficace', unit: 'mg/L' },
    { key: 'mtc', label: 'Seuil toxique', unit: 'mg/L' },
  ],
  plots: [{ title: 'Concentration plasmatique', x: 't', xLabel: 'Temps (h)', ys: ['c', 'mec', 'mtc'], yLabel: 'mg/L' }],
  physical: { costPerRun: 18_000, hoursPerRun: 72, note: 'Sujet en essai de phase I : recrutement, hospitalisation, prélèvements, dosages LC-MS' },
  simulate,
  validation: [
    {
      name: 'Exposition totale (dose unique)',
      reference: 'AUC₀–∞ = F·D / CL',
      tolerance: 2e-3,
      run: () => {
        const p: Params = { ...base, doses: 1, followUp: 400 };
        return { expected: (p.bioavailability * p.dose) / p.cl, obtained: simulate(p).metrics.auc };
      },
    },
    {
      name: 'Pic de concentration (dose unique)',
      reference: 'Cmax = F·D/V·e^(−ke·tmax), tmax = ln(ka/ke)/(ka − ke)',
      tolerance: 1e-4,
      run: () => {
        const p: Params = { ...base, doses: 1, interval: 48, followUp: 0 };
        const ke = p.cl / p.v;
        const tmax = Math.log(p.ka / ke) / (p.ka - ke);
        return { expected: ((p.bioavailability * p.dose) / p.v) * Math.exp(-ke * tmax), obtained: simulate(p).metrics.cMax };
      },
    },
  ],
};
