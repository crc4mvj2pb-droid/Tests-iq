import * as THREE from 'three';
import { mulberry32, randRange } from '@shared/rng';
import { Noise2D } from './noise';

export const MOUNTAIN_RADIUS = 240;
export const PEAK_HEIGHT = 152;
export const GRID_SEGMENTS = 168;

// Radial control points from the outer edge (r=1) in to the summit (r=0).
// Big height jumps over a small radius delta become steep cliffs; small
// height jumps over a big radius delta become walkable ledges. This one
// profile is what produces the base camp -> cliff -> ledge -> cliff ->
// snowfield -> summit structure of the whole climb.
const CONTROL: [number, number][] = [
  [1.0, 0],
  [0.88, 8],
  [0.78, 44],
  [0.64, 52],
  [0.5, 100],
  [0.35, 110],
  [0.19, 144],
  [0.0, PEAK_HEIGHT],
];

function smootherstep(t: number): number {
  const c = Math.min(1, Math.max(0, t));
  return c * c * c * (c * (c * 6 - 15) + 10);
}

interface Gully {
  angle: number;
  halfWidth: number;
  rInner: number;
  rOuter: number;
}

export type Biome = 'grass' | 'rock' | 'snow' | 'gully';

export class Mountain {
  readonly seed: number;
  private noise: Noise2D;
  private detailNoise: Noise2D;
  private gullies: Gully[] = [];
  private segSlope: number[] = [];

  constructor(seed: number) {
    this.seed = seed;
    this.noise = new Noise2D(seed);
    this.detailNoise = new Noise2D(seed ^ 0x9e3779b9);

    const rand = mulberry32(seed + 1);
    const gullyCount = 2;
    for (let i = 0; i < gullyCount; i++) {
      this.gullies.push({
        angle: randRange(rand, 0, Math.PI * 2),
        halfWidth: randRange(rand, 0.09, 0.14),
        rInner: 0.14,
        rOuter: randRange(rand, 0.62, 0.8),
      });
    }

    for (let i = 0; i < CONTROL.length - 1; i++) {
      const [r0, h0] = CONTROL[i];
      const [r1, h1] = CONTROL[i + 1];
      const run = Math.max(0.001, (r0 - r1) * MOUNTAIN_RADIUS);
      this.segSlope.push(Math.abs(h1 - h0) / run);
    }
  }

  private angularDist(a: number, b: number): number {
    let d = Math.abs(a - b) % (Math.PI * 2);
    if (d > Math.PI) d = Math.PI * 2 - d;
    return d;
  }

  private sampleRadial(rn: number): { height: number; ruggedness: number } {
    const clamped = Math.min(1, Math.max(0, rn));
    for (let i = 0; i < CONTROL.length - 1; i++) {
      const [r0, h0] = CONTROL[i];
      const [r1, h1] = CONTROL[i + 1];
      if (clamped <= r0 && clamped >= r1) {
        const t = (r0 - clamped) / Math.max(0.0001, r0 - r1);
        const height = h0 + (h1 - h0) * smootherstep(t);
        const slope = this.segSlope[i];
        const ruggedness = 1.5 + Math.min(1, slope / 1.4) * 7;
        return { height, ruggedness };
      }
    }
    return { height: CONTROL[CONTROL.length - 1][1], ruggedness: 6 };
  }

  private gullyCarve(x: number, z: number, rn: number, angle: number): number {
    let carve = 0;
    for (const g of this.gullies) {
      if (rn < g.rInner || rn > g.rOuter) continue;
      const ad = this.angularDist(angle, g.angle);
      if (ad > g.halfWidth * 2.2) continue;
      const angFalloff = 1 - smootherstep(ad / (g.halfWidth * 2.2));
      const radialFalloff = smootherstep((rn - g.rInner) / 0.06) * (1 - smootherstep((rn - (g.rOuter - 0.08)) / 0.08));
      carve = Math.max(carve, angFalloff * radialFalloff);
    }
    return carve;
  }

  isInGully(x: number, z: number): boolean {
    const r = Math.sqrt(x * x + z * z);
    const rn = r / MOUNTAIN_RADIUS;
    const angle = Math.atan2(z, x);
    return this.gullyCarve(x, z, rn, angle) > 0.35;
  }

