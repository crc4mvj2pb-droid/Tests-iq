import type { ChunkGenerator, GenContext, ObstacleCatalogEntry, TrackChunk, Vec2 } from '@shared/trackTypes';
import { arc, buildLoop, wave } from './builders';

function jitter(ctx: GenContext, base: number, spread: number): number {
  return base + (ctx.rng() * 2 - 1) * spread;
}

function flatChunk(ctx: GenContext, length: number, tag: string, extra: Partial<TrackChunk> = {}): TrackChunk {
  const res = arc(ctx.start, ctx.angle, length, 0, 2);
  return { strips: [res.points], endPoint: res.end, endAngle: res.endAngle, tag, ...extra };
}

// ---------------------------------------------------------------- RAMPS ----
function rampGen(length: number, peakAngle: number, bumps = 1): ChunkGenerator {
  return (ctx) => {
    let cursor: Vec2 = ctx.start;
    let a = ctx.angle;
    const points: Vec2[] = [cursor];
    const segLen = length / (bumps * 2);
    for (let i = 0; i < bumps; i++) {
      const up = arc(cursor, a, segLen, peakAngle, 6);
      points.push(...up.points.slice(1));
      const down = arc(up.end, up.endAngle, segLen, -peakAngle, 6);
      points.push(...down.points.slice(1));
      cursor = down.end;
      a = down.endAngle;
    }
    return { strips: [points], endPoint: cursor, endAngle: a, tag: 'ramp' };
  };
}

function launchRampGen(length: number, peakAngle: number): ChunkGenerator {
  return (ctx) => {
    const res = arc(ctx.start, ctx.angle, length, peakAngle, 8);
    return { strips: [res.points], endPoint: res.end, endAngle: res.endAngle, tag: 'launch_ramp' };
  };
}

// ----------------------------------------------------------------- GAPS ----
function gapGen(length: number): ChunkGenerator {
  return (ctx) => {
    const end: Vec2 = { x: ctx.start.x + Math.cos(ctx.angle) * length, y: ctx.start.y + Math.sin(ctx.angle) * length };
    return { strips: [], endPoint: end, endAngle: ctx.angle, tag: 'gap' };
  };
}

function multiGapGen(gapLen: number, padLen: number, count: number): ChunkGenerator {
  return (ctx) => {
    let cursor = ctx.start;
    const strips: Vec2[][] = [];
    for (let i = 0; i < count; i++) {
      cursor = { x: cursor.x + Math.cos(ctx.angle) * gapLen, y: cursor.y + Math.sin(ctx.angle) * gapLen };
      if (i < count - 1) {
        const padEnd = { x: cursor.x + Math.cos(ctx.angle) * padLen, y: cursor.y + Math.sin(ctx.angle) * padLen };
        strips.push([cursor, padEnd]);
        cursor = padEnd;
      }
    }
    return { strips, endPoint: cursor, endAngle: ctx.angle, tag: 'multi_gap' };
  };
}

// ------------------------------------------------------------- PLATFORMS ---
function flatGen(length: number, tag = 'flat'): ChunkGenerator {
  return (ctx) => flatChunk(ctx, length, tag);
}

function inclinedPlatformGen(length: number, tilt: number): ChunkGenerator {
  return (ctx) => {
    const res = arc(ctx.start, ctx.angle, length, 0, 2);
    const tilted = res.points.map((p, i) => ({ x: p.x, y: p.y + i * tilt }));
    return { strips: [tilted], endPoint: res.end, endAngle: res.endAngle, tag: 'inclined_platform' };
  };
}

function movingPlatformGen(width: number, amplitude: number, axis: 0 | 1, speed: number): ChunkGenerator {
  return (ctx) => {
    const gapLen = width + amplitude * 2 + 60;
    const end: Vec2 = { x: ctx.start.x + Math.cos(ctx.angle) * gapLen, y: ctx.start.y + Math.sin(ctx.angle) * gapLen };
    const cx = ctx.start.x + Math.cos(ctx.angle) * (gapLen / 2);
    const cy = ctx.start.y + Math.sin(ctx.angle) * (gapLen / 2) - 20;
    return {
      strips: [],
      platforms: [{ kind: 'moving', cx, cy, width, height: 26, angle: 0, param: amplitude, axis, speed }],
      endPoint: end,
      endAngle: ctx.angle,
      tag: 'moving_platform',
    };
  };
}

