/** Must match the total duration of RaceSession's on-screen 3-2-1-GO
 * countdown (client/src/core/game/GameEngine.ts) so the server's
 * authoritative round-start clock lines up with when clients actually
 * enable control. */
export const COUNTDOWN_MS = 2300;

export const PRIVATE_LEAD_MS = 350;

export const ROUND_TARGET_DISTANCE_M = 900;

export const MAX_ROUND_DURATION_MS = 100_000;

export const ENVIRONMENTS = ['neon_city', 'desert', 'industrial', 'sky', 'volcano', 'arctic'];

export function roundPoints(place: number): number {
  const table = [10, 8, 6, 5, 4, 3, 2, 1];
  return table[place - 1] ?? 0;
}
