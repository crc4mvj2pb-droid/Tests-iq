import type { CircuitDef } from "./circuits";
import type { CourseSnapshot, PlayerMeta } from "../../net/protocol";
import { VEHICLE_W, VEHICLE_H } from "./sim";

const GROUND_DEPTH = 1400;

export class CourseRenderer {
  private camX = 0;
  private camY = 0;
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
    const targetY = local ? local.y : circuit.startY;
    if (!this.camInit) {
      this.camX = targetX;
      this.camY = targetY;
      this.camInit = true;
    } else {
      this.camX += (targetX - this.camX) * 0.12;
      this.camY += (targetY - 120 - this.camY) * 0.08;
    }

    // sky
    const sky = ctx.createLinearGradient(0, 0, 0, h);
    sky.addColorStop(0, circuit.theme.sky);
    sky.addColorStop(1, circuit.theme.sky2);
    ctx.fillStyle = sky;
    ctx.fillRect(0, 0, w, h);

    ctx.save();
    ctx.translate(w / 2 - this.camX, h / 2 - this.camY + 60);

    // parallax hills
    ctx.fillStyle = "rgba(0,0,0,0.08)";
    for (let i = -2; i < 12; i++) {
      const bx = i * 400 - ((this.camX * 0.4) % 400);
      ctx.beginPath();
      ctx.ellipse(bx, circuit.startY - 40, 220, 120, 0, 0, Math.PI * 2);
      ctx.fill();
    }

    // ground
    ctx.fillStyle = circuit.theme.ground;
    for (const seg of circuit.ground) {
      ctx.beginPath();
      ctx.moveTo(seg.x0, seg.y0);
      ctx.lineTo(seg.x1, seg.y1);
      ctx.lineTo(seg.x1, seg.y1 + GROUND_DEPTH);
      ctx.lineTo(seg.x0, seg.y0 + GROUND_DEPTH);
      ctx.closePath();
      ctx.fill();
    }
    ctx.strokeStyle = "rgba(255,255,255,0.25)";
    ctx.lineWidth = 4;
    for (const seg of circuit.ground) {
      ctx.beginPath();
      ctx.moveTo(seg.x0, seg.y0);
      ctx.lineTo(seg.x1, seg.y1);
      ctx.stroke();
    }

    // walls
    ctx.fillStyle = circuit.theme.accent;
    for (const wobs of circuit.walls) {
      ctx.fillRect(wobs.x - wobs.w / 2, wobs.y - wobs.h / 2, wobs.w, wobs.h);
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

    // players
    for (const e of snapshot.entities) {
      const meta = metas.get(e.id);
      const color = meta?.color ?? "#ffffff";
      ctx.save();
      ctx.translate(e.x, e.y);
      if (e.crashFlash > 0 && e.crashFlash % 6 < 3) {
        ctx.globalAlpha = 0.35;
      }
      ctx.rotate(e.angle);
      ctx.fillStyle = "rgba(0,0,0,0.35)";
      ctx.beginPath();
      ctx.ellipse(0, VEHICLE_H, VEHICLE_W * 0.6, 6, 0, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = color;
      roundRect(ctx, -VEHICLE_W / 2, -VEHICLE_H / 2, VEHICLE_W, VEHICLE_H, 8);
      ctx.fill();

      ctx.fillStyle = "#111";
      ctx.beginPath();
      ctx.arc(-VEHICLE_W / 2 + 10, VEHICLE_H / 2, 8, 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      ctx.arc(VEHICLE_W / 2 - 10, VEHICLE_H / 2, 8, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = "rgba(255,255,255,0.9)";
      ctx.fillRect(VEHICLE_W / 2 - 10, -VEHICLE_H / 2 + 4, 8, 6);
      ctx.restore();

      // nameplate (unrotated)
      ctx.save();
      ctx.translate(e.x, e.y - VEHICLE_H - 14);
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

function roundRect(ctx: CanvasRenderingContext2D, x: number, y: number, w: number, h: number, r: number) {
  ctx.beginPath();
  ctx.moveTo(x + r, y);
  ctx.arcTo(x + w, y, x + w, y + h, r);
  ctx.arcTo(x + w, y + h, x, y + h, r);
  ctx.arcTo(x, y + h, x, y, r);
  ctx.arcTo(x, y, x + w, y, r);
  ctx.closePath();
}
