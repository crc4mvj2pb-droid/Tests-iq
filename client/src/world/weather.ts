import * as THREE from 'three';

function flakeTexture(): THREE.Texture {
  const size = 32;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;
  const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grad.addColorStop(0, 'rgba(255,255,255,1)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size);
  return new THREE.CanvasTexture(canvas);
}

export class SnowField {
  points: THREE.Points;
  private velocities: Float32Array;
  private box = 60;

  constructor(count = 500) {
    const geo = new THREE.BufferGeometry();
    const positions = new Float32Array(count * 3);
    this.velocities = new Float32Array(count);
    for (let i = 0; i < count; i++) {
      positions[i * 3] = (Math.random() - 0.5) * this.box;
      positions[i * 3 + 1] = Math.random() * 40;
      positions[i * 3 + 2] = (Math.random() - 0.5) * this.box;
      this.velocities[i] = 2 + Math.random() * 3;
    }
    geo.setAttribute('position', new THREE.BufferAttribute(positions, 3));
    const mat = new THREE.PointsMaterial({
      size: 0.28,
      map: flakeTexture(),
      transparent: true,
      depthWrite: false,
      opacity: 0,
      color: 0xffffff,
    });
    this.points = new THREE.Points(geo, mat);
    this.points.frustumCulled = false;
  }

  update(dt: number, center: THREE.Vector3, intensity: number) {
    const mat = this.points.material as THREE.PointsMaterial;
    mat.opacity += (Math.min(1, intensity) * 0.85 - mat.opacity) * Math.min(1, dt * 2);
    this.points.position.set(center.x, 0, center.z);
    const pos = this.points.geometry.attributes.position as THREE.BufferAttribute;
    for (let i = 0; i < pos.count; i++) {
      let y = pos.getY(i) - this.velocities[i] * dt;
      if (y < center.y - 5) y = center.y + 30;
      pos.setY(i, y);
    }
    pos.needsUpdate = true;
  }
}
