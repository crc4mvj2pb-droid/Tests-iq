import Matter from 'matter-js';
import type { CarProfile } from '../../data/cars';
import { createCarRig, applyCarControl, resetCarRig, carSpeed, type CarRig } from '../physics/car';
import { ActiveTrack, buildStartPad } from '../track/trackBuilder';
import { ClassicTrackGenerator } from '../track/classicGenerator';
import { buildMultiplayerRound } from '../track/multiplayerRound';
import { CrashSystem } from './CrashSystem';
import { Camera } from './Camera';
import { Input } from './Input';
import { Renderer, type GhostCar } from '../render/Renderer';
import { ParticleSystem } from '../render/Particles';
import { getEnvironment } from '../../data/environments';
import { sound } from '../audio/Sound';

export const METER_PX = 22;

export type RaceMode = 'classic' | 'multiplayer';

export type RaceConfig =
  | { mode: 'classic'; seed: number }
  | { mode: 'multiplayer'; seed: number; targetDistanceM: number; environment: string };

export interface RaceStats {
  timeMs: number;
  distanceM: number;
  flips: number;
  bestCombo: number;
  score: number;
  crashes: number;
}

export interface RaceCallbacks {
  onTick?: (stats: RaceStats & { speedKmh: number; comboNow: number }) => void;
  onCountdown?: (stage: string | null) => void;
  onCheckpoint?: (index: number, total: number) => void;
  onCrash?: () => void;
  onFinish?: (stats: RaceStats) => void;
  onGameOver?: (stats: RaceStats, isNewRecord: boolean) => void;
  /** Multiplayer only: fired ~10x/s so the caller can broadcast this client's
   * position to the server for ghost-car rendering on other screens. */
  onStateUpdate?: (x: number, y: number, angle: number, speed: number) => void;
}

export interface GhostFeed {
  id: string;
  name: string;
  color: string;
  get: () => { x: number; y: number; angle: number } | null;
}

export class RaceSession {
  private engine: Matter.Engine;
  private world: Matter.World;
  private rig: CarRig;
  private track!: ActiveTrack;
  private crashSystem: CrashSystem;
  private camera = new Camera();
  private input: Input;
  private renderer = new Renderer();
  private particles = new ParticleSystem();
  private ctx: CanvasRenderingContext2D;
  private raf = 0;
  private lastTime = 0;
  private accumulator = 0;
  private readonly fixedDt = 1 / 60;
  private controlEnabled = false;
  private running = false;

  private environmentId!: string;
  private classicGen: ClassicTrackGenerator | null = null;
  private finishBody: Matter.Body | null = null;

  private elapsedMs = 0;
  private distanceM = 0;
  private flips = 0;
  private comboCount = 0;
  private bestCombo = 0;
  private score = 0;
  private crashes = 0;
  private startX = 0;
  private respawnPoint = { x: 0, y: 0, angle: 0 };
  private lastCheckpointIdx = -1;
  private gameOverFired = false;

  ghosts: GhostFeed[] = [];

  private mode: RaceMode;
  private stateBroadcastAccum = 0;

  constructor(
    private canvas: HTMLCanvasElement,
    private profile: CarProfile,
    config: RaceConfig,
    private callbacks: RaceCallbacks,
  ) {
    this.mode = config.mode;
    this.engine = Matter.Engine.create({ gravity: { x: 0, y: 1, scale: 0.0009 } });
    this.world = this.engine.world;
    const ctx = canvas.getContext('2d');
    if (!ctx) throw new Error('Canvas 2D context unavailable');
    this.ctx = ctx;
    this.input = new Input((canvas.parentElement as HTMLElement) ?? canvas);

    if (config.mode === 'multiplayer') {
      this.environmentId = config.environment;
      const built = buildMultiplayerRound(this.world, config.seed, config.targetDistanceM);
      this.track = built.track;
      this.finishBody = built.finishBody;
      this.startX = built.start.x;
      this.respawnPoint = { x: built.start.x, y: built.start.y - 60, angle: 0 };
    } else {
      this.environmentId = pickClassicEnvironment();
      this.track = new ActiveTrack(this.world);
      this.track.addChunk(buildStartPad());
      this.classicGen = new ClassicTrackGenerator(this.track, config.seed, { x: 0, y: 0 });
      this.classicGen.generateAhead(2400);
      this.startX = 0;
      this.respawnPoint = { x: 0, y: -60, angle: 0 };
    }

    this.rig = createCarRig(profile, this.respawnPoint.x, this.respawnPoint.y);
    Matter.Composite.add(this.world, this.rig.composite);

    this.crashSystem = new CrashSystem(this.engine, this.rig, this.track, {
      onCrash: () => this.handleCrash(),
      onCheckpoint: (idx) => this.handleCheckpoint(idx),
      onFinish: () => this.handleFinish(),
      onFlipLanded: (flips, perfect) => this.handleFlip(flips, perfect),
      onLanded: () => {
        this.comboCount = 0;
        sound.landing();
      },
    });
  }

