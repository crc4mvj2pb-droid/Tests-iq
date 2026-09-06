import type { InputState } from "../../net/protocol";
import { emptyInput } from "../../net/protocol";

interface BotState {
  skill: number; // 0.7 - 1.0, affects how consistently it accelerates
  flipUrge: number; // ticks until next playful flip attempt
  flipHoldLeft: number; // ticks remaining in the current flip attempt
}

export class CourseBotController {
  private states = new Map<string, BotState>();

  register(id: string) {
    this.states.set(id, { skill: 0.82 + Math.random() * 0.18, flipUrge: 60 + Math.random() * 120, flipHoldLeft: 0 });
  }

  computeInput(id: string, onGround: boolean): InputState {
    const st = this.states.get(id);
    if (!st) return emptyInput();
    const input = emptyInput();

    if (onGround) {
      input.up = Math.random() < st.skill;
      st.flipHoldLeft = 0;
    } else {
      // Mostly coast safely (no rotation input) while airborne; occasionally
      // attempt a short, stylish flip — holding "up" both accelerates on the
      // ground and rotates in the air, so this must stay brief to land safely.
      st.flipUrge -= 1;
      if (st.flipUrge <= 0 && st.flipHoldLeft <= 0) {
        st.flipHoldLeft = 14;
        st.flipUrge = 90 + Math.random() * 150;
      }
      if (st.flipHoldLeft > 0) {
        input.up = true;
        st.flipHoldLeft -= 1;
      }
    }
    return input;
  }
}
