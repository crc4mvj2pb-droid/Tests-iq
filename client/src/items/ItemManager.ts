import * as THREE from 'three';
import { mulberry32, randRange, pick } from '@shared/rng';
import { Mountain, MOUNTAIN_RADIUS } from '../world/mountain';
import { buildItemMesh, ITEM_DEFS, ITEM_IDS, ItemId } from './items';

export interface WorldItem {
  instanceId: string;
  itemId: ItemId;
  position: THREE.Vector3;
  mesh: THREE.Object3D;
  collected: boolean;
}

const TOTAL_ITEMS = 46;

export class ItemManager {
  items: WorldItem[] = [];
  private group = new THREE.Group();

  constructor(scene: THREE.Object3D, mountain: Mountain, seed: number) {
    const rand = mulberry32(seed ^ 0x3c6ef372);
    const weighted: ItemId[] = [];
    for (const id of ITEM_IDS) {
      const def = ITEM_DEFS[id];
      for (let i = 0; i < def.weight; i++) weighted.push(id);
    }

    let attempts = 0;
    let placed = 0;
    while (placed < TOTAL_ITEMS && attempts < TOTAL_ITEMS * 60) {
      attempts++;
      const angle = randRange(rand, 0, Math.PI * 2);
      const r = randRange(rand, MOUNTAIN_RADIUS * 0.08, MOUNTAIN_RADIUS * 0.95);
      const x = Math.cos(angle) * r;
      const z = Math.sin(angle) * r;
      const slope = mountain.getSlopeDeg(x, z);
      if (slope > 52) continue; // keep pickups reachable without mid-air placement
      const y = mountain.getHeight(x, z);
      const itemId = pick(rand, weighted);
      const mesh = buildItemMesh(itemId);
      mesh.position.set(x, y + 0.4, z);
      this.group.add(mesh);
      this.items.push({
        instanceId: `it_${placed}_${itemId}`,
        itemId,
        position: new THREE.Vector3(x, y + 0.4, z),
        mesh,
        collected: false,
      });
      placed++;
    }
    scene.add(this.group);
  }

  update(dt: number, time: number) {
    for (const it of this.items) {
      if (it.collected) continue;
      it.mesh.rotation.y += dt * 0.9;
      it.mesh.position.y = it.position.y + Math.sin(time * 2 + it.position.x) * 0.08;
    }
  }

  tryPickup(playerPos: THREE.Vector3, radius = 1.6): WorldItem | null {
    for (const it of this.items) {
      if (it.collected) continue;
      if (it.position.distanceTo(playerPos) < radius) return it;
    }
    return null;
  }

  markCollected(instanceId: string) {
    const it = this.items.find((i) => i.instanceId === instanceId);
    if (it && !it.collected) {
      it.collected = true;
      it.mesh.visible = false;
    }
  }

  applyRemoteCollected(ids: string[]) {
    for (const id of ids) this.markCollected(id);
  }
}
