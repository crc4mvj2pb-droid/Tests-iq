import Matter from 'matter-js';
import type { GenContext, Vec2 } from '@shared/trackTypes';
import { mulberry32 } from '@shared/rng';
import { generateChunk } from './segments';
import { ActiveTrack, buildStartPad } from './trackBuilder';
import { CAT } from '../physics/categories';
import { METER_PX } from '../game/GameEngine';

const { Bodies, Composite } = Matter;

const EASY = ['ramp_small', 'gap_small', 'platform_wide', 'small_bump', 'flat_recovery', 'roller'];
const MEDIUM = ['ramp_medium', 'gap_medium', 'platform_narrow', 'tunnel', 'big_roller', 'ramp_large'];
const HARD = ['gap_large', 'wall_vertical', 'demi_loop', 'flip_gap_single', 'platform_moving_h', 'ramp_large'];

/** Builds a short procedurally-generated, checkpointed race track shared by
 * every client in a Private or Public round via a common numeric seed. */
export function buildMultiplayerRound(world: Matter.World, seed: number, targetDistanceM: number) {
  const track = new ActiveTrack(world);
  track.addChunk(buildStartPad());
  const rng = mulberry32(seed);
  let cursor: Vec2 = { x: 0, y: 0 };
  let angle = 0;
  const targetX = targetDistanceM * METER_PX;
  let obstacleIndex = 0;

  // Guaranteed flat runway right after spawn (see levelLoader/classicGenerator).
  const runway = generateChunk('flat_recovery', { start: cursor, angle, rng, difficulty: 0 });
  track.addChunk(runway);
  cursor = runway.endPoint;
  angle = runway.endAngle;

  while (cursor.x < targetX) {
    const progress = cursor.x / targetX;
    const pool = progress < 0.35 ? EASY : progress < 0.7 ? MEDIUM : HARD;
    const id = pool[Math.floor(rng() * pool.length)];
    const ctx: GenContext = { start: cursor, angle, rng, difficulty: progress };
    const chunk = generateChunk(id, ctx);
    obstacleIndex++;
    track.addChunk({ ...chunk, checkpoint: obstacleIndex % 3 === 0 });
    cursor = chunk.endPoint;
    angle = chunk.endAngle;
    if (Math.abs(angle) > 0.9) angle *= 0.5;
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