function fallingPlatformGen(width: number, delayMs: number): ChunkGenerator {
  return (ctx) => {
    const len = width + 140;
    const end: Vec2 = { x: ctx.start.x + Math.cos(ctx.angle) * len, y: ctx.start.y + Math.sin(ctx.angle) * len };
    const cx = ctx.start.x + Math.cos(ctx.angle) * (len / 2);
    const cy = ctx.start.y + Math.sin(ctx.angle) * (len / 2);
    return {
      strips: [],
      platforms: [{ kind: 'falling', cx, cy, width, height: 26, angle: 0, param: delayMs }],
      endPoint: end,
      endAngle: ctx.angle,
      tag: 'falling_platform',
    };
  };
}

function rotatingPlatformGen(width: number, speed: number): ChunkGenerator {
  return (ctx) => {
    const len = width + 160;
    const end: Vec2 = { x: ctx.start.x + Math.cos(ctx.angle) * len, y: ctx.start.y + Math.sin(ctx.angle) * len };
    const cx = ctx.start.x + Math.cos(ctx.angle) * (len / 2);
    const cy = ctx.start.y + Math.sin(ctx.angle) * (len / 2);
    return {
      strips: [],
      platforms: [{ kind: 'rotating', cx, cy, width, height: 22, angle: 0, param: speed }],
      endPoint: end,
      endAngle: ctx.angle,
      tag: 'rotating_platform',
    };
  };
}

function separatedPlatformsGen(count: number, padLen: number, gapLen: number, heightJitter: number): ChunkGenerator {
  return (ctx) => {
    let cursor = ctx.start;
    const strips: Vec2[][] = [];
    for (let i = 0; i < count; i++) {
      const yOff = i % 2 === 0 ? 0 : heightJitter;
      const a = { x: cursor.x, y: cursor.y - yOff };
      const b: Vec2 = { x: a.x + Math.cos(ctx.angle) * padLen, y: a.y + Math.sin(ctx.angle) * padLen };
      strips.push([a, b]);
      cursor = { x: b.x + Math.cos(ctx.angle) * gapLen, y: b.y + Math.sin(ctx.angle) * gapLen };
    }
    return { strips, endPoint: cursor, endAngle: ctx.angle, tag: 'separated_platforms' };
  };
}

// --------------------------------------------------------------- TUNNELS ---
function tunnelGen(length: number, clearance: number, floorAngleDelta = 0): ChunkGenerator {
  return (ctx) => {
    const floor = arc(ctx.start, ctx.angle, length, floorAngleDelta, 8);
    const ceiling = floor.points.map((p) => {
      const n = { x: -Math.sin(ctx.angle), y: Math.cos(ctx.angle) };
      return { x: p.x - n.x * clearance, y: p.y - n.y * clearance };
    });
    return { strips: [floor.points], ceilings: [ceiling], endPoint: floor.end, endAngle: floor.endAngle, tag: 'tunnel' };
  };
}

// --------------------------------------------------------- WALLS/HAZARDS ---
function barrierGen(height: number, count = 1, spacing = 140): ChunkGenerator {
  return (ctx) => {
    const totalLen = 100 + count * spacing;
    const floor = arc(ctx.start, ctx.angle, totalLen, 0, 2);
    const hazards = [];
    for (let i = 0; i < count; i++) {
      const d = 100 + i * spacing;
      hazards.push({
        cx: ctx.start.x + Math.cos(ctx.angle) * d,
        cy: ctx.start.y + Math.sin(ctx.angle) * d - height / 2 - 30,
        width: 16,
        height,
        angle: ctx.angle,
      });
    }
    return { strips: [floor.points], hazards, endPoint: floor.end, endAngle: floor.endAngle, tag: 'barrier' };
  };
}

// ---------------------------------------------------------------- WAVES ----
function bumpsGen(length: number, amplitude: number, cycles: number): ChunkGenerator {
  return (ctx) => {
    const res = wave(ctx.start, ctx.angle, length, amplitude, cycles);
    return { strips: [res.points], endPoint: res.end, endAngle: res.endAngle, tag: 'bumps' };
  };
}

// ---------------------------------------------------------------- LOOPS ----
function loopGen(radius: number, arcFraction: number): ChunkGenerator {
  return (ctx) => {
    const res = buildLoop(ctx.start, ctx.angle, radius, arcFraction, 46, 30);
    return { strips: [], explicitPolys: res.polys, endPoint: res.end, endAngle: res.endAngle, tag: 'loop' };
  };
}

