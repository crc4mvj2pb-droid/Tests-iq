import * as THREE from 'three';
import { buildCharacterRig, CharacterRig } from './characters';
import type { AnimState, CharacterId } from '@shared/protocol';

export class PlayerAvatar {
  group: THREE.Group;
  rig: CharacterRig;
  torchLight: THREE.PointLight;
  private holdAnchor: THREE.Group;
  private heldMesh: THREE.Object3D | null = null;
  private animTime = 0;
  private tumbleAxis = new THREE.Vector3(1, 0.3, 0.2).normalize();
  private bodyTilt = new THREE.Euler();

  constructor(character: CharacterId, accessoryColor: string) {
    this.rig = buildCharacterRig(character, accessoryColor);
    this.group = this.rig.group;

    this.holdAnchor = new THREE.Group();
    this.holdAnchor.position.set(-0.05, -0.42, 0.18);
    this.rig.rightArm.add(this.holdAnchor);

    this.torchLight = new THREE.PointLight(0xffb066, 0, 14, 2);
    this.torchLight.castShadow = false;
    this.holdAnchor.add(this.torchLight);
  }

  setHeldVisual(mesh: THREE.Object3D | null) {
    if (this.heldMesh) this.holdAnchor.remove(this.heldMesh);
    this.heldMesh = mesh;
    if (mesh) this.holdAnchor.add(mesh);
  }

  setTorchOn(on: boolean) {
    this.torchLight.intensity = on ? 2.4 : 0;
  }

  private beacon: THREE.Group | null = null;

  setBeacon(on: boolean) {
    if (on && !this.beacon) {
      const g = new THREE.Group();
      const beam = new THREE.Mesh(
        new THREE.CylinderGeometry(0.03, 0.03, 30, 6, 1, true),
        new THREE.MeshBasicMaterial({ color: 0xff5a3c, transparent: true, opacity: 0.55, side: THREE.DoubleSide, fog: false }),
      );
      beam.position.y = 15;
      const light = new THREE.PointLight(0xff5a3c, 3, 10);
      light.position.y = 1.5;
      g.add(beam, light);
      this.group.add(g);
      this.beacon = g;
    } else if (!on && this.beacon) {
      this.group.remove(this.beacon);
      this.beacon = null;
    }
  }

  update(dt: number, anim: AnimState, speed01: number) {
    this.animTime += dt * (0.6 + speed01 * (anim === 'run' ? 1.6 : 1));
    const t = this.animTime;
    const r = this.rig;

    r.leftArm.rotation.set(0, 0, 0);
    r.rightArm.rotation.set(0, 0, 0);
    r.leftLeg.rotation.set(0, 0, 0);
    r.rightLeg.rotation.set(0, 0, 0);
    this.group.rotation.set(0, this.group.rotation.y, 0);
    this.group.position.y = this.group.userData.baseY ?? this.group.position.y;

    switch (anim) {
      case 'walk':
      case 'run': {
        const freq = anim === 'run' ? 9 : 6;
        const amp = anim === 'run' ? 0.9 : 0.55;
        const s = Math.sin(t * freq);
        r.leftLeg.rotation.x = s * amp;
        r.rightLeg.rotation.x = -s * amp;
        r.leftArm.rotation.x = -s * amp * 0.8;
        r.rightArm.rotation.x = s * amp * 0.8;
        this.group.position.y += Math.abs(Math.sin(t * freq)) * 0.03;
        break;
      }
      case 'jump':
        r.leftArm.rotation.x = -0.9;
        r.rightArm.rotation.x = -0.9;
        r.leftLeg.rotation.x = 0.4;
        r.rightLeg.rotation.x = 0.2;
        break;
      case 'fall':
        r.leftArm.rotation.x = -1.3;
        r.rightArm.rotation.x = -1.3;
        r.leftLeg.rotation.x = 0.15;
        r.rightLeg.rotation.x = -0.15;
        break;
      case 'climb': {
        const s = Math.sin(t * 5);
        r.leftArm.rotation.x = -1.1 - s * 0.5;
        r.rightArm.rotation.x = -1.1 + s * 0.5;
        r.leftLeg.rotation.x = 0.5 + s * 0.4;
        r.rightLeg.rotation.x = 0.5 - s * 0.4;
        break;
      }
      case 'tumble':
        this.group.rotateOnAxis(this.tumbleAxis, dt * 14);
        break;
      case 'idle':
      default: {
        const s = Math.sin(t * 1.6);
        r.body.position.y = 0.95 * (this.group.userData.bodyScale ?? 1) + s * 0.012;
        r.leftArm.rotation.x = s * 0.05;
        r.rightArm.rotation.x = -s * 0.05;
        if (r.tail) r.tail.rotation.y = Math.sin(t * 1.2) * 0.2;
        break;
      }
    }
  }
}
