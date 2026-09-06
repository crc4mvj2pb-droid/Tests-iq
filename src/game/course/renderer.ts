import type { CircuitDef } from "./circuits";
import { isWaterSegAt, GROUND_Y0 } from "./circuits";
import type { CourseSnapshot, PlayerMeta } from "../../net/protocol";
import { PLAYER_H } from "./sim";

const GROUND_DEPTH = 1400;
// The ground line always lands at this fraction of the canvas height,
// regardless of viewport size — a fixed pixel offset (the old approach)
// looked fine in a tall test window but pushed the ground clean off the
// bottom of a real phone's short landscape viewport.
const GROUND_SCREEN_FRAC = 0.78;

export class CourseRenderer {
  private camX = 0;
  private camInit = false;

  draw(
    ctx: CanvasRenderingContext2D,
    w: number,
    h: number,
    circuit: CircuitDef,
    snapshot: CourseSnapshot,
    localId: string,
    metas: Map<string, PlayerMeta>
  ) {
    const local = snapshot.entities.find((e) => e.id === localId) ?? snapshot.entities[0];
    const targetX = local ? local.x : circuit.startX;
    if (!this.camInit) {
      this.camX = targetX;
      this.camInit = true;
    } else {
      this.camX += (targetX - this.camX) * 0.15;
    }

    // sky
    const sky = ctx.createLinearGradient(0, 0, 0, h);
    sky.addColorStop(0, circuit.theme.sky);
    sky.addColorStop(1, circuit.theme.sky2);
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, w, h);

    // The vertical camera position is completely fixed to the circuit's
    // ground baseline — it never tracks the player, so jumps, ramps and the
    // zipline never scroll the view. Only horizontal scroll follows. The
    // ground line is anchored to a fraction of the canvas height (not a
    // fixed pixel offset) so it stays on-screen on any viewport size.
    const vOffset = h * GROUND_SCREEN_FRAC - GROUND_Y0;
    ctx.save();
    ctx.translate(w / 2 - this.camX, vOffset);

