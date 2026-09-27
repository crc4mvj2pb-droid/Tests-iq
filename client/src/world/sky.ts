import * as THREE from 'three';

export interface SkyRig {
  hemi: THREE.HemisphereLight;
  sun: THREE.DirectionalLight;
  dome: THREE.Mesh;
  updateShadowFocus(target: THREE.Vector3): void;
}

function buildSkyDome(): THREE.Mesh {
  const geo = new THREE.SphereGeometry(900, 24, 16);
  const pos = geo.attributes.position as THREE.BufferAttribute;
  const colors = new Float32Array(pos.count * 3);
  const top = new THREE.Color('#2c6fb5');
  const mid = new THREE.Color('#bcd9ec');
  const bottom = new THREE.Color('#f2ead9');
  const tmp = new THREE.Color();
  for (let i = 0; i < pos.count; i++) {
    const y = pos.getY(i) / 900;
    let c: THREE.Color;
    if (y > 0.05) {
      c = tmp.copy(mid).lerp(top, Math.min(1, y / 0.7));
    } else {
      c = tmp.copy(mid).lerp(bottom, Math.min(1, (0.05 - y) / 0.35));
    }
    colors[i * 3] = c.r;
    colors[i * 3 + 1] = c.g;
    colors[i * 3 + 2] = c.b;
  }
  geo.setAttribute('color', new THREE.BufferAttribute(colors, 3));
  const mat = new THREE.MeshBasicMaterial({ vertexColors: true, side: THREE.BackSide, fog: false, depthWrite: false });
  const mesh = new THREE.Mesh(geo, mat);
  mesh.renderOrder = -10;
  return mesh;
}

export function setupSky(scene: THREE.Scene): SkyRig {
  scene.fog = new THREE.Fog(0xcfe3ee, 60, 420);

  const hemi = new THREE.HemisphereLight(0xdfefff, 0x3a3226, 0.85);
  scene.add(hemi);

  const sun = new THREE.DirectionalLight(0xfff3d6, 2.1);
  sun.position.set(120, 180, 90);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1536, 1536);
  sun.shadow.camera.near = 10;
  sun.shadow.camera.far = 260;
  sun.shadow.bias = -0.0015;
  sun.target.position.set(0, 0, 0);
  scene.add(sun);
  scene.add(sun.target);

  const dome = buildSkyDome();
  scene.add(dome);

  const halfSize = 55;
  const shadowCam = sun.shadow.camera as THREE.OrthographicCamera;
  shadowCam.left = -halfSize;
  shadowCam.right = halfSize;
  shadowCam.top = halfSize;
  shadowCam.bottom = -halfSize;
  shadowCam.updateProjectionMatrix();

  const sunOffset = new THREE.Vector3(120, 180, 90);

  return {
    hemi,
    sun,
    dome,
    updateShadowFocus(target: THREE.Vector3) {
      sun.position.copy(target).add(sunOffset);
      sun.target.position.copy(target);
      sun.target.updateMatrixWorld();
    },
  };
}
