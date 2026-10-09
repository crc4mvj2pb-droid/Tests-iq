import { describe, expect, it } from 'vitest';
import { MODELS } from '../src/models';
import { defaults } from '../src/models/types';

describe.each(MODELS.map((m) => [m.id, m] as const))('modèle %s', (_id, model) => {
  it.each(model.validation.map((v) => [v.name, v] as const))('validation : %s', (_name, v) => {
    const { expected, obtained } = v.run();
    expect(Math.abs(obtained - expected) / Math.abs(expected)).toBeLessThanOrEqual(v.tolerance);
  });

  it('produit des indicateurs finis aux conditions nominales', () => {
    const out = model.simulate(defaults(model));
    for (const m of model.metrics) expect(Number.isFinite(out.metrics[m.key]), m.key).toBe(true);
    for (const s of model.series) expect(out.series[s.key]?.length, s.key).toBe(out.t.length);
  });

  it('reste stable aux bornes des paramètres', () => {
    for (const bound of ['min', 'max'] as const) {
      for (const p of model.params) {
        const out = model.simulate({ ...defaults(model), [p.key]: p[bound] });
        const bad = model.metrics.filter((m) => !Number.isFinite(out.metrics[m.key]) && m.key !== 'period');
        expect(bad.map((m) => m.key), `${p.key}=${p[bound]}`).toEqual([]);
      }
    }
  });

  it('a des valeurs par défaut dans les plages déclarées', () => {
    for (const p of model.params) {
      expect(p.default).toBeGreaterThanOrEqual(p.min);
      expect(p.default).toBeLessThanOrEqual(p.max);
    }
  });
});

describe('comportements physiques attendus', () => {
  const get = (id: string) => MODELS.find((m) => m.id === id)!;

  it('balistique : la traînée réduit la portée et l\'angle optimal passe sous 45°', () => {
    const m = get('projectile');
    const base = defaults(m);
    const range = (angle: number, cd = base.cd) => m.simulate({ ...base, h0: 0, angle, cd }).metrics.range;
    expect(range(45)).toBeLessThan(range(45, 0));
    expect(range(40)).toBeGreaterThan(range(50));
  });

  it('épidémie : la vaccination réduit le taux d\'attaque', () => {
    const m = get('seir');
    const base = defaults(m);
    expect(m.simulate({ ...base, vaccination: 50 }).metrics.attackRate).toBeLessThan(m.simulate(base).metrics.attackRate);
  });

  it('paroi : un isolant réduit le flux de chaleur', () => {
    const m = get('wall');
    const base = defaults(m);
    expect(m.simulate({ ...base, k: 0.035 }).metrics.avgFlux).toBeLessThan(m.simulate(base).metrics.avgFlux / 10);
  });

  it('chémostat : lessivage au-delà du taux de dilution critique', () => {
    const m = get('bioreactor');
    const out = m.simulate({ ...defaults(m), dilution: 0.6, duration: 300 });
    expect(out.metrics.washout).toBe(1);
    expect(out.metrics.biomass).toBeLessThan(0.01);
  });

  it('réacteur : refroidissement nul et charge élevée déclenchent l\'emballement', () => {
    const m = get('reactor');
    expect(m.simulate({ ...defaults(m), a0: 4, ua: 0.2 }).metrics.runaway).toBe(1);
    expect(m.simulate(defaults(m)).metrics.runaway).toBe(0);
  });
});
