import { SaveManager } from '../state/SaveManager';
import { XP_REWARDS } from '../state/Progression';

export interface Challenge {
  id: string;
  icon: string;
  label: string;
  target: number;
  xp: number;
  progress: (data: typeof SaveManager.data) => number;
}

export const CHALLENGES: Challenge[] = [
  { id: 'races10', icon: '🏁', label: 'Terminer 10 courses', target: 10, xp: XP_REWARDS.challengeSmall, progress: (d) => d.totals.races },
  { id: 'flips50', icon: '🔄', label: 'Faire 50 flips', target: 50, xp: XP_REWARDS.challengeSmall, progress: (d) => d.totals.flips },
  { id: 'stars30', icon: '⭐', label: 'Obtenir 30 étoiles', target: 30, xp: XP_REWARDS.challengeMedium, progress: (d) => SaveManager.totalStars() },
  { id: 'wins3', icon: '🏆', label: 'Gagner 3 courses', target: 3, xp: XP_REWARDS.challengeMedium, progress: (d) => d.totals.victories },
  { id: 'cars5', icon: '🚗', label: 'Débloquer 5 voitures', target: 5, xp: XP_REWARDS.challengeMedium, progress: (d) => d.unlockedCars.length },
  { id: 'distance10k', icon: '♾️', label: 'Parcourir 10 000 m en Classic', target: 10000, xp: XP_REWARDS.challengeLarge, progress: (d) => d.totals.distanceM },
  { id: 'combo10', icon: '🔥', label: 'Faire un combo x10', target: 10, xp: XP_REWARDS.challengeLarge, progress: (d) => d.classicBest.bestCombo },
];

export function getChallengeState(c: Challenge) {
  const progress = Math.min(c.target, c.progress(SaveManager.data));
  const completed = progress >= c.target;
  return { progress, completed, ratio: progress / c.target };
}