function loopSeriesGen(radius: number, count: number): ChunkGenerator {
  return (ctx) => {
    let cursor = ctx.start;
    let angle = ctx.angle;
    const polys: Vec2[][] = [];
    for (let i = 0; i < count; i++) {
      const gapRes = arc(cursor, angle, 40, 0, 1);
      cursor = gapRes.end;
      const res = buildLoop(cursor, angle, radius, 1, 46, 30);
      polys.push(...res.polys);
      cursor = res.end;
      angle = res.endAngle;
    }
    return { strips: [], explicitPolys: polys, endPoint: cursor, endAngle: angle, tag: 'loop_series' };
  };
}

// ------------------------------------------------------- FLIP CHALLENGES ---
function flipGapGen(rampLen: number, peakAngle: number, gapLen: number, requiresFlip: boolean): ChunkGenerator {
  return (ctx) => {
    const up = arc(ctx.start, ctx.angle, rampLen, peakAngle, 8);
    const gapEnd: Vec2 = { x: up.end.x + Math.cos(up.endAngle) * gapLen, y: up.end.y + Math.sin(up.endAngle) * gapLen };
    const landing = arc(gapEnd, up.endAngle, 140, -peakAngle, 8);
    return {
      strips: [up.points, landing.points],
      endPoint: landing.end,
      endAngle: landing.endAngle,
      tag: 'flip_gap',
      requiresFlip,
    };
  };
}

// -------------------------------------------------------------- CATALOG ----
interface CatalogItem extends ObstacleCatalogEntry {
  gen: ChunkGenerator;
}

