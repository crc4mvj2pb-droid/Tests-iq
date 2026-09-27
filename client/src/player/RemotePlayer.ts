import * as THREE from 'three';
import { PlayerAvatar } from './PlayerAvatar';
import type { PlayerLiveState } from '@shared/protocol';

export class RemotePlayer {
  avatar: PlayerAvatar;
  id: string;
  name: string;
  private targetPos = new THREE.Vector3();
  private targetYaw = 0;
  private anim: PlayerLiveState['anim'] = 'idle';
  private lastSeen = Date.now();

  constructor(state: PlayerLiveState, accessoryColor: string) {
    this.id = state.id;
    this.name = state.name;
    this.avatar = new PlayerAvatar(state.character, accessoryColor);
    this.targetPos.set(state.x, state.y, state.z);
    this.avatar.group.position.copy(this.targetPos);
  }

  applyState(state: PlayerLiveState) {
    this.name = state.name;
    this.targetPos.set(state.x, state.y, state.z);
    this.targetYaw = state.ry;
    this.anim = state.anim;
    this.avatar.setTorchOn(state.holding === 'torche');
    this.avatar.setBeacon(state.flareUntil > Date.now());
    this.lastSeen = Date.now();
  }

  isStale(ms: number): boolean {
    return Date.now() - this.lastSeen > ms;
  }

  update(dt: number) {
    const g = this.avatar.group;
    g.position.lerp(this.targetPos, Math.min(1, dt * 10));
    let dy = this.targetYaw - g.rotation.y;
    dy = Math.atan2(Math.sin(dy), Math.cos(dy));
    g.rotation.y += dy * Math.min(1, dt * 10);
    const speed01 = this.anim === 'run' ? 1 : this.anim === 'walk' ? 0.5 : 0;
    this.avatar.update(dt, this.anim, speed01);
  }

  dispose(scene: THREE.Scene) {
    scene.remove(this.avatar.group);
  }
}
