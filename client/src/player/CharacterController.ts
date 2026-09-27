import * as THREE from 'three';
import { Mountain } from '../world/mountain';
import type { AnimState } from '@shared/protocol';

export interface ControllerInput {
  moveX: number; // strafe, -1..1, camera-relative
  moveZ: number; // forward/back, -1..1, camera-relative
  jumpPressed: boolean;
  sprint: boolean;
  grab: boolean;
}

export interface ControllerEvents {
  landedHard: boolean;
  staminaOut: boolean;
  died: boolean;
  damage: number;
  jumped: boolean;
  startedClimb: boolean;
}

const GRAVITY = -30;
const WALK_SPEED = 3.3;
const RUN_SPEED = 6.2;
const CLIMB_SPEED = 2.0;
const JUMP_VEL = 8.6;
const CLIMB_ENTER_SLOPE = 46;
const CLIMB_EXIT_SLOPE = 38;
const CLIMB_MAX_SLOPE = 82;
const STAMINA_MAX = 100;
const HEALTH_MAX = 100;

export class CharacterController {
  position: THREE.Vector3;
  velocity = new THREE.Vector3();
  yaw = 0;
  state: AnimState = 'idle';
  physState: 'ground' | 'air' | 'climb' | 'tumble' = 'ground';
  stamina = STAMINA_MAX;
  staminaMax = STAMINA_MAX;
  health = HEALTH_MAX;
  healthMax = HEALTH_MAX;
  grounded = true;
  checkpoint: THREE.Vector3;
  speedFactor = 1; // used by items (e.g. dizzy mushroom)
  private tumbleTimer = 0;
  private tumbleSpin = new THREE.Vector3();
  private staminaLockout = 0;
  private wasSprint = false;

  constructor(private mountain: Mountain, spawnPos: THREE.Vector3) {
    this.position = spawnPos.clone();
    this.checkpoint = spawnPos.clone();
  }

  setCheckpoint(pos: THREE.Vector3) {
    this.checkpoint = pos.clone();
  }

  respawn() {
    this.position.copy(this.checkpoint).add(new THREE.Vector3(0, 0.4, 0));
    this.velocity.set(0, 0, 0);
    this.health = Math.max(this.health, 60);
    this.stamina = this.staminaMax;
    this.physState = 'ground';
    this.state = 'idle';
  }

  applyImpulse(v: THREE.Vector3) {
    this.velocity.add(v);
    this.physState = 'air';
  }

