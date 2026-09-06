export interface Obstacle {
  x: number;
  y: number;
  w: number;
  h: number;
}

export interface ShooterMap {
  id: string;
  name: string;
  theme: { floor: string; floor2: string; wall: string; line: string };
  width: number;
  height: number;
  obstacles: Obstacle[];
  spawnPoints: { x: number; y: number }[];
}

export const SHOOTER_MAPS: ShooterMap[] = [
  {
    id: "arene",
    name: "Arène Centrale",
    theme: { floor: "#2b2f4a", floor2: "#232640", wall: "#565f8f", line: "rgba(255,255,255,0.08)" },
    width: 1600,
    height: 1000,
    obstacles: [
      { x: 780, y: 480, w: 40, h: 220 },
      { x: 300, y: 220, w: 160, h: 40 },
      { x: 1140, y: 220, w: 160, h: 40 },
      { x: 300, y: 740, w: 160, h: 40 },
      { x: 1140, y: 740, w: 160, h: 40 },
      { x: 560, y: 480, w: 40, h: 120 },
      { x: 1000, y: 480, w: 40, h: 120 },
    ],
    spawnPoints: [
      { x: 100, y: 100 },
      { x: 1500, y: 100 },
      { x: 100, y: 900 },
      { x: 1500, y: 900 },
      { x: 800, y: 100 },
      { x: 800, y: 900 },
      { x: 100, y: 500 },
      { x: 1500, y: 500 },
      { x: 450, y: 480 },
      { x: 1150, y: 480 },
    ],
  },
  {
    id: "labyrinthe",
    name: "Labyrinthe",
    theme: { floor: "#332a3d", floor2: "#291f32", wall: "#8a5fb0", line: "rgba(255,255,255,0.07)" },
    width: 1700,
    height: 1100,
    obstacles: [
      { x: 300, y: 200, w: 300, h: 36 },
      { x: 300, y: 900, w: 300, h: 36 },
      { x: 1400, y: 200, w: 300, h: 36 },
      { x: 1400, y: 900, w: 300, h: 36 },
      { x: 850, y: 550, w: 36, h: 400 },
      { x: 550, y: 550, w: 220, h: 36 },
      { x: 1150, y: 550, w: 220, h: 36 },
      { x: 300, y: 550, w: 36, h: 260 },
      { x: 1400, y: 550, w: 36, h: 260 },
      { x: 1000, y: 250, w: 36, h: 240 },
      { x: 700, y: 850, w: 36, h: 240 },
    ],
    spawnPoints: [
      { x: 90, y: 90 },
      { x: 1610, y: 90 },
      { x: 90, y: 1010 },
      { x: 1610, y: 1010 },
      { x: 850, y: 90 },
      { x: 850, y: 1010 },
      { x: 90, y: 550 },
      { x: 1610, y: 550 },
      { x: 500, y: 350 },
      { x: 1200, y: 750 },
    ],
  },
  {
    id: "entrepot",
    name: "Entrepôt",
    theme: { floor: "#38332a", floor2: "#2c2821", wall: "#c99a4a", line: "rgba(255,255,255,0.06)" },
    width: 1500,
    height: 950,
    obstacles: [
      { x: 400, y: 300, w: 220, h: 220 },
      { x: 1100, y: 300, w: 220, h: 220 },
      { x: 400, y: 650, w: 220, h: 220 },
      { x: 1100, y: 650, w: 220, h: 220 },
      { x: 750, y: 475, w: 60, h: 60 },
    ],
    spawnPoints: [
      { x: 80, y: 80 },
      { x: 1420, y: 80 },
      { x: 80, y: 870 },
      { x: 1420, y: 870 },
      { x: 750, y: 80 },
      { x: 750, y: 870 },
      { x: 80, y: 475 },
      { x: 1420, y: 475 },
      { x: 750, y: 250 },
      { x: 750, y: 700 },
    ],
  },
];

export function getMap(id: string): ShooterMap {
  return SHOOTER_MAPS.find((m) => m.id === id) ?? SHOOTER_MAPS[0];
}
