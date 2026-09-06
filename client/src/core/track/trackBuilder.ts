import Matter from 'matter-js';
import type { PlatformSpec, TrackChunk, Vec2 } from '@shared/trackTypes';
import { CAT } from '../physics/categories';

const { Bodies, Body, Composite } = Matter;

const GROUND_THICKNESS = 60;

/** A flat safety pad placed *behind* x=0. The car's chassis is centered on
 * its spawn point, so its rear wheel sits well behind x=0 (by roughly the
 * car's wheelOffset) — without this pad that wheel would spawn over open
 * air, immediately drooping and rotating the car into a bad-angle crash
 * before the player can even react. */
export function buildStartPad(width = 240): TrackChunk {
  return {
    strips: [[{ x: -width, y: 0 }, { x: 0, y: 0 }]],
    endPoint: { x: 0, y: 0 },
    endAngle: 0,
    tag: 'start_pad',
  };
}

interface GroundSegment {
  x1: number; y1: number; x2: number; y2: number; angle: number;
}

export interface CheckpointZone {
  index: number;
  body: Matter.Body;
  x: number;
  y: number;
  angle: number;
}

interface LivePlatform {
  spec: PlatformSpec;
  body: Matter.Body;
  t: number;
  triggered: boolean;
}

export interface RenderStrip {
  points: Vec2[];
  minX: number;
  maxX: number;
}

function leftPerp(dx: number, dy: number): Vec2 {
  const len = Math.hypot(dx, dy) || 1;
  return { x: -dy / len, y: dx / len };
}

function thickenStrip(points: Vec2[], thickness: number, sign: 1 | -1): Vec2[][] {
  const quads: Vec2[][] = [];
  for (let i = 0; i < points.length - 1; i++) {
    const a = points[i];
    const b = points[i + 1];
    const n = leftPerp(b.x - a.x, b.y - a.y);
    const ox = n.x * thickness * sign;
    const oy = n.y * thickness * sign;
    quads.push([
      { x: a.x, y: a.y },
      { x: b.x, y: b.y },
      { x: b.x + ox, y: b.y + oy },
      { x: a.x + ox, y: a.y + oy },
    ]);
  }
  return quads;
}

function bodyFromQuad(quad: Vec2[], category: number, mask: number, label: string): Matter.Body {
  const cx = quad.reduce((s, p) => s + p.x, 0) / quad.length;
  const cy = quad.reduce((s, p) => s + p.y, 0) / quad.length;
  const verts = quad.map((p) => ({ x: p.x - cx, y: p.y - cy }));
  const body = Bodies.fromVertices(cx, cy, [verts], {
    isStatic: true,
    friction: 0.9,
    label,
    collisionFilter: { category, mask },
  }, true);
  return body;
}

export class ActiveTrack {
  world: Matter.World;
  private groundBodies: Matter.Body[] = [];
  private segments: GroundSegment[] = [];
  private platforms: LivePlatform[] = [];
  /** Raw (pre-thickened) top-surface polylines, kept separately so the
   * renderer can draw one smooth continuous landscape instead of a strip of
   * individually-outlined physics quads. */
  renderStrips: RenderStrip[] = [];
  renderCeilings: RenderStrip[] = [];
  loopBodies: Matter.Body[] = [];
  checkpoints: CheckpointZone[] = [];
  startPoint: Vec2 = { x: 0, y: 0 };
  startAngle = 0;
  endPoint: Vec2 = { x: 0, y: 0 };
  private hasStart = false;

  constructor(world: Matter.World) {
    this.world = world;
  }

