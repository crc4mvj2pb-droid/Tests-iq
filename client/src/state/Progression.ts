export function xpForLevel(level: number): number {
  return Math.round(120 * level * (1 + level * 0.12));
}

export function levelFromXp(xp: number): { level: number; xpIntoLevel: number; xpForNext: number } {
  let level = 1;
  let remaining = xp;
  while (remaining >= xpForLevel(level)) {
    remaining -= xpForLevel(level);
    level++;
  }
  return { level, xpIntoLevel: remaining, xpForNext: xpForLevel(level) };
}

export const XP_REWARDS = {
  privateRoundWin: 100,
  privateMatchWin: 250,
  classicPer1000m: 40,
};
