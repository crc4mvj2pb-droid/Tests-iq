import * as THREE from 'three';
import { MountainGenerator, type Checkpoint, type PlacedItem, type ItemType } from '../terrain/MountainGenerator';
import { buildTerrainMesh } from '../terrain/TerrainMesh';
import { buildSky, applyFog } from '../render/Sky';
import { Weather } from '../render/Weather';
import { WorldMarkers } from '../render/Markers';
import { PlayerController, type PlayerAnimState } from '../player/PlayerController';
import { PlayerAvatar } from '../player/PlayerAvatar';
import { InputManager } from './InputManager';
import { OrbitFollowCamera } from './OrbitFollowCamera';
import type { HudState, RemoteHudInfo } from './HudState';
import type { NetClient } from '../../net/NetClient';
import type { PlayerInfo, PlayerStateSnapshot } from '../../../../shared/types';
import { REVIVE_RADIUS } from '../../../../shared/constants';

export interface GameEngineOptions {
  container: HTMLElement;
  seed: number;
  localId: string;
  localName: string;
  localColor: string;
  initialRoster: PlayerInfo[];
  net: NetClient | null;
  onHud: (hud: HudState) => void;
  onToast: (message: string) => void;
  onSummit: (timeMs: number) => void;
}

interface RemotePlayerEntry {
  info: PlayerInfo;
  avatar: PlayerAvatar;
  pos: THREE.Vector3;
  targetPos: THREE.Vector3;
  yaw: number;
  targetYaw: number;
  anim: PlayerAnimState;
  health: number;
}

const PICKUP_LABELS: Record<ItemType, string> = {
  berry: 'Baie récoltée (+faim)',
  chalk: 'Craie de préhension (+escalade)',
  cloak: 'Manteau chaud équipé',
  anchor: "Corde d'ancrage récupérée",
};

function lerpAngle(a: number, b: number, t: number): number {
  let diff = ((b - a + Math.PI) % (Math.PI * 2)) - Math.PI;
  if (diff < -Math.PI) diff += Math.PI * 2;
  return a + diff * t;
}

export class GameEngine {
  private scene = new THREE.Scene();
  private renderer: THREE.WebGLRenderer;
  private camera: OrbitFollowCamera;
  private mountain: MountainGenerator;
  private checkpoints: Checkpoint[];
  private items: PlacedItem[];
  private terrainMesh: THREE.Mesh;
  private markers: WorldMarkers;
  private weather = new Weather();
  private input: InputManager;
  private player: PlayerController;
  private localAvatar: PlayerAvatar;
  private remote = new Map<string, RemotePlayerEntry>();
  private clock = new THREE.Clock();
  private rafId = 0;
  private disposed = false;
  private startTime = performance.now();
  private finished = false;
  private netSendTimer = 0;
  private checkpointsCollectedCount = 0;
  private reviveTargetId: string | null = null;
  private resizeHandler = () => this.handleResize();

