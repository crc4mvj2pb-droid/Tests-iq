export interface CarStars {
  speed: number; // 1-5
  accel: number;
  stability: number;
  rotation: number;
  grip: number;
  air: number;
}

export type UnlockCondition =
  | { type: 'default' }
  | { type: 'levelsCompleted'; count: number }
  | { type: 'starsTotal'; count: number }
  | { type: 'privateWin' }
  | { type: 'publicWin' }
  | { type: 'flipsTotal'; count: number }
  | { type: 'distanceTotal'; meters: number }
  | { type: 'noDeathLevel' }
  | { type: 'perfectStars'; count: number };

export interface CarProfile {
  id: string;
  name: string;
  tagline: string;
  colorPrimary: string;
  colorSecondary: string;
  glow: string;
  stars: CarStars;
  unlock: UnlockCondition;
  // physics
  chassisWidth: number;
  chassisHeight: number;
  wheelRadius: number;
  wheelOffset: number;
  density: number;
  maxWheelSpeed: number;
  wheelAccelRate: number;
  airControlTorque: number;
  suspensionStiffness: number;
  suspensionDamping: number;
  wheelFriction: number;
  chassisFriction: number;
  restitution: number;
}

export const CARS: CarProfile[] = [
  {
    id: 'balanced',
    name: 'Nova Balanced',
    tagline: "L'équilibre parfait pour apprendre.",
    colorPrimary: '#4fd1ff',
    colorSecondary: '#0d2b3a',
    glow: '#7fe7ff',
    stars: { speed: 3, accel: 3, stability: 3, rotation: 3, grip: 3, air: 3 },
    unlock: { type: 'default' },
    chassisWidth: 86, chassisHeight: 30, wheelRadius: 19, wheelOffset: 32,
    density: 0.0018, maxWheelSpeed: 0.9, wheelAccelRate: 0.12, airControlTorque: 0.0303,
    suspensionStiffness: 0.55, suspensionDamping: 0.28, wheelFriction: 0.98, chassisFriction: 0.4, restitution: 0.05,
  },
  {
    id: 'velocity',
    name: 'Velocity X',
    tagline: 'Vitesse extrême, stabilité fragile.',
    colorPrimary: '#ff4f6d',
    colorSecondary: '#3a0d16',
    glow: '#ff8fa3',
    stars: { speed: 5, accel: 5, stability: 2, rotation: 2, grip: 3, air: 2 },
    unlock: { type: 'levelsCompleted', count: 5 },
    chassisWidth: 96, chassisHeight: 26, wheelRadius: 17, wheelOffset: 36,
    density: 0.0014, maxWheelSpeed: 1.35, wheelAccelRate: 0.16, airControlTorque: 0.0220,
    suspensionStiffness: 0.4, suspensionDamping: 0.18, wheelFriction: 0.95, chassisFriction: 0.35, restitution: 0.08,
  },
  {
    id: 'agile',
    name: 'Wisp Agile',
    tagline: 'Rotation exceptionnelle en vol.',
    colorPrimary: '#a6ff4f',
    colorSecondary: '#213a0d',
    glow: '#cfff8f',
    stars: { speed: 3, accel: 4, stability: 2, rotation: 5, grip: 3, air: 5 },
    unlock: { type: 'starsTotal', count: 10 },
    chassisWidth: 78, chassisHeight: 26, wheelRadius: 17, wheelOffset: 28,
    density: 0.0013, maxWheelSpeed: 1.0, wheelAccelRate: 0.17, airControlTorque: 0.0495,
    suspensionStiffness: 0.5, suspensionDamping: 0.22, wheelFriction: 0.96, chassisFriction: 0.35, restitution: 0.06,
  },
  {
    id: 'tank',
    name: 'Bastion Tank',
    tagline: 'Presque impossible à faire tomber.',
    colorPrimary: '#ffb84f',
    colorSecondary: '#3a2a0d',
    glow: '#ffd88f',
    stars: { speed: 2, accel: 2, stability: 5, rotation: 2, grip: 4, air: 2 },
    unlock: { type: 'starsTotal', count: 30 },
    chassisWidth: 104, chassisHeight: 38, wheelRadius: 23, wheelOffset: 38,
    density: 0.0026, maxWheelSpeed: 0.7, wheelAccelRate: 0.09, airControlTorque: 0.0165,
    suspensionStiffness: 0.7, suspensionDamping: 0.4, wheelFriction: 1.0, chassisFriction: 0.5, restitution: 0.02,
  },
  {
    id: 'phantom',
    name: 'Phantom Drift',
    tagline: 'Adhérence chirurgicale.',
    colorPrimary: '#c14fff',
    colorSecondary: '#2a0d3a',
    glow: '#e28fff',
    stars: { speed: 4, accel: 3, stability: 3, rotation: 3, grip: 5, air: 3 },
    unlock: { type: 'privateWin' },
    chassisWidth: 88, chassisHeight: 28, wheelRadius: 18, wheelOffset: 33,
    density: 0.0017, maxWheelSpeed: 1.1, wheelAccelRate: 0.13, airControlTorque: 0.0330,
    suspensionStiffness: 0.58, suspensionDamping: 0.3, wheelFriction: 1.05, chassisFriction: 0.42, restitution: 0.05,
  },
  {
    id: 'titan',
    name: 'Titan Prime',
    tagline: 'Champion des courses publiques.',
    colorPrimary: '#4fffe0',
    colorSecondary: '#0d3a33',
    glow: '#8fffea',
    stars: { speed: 4, accel: 4, stability: 4, rotation: 3, grip: 4, air: 3 },
    unlock: { type: 'publicWin' },
    chassisWidth: 90, chassisHeight: 30, wheelRadius: 19, wheelOffset: 34,
    density: 0.0019, maxWheelSpeed: 1.15, wheelAccelRate: 0.14, airControlTorque: 0.0330,
    suspensionStiffness: 0.55, suspensionDamping: 0.28, wheelFriction: 1.0, chassisFriction: 0.4, restitution: 0.05,
  },
  {
    id: 'acrobat',
    name: 'Acrobat Loop',
    tagline: "Née pour les triples flips.",
    colorPrimary: '#ffe14f',
    colorSecondary: '#3a340d',
    glow: '#fff08f',
    stars: { speed: 3, accel: 3, stability: 2, rotation: 5, grip: 2, air: 5 },
    unlock: { type: 'flipsTotal', count: 50 },
    chassisWidth: 76, chassisHeight: 24, wheelRadius: 16, wheelOffset: 27,
    density: 0.0012, maxWheelSpeed: 0.95, wheelAccelRate: 0.15, airControlTorque: 0.0550,
    suspensionStiffness: 0.48, suspensionDamping: 0.2, wheelFriction: 0.9, chassisFriction: 0.3, restitution: 0.06,
  },
  {
    id: 'nomad',
    name: 'Nomad Endurance',
    tagline: 'Faite pour la longue distance.',
    colorPrimary: '#ff9d4f',
    colorSecondary: '#3a220d',
    glow: '#ffc28f',
    stars: { speed: 3, accel: 3, stability: 4, rotation: 3, grip: 4, air: 3 },
    unlock: { type: 'distanceTotal', meters: 10000 },
    chassisWidth: 92, chassisHeight: 30, wheelRadius: 20, wheelOffset: 34,
    density: 0.002, maxWheelSpeed: 1.0, wheelAccelRate: 0.11, airControlTorque: 0.0275,
    suspensionStiffness: 0.6, suspensionDamping: 0.32, wheelFriction: 1.0, chassisFriction: 0.45, restitution: 0.04,
  },
  {
    id: 'ironclad',
    name: 'Ironclad Zero',
    tagline: 'Une seule course, aucune erreur.',
    colorPrimary: '#8f9bff',
    colorSecondary: '#161a3a',
    glow: '#b3bcff',
    stars: { speed: 3, accel: 2, stability: 5, rotation: 2, grip: 5, air: 2 },
    unlock: { type: 'noDeathLevel' },
    chassisWidth: 98, chassisHeight: 34, wheelRadius: 21, wheelOffset: 36,
    density: 0.0023, maxWheelSpeed: 0.85, wheelAccelRate: 0.1, airControlTorque: 0.0220,
    suspensionStiffness: 0.65, suspensionDamping: 0.36, wheelFriction: 1.05, chassisFriction: 0.48, restitution: 0.03,
  },
  {
    id: 'aurora',
    name: 'Aurora Perfect',
    tagline: 'La voiture des perfectionnistes.',
    colorPrimary: '#ff4fd6',
    colorSecondary: '#3a0d30',
    glow: '#ff8fe8',
    stars: { speed: 4, accel: 4, stability: 3, rotation: 4, grip: 4, air: 4 },
    unlock: { type: 'perfectStars', count: 15 },
    chassisWidth: 84, chassisHeight: 27, wheelRadius: 18, wheelOffset: 31,
    density: 0.0016, maxWheelSpeed: 1.2, wheelAccelRate: 0.15, airControlTorque: 0.0385,
    suspensionStiffness: 0.56, suspensionDamping: 0.27, wheelFriction: 1.0, chassisFriction: 0.4, restitution: 0.05,
  },
];

export function getCar(id: string): CarProfile {
  return CARS.find((c) => c.id === id) ?? CARS[0];
}
