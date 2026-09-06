import type { ShooterMap, Obstacle } from "./maps";
import type { InputState, PlayerMeta, ShooterSnapshot, ResultEntry } from "../../net/protocol";
import { mulberry32 } from "../../utils/rng";

export const PLAYER_R = 18;
const BULLET_R = 5;
const MAX_SPEED = 4.6;
const ACCEL = 0.7;
const FRICTION = 0.84;
const BULLET_SPEED = 12;
const BULLET_RANGE = 780;
const FIRE_COOLDOWN_TICKS = 15;
const DAMAGE = 22;
const MAX_HP = 100;
const RESPAWN_TICKS = 110;
const INVULN_TICKS = 70;
export const KILL_LIMIT = 15;
export const MATCH_TIME_LIMIT_MS = 3 * 60 * 1000;
export const COUNTDOWN_SECONDS = 3;

interface PlayerRuntime {
  meta: PlayerMeta;
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
  invulnTicks: number;
  respawnTicks: number;
  fireCooldown: number;
}

interface Bullet {
  id: number;
  x: number;
  y: number;
  vx: number;
  vy: number;
  ownerId: string;
  traveled: number;
}

export class ShooterSimulation {
  map: ShooterMap;
  private players = new Map<string, PlayerRuntime>();
  private bullets: Bullet[] = [];
  private nextBulletId = 1;
  private tick = 0;
  private elapsedMs = 0;
  private ended = false;
  private rand: () => number;

  constructor(map: ShooterMap, seed: number, playerMetas: PlayerMeta[]) {
    this.map = map;
    this.rand = mulberry32(seed);
    playerMetas.forEach((meta, i) => {
      const sp = map.spawnPoints[i % map.spawnPoints.length];
      this.players.set(meta.id, {
        meta,
        x: sp.x,
        y: sp.y,
        vx: 0,
        vy: 0,
        aimX: 1,
        aimY: 0,
        hp: MAX_HP,
        alive: true,
        kills: 0,
        deaths: 0,
        invulnTicks: INVULN_TICKS,
        respawnTicks: 0,
        fireCooldown: 0,
      });
    });
  }

  private randomSpawn(): { x: number; y: number } {
    const sp = this.map.spawnPoints;
    return sp[Math.floor(this.rand() * sp.length)];
  }

  private resolveObstacleCollision(x: number, y: number, r: number): { x: number; y: number } {
    let px = x;
    let py = y;
    for (const o of this.map.obstacles) {
      const closestX = clamp(px, o.x - o.w / 2, o.x + o.w / 2);
      const closestY = clamp(py, o.y - o.h / 2, o.y + o.h / 2);
      const dx = px - closestX;
      const dy = py - closestY;
      const distSq = dx * dx + dy * dy;
      if (distSq < r * r) {
        const dist = Math.sqrt(distSq) || 0.001;
        const push = r - dist;
        px += (dx / dist) * push;
        py += (dy / dist) * push;
      }
    }
    return { x: px, y: py };
  }

  private bulletHitsObstacle(x: number, y: number): boolean {
    for (const o of this.map.obstacles as Obstacle[]) {
      if (x > o.x - o.w / 2 && x < o.x + o.w / 2 && y > o.y - o.h / 2 && y < o.y + o.h / 2) return true;
    }
    return false;
  }

