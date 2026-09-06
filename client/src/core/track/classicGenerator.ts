import type { GenContext, Vec2 } from '@shared/trackTypes';
import { mulberry32 } from '@shared/rng';
import { createWaveField, rollingHill, type WaveField } from './builders';
import { generateChunk } from './segments';
import type { ActiveTrack } from './trackBuilder';

interface FeatureBand {
  maxDistance: number;
  difficulty: number;
  features: string[];
}

// Curated, hand-picked obstacles used as distinct "moments" inserted into
// the rolling landscape — not the whole 59-entry catalog at once, so the
// track reads as flowing terrain with occasional highlights, like the
// reference game, rather than wall-to-wall obstacles.
const BANDS: FeatureBand[] = [
  { maxDistance: 600, difficulty: 0.6, features: ['ramp_small', 'gap_small', 'small_bump'] },
  { maxDistance: 1400, difficulty: 0.85, features: ['ramp_medium', 'gap_medium', 'demi_loop', 'roller'] },
  { maxDistance: 2400, difficulty: 1.1, features: ['ramp_large', 'gap_large', 'loop', 'tunnel', 'flip_gap_single'] },
  { maxDistance: 3600, difficulty: 1.35, features: ['gap_huge', 'loop', 'flip_gap_single', 'wall_vertical', 'platform_moving_h'] },
  { maxDistance: Infinity, difficulty: 1.6, features: ['flip_gap_double', 'loop_series', 'gap_huge', 'wall_inclined', 'tunnel_narrow'] },
];

function pickBand(distance: number): FeatureBand {
  return BANDS.find((b) => distance < b.maxDistance) ?? BANDS[BANDS.length - 1];
}

export class ClassicTrackGenerator {
  private rng: () => number;
  private cursor: Vec2;
  private angle = 0;
  private track: ActiveTrack;
  private wave: WaveField;
  private distSinceFeature = 0;
  private nextFeatureAt = 500;
  frontierX: number;

  constructor(track: ActiveTrack, seed: number, start: Vec2) {
    this.rng = mulberry32(seed);
    this.cursor = start;
    this.angle = 0;
    this.track = track;
    this.wave = createWaveField(this.rng);
    this.frontierX = start.x;
    // Guaranteed flat runway right after spawn, so the player is never
    // dropped in front of a gap/loop with zero reaction time.
    this.emitFlatRunway(220);
  }

  private emitFlatRunway(length: number) {
    const ctx: GenContext = { start: this.cursor, angle: this.angle, rng: this.rng, difficulty: 0 };
    const chunk = generateChunk('flat_recovery', ctx);
    this.track.addChunk(chunk);
    this.cursor = chunk.endPoint;
    this.angle = chunk.endAngle;
    this.frontierX = Math.max(this.frontierX, this.cursor.x);
    this.wave.globalDist += length;
  }

  private emitHill(length: number, difficulty: number) {
    const res = rollingHill(this.cursor, this.angle, this.wave, length, difficulty);
    this.track.addChunk({ strips: [res.points], endPoint: res.end, endAngle: res.endAngle, tag: 'rolling_hill' });
    this.cursor = res.end;
    this.angle = res.endAngle;
    this.frontierX = Math.max(this.frontierX, this.cursor.x);
  }

  private emitFeature(id: string) {
    const ctx: GenContext = { start: this.cursor, angle: this.angle, rng: this.rng, difficulty: 0 };
    const chunk = generateChunk(id, ctx);
    this.track.addChunk(chunk);
    this.cursor = chunk.endPoint;
    this.angle = chunk.endAngle;
    this.frontierX = Math.max(this.frontierX, this.cursor.x);
    // Keep the car flyable: never let accumulated pitch wander too far from level.
    if (Math.abs(this.angle) > 0.8) this.angle *= 0.4;
  }

  /** Generates smooth rolling terrain, sprinkled with distinct features,
   * until the track frontier passes `targetX`. */
  generateAhead(targetX: number) {
    let guard = 0;
    while (this.frontierX < targetX && guard < 800) {
      guard++;
      const distance = Math.max(0, this.cursor.x);
      const band = pickBand(distance);

      if (this.distSinceFeature >= this.nextFeatureAt) {
        const feature = band.features[Math.floor(this.rng() * band.features.length)];
        this.emitFeature(feature);
        this.emitHill(140 + this.rng() * 100, band.difficulty * 0.5); // short recovery roll after a feature
        this.distSinceFeature = 0;
        this.nextFeatureAt = 420 + this.rng() * 380;
        continue;
      }

      const hillLen = 260 + this.rng() * 260;
      this.emitHill(hillLen, band.difficulty);
      this.distSinceFeature += hillLen;
    }
  }
}
