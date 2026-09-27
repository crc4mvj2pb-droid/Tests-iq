import * as THREE from 'three';
import { Mountain } from '../world/mountain';
import { setupSky, SkyRig } from '../world/sky';
import { CloudField } from '../world/clouds';
import { scatterProps, buildSummitFlag } from '../world/props';
import { SnowField } from '../world/weather';
import { ItemManager } from '../items/ItemManager';
import { Inventory } from '../items/Inventory';
import { ITEM_DEFS, ItemId } from '../items/items';
import { CharacterController } from '../player/CharacterController';
import { PlayerAvatar } from '../player/PlayerAvatar';
import { RemotePlayer } from '../player/RemotePlayer';
import { CHARACTER_DEFS } from '../player/characters';
import { InputManager } from '../input/InputManager';
import { mountTouchControls } from '../input/TouchControls';
import { ThirdPersonCamera } from './Camera';
import { HUD } from '../ui/HUD';
import { Menu } from '../ui/Menu';
import { AudioManager } from '../audio/Audio';
import { RoomClient } from '../net/RoomClient';
import { randSeed } from '@shared/rng';
import type { AnimState, CharacterId, PlayerLiveState } from '@shared/protocol';

type Phase = 'menu' | 'lobby' | 'countdown' | 'playing' | 'victory';

const ACCESSORY_COLORS = ['#3f6fa8', '#a84f3f', '#3fa85e', '#8a4fa8', '#a8933f', '#4fa8a0'];

export class Game {
  private renderer: THREE.WebGLRenderer;
  private scene = new THREE.Scene();
  private camera: ThirdPersonCamera;
  private clock = new THREE.Clock();
  private input: InputManager;
  private hud: HUD;
  private menu: Menu;
  private audio = new AudioManager();
  private room = new RoomClient();

  private mountain: Mountain | null = null;
  private worldGroup: THREE.Group | null = null;
  private sky: SkyRig | null = null;
  private clouds: CloudField | null = null;
  private snow: SnowField | null = null;
  private items: ItemManager | null = null;

  private controller: CharacterController | null = null;
  private localAvatar: PlayerAvatar | null = null;
  private inventory = new Inventory();
  private remotePlayers = new Map<string, RemotePlayer>();
  private announcedSummit = new Set<string>();

  private phase: Phase = 'menu';
  private isMultiplayer = false;
  private playerName = 'Aventurier';
  private character: CharacterId = 'renard';
  private startedAt = 0;
  private countdownUntil = 0;
  private netPushAccum = 0;
  private dizzyTimer = 0;
  private torchTimer = 0;

  constructor(canvas: HTMLCanvasElement, uiRoot: HTMLElement) {
    this.renderer = new THREE.WebGLRenderer({ canvas, antialias: true, powerPreference: 'high-performance' });
    this.renderer.setPixelRatio(Math.min(2, window.devicePixelRatio || 1));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.renderer.outputColorSpace = THREE.SRGBColorSpace;

    this.camera = new ThirdPersonCamera(window.innerWidth / window.innerHeight);
    this.input = new InputManager(canvas);
    mountTouchControls(uiRoot, this.input);

    this.hud = new HUD(uiRoot);
    this.hud.onHotbarTap = (i) => this.useItem(i);

    this.menu = new Menu(uiRoot, {
      onSolo: (name, character) => this.startSolo(name, character),
      onCreateRoom: (name, character) => this.createRoom(name, character),
      onJoinRoom: (code, name, character) => this.joinRoom(code, name, character),
      onToggleReady: (ready) => this.room.setReady(ready),
      onStart: () => this.room.start(),
      onLeaveLobby: () => this.leaveLobby(),
      onRestart: () => this.restart(),
      onBackToMenu: () => this.backToMenu(),
    });

    window.addEventListener('resize', () => this.onResize());
    window.addEventListener('pointerdown', () => this.audio.unlock(), { once: true });
    this.onResize();

    this.room.onLobbyUpdate = (meta) => {
      if (this.phase === 'lobby' && this.room.playerId) {
        this.menu.setLobby(meta.code, Object.values(meta.players), this.room.playerId);
      }
    };
    this.room.onGameStart = (startAt) => this.beginMultiplayerRun(startAt);

    this.animate();
  }

  private onResize() {
    this.renderer.setSize(window.innerWidth, window.innerHeight);
    this.camera.setAspect(window.innerWidth / window.innerHeight);
  }

  // ---------- flow ----------

  private startSolo(name: string, character: CharacterId) {
    this.playerName = name;
    this.character = character;
    this.isMultiplayer = false;
    this.menu.hideAll();
    this.buildWorld(randSeed());
    this.beginRun();
  }