  start() {
    this.running = true;
    sound.startEngine();
    this.runCountdown(() => {
      this.controlEnabled = true;
      this.callbacks.onCountdown?.(null);
    });
    this.raf = requestAnimationFrame(this.loop);
  }

  destroy() {
    this.running = false;
    cancelAnimationFrame(this.raf);
    this.crashSystem.destroy();
    this.input.destroy();
    sound.stopEngine();
    Matter.World.clear(this.world, false);
    Matter.Engine.clear(this.engine);
  }

  private runCountdown(done: () => void) {
    this.controlEnabled = false;
    const steps = ['3', '2', '1', 'GO !'];
    let i = 0;
    const next = () => {
      if (!this.running) return;
      this.callbacks.onCountdown?.(steps[i]);
      sound.countdownBeep(i === steps.length - 1);
      i++;
      if (i < steps.length) setTimeout(next, 600);
      else setTimeout(done, 500);
    };
    next();
  }

  private handleCheckpoint(idx: number) {
    const cp = this.track.checkpoints[idx];
    if (cp) this.respawnPoint = { x: cp.x, y: cp.y - 40, angle: cp.angle };
    this.lastCheckpointIdx = idx;
    sound.checkpoint();
    this.callbacks.onCheckpoint?.(idx, this.track.checkpoints.length);
  }

  private handleFlip(flips: number, perfect: boolean) {
    this.flips += flips;
    this.comboCount += 1;
    this.bestCombo = Math.max(this.bestCombo, this.comboCount);
    const base = flips >= 3 ? 500 : flips === 2 ? 250 : 100;
    const multiplier = 1 + Math.floor(this.comboCount / 2) * 0.5;
    this.score += Math.round(base * multiplier) + (perfect ? 150 : 0);
    sound.flip();
    if (perfect) sound.perfectLanding();
    this.particles.spawnSparks(this.rig.chassis.position.x, this.rig.chassis.position.y, perfect ? '#ffe14f' : '#4fd1ff');
    this.camera.addShake(0.25);
  }

  private handleCrash() {
    this.crashes++;
    this.controlEnabled = false;
    this.camera.addShake(0.9);
    this.particles.spawnSparks(this.rig.chassis.position.x, this.rig.chassis.position.y, '#ff5a5a', 22);
    sound.crash();
    this.comboCount = 0;
    this.callbacks.onCrash?.();

    if (this.mode !== 'classic') {
      this.callbacks.onCountdown?.('CRASH');
      setTimeout(() => {
        resetCarRig(this.rig, this.respawnPoint.x, this.respawnPoint.y, this.respawnPoint.angle);
        this.crashSystem.reset();
        this.runCountdown(() => {
          this.controlEnabled = true;
          this.callbacks.onCountdown?.(null);
        });
      }, 900);
    } else {
      this.finishClassicRun();
    }
  }

  private handleFinish() {
    this.controlEnabled = false;
    sound.victory();
    this.callbacks.onFinish?.(this.currentStats());
  }

  private finishClassicRun() {
    if (this.gameOverFired) return;
    this.gameOverFired = true;
    const stats = this.currentStats();
    this.callbacks.onGameOver?.(stats, false);
  }

