import { emptyInputState, type InputState } from './InputState';

const MOUSE_SENSITIVITY = 0.0022;
const TOUCH_LOOK_SENSITIVITY = 0.0055;
const JOYSTICK_RADIUS = 56;

export interface JoystickVisual {
  active: boolean;
  dx: number;
  dy: number;
  radius: number;
}

export class InputManager {
  readonly isTouch: boolean;
  readonly joystick: JoystickVisual = { active: false, dx: 0, dy: 0, radius: JOYSTICK_RADIUS };

  private keys = new Set<string>();
  private pointerLocked = false;
  private mouseDown = false;
  private disposed = false;

  private pendingLookX = 0;
  private pendingLookY = 0;
  private pulseJump = false;
  private pulseInteract = false;
  private pulseUseBerry = false;
  private pulsePlaceAnchor = false;

  private touchGripHeld = false;
  private touchSprintHeld = false;

  private joystickTouchId: number | null = null;
  private joystickOrigin = { x: 0, y: 0 };
  private lookTouchId: number | null = null;
  private lookLast = { x: 0, y: 0 };

  private onKeyDown = (e: KeyboardEvent) => {
    if (e.repeat) return;
    this.keys.add(e.code);
    if (e.code === 'Space') this.pulseJump = true;
    if (e.code === 'KeyE') this.pulseInteract = true;
    if (e.code === 'KeyB' || e.code === 'Digit1') this.pulseUseBerry = true;
    if (e.code === 'KeyR' || e.code === 'Digit2') this.pulsePlaceAnchor = true;
  };
  private onKeyUp = (e: KeyboardEvent) => {
    this.keys.delete(e.code);
  };
  private onClick = () => {
    if (!this.isTouch && document.pointerLockElement !== this.container) {
      this.container.requestPointerLock();
    }
  };
  private onPointerLockChange = () => {
    this.pointerLocked = document.pointerLockElement === this.container;
  };
  private onMouseMove = (e: MouseEvent) => {
    if (!this.pointerLocked) return;
    this.pendingLookX += e.movementX * MOUSE_SENSITIVITY;
    this.pendingLookY += e.movementY * MOUSE_SENSITIVITY;
  };
  private onMouseDown = (e: MouseEvent) => {
    if (e.button === 0) this.mouseDown = true;
  };
  private onMouseUp = (e: MouseEvent) => {
    if (e.button === 0) this.mouseDown = false;
  };

  private onTouchStart = (e: TouchEvent) => {
    for (const t of Array.from(e.changedTouches)) {
      const zone = this.zoneForTouch(t.clientX);
      if (zone === 'joystick' && this.joystickTouchId === null) {
        this.joystickTouchId = t.identifier;
        this.joystickOrigin = { x: t.clientX, y: t.clientY };
        this.joystick.active = true;
        this.joystick.dx = 0;
        this.joystick.dy = 0;
      } else if (zone === 'look' && this.lookTouchId === null) {
        this.lookTouchId = t.identifier;
        this.lookLast = { x: t.clientX, y: t.clientY };
      }
    }
  };
  private onTouchMove = (e: TouchEvent) => {
    for (const t of Array.from(e.changedTouches)) {
      if (t.identifier === this.joystickTouchId) {
        let dx = t.clientX - this.joystickOrigin.x;
        let dy = t.clientY - this.joystickOrigin.y;
        const len = Math.hypot(dx, dy);
        if (len > JOYSTICK_RADIUS) {
          dx = (dx / len) * JOYSTICK_RADIUS;
          dy = (dy / len) * JOYSTICK_RADIUS;
        }
        this.joystick.dx = dx;
        this.joystick.dy = dy;
      } else if (t.identifier === this.lookTouchId) {
        const dx = t.clientX - this.lookLast.x;
        const dy = t.clientY - this.lookLast.y;
        this.pendingLookX += dx * TOUCH_LOOK_SENSITIVITY;
        this.pendingLookY += dy * TOUCH_LOOK_SENSITIVITY;
        this.lookLast = { x: t.clientX, y: t.clientY };
      }
    }
  };
  private onTouchEnd = (e: TouchEvent) => {
    for (const t of Array.from(e.changedTouches)) {
      if (t.identifier === this.joystickTouchId) {
        this.joystickTouchId = null;
        this.joystick.active = false;
        this.joystick.dx = 0;
        this.joystick.dy = 0;
      } else if (t.identifier === this.lookTouchId) {
        this.lookTouchId = null;
      }
    }
  };

