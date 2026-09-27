import * as THREE from 'three';
import { WORLD_RADIUS, SUMMIT_HEIGHT, WALK_MAX_SLOPE, CLIMB_MAX_SLOPE } from '../../../../shared/constants';
import type { MountainGenerator } from './MountainGenerator';

const ROCK_LOW = new THREE.Color('#6b6255');
const ROCK_MID = new THREE.Color('#8a7f6d');
const GRASS = new THREE.Color('#5b7a4a');
const PATH = new THREE.Color('#a68a5c');
const SNOW = new THREE.Color('#eef3f5');
const CLIFF = new THREE.Color('#4a463f');

function colorFor(y: number, slope: number, pathness: number, out: THREE.Color) {
  const altFrac = Math.min(1, y / SUMMIT_HEIGHT);
  if (altFrac > 0.82) {
    out.copy(SNOW);
    return;
  }
  if (slope > CLIMB_MAX_SLOPE * 0.9) {
    out.copy(CLIFF);
    return;
  }
  if (slope > WALK_MAX_SLOPE) {
    out.copy(ROCK_MID).lerp(CLIFF, Math.min(1, (slope - WALK_MAX_SLOPE) / 0.9));
    return;
  }
  const base = altFrac > 0.45 ? ROCK_LOW.clone().lerp(ROCK_MID, (altFrac - 0.45) / 0.4) : GRASS.clone().lerp(ROCK_LOW, altFrac / 0.45);
  out.copy(base).lerp(PATH, pathness * 0.55);
}

export function buildTerrainMesh(mountain: MountainGenerator, segments = 176): THREE.Mesh {
  const size = WORLD_RADIUS * 2;
  const verts: number[] = [];
  const colors: number[] = [];
  const indices: number[] = [];
  const step = size / segments;
  const tmpColor = new THREE.Color();

  for (let j = 0; j <= segments; j++) {
    for (let i = 0; i <= segments; i++) {
      const x = -WORLD_RADIUS + i * step;
      const z = -WORLD_RADIUS + j * step;
      const y = mountain.heightAt(x, z);
      verts.push(x, y, z);
      const { slope } = mountain.normalAt(x, z);
      colorFor(y, slope, 0, tmpColor);
      colors.push(tmpColor.r, tmpColor.g, tmpColor.b);
    }
  }

  const rowLen = segments + 1;
  for (let j = 0; j < segments; j++) {
    for (let i = 0; i < segments; i++) {
      const a = j * rowLen + i;
      const b = a + 1;
      const c = a + rowLen;
      const d = c + 1;
      indices.push(a, c, b, b, c, d);
    }
  }

  const geometry = new THREE.BufferGeometry();
  geometry.setAttribute('position', new THREE.Float32BufferAttribute(verts, 3));
  geometry.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3));
  geometry.setIndex(indices);
  geometry.computeVertexNormals();

  const material = new THREE.MeshLambertMaterial({ vertexColors: true, flatShading: true });
  const mesh = new THREE.Mesh(geometry, material);
  mesh.receiveShadow = true;
  return mesh;
}
