import * as THREE from 'three';
import { mulberry32, randRange } from '@shared/rng';
import { MOUNTAIN_RADIUS } from './mountain';

function makeCloudTexture(): THREE.Texture {
  const size = 128;
  const canvas = document.createElement('canvas');
  canvas.width = size;
  canvas.height = size;
  const ctx = canvas.getContext('2d')!;
  const grad = ctx.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  grad.addColorStop(0, 'rgba(255,255,255,0.9)');
  grad.addColorStop(0.5, 'rgba(255,255,255,0.45)');
  grad.addColorStop(1, 'rgba(255,255,255,0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, size, size);
  const tex = new THREE.CanvasTexture(canvas);
  tex.needsUpdate = true;
  return tex;
}

export class CloudField {
  group = new THREE.Group();
  private sprites: { mesh: THREE.Sprite; speed: number; radius: number; angle: number; y: number }[] = [];

  constructor(seed: number) {
    const rand = mulberry32(seed ^ 0x51ed270b);
    const tex = makeCloudTexture();
    const mat = new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, fog: false });

    const count = 46;
    for (let i = 0; i < count; i++) {
      const sprite = new THREE.Sprite(mat.clone());
      const scale = randRange(rand, 45, 110);
      sprite.scale.set(scale, scale * 0.55, 1);
      const angle = randRange(rand, 0, Math.PI * 2);
      const radius = randRange(rand, MOUNTAIN_RADIUS * 0.55, MOUNTAIN_RADIUS * 1.5);
      const y = randRange(rand, -8, 18);
      sprite.material.opacity = randRange(rand, 0.35, 0.75);
      this.group.add(sprite);
      this.sprites.push({ mesh: sprite, speed: randRange(rand, 0.003, 0.012), radius, angle, y });
    }
    this.layout();

    const seaGeo = new THREE.CircleGeometry(MOUNTAIN_RADIUS * 2.6, 48);
    const seaMat = new THREE.MeshBasicMaterial({ color: 0xdfeaf2, transparent: true, opacity: 0.55, fog: false });
    const sea = new THREE.Mesh(seaGeo, seaMat);
    sea.rotation.x = -Math.PI / 2;
    sea.position.y = -5;
    this.group.add(sea);
  }

  private layout() {
    for (const s of this.sprites) {
      s.mesh.position.set(Math.cos(s.angle) * s.radius, s.y, Math.sin(s.angle) * s.radius);
    }
  }

  update(dt: number) {
    for (const s of this.sprites) {
      s.angle += s.speed * dt;
      s.mesh.position.set(Math.cos(s.angle) * s.radius, s.y, Math.sin(s.angle) * s.radius);
    }
  }
}
