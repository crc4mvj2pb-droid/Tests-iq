import * as THREE from 'three';
import { Mountain } from '../world/mountain';

export class ThirdPersonCamera {
  instance: THREE.PerspectiveCamera;
  distance = 6.5;
  private currentPos = new THREE.Vector3();
  private initialized = false;

  constructor(aspect: number) {
    this.instance = new THREE.PerspectiveCamera(62, aspect, 0.1, 900);
  }

  setAspect(aspect: number) {
    this.instance.aspect = aspect;
    this.instance.updateProjectionMatrix();
  }

  update(dt: number, yaw: number, pitch: number, target: THREE.Vector3, mountain: Mountain) {
    const pivot = target.clone().add(new THREE.Vector3(0, 1.55, 0));
    const dist = this.distance;
    const desired = new THREE.Vector3(
      dist * Math.cos(pitch) * Math.sin(yaw),
      dist * Math.sin(pitch) + 1.2,
      dist * Math.cos(pitch) * Math.cos(yaw),
    ).add(pivot);

    const terrainY = mountain.getHeight(desired.x, desired.z);
    if (desired.y < terrainY + 0.6) desired.y = terrainY + 0.6;

    if (!this.initialized) {
      this.currentPos.copy(desired);
      this.initialized = true;
    } else {
      const k = 1 - Math.exp(-dt * 10);
      this.currentPos.lerp(desired, k);
    }

    this.instance.position.copy(this.currentPos);
    this.instance.lookAt(pivot);
  }
}
