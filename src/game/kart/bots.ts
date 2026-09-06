import type { InputState, BotDifficulty } from "../../net/protocol";
import { emptyInput } from "../../net/protocol";
import type { KartTrack } from "./tracks";

function angleDiff(a: number, b: number): number {
  let d = (a - b) % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return d;
}

// Wider jitter and a slower correction threshold make a bot's line noticeably
// wobblier (and thus slower, since it scrapes walls more) without touching
// the shared driving physics at all.
const JITTER_RANGE: Record<BotDifficulty, number> = { easy: 0.7, normal: 0.1, hard: 0.03 };
const CORRECTION_THRESHOLD: Record<BotDifficulty, number> = { easy: 0.14, normal: 0.06, hard: 0.03 };

interface BotState {
  jitter: number;
  threshold: number;
}

export class KartBotController {
  private states = new Map<string, BotState>();
  private track: KartTrack;
  private difficulty: BotDifficulty;

  constructor(track: KartTrack, difficulty: BotDifficulty = "normal") {
    this.track = track;
    this.difficulty = difficulty;
  }

  register(id: string) {
    const range = JITTER_RANGE[this.difficulty];
    this.states.set(id, { jitter: (Math.random() - 0.5) * range, threshold: CORRECTION_THRESHOLD[this.difficulty] });
  }

  computeInput(id: string, x: number, y: number, heading: number, nextWaypoint: number): InputState {
    const st = this.states.get(id);
    const input = emptyInput();
    if (!st) return input;

    const target = this.track.waypoints[nextWaypoint];
    const targetAngle = Math.atan2(target.y - y, target.x - x) + st.jitter;
    const diff = angleDiff(targetAngle, heading);
    if (diff > st.threshold) input.right = true;
    else if (diff < -st.threshold) input.left = true;
    return input;
  }
}
