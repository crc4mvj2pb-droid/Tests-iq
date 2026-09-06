import type { KartTrack } from "./tracks";
import type { InputState, PlayerMeta, KartSnapshot, ResultEntry } from "../../net/protocol";

export const CAR_LENGTH = 34;
export const CAR_WIDTH = 20;

const MAX_SPEED = 6.6;
const WALL_SPEED_BLEED = 0.9;
const ACCEL = 0.16;
// Fast enough to fully make the tracks' tightest corners at top speed
// without scraping the wall the whole way through, but gentle enough that
// holding full lock for a normal corner (roughly a second) doesn't spin the
// car in circles. Cars turn tighter at low speed and calm down at top speed,
// like a real car, so fast straights don't feel twitchy.
const TURN_RATE = 0.040;
const TURN_RATE_HIGH_SPEED_FACTOR = 0.6; // multiplier applied at MAX_SPEED
const STEER_SMOOTHING = 0.25; // how quickly the wheel's effect ramps in/out
const WAYPOINT_RADIUS = 150;
export const LAPS_TOTAL = 3;
export const KART_TIME_LIMIT_MS = 5 * 60 * 1000;
export const COUNTDOWN_SECONDS = 3;

interface PlayerRuntime {
  meta: PlayerMeta;
  x: number;
  y: number;
  heading: number;
  speed: number;
  steerSmoothed: number;
  nextWaypoint: number;
  lap: number;
  offTrack: boolean;
  finished: boolean;
  finishTimeMs: number | null;
}

// Closest point on the track's centerline path, plus the distance to it —
// used to hard-clamp cars to the road so they can never drive off it.
function closestOnTrack(track: KartTrack, x: number, y: number): { dist: number; px: number; py: number } {
  let min = Infinity;
  let bestPx = x;
  let bestPy = y;
  const wp = track.waypoints;
  for (let i = 0; i < wp.length; i++) {
    const a = wp[i];
    const b = wp[(i + 1) % wp.length];
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const lenSq = dx * dx + dy * dy;
    let t = lenSq > 0 ? ((x - a.x) * dx + (y - a.y) * dy) / lenSq : 0;
    t = Math.max(0, Math.min(1, t));
    const px = a.x + t * dx;
    const py = a.y + t * dy;
    const d = Math.hypot(x - px, y - py);
    if (d < min) {
      min = d;
      bestPx = px;
      bestPy = py;
    }
  }
  return { dist: min, px: bestPx, py: bestPy };
}

function moveToward(current: number, target: number, maxDelta: number): number {
  if (current < target) return Math.min(current + maxDelta, target);
  return Math.max(current - maxDelta, target);
}

export class KartSimulation {
  track: KartTrack;
  private players = new Map<string, PlayerRuntime>();
  private tick = 0;
  private elapsedMs = 0;
  private ended = false;

  constructor(track: KartTrack, playerMetas: PlayerMeta[]) {
    this.track = track;
    const start = track.waypoints[track.startIndex];
    const next = track.waypoints[(track.startIndex + 1) % track.waypoints.length];
    const dirX = next.x - start.x;
    const dirY = next.y - start.y;
    const len = Math.hypot(dirX, dirY) || 1;
    const ux = dirX / len;
    const uy = dirY / len;
    const perpX = -uy;
    const perpY = ux;
    const heading = Math.atan2(uy, ux);

    playerMetas.forEach((meta, i) => {
      const row = Math.floor(i / 2);
      const side = i % 2 === 0 ? -1 : 1;
      const x = start.x - ux * (row * 55 + 40) + perpX * side * 45;
      const y = start.y - uy * (row * 55 + 40) + perpY * side * 45;
      this.players.set(meta.id, {
        meta,
        x,
        y,
        heading,
        speed: 0,
        steerSmoothed: 0,
        nextWaypoint: (track.startIndex + 1) % track.waypoints.length,
        lap: 0,
        offTrack: false,
        finished: false,
        finishTimeMs: null,
      });
    });
  }