  update(dt: number, input: ControllerInput, camYaw: number): ControllerEvents {
    const events: ControllerEvents = {
      landedHard: false,
      staminaOut: false,
      died: false,
      damage: 0,
      jumped: false,
      startedClimb: false,
    };
    dt = Math.min(dt, 1 / 20);

    const moveMag = Math.min(1, Math.hypot(input.moveX, input.moveZ));
    const forward = new THREE.Vector3(Math.sin(camYaw), 0, Math.cos(camYaw));
    const right = new THREE.Vector3(Math.cos(camYaw), 0, -Math.sin(camYaw));
    const wishDir = new THREE.Vector3()
      .addScaledVector(forward, input.moveZ)
      .addScaledVector(right, input.moveX);
    if (wishDir.lengthSq() > 0.0001) wishDir.normalize();

    if (this.staminaLockout > 0) this.staminaLockout -= dt;

    if (this.physState === 'tumble') {
      this.tumbleTimer -= dt;
      this.velocity.y += GRAVITY * dt;
      this.position.addScaledVector(this.velocity, dt);
      const terrainY = this.mountain.getHeight(this.position.x, this.position.z);
      if (this.position.y <= terrainY + 0.35) {
        this.position.y = terrainY + 0.35;
        this.velocity.multiplyScalar(0.2);
        if (this.tumbleTimer <= 0 && Math.abs(this.velocity.y) < 2) {
          this.physState = 'ground';
          this.state = 'idle';
        }
      }
      this.state = 'tumble';
      return events;
    }

    if (this.physState === 'climb') {
      const slope = this.mountain.getSlopeDeg(this.position.x, this.position.z);
      const stillHolding = input.grab && slope > CLIMB_EXIT_SLOPE && slope < CLIMB_MAX_SLOPE + 6 && this.stamina > 0;

      if (input.jumpPressed) {
        const normal = this.mountain.getNormal(this.position.x, this.position.z);
        this.velocity.copy(normal).multiplyScalar(5.5);
        this.velocity.y += 4;
        this.physState = 'air';
        this.state = 'jump';
        events.jumped = true;
        return events;
      }

      if (!stillHolding) {
        this.physState = this.stamina <= 0 ? 'air' : 'air';
        this.velocity.set(0, this.stamina <= 0 ? -1 : 0.5, 0);
        if (this.stamina <= 0) events.staminaOut = true;
        return events;
      }

      const normal = this.mountain.getNormal(this.position.x, this.position.z);
      const up = new THREE.Vector3(0, 1, 0);
      let tangentUp = up.clone().sub(normal.clone().multiplyScalar(up.dot(normal)));
      if (tangentUp.lengthSq() < 1e-5) tangentUp.set(0, 0, 1);
      tangentUp.normalize();
      const tangentRight = new THREE.Vector3().crossVectors(tangentUp, normal).normalize();

      const move = new THREE.Vector3()
        .addScaledVector(tangentUp, input.moveZ)
        .addScaledVector(tangentRight, input.moveX);
      if (move.lengthSq() > 1) move.normalize();

      this.position.addScaledVector(move, CLIMB_SPEED * dt);
      const newTerrainY = this.mountain.getHeight(this.position.x, this.position.z);
      this.position.y = newTerrainY + 0.05;

      const slopeFactor = 0.6 + Math.min(1, slope / 90) * 1.2;
      const staminaCost = (moveMag > 0.05 ? 9 : 5) * slopeFactor;
      this.stamina = Math.max(0, this.stamina - staminaCost * dt);

      if (moveMag > 0.05) this.yaw = Math.atan2(move.x, move.z);
      this.state = 'climb';
      this.grounded = false;
      return events;
    }

    // ground / air movement
    const targetSpeed = (input.sprint && this.stamina > 0.5 ? RUN_SPEED : WALK_SPEED) * moveMag * this.speedFactor;
    const accel = this.grounded ? 22 : 6;
    const desiredVel = wishDir.clone().multiplyScalar(targetSpeed);
    const horiz = new THREE.Vector3(this.velocity.x, 0, this.velocity.z);
    horiz.lerp(desiredVel, Math.min(1, accel * dt));
    this.velocity.x = horiz.x;
    this.velocity.z = horiz.z;

    if (input.sprint && this.stamina > 0 && moveMag > 0.1 && this.grounded) {
      this.stamina = Math.max(0, this.stamina - 12 * dt);
    } else if (this.grounded && this.staminaLockout <= 0) {
      this.stamina = Math.min(this.staminaMax, this.stamina + 16 * dt);
    }

    const slopeHere = this.mountain.getSlopeDeg(this.position.x, this.position.z);
    const canStartClimb = input.grab && slopeHere > CLIMB_ENTER_SLOPE && slopeHere < CLIMB_MAX_SLOPE && this.stamina > 2;
    if (canStartClimb) {
      this.physState = 'climb';
      this.velocity.set(0, 0, 0);
      events.startedClimb = true;
      this.state = 'climb';
      return events;
    }

    if (this.grounded && input.jumpPressed && slopeHere < 60) {
      this.velocity.y = JUMP_VEL;
      this.grounded = false;
      events.jumped = true;
      this.stamina = Math.max(0, this.stamina - 4);
    }

    this.velocity.y += GRAVITY * dt;
    const prevVy = this.velocity.y;
    this.position.addScaledVector(this.velocity, dt);

    const terrainY = this.mountain.getHeight(this.position.x, this.position.z);
    if (this.position.y <= terrainY + 0.35) {
      const wasFalling = !this.grounded;
      this.position.y = terrainY + 0.35;
      if (wasFalling && prevVy < -15) {
        const dmg = Math.min(65, (Math.abs(prevVy) - 15) * 5.5);
        this.health = Math.max(0, this.health - dmg);
        events.damage = dmg;
        events.landedHard = true;
        if (this.health <= 0) {
          events.died = true;
          this.physState = 'tumble';
          this.tumbleTimer = 1.1;
          this.state = 'tumble';
          this.velocity.set((Math.random() - 0.5) * 3, 4, (Math.random() - 0.5) * 3);
          return events;
        }
      }
      this.velocity.y = 0;
      this.grounded = true;
      this.physState = 'ground';

      const slopeNow = this.mountain.getSlopeDeg(this.position.x, this.position.z);
      if (slopeNow > 63 && !input.grab) {
        const normal = this.mountain.getNormal(this.position.x, this.position.z);
        const downSlope = new THREE.Vector3(normal.x, 0, normal.z).normalize();
        this.position.addScaledVector(downSlope, -3.2 * dt);
      }
    } else {
      this.grounded = false;
      this.physState = 'air';
    }

    if (moveMag > 0.08) this.yaw = Math.atan2(wishDir.x, wishDir.z);

    if (!this.grounded) {
      this.state = this.velocity.y > 1 ? 'jump' : 'fall';
    } else if (moveMag > 0.6 && input.sprint && this.stamina > 0) {
      this.state = 'run';
    } else if (moveMag > 0.08) {
      this.state = 'walk';
    } else {
      this.state = 'idle';
    }

    return events;
  }
}
