import Matter from 'matter-js';
import type { LevelDefinition, Vec2, GenContext } from '@shared/trackTypes';
import { mulberry32 } from '@shared/rng';
import { generateChunk } from './segments';
import { ActiveTrack, buildStartPad } from './trackBuilder';
import { CAT } from '../physics/categories';

const { Bodies, Composite } = Matter;

export interface LoadedLevel {
  track: ActiveTrack;
  finishBody: Matter.Body;
  finishPoint: Vec2;
  start: Vec2;
  startAngle: number;
}

export function loadLevel(world: Matter.World, level: LevelDefinition): LoadedLevel {
  const track = new ActiveTrack(world);
  track.addChunk(buildStartPad());
  const rng = mulberry32(1000 + level.id);
  let cursor: Vec2 = { x: 0, y: 0 };
  let angle = 0;

  level.pattern.forEach((id, i) => {
    const ctx: GenContext = { start: cursor, angle, rng, difficulty: i / level.pattern.length };
    const chunk = generateChunk(id, ctx);
    const withCheckpoint = i > 0 && i % 3 === 0;
    track.addChunk({ ...chunk, checkpoint: withCheckpoint });
    cursor = chunk.endPoint;
    angle = chunk.endAngle;
  });

  const finishBody = Bodies.circle(cursor.x, cursor.y - 40, 50, {
    isStatic: true,
    isSensor: true,
    label: 'finish',
    collisionFilter: { category: CAT.CHECKPOINT, mask: CAT.CHASSIS },
  });
  Composite.add(world, finishBody);

  return { track, finishBody, finishPoint: cursor, start: track.startPoint, startAngle: 0 };
}
