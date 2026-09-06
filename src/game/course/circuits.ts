export interface GroundSeg {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  angle: number; // radians, authored slope of this segment
  water?: boolean; // slow "swimming" surface instead of solid footing
}

export interface WallObstacle {
  x: number; // center
  y: number; // center
  w: number;
  h: number;
}

export interface Zipline {
  x0: number;
  x1: number;
  y: number;
}

export interface Spring {
  x0: number;
  x1: number;
}

export interface CircuitDef {
  id: string;
  name: string;
  theme: { sky: string; sky2: string; ground: string; accent: string };
  ground: GroundSeg[];
  walls: WallObstacle[];
  ziplines: Zipline[];
  springs: Spring[];
  startX: number;
  startY: number;
  finishX: number;
  checkpoints: number[];
  worldBottom: number;
  length: number;
}

type Piece =
  | { k: "flat"; len: number }
  | { k: "ramp"; len: number; deg: number }
  | { k: "gap"; len: number }
  | { k: "wall"; w: number; h: number }
  | { k: "bump"; len: number; height: number }
  | { k: "pool"; len: number; ropeHeight?: number }
  | { k: "spring"; len: number };

export const GROUND_Y0 = 520;
const DEFAULT_ROPE_HEIGHT = 95;

function build(pieces: Piece[]): { ground: GroundSeg[]; walls: WallObstacle[]; ziplines: Zipline[]; springs: Spring[]; endX: number } {
  let x = 0;
  let y = GROUND_Y0;
  const ground: GroundSeg[] = [];
  const walls: WallObstacle[] = [];
  const ziplines: Zipline[] = [];
  const springs: Spring[] = [];

  for (const p of pieces) {
    if (p.k === "flat") {
      const x1 = x + p.len;
      ground.push({ x0: x, y0: y, x1, y1: y, angle: 0 });
      x = x1;
    } else if (p.k === "ramp") {
      const rad = (p.deg * Math.PI) / 180;
      const x1 = x + p.len * Math.cos(rad);
      const y1 = y + p.len * Math.sin(rad);
      ground.push({ x0: x, y0: y, x1, y1, angle: rad });
      x = x1;
      y = y1;
    } else if (p.k === "gap") {
      x = x + p.len;
    } else if (p.k === "wall") {
      walls.push({ x: x + p.w / 2, y: y - p.h / 2, w: p.w, h: p.h });
      const x1 = x + p.w;
      ground.push({ x0: x, y0: y, x1, y1: y, angle: 0 });
      x = x1;
    } else if (p.k === "bump") {
      const half = p.len / 2;
      const upRad = Math.atan2(-p.height, half);
      const x1 = x + half * Math.cos(upRad);
      const y1 = y + half * Math.sin(upRad);
      ground.push({ x0: x, y0: y, x1, y1, angle: upRad });
      const downRad = Math.atan2(p.height, half);
      const x2 = x1 + half * Math.cos(downRad);
      const y2 = y1 + half * Math.sin(downRad);
      ground.push({ x0: x1, y0: y1, x1: x2, y1: y2, angle: downRad });
      x = x2;
      y = y2;
    } else if (p.k === "pool") {
      const x1 = x + p.len;
      ground.push({ x0: x, y0: y, x1, y1: y, angle: 0, water: true });
      ziplines.push({ x0: x, x1, y: y - (p.ropeHeight ?? DEFAULT_ROPE_HEIGHT) });
      x = x1;
    } else if (p.k === "spring") {
      // A springboard pad: touching it while running launches the player
      // into a much higher, longer arc than any manual jump can reach —
      // used to clear obstacles a normal jump physically cannot.
      const x1 = x + p.len;
      ground.push({ x0: x, y0: y, x1, y1: y, angle: 0 });
      springs.push({ x0: x, x1 });
      x = x1;
    }
  }
  return { ground, walls, ziplines, springs, endX: x };
}

function makeCircuit(
  id: string,
  name: string,
  theme: CircuitDef["theme"],
  pieces: Piece[],
  checkpointEvery = 900
): CircuitDef {
  const { ground, walls, ziplines, springs, endX } = build([{ k: "flat", len: 500 }, ...pieces, { k: "flat", len: 400 }]);
  const checkpoints: number[] = [];
  for (let cx = checkpointEvery; cx < endX - 300; cx += checkpointEvery) {
    if (groundYAt(ground, cx) !== null && !isWaterSegAt(ground, cx)) checkpoints.push(cx);
  }
  return {
    id,
    name,
    theme,
    ground,
    walls,
    ziplines,
    springs,
    startX: 120,
    startY: GROUND_Y0 - 60,
    finishX: endX - 250,
    checkpoints,
    worldBottom: GROUND_Y0 + 900,
    length: endX,
  };
}

