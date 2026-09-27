import { InputManager } from './InputManager';

const RADIUS = 52;

export function mountTouchControls(root: HTMLElement, input: InputManager) {
  if (!input.isTouch) return;

  const joyZone = document.createElement('div');
  joyZone.className = 'joystick-zone interactive';
  const base = document.createElement('div');
  base.className = 'joystick-base';
  const knob = document.createElement('div');
  knob.className = 'joystick-knob';
  base.appendChild(knob);
  joyZone.appendChild(base);
  root.appendChild(joyZone);

  let joyId: number | null = null;
  let centerX = 0;
  let centerY = 0;

  joyZone.addEventListener('pointerdown', (e) => {
    if (joyId !== null) return;
    joyId = e.pointerId;
    centerX = e.clientX;
    centerY = e.clientY;
    base.style.left = `${centerX - 50}px`;
    base.style.top = `${centerY - 50}px`;
    base.style.display = 'block';
    joyZone.setPointerCapture(e.pointerId);
  });
  joyZone.addEventListener('pointermove', (e) => {
    if (e.pointerId !== joyId) return;
    let dx = e.clientX - centerX;
    let dy = e.clientY - centerY;
    const len = Math.hypot(dx, dy);
    if (len > RADIUS) {
      dx = (dx / len) * RADIUS;
      dy = (dy / len) * RADIUS;
    }
    knob.style.left = `${27 + dx}px`;
    knob.style.top = `${27 + dy}px`;
    input.setTouchMove(dx / RADIUS, -dy / RADIUS);
  });
  const endJoy = (e: PointerEvent) => {
    if (e.pointerId !== joyId) return;
    joyId = null;
    base.style.display = 'none';
    knob.style.left = '27px';
    knob.style.top = '27px';
    input.setTouchMove(0, 0);
  };
  joyZone.addEventListener('pointerup', endJoy);
  joyZone.addEventListener('pointercancel', endJoy);

  const buttons = document.createElement('div');
  buttons.className = 'touch-buttons interactive';
  root.appendChild(buttons);

  const jumpBtn = document.createElement('div');
  jumpBtn.className = 'touch-btn';
  jumpBtn.textContent = 'SAUT';
  jumpBtn.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    input.touchJump = true;
    jumpBtn.classList.add('active');
  });
  const endJump = () => {
    input.touchJump = false;
    jumpBtn.classList.remove('active');
  };
  jumpBtn.addEventListener('pointerup', endJump);
  jumpBtn.addEventListener('pointercancel', endJump);

  const grabBtn = document.createElement('div');
  grabBtn.className = 'touch-btn';
  grabBtn.textContent = 'PRISE';
  grabBtn.addEventListener('pointerdown', (e) => {
    e.preventDefault();
    input.touchGrab = true;
    grabBtn.classList.add('active');
  });
  const endGrab = () => {
    input.touchGrab = false;
    grabBtn.classList.remove('active');
  };
  grabBtn.addEventListener('pointerup', endGrab);
  grabBtn.addEventListener('pointercancel', endGrab);

  buttons.appendChild(jumpBtn);
  buttons.appendChild(grabBtn);
}
