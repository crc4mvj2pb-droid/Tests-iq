import * as THREE from 'three';

const MIN_PITCH = -1.35;
const MAX_PITCH = 0.95;
const MIN_DISTANCE = 3.2;
const BASE_DISTANCE = 8.5;
const TARGET_HEIGHT = 1.7;

export class OrbitFollowCamera {
  readonly camera: THREE.PerspectiveCamera;
  yaw = 0;
  pitch = 0.05;
  distance = BASE_DISTANCE;
  private currentDistance = BASE_DISTANCE;

  private raycaster = new THREE.Raycaster();
  private viewDir = new THREE.Vector3();
  private lookTarget = new THREE.Vector3();

  constructor(aspect: number) {
    this.camera = new THREE.PerspectiveCamera(65, aspect, 0.1, 900);
  }

  applyLook(dx: number, dy: number) {
    this.yaw -= dx;
    this.pitch = Math.max(MIN_PITCH, Math.min(MAX_PITCH, this.pitch - dy));
  }

  setAspect(aspect: number) {
    this.camera.aspect = aspect;
    this.camera.updateProjectionMatrix();
  }

  update(targetPos: THREE.Vector3, terrainMesh: THREE.Object3D | null, dt = 1 / 60) {
    this.lookTarget.set(targetPos.x, targetPos.y + TARGET_HEIGHT, targetPos.z);

    this.viewDir.set(
      Math.sin(this.yaw) * Math.cos(this.pitch),
      Math.sin(this.pitch),
      Math.cos(this.yaw) * Math.cos(this.pitch),
    );

    let desiredDistance = this.distance;
    if (terrainMesh) {
      this.raycaster.set(this.lookTarget, this.viewDir.clone().negate());
      this.raycaster.far = this.distance + 1;
      this.raycaster.near = 0.05;
      const hits = this.raycaster.intersectObject(terrainMesh, false);
      if (hits.length > 0) {
        desiredDistance = Math.max(MIN_DISTANCE, hits[0].distance - 0.35);
      }
    }

    // Lissage : la caméra se rapproche vite (évite de traverser un mur) mais
    // ne s'éloigne à nouveau que progressivement (évite les à-coups).
    const pullInSpeed = 18;
    const pullOutSpeed = 6;
    const speed = desiredDistance < this.currentDistance ? pullInSpeed : pullOutSpeed;
    this.currentDistance = THREE.MathUtils.lerp(this.currentDistance, desiredDistance, Math.min(1, speed * dt));

    const camPos = this.lookTarget.clone().addScaledVector(this.viewDir, -this.currentDistance);
    this.camera.position.copy(camPos);
    this.camera.lookAt(this.lookTarget);
  }
}
