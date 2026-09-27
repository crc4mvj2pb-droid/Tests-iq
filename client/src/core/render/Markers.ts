import * as THREE from 'three';
import type { Checkpoint, PlacedItem, ItemType } from '../terrain/MountainGenerator';

const ITEM_COLORS: Record<ItemType, string> = {
  berry: '#c23b4a',
  chalk: '#e8e2d0',
  cloak: '#3b6ea5',
  anchor: '#caa23a',
};

function buildFlag(color: string): THREE.Group {
  const group = new THREE.Group();
  const pole = new THREE.Mesh(
    new THREE.CylinderGeometry(0.04, 0.04, 2.2, 6),
    new THREE.MeshLambertMaterial({ color: '#5b4a3a' }),
  );
  pole.position.y = 1.1;
  group.add(pole);

  const flag = new THREE.Mesh(
    new THREE.PlaneGeometry(0.6, 0.4),
    new THREE.MeshLambertMaterial({ color, side: THREE.DoubleSide }),
  );
  flag.position.set(0.32, 1.8, 0);
  group.add(flag);
  return group;
}

export class WorldMarkers {
  readonly group = new THREE.Group();
  private checkpointMeshes = new Map<number, THREE.Object3D>();
  private itemMeshes = new Map<string, THREE.Object3D>();
  summitMesh: THREE.Object3D;

  constructor(checkpoints: Checkpoint[], items: PlacedItem[], summitPos: [number, number, number]) {
    for (const cp of checkpoints) {
      const flag = buildFlag('#4a90d9');
      flag.position.set(cp.pos[0], cp.pos[1], cp.pos[2]);
      this.group.add(flag);
      this.checkpointMeshes.set(cp.index, flag);
    }

    for (const item of items) {
      const mesh = new THREE.Mesh(
        new THREE.IcosahedronGeometry(0.22, 0),
        new THREE.MeshLambertMaterial({ color: ITEM_COLORS[item.type] }),
      );
      mesh.position.set(item.pos[0], item.pos[1] + 0.4, item.pos[2]);
      mesh.userData.spin = true;
      this.group.add(mesh);
      this.itemMeshes.set(item.id, mesh);
    }

    this.summitMesh = buildFlag('#d94a4a');
    this.summitMesh.scale.setScalar(1.6);
    this.summitMesh.position.set(summitPos[0], summitPos[1], summitPos[2]);
    this.group.add(this.summitMesh);
  }

  update(dt: number) {
    for (const mesh of this.itemMeshes.values()) {
      mesh.rotation.y += dt * 1.4;
      mesh.position.y += Math.sin(performance.now() * 0.002 + mesh.id) * 0.0015;
    }
  }

  collectCheckpoint(index: number) {
    const mesh = this.checkpointMeshes.get(index);
    if (mesh) mesh.visible = false;
  }

  collectItem(id: string) {
    const mesh = this.itemMeshes.get(id);
    if (mesh) mesh.visible = false;
  }
}
