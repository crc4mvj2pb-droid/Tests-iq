import * as THREE from 'three';
import type { MountainGenerator, Checkpoint, PlacedItem } from '../terrain/MountainGenerator';
import type { InputState } from '../game/InputState';
import { emptyInventory, type Inventory } from './Inventory';
import {
  GRAVITY,
  WALK_SPEED,
  RUN_SPEED,
  AIR_CONTROL,
  JUMP_SPEED,
  JUMP_STAMINA_COST,
  CLIMB_SPEED,
  GRAB_REACH,
  WALL_STANDOFF,
  SLIP_SPEED,
  MAX_STAMINA,
  STAMINA_CLIMB_DRAIN,
  STAMINA_CLIMB_DRAIN_STEEP_MULT,
  STAMINA_SPRINT_DRAIN,
  STAMINA_REGEN_GROUND,
  STAMINA_EXHAUST_LOCK_S,
  MAX_HUNGER,
  HUNGER_DRAIN_PER_S,
  STARVE_HEALTH_DRAIN,
  BERRY_HUNGER_RESTORE,
  MAX_HEALTH,
  SAFE_FALL_DISTANCE,
  FALL_DAMAGE_PER_UNIT,
  HEALTH_REGEN_PER_S,
  COLD_ALTITUDE_THRESHOLD,
  COLD_RATE,
  COLD_REGEN,
  COLD_HEALTH_DRAIN,
  SUMMIT_HEIGHT,
  DOWNED_TIME_S,
  RESPAWN_HEALTH,
  CHALK_DURATION_S,
  CHALK_DRAIN_MULT,
  WALK_MAX_SLOPE,
  CLIMB_MAX_SLOPE,
} from '../../../../shared/constants';

export type PlayerAnimState = 'idle' | 'walk' | 'run' | 'climb' | 'air' | 'downed';

export interface PlayerEvents {
  onPickup?: (item: PlacedItem) => void;
  onCheckpoint?: (checkpoint: Checkpoint) => void;
  onSummit?: () => void;
  onDamage?: (amount: number) => void;
  onDowned?: () => void;
  onRespawn?: () => void;
  onToast?: (message: string) => void;
}

const PICKUP_RADIUS = 1.6;
const CHECKPOINT_RADIUS = 3;
const SUMMIT_RADIUS = 4;
const START_RADIUS = 213;

export class PlayerController {
  readonly position = new THREE.Vector3(0, 0, 0);
  readonly velocity = new THREE.Vector3();
  yaw = 0;

  grounded = false;
  climbing = false;
  downed = false;
  downedTimer = 0;
  anim: PlayerAnimState = 'idle';

  health = MAX_HEALTH;
  stamina = MAX_STAMINA;
  hunger = MAX_HUNGER;
  cold = 0;
  exhaustLock = 0;
  chalkTimer = 0;

  inventory: Inventory = emptyInventory();
  wet = false;

  lastCheckpoint: [number, number, number];
  private collectedCheckpoints = new Set<number>();
  private collectedItems = new Set<string>();
  private peakY = 0;
  private wasAirborne = false;
  private finished = false;

  constructor(
    private mountain: MountainGenerator,
    private checkpoints: Checkpoint[],
    private items: PlacedItem[],
    private events: PlayerEvents = {},
  ) {
    const start = this.findStartPosition();
    this.position.set(start[0], start[1], start[2]);
    this.lastCheckpoint = start;
    this.peakY = this.position.y;
    this.grounded = true;
  }

