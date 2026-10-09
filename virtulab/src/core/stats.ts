export interface Summary {
  n: number;
  mean: number;
  sd: number;
  min: number;
  max: number;
  median: number;
  p05: number;
  p95: number;
  /** Intervalle de confiance à 95 % de la moyenne (loi de Student). */
  ciLow: number;
  ciHigh: number;
  /** Coefficient de variation (sd / |moyenne|). */
  cv: number;
}

export function mean(xs: number[]): number {
  let s = 0;
  for (const x of xs) s += x;
  return xs.length ? s / xs.length : NaN;
}

export function variance(xs: number[]): number {
  if (xs.length < 2) return 0;
  const m = mean(xs);
  let s = 0;
  for (const x of xs) s += (x - m) ** 2;
  return s / (xs.length - 1);
}

export function sd(xs: number[]): number {
  return Math.sqrt(variance(xs));
}

/** Quantile empirique (interpolation linéaire, type 7 de R). */
export function quantile(sorted: number[], p: number): number {
  if (!sorted.length) return NaN;
  const h = (sorted.length - 1) * p;
  const lo = Math.floor(h);
  const hi = Math.ceil(h);
  return sorted[lo] + (h - lo) * (sorted[hi] - sorted[lo]);
}

export function summarize(xs: number[]): Summary {
  const v = xs.filter(Number.isFinite);
  const sorted = v.slice().sort((a, b) => a - b);
  const n = v.length;
  const m = mean(v);
  const s = sd(v);
  const half = n > 1 ? studentTQuantile(0.975, n - 1) * (s / Math.sqrt(n)) : 0;
  return {
    n,
    mean: m,
    sd: s,
    min: sorted[0] ?? NaN,
    max: sorted[n - 1] ?? NaN,
    median: quantile(sorted, 0.5),
    p05: quantile(sorted, 0.05),
    p95: quantile(sorted, 0.95),
    ciLow: m - half,
    ciHigh: m + half,
    cv: m !== 0 ? s / Math.abs(m) : NaN,
  };
}

// ---------- Fonctions spéciales ----------

function logGamma(x: number): number {
  const c = [76.18009172947146, -86.50532032941677, 24.01409824083091,
    -1.231739572450155, 0.1208650973866179e-2, -0.5395239384953e-5];
  let y = x;
  const tmp = x + 5.5 - (x + 0.5) * Math.log(x + 5.5);
  let ser = 1.000000000190015;
  for (const ci of c) ser += ci / ++y;
  return -tmp + Math.log((2.5066282746310005 * ser) / x);
}

function betacf(a: number, b: number, x: number): number {
  const FPMIN = 1e-300;
  let c = 1;
  let d = 1 - ((a + b) * x) / (a + 1);
  if (Math.abs(d) < FPMIN) d = FPMIN;
  d = 1 / d;
  let h = d;
  for (let m = 1; m <= 200; m++) {
    const m2 = 2 * m;
    let aa = (m * (b - m) * x) / ((a + m2 - 1) * (a + m2));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d; h *= d * c;
    aa = (-(a + m) * (a + b + m) * x) / ((a + m2) * (a + m2 + 1));
    d = 1 + aa * d; if (Math.abs(d) < FPMIN) d = FPMIN;
    c = 1 + aa / c; if (Math.abs(c) < FPMIN) c = FPMIN;
    d = 1 / d;
    const del = d * c;
    h *= del;
    if (Math.abs(del - 1) < 3e-14) break;
  }
  return h;
}

/** Fonction bêta incomplète régularisée I_x(a, b). */
export function incompleteBeta(x: number, a: number, b: number): number {
  if (x <= 0) return 0;
  if (x >= 1) return 1;
  const bt = Math.exp(logGamma(a + b) - logGamma(a) - logGamma(b) + a * Math.log(x) + b * Math.log(1 - x));
  return x < (a + 1) / (a + b + 2) ? (bt * betacf(a, b, x)) / a : 1 - (bt * betacf(b, a, 1 - x)) / b;
}

/** Fonction de répartition de la loi de Student à df degrés de liberté. */
export function studentTCdf(t: number, df: number): number {
  const x = df / (df + t * t);
  const tail = 0.5 * incompleteBeta(x, df / 2, 0.5);
  return t >= 0 ? 1 - tail : tail;
}

export function studentTQuantile(p: number, df: number): number {
  let lo = -1e3, hi = 1e3;
  for (let i = 0; i < 200; i++) {
    const mid = (lo + hi) / 2;
    if (studentTCdf(mid, df) < p) lo = mid; else hi = mid;
  }
  return (lo + hi) / 2;
}

// ---------- Tests d'hypothèse ----------

export interface TTestResult {
  t: number;
  df: number;
  pValue: number;
  /** Différence observée (moyenne - référence, ou A - B). */
  diff: number;
}

/** Test t bilatéral à un échantillon : H0 « moyenne = mu0 ». */
export function oneSampleTTest(xs: number[], mu0: number): TTestResult {
  const n = xs.length;
  const m = mean(xs);
  const se = sd(xs) / Math.sqrt(n);
  if (se === 0) return { t: m === mu0 ? 0 : Infinity, df: n - 1, pValue: m === mu0 ? 1 : 0, diff: m - mu0 };
  const t = (m - mu0) / se;
  return { t, df: n - 1, pValue: 2 * (1 - studentTCdf(Math.abs(t), n - 1)), diff: m - mu0 };
}