  constructor(private opts: GameEngineOptions) {
    this.mountain = new MountainGenerator(opts.seed);
    this.checkpoints = this.mountain.generateCheckpoints();
    this.items = this.mountain.generateItems();

    this.renderer = new THREE.WebGLRenderer({ antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    this.renderer.setSize(opts.container.clientWidth, opts.container.clientHeight);
    opts.container.appendChild(this.renderer.domElement);

    this.camera = new OrbitFollowCamera(opts.container.clientWidth / Math.max(1, opts.container.clientHeight));

    this.terrainMesh = buildTerrainMesh(this.mountain);
    this.scene.add(this.terrainMesh);
    this.scene.add(buildSky());
    applyFog(this.scene);
    this.scene.add(this.weather.group);

    const hemi = new THREE.HemisphereLight('#cfe3ee', '#3a3226', 0.95);
    this.scene.add(hemi);
    const sun = new THREE.DirectionalLight('#fff4de', 1.05);
    sun.position.set(120, 200, 90);
    this.scene.add(sun);

    this.markers = new WorldMarkers(this.checkpoints, this.items, this.mountain.summitPosition());
    this.scene.add(this.markers.group);

    this.player = new PlayerController(this.mountain, this.checkpoints, this.items, {
      onPickup: (item) => {
        this.markers.collectItem(item.id);
        this.opts.onToast(PICKUP_LABELS[item.type]);
      },
      onCheckpoint: (cp) => {
        this.markers.collectCheckpoint(cp.index);
        this.checkpointsCollectedCount++;
        this.opts.onToast(`Checkpoint ${cp.index}/${this.checkpoints.length} atteint`);
      },
      onSummit: () => this.handleSummit(),
      onDowned: () => {
        this.opts.net?.sendDowned();
        this.opts.onToast('À terre ! Un coéquipier peut vous relever.');
      },
      onRespawn: () => this.opts.onToast('Respawn au dernier point de passage'),
      onToast: (m) => this.opts.onToast(m),
    });

    this.localAvatar = new PlayerAvatar(opts.localColor);
    this.scene.add(this.localAvatar.group);

    this.input = new InputManager(opts.container);
    this.camera.yaw = Math.atan2(-this.player.position.x, -this.player.position.z);

    for (const p of opts.initialRoster) {
      if (p.id !== opts.localId) this.addRemote(p);
    }

    if (opts.net) this.wireNet(opts.net);

    window.addEventListener('resize', this.resizeHandler);
    this.animate();
  }

  private wireNet(net: NetClient) {
    net.callbacks.onPlayerJoined = (p) => this.addRemote(p);
    net.callbacks.onPlayerLeft = (id) => this.removeRemote(id);
    net.callbacks.onStateUpdate = (id, s) => this.applyRemoteState(id, s);
    net.callbacks.onPlayerDowned = (id) => {
      if (id !== this.opts.localId) {
        const entry = this.remote.get(id);
        this.opts.onToast(`${entry?.info.name ?? 'Un coéquipier'} est à terre !`);
      }
    };
    net.callbacks.onPlayerRevived = (id) => {
      if (id === this.opts.localId) {
        this.player.reviveInPlace();
        this.opts.onToast('Relevé par un coéquipier !');
      } else {
        this.opts.onToast(`${this.remote.get(id)?.info.name ?? 'Un coéquipier'} a été relevé`);
      }
    };
    net.callbacks.onPlayerSummited = (id, timeMs) => {
      if (id !== this.opts.localId) {
        const minutes = Math.floor(timeMs / 60000);
        const seconds = Math.floor((timeMs % 60000) / 1000);
        this.opts.onToast(
          `${this.remote.get(id)?.info.name ?? 'Un coéquipier'} a atteint le sommet ! (${minutes}:${String(seconds).padStart(2, '0')})`,
        );
      }
    };
  }

  private addRemote(info: PlayerInfo) {
    if (this.remote.has(info.id)) return;
    const avatar = new PlayerAvatar(info.color);
    this.scene.add(avatar.group);
    const start = new THREE.Vector3(this.player.position.x, this.player.position.y, this.player.position.z);
    this.remote.set(info.id, {
      info,
      avatar,
      pos: start.clone(),
      targetPos: start.clone(),
      yaw: 0,
      targetYaw: 0,
      anim: 'idle',
      health: 100,
    });
  }

  private removeRemote(id: string) {
    const entry = this.remote.get(id);
    if (!entry) return;
    this.scene.remove(entry.avatar.group);
    entry.avatar.dispose();
    this.remote.delete(id);
  }

  private applyRemoteState(id: string, s: PlayerStateSnapshot) {
    let entry = this.remote.get(id);
    if (!entry) {
      this.addRemote({ id, name: 'Coéquipier', color: '#7a9c6b', ready: true, isHost: false });
      entry = this.remote.get(id)!;
    }
    entry.targetPos.set(s.pos[0], s.pos[1], s.pos[2]);
    entry.targetYaw = s.yaw;
    entry.anim = s.anim;
    entry.health = s.health;
  }

  private findReviveTarget(): string | null {
    let best: string | null = null;
    let bestDist = REVIVE_RADIUS;
    for (const [id, entry] of this.remote) {
      if (entry.anim !== 'downed') continue;
      const d = entry.pos.distanceTo(this.player.position);
      if (d < bestDist) {
        bestDist = d;
        best = id;
      }
    }
    return best;
  }

  private handleSummit() {
    if (this.finished) return;
    this.finished = true;
    const timeMs = performance.now() - this.startTime;
    this.opts.net?.sendSummit(timeMs);
    this.opts.onSummit(timeMs);
  }

  private buildHud(): HudState {
    const remotePlayers: RemoteHudInfo[] = Array.from(this.remote.values()).map((e) => ({
      id: e.info.id,
      name: e.info.name,
      color: e.info.color,
      health: e.health,
      downed: e.anim === 'downed',
    }));
    return {
      health: this.player.health,
      stamina: this.player.stamina,
      hunger: this.player.hunger,
      cold: this.player.cold,
      altitudeFrac: this.player.altitudeFraction,
      inventory: this.player.inventory,
      anim: this.player.anim,
      downed: this.player.downed,
      downedTimer: this.player.downedTimer,
      elapsedMs: performance.now() - this.startTime,
      checkpointsCollected: this.checkpointsCollectedCount,
      checkpointsTotal: this.checkpoints.length,
      isRaining: this.weather.isRaining,
      remotePlayers,
      reviveTargetId: this.reviveTargetId,
    };
  }

  get inputManager(): InputManager {
    return this.input;
  }

  private handleResize() {
    const w = this.opts.container.clientWidth;
    const h = this.opts.container.clientHeight;
    this.renderer.setSize(w, h);
    this.camera.setAspect(w / Math.max(1, h));
  }

  private animate = () => {
    if (this.disposed) return;
    this.rafId = requestAnimationFrame(this.animate);
    const dt = Math.min(this.clock.getDelta(), 0.05);

    const input = this.input.consumeFrame();
    this.camera.applyLook(input.lookDeltaX, input.lookDeltaY);
    this.player.wet = this.weather.isRaining;

    if (!this.finished) {
      this.player.update(dt, input, this.camera.yaw);
    }

    this.camera.update(this.player.position, this.terrainMesh, dt);
    this.weather.update(dt, this.player.position);
    this.markers.update(dt);
    this.localAvatar.update(dt, this.player.position, this.player.yaw, this.player.anim);

    this.reviveTargetId = this.findReviveTarget();
    if (input.interact && this.reviveTargetId && this.opts.net) {
      this.opts.net.sendRevive(this.reviveTargetId);
    }

    for (const entry of this.remote.values()) {
      entry.pos.lerp(entry.targetPos, Math.min(1, dt * 10));
      entry.yaw = lerpAngle(entry.yaw, entry.targetYaw, Math.min(1, dt * 10));
      entry.avatar.update(dt, entry.pos, entry.yaw, entry.anim);
    }

    if (this.opts.net && !this.finished) {
      this.netSendTimer += dt;
      if (this.netSendTimer > 0.08) {
        this.netSendTimer = 0;
        this.opts.net.sendState({
          pos: [this.player.position.x, this.player.position.y, this.player.position.z],
          yaw: this.player.yaw,
          anim: this.player.anim,
          health: this.player.health,
          stamina: this.player.stamina,
          hunger: this.player.hunger,
        });
      }
    }

    this.opts.onHud(this.buildHud());
    this.renderer.render(this.scene, this.camera.camera);
  };

  dispose() {
    this.disposed = true;
    cancelAnimationFrame(this.rafId);
    window.removeEventListener('resize', this.resizeHandler);
    this.input.dispose();
    this.renderer.dispose();
    if (this.renderer.domElement.parentElement) {
      this.renderer.domElement.parentElement.removeChild(this.renderer.domElement);
    }
  }
}
