import { CARS, type UnlockCondition } from './cars';
import { SaveManager } from '../state/SaveManager';

function isMet(cond: UnlockCondition): boolean {
  const d = SaveManager.data;
  switch (cond.type) {
    case 'default':
      return true;
    case 'privateWin':
      return d.totals.privateWins >= 1;
    case 'privateWins':
      return d.totals.privateWins >= cond.count;
    case 'flipsTotal':
      return d.totals.flips >= cond.count;
    case 'distanceTotal':
      return d.totals.distanceM >= cond.meters;
    case 'classicBestDistance':
      return d.classicBest.distanceM >= cond.meters;
    case 'classicScore':
      return d.classicBest.score >= cond.score;
    case 'comboAchieved':
      return d.classicBest.bestCombo >= cond.count;
    default:
      return false;
  }
}

export function describeUnlock(cond: UnlockCondition): string {
  switch (cond.type) {
    case 'default': return 'Débloquée par défaut';
    case 'privateWin': return 'Gagner une partie Private';
    case 'privateWins': return `Gagner ${cond.count} parties Private`;
    case 'flipsTotal': return `Faire ${cond.count} flips au total`;
    case 'distanceTotal': return `Parcourir ${cond.meters.toLocaleString('fr-FR')} m au total`;
    case 'classicBestDistance': return `Atteindre ${cond.meters.toLocaleString('fr-FR')} m en une course`;
    case 'classicScore': return `Obtenir un score de ${cond.score.toLocaleString('fr-FR')}`;
    case 'comboAchieved': return `Réaliser un combo x${cond.count}`;
    default: return '';
  }
}

/** Call after any stat-changing event. Returns newly unlocked car ids. */
export function checkUnlocks(): string[] {
  const newly: string[] = [];
  for (const car of CARS) {
    if (SaveManager.data.unlockedCars.includes(car.id)) continue;
    if (isMet(car.unlock)) {
      SaveManager.unlockCar(car.id);
      newly.push(car.id);
    }
  }
  return newly;
}