  private async createRoom(name: string, character: CharacterId) {
    this.playerName = name;
    this.character = character;
    try {
      await this.room.create(name, character);
      this.isMultiplayer = true;
      this.phase = 'lobby';
      this.menu.showScreen('lobby');
    } catch {
      this.menu.showMpError('Impossible de créer la partie. Vérifie ta connexion.');
    }
  }

  private async joinRoom(code: string, name: string, character: CharacterId) {
    if (!/^[0-9]{4}$/.test(code)) {
      this.menu.showMpError('Entre un code à 4 chiffres.');
      return;
    }
    this.playerName = name;
    this.character = character;
    const res = await this.room.join(code, name, character).catch(() => ({ ok: false, error: 'Connexion impossible.' }));
    if (!res.ok) {
      this.menu.showMpError(res.error || 'Erreur inconnue.');
      return;
    }
    this.isMultiplayer = true;
    this.phase = 'lobby';
    this.menu.showScreen('lobby');
  }

  private leaveLobby() {
    this.room.leave();
    this.phase = 'menu';
    this.menu.showScreen('mp-choice');
  }

  private beginMultiplayerRun(startAt: number) {
    if (!this.room.seed) return;
    this.menu.hideAll();
    this.buildWorld(this.room.seed);
    const wait = startAt - Date.now();
    if (wait > 0) {
      this.phase = 'countdown';
      this.countdownUntil = startAt;
      this.hud.show();
      this.hud.setPrompt(`Départ dans ${Math.ceil(wait / 1000)}s...`);
    } else {
      this.beginRun();
    }
  }

  private beginRun() {
    this.phase = 'playing';
    this.hud.show();
    this.hud.setRoomCode(this.room.code);
    this.startedAt = performance.now();
    this.announcedSummit.clear();
  }

  private restart() {
    if (this.isMultiplayer) {
      this.room.leave();
      this.backToMenu();
    } else {
      this.startSolo(this.playerName, this.character);
    }
  }

  private backToMenu() {
    this.phase = 'menu';
    this.hud.hide();
    this.menu.showScreen('main');
  }

  // ---------- world ----------

  private clearWorld() {
    if (this.worldGroup) this.scene.remove(this.worldGroup);
    if (this.localAvatar) this.scene.remove(this.localAvatar.group);
    for (const rp of this.remotePlayers.values()) rp.dispose(this.scene);
    this.remotePlayers.clear();
    this.scene.clear();
  }

  private buildWorld(seed: number) {
    this.clearWorld();
    this.mountain = new Mountain(seed);
    this.worldGroup = new THREE.Group();

    this.sky = setupSky(this.scene);
    this.worldGroup.add(this.mountain.buildMesh());
    this.worldGroup.add(buildSummitFlag(this.mountain));
    scatterProps(this.worldGroup, this.mountain, seed);

    this.clouds = new CloudField(seed);
    this.worldGroup.add(this.clouds.group);
    this.snow = new SnowField();
    this.worldGroup.add(this.snow.points);

    this.items = new ItemManager(this.worldGroup, this.mountain, seed);
    if (this.room.collectedItems.length) this.items.applyRemoteCollected(this.room.collectedItems);

    this.scene.add(this.worldGroup);

    const spawn = this.mountain.basePos();
    this.controller = new CharacterController(this.mountain, spawn);
    const accColor = ACCESSORY_COLORS[Object.keys(CHARACTER_DEFS).indexOf(this.character) % ACCESSORY_COLORS.length];
    this.localAvatar = new PlayerAvatar(this.character, accColor);
    this.localAvatar.group.position.copy(spawn);
    this.scene.add(this.localAvatar.group);

    this.inventory = new Inventory();
    this.dizzyTimer = 0;
    this.torchTimer = 0;
    this.hud.setHotbar(this.inventory.slots, this.inventory.selected);
  }

  // ---------- items ----------

  private useItem(index: number) {
    const itemId = this.inventory.slots[index];
    if (!itemId || !this.controller) return;
    this.inventory.selected = index;
    this.inventory.consumeSelected();
    this.applyItemEffect(itemId);
    this.hud.setHotbar(this.inventory.slots, this.inventory.selected);
    this.audio.useItem();
  }

