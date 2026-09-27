import * as THREE from 'three';

const RAIN_COUNT = 900;
const AREA = 40;
const HEIGHT = 30;

export class Weather {
  readonly group = new THREE.Group();
  isRaining = false;

  private points: THREE.Points;
  private velocities: Float32Array;
  private timer = 0;
  private nextToggle = 25 + Math.random() * 20;

  constructor() {
    const positions = new Float32Array(RAIN_COUNT * 3);
    this.velocities = new Float32Array(RAIN_COUNT);
    for (let i = 0; i < RAIN_COUNT; i++) {
      positions[i * 3] = (Math.random() - 0.5) * AREA;
      positions[i * 3 + 1] = Math.random() * HEIGHT;
      positions[i * 3 + 2] = (Math.random() - 0.5) * AREA;
      this.velocities[i] = 14 + Math.random() * 8;
    }
    const geometry = new THREE.BufferGeometry();
    geometry.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const material = new THREE.PointsMaterial({
      color: '#bcd4e6',
      size: 0.12,
      transparent: true,
      opacity: 0,
      depthWrite: false,
    });
    this.points = new THREE.Points(geometry, material);
    this.group.add(this.points);
  }

  update(dt: number, followPos: THREE.Vector3) {
    this.timer += dt;
    if (this.timer > this.nextToggle) {
      this.timer = 0;
      this.nextToggle = 30 + Math.random() * 40;
      this.isRaining = !this.isRaining;
    }

    const material = this.points.material as THREE.PointsMaterial;
    const targetOpacity = this.isRaining ? 0.55 : 0;
    material.opacity = THREE.MathUtils.lerp(material.opacity, targetOpacity, Math.min(1, dt * 2));

    this.group.position.set(followPos.x, 0, followPos.z);

    if (this.isRaining) {
      const positions = this.points.geometry.getAttribute('position') as THREE.BufferAttribute;
      for (let i = 0; i < RAIN_COUNT; i++) {
        let y = positions.getY(i) - this.velocities[i] * dt;
        if (y < 0) y = HEIGHT;
        positions.setY(i, y);
      }
      positions.needsUpdate = true;
    }
  }
}
