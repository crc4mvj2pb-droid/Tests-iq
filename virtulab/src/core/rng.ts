/**
 * Générateur pseudo-aléatoire déterministe (mulberry32) : une même graine
 * reproduit exactement la même expérience, condition de la reproductibilité.
 */
export class Rng {
  private state: number;

  constructor(seed: number) {
    this.state = seed >>> 0 || 0x9e3779b9;
  }

  next(): number {
    let t = (this.state = (this.state + 0x6d2b79f5) >>> 0);
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  }

  uniform(min: number, max: number): number {
    return min + (max - min) * this.next();
  }

  /** Loi normale par Box-Muller. */
  normal(mean = 0, sd = 1): number {
    let u = 0;
    while (u === 0) u = this.next();
    const v = this.next();
    return mean + sd * Math.sqrt(-2 * Math.log(u)) * Math.cos(2 * Math.PI * v);
  }

  /** Graine dérivée pour un sous-flux indépendant (ex. un run donné). */
  fork(index: number): Rng {
    return new Rng(Math.imul(this.state ^ (index + 1), 2654435761) ^ (index * 40503));
  }
}
