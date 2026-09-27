import * as THREE from 'three';
import type { CharacterId } from '@shared/protocol';

export interface CharacterDef {
  id: CharacterId;
  label: string;
  primary: string;
  secondary: string;
  accent: string;
  ears: 'round' | 'point' | 'tuft' | 'none';
  horns: boolean;
  tail: 'stub' | 'bushy' | 'thin' | 'none';
  snout: number;
  bodyScale: number;
}

export const CHARACTER_DEFS: Record<CharacterId, CharacterDef> = {
  marmotte: {
    id: 'marmotte',
    label: 'Marmotte',
    primary: '#b98a4e',
    secondary: '#f1d9a8',
    accent: '#7a5230',
    ears: 'round',
    horns: false,
    tail: 'stub',
    snout: 0.34,
    bodyScale: 1.08,
  },
  corbeau: {
    id: 'corbeau',
    label: 'Corbeau',
    primary: '#2b2b34',
    secondary: '#46465a',
    accent: '#e8b23d',
    ears: 'none',
    horns: false,
    tail: 'thin',
    snout: 0.52,
    bodyScale: 0.92,
  },
  renard: {
    id: 'renard',
    label: 'Renard',
    primary: '#d9722c',
    secondary: '#f7ead2',
    accent: '#2b2b2b',
    ears: 'point',
    horns: false,
    tail: 'bushy',
    snout: 0.42,
    bodyScale: 0.98,
  },
  chevre: {
    id: 'chevre',
    label: 'Chèvre',
    primary: '#e7e2d6',
    secondary: '#cfcabf',
    accent: '#5b5b5b',
    ears: 'round',
    horns: true,
    tail: 'stub',
    snout: 0.3,
    bodyScale: 1.0,
  },
  ourson: {
    id: 'ourson',
    label: 'Ourson',
    primary: '#6b4a34',
    secondary: '#8a6449',
    accent: '#3f2a1d',
    ears: 'round',
    horns: false,
    tail: 'stub',
    snout: 0.32,
    bodyScale: 1.22,
  },
  lynx: {
    id: 'lynx',
    label: 'Lynx',
    primary: '#b7a98d',
    secondary: '#87795f',
    accent: '#2e2a22',
    ears: 'tuft',
    horns: false,
    tail: 'stub',
    snout: 0.32,
    bodyScale: 1.0,
  },
};

export interface CharacterRig {
  group: THREE.Group;
  head: THREE.Group;
  body: THREE.Mesh;
  leftArm: THREE.Group;
  rightArm: THREE.Group;
  leftLeg: THREE.Group;
  rightLeg: THREE.Group;
  tail: THREE.Object3D | null;
  backpackFlap: THREE.Mesh | null;
}

function limb(radiusTop: number, radiusBottom: number, length: number, color: string): THREE.Group {
  const pivot = new THREE.Group();
  const geo = new THREE.CapsuleGeometry(radiusTop, length, 4, 8);
  const mesh = new THREE.Mesh(geo, new THREE.MeshStandardMaterial({ color, roughness: 0.85 }));
  mesh.position.y = -length / 2 - radiusTop;
  mesh.castShadow = true;
  pivot.add(mesh);
  return pivot;
}

