import Matter from 'matter-js';
import type { CarRig } from '../physics/car';
import type { CarProfile } from '../../data/cars';
import type { EnvironmentTheme } from '../../data/environments';
import type { Camera } from '../game/Camera';
import type { ParticleSystem } from './Particles';
import type { ActiveTrack, RenderStrip } from '../track/trackBuilder';

export interface GhostCar {
  x: number; y: number; angle: number; color: string; name: string;
}

function drawBodyPoly(ctx: CanvasRenderingContext2D, body: Matter.Body, fill: string, stroke?: string) {
  const verts = body.vertices;
  ctx.beginPath();
  ctx.moveTo(verts[0].x, verts[0].y);
  for (let i = 1; i < verts.length; i++) ctx.lineTo(verts[i].x, verts[i].y);
  ctx.closePath();
  ctx.fillStyle = fill;
  ctx.fill();
  if (stroke) {
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 2;
    ctx.stroke();
  }
}

export class Renderer {
  private wheelSpin = { back: 0, front: 0 };

  drawBackground(ctx: CanvasRenderingContext2D, width: number, height: number, camX: number, env: EnvironmentTheme) {
    const grad = ctx.createLinearGradient(0, 0, 0, height);
    grad.addColorStop(0, env.sky[0]);
    grad.addColorStop(1, env.sky[1]);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, width, height);