  getHeight(x: number, z: number): number {
    const r = Math.sqrt(x * x + z * z);
    const rn = r / MOUNTAIN_RADIUS;
    const { height, ruggedness } = this.sampleRadial(rn);

    const warpAngle = Math.atan2(z, x);
    const warp = this.noise.fbm(Math.cos(warpAngle) * 1.6, Math.sin(warpAngle) * 1.6, 3) * 0.1;
    const warpedRn = Math.max(0, rn * (1 + warp));
    const shaped = this.sampleRadial(warpedRn);

    const detail = this.detailNoise.fbm(x * 0.045, z * 0.045, 5, 2.05, 0.52) * shaped.ruggedness;
    const fineGrain = this.noise.fbm(x * 0.22, z * 0.22, 2) * 0.6;

    const carve = this.gullyCarve(x, z, rn, warpAngle) * 9;

    const edgeFade = rn > 1 ? Math.max(0, 1 - (rn - 1) * 5) : 1;

    return shaped.height * edgeFade + (detail + fineGrain) * edgeFade - carve;
  }

  getNormal(x: number, z: number, d = 0.6): THREE.Vector3 {
    const hL = this.getHeight(x - d, z);
    const hR = this.getHeight(x + d, z);
    const hD = this.getHeight(x, z - d);
    const hU = this.getHeight(x, z + d);
    return new THREE.Vector3(hL - hR, 2 * d, hD - hU).normalize();
  }

  getSlopeDeg(x: number, z: number): number {
    const n = this.getNormal(x, z);
    return (Math.acos(Math.min(1, Math.max(-1, n.y))) * 180) / Math.PI;
  }

  getBiome(x: number, z: number, y: number): Biome {
    if (this.isInGully(x, z)) return 'gully';
    if (y > 118) return 'snow';
    if (y > 16) return 'rock';
    return 'grass';
  }

  basePos(): THREE.Vector3 {
    const angle = 0.6;
    const r = MOUNTAIN_RADIUS * 0.93;
    const x = Math.cos(angle) * r;
    const z = Math.sin(angle) * r;
    return new THREE.Vector3(x, this.getHeight(x, z), z);
  }

  summitPos(): THREE.Vector3 {
    return new THREE.Vector3(0, this.getHeight(0.001, 0.001), 0.001);
  }

  altitudePct(y: number): number {
    const base = this.basePos().y;
    return Math.max(0, Math.min(100, ((y - base) / (PEAK_HEIGHT - base)) * 100));
  }

  buildMesh(): THREE.Mesh {
    const seg = GRID_SEGMENTS;
    const size = MOUNTAIN_RADIUS * 2.05;
    const geo = new THREE.PlaneGeometry(size, size, seg, seg);
    geo.rotateX(-Math.PI / 2);

    const pos = geo.attributes.position as THREE.BufferAttribute;
    const colors = new Float32Array(pos.count * 3);
    const grassCol = new THREE.Color('#4f7c3c');
    const grassCol2 = new THREE.Color('#3f6a30');
    const rockCol = new THREE.Color('#84796c');
    const rockCol2 = new THREE.Color('#655c52');
    const snowCol = new THREE.Color('#f4f8ff');
    const gullyCol = new THREE.Color('#403c3f');
    const tmp = new THREE.Color();

    for (let i = 0; i < pos.count; i++) {
      const x = pos.getX(i);
      const z = pos.getZ(i);
      const y = this.getHeight(x, z);
      pos.setY(i, y);

      const slope = this.getSlopeDeg(x, z);
      const rockFactor = smootherstep((slope - 32) / 28);
      const inGully = this.isInGully(x, z);
      const grain = this.noise.fbm(x * 0.08, z * 0.08, 2);

      let base: THREE.Color;
      if (y > 120) {
        base = tmp.copy(snowCol).lerp(rockCol, smootherstep((122 - y) / 10) * 0.5 + rockFactor * 0.15);
      } else if (y > 14) {
        base = tmp.copy(rockCol).lerp(rockCol2, (grain + 1) * 0.5);
        base.lerp(grassCol, Math.max(0, 1 - rockFactor) * smootherstep((18 - y) / 6));
      } else {
        base = tmp.copy(grassCol).lerp(grassCol2, (grain + 1) * 0.5);
        base.lerp(rockCol, rockFactor);
      }
      if (inGully) base = base.clone().lerp(gullyCol, 0.55);

      colors[i * 3] = base.r;
      colors[i * 3 + 1] = base.g;
      colors[i * 3 + 2] = base.b;
    }

    geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
    geo.computeVertexNormals();

    const mat = new THREE.MeshStandardMaterial({
      vertexColors: true,
      flatShading: false,
      roughness: 1,
      metalness: 0,
    });
    const mesh = new THREE.Mesh(geo, mat);
    mesh.receiveShadow = true;
    mesh.castShadow = true;
    mesh.name = 'mountain';
    return mesh;
  }
}
