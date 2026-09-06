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
  pickupSpots: { x: number; y: number }[];
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
    pickupSpots: [
      { x: 780, y: 220 },
      { x: 780, y: 740 },
      { x: 450, y: 220 },
      { x: 1150, y: 740 },
      { x: 100, y: 500 },
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
    pickupSpots: [
      { x: 850, y: 350 },
      { x: 850, y: 750 },
      { x: 450, y: 550 },
      { x: 1250, y: 550 },
      { x: 850, y: 550 },
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
    pickupSpots: [
      { x: 750, y: 475 - 130 },
      { x: 750, y: 475 + 130 },
      { x: 400, y: 475 },
      { x: 1100, y: 475 },
    ],
  },
  {
    id: "forteresse",
    name: "Forteresse",
    theme: { floor: "#2a3a2c", floor2: "#213024", wall: "#6b8f6f", line: "rgba(255,255,255,0.07)" },
    width: 1900,
    height: 1300,
    obstacles: [
      // outer ring bunkers
      { x: 300, y: 250, w: 260, h: 50 },
      { x: 950, y: 180, w: 260, h: 50 },
      { x: 1600, y: 250, w: 260, h: 50 },
      { x: 300, y: 1050, w: 260, h: 50 },
      { x: 950, y: 1120, w: 260, h: 50 },
      { x: 1600, y: 1050, w: 260, h: 50 },
      { x: 150, y: 650, w: 50, h: 260 },
      { x: 1750, y: 650, w: 50, h: 260 },
      // inner keep (four walls with gaps to peek through)
      { x: 750, y: 500, w: 40, h: 220 },
      { x: 1150, y: 500, w: 40, h: 220 },
      { x: 750, y: 800, w: 40, h: 220 },
      { x: 1150, y: 800, w: 40, h: 220 },
      { x: 950, y: 420, w: 240, h: 36 },
      { x: 950, y: 880, w: 240, h: 36 },
      // scattered mid cover
      { x: 550, y: 650, w: 70, h: 70 },
      { x: 1350, y: 650, w: 70, h: 70 },
    ],
    spawnPoints: [
      { x: 100, y: 100 },
      { x: 1800, y: 100 },
      { x: 100, y: 1200 },
      { x: 1800, y: 1200 },
      { x: 950, y: 80 },
      { x: 950, y: 1220 },
      { x: 80, y: 650 },
      { x: 1820, y: 650 },
      { x: 650, y: 650 },
      { x: 1250, y: 650 },
      { x: 950, y: 650 },
      { x: 950, y: 300 },
    ],
    pickupSpots: [
      { x: 950, y: 650 },
      { x: 550, y: 650 },
      { x: 1350, y: 650 },
      { x: 950, y: 300 },
      { x: 950, y: 1000 },
      { x: 300, y: 650 },
    ],
  },
  {
    id: "ruines",
    name: "Ruines",
    theme: { floor: "#3d332e", floor2: "#312923", wall: "#9c7a52", line: "rgba(255,255,255,0.06)" },
    width: 2000,
    height: 1250,
    obstacles: [
      { x: 250, y: 300, w: 180, h: 120 },
      { x: 550, y: 180, w: 100, h: 260 },
      { x: 850, y: 350, w: 220, h: 60 },
      { x: 1150, y: 200, w: 140, h: 140 },
      { x: 1450, y: 320, w: 260, h: 50 },
      { x: 1750, y: 220, w: 120, h: 220 },
      { x: 350, y: 620, w: 60, h: 260 },
      { x: 700, y: 650, w: 160, h: 90 },
      { x: 1000, y: 620, w: 90, h: 300 },
      { x: 1300, y: 680, w: 200, h: 70 },
      { x: 1650, y: 650, w: 140, h: 140 },
      { x: 250, y: 950, w: 220, h: 60 },
      { x: 550, y: 1050, w: 90, h: 200 },
      { x: 900, y: 980, w: 260, h: 60 },
      { x: 1250, y: 1050, w: 130, h: 130 },
      { x: 1600, y: 980, w: 220, h: 60 },
    ],
    spawnPoints: [
      { x: 100, y: 100 },
      { x: 1900, y: 100 },
      { x: 100, y: 1150 },
      { x: 1900, y: 1150 },
      { x: 1000, y: 100 },
      { x: 1000, y: 1150 },
      { x: 100, y: 625 },
      { x: 1900, y: 625 },
      { x: 500, y: 850 },
      { x: 1500, y: 450 },
      { x: 850, y: 550 },
      { x: 1500, y: 900 },
    ],
    pickupSpots: [
      { x: 700, y: 350 },
      { x: 1450, y: 550 },
      { x: 550, y: 850 },
      { x: 1300, y: 950 },
      { x: 1000, y: 200 },
      { x: 1750, y: 1000 },
    ],
  },
];

export function getMap(id: string): ShooterMap {
  return SHOOTER_MAPS.find((m) => m.id === id) ?? SHOOTER_MAPS[0];
}