  // Cherche un point de départ proche du bord de la montagne où le relief est
  // localement le plus plat possible (évite un spawn au pied d'une paroi).
  private findStartPosition(): [number, number, number] {
    let best: [number, number, number] | null = null;
    let bestSlope = Infinity;
    for (let ring = 0; ring < 4; ring++) {
      const radius = START_RADIUS + ring * 3;
      for (let a = 0; a < 48; a++) {
        const theta = (a / 48) * Math.PI * 2;
        const x = Math.cos(theta) * radius;
        const z = Math.sin(theta) * radius;
        const { slope } = this.mountain.normalAt(x, z);
        if (slope < bestSlope) {
          bestSlope = slope;
          best = [x, this.mountain.heightAt(x, z) + 0.1, z];
        }
        if (bestSlope < 0.12) break;
      }
      if (bestSlope < 0.12) break;
    }
    return best ?? [START_RADIUS, this.mountain.heightAt(START_RADIUS, 0) + 0.1, 0];
  }

  get altitudeFraction(): number {
    return Math.min(1, this.position.y / SUMMIT_HEIGHT);
  }

  private respawnAt(pos: [number, number, number], healthValue: number) {
    this.position.set(pos[0], pos[1], pos[2]);
    this.velocity.set(0, 0, 0);
    this.health = healthValue;
    this.downed = false;
    this.downedTimer = 0;
    this.climbing = false;
    this.grounded = true;
    this.wasAirborne = false;
    this.peakY = this.position.y;
    this.events.onRespawn?.();
  }

  reviveInPlace() {
    if (!this.downed) return;
    this.downed = false;
    this.downedTimer = 0;
    this.health = Math.min(MAX_HEALTH, this.health + 40);
  }

  private applyDamage(amount: number) {
    if (amount <= 0) return;
    this.health = Math.max(0, this.health - amount);
    this.events.onDamage?.(amount);
  }

