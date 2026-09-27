import * as THREE from 'three';

export type ItemId = 'corde' | 'torche' | 'champignon' | 'gourde' | 'grappin' | 'fusee' | 'sac';

export interface ItemDef {
  id: ItemId;
  label: string;
  icon: string;
  desc: string;
  instant: boolean; // applied immediately on pickup, never enters the hotbar
  weight: number; // spawn frequency weight
}

export const ITEM_DEFS: Record<ItemId, ItemDef> = {
  gourde: {
    id: 'gourde',
    label: 'Gourde',
    icon: '🧴',
    desc: 'Restaure toute ton endurance.',
    instant: false,
    weight: 10,
  },
  champignon: {
    id: 'champignon',
    label: 'Champignon',
    icon: '🍄',
    desc: 'Effet aléatoire : régénère ta santé... ou te donne le tournis.',
    instant: false,
    weight: 9,
  },
  corde: {
    id: 'corde',
    label: 'Corde',
    icon: '🪢',
    desc: "Plante un point d'ancrage : tu réapparaîtras ici en cas de chute.",
    instant: false,
    weight: 6,
  },
  torche: {
    id: 'torche',
    label: 'Torche',
    icon: '🔦',
    desc: 'Éclaire les ravins sombres pendant 60 secondes.',
    instant: false,
    weight: 5,
  },
  grappin: {
    id: 'grappin',
    label: 'Grappin',
    icon: '🪝',
    desc: "Vise une corniche et propulse-toi vers elle.",
    instant: false,
    weight: 4,
  },
  fusee: {
    id: 'fusee',
    label: 'Fusée éclairante',
    icon: '🔴',
    desc: 'Signale ta position à ton équipe pendant 8 secondes.',
    instant: false,
    weight: 4,
  },
  sac: {
    id: 'sac',
    label: 'Sac renforcé',
    icon: '🎒',
    desc: 'Augmente ton endurance maximale, définitivement.',
    instant: true,
    weight: 1,
  },
};

export const ITEM_IDS = Object.keys(ITEM_DEFS) as ItemId[];

function glow(color: number): THREE.Sprite {
  const canvas = document.createElement('canvas');
  canvas.width = 64;
  canvas.height = 64;
  const ctx = canvas.getContext('2d')!;
  const grad = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  const c = new THREE.Color(color);
  grad.addColorStop(0, `rgba(${c.r * 255},${c.g * 255},${c.b * 255},0.55)`);
  grad.addColorStop(1, 'rgba(0,0,0,0)');
  ctx.fillStyle = grad;
  ctx.fillRect(0, 0, 64, 64);
  const tex = new THREE.CanvasTexture(canvas);
  const sprite = new THREE.Sprite(new THREE.SpriteMaterial({ map: tex, transparent: true, depthWrite: false, fog: false }));
  sprite.scale.set(1.4, 1.4, 1);
  return sprite;
}

export function buildItemMesh(id: ItemId): THREE.Object3D {
  const g = new THREE.Group();
  switch (id) {
    case 'gourde': {
      const body = new THREE.Mesh(
        new THREE.CylinderGeometry(0.11, 0.13, 0.32, 10),
        new THREE.MeshStandardMaterial({ color: '#4a7ca8', metalness: 0.3, roughness: 0.5 }),
      );
      const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.08, 8), new THREE.MeshStandardMaterial({ color: '#2b2b2b' }));
      cap.position.y = 0.2;
      g.add(body, cap, glow(0x6db3ff));
      break;
    }
    case 'champignon': {
      const cap = new THREE.Mesh(
        new THREE.SphereGeometry(0.16, 10, 8, 0, Math.PI * 2, 0, Math.PI / 2),
        new THREE.MeshStandardMaterial({ color: '#c1442e', roughness: 0.7 }),
      );
      cap.position.y = 0.14;
      const stem = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.08, 0.2, 8), new THREE.MeshStandardMaterial({ color: '#f2e6c9' }));
      g.add(cap, stem, glow(0xff8a6a));
      break;
    }
    case 'corde': {
      const t1 = new THREE.Mesh(new THREE.TorusGeometry(0.15, 0.045, 8, 16), new THREE.MeshStandardMaterial({ color: '#c9a15a' }));
      const t2 = new THREE.Mesh(new THREE.TorusGeometry(0.15, 0.045, 8, 16), new THREE.MeshStandardMaterial({ color: '#c9a15a' }));
      t1.rotation.x = Math.PI / 2;
      t2.rotation.x = Math.PI / 2;
      t2.position.y = 0.09;
      g.add(t1, t2, glow(0xd9b877));
      break;
    }
    case 'torche': {
      const handle = new THREE.Mesh(new THREE.CylinderGeometry(0.04, 0.05, 0.4, 8), new THREE.MeshStandardMaterial({ color: '#5b4230' }));
      const flame = new THREE.Mesh(new THREE.ConeGeometry(0.08, 0.18, 8), new THREE.MeshBasicMaterial({ color: '#ffb347' }));
      flame.position.y = 0.28;
      g.add(handle, flame, glow(0xffb347));
      break;
    }
    case 'grappin': {
      const base = new THREE.Mesh(new THREE.SphereGeometry(0.07, 8, 8), new THREE.MeshStandardMaterial({ color: '#8a8f96', metalness: 0.6, roughness: 0.3 }));
      g.add(base);
      for (let i = 0; i < 3; i++) {
        const hook = new THREE.Mesh(new THREE.ConeGeometry(0.04, 0.2, 6), new THREE.MeshStandardMaterial({ color: '#8a8f96', metalness: 0.6, roughness: 0.3 }));
        hook.position.set(Math.cos((i / 3) * Math.PI * 2) * 0.08, -0.1, Math.sin((i / 3) * Math.PI * 2) * 0.08);
        hook.rotation.x = Math.PI;
        g.add(hook);
      }
      g.add(glow(0xbfd0e0));
      break;
    }
    case 'fusee': {
      const body = new THREE.Mesh(new THREE.CylinderGeometry(0.05, 0.05, 0.34, 8), new THREE.MeshStandardMaterial({ color: '#c23b3b' }));
      const tip = new THREE.Mesh(new THREE.SphereGeometry(0.055, 8, 8), new THREE.MeshBasicMaterial({ color: '#ffe27a' }));
      tip.position.y = 0.19;
      g.add(body, tip, glow(0xff5a3c));
      break;
    }
    case 'sac': {
      const box = new THREE.Mesh(new THREE.BoxGeometry(0.3, 0.34, 0.18), new THREE.MeshStandardMaterial({ color: '#d9a441', roughness: 0.7 }));
      g.add(box, glow(0xffd27f));
      break;
    }
  }
  g.traverse((o: THREE.Object3D) => {
    if (o instanceof THREE.Mesh) o.castShadow = true;
  });
  return g;
}