export const CIRCUITS: CircuitDef[] = [
  makeCircuit(
    "verte",
    "Colline Verte",
    { sky: "#8fd3f4", sky2: "#4fb6e8", ground: "#3ea24a", accent: "#ffd166" },
    [
      { k: "flat", len: 140 },
      { k: "wall", w: 34, h: 44 },
      { k: "flat", len: 130 },
      { k: "wall", w: 34, h: 54 },
      { k: "flat", len: 90 },
      { k: "bump", len: 260, height: 70 },
      { k: "flat", len: 110 },
      { k: "wall", w: 34, h: 62 },
      { k: "flat", len: 18 },
      { k: "wall", w: 34, h: 58 },
      { k: "flat", len: 140 },
      { k: "gap", len: 185 },
      { k: "flat", len: 130 },
      { k: "wall", w: 34, h: 58 },
      { k: "flat", len: 90 },
      { k: "bump", len: 300, height: 100 },
      { k: "flat", len: 110 },
      { k: "wall", w: 40, h: 82 },
      { k: "flat", len: 130 },
      { k: "wall", w: 34, h: 60 },
      { k: "flat", len: 90 },
      { k: "ramp", len: 220, deg: -22 },
      { k: "flat", len: 80 },
      { k: "wall", w: 34, h: 40 },
      { k: "flat", len: 50 },
      { k: "ramp", len: 220, deg: 22 },
      { k: "flat", len: 140 },
      { k: "wall", w: 34, h: 66 },
      { k: "flat", len: 140 },
      { k: "gap", len: 215 },
      { k: "flat", len: 150 },
      { k: "wall", w: 34, h: 58 },
      { k: "flat", len: 18 },
      { k: "wall", w: 34, h: 58 },
      { k: "flat", len: 90 },
      { k: "bump", len: 340, height: 130 },
      { k: "flat", len: 60 },
      { k: "spring", len: 50 },
      { k: "gap", len: 280 },
      { k: "flat", len: 90 },
      { k: "wall", w: 34, h: 62 },
      { k: "flat", len: 18 },
      { k: "wall", w: 34, h: 58 },
      { k: "flat", len: 170 },
      { k: "pool", len: 340 },
      { k: "flat", len: 200 },
      { k: "spring", len: 50 },
      { k: "gap", len: 260 },
      { k: "flat", len: 300 },
    ]
  ),
  makeCircuit(
    "canyon",
    "Canyon Rouge",
    { sky: "#f5a35c", sky2: "#e0663f", ground: "#8a4a2b", accent: "#ff5d73" },
    [
      { k: "flat", len: 120 },
      { k: "wall", w: 36, h: 46 },
      { k: "flat", len: 120 },
      { k: "wall", w: 36, h: 56 },
      { k: "flat", len: 140 },
      { k: "gap", len: 220 },
      { k: "flat", len: 140 },
      { k: "wall", w: 44, h: 70 },
      { k: "flat", len: 140 },
      { k: "wall", w: 36, h: 46 },
      { k: "flat", len: 30 },
      { k: "ramp", len: 240, deg: -28 },
      { k: "flat", len: 90 },
      { k: "gap", len: 232 },
      { k: "ramp", len: 200, deg: 28 },
      { k: "flat", len: 70 },
      { k: "wall", w: 36, h: 60 },
      { k: "flat", len: 18 },
      { k: "wall", w: 36, h: 52 },
      { k: "flat", len: 90 },
      { k: "bump", len: 300, height: 140 },
      { k: "flat", len: 110 },
      { k: "wall", w: 44, h: 70 },
      { k: "flat", len: 140 },
      { k: "wall", w: 44, h: 68 },
      { k: "flat", len: 170 },
      { k: "gap", len: 238 },
      { k: "flat", len: 120 },
      { k: "ramp", len: 260, deg: -30 },
      { k: "flat", len: 90 },
      { k: "ramp", len: 260, deg: 30 },
      { k: "flat", len: 190 },
      { k: "bump", len: 360, height: 160 },
      { k: "flat", len: 60 },
      { k: "spring", len: 50 },
      { k: "gap", len: 280 },
      { k: "flat", len: 90 },
      { k: "wall", w: 34, h: 62 },
      { k: "flat", len: 18 },
      { k: "wall", w: 34, h: 58 },
      { k: "flat", len: 170 },
      { k: "pool", len: 420 },
      { k: "flat", len: 200 },
      { k: "spring", len: 50 },
      { k: "gap", len: 260 },
      { k: "flat", len: 300 },
    ],
    750
  ),
  makeCircuit(
    "nocturne",
    "Piste Nocturne",
    { sky: "#1b1e3a", sky2: "#0c0d1c", ground: "#2e3358", accent: "#4dd6ff" },
    [
      { k: "flat", len: 100 },
      { k: "wall", w: 34, h: 42 },
      { k: "flat", len: 110 },
      { k: "wall", w: 34, h: 54 },
      { k: "flat", len: 20 },
      { k: "bump", len: 220, height: 90 },
      { k: "gap", len: 222 },
      { k: "flat", len: 130 },
      { k: "wall", w: 40, h: 70 },
      { k: "ramp", len: 200, deg: -26 },
      { k: "gap", len: 198 },
      { k: "ramp", len: 200, deg: 26 },
      { k: "flat", len: 80 },
      { k: "bump", len: 280, height: 150 },
      { k: "flat", len: 80 },
      { k: "wall", w: 40, h: 70 },
      { k: "flat", len: 18 },
      { k: "wall", w: 40, h: 64 },
      { k: "flat", len: 140 },
      { k: "gap", len: 235 },
      { k: "flat", len: 120 },
      { k: "ramp", len: 220, deg: -32 },
      { k: "flat", len: 60 },
      { k: "gap", len: 232 },
      { k: "ramp", len: 220, deg: 32 },
      { k: "flat", len: 100 },
      { k: "bump", len: 320, height: 170 },
      { k: "flat", len: 90 },
      { k: "gap", len: 238 },
      { k: "flat", len: 160 },
      { k: "bump", len: 400, height: 200 },
      { k: "flat", len: 60 },
      { k: "spring", len: 50 },
      { k: "gap", len: 280 },
      { k: "flat", len: 90 },
      { k: "wall", w: 34, h: 58 },
      { k: "flat", len: 18 },
      { k: "wall", w: 34, h: 54 },
      { k: "flat", len: 170 },
      { k: "pool", len: 470 },
      { k: "flat", len: 220 },
      { k: "spring", len: 50 },
      { k: "gap", len: 260 },
      { k: "flat", len: 380 },
    ],
    700
  ),
  makeCircuit(
    "extreme",
    "Piste Extrême",
    { sky: "#3a1f4d", sky2: "#150a1f", ground: "#5c2e6b", accent: "#ff3d81" },
    [
      { k: "flat", len: 140 },
      { k: "wall", w: 34, h: 62 },
      { k: "flat", len: 180 },
      { k: "gap", len: 215 },
      { k: "flat", len: 130 },
      { k: "wall", w: 34, h: 60 },
      { k: "flat", len: 15 },
      { k: "wall", w: 34, h: 52 },
      { k: "flat", len: 80 },
      { k: "bump", len: 240, height: 110 },
      { k: "gap", len: 225 },
      { k: "flat", len: 130 },
      { k: "wall", w: 40, h: 70 },
      { k: "flat", len: 180 },
      { k: "gap", len: 210 },
      { k: "flat", len: 70 },
      { k: "ramp", len: 220, deg: -30 },
      { k: "flat", len: 30 },
      { k: "wall", w: 34, h: 62 },
      { k: "flat", len: 140 },
      { k: "gap", len: 198 },
      { k: "ramp", len: 220, deg: 30 },
      { k: "flat", len: 50 },
      { k: "wall", w: 34, h: 48 },
      { k: "flat", len: 15 },
      { k: "wall", w: 34, h: 48 },
      { k: "flat", len: 15 },
      { k: "wall", w: 34, h: 48 },
      { k: "flat", len: 90 },
      { k: "bump", len: 300, height: 150 },
      { k: "gap", len: 236 },
      { k: "flat", len: 130 },
      { k: "wall", w: 44, h: 70 },
      { k: "flat", len: 90 },
      { k: "ramp", len: 240, deg: -30 },
      { k: "flat", len: 30 },
      { k: "gap", len: 236 },
      { k: "ramp", len: 240, deg: 30 },
      { k: "flat", len: 50 },
      { k: "wall", w: 40, h: 70 },
      { k: "flat", len: 18 },
      { k: "wall", w: 40, h: 64 },
      { k: "flat", len: 60 },
      { k: "spring", len: 50 },
      { k: "gap", len: 280 },
      { k: "flat", len: 90 },
      { k: "bump", len: 360, height: 180 },
      { k: "flat", len: 110 },
      { k: "pool", len: 520 },
      { k: "flat", len: 150 },
      { k: "wall", w: 34, h: 60 },
      { k: "flat", len: 18 },
      { k: "wall", w: 34, h: 54 },
      { k: "flat", len: 220 },
      { k: "spring", len: 50 },
      { k: "gap", len: 260 },
      { k: "flat", len: 380 },
    ],
    650
  ),
];

export function getCircuit(id: string): CircuitDef {
  return CIRCUITS.find((c) => c.id === id) ?? CIRCUITS[0];
}

// Returns ground height (y) at world x, or null if x falls over a gap / off-track.
export function groundYAt(ground: GroundSeg[], x: number): number | null {
  for (const seg of ground) {
    const lo = Math.min(seg.x0, seg.x1);
    const hi = Math.max(seg.x0, seg.x1);
    if (x >= lo && x <= hi) {
      const t = seg.x1 === seg.x0 ? 0 : (x - seg.x0) / (seg.x1 - seg.x0);
      return seg.y0 + (seg.y1 - seg.y0) * t;
    }
  }
  return null;
}

export function isWaterSegAt(ground: GroundSeg[], x: number): boolean {
  for (const seg of ground) {
    const lo = Math.min(seg.x0, seg.x1);
    const hi = Math.max(seg.x0, seg.x1);
    if (x >= lo && x <= hi) return !!seg.water;
  }
  return false;
}

export function isSpringSegAt(springs: Spring[], x: number): boolean {
  for (const s of springs) {
    if (x >= s.x0 && x <= s.x1) return true;
  }
  return false;
}
