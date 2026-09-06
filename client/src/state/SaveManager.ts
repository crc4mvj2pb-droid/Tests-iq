export interface ClassicBest {
  score: number;
  distanceM: number;
  flips: number;
  bestCombo: number;
}

export interface SaveData {
  version: 3;
  xp: number;
  unlockedCars: string[];
  selectedCar: string;
  classicBest: ClassicBest;
  totals: {
    flips: number;
    distanceM: number;
    races: number;
    victories: number;
    crashes: number;
    privateWins: number;
  };
}

const KEY = 'fliprush_save_v3';

function defaultSave(): SaveData {
  return {
    version: 3,
    xp: 0,
    unlockedCars: ['balanced'],
    selectedCar: 'balanced',
    classicBest: { score: 0, distanceM: 0, flips: 0, bestCombo: 0 },
    totals: { flips: 0, distanceM: 0, races: 0, victories: 0, crashes: 0, privateWins: 0 },
  };
}

class SaveManagerImpl {
  data: SaveData;

  constructor() {
    this.data = this.load();
  }

  private load(): SaveData {
    try {
      const raw = localStorage.getItem(KEY);
      if (!raw) return defaultSave();
      const parsed = JSON.parse(raw);
      if (parsed.version !== 3) return defaultSave();
      return { ...defaultSave(), ...parsed };
    } catch {
      return defaultSave();
    }
  }

  save() {
    try {
      localStorage.setItem(KEY, JSON.stringify(this.data));
    } catch {
      /* storage unavailable (private browsing, quota) - progress just won't persist */
    }
  }

  recordClassicResult(result: ClassicBest) {
    const isRecord = result.score > this.data.classicBest.score;
    if (isRecord) this.data.classicBest = result;
    this.save();
    return isRecord;
  }

  addTotals(delta: Partial<SaveData['totals']>) {
    for (const k of Object.keys(delta) as (keyof SaveData['totals'])[]) {
      this.data.totals[k] += delta[k] ?? 0;
    }
    this.save();
  }

  unlockCar(id: string) {
    if (!this.data.unlockedCars.includes(id)) {
      this.data.unlockedCars.push(id);
      this.save();
      return true;
    }
    return false;
  }

  selectCar(id: string) {
    this.data.selectedCar = id;
    this.save();
  }

  addXp(amount: number) {
    this.data.xp += amount;
    this.save();
  }
}

export const SaveManager = new SaveManagerImpl();