    // parallax hills
    ctx.fillStyle = "rgba(0,0,0,0.08)";
    for (let i = -2; i < 12; i++) {
      const bx = i * 400 - ((this.camX * 0.4) % 400);
      ctx.beginPath();
      ctx.ellipse(bx, circuit.startY - 40, 220, 120, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    // ground
    for (const seg of circuit.ground) {
      ctx.fillStyle = seg.water ? "#2a6f8f" : circuit.theme.ground;
      ctx.beginPath();
      ctx.moveTo(seg.x0, seg.y0);
      ctx.lineTo(seg.x1, seg.y1);
      ctx.lineTo(seg.x1, seg.y1 + GROUND_DEPTH);
      ctx.lineTo(seg.x0, seg.y0 + GROUND_DEPTH);
      ctx.closePath();
      ctx.fill();
    }
    ctx.lineWidth = 4;
    for (const seg of circuit.ground) {
      ctx.strokeStyle = seg.water ? "rgba(180,230,255,0.6)" : "rgba(255,255,255,0.25)";
      ctx.beginPath();
      ctx.moveTo(seg.x0, seg.y0);
      ctx.lineTo(seg.x1, seg.y1);
      ctx.stroke();
      if (seg.water) {
        // gentle wave ripples on the surface
        ctx.strokeStyle = "rgba(255,255,255,0.35)";
        ctx.lineWidth = 2;
        for (let wx = seg.x0 + 20; wx < seg.x1 - 10; wx += 40) {
          ctx.beginPath();
          ctx.arc(wx, seg.y0 + 10, 10, Math.PI, 0);
          ctx.stroke();
        }
        ctx.lineWidth = 4;
      }
    }

    // ziplines (grab mid-air to cross a pool quickly)
    for (const z of circuit.ziplines) {
      ctx.strokeStyle = "#5a4632";
      ctx.lineWidth = 3;
      ctx.beginPath();
      ctx.moveTo(z.x0, z.y - 60);
      ctx.lineTo(z.x0, z.y);
      ctx.moveTo(z.x1, z.y - 60);
      ctx.lineTo(z.x1, z.y);
      ctx.stroke();
      ctx.strokeStyle = "#caa46a";
      ctx.lineWidth = 4;
      ctx.beginPath();
      ctx.moveTo(z.x0, z.y);
      ctx.lineTo(z.x1, z.y);
      ctx.stroke();
    }

    // walls (hurdles to jump over)
    for (const wobs of circuit.walls) {
      ctx.fillStyle = circuit.theme.accent;
      ctx.fillRect(wobs.x - wobs.w / 2, wobs.y - wobs.h / 2, wobs.w, wobs.h);
      ctx.strokeStyle = "rgba(0,0,0,0.35)";
      ctx.lineWidth = 3;
      ctx.strokeRect(wobs.x - wobs.w / 2, wobs.y - wobs.h / 2, wobs.w, wobs.h);
    }

    // checkpoints (subtle markers)
    ctx.strokeStyle = "rgba(255,255,255,0.35)";
    ctx.lineWidth = 3;
    ctx.setLineDash([8, 8]);
    for (const cx of circuit.checkpoints) {
      ctx.beginPath();
      ctx.moveTo(cx, circuit.startY - 400);
      ctx.lineTo(cx, circuit.startY + 40);
      ctx.stroke();
    }
    ctx.setLineDash([]);

    // finish line
    ctx.save();
    ctx.translate(circuit.finishX, circuit.startY - 260);
    for (let i = 0; i < 13; i++) {
      ctx.fillStyle = i % 2 === 0 ? "#ffffff" : "#111111";
      ctx.fillRect(-10, i * 24, 20, 24);
    }
    ctx.restore();

    // players (stick figures)
    for (const e of snapshot.entities) {
      const meta = metas.get(e.id);
      const color = meta?.color ?? "#ffffff";
      const flashHidden = e.crashFlash > 0 && e.crashFlash % 6 < 3;
      const inWater = e.onGround && isWaterSegAt(circuit.ground, e.x);
      drawStickFigure(ctx, e.x, e.y, color, e.onGround, e.onZipline, flashHidden, e.finished, inWater);

      ctx.save();
      ctx.translate(e.x, e.y - PLAYER_H - 14);
      ctx.font = "700 12px Segoe UI, sans-serif";
      ctx.textAlign = "center";
      ctx.fillStyle = "rgba(0,0,0,0.5)";
      const label = meta?.name ?? "?";
      const tw = ctx.measureText(label).width;
      roundRect(ctx, -tw / 2 - 6, -14, tw + 12, 18, 6);
      ctx.fill();
      ctx.fillStyle = "#fff";
      ctx.fillText(label, 0, -1);
      if (e.finished) {
        ctx.fillStyle = "#ffd166";
        ctx.fillText("🏁", 0, -20);
      }
      ctx.restore();
    }

    ctx.restore();
  }
}

function drawStickFigure(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  color: string,
  onGround: boolean,
  onZipline: boolean,
  hidden: boolean,
  finished: boolean,
  inWater: boolean
) {
  ctx.save();
  ctx.translate(x, y);
  if (hidden) ctx.globalAlpha = 0.3;

  ctx.fillStyle = "rgba(0,0,0,0.3)";
  ctx.beginPath();
  ctx.ellipse(0, 2, 12, 4, 0, 0, Math.PI * 2);
  ctx.fill();

  const headR = 8;
  const hipY = -14;
  const shoulderY = -34;
  const headY = shoulderY - headR - 2;
  const phase = (x * 0.14) % (Math.PI * 2);
  const swing = onGround && !finished ? Math.sin(phase) : 0;

  ctx.strokeStyle = color;
  ctx.lineWidth = 4;
  ctx.lineCap = "round";

  // legs
  ctx.beginPath();
  if (onZipline) {
    ctx.moveTo(0, hipY);
    ctx.lineTo(6, hipY + 14);
    ctx.moveTo(0, hipY);
    ctx.lineTo(-6, hipY + 14);
  } else if (onGround) {
    ctx.moveTo(0, hipY);
    ctx.lineTo(6 + swing * 8, 0);
    ctx.moveTo(0, hipY);
    ctx.lineTo(-6 - swing * 8, 0);
  } else {
    // tucked jump pose
    ctx.moveTo(0, hipY);
    ctx.lineTo(8, hipY + 10);
    ctx.moveTo(0, hipY);
    ctx.lineTo(-4, hipY + 12);
  }
  ctx.stroke();

  // torso
  ctx.beginPath();
  ctx.moveTo(0, hipY);
  ctx.lineTo(0, shoulderY);
  ctx.stroke();

  // arms
  ctx.beginPath();
  if (onZipline) {
    // both arms reach straight up to the rope
    ctx.moveTo(0, shoulderY + 4);
    ctx.lineTo(6, shoulderY - 18);
    ctx.moveTo(0, shoulderY + 4);
    ctx.lineTo(-6, shoulderY - 18);
  } else if (onGround) {
    ctx.moveTo(0, shoulderY + 4);
    ctx.lineTo(9 - swing * 10, shoulderY + 16);
    ctx.moveTo(0, shoulderY + 4);
    ctx.lineTo(-9 + swing * 10, shoulderY + 16);
  } else {
    ctx.moveTo(0, shoulderY + 4);
    ctx.lineTo(10, shoulderY - 8);
    ctx.moveTo(0, shoulderY + 4);
    ctx.lineTo(-10, shoulderY - 8);
  }
  ctx.stroke();

  // head
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(0, headY, headR, 0, Math.PI * 2);
  ctx.fill();
  ctx.strokeStyle = "rgba(255,255,255,0.7)";
  ctx.lineWidth = 2;
  ctx.stroke();

  if (inWater) {
    ctx.fillStyle = "rgba(120,210,255,0.55)";
    ctx.beginPath();
    ctx.ellipse(0, -4, 15, 9, 0, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.restore();
}

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
