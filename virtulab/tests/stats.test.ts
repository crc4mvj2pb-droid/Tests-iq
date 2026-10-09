import { describe, expect, it } from 'vitest';
import { Rng } from '../src/core/rng';
import { fCdf, histogram, mean, ols, oneSampleTTest, pearson, quantile, spearman, studentTCdf, studentTQuantile, summarize, welchTTest, wilson } from '../src/core/stats';

describe('statistiques', () => {
  it('quantiles de Student (tables de référence)', () => {
    expect(studentTQuantile(0.975, 10)).toBeCloseTo(2.228139, 5);
    expect(studentTQuantile(0.975, 1)).toBeCloseTo(12.7062, 3);
    expect(studentTCdf(0, 5)).toBeCloseTo(0.5, 10);
  });

  it('loi de Fisher (valeur critique F(2,10) à 95 % = 4,1028)', () => {
    expect(fCdf(4.1028, 2, 10)).toBeCloseTo(0.95, 4);
  });

  it('test t à un échantillon', () => {
    const r = oneSampleTTest([5.1, 4.9, 5.3, 5.0, 5.2], 5);
    expect(r.t).toBeCloseTo(1.4142, 3);
    expect(r.pValue).toBeCloseTo(0.2302, 3);
  });

  it('test de Welch détecte une différence nette', () => {
    expect(welchTTest([1, 2, 3, 4, 5], [11, 12, 13, 14, 15]).pValue).toBeLessThan(1e-4);
  });

  it('résumé et intervalle de confiance', () => {
    const s = summarize([1, 2, 3, 4, 5]);
    expect(s.mean).toBe(3);
    expect(s.median).toBe(3);
    expect(s.sd).toBeCloseTo(Math.sqrt(2.5), 12);
    expect(s.ciHigh - s.mean).toBeCloseTo(2.776445 * Math.sqrt(2.5) / Math.sqrt(5), 4);
    expect(quantile([0, 10], 0.25)).toBe(2.5);
  });

  it('régression multiple exacte', () => {
    const X = [[1, 2], [2, 1], [3, 5], [4, 3], [5, 4]];
    const y = X.map(([a, b]) => 3 + 2 * a - b);
    const r = ols(X, y);
    expect(r.coefficients[0]).toBeCloseTo(3, 8);
    expect(r.coefficients[1]).toBeCloseTo(2, 8);
    expect(r.coefficients[2]).toBeCloseTo(-1, 8);
    expect(r.r2).toBeCloseTo(1, 10);
  });

  it('corrélations', () => {
    const x = [1, 2, 3, 4, 5];
    expect(pearson(x, x.map((v) => 2 * v + 1))).toBeCloseTo(1, 12);
    expect(spearman(x, x.map((v) => Math.exp(v)))).toBeCloseTo(1, 12);
    expect(spearman(x, x.map((v) => -(v ** 3)))).toBeCloseTo(-1, 12);
  });

  it('intervalle de Wilson', () => {
    const [lo, hi] = wilson(50, 100);
    expect(lo).toBeCloseTo(0.4038, 3);
    expect(hi).toBeCloseTo(0.5962, 3);
  });

  it('histogramme conserve les effectifs', () => {
    const xs = Array.from({ length: 1000 }, (_, i) => Math.sin(i));
    expect(histogram(xs, 17).reduce((a, b) => a + b.count, 0)).toBe(1000);
  });

  it('générateur : reproductible et de loi normale correcte', () => {
    const a = new Rng(42), b = new Rng(42);
    for (let i = 0; i < 10; i++) expect(a.next()).toBe(b.next());
    const r = new Rng(7);
    const xs = Array.from({ length: 50000 }, () => r.normal(10, 2));
    expect(mean(xs)).toBeCloseTo(10, 1);
    expect(summarize(xs).sd).toBeCloseTo(2, 1);
  });
});