  private applyItemEffect(itemId: ItemId) {
    const c = this.controller!;
    switch (itemId) {
      case 'gourde':
        c.stamina = c.staminaMax;
        this.hud.toast('Gourde vidée : endurance restaurée !');
        break;
      case 'champignon':
        if (Math.random() < 0.7) {
          c.health = Math.min(c.healthMax, c.health + 40);
          this.hud.toast('Champignon revigorant : santé régénérée.');
        } else {
          c.speedFactor = 0.45;
          this.dizzyTimer = 3.5;
          this.hud.toast('Champignon douteux... tu as le tournis !');
        }
        break;
      case 'corde':
        c.setCheckpoint(c.position);
        this.hud.toast("Point d'ancrage posé ici.");
        break;
      case 'torche':
        this.torchTimer = 60;
        this.localAvatar?.setTorchOn(true);
        this.hud.toast('Torche allumée pour 60 secondes.');
        break;
      case 'grappin':
        this.fireGrapple();
        break;
      case 'fusee':
        this.flareUntil = Date.now() + 8000;
        this.hud.toast('Fusée envoyée : ton équipe voit ta position !');
        break;
      case 'sac':
        c.staminaMax = Math.min(160, c.staminaMax + 20);
        c.stamina = c.staminaMax;
        this.hud.toast('Sac renforcé : endurance maximale augmentée !');
        break;
    }
  }

  private flareUntil = 0;

  private fireGrapple() {
    const c = this.controller!;
    const m = this.mountain!;
    const forward = new THREE.Vector3(Math.sin(c.yaw), 0, Math.cos(c.yaw));
    let best: THREE.Vector3 | null = null;
    for (const d of [10, 16, 22, 28]) {
      const px = c.position.x + forward.x * d;
      const pz = c.position.z + forward.z * d;
      const py = m.getHeight(px, pz);
      const slope = m.getSlopeDeg(px, pz);
      if (py > c.position.y + 2 && slope < 58) best = new THREE.Vector3(px, py, pz);
    }
    if (best) {
      const dir = best.clone().sub(c.position).normalize();
      c.applyImpulse(dir.multiplyScalar(14));
      this.hud.toast('Grappin accroché !');
    } else {
      this.hud.toast('Rien à accrocher par ici...');
    }
  }

  // ---------- loop ----------

  private animate = () => {
    requestAnimationFrame(this.animate);
    const dt = Math.min(this.clock.getDelta(), 1 / 20);

    if (this.phase === 'countdown' && Date.now() >= this.countdownUntil) {
      this.beginRun();
    }
    if (this.phase === 'countdown') {
      const remain = Math.max(0, Math.ceil((this.countdownUntil - Date.now()) / 1000));
      this.hud.setPrompt(remain > 0 ? `Départ dans ${remain}s...` : null);
    }

    if ((this.phase === 'playing' || this.phase === 'countdown') && this.controller && this.mountain) {
      this.updateGameplay(dt);
    }

    this.renderer.render(this.scene, this.camera.instance);
  };

