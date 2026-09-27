import { createNoise2D } from 'simplex-noise';
import { mulberry32 } from '../../../../shared/rng';
import {
  WORLD_RADIUS,
  SUMMIT_HEIGHT,
  SPIRAL_TURNS,
  SPIRAL_PATH_WIDTH,
  SPIRAL_CARVE_DEPTH,
  CHECKPOINT_COUNT,
  ITEM_DENSITY_RADIUS_STEP,
  WALK_MAX_SLOPE,
} from '../../../../shared/constants';

export type ItemType = 'berry' | 'chalk' | 'cloak' | 'anchor';

export interface PlacedItem {
  id: string;
  type: ItemType;
  pos: [number, number, number];
}

export interface Checkpoint {
  index: number;
  pos: [number, number, number];
}

const EPS = 0.75;

/**
 * Montagne procédurale déterministe par seed. heightAt()/normalAt() doivent
 * rester identiques entre tous les clients d'une même partie coop.
 *
 * Simplification assumée : le relief est un champ de hauteur (pas de vraies
 * cavités/surplombs) — l'escalade se joue sur des pentes raides, pas sous
 * des à-pics négatifs. Un "sentier" en spirale, creusé dans le relief, offre
 * toujours une route praticable jusqu'au sommet pour qui ne veut pas grimper.
 */
export class MountainGenerator {
  readonly seed: number;
  private noiseA: (x: number, y: number) => number;
  private noiseB: (x: number, y: number) => number;
  private noiseC: (x: number, y: number) => number;
  private pathPhase: number;

  constructor(seed: number) {
    this.seed = seed;
    const rngA = mulberry32(seed);
    const rngB = mulberry32(seed ^ 0x9e3779b9);
    const rngC = mulberry32(seed ^ 0x85ebca6b);
    this.noiseA = createNoise2D(rngA);
    this.noiseB = createNoise2D(rngB);
    this.noiseC = createNoise2D(rngC);
    this.pathPhase = rngA() * Math.PI * 2;
  }

  private pathFactorAt(x: number, z: number): number {
    const r = Math.hypot(x, z);
    const theta = Math.atan2(z, x);
    const idealTheta =
      (r / WORLD_RADIUS) * SPIRAL_TURNS * Math.PI * 2 + this.pathPhase;
    let d = theta - idealTheta;
    d = Math.atan2(Math.sin(d), Math.cos(d)); // wrap [-pi, pi]
    return Math.exp(-(d * d) / (2 * SPIRAL_PATH_WIDTH * SPIRAL_PATH_WIDTH));
  }

  heightAt(x: number, z: number): number {
    const r = Math.hypot(x, z);
    const rf = Math.min(1, r / WORLD_RADIUS);
    const cone = SUMMIT_HEIGHT * Math.pow(Math.max(0, 1 - rf), 1.25);

    const altitudeFrac = 1 - rf;
    // L'amplitude du relief croît avec l'altitude : contreforts doux près de la base,
    // parois plus accidentées près du sommet (évite un spawn cahoteux).
    const ridge =
      this.noiseA(x * 0.012, z * 0.012) * 20 * Math.pow(altitudeFrac, 0.8) +
      this.noiseB(x * 0.035, z * 0.035) * 9 * Math.pow(altitudeFrac, 0.6) +
      this.noiseC(x * 0.08, z * 0.08) * 2.5 * (0.15 + altitudeFrac * 0.85);

    const path = this.pathFactorAt(x, z);
    const smoothedRidge = ridge * (1 - path * 0.88);
    const carve = path * SPIRAL_CARVE_DEPTH * (0.3 + altitudeFrac * 0.9);

    const h = cone + smoothedRidge - carve;
    return Math.max(0, h);
  }

  normalAt(x: number, z: number): { nx: number; ny: number; nz: number; slope: number } {
    const hL = this.heightAt(x - EPS, z);
    const hR = this.heightAt(x + EPS, z);
    const hD = this.heightAt(x, z - EPS);
    const hU = this.heightAt(x, z + EPS);
    const dx = (hR - hL) / (2 * EPS);
    const dz = (hU - hD) / (2 * EPS);
    const len = Math.hypot(dx, 1, dz);
    const nx = -dx / len;
    const ny = 1 / len;
    const nz = -dz / len;
    const slope = Math.acos(Math.min(1, Math.max(-1, ny)));
    return { nx, ny, nz, slope };
  }

  isWalkable(x: number, z: number): boolean {
    return this.normalAt(x, z).slope <= WALK_MAX_SLOPE;
  }

  summitPosition(): [number, number, number] {
    return [0, this.heightAt(0, 0) + 0.5, 0];
  }

  private findWalkableNear(
    rng: () => number,
    targetR: number,
  ): [number, number, number] | null {
    for (let attempt = 0; attempt < 40; attempt++) {
      const theta = rng() * Math.PI * 2;
      const jitter = (rng() - 0.5) * 26;
      const r = Math.max(4, targetR + jitter);
      const x = Math.cos(theta) * r;
      const z = Math.sin(theta) * r;
      if (this.isWalkable(x, z)) {
        return [x, this.heightAt(x, z) + 0.1, z];
      }
    }
    return null;
  }

  generateCheckpoints(): Checkpoint[] {
    const rng = mulberry32(this.seed ^ 0x1234567);
    const checkpoints: Checkpoint[] = [];
    for (let i = 1; i <= CHECKPOINT_COUNT; i++) {
      const frac = i / (CHECKPOINT_COUNT + 1);
      const targetR = WORLD_RADIUS * (1 - frac) * 0.96;
      const pos = this.findWalkableNear(rng, targetR);
      if (pos) checkpoints.push({ index: i, pos });
    }
    return checkpoints;
  }

  generateItems(): PlacedItem[] {
    const rng = mulberry32(this.seed ^ 0x7f4a7c15);
    const items: PlacedItem[] = [];
    const rings = Math.floor(WORLD_RADIUS / ITEM_DENSITY_RADIUS_STEP);
    let id = 0;
    const types: ItemType[] = ['berry', 'berry', 'chalk', 'berry', 'anchor', 'cloak'];
    for (let ring = 0; ring < rings; ring++) {
      const targetR = WORLD_RADIUS - ring * ITEM_DENSITY_RADIUS_STEP;
      const perRing = 2 + Math.floor(rng() * 3);
      for (let i = 0; i < perRing; i++) {
        const pos = this.findWalkableNear(rng, targetR);
        if (!pos) continue;
        const type = types[Math.floor(rng() * types.length)];
        items.push({ id: `item_${id++}`, type, pos });
      }
    }
    return items;
  }
}