    ctx.save();
    ctx.globalAlpha = 0.35;
    ctx.fillStyle = env.accent;
    for (let i = 0; i < 6; i++) {
      const px = (((i * 340 - camX * 0.25) % (width + 400)) + width + 400) % (width + 400) - 200;
      ctx.beginPath();
      ctx.arc(px, height * 0.3 + (i % 3) * 40, 60 - (i % 3) * 10, 0, Math.PI * 2);
      ctx.fill();
    }
    ctx.restore();
  }

  drawWorld(
    ctx: CanvasRenderingContext2D,
    world: Matter.World,
    track: ActiveTrack,
    env: EnvironmentTheme,
  ) {
    // Ground/ceiling render as one continuous smooth landscape (from the
    // original pre-thickened polylines) rather than a strip of individually
    // outlined physics quads — no visible seams, reads as real terrain.
    this.drawTerrainStrips(ctx, track.renderStrips, env, 1);
    this.drawTerrainStrips(ctx, track.renderCeilings, env, -1);

    const bodies = Matter.Composite.allBodies(world);
    for (const b of bodies) {
      if (b.label === 'loop') {
        drawBodyPoly(ctx, b, env.ground, env.groundEdge);
      } else if (b.label === 'platform') {
        drawBodyPoly(ctx, b, env.accent, '#ffffff55');
      } else if (b.label === 'hazard') {
        drawBodyPoly(ctx, b, '#ff3b3b', '#ffb3b3');
      }
    }
  }

  private drawTerrainStrips(ctx: CanvasRenderingContext2D, strips: RenderStrip[], env: EnvironmentTheme, side: 1 | -1) {
    const depth = 700 * side;
    for (const strip of strips) {
      const points = strip.points;
      if (points.length < 2) continue;
      const first = points[0];
      const last = points[points.length - 1];

      ctx.beginPath();
      ctx.moveTo(first.x, first.y);
      for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
      ctx.lineTo(last.x, last.y + depth);
      ctx.lineTo(first.x, first.y + depth);
      ctx.closePath();
      const grad = ctx.createLinearGradient(0, first.y, 0, first.y + depth);
      grad.addColorStop(0, env.ground);
      grad.addColorStop(1, env.fog);
      ctx.fillStyle = grad;
      ctx.fill();

      ctx.beginPath();
      ctx.moveTo(first.x, first.y);
      for (let i = 1; i < points.length; i++) ctx.lineTo(points[i].x, points[i].y);
      ctx.strokeStyle = env.groundEdge;
      ctx.lineWidth = 4;
      ctx.lineJoin = 'round';
      ctx.shadowColor = env.groundEdge;
      ctx.shadowBlur = 8;
      ctx.stroke();
      ctx.shadowBlur = 0;
    }
  }

  drawCheckpoints(ctx: CanvasRenderingContext2D, points: { x: number; y: number }[], passed: number, color: string) {
    points.forEach((p, i) => {
      ctx.save();
      ctx.translate(p.x, p.y);
      ctx.strokeStyle = i <= passed ? '#4fffb0' : color;
      ctx.lineWidth = 6;
      ctx.globalAlpha = 0.85;
      ctx.beginPath();
      ctx.moveTo(0, -70);
      ctx.lineTo(0, 70);
      ctx.stroke();
      ctx.restore();
    });
  }

  drawFinish(ctx: CanvasRenderingContext2D, x: number, y: number) {
    ctx.save();
    ctx.translate(x, y);
    for (let i = 0; i < 8; i++) {
      ctx.fillStyle = i % 2 === 0 ? '#ffffff' : '#111111';
      ctx.fillRect(-8, -100 + i * 14, 16, 14);
    }
    ctx.restore();
  }

  drawCar(ctx: CanvasRenderingContext2D, rig: CarRig, profile: CarProfile) {
    this.wheelSpin.back = rig.wheelBack.angle;
    this.wheelSpin.front = rig.wheelFront.angle;
    this.drawWheel(ctx, rig.wheelFront.position.x, rig.wheelFront.position.y, profile.wheelRadius, this.wheelSpin.front, profile);
    this.drawWheel(ctx, rig.wheelBack.position.x, rig.wheelBack.position.y, profile.wheelRadius, this.wheelSpin.back, profile);

    ctx.save();
    ctx.translate(rig.chassis.position.x, rig.chassis.position.y);
    ctx.rotate(rig.chassis.angle);
    const w = profile.chassisWidth;
    const h = profile.chassisHeight;
    const grad = ctx.createLinearGradient(0, -h / 2, 0, h / 2);
    grad.addColorStop(0, profile.colorPrimary);
    grad.addColorStop(1, profile.colorSecondary);
    ctx.fillStyle = grad;
    ctx.beginPath();
    ctx.moveTo(-w / 2, h / 2);
    ctx.lineTo(-w / 2 + 8, -h / 2);
    ctx.lineTo(w / 2 - 18, -h / 2);
    ctx.lineTo(w / 2 + 6, h / 4);
    ctx.lineTo(w / 2, h / 2);
    ctx.closePath();
    ctx.fill();
    ctx.strokeStyle = profile.glow;
    ctx.lineWidth = 2.5;
    ctx.stroke();

    ctx.fillStyle = 'rgba(255,255,255,0.55)';
    ctx.beginPath();
    ctx.moveTo(w * 0.02, -h / 2 + 2);
    ctx.lineTo(w * 0.3, -h / 2 + 2);
    ctx.lineTo(w * 0.18, h * 0.05);
    ctx.lineTo(w * -0.05, h * 0.05);
    ctx.closePath();
    ctx.fill();

    if (rig.throttleHeld) {
      ctx.fillStyle = profile.glow;
      ctx.globalAlpha = 0.8;
      ctx.beginPath();
      ctx.ellipse(-w / 2 - 6, h * 0.3, 10 + Math.random() * 6, 5, 0, 0, Math.PI * 2);
      ctx.fill();
      ctx.globalAlpha = 1;
    }
    ctx.restore();
  }

  private drawWheel(ctx: CanvasRenderingContext2D, x: number, y: number, r: number, spin: number, profile: CarProfile) {
    ctx.save();
    ctx.translate(x, y);
    ctx.rotate(spin);
    ctx.fillStyle = '#161616';
    ctx.beginPath();
    ctx.arc(0, 0, r, 0, Math.PI * 2);
    ctx.fill();
    ctx.strokeStyle = profile.glow;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(0, 0, r * 0.55, 0, Math.PI * 2);
    ctx.stroke();
    for (let i = 0; i < 4; i++) {
      const a = (i / 4) * Math.PI * 2;
      ctx.beginPath();
      ctx.moveTo(0, 0);
      ctx.lineTo(Math.cos(a) * r * 0.55, Math.sin(a) * r * 0.55);
      ctx.strokeStyle = '#555';
      ctx.lineWidth = 3;
      ctx.stroke();
    }
    ctx.restore();
  }

  drawGhost(ctx: CanvasRenderingContext2D, ghost: GhostCar) {
    ctx.save();
    ctx.globalAlpha = 0.55;
    ctx.translate(ghost.x, ghost.y);
    ctx.rotate(ghost.angle);
    ctx.fillStyle = ghost.color;
    ctx.beginPath();
    ctx.moveTo(-40, 15);
    ctx.lineTo(-34, -15);
    ctx.lineTo(28, -15);
    ctx.lineTo(40, 15);
    ctx.closePath();
    ctx.fill();
    ctx.restore();
    ctx.save();
    ctx.globalAlpha = 0.8;
    ctx.fillStyle = '#fff';
    ctx.font = '12px system-ui';
    ctx.textAlign = 'center';
    ctx.fillText(ghost.name, ghost.x, ghost.y - 30);
    ctx.restore();
  }

  drawParticles(ctx: CanvasRenderingContext2D, particles: ParticleSystem) {
    particles.draw(ctx);
  }
}
