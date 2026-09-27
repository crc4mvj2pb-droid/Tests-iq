import type { InputManager } from '../core/game/InputManager';

export interface TouchControlsHandle {
  updateJoystick: () => void;
  destroy: () => void;
}

function bindHold(btn: HTMLElement, onDown: () => void, onUp: () => void) {
  const down = (e: TouchEvent) => {
    e.preventDefault();
    e.stopPropagation();
    btn.classList.add('active');
    onDown();
  };
  const up = (e: TouchEvent) => {
    e.preventDefault();
    e.stopPropagation();
    btn.classList.remove('active');
    onUp();
  };
  btn.addEventListener('touchstart', down, { passive: false });
  btn.addEventListener('touchend', up, { passive: false });
  btn.addEventListener('touchcancel', up, { passive: false });
}

function bindPulse(btn: HTMLElement, onPulse: () => void) {
  const down = (e: TouchEvent) => {
    e.preventDefault();
    e.stopPropagation();
    btn.classList.add('active');
    onPulse();
  };
  const up = (e: TouchEvent) => {
    e.preventDefault();
    e.stopPropagation();
    btn.classList.remove('active');
  };
  btn.addEventListener('touchstart', down, { passive: false });
  btn.addEventListener('touchend', up, { passive: false });
  btn.addEventListener('touchcancel', up, { passive: false });
}

export function mountTouchControls(root: HTMLElement, input: InputManager): TouchControlsHandle {
  const layer = document.createElement('div');
  layer.className = 'touch-layer';
  layer.innerHTML = `
    <div class="joystick-base"><div class="joystick-knob" id="tc-knob"></div></div>
    <div class="touch-buttons">
      <button class="touch-btn berry" id="tc-berry" title="Manger">🍓</button>
      <button class="touch-btn anchor" id="tc-anchor" title="Ancre">⚓</button>
      <button class="touch-btn jump" id="tc-jump" title="Sauter">⤒</button>
      <button class="touch-btn grip" id="tc-grip">S'AGRIPPER</button>
      <button class="touch-btn sprint" id="tc-sprint" title="Sprint">⚡</button>
      <button class="touch-btn interact" id="tc-interact" title="Relever">✋</button>
    </div>
  `;
  root.appendChild(layer);

  const knob = layer.querySelector<HTMLElement>('#tc-knob')!;
  const gripBtn = layer.querySelector<HTMLElement>('#tc-grip')!;
  const sprintBtn = layer.querySelector<HTMLElement>('#tc-sprint')!;
  const jumpBtn = layer.querySelector<HTMLElement>('#tc-jump')!;
  const berryBtn = layer.querySelector<HTMLElement>('#tc-berry')!;
  const anchorBtn = layer.querySelector<HTMLElement>('#tc-anchor')!;
  const interactBtn = layer.querySelector<HTMLElement>('#tc-interact')!;

  bindHold(
    gripBtn,
    () => input.setTouchGrip(true),
    () => input.setTouchGrip(false),
  );
  bindHold(
    sprintBtn,
    () => input.setTouchSprint(true),
    () => input.setTouchSprint(false),
  );
  bindPulse(jumpBtn, () => input.pulseTouchJump());
  bindPulse(berryBtn, () => input.pulseTouchUseBerry());
  bindPulse(anchorBtn, () => input.pulseTouchPlaceAnchor());
  bindPulse(interactBtn, () => input.pulseTouchInteract());

  return {
    updateJoystick: () => {
      const { active, dx, dy } = input.joystick;
      if (active) {
        knob.style.transform = `translate(calc(-50% + ${dx}px), calc(-50% + ${dy}px))`;
      } else {
        knob.style.transform = 'translate(-50%, -50%)';
      }
    },
    destroy: () => {
      layer.remove();
    },
  };
}
