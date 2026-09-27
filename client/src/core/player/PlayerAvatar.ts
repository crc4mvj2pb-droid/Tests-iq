import * as THREE from 'three';
import type { PlayerAnimState } from './PlayerController';

/**
 * Silhouette basse-poly, entièrement procédurale (aucun asset externe).
 */
export class PlayerAvatar {
  readonly group = new THREE.Group();
  private torso: THREE.Mesh;
  private head: THREE.Mesh;
  private bobPhase = Math.random() * Math.PI * 2;

  constructor(color: string) {
    const bodyMat = new THREE.MeshLambertMaterial({ color });
    const headMat = new THREE.MeshLambertMaterial({ color: '#f0c9a0' });

    this.torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.32, 0.75, 4, 8), bodyMat);
    this.torso.position.y = 0.78;
    this.group.add(this.torso);

    this.head = new THREE.Mesh(new THREE.SphereGeometry(0.24, 12, 10), headMat);
    this.head.position.y = 1.42;
    this.group.add(this.head);

    const packMat = new THREE.MeshLambertMaterial({ color: '#3a3a3a' });
    const pack = new THREE.Mesh(new THREE.BoxGeometry(0.32, 0.4, 0.18), packMat);
    pack.position.set(0, 0.85, -0.28);
    this.group.add(pack);
  }

  setNameTagVisible() {
    // Réservé pour une future étiquette DOM/Sprite ; pas nécessaire au MVP.
  }

  update(dt: number, pos: THREE.Vector3, yaw: number, anim: PlayerAnimState) {
    this.group.position.copy(pos);
    this.group.rotation.y = yaw;

    this.bobPhase += dt * (anim === 'run' ? 9 : anim === 'walk' ? 6 : 3);
    const bob = anim === 'walk' || anim === 'run' ? Math.sin(this.bobPhase) * 0.05 : 0;
    this.torso.position.y = 0.78 + bob;
    this.head.position.y = 1.42 + bob;

    if (anim === 'climb') {
      this.torso.rotation.x = -0.35;
    } else if (anim === 'air') {
      this.torso.rotation.x = -0.15;
    } else if (anim === 'downed') {
      this.torso.rotation.x = Math.PI / 2.1;
    } else {
      this.torso.rotation.x = 0;
    }

    this.group.visible = true;
  }

  dispose() {
    this.torso.geometry.dispose();
    this.head.geometry.dispose();
  }
}
