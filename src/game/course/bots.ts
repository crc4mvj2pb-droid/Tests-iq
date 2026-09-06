import type { InputState } from "../../net/protocol";
import { emptyInput } from "../../net/protocol";

interface BotState {
  skill: number; // 0.7 - 1.0, affects how consistently it accelerates
  flipUrge: number; // countdown to next playful flip attempt
}

export class CourseBotController {
  private states = new Map<string, BotState>();

  register(id: string) {
    this.states.set(id, { skill: 0.82 + Math.random() * 0.18, flipUrge: 60 + Math.random() * 120 });
  }

  computeInput(id: string, onGround: boolean): InputState {
    const st = this.states.get(id);
    if (!st) return emptyInput();
    const input = emptyInput();
    input.up = Math.random() < st.skill;

    if (!onGround) {
      st.flipUrge -= 1;
      if (st.flipUrge <= 0) {
        if (Math.random() < 0.5) input.left = true;
        else input.right = true;
        if (st.flipUrge < -12) st.flipUrge = 80 + Math.random() * 140;
      }
    }
    return input;
  }
}