  private updateGameplay(dt: number) {
    const c = this.controller!;
    const m = this.mountain!;

    if (this.dizzyTimer > 0) {
      this.dizzyTimer -= dt;
      if (this.dizzyTimer <= 0) c.speedFactor = 1;
    }
    if (this.torchTimer > 0) {
      this.torchTimer -= dt;
      if (this.torchTimer <= 0) this.localAvatar?.setTorchOn(false);
    }

    const canAct = this.phase === 'playing';
    const jumpPressed = canAct && this.input.consumeJumpPressed();
    const events = c.update(dt, {
      moveX: canAct ? this.input.moveX : 0,
      moveZ: canAct ? this.input.moveZ : 0,
      jumpPressed,
      sprint: this.input.sprintHeld,
      grab: canAct && this.input.grabHeld,
    }, this.input.yaw);

    if (canAct) {
      const hb = this.input.consumeHotbar();
      if (hb !== null) this.useItem(hb);

      if (events.jumped) this.audio.jump();
      if (events.landedHard) this.audio.land();
      if (events.damage > 0) this.audio.hurt();
      if (events.staminaOut) {
        this.audio.fall();
        this.hud.toast("Plus d'endurance... tu lâches prise !");
      }
      if (events.died) {
        this.hud.toast('Chute sévère : retour au dernier point sûr.');
        c.respawn();
      }

      if (this.items) {
        const pickup = this.items.tryPickup(c.position);
        if (pickup) {
          const def = ITEM_DEFS[pickup.itemId];
          if (def.instant) {
            this.items.markCollected(pickup.instanceId);
            this.applyItemEffect(pickup.itemId);
            this.audio.pickup();
            this.room.pushState(this.buildLiveState(c), pickup.instanceId);
          } else if (this.inventory.add(pickup.itemId)) {
            this.items.markCollected(pickup.instanceId);
            this.hud.toast(`${def.icon} ${def.label} récupéré(e).`);
            this.hud.setHotbar(this.inventory.slots, this.inventory.selected);
            this.audio.pickup();
            this.room.pushState(this.buildLiveState(c), pickup.instanceId);
          }
        }
        this.items.update(dt, performance.now() / 1000);
        if (this.room.collectedItems.length) this.items.applyRemoteCollected(this.room.collectedItems);
      }

      const slope = m.getSlopeDeg(c.position.x, c.position.z);
      if (c.physState === 'ground' && slope > 42 && slope < 82) {
        this.hud.setPrompt('Maintiens E (ou PRISE) pour grimper');
      } else {
        this.hud.setPrompt(null);
      }
    }

    if (this.localAvatar) {
      this.localAvatar.group.position.copy(c.position);
      this.localAvatar.group.rotation.y = c.yaw;
      const speed01 = Math.min(1, new THREE.Vector2(c.velocity.x, c.velocity.z).length() / 6);
      this.localAvatar.update(dt, c.state, speed01);
    }

    this.camera.update(dt, this.input.yaw, this.input.pitch, c.position, m);
    this.sky?.updateShadowFocus(c.position);
    this.clouds?.update(dt);
    const nearSnow = m.altitudePct(c.position.y) > 55 ? (m.altitudePct(c.position.y) - 55) / 25 : 0;
    this.snow?.update(dt, c.position, nearSnow);

    this.hud.setStamina((c.stamina / c.staminaMax) * 100);
    this.hud.setHealth((c.health / c.healthMax) * 100);
    const altPct = m.altitudePct(c.position.y);
    this.hud.setAltitude(altPct);
    const toSummit = m.summitPos().clone().sub(c.position);
    const angleToSummit = Math.atan2(toSummit.x, toSummit.z) - this.input.yaw;
    this.hud.setCompass(angleToSummit);

    if (canAct && altPct > 98.5 && toSummit.length() < 6) {
      this.triggerVictory();
      return;
    }

    if (this.isMultiplayer && canAct) {
      this.netPushAccum += dt;
      if (this.netPushAccum > 0.22) {
        this.netPushAccum = 0;
        this.room.pushState(this.buildLiveState(c));
      }
      this.syncRemotePlayers(dt);
    }
  }

  private buildLiveState(c: CharacterController): Omit<PlayerLiveState, 'ts'> {
    return {
      id: this.room.playerId!,
      name: this.playerName,
      character: this.character,
      x: c.position.x,
      y: c.position.y,
      z: c.position.z,
      ry: c.yaw,
      anim: c.state as AnimState,
      stamina: c.stamina,
      health: c.health,
      altitudePct: this.mountain!.altitudePct(c.position.y),
      holding: this.torchTimer > 0 ? 'torche' : null,
      flareUntil: this.flareUntil,
    };
  }

  private syncRemotePlayers(dt: number) {
    const seen = new Set<string>();
    for (const state of this.room.players) {
      if (state.id === this.room.playerId) continue;
      seen.add(state.id);
      let rp = this.remotePlayers.get(state.id);
      if (!rp) {
        const idx = Object.keys(CHARACTER_DEFS).indexOf(state.character) % ACCESSORY_COLORS.length;
        rp = new RemotePlayer(state, ACCESSORY_COLORS[idx]);
        this.scene.add(rp.avatar.group);
        this.remotePlayers.set(state.id, rp);
      }
      rp.applyState(state);
      if (state.altitudePct > 98 && !this.announcedSummit.has(state.id)) {
        this.announcedSummit.add(state.id);
        this.hud.toast(`🏔 ${state.name} a atteint le sommet !`);
      }
    }
    for (const [id, rp] of this.remotePlayers) {
      if (!seen.has(id)) {
        rp.dispose(this.scene);
        this.remotePlayers.delete(id);
      }
    }
    for (const rp of this.remotePlayers.values()) rp.update(dt);

    const entries = [...this.remotePlayers.values()].map((rp) => {
      const head = rp.avatar.group.position.clone().add(new THREE.Vector3(0, 1.9, 0));
      const proj = head.clone().project(this.camera.instance);
      if (proj.z > 1) return { id: rp.id, name: rp.name, screen: null };
      const x = (proj.x * 0.5 + 0.5) * window.innerWidth;
      const y = (-proj.y * 0.5 + 0.5) * window.innerHeight;
      return { id: rp.id, name: rp.name, screen: { x, y } };
    });
    this.hud.updateNametags(entries);
  }

  private triggerVictory() {
    this.phase = 'victory';
    this.audio.summit();
    const seconds = (performance.now() - this.startedAt) / 1000;
    this.hud.setPrompt(null);
    this.menu.showVictory(seconds);
  }
}
