import type { ShooterMap } from "./maps";
import type { ShooterSnapshot, PlayerMeta } from "../../net/protocol";
import { PLAYER_R } from "./sim";

export class ShooterRenderer {
  private camX = 0;
  private camY = 0;
  private camInit = false;

  draw(
    ctx: CanvasRenderingContext2D,
    w: number,
    h: number,
    map: ShooterMap,
    snapshot: ShooterSnapshot,
    localId: string,
    metas: Map<string, PlayerMeta>
  ) {
    const local = snapshot.entities.find((e) => e.id === localId);
    const targetX = local ? local.x : map.width / 2;
    const targetY = local ? local.y : map.height / 2;
    if (!this.camInit) {
      this.camX = targetX;
      this.camY = targetY;
      this.camInit = true;
    } else {
      this.camX += (targetX - this.camX) * 0.18;
      this.camY += (targetY - this.camY) * 0.18;
    }

    ctx.fillStyle = "#05060a";
    ctx.fillRect(0, 0, w, h);

    ctx.save();
    ctx.translate(w / 2 - this.camX, h / 2 - this.camY);

    // floor
    ctx.fillStyle = map.theme.floor;
    ctx.fillRect(0, 0, map.width, map.height);
    ctx.fillStyle = map.theme.line;
    const grid = 80;
    for (let x = 0; x < map.width; x += grid) {
      ctx.fillRect(x, 0, 1, map.height);
    }
    for (let y = 0; y < map.height; y += grid) {
      ctx.fillRect(0, y, map.width, 1);
    }
    ctx.strokeStyle = map.theme.wall;
    ctx.lineWidth = 6;
    ctx.strokeRect(3, 3, map.width - 6, map.height - 6);

    // obstacles
    ctx.fillStyle = map.theme.wall;
    for (const o of map.obstacles) {
      ctx.fillRect(o.x - o.w / 2, o.y - o.h / 2, o.w, o.h);
      ctx.strokeStyle = "rgba(0,0,0,0.3)";
      ctx.lineWidth = 3;
      ctx.strokeRect(o.x - o.w / 2, o.y - o.h / 2, o.w, o.h);
    }

    // bullets
    ctx.fillStyle = "#fff8c9";
    for (const b of snapshot.bullets) {
      ctx.beginPath();
      ctx.arc(b.x, b.y, 5, 0, Math.PI * 2);
      ctx.fill();
    }

    // players
    for (const e of snapshot.entities) {
      if (!e.alive) continue;
      const meta = metas.get(e.id);
      const color = meta?.color ?? "#fff";
      ctx.save();
      ctx.globalAlpha = e.invuln ? 0.55 : 1;
      ctx.translate(e.x, e.y);

      ctx.fillStyle = "rgba(0,0,0,0.35)";
      ctx.beginPath();
      ctx.ellipse(0, PLAYER_R * 0.7, PLAYER_R * 0.9, PLAYER_R * 0.4, 0, 0, Math.PI * 2);
      ctx.fill();

      const aimAngle = Math.atan2(e.aimY, e.aimX);
      ctx.save();
      ctx.rotate(aimAngle);
      ctx.fillStyle = "#333";
      ctx.fillRect(PLAYER_R - 4, -4, 20, 8);
      ctx.restore();

      ctx.fillStyle = color;
      ctx.beginPath();
      ctx.arc(0, 0, PLAYER_R, 0, Math.PI * 2);
      ctx.fill();
      ctx.strokeStyle = "rgba(255,255,255,0.6)";
      ctx.lineWidth = 2;
      ctx.stroke();
      ctx.restore();

      // hp bar + name
      ctx.save();
      ctx.translate(e.x, e.y - PLAYER_R - 20);
      const label = meta?.name ?? "?";
      ctx.font = "700 11px Segoe UI, sans-serif";
      ctx.textAlign = "center";
      ctx.fillStyle = "rgba(0,0,0,0.55)";
      const tw = ctx.measureText(label).width;
      ctx.fillRect(-tw / 2 - 5, -13, tw + 10, 14);
      ctx.fillStyle = "#fff";
      ctx.fillText(label, 0, -2);
      const barW = 34;
      ctx.fillStyle = "rgba(0,0,0,0.5)";
      ctx.fillRect(-barW / 2, 2, barW, 5);
      ctx.fillStyle = e.hp > 40 ? "#4ade80" : "#ff5d73";
      ctx.fillRect(-barW / 2, 2, barW * Math.max(0, e.hp / 100), 5);
      ctx.restore();
    }

    ctx.restore();
  }
}
