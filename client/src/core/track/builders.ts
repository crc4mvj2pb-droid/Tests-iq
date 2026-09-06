import type { Vec2 } from '@shared/trackTypes';

export interface ArcResult {
  points: Vec2[];
  end: Vec2;
  endAngle: number;
}

/** Sweeps forward `length` px, turning by `angleDelta` radians total, in
 * `segments` smooth steps. angleDelta > 0 = descending, < 0 = climbing
 * (y grows downward). This is the workhorse for ramps, hills and rollers. */
export function arc(start: Vec2, angle: number, length: number, angleDelta: number, segments = 8): ArcResult {
  const points: Vec2[] = [{ x: start.x, y: start.y }];
  let x = start.x;
  let y = start.y;
  let a = angle;
  const da = angleDelta / segments;
  const dl = length / segments;
  for (let i = 0; i < segments; i++) {
    a += da;
    x += Math.cos(a) * dl;
    y += Math.sin(a) * dl;
    points.push({ x, y });
  }
  return { points, end: { x, y }, endAngle: a };
}

/** Rolling wave terrain: alternates climb/descend to create bumps/rollers. */
export function wave(start: Vec2, angle: number, length: number, amplitudeAngle: number, cycles: number): ArcResult {
  const segmentsPerCycle = 8;
  let cursor: Vec2 = start;
  let a = angle;
  const points: Vec2[] = [{ x: start.x, y: start.y }];
  const lenPerHalf = length / (cycles * 2);
  for (let c = 0; c < cycles * 2; c++) {
    const delta = c % 2 === 0 ? -amplitudeAngle : amplitudeAngle;
    const res = arc(cursor, a, lenPerHalf, delta, segmentsPerCycle);
    points.push(...res.points.slice(1));
    cursor = res.end;
    a = res.endAngle;
  }
  return { points, end: cursor, endAngle: a };
}

export interface WaveField {
  ampA: number;
  wavelengthA: number;
  phaseA: number;
  ampB: number;
  wavelengthB: number;
  phaseB: number;
  globalDist: number;
}

/** A per-run randomized "landscape" of two overlaid sine waves (a big lazy
 * roll + a smaller ripple on top) — this is what makes every run's terrain
 * flow smoothly and never feel identical, like real rolling hills instead
 * of a stitched-together obstacle course. */
export function createWaveField(rng: () => number): WaveField {
  return {
    ampA: 0.16 + rng() * 0.14,
    wavelengthA: 650 + rng() * 500,
    phaseA: rng() * Math.PI * 2,
    ampB: 0.05 + rng() * 0.07,
    wavelengthB: 200 + rng() * 160,
    phaseB: rng() * Math.PI * 2,
    globalDist: 0,
  };
}

function waveAngleAt(wave: WaveField, dist: number, difficulty: number): number {
  const a = wave.ampA * difficulty * Math.sin((dist / wave.wavelengthA) * Math.PI * 2 + wave.phaseA);
  const b = wave.ampB * difficulty * Math.sin((dist / wave.wavelengthB) * Math.PI * 2 + wave.phaseB);
  return a + b;
}

/** Generates a smooth rolling-hill stretch of ground. Re-anchors to
 * `ctx.angle` at its own start (so it always joins seamlessly with
 * whatever came before — a feature obstacle, a checkpoint, spawn...) while
 * letting the underlying wave field keep evolving continuously across
 * calls, so the landscape never resets or repeats. */
export function rollingHill(start: Vec2, angle: number, wave: WaveField, length: number, difficulty: number): ArcResult {
  const steps = Math.max(6, Math.round(length / 26));
  const stepLen = length / steps;
  const baseField = waveAngleAt(wave, wave.globalDist, difficulty);
  const points: Vec2[] = [{ x: start.x, y: start.y }];
  let x = start.x;
  let y = start.y;
  let dist = wave.globalDist;
  let a = angle;
  for (let i = 0; i < steps; i++) {
    dist += stepLen;
    a = angle + (waveAngleAt(wave, dist, difficulty) - baseField);
    x += Math.cos(a) * stepLen;
    y += Math.sin(a) * stepLen;
    points.push({ x, y });
  }
  wave.globalDist += length;
  return { points, end: { x, y }, endAngle: a };
}

export function leftPerpVec(angle: number): Vec2 {
  const d = { x: Math.cos(angle), y: Math.sin(angle) };
  const len = Math.hypot(d.x, d.y) || 1;
  return { x: -d.y / len, y: d.x / len };
}

export function rightPerpVec(angle: number): Vec2 {
  const l = leftPerpVec(angle);
  return { x: -l.x, y: -l.y };
}

export interface LoopResult {
  polys: Vec2[][];
  end: Vec2;
  endAngle: number;
}

/** Builds a full or partial circular loop as pre-thickened ring segments.
 * The car enters at `start` moving at `angle`; the ring curves up and
 * around and rejoins the ground tangentially. */
export function buildLoop(start: Vec2, angle: number, radius: number, arcFraction: number, thickness = 46, segments = 28): LoopResult {
  const up = rightPerpVec(angle); // points away from ground, toward loop center
  const center = { x: start.x + up.x * radius, y: start.y + up.y * radius };
  const thetaEntry = Math.atan2(start.y - center.y, start.x - center.x);
  const tangentCCW = { x: -Math.sin(thetaEntry), y: Math.cos(thetaEntry) };
  const dir = { x: Math.cos(angle), y: Math.sin(angle) };
  const sweepSign = tangentCCW.x * dir.x + tangentCCW.y * dir.y >= 0 ? 1 : -1;

  const totalTheta = sweepSign * arcFraction * Math.PI * 2;
  const polys: Vec2[][] = [];
  let prevInner = start;
  let prevTheta = thetaEntry;
  for (let i = 1; i <= segments; i++) {
    const theta = thetaEntry + (totalTheta * i) / segments;
    const inner: Vec2 = { x: center.x + Math.cos(theta) * radius, y: center.y + Math.sin(theta) * radius };
    const outerA: Vec2 = {
      x: center.x + Math.cos(prevTheta) * (radius + thickness),
      y: center.y + Math.sin(prevTheta) * (radius + thickness),
    };
    const outerB: Vec2 = {
      x: center.x + Math.cos(theta) * (radius + thickness),
      y: center.y + Math.sin(theta) * (radius + thickness),
    };
    polys.push([prevInner, inner, outerB, outerA]);
    prevInner = inner;
    prevTheta = theta;
  }
  const finalTheta = thetaEntry + totalTheta;
  // Tangent direction at exit = derivative of circle position w.r.t. theta, times sweep sign.
  const tangent = { x: -Math.sin(finalTheta) * sweepSign, y: Math.cos(finalTheta) * sweepSign };
  const exitAngle = Math.atan2(tangent.y, tangent.x);
  return { polys, end: prevInner, endAngle: exitAngle };
}
