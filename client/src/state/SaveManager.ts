export interface ClassicBest {
  score: number;
  distanceM: number;
  flips: number;
  bestCombo: number;
}

export interface SaveData {
  version: 2;
  xp: number;
  levelStars: Record<number, 0 | 1 | 2 | 3>;
  levelBestTimeMs: Record<number, number>;
  levelNoDeath: Record<number, boolean>;
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
    publicWins: number;
  };
  challengeProgress: Record<string, number>;
  challengeCompleted: Record<string, boolean>;
}

const KEY = 'fliprush_save_v2';

function defaultSave(): SaveData {
  return {
    version: 2,
    xp: 0,
    levelStars: {},
    levelBestTimeMs: {},
    levelNoDeath: {},
    unlockedCars: ['balanced'],
    selectedCar: 'balanced',
    classicBest: { score: 0, distanceM: 0, flips: 0, bestCombo: 0 },
    totals: { flips: 0, distanceM: 0, races: 0, victories: 0, crashes: 0, privateWins: 0, publicWins: 0 },
    challengeProgress: {},
    challengeCompleted: {},
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
      if (parsed.version !== 2) return defaultSave();
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

  recordLevelResult(levelId: number, timeMs: number, stars: 0 | 1 | 2 | 3, noDeath: boolean) {
    const prevStars = this.data.levelStars[levelId] ?? 0;
    if (stars > prevStars) this.data.levelStars[levelId] = stars;
    const prevTime = this.data.levelBestTimeMs[levelId];
    if (!prevTime || timeMs < prevTime) this.data.levelBestTimeMs[levelId] = timeMs;
    if (noDeath) this.data.levelNoDeath[levelId] = true;
    this.save();
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

  totalStars(): number {
    return (Object.values(this.data.levelStars) as number[]).reduce((a, b) => a + b, 0);
  }

  levelsCompleted(): number {
    return Object.keys(this.data.levelStars).length;
  }

  perfectLevels(): number {
    return Object.values(this.data.levelStars).filter((s) => s === 3).length;
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