  private currentStats(): RaceStats {
    return {
      timeMs: this.elapsedMs,
      distanceM: Math.round(this.distanceM),
      flips: this.flips,
      bestCombo: this.bestCombo,
      score: Math.round(this.score),
      crashes: this.crashes,
    };
  }

  private loop = (time: number) => {
    if (!this.running) return;
    if (!this.lastTime) this.lastTime = time;
    let dt = (time - this.lastTime) / 1000;
    this.lastTime = time;
    dt = Math.min(dt, 0.05);
    this.accumulator += dt;

    while (this.accumulator >= this.fixedDt) {
      const groundAngle = this.rig.groundedWheels >= 2
        ? this.track.getGroundAngleNear(this.rig.chassis.position.x, this.rig.chassis.position.y)
        : 0;
      applyCarControl(this.rig, this.controlEnabled && this.input.held, this.fixedDt, groundAngle);
      Matter.Engine.update(this.engine, this.fixedDt * 1000);
      this.crashSystem.tick();
      this.accumulator -= this.fixedDt;
      if (this.controlEnabled) this.elapsedMs += this.fixedDt * 1000;
    }

    sound.updateEngine(carSpeed(this.rig), this.controlEnabled && this.input.held);

    const carX = this.rig.chassis.position.x;
    const newDistanceM = Math.max(this.distanceM, (carX - this.startX) / METER_PX);
    if (this.mode === 'classic' && newDistanceM > this.distanceM) {
      this.score += (newDistanceM - this.distanceM) * 10;
    }
    this.distanceM = newDistanceM;

    this.track.update(dt, carX);
    if (this.mode === 'classic' && this.classicGen) {
      this.classicGen.generateAhead(carX + 2200);
      this.track.pruneBefore(carX - 1400);
    }
    this.particles.update(dt);
    this.camera.follow(carX, this.rig.chassis.position.y, this.rig.chassis.velocity.x * 40, dt);

    if (this.mode === 'multiplayer') {
      this.stateBroadcastAccum += dt;
      if (this.stateBroadcastAccum > 0.1) {
        this.stateBroadcastAccum = 0;
        this.callbacks.onStateUpdate?.(carX, this.rig.chassis.position.y, this.rig.chassis.angle, carSpeed(this.rig));
      }
    }

    this.render();

    this.callbacks.onTick?.({
      ...this.currentStats(),
      distanceM: Math.round(this.distanceM),
      score: Math.round(this.score),
      speedKmh: Math.round(carSpeed(this.rig) * 11),
      comboNow: this.comboCount,
    });

    if (this.rig.chassis.position.y > 4200 && this.mode === 'classic' && !this.gameOverFired) {
      this.finishClassicRun();
    }

    this.raf = requestAnimationFrame(this.loop);
  };

  private render() {
    const { width, height } = this.canvas;
    const ctx = this.ctx;
    const env = getEnvironment(this.environmentId);
    ctx.save();
    ctx.clearRect(0, 0, width, height);
    this.renderer.drawBackground(ctx, width, height, this.camera.x, env);
    ctx.save();
    this.camera.applyTransform(ctx, width, height);
    this.renderer.drawWorld(ctx, this.world, env);
    if (this.mode !== 'classic') {
      this.renderer.drawCheckpoints(
        ctx,
        this.track.checkpoints.map((c) => ({ x: c.x, y: c.y })),
        this.lastCheckpointIdx,
        env.accent,
      );
      if (this.finishBody) this.renderer.drawFinish(ctx, this.finishBody.position.x, this.finishBody.position.y);
    }
    for (const g of this.ghosts) {
      const state = g.get();
      if (state) this.renderer.drawGhost(ctx, { ...state, color: g.color, name: g.name } as GhostCar);
    }
    this.renderer.drawCar(ctx, this.rig, this.profile);
    this.renderer.drawParticles(ctx, this.particles);
    ctx.restore();
    ctx.restore();
  }

  getRig() {
    return this.rig;
  }

  isThrottleHeld() {
    return this.rig.throttleHeld;
  }
}

function pickClassicEnvironment(): string {
  const ids = ['neon_city', 'desert', 'industrial', 'sky', 'volcano', 'arctic'];
  return ids[Math.floor(Math.random() * ids.length)];
}
