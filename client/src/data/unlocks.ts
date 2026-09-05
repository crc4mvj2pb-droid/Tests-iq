import { CARS, type UnlockCondition } from './cars';
import { SaveManager } from '../state/SaveManager';

function isMet(cond: UnlockCondition): boolean {
  const d = SaveManager.data;
  switch (cond.type) {
    case 'default':
      return true;
    case 'levelsCompleted':
      return SaveManager.levelsCompleted() >= cond.count;
    case 'starsTotal':
      return SaveManager.totalStars() >= cond.count;
    case 'privateWin':
      return d.totals.privateWins >= 1;
    case 'publicWin':
      return d.totals.publicWins >= 1;
    case 'flipsTotal':
      return d.totals.flips >= cond.count;
    case 'distanceTotal':
      return d.totals.distanceM >= cond.meters;
    case 'noDeathLevel':
      return Object.values(d.levelNoDeath).some(Boolean);
    case 'perfectStars':
      return SaveManager.perfectLevels() * 3 >= cond.count;
    default:
      return false;
  }
}

export function describeUnlock(cond: UnlockCondition): string {
  switch (cond.type) {
    case 'default': return 'Débloquée par défaut';
    case 'levelsCompleted': return `Terminer ${cond.count} niveaux`;
    case 'starsTotal': return `Obtenir ${cond.count} étoiles au total`;
    case 'privateWin': return 'Gagner une partie Private';
    case 'publicWin': return 'Gagner une partie Public';
    case 'flipsTotal': return `Faire ${cond.count} flips au total`;
    case 'distanceTotal': return `Parcourir ${cond.meters.toLocaleString('fr-FR')} m au total`;
    case 'noDeathLevel': return 'Terminer un niveau sans crash';
    case 'perfectStars': return `Obtenir ${cond.count} étoiles parfaites`;
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
