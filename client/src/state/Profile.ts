const KEY = 'talus.profile.v1';

export interface Profile {
  name: string;
  color: string;
}

const COLORS = ['#c0503f', '#3f7fc0', '#5a9e52', '#c0973f', '#8a5fc0', '#3fb7b0'];

function randomName(): string {
  const n = 1000 + Math.floor(Math.random() * 9000);
  return `Grimpeur${n}`;
}

export function loadProfile(): Profile {
  try {
    const raw = localStorage.getItem(KEY);
    if (raw) return JSON.parse(raw) as Profile;
  } catch {
    // ignore
  }
  const profile: Profile = { name: randomName(), color: COLORS[Math.floor(Math.random() * COLORS.length)] };
  saveProfile(profile);
  return profile;
}

export function saveProfile(profile: Profile) {
  try {
    localStorage.setItem(KEY, JSON.stringify(profile));
  } catch {
    // stockage indisponible (navigation privée...) — on continue sans persister
  }
}

export { COLORS };
