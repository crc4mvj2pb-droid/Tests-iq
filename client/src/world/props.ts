import * as THREE from 'three';
import { mergeGeometries } from 'three/examples/jsm/utils/BufferGeometryUtils.js';
import { mulberry32, randRange } from '@shared/rng';
import { Mountain, MOUNTAIN_RADIUS } from './mountain';

function colorGeo(geo: THREE.BufferGeometry, color: THREE.Color): THREE.BufferGeometry {
  const count = geo.attributes.position.count;
  const colors = new Float32Array(count * 3);
  for (let i = 0; i < count; i++) {
    colors[i * 3] = color.r;
    colors[i * 3 + 1] = color.g;
    colors[i * 3 + 2] = color.b;
  }
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  return geo;
}

function pineGeometry(): THREE.BufferGeometry {
  const trunk = new THREE.CylinderGeometry(0.12, 0.16, 1.1, 6);
  trunk.translate(0, 0.55, 0);
  colorGeo(trunk, new THREE.Color('#5b4230'));

  const tiers: THREE.BufferGeometry[] = [];
  const foliageColor = new THREE.Color('#2f5c33');
  for (let i = 0; i < 3; i++) {
    const h = 1.5 - i * 0.35;
    const r = 1.05 - i * 0.28;
    const cone = new THREE.ConeGeometry(r, h, 7);
    cone.translate(0, 1.1 + i * 0.75, 0);
    colorGeo(cone, foliageColor);
    tiers.push(cone);
  }
  return mergeGeometries([trunk, ...tiers], false);
}

function rockGeometry(): THREE.BufferGeometry {
  const geo = new THREE.IcosahedronGeometry(1, 0);
  const pos = geo.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < pos.count; i++) {
    const jitter = 0.85 + Math.random() * 0.3;
    pos.setXYZ(i, pos.getX(i) * jitter, pos.getY(i) * jitter * 0.75, pos.getZ(i) * jitter);
  }
  geo.computeVertexNormals();
  colorGeo(geo, new THREE.Color('#8b8177'));
  return geo;
}

function crystalGeometry(): THREE.BufferGeometry {
  const geo = new THREE.OctahedronGeometry(1, 0);
  geo.scale(0.4, 1.3, 0.4);
  colorGeo(geo, new THREE.Color('#bfe8f5'));
  return geo;
}

export function buildSummitFlag(mountain: Mountain): THREE.Group {
  const g = new THREE.Group();
  const pos = mountain.summitPos();
  g.position.copy(pos);

  const pole = new THREE.Mesh(
    new THREE.CylinderGeometry(0.06, 0.06, 3.4, 6),
    new THREE.MeshStandardMaterial({ color: '#d8d8d8', roughness: 0.6 }),
  );
  pole.position.y = 1.7;
  pole.castShadow = true;
  g.add(pole);

  const flagGeo = new THREE.PlaneGeometry(0.9, 0.55, 4, 3);
  const flagPos = flagGeo.attributes.position as THREE.BufferAttribute;
  for (let i = 0; i < flagPos.count; i++) {
    const x = flagPos.getX(i);
    flagPos.setZ(i, Math.sin(x * 3) * 0.05);
  }
  flagGeo.computeVertexNormals();
  const flag = new THREE.Mesh(
    flagGeo,
    new THREE.MeshStandardMaterial({ color: '#e0473f', side: THREE.DoubleSide, roughness: 0.8 }),
  );
  flag.position.set(0.5, 3, 0);
  flag.castShadow = true;
  g.add(flag);

  return g;
}

export function scatterProps(scene: THREE.Object3D, mountain: Mountain, seed: number) {
  const rand = mulberry32(seed ^ 0x27d4eb2f);

  const specs: { geo: THREE.BufferGeometry; count: number; test: (y: number, slope: number, biome: string) => boolean; scaleRange: [number, number] }[] = [
    {
      geo: pineGeometry(),
      count: 260,
      test: (y, slope, biome) => biome === 'grass' && slope < 30,
      scaleRange: [0.8, 1.6],
    },
    {
      geo: rockGeometry(),
      count: 180,
      test: (_y, slope, biome) => biome !== 'gully' && slope > 14 && slope < 62,
      scaleRange: [0.6, 2.4],
    },
    {
      geo: crystalGeometry(),
      count: 90,
      test: (_y, slope, biome) => biome === 'snow' && slope < 45,
      scaleRange: [0.7, 1.8],
    },
  ];

  for (const spec of specs) {
    const mat = new THREE.MeshStandardMaterial({ vertexColors: true, roughness: 0.9 });
    const inst = new THREE.InstancedMesh(spec.geo, mat, spec.count);
    inst.castShadow = true;
    inst.receiveShadow = true;
    const dummy = new THREE.Object3D();
    let placed = 0;
    let attempts = 0;
    while (placed < spec.count && attempts < spec.count * 40) {
      attempts++;
      const angle = randRange(rand, 0, Math.PI * 2);
      const r = Math.sqrt(rand()) * MOUNTAIN_RADIUS * 0.97;
      const x = Math.cos(angle) * r;
      const z = Math.sin(angle) * r;
      const y = mountain.getHeight(x, z);
      const slope = mountain.getSlopeDeg(x, z);
      const biome = mountain.getBiome(x, z, y);
      if (!spec.test(y, slope, biome)) continue;
      const scale = randRange(rand, spec.scaleRange[0], spec.scaleRange[1]);
      dummy.position.set(x, y - 0.05, z);
      dummy.rotation.set(0, randRange(rand, 0, Math.PI * 2), 0);
      dummy.scale.setScalar(scale);
      dummy.updateMatrix();
      inst.setMatrixAt(placed, dummy.matrix);
      placed++;
    }
    inst.count = placed;
    inst.instanceMatrix.needsUpdate = true;
    scene.add(inst);
  }
}