export function buildCharacterRig(id: CharacterId, accessoryColor: string): CharacterRig {
  const def = CHARACTER_DEFS[id];
  const group = new THREE.Group();
  const s = def.bodyScale;

  const bodyGeo = new THREE.CapsuleGeometry(0.34 * s, 0.5 * s, 6, 10);
  const body = new THREE.Mesh(bodyGeo, new THREE.MeshStandardMaterial({ color: def.primary, roughness: 0.8 }));
  body.position.y = 0.95 * s;
  body.castShadow = true;
  group.add(body);

  const belly = new THREE.Mesh(
    new THREE.SphereGeometry(0.22 * s, 8, 8),
    new THREE.MeshStandardMaterial({ color: def.secondary, roughness: 0.85 }),
  );
  belly.position.set(0, 0.85 * s, 0.26 * s);
  belly.scale.set(1, 1.15, 0.65);
  group.add(belly);

  const headGroup = new THREE.Group();
  headGroup.position.y = 1.5 * s;
  const head = new THREE.Mesh(
    new THREE.SphereGeometry(0.26 * s, 10, 10),
    new THREE.MeshStandardMaterial({ color: def.primary, roughness: 0.8 }),
  );
  head.castShadow = true;
  headGroup.add(head);

  const snout: THREE.Mesh = new THREE.Mesh(
    new THREE.SphereGeometry(0.13 * s, 8, 8),
    new THREE.MeshStandardMaterial({ color: def.secondary, roughness: 0.85 }),
  );
  snout.position.set(0, -0.04 * s, def.snout * s);
  snout.scale.set(0.85, 0.75, 1.1);
  headGroup.add(snout);

  const nose = new THREE.Mesh(new THREE.SphereGeometry(0.045 * s, 6, 6), new THREE.MeshStandardMaterial({ color: def.accent }));
  nose.position.set(0, -0.02 * s, def.snout * s + 0.1 * s);
  headGroup.add(nose);

  const eyeGeo = new THREE.SphereGeometry(0.035 * s, 6, 6);
  const eyeMat = new THREE.MeshStandardMaterial({ color: '#1a1a1a' });
  for (const side of [-1, 1]) {
    const eye = new THREE.Mesh(eyeGeo, eyeMat);
    eye.position.set(0.11 * s * side, 0.05 * s, def.snout * s * 0.55 + 0.1);
    headGroup.add(eye);
  }

  if (def.ears === 'round') {
    for (const side of [-1, 1]) {
      const ear = new THREE.Mesh(
        new THREE.SphereGeometry(0.1 * s, 8, 8),
        new THREE.MeshStandardMaterial({ color: def.primary, roughness: 0.85 }),
      );
      ear.position.set(0.2 * s * side, 0.22 * s, -0.02 * s);
      headGroup.add(ear);
    }
  } else if (def.ears === 'point') {
    for (const side of [-1, 1]) {
      const ear = new THREE.Mesh(
        new THREE.ConeGeometry(0.09 * s, 0.24 * s, 6),
        new THREE.MeshStandardMaterial({ color: def.primary, roughness: 0.85 }),
      );
      ear.position.set(0.16 * s * side, 0.32 * s, -0.02 * s);
      headGroup.add(ear);
    }
  } else if (def.ears === 'tuft') {
    for (const side of [-1, 1]) {
      const ear = new THREE.Mesh(
        new THREE.ConeGeometry(0.08 * s, 0.16 * s, 6),
        new THREE.MeshStandardMaterial({ color: def.accent, roughness: 0.85 }),
      );
      ear.position.set(0.17 * s * side, 0.28 * s, -0.02 * s);
      ear.rotation.z = 0.25 * side;
      headGroup.add(ear);
    }
  }

  if (def.horns) {
    for (const side of [-1, 1]) {
      const horn = new THREE.Mesh(
        new THREE.ConeGeometry(0.035 * s, 0.26 * s, 5),
        new THREE.MeshStandardMaterial({ color: def.accent, roughness: 0.5 }),
      );
      horn.position.set(0.13 * s * side, 0.32 * s, -0.06 * s);
      horn.rotation.z = 0.35 * side;
      horn.rotation.x = -0.3;
      headGroup.add(horn);
    }
  }

  if (id === 'corbeau') {
    head.scale.set(0.85, 0.85, 0.85);
    snout.geometry = new THREE.ConeGeometry(0.07 * s, 0.34 * s, 6);
    snout.material = new THREE.MeshStandardMaterial({ color: def.accent });
    snout.position.set(0, 0, def.snout * s - 0.05);
    snout.rotation.x = Math.PI / 2;
  }

  group.add(headGroup);

  const armLen = 0.36 * s;
  const leftArm = limb(0.09 * s, 0.07 * s, armLen, def.primary);
  leftArm.position.set(0.32 * s, 1.12 * s, 0);
  const rightArm = limb(0.09 * s, 0.07 * s, armLen, def.primary);
  rightArm.position.set(-0.32 * s, 1.12 * s, 0);
  group.add(leftArm, rightArm);

  const legLen = 0.4 * s;
  const leftLeg = limb(0.11 * s, 0.09 * s, legLen, def.secondary);
  leftLeg.position.set(0.15 * s, 0.55 * s, 0);
  const rightLeg = limb(0.11 * s, 0.09 * s, legLen, def.secondary);
  rightLeg.position.set(-0.15 * s, 0.55 * s, 0);
  group.add(leftLeg, rightLeg);

  let tail: THREE.Object3D | null = null;
  if (def.tail === 'bushy') {
    tail = new THREE.Mesh(
      new THREE.ConeGeometry(0.14 * s, 0.5 * s, 8),
      new THREE.MeshStandardMaterial({ color: def.primary, roughness: 0.9 }),
    );
    tail.position.set(0, 0.95 * s, -0.4 * s);
    tail.rotation.x = Math.PI * 0.42;
    group.add(tail);
  } else if (def.tail === 'stub') {
    tail = new THREE.Mesh(new THREE.SphereGeometry(0.09 * s, 8, 8), new THREE.MeshStandardMaterial({ color: def.secondary }));
    tail.position.set(0, 0.95 * s, -0.36 * s);
    group.add(tail);
  } else if (def.tail === 'thin') {
    tail = new THREE.Mesh(
      new THREE.ConeGeometry(0.05 * s, 0.4 * s, 5),
      new THREE.MeshStandardMaterial({ color: def.accent }),
    );
    tail.position.set(0, 1.0 * s, -0.4 * s);
    tail.rotation.x = Math.PI * 0.48;
    group.add(tail);
  }

  const backpack = new THREE.Mesh(
    new THREE.BoxGeometry(0.32 * s, 0.34 * s, 0.16 * s),
    new THREE.MeshStandardMaterial({ color: accessoryColor, roughness: 0.75 }),
  );
  backpack.position.set(0, 0.98 * s, -0.28 * s);
  backpack.castShadow = true;
  group.add(backpack);

  const flap = new THREE.Mesh(
    new THREE.BoxGeometry(0.24 * s, 0.14 * s, 0.05 * s),
    new THREE.MeshStandardMaterial({ color: accessoryColor, roughness: 0.7 }),
  );
  flap.position.set(0, 1.1 * s, -0.34 * s);
  group.add(flap);

  group.traverse((obj: THREE.Object3D) => {
    if (obj instanceof THREE.Mesh) obj.castShadow = true;
  });

  return { group, head: headGroup, body, leftArm, rightArm, leftLeg, rightLeg, tail, backpackFlap: flap };
}
