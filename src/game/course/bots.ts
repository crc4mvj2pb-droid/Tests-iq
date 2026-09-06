import type { InputState } from "../../net/protocol";
import { emptyInput } from "../../net/protocol";
import type { CircuitDef } from "./circuits";
import { groundYAt } from "./circuits";
import { RUN_SPEED, GRAVITY, JUMP_VELOCITY } from "./sim";

interface Hazard {
  start: number;
  end: number;
  kind: "gap" | "wall" | "zipline";
  topY: number; // wall's absolute world y at its top surface; unused for gap/zipline
  width: number; // wall width; unused for gap/zipline
}

// A jump must already have cleared the wall's height by the time it reaches
// the wall's near edge, AND still be above it by the time it reaches the far
// edge (a jump timed too early has already started falling again by then).
// Both bounds come from the same projectile physics as the sim, with a
// small safety margin.
function wallJumpWindow(h: number, w: number): [number, number] {
  const vy0 = JUMP_VELOCITY;
  const disc = vy0 * vy0 - 2 * GRAVITY * h;
  if (disc <= 0) return [999999, 0]; // taller than max jump height — unreachable
  const sq = Math.sqrt(disc);
  const tRise = (-vy0 - sq) / GRAVITY;
  const tFall = (-vy0 + sq) / GRAVITY;
  const margin = 20;
  const minLead = tRise * RUN_SPEED + margin;
  const maxLead = tFall * RUN_SPEED - w - margin;
  return [minLead, Math.max(minLead + 10, maxLead)];
}

// Two walls close enough together must be cleared by a single jump — merge
// them into one hazard spanning both, using the taller height and the full
// combined width, so the jump window accounts for the whole obstacle rather
// than just the first piece (which was clearing fine on its own while still
// clipping the second one further along the same arc).
const WALL_MERGE_GAP = 100;

function computeHazards(circuit: CircuitDef): Hazard[] {
  const hazards: Hazard[] = [];
  const segs = [...circuit.ground].sort((a, b) => Math.min(a.x0, a.x1) - Math.min(b.x0, b.x1));
  for (let i = 0; i < segs.length - 1; i++) {
    const endOfThis = Math.max(segs[i].x0, segs[i].x1);
    const startOfNext = Math.min(segs[i + 1].x0, segs[i + 1].x1);
    if (startOfNext - endOfThis > 4) {
      hazards.push({ start: endOfThis, end: startOfNext, kind: "gap", topY: 0, width: 0 });
    }
  }

  const wallHazards: Hazard[] = [];
  const sortedWalls = [...circuit.walls].sort((a, b) => a.x - b.x);
  for (const w of sortedWalls) {
    const start = w.x - w.w / 2;
    const end = w.x + w.w / 2;
    const topY = w.y - w.h / 2;
    const last = wallHazards[wallHazards.length - 1];
    if (last && start - last.end < WALL_MERGE_GAP) {
      last.end = end;
      last.topY = Math.min(last.topY, topY); // smaller y = higher/taller — most restrictive wins
      last.width = last.end - last.start;
    } else {
      wallHazards.push({ start, end, kind: "wall", topY, width: w.w });
    }
  }
  hazards.push(...wallHazards);

  for (const z of circuit.ziplines) {
    hazards.push({ start: z.x0, end: z.x1, kind: "zipline", topY: 0, width: 0 });
  }
  hazards.sort((a, b) => a.start - b.start);
  return hazards;
}

interface BotState {
  hazards: Hazard[];
  jitter: number;
}

export class CourseBotController {
  private states = new Map<string, BotState>();
  private circuit: CircuitDef;

  constructor(circuit: CircuitDef) {
    this.circuit = circuit;
  }

  register(id: string) {
    this.states.set(id, { hazards: computeHazards(this.circuit), jitter: Math.random() * 6 - 3 });
  }

  computeInput(id: string, botX: number, onGround: boolean): InputState {
    const st = this.states.get(id);
    const input = emptyInput();
    // Only ever commit to a jump from solid ground: triggering mid-air (even
    // for a "different" upcoming hazard) can stack a weak double-jump onto
    // an already-in-flight arc and wreck its trajectory. A bot that's still
    // airborne just rides out its current jump and reacts once it lands.
    if (!st || !onGround) return input;

    const upcoming = st.hazards.find((h) => h.end > botX);
    if (!upcoming) return input;

    const lead = upcoming.start - botX;
    let minLead = 0;
    let maxLead = 18;
    if (upcoming.kind === "wall") {
      // Height to clear is relative to THIS bot's current ground elevation,
      // not a fixed circuit-authored number — on a slope leading into a wall,
      // the wall's absolute top can sit well above (or below) the launch
      // point, so the jump window must be computed from the real gap.
      const launchGroundY = groundYAt(this.circuit.ground, botX) ?? upcoming.topY;
      const effectiveHeight = launchGroundY - upcoming.topY;
      [minLead, maxLead] = wallJumpWindow(effectiveHeight, upcoming.width);
    }
    if (lead >= minLead - 5 && lead <= maxLead + st.jitter) {
      input.up = true;
    }
    return input;
  }
}