  update(dt: number, input: InputState, cameraYaw: number) {
    this.yaw = cameraYaw;
    if (this.finished) return;

    if (this.downed) {
      this.downedTimer -= dt;
      this.anim = 'downed';
      if (this.downedTimer <= 0) {
        this.respawnAt(this.lastCheckpoint, RESPAWN_HEALTH);
      }
      return;
    }

    this.exhaustLock = Math.max(0, this.exhaustLock - dt);
    this.chalkTimer = Math.max(0, this.chalkTimer - dt);
    const chalkActive = this.chalkTimer > 0;
    const drainMult = chalkActive ? CHALK_DRAIN_MULT : 1;

    const h = this.mountain.heightAt(this.position.x, this.position.z);
    const { nx, ny, nz, slope } = this.mountain.normalAt(this.position.x, this.position.z);
    const heightAboveGround = this.position.y - h;

    const forward = new THREE.Vector3(Math.sin(this.yaw), 0, Math.cos(this.yaw));
    const right = new THREE.Vector3(Math.cos(this.yaw), 0, -Math.sin(this.yaw));
    const moveDir = new THREE.Vector3()
      .addScaledVector(forward, input.moveForward)
      .addScaledVector(right, input.moveRight);
    if (moveDir.lengthSq() > 1) moveDir.normalize();

    const climbable = slope > WALK_MAX_SLOPE && slope < CLIMB_MAX_SLOPE;
    const canGrab = climbable && heightAboveGround < GRAB_REACH && this.stamina > 0.5 && this.exhaustLock <= 0;

    if (input.grip && canGrab) {
      this.climbing = true;
      this.grounded = false;
      this.wasAirborne = false;

      const normal = new THREE.Vector3(nx, ny, nz);
      const worldUp = new THREE.Vector3(0, 1, 0);
      const upTangent = worldUp.clone().sub(normal.clone().multiplyScalar(normal.dot(worldUp)));
      if (upTangent.lengthSq() < 1e-5) upTangent.set(0, 0, 1);
      upTangent.normalize();
      const sideTangent = new THREE.Vector3().crossVectors(upTangent, normal).normalize();

      const climbInput = new THREE.Vector3()
        .addScaledVector(upTangent, input.moveForward)
        .addScaledVector(sideTangent, input.moveRight);
      if (climbInput.lengthSq() > 1) climbInput.normalize();

      this.velocity.copy(climbInput).multiplyScalar(CLIMB_SPEED);
      this.position.addScaledVector(this.velocity, dt);

      const newH = this.mountain.heightAt(this.position.x, this.position.z);
      const { ny: newNy } = this.mountain.normalAt(this.position.x, this.position.z);
      this.position.y = Math.max(this.position.y, newH + WALL_STANDOFF * newNy);

      const steepMult = slope > CLIMB_MAX_SLOPE * 0.75 ? STAMINA_CLIMB_DRAIN_STEEP_MULT : 1;
      const wetMult = this.wet ? 1.25 : 1;
      const moving = climbInput.lengthSq() > 0.01;
      this.stamina -= STAMINA_CLIMB_DRAIN * steepMult * drainMult * wetMult * dt * (moving ? 1 : 0.35);

      if (this.stamina <= 0) {
        this.stamina = 0;
        this.climbing = false;
        this.exhaustLock = STAMINA_EXHAUST_LOCK_S;
        this.velocity.set(0, SLIP_SPEED, 0);
        this.wasAirborne = true;
        this.peakY = this.position.y;
        this.events.onToast?.('Épuisé — la prise lâche !');
      }
      this.anim = 'climb';
    } else {
      this.climbing = false;
      const isGroundedNow = heightAboveGround <= 0.15 && this.velocity.y <= 0.05;

      if (isGroundedNow) {
        if (this.wasAirborne) {
          const fallDistance = this.peakY - h;
          if (fallDistance > SAFE_FALL_DISTANCE) {
            this.applyDamage((fallDistance - SAFE_FALL_DISTANCE) * FALL_DAMAGE_PER_UNIT);
            this.events.onToast?.('Chute douloureuse !');
          }
          this.wasAirborne = false;
        }
        this.grounded = true;

        const speed = input.sprint && this.stamina > 1 ? RUN_SPEED : WALK_SPEED;
        this.velocity.set(moveDir.x * speed, 0, moveDir.z * speed);
        this.position.x += this.velocity.x * dt;
        this.position.z += this.velocity.z * dt;
        this.position.y = this.mountain.heightAt(this.position.x, this.position.z);

        if (input.jump && this.stamina >= JUMP_STAMINA_COST) {
          this.velocity.y = JUMP_SPEED;
          this.stamina -= JUMP_STAMINA_COST;
          this.grounded = false;
          this.wasAirborne = true;
          this.peakY = this.position.y;
          this.anim = 'air';
        } else {
          if (input.sprint && moveDir.lengthSq() > 0.01) {
            this.stamina -= STAMINA_SPRINT_DRAIN * drainMult * dt;
          } else {
            this.stamina = Math.min(MAX_STAMINA, this.stamina + STAMINA_REGEN_GROUND * dt);
          }
          this.anim = moveDir.lengthSq() > 0.01 ? (input.sprint ? 'run' : 'walk') : 'idle';
        }
      } else {
        this.grounded = false;
        if (!this.wasAirborne) {
          this.wasAirborne = true;
          this.peakY = this.position.y;
        }
        this.velocity.y -= GRAVITY * dt;
        this.velocity.x = THREE.MathUtils.lerp(this.velocity.x, moveDir.x * WALK_SPEED, Math.min(1, AIR_CONTROL * dt));
        this.velocity.z = THREE.MathUtils.lerp(this.velocity.z, moveDir.z * WALK_SPEED, Math.min(1, AIR_CONTROL * dt));
        this.position.addScaledVector(this.velocity, dt);
        this.peakY = Math.max(this.peakY, this.position.y);
        this.anim = 'air';

        const groundNow = this.mountain.heightAt(this.position.x, this.position.z);
        if (this.position.y <= groundNow) {
          this.position.y = groundNow;
          this.velocity.set(0, 0, 0);
          this.grounded = true;
          this.wasAirborne = false;
          const fallDistance = this.peakY - groundNow;
          if (fallDistance > SAFE_FALL_DISTANCE) {
            this.applyDamage((fallDistance - SAFE_FALL_DISTANCE) * FALL_DAMAGE_PER_UNIT);
            this.events.onToast?.('Chute douloureuse !');
          }
        }
      }
    }

    this.updateSurvivalStats(dt);
    this.handlePickups();
    this.handleCheckpoints();
    this.handleSummit();

    if (input.useBerry && this.inventory.berries > 0) {
      this.inventory.berries -= 1;
      this.hunger = Math.min(MAX_HUNGER, this.hunger + BERRY_HUNGER_RESTORE);
      this.events.onToast?.('Baie mangée (+faim)');
    }
    if (input.placeAnchor && this.inventory.anchors > 0 && this.grounded) {
      this.inventory.anchors -= 1;
      this.lastCheckpoint = [this.position.x, this.position.y, this.position.z];
      this.events.onToast?.("Point d'ancrage posé — nouveau respawn ici");
    }

    if (this.health <= 0 && !this.downed) {
      this.downed = true;
      this.downedTimer = DOWNED_TIME_S;
      this.velocity.set(0, 0, 0);
      this.events.onDowned?.();
    }
  }