  constructor(private container: HTMLElement) {
    this.isTouch = navigator.maxTouchPoints > 0 || 'ontouchstart' in window;
    this.attachKeyboardMouse();
    if (this.isTouch) this.attachTouch();
  }

  private attachKeyboardMouse() {
    window.addEventListener('keydown', this.onKeyDown);
    window.addEventListener('keyup', this.onKeyUp);
    this.container.addEventListener('click', this.onClick);
    document.addEventListener('pointerlockchange', this.onPointerLockChange);
    document.addEventListener('mousemove', this.onMouseMove);
    this.container.addEventListener('mousedown', this.onMouseDown);
    window.addEventListener('mouseup', this.onMouseUp);
  }

  private zoneForTouch(clientX: number): 'joystick' | 'look' {
    return clientX < window.innerWidth * 0.5 ? 'joystick' : 'look';
  }

  private attachTouch() {
    this.container.addEventListener('touchstart', this.onTouchStart, { passive: true });
    this.container.addEventListener('touchmove', this.onTouchMove, { passive: true });
    this.container.addEventListener('touchend', this.onTouchEnd, { passive: true });
    this.container.addEventListener('touchcancel', this.onTouchEnd, { passive: true });
  }

  dispose() {
    if (this.disposed) return;
    this.disposed = true;
    window.removeEventListener('keydown', this.onKeyDown);
    window.removeEventListener('keyup', this.onKeyUp);
    this.container.removeEventListener('click', this.onClick);
    document.removeEventListener('pointerlockchange', this.onPointerLockChange);
    document.removeEventListener('mousemove', this.onMouseMove);
    this.container.removeEventListener('mousedown', this.onMouseDown);
    window.removeEventListener('mouseup', this.onMouseUp);
    if (this.isTouch) {
      this.container.removeEventListener('touchstart', this.onTouchStart);
      this.container.removeEventListener('touchmove', this.onTouchMove);
      this.container.removeEventListener('touchend', this.onTouchEnd);
      this.container.removeEventListener('touchcancel', this.onTouchEnd);
    }
    if (document.pointerLockElement === this.container) document.exitPointerLock();
  }

  // --- appelé par les boutons tactiles (UI) ---
  setTouchGrip(held: boolean) {
    this.touchGripHeld = held;
  }
  setTouchSprint(held: boolean) {
    this.touchSprintHeld = held;
  }
  pulseTouchJump() {
    this.pulseJump = true;
  }
  pulseTouchInteract() {
    this.pulseInteract = true;
  }
  pulseTouchUseBerry() {
    this.pulseUseBerry = true;
  }
  pulseTouchPlaceAnchor() {
    this.pulsePlaceAnchor = true;
  }

  consumeFrame(): InputState {
    let mf = 0;
    let mr = 0;
    if (this.keys.has('KeyW') || this.keys.has('KeyZ') || this.keys.has('ArrowUp')) mf += 1;
    if (this.keys.has('KeyS') || this.keys.has('ArrowDown')) mf -= 1;
    if (this.keys.has('KeyD') || this.keys.has('ArrowRight')) mr += 1;
    if (this.keys.has('KeyA') || this.keys.has('KeyQ') || this.keys.has('ArrowLeft')) mr -= 1;

    if (this.joystick.active) {
      mf += -this.joystick.dy / this.joystick.radius;
      mr += this.joystick.dx / this.joystick.radius;
    }

    const sprint = this.keys.has('ShiftLeft') || this.keys.has('ShiftRight') || this.touchSprintHeld;
    const grip = this.keys.has('KeyF') || this.mouseDown || this.touchGripHeld;

    const state: InputState = {
      ...emptyInputState(),
      moveForward: Math.max(-1, Math.min(1, mf)),
      moveRight: Math.max(-1, Math.min(1, mr)),
      lookDeltaX: this.pendingLookX,
      lookDeltaY: this.pendingLookY,
      jump: this.pulseJump,
      grip,
      sprint,
      interact: this.pulseInteract,
      useBerry: this.pulseUseBerry,
      placeAnchor: this.pulsePlaceAnchor,
    };

    this.pendingLookX = 0;
    this.pendingLookY = 0;
    this.pulseJump = false;
    this.pulseInteract = false;
    this.pulseUseBerry = false;
    this.pulsePlaceAnchor = false;

    return state;
  }
}
