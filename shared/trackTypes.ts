// Shared track/track-generation types, used by both client (rendering + local
// physics simulation) and server (deterministic seed-based track replay for
// multiplayer rounds, and difficulty/scoring metadata).

export interface Vec2 {
  x: number;
  y: number;
}

/** A moving / rotating / falling platform placed on top of a chunk. */
export interface PlatformSpec {
  kind: 'moving' | 'rotating' | 'falling' | 'static';
  cx: number;
  cy: number;
  width: number;
  height: number;
  angle: number;
  /** moving: amplitude in px along the motion axis. rotating: rad/s. falling: delay in ms before it drops. */
  param: number;
  /** moving platforms only: 0 = horizontal, 1 = vertical */
  axis?: 0 | 1;
  speed?: number;
}

export interface TrackChunk {
  /** One or more continuous polylines. Each is turned into a chain of static
   * trapezoid ground bodies, solid on the left-hand side of travel direction
   * (i.e. "below" for rightward-moving terrain). Multiple strips = gaps. */
  strips: Vec2[][];
  /** Optional roof strips (tunnels), thickened on the right-hand side (above). */
  ceilings?: Vec2[][];
  /** Pre-thickened static polygons for shapes the generic strip rule can't
   * express (loops, where solid material must face outward from a center). */
  explicitPolys?: Vec2[][];
  platforms?: PlatformSpec[];
  /** Static obstacles that crash the car on any contact (barriers, spikes). */
  hazards?: { cx: number; cy: number; width: number; height: number; angle: number }[];
  /** Place a checkpoint trigger at the end of this chunk (Solo mode only). */
  checkpoint?: boolean;
  endPoint: Vec2;
  endAngle: number;
  tag: string;
  requiresFlip?: boolean;
}

export interface GenContext {
  start: Vec2;
  angle: number;
  rng: () => number;
  /** 0 (trivial) .. 1 (extreme) */
  difficulty: number;
}

export type ChunkGenerator = (ctx: GenContext) => TrackChunk;

export interface LevelDefinition {
  id: number;
  name: string;
  environment: string;
  /** Sequence of obstacle-catalog ids composing this level. */
  pattern: string[];
  bronzeMs: number;
  silverMs: number;
  goldMs: number;
}

export interface ObstacleCatalogEntry {
  id: string;
  label: string;
  category: 'ramp' | 'gap' | 'platform' | 'tunnel' | 'loop' | 'wall' | 'terrain' | 'technical';
  minDifficulty: number;
  maxDifficulty: number;
}
