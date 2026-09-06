import Matter from "matter-js";
import type { CircuitDef, GroundSeg } from "./circuits";
import { groundYAt } from "./circuits";
import type { InputState, PlayerMeta, CourseSnapshot, ResultEntry } from "../../net/protocol";

const { Engine, World, Bodies, Body, Events } = Matter;

export const VEHICLE_W = 46;
export const VEHICLE_H = 24;
const MAX_SPEED = 9.5; // px per physics step (tangential)
const ACCEL = 0.42;
const DECEL = 0.28;
const FLIP_RATE = 0.18; // rad per physics step while holding a flip direction
const FLIP_DAMPING = 0.94;
const LAND_SAFE_TOLERANCE = (68 * Math.PI) / 180;
const RESPAWN_LIFT = 40;
export const RACE_TIME_LIMIT_MS = 3 * 60 * 1000;
export const COUNTDOWN_SECONDS = 3;

type BodyPlugin =
  | { type: "ground"; angle: number }
  | { type: "wall" }
  | { type: "player"; id: string };

interface PlayerRuntime {
  meta: PlayerMeta;
  body: Matter.Body;
  grounded: boolean;
  groundAngle: number;
  airborneAccum: number;
  flips: number;
  distance: number;
  finished: boolean;
  finishTimeMs: number | null;
  lastCheckpoint: { x: number; y: number };
  crashFlash: number;
  hitWallTick: boolean;
  wasAirborne: boolean;
}

export class CourseSimulation {
  circuit: CircuitDef;
  engine: Matter.Engine;
  private players = new Map<string, PlayerRuntime>();
  private tick = 0;
  private elapsedMs = 0;
  private ended = false;

  constructor(circuit: CircuitDef, playerMetas: PlayerMeta[]) {
    this.circuit = circuit;
    this.engine = Engine.create({ gravity: { x: 0, y: 1 } });

    const groundBodies = circuit.ground.map((seg, i) => this.makeGroundBody(seg, i));
    const wallBodies = circuit.walls.map((w) =>
      Bodies.rectangle(w.x, w.y, w.w, w.h, {
        isStatic: true,
        friction: 1,
        plugin: { type: "wall" } as BodyPlugin,
        render: {},
      })
    );
    World.add(this.engine.world, [...groundBodies, ...wallBodies]);

    playerMetas.forEach((meta, i) => {
      const body = Bodies.rectangle(circuit.startX - i * 55, circuit.startY, VEHICLE_W, VEHICLE_H, {
        friction: 0.9,
        frictionAir: 0.0005,
        restitution: 0,
        density: 0.0025,
        plugin: { type: "player", id: meta.id } as BodyPlugin,
      });
      World.add(this.engine.world, body);
      this.players.set(meta.id, {
        meta,
        body,
        grounded: false,
        groundAngle: 0,
        airborneAccum: 0,
        flips: 0,
        distance: 0,
        finished: false,
        finishTimeMs: null,
        lastCheckpoint: { x: circuit.startX, y: circuit.startY },
        crashFlash: 0,
        hitWallTick: false,
        wasAirborne: true,
      });
    });

    const handlePairs = (pairs: Matter.Pair[]) => {
      for (const pair of pairs) {
        const a = pair.bodyA.plugin as BodyPlugin | undefined;
        const b = pair.bodyB.plugin as BodyPlugin | undefined;
        this.applyPairContact(a, pair.bodyA, b, pair.bodyB);
        this.applyPairContact(b, pair.bodyB, a, pair.bodyA);
      }
    };
    Events.on(this.engine, "collisionStart", (e) => handlePairs(e.pairs));
    Events.on(this.engine, "collisionActive", (e) => handlePairs(e.pairs));
  }

  private applyPairContact(
    selfPlugin: BodyPlugin | undefined,
    _selfBody: Matter.Body,
    otherPlugin: BodyPlugin | undefined,
    otherBody: Matter.Body
  ) {
    if (!selfPlugin || selfPlugin.type !== "player") return;
    const pr = this.players.get(selfPlugin.id);
    if (!pr) return;
    if (otherPlugin?.type === "ground") {
      pr.grounded = true;
      pr.groundAngle = otherPlugin.angle;
    } else if (otherPlugin?.type === "wall") {
      pr.hitWallTick = true;
    } else if (otherPlugin?.type === "player") {
      // player-vs-player bumps: let Matter's normal collision response handle it (fun chaos), no extra logic.
      void otherBody;
    }
  }

