import type { InputState, BotDifficulty } from "../../net/protocol";
import { emptyInput } from "../../net/protocol";
import type { ShooterMap } from "./maps";

const ACCURACY_RANGE: Record<BotDifficulty, [number, number]> = {
  easy: [0.2, 0.4],
  normal: [0.55, 0.9],
  hard: [0.85, 1.0],
};
const ENGAGE_RANGE: Record<BotDifficulty, number> = { easy: 480, normal: 620, hard: 760 };
const SHOOT_CHANCE: Record<BotDifficulty, number> = { easy: 0.5, normal: 0.85, hard: 1.0 };

interface BotState {
  accuracy: number;
  strafeDir: number;
  strafeTimer: number;
  engageRange: number;
  shootChance: number;
}

export class ShooterBotController {
  private states = new Map<string, BotState>();

  register(id: string, difficulty: BotDifficulty = "normal") {
    const [lo, hi] = ACCURACY_RANGE[difficulty];
    this.states.set(id, {
      accuracy: lo + Math.random() * (hi - lo),
      strafeDir: Math.random() < 0.5 ? 1 : -1,
      strafeTimer: 30 + Math.random() * 60,
      engageRange: ENGAGE_RANGE[difficulty],
      shootChance: SHOOT_CHANCE[difficulty],
    });
  }

  computeInput(
    id: string,
    map: ShooterMap,
    players: { id: string; x: number; y: number; alive: boolean }[]
  ): InputState {
    const st = this.states.get(id);
    const self = players.find((p) => p.id === id);
    const input = emptyInput();
    if (!st || !self || !self.alive) return input;

    let nearest: { id: string; x: number; y: number } | null = null;
    let nearestDist = Infinity;
    for (const p of players) {
      if (p.id === id || !p.alive) continue;
      const d = Math.hypot(p.x - self.x, p.y - self.y);
      if (d < nearestDist) {
        nearestDist = d;
        nearest = p;
      }
    }

    st.strafeTimer -= 1;
    if (st.strafeTimer <= 0) {
      st.strafeDir *= -1;
      st.strafeTimer = 30 + Math.random() * 60;
    }

    if (!nearest) {
      // wander toward map center-ish
      input.right = self.x < map.width / 2;
      input.left = !input.right;
      return input;
    }

    const dx = nearest.x - self.x;
    const dy = nearest.y - self.y;
    const dist = Math.hypot(dx, dy) || 1;
    const dirX = dx / dist;
    const dirY = dy / dist;

    const desiredRange = 260;
    if (dist > desiredRange + 40) {
      input.right = dirX > 0.2;
      input.left = dirX < -0.2;
      input.down = dirY > 0.2;
      input.up = dirY < -0.2;
    } else if (dist < desiredRange - 60) {
      input.right = dirX < -0.2;
      input.left = dirX > 0.2;
      input.down = dirY < -0.2;
      input.up = dirY > 0.2;
    } else {
      // strafe perpendicular to keep distance and stay unpredictable
      const perpX = -dirY * st.strafeDir;
      const perpY = dirX * st.strafeDir;
      input.right = perpX > 0.2;
      input.left = perpX < -0.2;
      input.down = perpY > 0.2;
      input.up = perpY < -0.2;
    }

    const spread = (1 - st.accuracy) * 0.5;
    const angle = Math.atan2(dirY, dirX) + (Math.random() * 2 - 1) * spread;
    input.aimX = Math.cos(angle);
    input.aimY = Math.sin(angle);
    input.shoot = dist < st.engageRange && Math.random() < st.shootChance;

    return input;
  }
}
