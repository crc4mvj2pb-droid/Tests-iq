import { rk4 } from '../core/ode';
import { maxOf, type Model, type Params, type SimOutput } from './types';

const G = 9.80665;

function simulate(p: Params): SimOutput {
  const theta = (p.angle * Math.PI) / 180;
  const area = Math.PI * (p.diameter / 2) ** 2;
  const kDrag = (0.5 * p.rho * p.cd * area) / p.mass;
  const vx0 = p.v0 * Math.cos(theta);
  const vy0 = p.v0 * Math.sin(theta);

  // Horizon d'intégration : temps de vol dans le vide + marge pour une chute à vitesse limite.
  const tVac = (vy0 + Math.sqrt(vy0 * vy0 + 2 * G * p.h0)) / G;
  const vTerm = kDrag > 0 ? Math.sqrt(G / kDrag) : Infinity;
  const apex = p.h0 + (vy0 * vy0) / (2 * G);
  const t1 = 3 * tVac + (Number.isFinite(vTerm) ? (2 * apex) / vTerm : 0) + 5;

  const res = rk4(
    (_t, y, out) => {
      const rx = y[2] - p.wind;
      const ry = y[3];
      const v = Math.hypot(rx, ry);
      out[0] = y[2];
      out[1] = y[3];
      out[2] = -kDrag * v * rx;
      out[3] = -G - kDrag * v * ry;
    },
    [0, p.h0, vx0, vy0],
    { t0: 0, t1, dt: Math.min(1e-3, t1 / 20000), samples: 3000, stop: (t, y) => t > 0 && y[1] < 0 },
  );

  const [x, y, vx, vy] = res.y;
  const n = res.t.length - 1;
  const speed = vx.map((v, i) => Math.hypot(v, vy[i]));
  const e0 = 0.5 * p.v0 ** 2 + G * p.h0;
  const ef = 0.5 * speed[n] ** 2 + G * Math.max(0, y[n]);

  return {
    t: res.t,
    series: { x, y, speed },
    metrics: {
      range: x[n],
      maxHeight: maxOf(y),
      flightTime: res.t[n],
      impactSpeed: speed[n],
      impactAngle: (Math.atan2(-vy[n], Math.abs(vx[n])) * 180) / Math.PI,
      energyLoss: (100 * (e0 - ef)) / e0,
    },
  };
}

export const projectile: Model = {
  id: 'projectile',
  name: 'Balistique avec traînée aérodynamique',
  discipline: 'Physique',
  icon: '🎯',
  summary: "Trajectoire d'un projectile soumis à la gravité, à la traînée quadratique et au vent.",
  description:
    "Simule le vol d'un objet sphérique (ballon, projectile, gouttelette) dans un fluide. La traînée quadratique " +
    "rend le problème non linéaire et sans solution analytique : l'angle optimal n'est plus 45° et dépend de la " +
    "masse, du diamètre et du coefficient de traînée. Remplace des campagnes de tirs instrumentés en soufflerie ou en extérieur.",
  equations: [
    'm·dv/dt = m·g − ½·ρ·Cd·A·|v − w|·(v − w)',
    'A = π·D²/4',
    'dx/dt = vx,  dy/dt = vy',
  ],
  assumptions: [
    'Objet sphérique rigide, sans rotation (pas d\'effet Magnus)',
    'Coefficient de traînée constant (régime de Reynolds fixe)',
    'Vent horizontal uniforme, gravité constante, Terre plate',
  ],
  references: ['Landau & Lifchitz, Mécanique des fluides', 'NASA Glenn — Drag of a Sphere'],
  timeUnit: 's',
  params: [
    { key: 'v0', label: 'Vitesse initiale', unit: 'm/s', min: 1, max: 150, default: 40, kind: 'control' },
    { key: 'angle', label: 'Angle de tir', unit: '°', min: 5, max: 85, default: 45, kind: 'control' },
    { key: 'h0', label: 'Hauteur de départ', unit: 'm', min: 0, max: 100, default: 1.5, kind: 'control' },
    { key: 'mass', label: 'Masse', unit: 'kg', min: 0.01, max: 20, default: 0.45, log: true, kind: 'property' },
    { key: 'diameter', label: 'Diamètre', unit: 'm', min: 0.02, max: 0.5, default: 0.22, kind: 'property' },
    { key: 'cd', label: 'Coefficient de traînée Cd', unit: '—', min: 0, max: 1.5, default: 0.47, step: 0.01, kind: 'property', help: 'Sphère lisse ≈ 0,47 ; balle de golf ≈ 0,25' },
    { key: 'rho', label: "Masse volumique de l'air", unit: 'kg/m³', min: 0.4, max: 1.4, default: 1.225, step: 0.005, kind: 'property', help: '1,225 au niveau de la mer à 15 °C ; ≈ 0,9 à 3000 m' },
    { key: 'wind', label: 'Vent (+ = arrière)', unit: 'm/s', min: -20, max: 20, default: 0, kind: 'property' },
  ],
  metrics: [
    { key: 'range', label: 'Portée', unit: 'm', digits: 2, noise: 0.01 },
    { key: 'maxHeight', label: 'Hauteur maximale', unit: 'm', digits: 2, noise: 0.015 },
    { key: 'flightTime', label: 'Temps de vol', unit: 's', digits: 3, noise: 0.005 },
    { key: 'impactSpeed', label: "Vitesse à l'impact", unit: 'm/s', digits: 2, noise: 0.02 },
    { key: 'impactAngle', label: "Angle d'impact", unit: '°', digits: 1, noise: 0.02 },
    { key: 'energyLoss', label: 'Énergie dissipée', unit: '%', digits: 1, noise: 0.02 },
  ],
  series: [
    { key: 'x', label: 'Position x', unit: 'm' },
    { key: 'y', label: 'Altitude', unit: 'm' },
    { key: 'speed', label: 'Vitesse', unit: 'm/s' },
  ],
  plots: [
    { title: 'Trajectoire', x: 'x', xLabel: 'Distance (m)', ys: ['y'], yLabel: 'Altitude (m)' },
    { title: 'Vitesse', x: 't', xLabel: 'Temps (s)', ys: ['speed'], yLabel: 'Vitesse (m/s)' },
  ],
  physical: { costPerRun: 450, hoursPerRun: 1.5, note: 'Tir instrumenté (lanceur, caméra rapide, radar Doppler, opérateurs)' },
  simulate,
  validation: [
    {
      name: 'Tir dans le vide',
      reference: 'Portée analytique R = v₀²·sin(2θ)/g (Cd = 0)',
      tolerance: 1e-4,
      run: () => {
        const p = { v0: 30, angle: 40, h0: 0, mass: 1, diameter: 0.1, cd: 0, rho: 1.225, wind: 0 };
        return { expected: (30 ** 2 * Math.sin((80 * Math.PI) / 180)) / G, obtained: simulate(p).metrics.range };
      },
    },
    {
      name: 'Vitesse limite de chute',
      reference: 'v∞ = √(2mg / (ρ·Cd·A)) pour une chute depuis 3000 m',
      tolerance: 1e-3,
      run: () => {
        const p = { v0: 0, angle: 45, h0: 3000, mass: 0.45, diameter: 0.22, cd: 0.47, rho: 1.225, wind: 0 };
        const area = Math.PI * 0.11 ** 2;
        return { expected: Math.sqrt((2 * 0.45 * G) / (1.225 * 0.47 * area)), obtained: simulate(p).metrics.impactSpeed };
      },
    },
  ],
};
