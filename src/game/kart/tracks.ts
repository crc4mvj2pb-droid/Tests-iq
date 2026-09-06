export interface Waypoint {
  x: number;
  y: number;
}

export interface KartTrack {
  id: string;
  name: string;
  theme: { road: string; roadLine: string; grass: string; grass2: string; accent: string };
  waypoints: Waypoint[]; // closed loop, in driving order
  roadWidth: number;
  startIndex: number; // waypoint index used as the start/finish line
  decorations: { x: number; y: number; r: number }[]; // simple round scenery blobs
}

function roundedRectLoop(cx: number, cy: number, halfW: number, halfH: number, cornerR: number, segsPerCorner: number): Waypoint[] {
  const pts: Waypoint[] = [];
  const corners = [
    { ccx: cx + halfW - cornerR, ccy: cy - halfH + cornerR, start: -90, end: 0 },
    { ccx: cx + halfW - cornerR, ccy: cy + halfH - cornerR, start: 0, end: 90 },
    { ccx: cx - halfW + cornerR, ccy: cy + halfH - cornerR, start: 90, end: 180 },
    { ccx: cx - halfW + cornerR, ccy: cy - halfH + cornerR, start: 180, end: 270 },
  ];
  for (const c of corners) {
    for (let i = 0; i < segsPerCorner; i++) {
      const t = i / segsPerCorner;
      const deg = c.start + (c.end - c.start) * t;
      const rad = (deg * Math.PI) / 180;
      pts.push({ x: c.ccx + Math.cos(rad) * cornerR, y: c.ccy + Math.sin(rad) * cornerR });
    }
  }
  return pts;
}

function ring(cx: number, cy: number, r: number, count: number, seedOffset: number): { x: number; y: number; r: number }[] {
  const out: { x: number; y: number; r: number }[] = [];
  for (let i = 0; i < count; i++) {
    const a = (i / count) * Math.PI * 2 + seedOffset;
    out.push({ x: cx + Math.cos(a) * r, y: cy + Math.sin(a) * r, r: 14 + ((i * 7) % 12) });
  }
  return out;
}

export const KART_TRACKS: KartTrack[] = [
  {
    id: "desert",
    name: "Circuit du Désert",
    theme: { road: "#8a6a45", roadLine: "#f5e6c8", grass: "#d9c08a", grass2: "#c9ac6c", accent: "#e0663f" },
    waypoints: roundedRectLoop(1000, 650, 650, 380, 180, 7),
    roadWidth: 240,
    startIndex: 0,
    decorations: [...ring(1000, 650, 500, 14, 0.3), ...ring(1000, 650, 850, 10, 1.1)],
  },
  {
    id: "nocturne-gp",
    name: "Grand Prix Nocturne",
    theme: { road: "#31344a", roadLine: "#ffd166", grass: "#1a1d2e", grass2: "#141724", accent: "#4dd6ff" },
    waypoints: roundedRectLoop(1350, 850, 950, 550, 220, 8),
    roadWidth: 260,
    startIndex: 0,
    decorations: [...ring(1350, 850, 700, 18, 0.5), ...ring(1350, 850, 1200, 14, 1.4)],
  },
];

export function getTrack(id: string): KartTrack {
  return KART_TRACKS.find((t) => t.id === id) ?? KART_TRACKS[0];
}
