export type GameMode = "course" | "shooter";

export interface PlayerMeta {
  id: string;
  name: string;
  color: string;
  isBot: boolean;
}

export interface InputState {
  left: boolean;
  right: boolean;
  up: boolean;
  down: boolean;
  jump: boolean;
  shoot: boolean;
  // Aim direction in world space, used by shooter mode.
  aimX: number;
  aimY: number;
}

export function emptyInput(): InputState {
  return { left: false, right: false, up: false, down: false, jump: false, shoot: false, aimX: 1, aimY: 0 };
}

export interface ResultEntry {
  id: string;
  name: string;
  isBot: boolean;
  color: string;
  rank: number;
  // Course:
  timeMs?: number;
  distance?: number;
  finished?: boolean;
  flips?: number;
  // Shooter:
  kills?: number;
  deaths?: number;
}

// ---- Course mode (vehicle physics with flips) ----
export interface CourseEntitySnapshot {
  id: string;
  x: number;
  y: number;
  angle: number;
  vx: number;
  vy: number;
  onGround: boolean;
  finished: boolean;
  finishTimeMs: number | null;
  distance: number;
  flips: number;
  crashFlash: number; // >0 shortly after a crash/respawn, for renderer feedback
}

export interface CourseSnapshot {
  tick: number;
  elapsedMs: number;
  entities: CourseEntitySnapshot[];
}

// ---- Shooter mode (top-down arena) ----
export interface ShooterEntitySnapshot {
  id: string;
  x: number;
  y: number;
  vx: number;
  vy: number;
  aimX: number;
  aimY: number;
  hp: number;
  alive: boolean;
  kills: number;
  deaths: number;
  invuln: boolean;
}

export interface BulletSnapshot {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  ownerId: string;
}

export interface ShooterSnapshot {
  tick: number;
  elapsedMs: number;
  entities: ShooterEntitySnapshot[];
  bullets: BulletSnapshot[];
}

// ---- Messages: client -> host ----
export type ClientToHostMessage =
  | { t: "hello"; name: string; color: string }
  | { t: "input"; input: InputState }
  | { t: "profile"; name: string; color: string };

// ---- Messages: host -> client (also dispatched locally on host) ----
export type HostToClientMessage =
  | { t: "lobby"; players: PlayerMeta[]; hostId: string; mode: GameMode | null; levelId: string | null }
  | { t: "gameStart"; mode: GameMode; levelId: string; seed: number; players: PlayerMeta[]; startAt: number }
  | { t: "courseState"; snapshot: CourseSnapshot }
  | { t: "shooterState"; snapshot: ShooterSnapshot }
  | { t: "gameOver"; results: ResultEntry[] }
  | { t: "toLobby" };
