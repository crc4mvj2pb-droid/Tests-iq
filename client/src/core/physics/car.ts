import Matter from 'matter-js';
import type { CarProfile } from '../../data/cars';
import { CAT } from './categories';

const { Body, Bodies, Composite, Constraint, Vector } = Matter;

export interface CarRig {
  profile: CarProfile;
  chassis: Matter.Body;
  wheelBack: Matter.Body;
  wheelFront: Matter.Body;
  axleBack: Matter.Constraint;
  axleFront: Matter.Constraint;
  composite: Matter.Composite;
  // runtime state
  grounded: boolean;
  groundedWheels: number;
  airborneRotation: number;
  crashed: boolean;
  lastSafeAngle: number;
  throttleHeld: boolean;
}

export function createCarRig(profile: CarProfile, x: number, y: number): CarRig {
  const w = profile.chassisWidth;
  const h = profile.chassisHeight;
  const r = profile.wheelRadius;
  const off = profile.wheelOffset;

  const chassis = Bodies.rectangle(x, y, w, h, {
    density: profile.density,
    friction: profile.chassisFriction,
    frictionAir: 0.012,
    restitution: profile.restitution,
    chamfer: { radius: 6 },
    collisionFilter: {
      category: CAT.CHASSIS,
      mask: CAT.GROUND | CAT.PLATFORM | CAT.HAZARD,
    },
    label: 'chassis',
  });

  const wheelOpts = {
    friction: profile.wheelFriction,
    frictionAir: 0.01,
    density: profile.density * 1.6,
    restitution: 0.15,
    collisionFilter: {
      category: CAT.WHEEL,
      mask: CAT.GROUND | CAT.PLATFORM,
    },
    label: 'wheel',
  };

  const wheelBack = Bodies.circle(x - off, y + h * 0.35, r, wheelOpts);
  const wheelFront = Bodies.circle(x + off, y + h * 0.35, r, wheelOpts);

  const mkAxle = (wheel: Matter.Body, ox: number) =>
    Constraint.create({
      bodyA: chassis,
      pointA: { x: ox, y: h * 0.35 },
      bodyB: wheel,
      stiffness: profile.suspensionStiffness,
      damping: profile.suspensionDamping,
      length: 2,
    });

  const axleBack = mkAxle(wheelBack, -off);
  const axleFront = mkAxle(wheelFront, off);

  const composite = Composite.create({ label: 'car' });
  Composite.add(composite, [chassis, wheelBack, wheelFront, axleBack, axleFront]);

  return {
    profile,
    chassis,
    wheelBack,
    wheelFront,
    axleBack,
    axleFront,
    composite,
    grounded: false,
    groundedWheels: 0,
    airborneRotation: 0,
    crashed: false,
    lastSafeAngle: 0,
    throttleHeld: false,
  };
}

function normalizeAngle(a: number): number {
  let d = a % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return d;
}

/** Call once per physics step, before Engine.update. `groundAngle` is the
 * local terrain slope under the car right now (only used while both wheels
 * are grounded). */
export function applyCarControl(rig: CarRig, throttle: boolean, dt: number, groundAngle = 0) {
  const p = rig.profile;
  rig.throttleHeld = throttle;
  const bothWheelsDown = rig.groundedWheels >= 2;

  if (throttle) {
    const target = p.maxWheelSpeed;
    Body.setAngularVelocity(rig.wheelBack, rig.wheelBack.angularVelocity + (target - rig.wheelBack.angularVelocity) * p.wheelAccelRate);
    Body.setAngularVelocity(rig.wheelFront, rig.wheelFront.angularVelocity + (target - rig.wheelFront.angularVelocity) * p.wheelAccelRate);

    if (!rig.grounded) {
      // Air control: rotate nose forward while gas is held (Rider-style).
      Body.setAngularVelocity(rig.chassis, rig.chassis.angularVelocity + p.airControlTorque);
    }
  }

  if (!rig.grounded) {
    rig.airborneRotation += rig.chassis.angularVelocity;
  } else if (bothWheelsDown) {
    // Glue the chassis to the local slope while both wheels are down, like
    // the reference game: driving on the ground stays flat and stable, all
    // rotation control happens in the air. Without this, the soft wheel
    // suspension lets the chassis tip onto one wheel on its own.
    const diff = normalizeAngle(groundAngle - rig.chassis.angle);
    Body.setAngle(rig.chassis, rig.chassis.angle + diff * p.groundStability);
    Body.setAngularVelocity(rig.chassis, rig.chassis.angularVelocity * 0.5);
  }
}

export function resetCarRig(rig: CarRig, x: number, y: number, angle = 0) {
  Body.setPosition(rig.chassis, { x, y });
  Body.setAngle(rig.chassis, angle);
  Body.setVelocity(rig.chassis, { x: 0, y: 0 });
  Body.setAngularVelocity(rig.chassis, 0);

  const off = rig.profile.wheelOffset;
  const h = rig.profile.chassisHeight;
  const cos = Math.cos(angle);
  const sin = Math.sin(angle);
  const back = Vector.add({ x, y }, Vector.rotate({ x: -off, y: h * 0.35 }, angle));
  const front = Vector.add({ x, y }, Vector.rotate({ x: off, y: h * 0.35 }, angle));
  void cos;
  void sin;

  Body.setPosition(rig.wheelBack, back);
  Body.setPosition(rig.wheelFront, front);
  Body.setAngle(rig.wheelBack, angle);
  Body.setAngle(rig.wheelFront, angle);
  Body.setVelocity(rig.wheelBack, { x: 0, y: 0 });
  Body.setVelocity(rig.wheelFront, { x: 0, y: 0 });
  Body.setAngularVelocity(rig.wheelBack, 0);
  Body.setAngularVelocity(rig.wheelFront, 0);

  rig.grounded = false;
  rig.groundedWheels = 0;
  rig.airborneRotation = 0;
  rig.crashed = false;
  rig.lastSafeAngle = angle;
}

export function carSpeed(rig: CarRig): number {
  return Vector.magnitude(rig.chassis.velocity);
}