  private makeGroundBody(seg: GroundSeg, index: number): Matter.Body {
    const midX = (seg.x0 + seg.x1) / 2;
    const midY = (seg.y0 + seg.y1) / 2;
    const len = Math.hypot(seg.x1 - seg.x0, seg.y1 - seg.y0);
    const thickness = 26;
    // The authored line is the walkable surface; the body's centroid sits
    // `thickness/2` below it along the segment's own normal (down-facing at angle 0).
    const nx = -Math.sin(seg.angle);
    const ny = Math.cos(seg.angle);
    const cx = midX + nx * (thickness / 2);
    const cy = midY + ny * (thickness / 2);
    const body = Bodies.rectangle(cx, cy, len + 4, thickness, {
      isStatic: true,
      friction: 1,
      plugin: { type: "ground", angle: seg.angle } as BodyPlugin,
    });
    Body.setAngle(body, seg.angle);
    Body.setPosition(body, { x: cx, y: cy });
    void index;
    return body;
  }

  private respawn(pr: PlayerRuntime) {
    const { x, y } = pr.lastCheckpoint;
    Body.setPosition(pr.body, { x, y: y - RESPAWN_LIFT });
    Body.setVelocity(pr.body, { x: 0, y: 0 });
    Body.setAngle(pr.body, 0);
    Body.setAngularVelocity(pr.body, 0);
    pr.airborneAccum = 0;
    pr.crashFlash = 20;
    pr.grounded = false;
    pr.wasAirborne = true;
  }

  step(dtMs: number, inputs: Map<string, InputState>) {
    if (this.ended) return;
    this.tick++;
    this.elapsedMs += dtMs;

    for (const pr of this.players.values()) {
      pr.hitWallTick = false;
    }

    Engine.update(this.engine, dtMs);

    for (const pr of this.players.values()) {
      if (pr.crashFlash > 0) pr.crashFlash--;
      if (pr.finished) continue;

      const input = inputs.get(pr.meta.id);
      const pos = pr.body.position;

      if (pr.body.position.y > this.circuit.worldBottom || pr.hitWallTick) {
        this.respawn(pr);
        continue;
      }

      const landingNow = pr.grounded && pr.wasAirborne;
      if (landingNow) {
        const diff = angleDiff(pr.body.angle, pr.groundAngle);
        if (Math.abs(diff) > LAND_SAFE_TOLERANCE) {
          this.respawn(pr);
          continue;
        }
        const flipsGained = Math.floor(Math.abs(pr.airborneAccum) / (Math.PI * 2));
        pr.flips += flipsGained;
        pr.airborneAccum = 0;
        Body.setAngle(pr.body, pr.groundAngle);
        Body.setAngularVelocity(pr.body, 0);
      }

      if (pr.grounded) {
        pr.wasAirborne = false;
        const tangent = { x: Math.cos(pr.groundAngle), y: Math.sin(pr.groundAngle) };
        const currentSpeed = pr.body.velocity.x * tangent.x + pr.body.velocity.y * tangent.y;
        const accelerating = !!input?.up || !!input?.jump;
        const target = accelerating ? MAX_SPEED : Math.max(currentSpeed - DECEL, 0);
        const rate = accelerating ? ACCEL : DECEL;
        const newSpeed = moveToward(currentSpeed, target, rate);
        Body.setVelocity(pr.body, { x: tangent.x * newSpeed, y: tangent.y * newSpeed });
        Body.setAngle(pr.body, lerpAngle(pr.body.angle, pr.groundAngle, 0.35));
        Body.setAngularVelocity(pr.body, 0);
      } else {
        pr.wasAirborne = true;
        let av = pr.body.angularVelocity;
        if (input?.left) av = -FLIP_RATE;
        else if (input?.right) av = FLIP_RATE;
        else av *= FLIP_DAMPING;
        Body.setAngularVelocity(pr.body, av);
        pr.airborneAccum += av;
      }

      pr.distance = Math.max(pr.distance, pos.x - this.circuit.startX);

      for (const cpX of this.circuit.checkpoints) {
        if (pos.x >= cpX && pr.lastCheckpoint.x < cpX) {
          const gy = groundYAt(this.circuit.ground, cpX);
          if (gy !== null) pr.lastCheckpoint = { x: cpX, y: gy - 40 };
        }
      }

      if (pos.x >= this.circuit.finishX && !pr.finished) {
        pr.finished = true;
        pr.finishTimeMs = this.elapsedMs;
      }

      // reset grounded flag; collision events will re-set it next step if still touching
      pr.grounded = false;
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
        x: p.body.position.x,
        y: p.body.position.y,
        angle: p.body.angle,
        vx: p.body.velocity.x,
        vy: p.body.velocity.y,
        onGround: p.grounded,
        finished: p.finished,
        finishTimeMs: p.finishTimeMs,
        distance: p.distance,
        flips: p.flips,
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
      flips: p.flips,
    }));
  }

  playerBody(id: string): Matter.Body | undefined {
    return this.players.get(id)?.body;
  }
}

function moveToward(current: number, target: number, maxDelta: number): number {
  if (current < target) return Math.min(current + maxDelta, target);
  return Math.max(current - maxDelta, target);
}

function angleDiff(a: number, b: number): number {
  let d = (a - b) % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return d;
}

function lerpAngle(a: number, b: number, t: number): number {
  return a + angleDiff(b, a) * t;
}
