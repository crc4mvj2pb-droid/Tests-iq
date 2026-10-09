export type Derivative = (t: number, y: number[], out: number[]) => void;

export interface OdeResult {
  t: number[];
  y: number[][]; // y[i] = trajectoire de la variable i
}

export interface OdeOptions {
  t0: number;
  t1: number;
  dt: number;
  /** Nombre de points conservés en sortie (sous-échantillonnage). */
  samples?: number;
  /** Arrêt anticipé (ex. projectile au sol). Renvoie true pour stopper. */
  stop?: (t: number, y: number[]) => boolean;
  /** Contraintes appliquées après chaque pas (ex. concentrations >= 0). */
  clamp?: (y: number[]) => void;
}

/**
 * Intégrateur Runge-Kutta d'ordre 4 à pas fixe. Erreur globale en O(dt^4),
 * vérifiée contre des solutions analytiques dans tests/.
 */
export function rk4(f: Derivative, y0: number[], opts: OdeOptions): OdeResult {
  const n = y0.length;
  const steps = Math.max(1, Math.ceil((opts.t1 - opts.t0) / opts.dt));
  const h = (opts.t1 - opts.t0) / steps;
  const every = Math.max(1, Math.floor(steps / (opts.samples ?? 400)));
  const k1 = new Array(n), k2 = new Array(n), k3 = new Array(n), k4 = new Array(n), tmp = new Array(n);
  let y = y0.slice();
  let t = opts.t0;
  const T: number[] = [t];
  const Y: number[][] = y0.map((v) => [v]);

  for (let s = 1; s <= steps; s++) {
    f(t, y, k1);
    for (let i = 0; i < n; i++) tmp[i] = y[i] + 0.5 * h * k1[i];
    f(t + 0.5 * h, tmp, k2);
    for (let i = 0; i < n; i++) tmp[i] = y[i] + 0.5 * h * k2[i];
    f(t + 0.5 * h, tmp, k3);
    for (let i = 0; i < n; i++) tmp[i] = y[i] + h * k3[i];
    f(t + h, tmp, k4);
    const next = new Array(n);
    for (let i = 0; i < n; i++) next[i] = y[i] + (h / 6) * (k1[i] + 2 * k2[i] + 2 * k3[i] + k4[i]);
    opts.clamp?.(next);
    const prevY = y;
    const prevT = t;
    y = next;
    t = opts.t0 + s * h;

    if (opts.stop?.(t, y)) {
      // Interpolation linéaire du point d'arrêt pour ne pas biaiser les métriques.
      const a = stopFraction(opts.stop, prevT, prevY, t, y);
      T.push(prevT + a * (t - prevT));
      for (let i = 0; i < n; i++) Y[i].push(prevY[i] + a * (y[i] - prevY[i]));
      return { t: T, y: Y };
    }
    if (s % every === 0 || s === steps) {
      T.push(t);
      for (let i = 0; i < n; i++) Y[i].push(y[i]);
    }
  }
  return { t: T, y: Y };
}

function stopFraction(
  stop: (t: number, y: number[]) => boolean,
  t0: number, y0: number[], t1: number, y1: number[],
): number {
  let lo = 0, hi = 1;
  const yi = new Array(y0.length);
  for (let it = 0; it < 30; it++) {
    const mid = (lo + hi) / 2;
    for (let i = 0; i < y0.length; i++) yi[i] = y0[i] + mid * (y1[i] - y0[i]);
    if (stop(t0 + mid * (t1 - t0), yi)) hi = mid; else lo = mid;
  }
  return hi;
}

/** Intégrale par la méthode des trapèzes. */
export function trapz(x: number[], y: number[]): number {
  let s = 0;
  for (let i = 1; i < x.length; i++) s += 0.5 * (y[i] + y[i - 1]) * (x[i] - x[i - 1]);
  return s;
}

export interface AdaptiveOptions {
  t0: number;
  t1: number;
  rtol?: number;
  atol?: number;
  hmax?: number;
  samples?: number;
  maxSteps?: number;
  clamp?: (y: number[]) => void;
}

/**
 * Runge-Kutta-Dormand-Prince 5(4) à pas adaptatif (base de ode45). Indispensable
 * pour les systèmes raides comme l'emballement thermique d'un réacteur.
 * La sortie est rééchantillonnée sur une grille uniforme de `samples` points.
 */
