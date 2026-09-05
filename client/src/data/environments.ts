export interface EnvironmentTheme {
  id: string;
  name: string;
  sky: [string, string];
  ground: string;
  groundEdge: string;
  accent: string;
  fog: string;
  particles: string;
}

export const ENVIRONMENTS: Record<string, EnvironmentTheme> = {
  neon_city: {
    id: 'neon_city', name: 'Neon City',
    sky: ['#0a0e2e', '#2a1258'], ground: '#151a3a', groundEdge: '#7c4fff', accent: '#4fd1ff', fog: '#1a1240', particles: '#ff4fd6',
  },
  desert: {
    id: 'desert', name: 'Desert',
    sky: ['#3a1f0d', '#c9722f'], ground: '#4a2c14', groundEdge: '#e8a95a', accent: '#ffce6b', fog: '#5a3a1a', particles: '#ffe0a3',
  },
  industrial: {
    id: 'industrial', name: 'Industrial',
    sky: ['#1a1a1f', '#3a3a45'], ground: '#26262d', groundEdge: '#ff8f3f', accent: '#c7c7d1', fog: '#2a2a33', particles: '#ffb84f',
  },
  sky: {
    id: 'sky', name: 'Sky Circuit',
    sky: ['#1c3a63', '#8fd3ff'], ground: '#2a4a6b', groundEdge: '#ffffff', accent: '#4fffe0', fog: '#3a5f85', particles: '#ffffff',
  },
  volcano: {
    id: 'volcano', name: 'Volcano',
    sky: ['#1a0505', '#5a1010'], ground: '#2a0a0a', groundEdge: '#ff4f2f', accent: '#ff9d4f', fog: '#3a0f0f', particles: '#ff6b3f',
  },
  arctic: {
    id: 'arctic', name: 'Arctic',
    sky: ['#0d2233', '#7fc7e8'], ground: '#1e3a4a', groundEdge: '#dff6ff', accent: '#8fe0ff', fog: '#2a4a5c', particles: '#ffffff',
  },
};

export function getEnvironment(id: string): EnvironmentTheme {
  return ENVIRONMENTS[id] ?? ENVIRONMENTS.neon_city;
}