  step(dtMs: number, inputs: Map<string, InputState>) {
    if (this.ended) return;
    this.tick++;
    this.elapsedMs += dtMs;

    for (const pr of this.players.values()) {
      if (pr.finished) continue;
      const input = inputs.get(pr.meta.id);
      const targetSteer = input?.steer ?? ((input?.right ? 1 : 0) - (input?.left ? 1 : 0));
      pr.steerSmoothed += (targetSteer - pr.steerSmoothed) * STEER_SMOOTHING;

      pr.speed = moveToward(pr.speed, MAX_SPEED, ACCEL);

      const speedFactor = 1 - (pr.speed / MAX_SPEED) * (1 - TURN_RATE_HIGH_SPEED_FACTOR);
      pr.heading += TURN_RATE * speedFactor * pr.steerSmoothed;

      pr.x += Math.cos(pr.heading) * pr.speed;
      pr.y += Math.sin(pr.heading) * pr.speed;

      // Hard track boundary: clamp back onto the road edge instead of just
      // slowing down, so a car can never actually leave the circuit.
      const closest = closestOnTrack(this.track, pr.x, pr.y);
      const halfWidth = this.track.roadWidth / 2;
      pr.offTrack = closest.dist > halfWidth;
      if (pr.offTrack) {
        const nx = (pr.x - closest.px) / (closest.dist || 1);
        const ny = (pr.y - closest.py) / (closest.dist || 1);
        pr.x = closest.px + nx * halfWidth;
        pr.y = closest.py + ny * halfWidth;
        pr.speed *= WALL_SPEED_BLEED;
      }

      const target = this.track.waypoints[pr.nextWaypoint];
      if (Math.hypot(pr.x - target.x, pr.y - target.y) < WAYPOINT_RADIUS) {
        const wasLast = pr.nextWaypoint === this.track.waypoints.length - 1;
        pr.nextWaypoint = (pr.nextWaypoint + 1) % this.track.waypoints.length;
        if (wasLast) {
          pr.lap++;
          if (pr.lap >= LAPS_TOTAL && !pr.finished) {
            pr.finished = true;
            pr.finishTimeMs = this.elapsedMs;
          }
        }
      }
    }
  }

  isRaceOver(): boolean {
    if (this.ended) return true;
    const allFinished = [...this.players.values()].every((p) => p.finished);
    if (allFinished || this.elapsedMs >= KART_TIME_LIMIT_MS) {
      this.ended = true;
      return true;
    }
    return false;
  }

  snapshot(): KartSnapshot {
    return {
      tick: this.tick,
      elapsedMs: this.elapsedMs,
      entities: [...this.players.values()].map((p) => ({
        id: p.meta.id,
        x: p.x,
        y: p.y,
        heading: p.heading,
        speed: p.speed,
        lap: p.lap,
        nextWaypoint: p.nextWaypoint,
        offTrack: p.offTrack,
        finished: p.finished,
        finishTimeMs: p.finishTimeMs,
      })),
    };
  }

  getPlayersPublic(): { id: string; x: number; y: number; heading: number; nextWaypoint: number }[] {
    return [...this.players.values()].map((p) => ({ id: p.meta.id, x: p.x, y: p.y, heading: p.heading, nextWaypoint: p.nextWaypoint }));
  }

  results(): ResultEntry[] {
    const wpCount = this.track.waypoints.length;
    const progress = (p: PlayerRuntime) => p.lap * wpCount + p.nextWaypoint;
    const arr = [...this.players.values()];
    arr.sort((a, b) => {
      if (a.finished && b.finished) return (a.finishTimeMs ?? 0) - (b.finishTimeMs ?? 0);
      if (a.finished) return -1;
      if (b.finished) return 1;
      return progress(b) - progress(a);
    });
    return arr.map((p, i) => ({
      id: p.meta.id,
      name: p.meta.name,
      isBot: p.meta.isBot,
      color: p.meta.color,
      rank: i + 1,
      timeMs: p.finishTimeMs ?? undefined,
      finished: p.finished,
      laps: Math.min(p.lap, LAPS_TOTAL),
    }));
  }
}
