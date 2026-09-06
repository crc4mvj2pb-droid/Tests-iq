export interface GroundSeg {
  x0: number;
  y0: number;
  x1: number;
  y1: number;
  angle: number; // radians, authored slope of this segment
}

export interface WallObstacle {
  x: number; // center
  y: number; // center
  w: number;
  h: number;
}

export interface CircuitDef {
  id: string;
  name: string;
  theme: { sky: string; sky2: string; ground: string; accent: string };
  ground: GroundSeg[];
  walls: WallObstacle[];
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
  | { k: "bump"; len: number; height: number };

const GROUND_Y0 = 520;

function build(pieces: Piece[]): { ground: GroundSeg[]; walls: WallObstacle[]; endX: number } {
  let x = 0;
  let y = GROUND_Y0;
  const ground: GroundSeg[] = [];
  const walls: WallObstacle[] = [];

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
    }
  }
  return { ground, walls, endX: x };
}

function makeCircuit(
  id: string,
  name: string,
  theme: CircuitDef["theme"],
  pieces: Piece[],
  checkpointEvery = 900
): CircuitDef {
  const { ground, walls, endX } = build([{ k: "flat", len: 500 }, ...pieces, { k: "flat", len: 400 }]);
  const checkpoints: number[] = [];
  for (let cx = checkpointEvery; cx < endX - 300; cx += checkpointEvery) {
    if (groundYAt(ground, cx) !== null) checkpoints.push(cx);
  }
  return {
    id,
    name,
    theme,
    ground,
    walls,
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
      { k: "flat", len: 250 },
      { k: "wall", w: 34, h: 32 },
      { k: "flat", len: 120 },
      { k: "bump", len: 260, height: 70 },
      { k: "flat", len: 180 },
      { k: "wall", w: 34, h: 40 },
      { k: "flat", len: 100 },
      { k: "gap", len: 130 },
      { k: "flat", len: 200 },
      { k: "wall", w: 34, h: 34 },
      { k: "flat", len: 130 },
      { k: "bump", len: 300, height: 100 },
      { k: "flat", len: 180 },
      { k: "wall", w: 40, h: 70 },
      { k: "flat", len: 200 },
      { k: "wall", w: 34, h: 36 },
      { k: "flat", len: 130 },
      { k: "ramp", len: 220, deg: -22 },
      { k: "flat", len: 120 },
      { k: "wall", w: 34, h: 30 },
      { k: "flat", len: 60 },
      { k: "ramp", len: 220, deg: 22 },
      { k: "flat", len: 220 },
      { k: "wall", w: 34, h: 42 },
      { k: "flat", len: 60 },
      { k: "gap", len: 170 },
      { k: "flat", len: 250 },
      { k: "wall", w: 34, h: 38 },
      { k: "flat", len: 130 },
      { k: "bump", len: 340, height: 130 },
      { k: "flat", len: 500 },
    ]
  ),
  makeCircuit(
    "canyon",
    "Canyon Rouge",
    { sky: "#f5a35c", sky2: "#e0663f", ground: "#8a4a2b", accent: "#ff5d73" },
    [
      { k: "flat", len: 220 },
      { k: "wall", w: 36, h: 36 },
      { k: "flat", len: 60 },
      { k: "gap", len: 180 },
      { k: "flat", len: 220 },
      { k: "wall", w: 44, h: 90 },
      { k: "flat", len: 130 },
      { k: "wall", w: 36, h: 32 },
      { k: "flat", len: 50 },
      { k: "ramp", len: 240, deg: -28 },
      { k: "flat", len: 150 },
      { k: "gap", len: 200 },
      { k: "ramp", len: 200, deg: 28 },
      { k: "flat", len: 130 },
      { k: "wall", w: 36, h: 38 },
      { k: "flat", len: 50 },
      { k: "bump", len: 300, height: 140 },
      { k: "flat", len: 200 },
      { k: "wall", w: 44, h: 100 },
      { k: "wall", w: 44, h: 60 },
      { k: "flat", len: 260 },
      { k: "gap", len: 220 },
      { k: "flat", len: 200 },
      { k: "ramp", len: 260, deg: -30 },
      { k: "flat", len: 180 },
      { k: "ramp", len: 260, deg: 30 },
      { k: "flat", len: 300 },
      { k: "bump", len: 360, height: 160 },
      { k: "flat", len: 500 },
    ],
    750
  ),
  makeCircuit(
    "nocturne",
    "Piste Nocturne",
    { sky: "#1b1e3a", sky2: "#0c0d1c", ground: "#2e3358", accent: "#4dd6ff" },
    [
      { k: "flat", len: 180 },
      { k: "wall", w: 34, h: 34 },
      { k: "flat", len: 40 },
      { k: "bump", len: 220, height: 90 },
      { k: "gap", len: 190 },
      { k: "flat", len: 150 },
      { k: "wall", w: 40, h: 80 },
      { k: "ramp", len: 200, deg: -26 },
      { k: "gap", len: 160 },
      { k: "ramp", len: 200, deg: 26 },
      { k: "flat", len: 150 },
      { k: "bump", len: 280, height: 150 },
      { k: "flat", len: 150 },
      { k: "wall", w: 40, h: 70 },
      { k: "wall", w: 40, h: 70 },
      { k: "gap", len: 220 },
      { k: "flat", len: 200 },
      { k: "ramp", len: 220, deg: -32 },
      { k: "flat", len: 130 },
      { k: "gap", len: 200 },
      { k: "ramp", len: 220, deg: 32 },
      { k: "flat", len: 180 },
      { k: "bump", len: 320, height: 170 },
      { k: "flat", len: 180 },
      { k: "gap", len: 230 },
      { k: "flat", len: 250 },
      { k: "bump", len: 400, height: 200 },
      { k: "flat", len: 600 },
    ],
    700
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