  private updateSurvivalStats(dt: number) {
    this.hunger = Math.max(0, this.hunger - HUNGER_DRAIN_PER_S * dt);
    if (this.hunger <= 0) {
      this.applyDamage(STARVE_HEALTH_DRAIN * dt);
    }

    const altFrac = this.altitudeFraction;
    if (altFrac > COLD_ALTITUDE_THRESHOLD && !this.inventory.cloakEquipped) {
      this.cold = Math.min(100, this.cold + COLD_RATE * (altFrac - COLD_ALTITUDE_THRESHOLD) * dt * 3);
    } else {
      this.cold = Math.max(0, this.cold - COLD_REGEN * dt);
    }
    if (this.cold >= 100) {
      this.applyDamage(COLD_HEALTH_DRAIN * dt);
    }

    if (this.hunger > 40 && this.cold < 60 && this.health > 0 && this.health < MAX_HEALTH) {
      this.health = Math.min(MAX_HEALTH, this.health + HEALTH_REGEN_PER_S * dt);
    }
  }

  private handlePickups() {
    for (const item of this.items) {
      if (this.collectedItems.has(item.id)) continue;
      const dx = item.pos[0] - this.position.x;
      const dy = item.pos[1] - this.position.y;
      const dz = item.pos[2] - this.position.z;
      if (dx * dx + dy * dy + dz * dz <= PICKUP_RADIUS * PICKUP_RADIUS) {
        this.collectedItems.add(item.id);
        switch (item.type) {
          case 'berry':
            this.inventory.berries += 1;
            break;
          case 'chalk':
            this.inventory.chalk += 1;
            this.chalkTimer = CHALK_DURATION_S;
            break;
          case 'anchor':
            this.inventory.anchors += 1;
            break;
          case 'cloak':
            this.inventory.cloakEquipped = true;
            break;
        }
        this.events.onPickup?.(item);
      }
    }
  }

  private handleCheckpoints() {
    for (const cp of this.checkpoints) {
      if (this.collectedCheckpoints.has(cp.index)) continue;
      const dx = cp.pos[0] - this.position.x;
      const dz = cp.pos[2] - this.position.z;
      const dy = cp.pos[1] - this.position.y;
      if (dx * dx + dy * dy + dz * dz <= CHECKPOINT_RADIUS * CHECKPOINT_RADIUS) {
        this.collectedCheckpoints.add(cp.index);
        this.lastCheckpoint = cp.pos;
        this.events.onCheckpoint?.(cp);
      }
    }
  }

  private handleSummit() {
    if (this.finished) return;
    const summit = this.mountain.summitPosition();
    const dx = summit[0] - this.position.x;
    const dz = summit[2] - this.position.z;
    const dy = summit[1] - this.position.y;
    if (dx * dx + dy * dy + dz * dz <= SUMMIT_RADIUS * SUMMIT_RADIUS) {
      this.finished = true;
      this.events.onSummit?.();
    }
  }
}
