export function isTouchDevice(): boolean {
  return 'ontouchstart' in window || navigator.maxTouchPoints > 0;
}

export class InputManager {
  private keys = new Set<string>();
  private prevKeys = new Set<string>();

  yaw = -Math.PI / 4;
  pitch = 0.35;

  touchMoveX = 0;
  touchMoveZ = 0;

  hotbarPressed: number | null = null;
  touchGrab = false;
  touchJump = false;

  readonly isTouch = isTouchDevice();

  private dragId: number | null = null;
  private lastX = 0;
  private lastY = 0;

  constructor(private canvas: HTMLElement) {
    window.addEventListener('keydown', (e) => {
      this.keys.add(e.code);
    });
    window.addEventListener('keyup', (e) => {
      this.keys.delete(e.code);
    });
    window.addEventListener('blur', () => this.keys.clear());

    canvas.addEventListener('pointerdown', (e) => {
      if (this.dragId !== null) return;
      this.dragId = e.pointerId;
      this.lastX = e.clientX;
      this.lastY = e.clientY;
      canvas.setPointerCapture(e.pointerId);
    });
    canvas.addEventListener('pointermove', (e) => {
      if (e.pointerId !== this.dragId) return;
      const dx = e.clientX - this.lastX;
      const dy = e.clientY - this.lastY;
      this.lastX = e.clientX;
      this.lastY = e.clientY;
      this.yaw -= dx * 0.0042;
      this.pitch = Math.max(-0.75, Math.min(1.25, this.pitch - dy * 0.0032));
    });
    const release = (e: PointerEvent) => {
      if (e.pointerId === this.dragId) this.dragId = null;
    };
    canvas.addEventListener('pointerup', release);
    canvas.addEventListener('pointercancel', release);
  }

  private keyMoveX(): number {
    let x = 0;
    if (this.keys.has('KeyD') || this.keys.has('ArrowRight')) x += 1;
    if (this.keys.has('KeyA') || this.keys.has('ArrowLeft')) x -= 1;
    return x;
  }

  private keyMoveZ(): number {
    let z = 0;
    if (this.keys.has('KeyW') || this.keys.has('ArrowUp')) z += 1;
    if (this.keys.has('KeyS') || this.keys.has('ArrowDown')) z -= 1;
    return z;
  }

  get moveX(): number {
    const v = this.keyMoveX() + this.touchMoveX;
    return Math.max(-1, Math.min(1, v));
  }

  get moveZ(): number {
    const v = this.keyMoveZ() + this.touchMoveZ;
    return Math.max(-1, Math.min(1, v));
  }

  get moveMagnitude(): number {
    return Math.min(1, Math.hypot(this.moveX, this.moveZ));
  }

  get sprintHeld(): boolean {
    return this.keys.has('ShiftLeft') || this.keys.has('ShiftRight') || this.moveMagnitude > 0.85;
  }

  get grabHeld(): boolean {
    return this.keys.has('KeyE') || this.keys.has('KeyF') || this.touchGrab;
  }

  consumeJumpPressed(): boolean {
    const jumpDown = this.keys.has('Space') || this.touchJump;
    const wasDown = this.prevKeys.has('__jump__');
    if (jumpDown) this.prevKeys.add('__jump__');
    else this.prevKeys.delete('__jump__');
    return jumpDown && !wasDown;
  }

  consumeHotbar(): number | null {
    for (let i = 0; i < 4; i++) {
      const code = `Digit${i + 1}`;
      if (this.keys.has(code) && !this.prevKeys.has(code)) {
        this.syncPrevDigit(code);
        return i;
      }
    }
    if (this.hotbarPressed !== null) {
      const v = this.hotbarPressed;
      this.hotbarPressed = null;
      return v;
    }
    this.syncPrevDigits();
    return null;
  }

  private syncPrevDigit(code: string) {
    this.prevKeys.add(code);
  }

  private syncPrevDigits() {
    for (let i = 0; i < 4; i++) {
      const code = `Digit${i + 1}`;
      if (this.keys.has(code)) this.prevKeys.add(code);
      else this.prevKeys.delete(code);
    }
  }

  setTouchMove(x: number, z: number) {
    this.touchMoveX = x;
    this.touchMoveZ = z;
  }
}