  addChunk(chunk: TrackChunk) {
    if (!this.hasStart && chunk.tag !== 'start_pad') {
      this.startPoint = chunk.strips[0]?.[0] ?? chunk.endPoint;
      this.hasStart = true;
    }
    for (const strip of chunk.strips) {
      if (strip.length < 2) continue;
      let minX = Infinity;
      let maxX = -Infinity;
      for (let i = 0; i < strip.length - 1; i++) {
        const a = strip[i];
        const b = strip[i + 1];
        this.segments.push({ x1: a.x, y1: a.y, x2: b.x, y2: b.y, angle: Math.atan2(b.y - a.y, b.x - a.x) });
        minX = Math.min(minX, a.x, b.x);
        maxX = Math.max(maxX, a.x, b.x);
      }
      this.renderStrips.push({ points: strip, minX, maxX });
      const quads = thickenStrip(strip, GROUND_THICKNESS, 1);
      for (const q of quads) {
        const b = bodyFromQuad(q, CAT.GROUND, CAT.CHASSIS | CAT.WHEEL, 'ground');
        this.groundBodies.push(b);
        Composite.add(this.world, b);
      }
    }
    for (const ceil of chunk.ceilings ?? []) {
      if (ceil.length < 2) continue;
      let minX = Infinity;
      let maxX = -Infinity;
      for (const p of ceil) {
        minX = Math.min(minX, p.x);
        maxX = Math.max(maxX, p.x);
      }
      this.renderCeilings.push({ points: ceil, minX, maxX });
      const quads = thickenStrip(ceil, GROUND_THICKNESS, -1);
      for (const q of quads) {
        const b = bodyFromQuad(q, CAT.GROUND, CAT.CHASSIS | CAT.WHEEL, 'ceiling');
        this.groundBodies.push(b);
        Composite.add(this.world, b);
      }
    }
    for (const poly of chunk.explicitPolys ?? []) {
      // Each loop-ring quad's inner edge (poly[0] -> poly[1]) is the actual
      // ground surface at that point, so it also feeds the angle lookup
      // used for landing/crash checks and ground-stability while inside a
      // loop — without this the car would compare itself against whatever
      // flat segment happened to be physically nearest, which is wrong.
      const [innerA, innerB] = poly;
      this.segments.push({ x1: innerA.x, y1: innerA.y, x2: innerB.x, y2: innerB.y, angle: Math.atan2(innerB.y - innerA.y, innerB.x - innerA.x) });
      const b = bodyFromQuad(poly, CAT.GROUND, CAT.CHASSIS | CAT.WHEEL, 'loop');
      this.groundBodies.push(b);
      this.loopBodies.push(b);
      Composite.add(this.world, b);
    }
    for (const hz of chunk.hazards ?? []) {
      const body = Bodies.rectangle(hz.cx, hz.cy, hz.width, hz.height, {
        isStatic: true,
        angle: hz.angle,
        label: 'hazard',
        collisionFilter: { category: CAT.HAZARD, mask: CAT.CHASSIS | CAT.WHEEL },
      });
      Composite.add(this.world, body);
      this.groundBodies.push(body);
    }
    for (const spec of chunk.platforms ?? []) {
      const isStaticBody = spec.kind !== 'falling';
      const body = Bodies.rectangle(spec.cx, spec.cy, spec.width, spec.height, {
        isStatic: isStaticBody,
        angle: spec.angle,
        friction: 0.9,
        label: 'platform',
        collisionFilter: { category: CAT.PLATFORM, mask: CAT.CHASSIS | CAT.WHEEL },
      });
      Composite.add(this.world, body);
      this.platforms.push({ spec, body, t: 0, triggered: false });
    }
    if (chunk.checkpoint) {
      const p = chunk.endPoint;
      const sensor = Bodies.circle(p.x, p.y - 40, 46, {
        isStatic: true,
        isSensor: true,
        label: 'checkpoint',
        collisionFilter: { category: CAT.CHECKPOINT, mask: CAT.CHASSIS },
      });
      Composite.add(this.world, sensor);
      this.checkpoints.push({ index: this.checkpoints.length, body: sensor, x: p.x, y: p.y, angle: chunk.endAngle });
    }
    this.endPoint = chunk.endPoint;
  }

  /** Remove ground/platform/checkpoint geometry whose relevant x is far behind minX. */
  pruneBefore(minX: number) {
    this.groundBodies = this.groundBodies.filter((b) => {
      if (b.bounds.max.x < minX) {
        Composite.remove(this.world, b);
        return false;
      }
      return true;
    });
    this.loopBodies = this.loopBodies.filter((b) => b.bounds.max.x >= minX);
    this.segments = this.segments.filter((s) => Math.max(s.x1, s.x2) >= minX);
    this.renderStrips = this.renderStrips.filter((s) => s.maxX >= minX);
    this.renderCeilings = this.renderCeilings.filter((s) => s.maxX >= minX);
    for (const p of this.platforms.slice()) {
      if (p.body.position.x < minX - 400) {
        Composite.remove(this.world, p.body);
        this.platforms.splice(this.platforms.indexOf(p), 1);
      }
    }
  }

  getGroundAngleNear(x: number, y: number): number {
    let best: GroundSegment | null = null;
    let bestDist = Infinity;
    for (const s of this.segments) {
      const mx = (s.x1 + s.x2) / 2;
      const my = (s.y1 + s.y2) / 2;
      const d = (mx - x) ** 2 + (my - y) ** 2;
      if (d < bestDist) {
        bestDist = d;
        best = s;
      }
    }
    return best ? best.angle : 0;
  }

  update(dtSeconds: number, carX: number) {
    for (const p of this.platforms) {
      const spec = p.spec;
      if (spec.kind === 'moving') {
        p.t += dtSeconds * (spec.speed ?? 1);
        const off = Math.sin(p.t) * spec.param;
        if (spec.axis === 1) {
          Body.setPosition(p.body, { x: spec.cx, y: spec.cy + off });
        } else {
          Body.setPosition(p.body, { x: spec.cx + off, y: spec.cy });
        }
      } else if (spec.kind === 'rotating') {
        p.t += dtSeconds * spec.param;
        Body.setAngle(p.body, spec.angle + p.t);
      } else if (spec.kind === 'falling' && !p.triggered) {
        if (Math.abs(p.body.position.x - carX) < 90) {
          p.triggered = true;
          setTimeout(() => {
            Body.setStatic(p.body, false);
          }, spec.param);
        }
      }
    }
  }
}
