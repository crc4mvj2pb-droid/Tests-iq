import type { KartTrack } from "./tracks";
import type { KartSnapshot, PlayerMeta } from "../../net/protocol";
import { CAR_LENGTH, CAR_WIDTH, LAPS_TOTAL } from "./sim";

export class KartRenderer {
  private camX = 0;
  private camY = 0;
  private camInit = false;

  draw(
    ctx: CanvasRenderingContext2D,
    w: number,
    h: number,
    track: KartTrack,
    snapshot: KartSnapshot,
    localId: string,
    metas: Map<string, PlayerMeta>
  ) {
    const local = snapshot.entities.find((e) => e.id === localId) ?? snapshot.entities[0];
    const targetX = local ? local.x : track.waypoints[0].x;
    const targetY = local ? local.y : track.waypoints[0].y;
    if (!this.camInit) {
      this.camX = targetX;
      this.camY = targetY;
      this.camInit = true;
    } else {
      this.camX += (targetX - this.camX) * 0.15;
      this.camY += (targetY - this.camY) * 0.15;
    }

    ctx.fillStyle = track.theme.grass;
    ctx.fillRect(0, 0, w, h);

    ctx.save();
    ctx.translate(w / 2 - this.camX, h / 2 - this.camY);

    // scenery
    ctx.fillStyle = track.theme.grass2;
    for (const d of track.decorations) {
      ctx.beginPath();
      ctx.arc(d.x, d.y, d.r, 0, Math.PI * 2);
      ctx.fill();
    }

    // road
    const wp = track.waypoints;
    ctx.lineJoin = "round";
    ctx.lineCap = "round";
    ctx.strokeStyle = track.theme.road;
    ctx.lineWidth = track.roadWidth;
    tracePath(ctx, wp);
    ctx.stroke();

    // edge lines
    ctx.strokeStyle = "rgba(255,255,255,0.5)";
    ctx.lineWidth = 4;
    tracePathOffset(ctx, wp, track.roadWidth / 2 - 6);
    ctx.stroke();
    tracePathOffset(ctx, wp, -(track.roadWidth / 2 - 6));
    ctx.stroke();

    // dashed centerline
    ctx.strokeStyle = track.theme.roadLine;
    ctx.lineWidth = 4;
    ctx.setLineDash([22, 18]);
    tracePath(ctx, wp);
    ctx.stroke();
    ctx.setLineDash([]);

    // start/finish line
    const s0 = wp[track.startIndex];
    const s1 = wp[(track.startIndex + 1) % wp.length];
    const dx = s1.x - s0.x;
    const dy = s1.y - s0.y;
    const half = track.roadWidth / 2;
    ctx.save();
    ctx.translate(s0.x, s0.y);
    ctx.rotate(Math.atan2(dy, dx));
    const squares = 8;
    const sqSize = (half * 2) / squares;
    for (let i = 0; i < squares; i++) {
      ctx.fillStyle = i % 2 === 0 ? "#ffffff" : "#111111";
      ctx.fillRect(-10, -half + i * sqSize, 20, sqSize);
    }
    ctx.restore();

    // cars
    for (const e of snapshot.entities) {
      const meta = metas.get(e.id);
      const color = meta?.color ?? "#ffffff";
      ctx.save();
      ctx.translate(e.x, e.y);
      ctx.rotate(e.heading);

      ctx.fillStyle = "rgba(0,0,0,0.3)";
      ctx.beginPath();
      ctx.ellipse(0, 3, CAR_LENGTH / 2, CAR_WIDTH / 2, 0, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = color;
      roundRect(ctx, -CAR_LENGTH / 2, -CAR_WIDTH / 2, CAR_LENGTH, CAR_WIDTH, 6);
      ctx.fill();
      ctx.strokeStyle = "rgba(255,255,255,0.7)";
      ctx.lineWidth = 2;
      ctx.stroke();

      ctx.fillStyle = "rgba(20,20,30,0.85)";
      ctx.fillRect(CAR_LENGTH / 2 - 12, -CAR_WIDTH / 2 + 3, 8, CAR_WIDTH - 6);
      ctx.restore();

      ctx.save();
      ctx.translate(e.x, e.y - 26);
      ctx.font = "700 11px Segoe UI, sans-serif";
      ctx.textAlign = "center";
      const label = `${meta?.name ?? "?"} · ${Math.min(e.lap + 1, LAPS_TOTAL)}/${LAPS_TOTAL}`;
      ctx.fillStyle = "rgba(0,0,0,0.55)";
      const tw = ctx.measureText(label).width;
      roundRect(ctx, -tw / 2 - 5, -13, tw + 10, 15, 6);
      ctx.fill();
      ctx.fillStyle = "#fff";
      ctx.fillText(label, 0, -2);
      ctx.restore();
    }

    ctx.restore();
  }
}

function tracePath(ctx: CanvasRenderingContext2D, wp: { x: number; y: number }[]) {
  ctx.beginPath();
  ctx.moveTo(wp[0].x, wp[0].y);
  for (let i = 1; i <= wp.length; i++) {
    const p = wp[i % wp.length];
    ctx.lineTo(p.x, p.y);
  }
}

function tracePathOffset(ctx: CanvasRenderingContext2D, wp: { x: number; y: number }[], offset: number) {
  ctx.beginPath();
  for (let i = 0; i <= wp.length; i++) {
    const a = wp[i % wp.length];
    const b = wp[(i + 1) % wp.length];
    const dx = b.x - a.x;
    const dy = b.y - a.y;
    const len = Math.hypot(dx, dy) || 1;
    const nx = (-dy / len) * offset;
    const ny = (dx / len) * offset;
    if (i === 0) ctx.moveTo(a.x + nx, a.y + ny);
    else ctx.lineTo(a.x + nx, a.y + ny);
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
