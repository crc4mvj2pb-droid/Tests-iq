import { mulberry32 } from '@shared/rng';

// Seeded 2D Perlin-style gradient noise. Deterministic per seed so every
// player in a room generates the exact same mountain from the same number.
export class Noise2D {
  private perm = new Uint8Array(512);
  private grad: [number, number][] = [];

  constructor(seed: number) {
    const rand = mulberry32(seed);
    const p = new Uint8Array(256);
    for (let i = 0; i < 256; i++) p[i] = i;
    for (let i = 255; i > 0; i--) {
      const j = Math.floor(rand() * (i + 1));
      [p[i], p[j]] = [p[j], p[i]];
    }
    for (let i = 0; i < 512; i++) this.perm[i] = p[i & 255];
    for (let i = 0; i < 256; i++) {
      const a = rand() * Math.PI * 2;
      this.grad.push([Math.cos(a), Math.sin(a)]);
    }
  }

  private fade(t: number) {
    return t * t * t * (t * (t * 6 - 15) + 10);
  }

  private gradAt(hash: number, x: number, y: number) {
    const g = this.grad[hash & 255];
    return g[0] * x + g[1] * y;
  }

  noise(x: number, y: number): number {
    const X = Math.floor(x) & 255;
    const Y = Math.floor(y) & 255;
    const xf = x - Math.floor(x);
    const yf = y - Math.floor(y);
    const topRight = this.gradAt(this.perm[this.perm[X + 1] + Y + 1], xf - 1, yf - 1);
    const topLeft = this.gradAt(this.perm[this.perm[X] + Y + 1], xf, yf - 1);
    const bottomRight = this.gradAt(this.perm[this.perm[X + 1] + Y], xf - 1, yf);
    const bottomLeft = this.gradAt(this.perm[this.perm[X] + Y], xf, yf);
    const u = this.fade(xf);
    const v = this.fade(yf);
    const top = topLeft + u * (topRight - topLeft);
    const bottom = bottomLeft + u * (bottomRight - bottomLeft);
    return bottom + v * (top - bottom);
  }

  fbm(x: number, y: number, octaves = 4, lacunarity = 2.1, gain = 0.5): number {
    let amp = 1;
    let freq = 1;
    let sum = 0;
    let norm = 0;
    for (let i = 0; i < octaves; i++) {
      sum += this.noise(x * freq, y * freq) * amp;
      norm += amp;
      amp *= gain;
      freq *= lacunarity;
    }
    return sum / norm;
  }
}
