import type { CircuitDef, Zipline } from "./circuits";
import { groundYAt, isWaterSegAt } from "./circuits";
import type { InputState, PlayerMeta, CourseSnapshot, ResultEntry } from "../../net/protocol";

export const PLAYER_W = 22;
export const PLAYER_H = 46;

export const RUN_SPEED = 5.2;
export const GRAVITY = 0.62;
export const JUMP_VELOCITY = -14.5;
const DOUBLE_JUMP_VELOCITY = -12;
const MAX_JUMPS = 2;
const RESPAWN_LIFT = 40;
const ZIPLINE_SPEED = 7.6;
const ZIPLINE_GRAB_TOLERANCE = 45;
const WATER_SPEED_FACTOR = 0.35;
export const RACE_TIME_LIMIT_MS = 3 * 60 * 1000;
export const COUNTDOWN_SECONDS = 3;

interface PlayerRuntime {
  meta: PlayerMeta;
  x: number;
  y: number; // feet position
  vx: number;
  vy: number;
  onGround: boolean;
  onZipline: boolean;
  zip: Zipline | null;
  jumpsLeft: number;
  prevPressed: boolean;
  distance: number;
  finished: boolean;
  finishTimeMs: number | null;
  lastCheckpoint: { x: number; y: number };
  crashFlash: number;
}

export class CourseSimulation {
  circuit: CircuitDef;
  private players = new Map<string, PlayerRuntime>();
  private tick = 0;
  private elapsedMs = 0;
  private ended = false;

  constructor(circuit: CircuitDef, playerMetas: PlayerMeta[]) {
    this.circuit = circuit;
    playerMetas.forEach((meta, i) => {
      this.players.set(meta.id, {
        meta,
        x: circuit.startX - i * 30,
        y: circuit.startY,
        vx: RUN_SPEED,
        vy: 0,
        onGround: true,
        onZipline: false,
        zip: null,
        jumpsLeft: MAX_JUMPS,
        prevPressed: false,
        distance: 0,
        finished: false,
        finishTimeMs: null,
        lastCheckpoint: { x: circuit.startX, y: circuit.startY },
        crashFlash: 0,
      });
    });
  }

  private respawn(pr: PlayerRuntime) {
    pr.x = pr.lastCheckpoint.x;
    pr.y = pr.lastCheckpoint.y - RESPAWN_LIFT;
    pr.vx = RUN_SPEED;
    pr.vy = 0;
    pr.onGround = false;
    pr.onZipline = false;
    pr.zip = null;
    pr.jumpsLeft = MAX_JUMPS;
    pr.crashFlash = 20;
  }

  private hitsWall(pr: PlayerRuntime): boolean {
    const left = pr.x - PLAYER_W / 2;
    const right = pr.x + PLAYER_W / 2;
    const bottom = pr.y;
    const top = pr.y - PLAYER_H;
    for (const w of this.circuit.walls) {
      const wLeft = w.x - w.w / 2;
      const wRight = w.x + w.w / 2;
      const wTop = w.y - w.h / 2;
      const wBottom = w.y + w.h / 2;
      if (right > wLeft && left < wRight && bottom > wTop && top < wBottom) return true;
    }
    return false;
  }

  step(dtMs: number, inputs: Map<string, InputState>) {
    if (this.ended) return;
    this.tick++;
    this.elapsedMs += dtMs;

    for (const pr of this.players.values()) {
      if (pr.crashFlash > 0) pr.crashFlash--;
      if (pr.finished) continue;

      const input = inputs.get(pr.meta.id);
      const pressed = !!input?.up || !!input?.jump;
      const justPressed = pressed && !pr.prevPressed;
      pr.prevPressed = pressed;

      if (pr.onZipline && pr.zip) {
        pr.x += ZIPLINE_SPEED;
        pr.y = pr.zip.y;
        pr.vy = 0;
        if (pr.x >= pr.zip.x1) {
          pr.onZipline = false;
          pr.zip = null;
        }
      } else {
        let grabbed = false;
        if (justPressed && !pr.onGround) {
          for (const z of this.circuit.ziplines) {
            if (pr.x >= z.x0 && pr.x <= z.x1 && Math.abs(pr.y - z.y) < ZIPLINE_GRAB_TOLERANCE) {
              pr.onZipline = true;
              pr.zip = z;
              pr.y = z.y;
              pr.vy = 0;
              grabbed = true;
              break;
            }
          }
        }

        if (!grabbed) {
          if (justPressed && pr.jumpsLeft > 0) {
            pr.vy = pr.jumpsLeft === MAX_JUMPS ? JUMP_VELOCITY : DOUBLE_JUMP_VELOCITY;
            pr.jumpsLeft--;
            pr.onGround = false;
          }

          const inWater = pr.onGround && isWaterSegAt(this.circuit.ground, pr.x);
          pr.x += inWater ? RUN_SPEED * WATER_SPEED_FACTOR : RUN_SPEED;
          pr.vy += GRAVITY;
          pr.y += pr.vy;

          const groundY = groundYAt(this.circuit.ground, pr.x);
          if (groundY !== null && pr.vy >= 0 && pr.y >= groundY) {
            pr.y = groundY;
            pr.vy = 0;
            pr.onGround = true;
            pr.jumpsLeft = MAX_JUMPS;
          } else {
            pr.onGround = false;
          }
        }
      }

      if (pr.y > this.circuit.worldBottom || this.hitsWall(pr)) {
        this.respawn(pr);
        continue;
      }

      pr.distance = Math.max(pr.distance, pr.x - this.circuit.startX);

      for (const cpX of this.circuit.checkpoints) {
        if (pr.x >= cpX && pr.lastCheckpoint.x < cpX) {
          const gy = groundYAt(this.circuit.ground, cpX);
          if (gy !== null) pr.lastCheckpoint = { x: cpX, y: gy };
        }
      }

      if (pr.x >= this.circuit.finishX && !pr.finished) {
        pr.finished = true;
        pr.finishTimeMs = this.elapsedMs;
      }
    }
  }

  isRaceOver(): boolean {
    if (this.ended) return true;
    const allFinished = [...this.players.values()].every((p) => p.finished);
    if (allFinished || this.elapsedMs >= RACE_TIME_LIMIT_MS) {
      this.ended = true;
      return true;
    }
    return false;
  }

  snapshot(): CourseSnapshot {
    return {
      tick: this.tick,
      elapsedMs: this.elapsedMs,
      entities: [...this.players.values()].map((p) => ({
        id: p.meta.id,
        x: p.x,
        y: p.y,
        vx: p.vx,
        vy: p.vy,
        onGround: p.onGround,
        onZipline: p.onZipline,
        facing: 1 as const,
        finished: p.finished,
        finishTimeMs: p.finishTimeMs,
        distance: p.distance,
        crashFlash: p.crashFlash,
      })),
    };
  }

  results(): ResultEntry[] {
    const arr = [...this.players.values()];
    arr.sort((a, b) => {
      if (a.finished && b.finished) return (a.finishTimeMs ?? 0) - (b.finishTimeMs ?? 0);
      if (a.finished) return -1;
      if (b.finished) return 1;
      return b.distance - a.distance;
    });
    return arr.map((p, i) => ({
      id: p.meta.id,
      name: p.meta.name,
      isBot: p.meta.isBot,
      color: p.meta.color,
      rank: i + 1,
      timeMs: p.finishTimeMs ?? undefined,
      distance: Math.round(p.distance),
      finished: p.finished,
    }));
  }
}