export function rk45(
  f: Derivative, y0: number[], opts: AdaptiveOptions,
): OdeResult & { raw: OdeResult; steps: number; ok: boolean } {
  const n = y0.length;
  const rtol = opts.rtol ?? 1e-6;
  const atol = opts.atol ?? 1e-9;
  const span = opts.t1 - opts.t0;
  const hmax = opts.hmax ?? span / 50;
  const maxSteps = opts.maxSteps ?? 200_000;
  const c = [0, 1 / 5, 3 / 10, 4 / 5, 8 / 9, 1, 1];
  const a = [
    [],
    [1 / 5],
    [3 / 40, 9 / 40],
    [44 / 45, -56 / 15, 32 / 9],
    [19372 / 6561, -25360 / 2187, 64448 / 6561, -212 / 729],
    [9017 / 3168, -355 / 33, 46732 / 5247, 49 / 176, -5103 / 18656],
    [35 / 384, 0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84],
  ];
  const b5 = [35 / 384, 0, 500 / 1113, 125 / 192, -2187 / 6784, 11 / 84, 0];
  const b4 = [5179 / 57600, 0, 7571 / 16695, 393 / 640, -92097 / 339200, 187 / 2100, 1 / 40];
  const k = Array.from({ length: 7 }, () => new Array(n).fill(0));
  const tmp = new Array(n);
  let y = y0.slice();
  let t = opts.t0;
  let h = Math.min(hmax, span / 1000);
  const T = [t];
  const Y = y0.map((v) => [v]);
  let steps = 0;
  let ok = true;

  f(t, y, k[0]);
  while (t < opts.t1) {
    if (++steps > maxSteps) { ok = false; break; }
    if (t + h > opts.t1) h = opts.t1 - t;
    for (let s = 1; s < 7; s++) {
      for (let i = 0; i < n; i++) {
        let acc = y[i];
        for (let j = 0; j < s; j++) acc += h * a[s][j] * k[j][i];
        tmp[i] = acc;
      }
      f(t + c[s] * h, tmp, k[s]);
    }
    let err = 0;
    const next = new Array(n);
    for (let i = 0; i < n; i++) {
      let y5 = y[i], y4 = y[i];
      for (let s = 0; s < 7; s++) { y5 += h * b5[s] * k[s][i]; y4 += h * b4[s] * k[s][i]; }
      next[i] = y5;
      const sc = atol + rtol * Math.max(Math.abs(y[i]), Math.abs(y5));
      err = Math.max(err, Math.abs(y5 - y4) / sc);
    }
    if (err <= 1 || h < 1e-12 * span) {
      opts.clamp?.(next);
      t += h;
      y = next;
      T.push(t);
      for (let i = 0; i < n; i++) Y[i].push(y[i]);
      f(t, y, k[0]); // FSAL recalculé après éventuel clamp
    }
    const factor = err === 0 ? 5 : Math.min(5, Math.max(0.2, 0.9 * Math.pow(err, -0.2)));
    h = Math.min(hmax, h * factor);
    if (!Number.isFinite(h) || h <= 0) { ok = false; break; }
  }
  // `raw` garde tous les pas acceptés : les extrema (pic de température…) se
  // calculent dessus pour ne pas être écrêtés par le rééchantillonnage.
  return { ...resample(T, Y, opts.t0, Math.min(t, opts.t1), opts.samples ?? 400), raw: { t: T, y: Y }, steps, ok };
}

function resample(T: number[], Y: number[][], t0: number, t1: number, samples: number): OdeResult {
  if (T.length < 2) return { t: T.slice(), y: Y.map((v) => v.slice()) };
  const outT: number[] = [];
  const outY: number[][] = Y.map(() => []);
  let j = 0;
  for (let s = 0; s <= samples; s++) {
    const tt = t0 + ((t1 - t0) * s) / samples;
    while (j < T.length - 2 && T[j + 1] < tt) j++;
    const span = T[j + 1] - T[j];
    const w = span > 0 ? Math.min(1, Math.max(0, (tt - T[j]) / span)) : 0;
    outT.push(tt);
    for (let i = 0; i < Y.length; i++) {
      const lo = Y[i][j], hi = Y[i][Math.min(j + 1, T.length - 1)];
      outY[i].push(lo + w * (hi - lo));
    }
  }
  return { t: outT, y: outY };
}
