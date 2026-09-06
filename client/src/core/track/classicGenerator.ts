import type { GenContext, Vec2 } from '@shared/trackTypes';
import { mulberry32 } from '@shared/rng';
import { generateChunk } from './segments';
import type { ActiveTrack } from './trackBuilder';

interface Band {
  maxDistance: number;
  difficulty: number;
  patterns: string[][];
}

const PATTERN_FLIP = ['ramp_large', 'gap_large', 'platform_narrow'];
const PATTERN_SPEED = ['long_descent', 'speed_straight', 'gros_tremplin', 'gap_huge'];
const PATTERN_TECHNIQUE = ['platform_narrow', 'ramp_small', 'wall_vertical', 'platform_wide'];
const PATTERN_CHAOS = ['obstacle_chaos', 'ramp_small', 'platform_moving_h', 'gap_medium'];
const PATTERN_EXPERT = ['ramp_large', 'flip_gap_double', 'platform_narrow', 'fast_descent', 'loop'];
const PATTERN_EASY_A = ['ramp_small', 'gap_small', 'platform_wide'];
const PATTERN_EASY_B = ['long_climb', 'long_descent'];
const PATTERN_EASY_C = ['small_bump', 'flat_recovery'];
const PATTERN_LOOP_INTRO = ['ramp_medium', 'demi_loop', 'flat_recovery'];
const PATTERN_TUNNEL_RUN = ['tunnel', 'gap_medium', 'tunnel_narrow'];

const BANDS: Band[] = [
  { maxDistance: 500, difficulty: 0.12, patterns: [PATTERN_EASY_A, PATTERN_EASY_B, PATTERN_EASY_C] },
  { maxDistance: 1000, difficulty: 0.32, patterns: [PATTERN_EASY_A, PATTERN_TECHNIQUE, PATTERN_LOOP_INTRO, PATTERN_TUNNEL_RUN] },
  { maxDistance: 2000, difficulty: 0.55, patterns: [PATTERN_FLIP, PATTERN_TECHNIQUE, PATTERN_SPEED, PATTERN_TUNNEL_RUN, PATTERN_CHAOS] },
  { maxDistance: 3000, difficulty: 0.8, patterns: [PATTERN_FLIP, PATTERN_SPEED, PATTERN_CHAOS, PATTERN_EXPERT] },
  { maxDistance: Infinity, difficulty: 1.0, patterns: [PATTERN_EXPERT, PATTERN_CHAOS, PATTERN_SPEED, PATTERN_FLIP] },
];

function pickBand(distance: number): Band {
  return BANDS.find((b) => distance < b.maxDistance) ?? BANDS[BANDS.length - 1];
}

export class ClassicTrackGenerator {
  private rng: () => number;
  private cursor: Vec2;
  private angle = 0;
  private track: ActiveTrack;
  private patternsSincePause = 0;
  frontierX: number;

  constructor(track: ActiveTrack, seed: number, start: Vec2) {
    this.rng = mulberry32(seed);
    this.cursor = start;
    this.angle = 0;
    this.track = track;
    this.frontierX = start.x;
    // Guaranteed flat runway right after spawn, so the player is never
    // dropped in front of a gap/loop with zero reaction time.
    this.emit('flat_recovery');
  }

  private emit(id: string) {
    const ctx: GenContext = { start: this.cursor, angle: this.angle, rng: this.rng, difficulty: 0 };
    const chunk = generateChunk(id, ctx);
    this.track.addChunk(chunk);
    this.cursor = chunk.endPoint;
    this.angle = chunk.endAngle;
    this.frontierX = Math.max(this.frontierX, this.cursor.x);
    // Keep the car flyable: never let accumulated pitch wander too far from level.
    if (Math.abs(this.angle) > 0.9) this.angle *= 0.5;
  }

  /** Generates full patterns until the track frontier passes `targetX`. */
  generateAhead(targetX: number) {
    let guard = 0;
    while (this.frontierX < targetX && guard < 500) {
      guard++;
      const distance = Math.max(0, this.cursor.x - 0);
      const band = pickBand(distance);
      this.patternsSincePause++;
      if (this.patternsSincePause >= 3) {
        this.emit('flat_recovery');
        this.patternsSincePause = 0;
        continue;
      }
      const pattern = band.patterns[Math.floor(this.rng() * band.patterns.length)];
      for (const id of pattern) this.emit(id);
    }
  }
}
