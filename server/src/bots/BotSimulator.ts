export type BotTier = 'easy' | 'normal' | 'hard' | 'expert';

export const BOT_TIERS: BotTier[] = ['easy', 'normal', 'hard', 'expert'];

interface TierProfile {
  msPerMeter: number;
  variance: number; // +/- fraction of pace
  dnfChance: number;
}

const TIER_PROFILES: Record<BotTier, TierProfile> = {
  easy: { msPerMeter: 105, variance: 0.28, dnfChance: 0.3 },
  normal: { msPerMeter: 82, variance: 0.2, dnfChance: 0.18 },
  hard: { msPerMeter: 66, variance: 0.14, dnfChance: 0.1 },
  expert: { msPerMeter: 54, variance: 0.09, dnfChance: 0.05 },
};

export function randomTier(): BotTier {
  const r = Math.random();
  if (r < 0.3) return 'easy';
  if (r < 0.65) return 'normal';
  if (r < 0.9) return 'hard';
  return 'expert';
}

export interface BotRaceProfile {
  tier: BotTier;
  /** null = the bot crashes out and never finishes this round. */
  finishTimeMs: number | null;
  /** Fraction (0..1) of the track the bot reaches before crashing, if DNF. */
  dnfProgress: number;
  wobble: number;
}

/** Non-deterministic: every call (i.e. every race) produces a different
 * outcome for the same tier, so no bot ever runs the exact same race twice. */
export function simulateBotRace(tier: BotTier, targetDistanceM: number): BotRaceProfile {
  const profile = TIER_PROFILES[tier];
  const wobble = Math.random();
  if (Math.random() < profile.dnfChance) {
    return { tier, finishTimeMs: null, dnfProgress: 0.15 + Math.random() * 0.7, wobble };
  }
  const noise = 1 + (Math.random() * 2 - 1) * profile.variance;
  const finishTimeMs = Math.round(targetDistanceM * profile.msPerMeter * noise);
  return { tier, finishTimeMs, dnfProgress: 1, wobble };
}

/** Fraction of the track a bot has covered at a given elapsed time, used to
 * drive its ghost-car position for other players during the round. */
export function botProgressAt(bot: BotRaceProfile, elapsedMs: number): number {
  if (bot.finishTimeMs === null) {
    const capTime = 4000 + bot.dnfProgress * 12000;
    const t = Math.min(1, elapsedMs / capTime);
    return t * bot.dnfProgress;
  }
  const wobbleFactor = 1 + Math.sin(elapsedMs / 900 + bot.wobble * 10) * 0.03;
  return Math.min(1, (elapsedMs / bot.finishTimeMs) * wobbleFactor);
}