/** Test t de Welch (variances inégales), bilatéral. */
export function welchTTest(a: number[], b: number[]): TTestResult {
  const va = variance(a) / a.length;
  const vb = variance(b) / b.length;
  const diff = mean(a) - mean(b);
  const se = Math.sqrt(va + vb);
  if (se === 0) return { t: diff === 0 ? 0 : Infinity, df: a.length + b.length - 2, pValue: diff === 0 ? 1 : 0, diff };
  const df = (va + vb) ** 2 / (va ** 2 / (a.length - 1) + vb ** 2 / (b.length - 1));
  const t = diff / se;
  return { t, df, pValue: 2 * (1 - studentTCdf(Math.abs(t), df)), diff };
}

// ---------- Corrélation et régression ----------

export function pearson(x: number[], y: number[]): number {
  const mx = mean(x), my = mean(y);
  let sxy = 0, sxx = 0, syy = 0;
  for (let i = 0; i < x.length; i++) {
    sxy += (x[i] - mx) * (y[i] - my);
    sxx += (x[i] - mx) ** 2;
    syy += (y[i] - my) ** 2;
  }
  return sxx && syy ? sxy / Math.sqrt(sxx * syy) : 0;
}

function ranks(xs: number[]): number[] {
  const idx = xs.map((v, i) => [v, i] as const).sort((p, q) => p[0] - q[0]);
  const r = new Array(xs.length);
  for (let i = 0; i < idx.length;) {
    let j = i;
    while (j + 1 < idx.length && idx[j + 1][0] === idx[i][0]) j++;
    const avg = (i + j) / 2 + 1;
    for (let k = i; k <= j; k++) r[idx[k][1]] = avg;
    i = j + 1;
  }
  return r;
}

/** Corrélation de rang de Spearman (robuste aux relations monotones non linéaires). */
export function spearman(x: number[], y: number[]): number {
  return pearson(ranks(x), ranks(y));
}

export interface Regression {
  /** coefficients[0] = ordonnée à l'origine, puis un coefficient par prédicteur. */
  coefficients: number[];
  /** Coefficients standardisés (SRC) : effet d'un écart-type de chaque facteur. */
  standardized: number[];
  r2: number;
  rmse: number;
}

/** Moindres carrés ordinaires y = b0 + Σ bi·xi (équations normales, pivot de Gauss). */
export function ols(X: number[][], y: number[]): Regression {
  const n = y.length;
  const p = X[0]?.length ?? 0;
  const A = Array.from({ length: p + 1 }, () => new Array(p + 2).fill(0));
  for (let r = 0; r < n; r++) {
    const row = [1, ...X[r]];
    for (let i = 0; i <= p; i++) {
      for (let j = 0; j <= p; j++) A[i][j] += row[i] * row[j];
      A[i][p + 1] += row[i] * y[r];
    }
  }
  const beta = solve(A, p + 1);
  const my = mean(y);
  let ssr = 0, sst = 0;
  for (let r = 0; r < n; r++) {
    let pred = beta[0];
    for (let j = 0; j < p; j++) pred += beta[j + 1] * X[r][j];
    ssr += (y[r] - pred) ** 2;
    sst += (y[r] - my) ** 2;
  }
  const sy = sd(y);
  const standardized = beta.slice(1).map((b, j) => {
    const sx = sd(X.map((row) => row[j]));
    return sy ? (b * sx) / sy : 0;
  });
  return { coefficients: beta, standardized, r2: sst ? 1 - ssr / sst : 1, rmse: Math.sqrt(ssr / n) };
}

function solve(A: number[][], m: number): number[] {
  for (let c = 0; c < m; c++) {
    let piv = c;
    for (let r = c + 1; r < m; r++) if (Math.abs(A[r][c]) > Math.abs(A[piv][c])) piv = r;
    [A[c], A[piv]] = [A[piv], A[c]];
    if (Math.abs(A[c][c]) < 1e-12) continue; // facteur constant : coefficient nul
    for (let r = 0; r < m; r++) {
      if (r === c) continue;
      const f = A[r][c] / A[c][c];
      for (let k = c; k <= m; k++) A[r][k] -= f * A[c][k];
    }
  }
  return A.map((row, i) => (Math.abs(row[i]) < 1e-12 ? 0 : row[m] / row[i]));
}

export interface Bin { x0: number; x1: number; count: number }

export function histogram(xs: number[], bins = 20): Bin[] {
  const v = xs.filter(Number.isFinite);
  if (!v.length) return [];
  let lo = Infinity, hi = -Infinity;
  for (const x of v) { if (x < lo) lo = x; if (x > hi) hi = x; }
  if (lo === hi) { lo -= 0.5; hi += 0.5; }
  const w = (hi - lo) / bins;
  const out: Bin[] = Array.from({ length: bins }, (_, i) => ({ x0: lo + i * w, x1: lo + (i + 1) * w, count: 0 }));
  for (const x of v) out[Math.min(bins - 1, Math.floor((x - lo) / w))].count++;
  return out;
}

/** Fonction de répartition de la loi de Fisher-Snedecor F(d1, d2). */
export function fCdf(x: number, d1: number, d2: number): number {
  if (x <= 0) return 0;
  return incompleteBeta((d1 * x) / (d1 * x + d2), d1 / 2, d2 / 2);
}

/** Intervalle de confiance de Wilson (95 %) pour une proportion. */
export function wilson(successes: number, n: number): [number, number] {
  if (n === 0) return [0, 1];
  const z = 1.959964;
  const ph = successes / n;
  const den = 1 + (z * z) / n;
  const centre = (ph + (z * z) / (2 * n)) / den;
  const half = (z * Math.sqrt((ph * (1 - ph)) / n + (z * z) / (4 * n * n))) / den;
  return [Math.max(0, centre - half), Math.min(1, centre + half)];
}
