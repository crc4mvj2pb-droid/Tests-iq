import type { KartTrack } from "./tracks";
import type { InputState, PlayerMeta, KartSnapshot, ResultEntry } from "../../net/protocol";

export const CAR_LENGTH = 34;
export const CAR_WIDTH = 20;

const MAX_SPEED = 6.6;
const OFFTRACK_SPEED_FACTOR = 0.45;
const ACCEL = 0.16;
const TURN_RATE = 0.045;
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
  nextWaypoint: number;
  lap: number;
  offTrack: boolean;
  finished: boolean;
  finishTimeMs: number | null;
}

function distToSegment(px: number, py: number, ax: number, ay: number, bx: number, by: number): number {
  const dx = bx - ax;
  const dy = by - ay;
  const lenSq = dx * dx + dy * dy;
  let t = lenSq > 0 ? ((px - ax) * dx + (py - ay) * dy) / lenSq : 0;
  t = Math.max(0, Math.min(1, t));
  const cx = ax + t * dx;
  const cy = ay + t * dy;
  return Math.hypot(px - cx, py - cy);
}

function distToTrack(track: KartTrack, x: number, y: number): number {
  let min = Infinity;
  const wp = track.waypoints;
  for (let i = 0; i < wp.length; i++) {
    const a = wp[i];
    const b = wp[(i + 1) % wp.length];
    const d = distToSegment(x, y, a.x, a.y, b.x, b.y);
    if (d < min) min = d;
  }
  return min;
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
      if (input?.left) pr.heading -= TURN_RATE;
      if (input?.right) pr.heading += TURN_RATE;

      pr.offTrack = distToTrack(this.track, pr.x, pr.y) > this.track.roadWidth / 2;
      const maxSpeed = pr.offTrack ? MAX_SPEED * OFFTRACK_SPEED_FACTOR : MAX_SPEED;
      pr.speed = moveToward(pr.speed, maxSpeed, ACCEL);

      pr.x += Math.cos(pr.heading) * pr.speed;
      pr.y += Math.sin(pr.heading) * pr.speed;

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