  step(dtMs: number, inputs: Map<string, InputState>) {
    if (this.ended) return;
    this.tick++;
    this.elapsedMs += dtMs;

    for (const pr of this.players.values()) {
      if (!pr.alive) {
        pr.respawnTicks--;
        if (pr.respawnTicks <= 0) {
          const sp = this.randomSpawn();
          pr.x = sp.x;
          pr.y = sp.y;
          pr.vx = 0;
          pr.vy = 0;
          pr.hp = MAX_HP;
          pr.alive = true;
          pr.invulnTicks = INVULN_TICKS;
        }
        continue;
      }
      if (pr.invulnTicks > 0) pr.invulnTicks--;
      if (pr.fireCooldown > 0) pr.fireCooldown--;

      const input = inputs.get(pr.meta.id);
      let ax = 0;
      let ay = 0;
      if (input?.left) ax -= 1;
      if (input?.right) ax += 1;
      if (input?.up) ay -= 1;
      if (input?.down) ay += 1;
      if (ax !== 0 || ay !== 0) {
        const len = Math.hypot(ax, ay) || 1;
        pr.vx += (ax / len) * ACCEL;
        pr.vy += (ay / len) * ACCEL;
      } else {
        pr.vx *= FRICTION;
        pr.vy *= FRICTION;
      }
      const speed = Math.hypot(pr.vx, pr.vy);
      if (speed > MAX_SPEED) {
        pr.vx = (pr.vx / speed) * MAX_SPEED;
        pr.vy = (pr.vy / speed) * MAX_SPEED;
      }

      let nx = pr.x + pr.vx;
      let ny = pr.y + pr.vy;
      nx = clamp(nx, PLAYER_R, this.map.width - PLAYER_R);
      ny = clamp(ny, PLAYER_R, this.map.height - PLAYER_R);
      const resolved = this.resolveObstacleCollision(nx, ny, PLAYER_R);
      pr.x = resolved.x;
      pr.y = resolved.y;

      if (input && (input.aimX !== 0 || input.aimY !== 0)) {
        const l = Math.hypot(input.aimX, input.aimY) || 1;
        pr.aimX = input.aimX / l;
        pr.aimY = input.aimY / l;
      }

      if (input?.shoot && pr.fireCooldown <= 0) {
        pr.fireCooldown = FIRE_COOLDOWN_TICKS;
        this.bullets.push({
          id: this.nextBulletId++,
          x: pr.x + pr.aimX * (PLAYER_R + 6),
          y: pr.y + pr.aimY * (PLAYER_R + 6),
          vx: pr.aimX * BULLET_SPEED,
          vy: pr.aimY * BULLET_SPEED,
          ownerId: pr.meta.id,
          traveled: 0,
        });
      }
    }

    const survivors: Bullet[] = [];
    for (const b of this.bullets) {
      b.x += b.vx;
      b.y += b.vy;
      b.traveled += BULLET_SPEED;
      if (
        b.traveled > BULLET_RANGE ||
        b.x < 0 ||
        b.x > this.map.width ||
        b.y < 0 ||
        b.y > this.map.height ||
        this.bulletHitsObstacle(b.x, b.y)
      ) {
        continue;
      }
      let hit = false;
      for (const pr of this.players.values()) {
        if (pr.meta.id === b.ownerId || !pr.alive || pr.invulnTicks > 0) continue;
        const d = Math.hypot(pr.x - b.x, pr.y - b.y);
        if (d < PLAYER_R + BULLET_R) {
          hit = true;
          pr.hp -= DAMAGE;
          if (pr.hp <= 0) {
            pr.alive = false;
            pr.deaths++;
            pr.respawnTicks = RESPAWN_TICKS;
            const shooter = this.players.get(b.ownerId);
            if (shooter) shooter.kills++;
          }
          break;
        }
      }
      if (!hit) survivors.push(b);
    }
    this.bullets = survivors;
  }

  isMatchOver(): boolean {
    if (this.ended) return true;
    const topKills = Math.max(0, ...[...this.players.values()].map((p) => p.kills));
    if (topKills >= KILL_LIMIT || this.elapsedMs >= MATCH_TIME_LIMIT_MS) {
      this.ended = true;
      return true;
    }
    return false;
  }

  snapshot(): ShooterSnapshot {
    return {
      tick: this.tick,
      elapsedMs: this.elapsedMs,
      entities: [...this.players.values()].map((p) => ({
        id: p.meta.id,
        x: p.x,
        y: p.y,
        vx: p.vx,
        vy: p.vy,
        aimX: p.aimX,
        aimY: p.aimY,
        hp: p.hp,
        alive: p.alive,
        kills: p.kills,
        deaths: p.deaths,
        invuln: p.invulnTicks > 0,
      })),
      bullets: this.bullets.map((b) => ({ id: b.id, x: b.x, y: b.y, vx: b.vx, vy: b.vy, ownerId: b.ownerId })),
    };
  }

  getPlayersPublic(): { id: string; x: number; y: number; alive: boolean }[] {
    return [...this.players.values()].map((p) => ({ id: p.meta.id, x: p.x, y: p.y, alive: p.alive }));
  }

  results(): ResultEntry[] {
    const arr = [...this.players.values()];
    arr.sort((a, b) => b.kills - a.kills || a.deaths - b.deaths);
    return arr.map((p, i) => ({
      id: p.meta.id,
      name: p.meta.name,
      isBot: p.meta.isBot,
      color: p.meta.color,
      rank: i + 1,
      kills: p.kills,
      deaths: p.deaths,
    }));
  }
}

function clamp(v: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, v));
}
