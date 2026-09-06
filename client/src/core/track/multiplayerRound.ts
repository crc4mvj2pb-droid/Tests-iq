import Matter from 'matter-js';
import type { GenContext, Vec2 } from '@shared/trackTypes';
import { mulberry32 } from '@shared/rng';
import { arc, createWaveField, rollingHill } from './builders';
import { generateChunk } from './segments';
import { ActiveTrack, buildStartPad } from './trackBuilder';
import { CAT } from '../physics/categories';
import { METER_PX } from '../game/GameEngine';

const { Bodies, Composite } = Matter;

const EASY_FEATURES = ['ramp_small', 'gap_combo_small', 'small_bump', 'roller'];
const MEDIUM_FEATURES = ['ramp_medium', 'gap_combo_medium', 'roller', 'tunnel'];
const HARD_FEATURES = ['gap_combo_large', 'loop', 'flip_gap_single', 'tunnel_narrow'];

/** Builds a short, smoothly rolling race track shared by every client in a
 * Private or Public round via a common numeric seed — flowing hills with a
 * handful of distinct features, checkpointed every couple of features. */
export function buildMultiplayerRound(world: Matter.World, seed: number, targetDistanceM: number) {
  const track = new ActiveTrack(world);
  track.addChunk(buildStartPad());
  const rng = mulberry32(seed);
  const wave = createWaveField(rng);
  let cursor: Vec2 = { x: 0, y: 0 };
  let angle = 0;
  const targetX = targetDistanceM * METER_PX;

  // Guaranteed flat runway right after spawn.
  const runway = generateChunk('flat_recovery', { start: cursor, angle, rng, difficulty: 0 });
  track.addChunk(runway);
  cursor = runway.endPoint;
  angle = runway.endAngle;
  wave.globalDist += 220;

  let featureCount = 0;
  let distSinceFeature = 0;
  let nextFeatureAt = 380 + rng() * 260;

  while (cursor.x < targetX) {
    const progress = cursor.x / targetX;
    const difficulty = 0.6 + progress * 0.9;

    if (distSinceFeature >= nextFeatureAt) {
      // Level out to near-flat before the feature: features are calibrated
      // for a flat entry, and their own angleDelta stacking on top of
      // whatever the rolling terrain was doing can otherwise compound into
      // a slope too steep to climb (an effective wall).
      if (Math.abs(angle) >= 0.08) {
        const level = arc(cursor, angle, 120, -angle, 10);
        track.addChunk({ strips: [level.points], endPoint: level.end, endAngle: level.endAngle, tag: 'level_out' });
        cursor = level.end;
        angle = level.endAngle;
        wave.globalDist += 120;
      }

      const pool = progress < 0.35 ? EASY_FEATURES : progress < 0.7 ? MEDIUM_FEATURES : HARD_FEATURES;
      const id = pool[Math.floor(rng() * pool.length)];
      const ctx: GenContext = { start: cursor, angle, rng, difficulty: progress };
      const chunk = generateChunk(id, ctx);
      featureCount++;
      track.addChunk({ ...chunk, checkpoint: featureCount % 2 === 0 });
      cursor = chunk.endPoint;
      angle = chunk.endAngle;

      const recovery = rollingHill(cursor, angle, wave, 130 + rng() * 90, difficulty * 0.5);
      track.addChunk({ strips: [recovery.points], endPoint: recovery.end, endAngle: recovery.endAngle, tag: 'rolling_hill' });
      cursor = recovery.end;
      angle = recovery.endAngle;

      distSinceFeature = 0;
      nextFeatureAt = 380 + rng() * 300;
      continue;
    }

    const hillLen = Math.min(240 + rng() * 220, targetX - cursor.x + 50);
    const res = rollingHill(cursor, angle, wave, hillLen, difficulty);
    track.addChunk({ strips: [res.points], endPoint: res.end, endAngle: res.endAngle, tag: 'rolling_hill' });
    cursor = res.end;
    angle = res.endAngle;
    distSinceFeature += hillLen;
  }

  const finishBody = Bodies.circle(cursor.x, cursor.y - 40, 50, {
    isStatic: true,
    isSensor: true,
    label: 'finish',
    collisionFilter: { category: CAT.CHECKPOINT, mask: CAT.CHASSIS },
  });
  Composite.add(world, finishBody);

  return { track, finishBody, finishPoint: cursor, start: track.startPoint };
}
