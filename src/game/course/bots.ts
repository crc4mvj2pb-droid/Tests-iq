import type { InputState } from "../../net/protocol";
import { emptyInput } from "../../net/protocol";
import type { CircuitDef } from "./circuits";

interface Hazard {
  start: number;
  end: number;
  kind: "gap" | "wall";
}

function computeHazards(circuit: CircuitDef): Hazard[] {
  const hazards: Hazard[] = [];
  const segs = [...circuit.ground].sort((a, b) => Math.min(a.x0, a.x1) - Math.min(b.x0, b.x1));
  for (let i = 0; i < segs.length - 1; i++) {
    const endOfThis = Math.max(segs[i].x0, segs[i].x1);
    const startOfNext = Math.min(segs[i + 1].x0, segs[i + 1].x1);
    if (startOfNext - endOfThis > 4) {
      hazards.push({ start: endOfThis, end: startOfNext, kind: "gap" });
    }
  }
  for (const w of circuit.walls) {
    hazards.push({ start: w.x - w.w / 2, end: w.x + w.w / 2, kind: "wall" });
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
    this.states.set(id, { hazards: computeHazards(this.circuit), jitter: Math.random() * 12 - 6 });
  }

  computeInput(id: string, botX: number): InputState {
    const st = this.states.get(id);
    const input = emptyInput();
    if (!st) return input;

    // Deliberately not gated on "grounded": a bot can still be airborne from
    // clearing the previous obstacle (e.g. landing off a bump) exactly when
    // the next one enters its window, and the sim safely ignores a jump
    // attempt once its jump charges are spent.
    const upcoming = st.hazards.find((h) => h.end > botX);
    if (!upcoming) return input;

    const lead = upcoming.start - botX;
    const [minLead, maxLead] = upcoming.kind === "gap" ? [0, 18] : [30, 130];
    if (lead >= minLead - 5 && lead <= maxLead + st.jitter) {
      input.up = true;
    }
    return input;
  }
}
