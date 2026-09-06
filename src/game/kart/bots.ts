import type { InputState } from "../../net/protocol";
import { emptyInput } from "../../net/protocol";
import type { KartTrack } from "./tracks";

function angleDiff(a: number, b: number): number {
  let d = (a - b) % (Math.PI * 2);
  if (d > Math.PI) d -= Math.PI * 2;
  if (d < -Math.PI) d += Math.PI * 2;
  return d;
}

interface BotState {
  jitter: number;
}

export class KartBotController {
  private states = new Map<string, BotState>();
  private track: KartTrack;

  constructor(track: KartTrack) {
    this.track = track;
  }

  register(id: string) {
    this.states.set(id, { jitter: (Math.random() - 0.5) * 0.1 });
  }

  computeInput(id: string, x: number, y: number, heading: number, nextWaypoint: number): InputState {
    const st = this.states.get(id);
    const input = emptyInput();
    if (!st) return input;

    const target = this.track.waypoints[nextWaypoint];
    const targetAngle = Math.atan2(target.y - y, target.x - x) + st.jitter;
    const diff = angleDiff(targetAngle, heading);
    if (diff > 0.06) input.right = true;
    else if (diff < -0.06) input.left = true;
    return input;
  }
}
