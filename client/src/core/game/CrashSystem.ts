import Matter from 'matter-js';
import type { CarRig } from '../physics/car';
import type { ActiveTrack } from '../track/trackBuilder';

const GROUND_LABELS = new Set(['ground', 'ceiling']);
const SOLID_LABELS = new Set(['ground', 'ceiling', 'platform', 'hazard']);

function normalizeAngleDiff(a: number, b: number): number {
  let d = (a - b) % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return Math.abs(d);
}

export interface CrashSystemCallbacks {
  onCrash: (reason: string) => void;
  onCheckpoint?: (index: number) => void;
  onFinish?: () => void;
  onFlipLanded?: (flips: number, perfect: boolean, impactSpeed: number) => void;
  onLanded?: (impactSpeed: number) => void;
}

const CRASH_ANGLE_THRESHOLD = 1.55; // ~89deg from local ground normal
const PERFECT_ANGLE_THRESHOLD = 0.16;

export class CrashSystem {
  private wheelContacts = 0;
  private lastCheckpoint = -1;
  private finished = false;
  private crashed = false;
  private stuckFrames = 0;

  constructor(
    private engine: Matter.Engine,
    private rig: CarRig,
    private track: ActiveTrack,
    private cb: CrashSystemCallbacks,
  ) {
    Matter.Events.on(engine, 'collisionStart', this.onStart);
    Matter.Events.on(engine, 'collisionEnd', this.onEnd);
  }

  destroy() {
    Matter.Events.off(this.engine, 'collisionStart', this.onStart);
    Matter.Events.off(this.engine, 'collisionEnd', this.onEnd);
  }

  reset() {
    this.wheelContacts = 0;
    this.crashed = false;
    this.stuckFrames = 0;
    this.rig.grounded = false;
    this.rig.crashed = false;
  }

  resetCheckpointProgress() {
    this.lastCheckpoint = -1;
    this.finished = false;
  }

  private fail(reason: string) {
    if (this.crashed || this.finished) return;
    this.crashed = true;
    this.rig.crashed = true;
    this.cb.onCrash(reason);
  }

  private onStart = (evt: Matter.IEventCollision<Matter.Engine>) => {
    for (const pair of evt.pairs) {
      const { bodyA, bodyB } = pair;
      const labels = [bodyA.label, bodyB.label];

      if (labels.includes('chassis') && labels.includes('hazard')) {
        this.fail('hazard');
        continue;
      }

      if (labels.includes('chassis') && labels.some((l) => GROUND_LABELS.has(l) || l === 'platform')) {
        // The chassis is a wide, flat shape: its corners can lightly clip the
        // ground during normal suspension travel on bumpy terrain without
        // the car actually being flipped. Only treat this as a crash if the
        // car's orientation is genuinely wrong for the surface it hit.
        const groundAngle = this.track.getGroundAngleNear(this.rig.chassis.position.x, this.rig.chassis.position.y);
        const diff = normalizeAngleDiff(this.rig.chassis.angle, groundAngle);
        if (diff > CRASH_ANGLE_THRESHOLD) {
          this.fail('chassis-impact');
        }
        continue;
      }

      if (labels.includes('wheel') && labels.some((l) => SOLID_LABELS.has(l) && l !== 'hazard')) {
        const wasAirborne = this.wheelContacts === 0;
        this.wheelContacts++;
        this.rig.grounded = true;
        if (wasAirborne) this.handleLanding();
        continue;
      }

      if (labels.includes('wheel') && labels.includes('hazard')) {
        this.fail('hazard');
        continue;
      }

      if (labels.includes('chassis') && labels.includes('checkpoint')) {
        const idx = this.track.checkpoints.findIndex(
          (c) => c.body === bodyA || c.body === bodyB,
        );
        if (idx === this.lastCheckpoint + 1) {
          this.lastCheckpoint = idx;
          this.cb.onCheckpoint?.(idx);
        }
        continue;
      }

      if (labels.includes('chassis') && labels.includes('finish')) {
        if (!this.finished) {
          this.finished = true;
          this.cb.onFinish?.();
        }
      }
    }
  };

  private onEnd = (evt: Matter.IEventCollision<Matter.Engine>) => {
    for (const pair of evt.pairs) {
      const { bodyA, bodyB } = pair;
      const labels = [bodyA.label, bodyB.label];
      if (labels.includes('wheel') && labels.some((l) => SOLID_LABELS.has(l) && l !== 'hazard')) {
        this.wheelContacts = Math.max(0, this.wheelContacts - 1);
        if (this.wheelContacts === 0) {
          this.rig.grounded = false;
        }
      }
    }
  };

  private handleLanding() {
    const rotation = this.rig.airborneRotation;
    const impactSpeed = Matter.Vector.magnitude(this.rig.chassis.velocity);
    const groundAngle = this.track.getGroundAngleNear(this.rig.chassis.position.x, this.rig.chassis.position.y);
    const diff = normalizeAngleDiff(this.rig.chassis.angle, groundAngle);
    this.rig.airborneRotation = 0;

    if (diff > CRASH_ANGLE_THRESHOLD) {
      this.fail('bad-landing');
      return;
    }

    const flips = Math.round(Math.abs(rotation) / (Math.PI * 2));
    if (flips >= 1) {
      const perfect = diff < PERFECT_ANGLE_THRESHOLD;
      this.cb.onFlipLanded?.(flips, perfect, impactSpeed);
    } else {
      this.cb.onLanded?.(impactSpeed);
    }
  }

  /** Call once per animation frame to catch cars stuck flipped on flat ground. */
  tick() {
    if (this.crashed || this.finished) return;
    if (this.rig.grounded) {
      const groundAngle = this.track.getGroundAngleNear(this.rig.chassis.position.x, this.rig.chassis.position.y);
      const diff = normalizeAngleDiff(this.rig.chassis.angle, groundAngle);
      const speed = Matter.Vector.magnitude(this.rig.chassis.velocity);
      if (diff > CRASH_ANGLE_THRESHOLD && speed < 0.6) {
        this.stuckFrames++;
        if (this.stuckFrames > 40) this.fail('stuck');
      } else {
        this.stuckFrames = 0;
      }
    }
    if (this.rig.chassis.position.y > 4000) {
      this.fail('fell-off');
    }
  }
}