export const CATALOG: CatalogItem[] = [
  { id: 'ramp_small', label: 'Petite rampe', category: 'ramp', minDifficulty: 0, maxDifficulty: 1, gen: launchRampGen(90, -0.32) },
  { id: 'ramp_medium', label: 'Rampe moyenne', category: 'ramp', minDifficulty: 0.1, maxDifficulty: 1, gen: launchRampGen(120, -0.45) },
  { id: 'ramp_large', label: 'Grande rampe', category: 'ramp', minDifficulty: 0.2, maxDifficulty: 1, gen: launchRampGen(150, -0.58) },
  { id: 'ramp_double', label: 'Double rampe', category: 'ramp', minDifficulty: 0.2, maxDifficulty: 1, gen: rampGen(220, -0.4, 2) },
  { id: 'ramp_triple', label: 'Triple rampe', category: 'ramp', minDifficulty: 0.35, maxDifficulty: 1, gen: rampGen(320, -0.38, 3) },
  { id: 'mega_jump', label: 'Méga tremplin', category: 'ramp', minDifficulty: 0.4, maxDifficulty: 1, gen: launchRampGen(190, -0.72) },
  { id: 'series_ramps', label: 'Série de rampes', category: 'ramp', minDifficulty: 0.3, maxDifficulty: 1, gen: rampGen(360, -0.3, 4) },
  { id: 'gros_tremplin', label: 'Gros tremplin', category: 'ramp', minDifficulty: 0.35, maxDifficulty: 1, gen: launchRampGen(170, -0.68) },

  { id: 'gap_small', label: 'Petit gap', category: 'gap', minDifficulty: 0, maxDifficulty: 1, gen: gapGen(100) },
  { id: 'gap_medium', label: 'Gap moyen', category: 'gap', minDifficulty: 0.1, maxDifficulty: 1, gen: gapGen(150) },
  { id: 'gap_large', label: 'Grand gap', category: 'gap', minDifficulty: 0.2, maxDifficulty: 1, gen: gapGen(190) },
  { id: 'gap_huge', label: 'Énorme gap', category: 'gap', minDifficulty: 0.4, maxDifficulty: 1, gen: gapGen(280) },
  { id: 'gap_double', label: 'Double gap', category: 'gap', minDifficulty: 0.3, maxDifficulty: 1, gen: multiGapGen(140, 60, 2) },
  { id: 'gap_triple', label: 'Triple gap', category: 'gap', minDifficulty: 0.45, maxDifficulty: 1, gen: multiGapGen(120, 50, 3) },

  { id: 'platform_wide', label: 'Plateforme large', category: 'platform', minDifficulty: 0, maxDifficulty: 1, gen: flatGen(240, 'platform_wide') },
  { id: 'platform_narrow', label: 'Plateforme étroite', category: 'platform', minDifficulty: 0.25, maxDifficulty: 1, gen: flatGen(80, 'platform_narrow') },
  { id: 'platform_tiny_landing', label: "Plateforme d'atterrissage minuscule", category: 'platform', minDifficulty: 0.5, maxDifficulty: 1, gen: flatGen(56, 'platform_tiny') },
  { id: 'platform_inclined', label: 'Plateforme inclinée', category: 'platform', minDifficulty: 0.15, maxDifficulty: 1, gen: inclinedPlatformGen(170, 0.55) },
  { id: 'platform_moving_h', label: 'Plateforme mobile', category: 'platform', minDifficulty: 0.3, maxDifficulty: 1, gen: movingPlatformGen(140, 70, 0, 1.1) },
  { id: 'platform_moving_v', label: 'Plateforme mobile verticale', category: 'platform', minDifficulty: 0.35, maxDifficulty: 1, gen: movingPlatformGen(130, 40, 1, 1.4) },
  { id: 'platform_falling', label: 'Plateforme qui tombe', category: 'platform', minDifficulty: 0.3, maxDifficulty: 1, gen: fallingPlatformGen(140, 260) },
  { id: 'platform_rotating', label: 'Plateforme rotative', category: 'platform', minDifficulty: 0.4, maxDifficulty: 1, gen: rotatingPlatformGen(150, 0.9) },
  { id: 'platform_suspended', label: 'Plateforme suspendue', category: 'platform', minDifficulty: 0.35, maxDifficulty: 1, gen: flatGen(70, 'platform_suspended') },
  { id: 'platforms_separated', label: 'Plateformes séparées', category: 'platform', minDifficulty: 0.35, maxDifficulty: 1, gen: separatedPlatformsGen(3, 70, 90, 0) },
  { id: 'platforms_alternating', label: 'Plateformes alternées', category: 'platform', minDifficulty: 0.45, maxDifficulty: 1, gen: separatedPlatformsGen(4, 65, 85, 45) },

  { id: 'tunnel', label: 'Tunnel', category: 'tunnel', minDifficulty: 0.1, maxDifficulty: 1, gen: tunnelGen(260, 150) },
  { id: 'tunnel_narrow', label: 'Tunnel étroit', category: 'tunnel', minDifficulty: 0.3, maxDifficulty: 1, gen: tunnelGen(240, 115) },
  { id: 'tunnel_low_ceiling', label: 'Tunnel plafond bas', category: 'tunnel', minDifficulty: 0.45, maxDifficulty: 1, gen: tunnelGen(300, 95) },
  { id: 'tunnel_ramp', label: 'Tunnel en pente', category: 'tunnel', minDifficulty: 0.35, maxDifficulty: 1, gen: tunnelGen(260, 140, 0.25) },
  { id: 'plafond_bas', label: 'Plafond bas', category: 'tunnel', minDifficulty: 0.4, maxDifficulty: 1, gen: tunnelGen(200, 100) },
  { id: 'passage_etroit', label: 'Passage très étroit', category: 'tunnel', minDifficulty: 0.5, maxDifficulty: 1, gen: tunnelGen(220, 88) },

  { id: 'wall_vertical', label: 'Mur vertical', category: 'wall', minDifficulty: 0.25, maxDifficulty: 1, gen: barrierGen(120, 1) },
  { id: 'wall_inclined', label: 'Mur incliné', category: 'wall', minDifficulty: 0.3, maxDifficulty: 1, gen: barrierGen(100, 1, 160) },
  { id: 'barrier_low', label: 'Barrière basse', category: 'wall', minDifficulty: 0.15, maxDifficulty: 1, gen: barrierGen(55, 1) },
  { id: 'barrier_high', label: 'Barrière haute', category: 'wall', minDifficulty: 0.35, maxDifficulty: 1, gen: barrierGen(150, 1) },
  { id: 'barrier_series', label: 'Série de barrières', category: 'wall', minDifficulty: 0.4, maxDifficulty: 1, gen: barrierGen(90, 3, 130) },
  { id: 'barriere', label: 'Barrière', category: 'wall', minDifficulty: 0.2, maxDifficulty: 1, gen: barrierGen(80, 1) },

  { id: 'small_bump', label: 'Bosses', category: 'terrain', minDifficulty: 0, maxDifficulty: 1, gen: bumpsGen(200, 0.22, 2) },
  { id: 'roller', label: 'Rouleau', category: 'terrain', minDifficulty: 0.1, maxDifficulty: 1, gen: bumpsGen(240, 0.3, 1) },
  { id: 'big_roller', label: 'Gros rouleau', category: 'terrain', minDifficulty: 0.25, maxDifficulty: 1, gen: bumpsGen(300, 0.5, 1) },
  { id: 'zigzag', label: 'Passage en zigzag', category: 'technical', minDifficulty: 0.3, maxDifficulty: 1, gen: bumpsGen(260, 0.38, 4) },
  { id: 'fast_descent', label: 'Descente rapide', category: 'terrain', minDifficulty: 0.1, maxDifficulty: 1, gen: (ctx) => { const r = arc(ctx.start, ctx.angle, 260, 0.85, 10); return { strips: [r.points], endPoint: r.end, endAngle: r.endAngle, tag: 'fast_descent' }; } },
  { id: 'fast_climb', label: 'Montée rapide', category: 'terrain', minDifficulty: 0.15, maxDifficulty: 1, gen: (ctx) => { const r = arc(ctx.start, ctx.angle, 260, -0.75, 10); return { strips: [r.points], endPoint: r.end, endAngle: r.endAngle, tag: 'fast_climb' }; } },
  { id: 'long_descent', label: 'Longue descente', category: 'terrain', minDifficulty: 0.05, maxDifficulty: 1, gen: (ctx) => { const r = arc(ctx.start, ctx.angle, 420, 0.45, 12); return { strips: [r.points], endPoint: r.end, endAngle: r.endAngle, tag: 'long_descent' }; } },
  { id: 'long_climb', label: 'Longue montée', category: 'terrain', minDifficulty: 0.1, maxDifficulty: 1, gen: (ctx) => { const r = arc(ctx.start, ctx.angle, 420, -0.4, 12); return { strips: [r.points], endPoint: r.end, endAngle: r.endAngle, tag: 'long_climb' }; } },
  { id: 'sudden_height_change', label: 'Changement brutal de hauteur', category: 'terrain', minDifficulty: 0.3, maxDifficulty: 1, gen: (ctx) => { const r = arc(ctx.start, ctx.angle, 70, ctx.rng() > 0.5 ? 1.1 : -1.1, 6); return { strips: [r.points], endPoint: r.end, endAngle: r.endAngle, tag: 'sudden_height' }; } },
  { id: 'flat_recovery', label: 'Section de récupération', category: 'terrain', minDifficulty: 0, maxDifficulty: 1, gen: flatGen(200, 'flat_recovery') },
  { id: 'speed_straight', label: 'Ligne droite rapide', category: 'terrain', minDifficulty: 0, maxDifficulty: 1, gen: flatGen(340, 'speed_straight') },
  { id: 'plateau', label: 'Plateau élevé', category: 'terrain', minDifficulty: 0.1, maxDifficulty: 1, gen: flatGen(260, 'plateau') },
  { id: 's_curve', label: 'Courbe en S', category: 'technical', minDifficulty: 0.2, maxDifficulty: 1, gen: bumpsGen(260, 0.3, 2) },
  { id: 'technical_section', label: 'Section technique', category: 'technical', minDifficulty: 0.4, maxDifficulty: 1, gen: separatedPlatformsGen(3, 60, 70, 30) },
  { id: 'section_challenge_extreme', label: 'Section challenge extrême', category: 'technical', minDifficulty: 0.7, maxDifficulty: 1, gen: separatedPlatformsGen(4, 55, 95, 55) },

  { id: 'loop', label: 'Loop', category: 'loop', minDifficulty: 0.35, maxDifficulty: 1, gen: loopGen(130, 1) },
  { id: 'demi_loop', label: 'Demi-loop', category: 'loop', minDifficulty: 0.3, maxDifficulty: 1, gen: loopGen(120, 0.5) },
  { id: 'loop_inverse', label: 'Loop inversé', category: 'loop', minDifficulty: 0.45, maxDifficulty: 1, gen: loopGen(140, 1) },
  { id: 'loop_series', label: 'Série de loops', category: 'loop', minDifficulty: 0.6, maxDifficulty: 1, gen: loopSeriesGen(115, 2) },

  { id: 'flip_gap_single', label: 'Saut nécessitant un flip', category: 'technical', minDifficulty: 0.4, maxDifficulty: 1, gen: flipGapGen(150, -0.62, 220, true) },
  { id: 'flip_gap_double', label: 'Saut nécessitant un double flip', category: 'technical', minDifficulty: 0.65, maxDifficulty: 1, gen: flipGapGen(190, -0.78, 300, true) },

  { id: 'obstacle_chaos', label: 'Obstacle chaotique', category: 'technical', minDifficulty: 0.4, maxDifficulty: 1, gen: (ctx) => flatChunk(ctx, jitter(ctx, 150, 40), 'chaos') },
];

export const CATALOG_BY_ID = new Map(CATALOG.map((c) => [c.id, c]));

export function generateChunk(id: string, ctx: GenContext): TrackChunk {
  const item = CATALOG_BY_ID.get(id);
  if (!item) throw new Error(`Unknown obstacle id: ${id}`);
  return item.gen(ctx);
}
