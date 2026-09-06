import type { GameMode, InputState } from "../net/protocol";
import { emptyInput } from "../net/protocol";

export class InputCapture {
  private state: InputState = emptyInput();
  private mode: GameMode;
  private canvas: HTMLCanvasElement;
  private touchRoot: HTMLElement;
  private aimDialTouched = false;
  private fireZoneHeld = false;
  private aimDialHeld = false;
  private nearestEnemyProvider: () => { x: number; y: number } | null = () => null;
  private keydownHandler = (e: KeyboardEvent) => this.onKey(e, true);
  private keyupHandler = (e: KeyboardEvent) => this.onKey(e, false);
  private mouseMoveHandler = (e: MouseEvent) => this.onMouseMove(e);
  private mouseDownHandler = () => {
    this.state.shoot = true;
  };
  private mouseUpHandler = () => {
    this.state.shoot = false;
  };
  private holdDownHandler = (e: PointerEvent) => {
    e.preventDefault();
    this.state.up = true;
    this.state.jump = true;
  };
  private holdUpHandler = () => {
    this.state.up = false;
    this.state.jump = false;
  };
  private touchNodes: HTMLElement[] = [];

  constructor(mode: GameMode, canvas: HTMLCanvasElement, touchRoot: HTMLElement) {
    this.mode = mode;
    this.canvas = canvas;
    this.touchRoot = touchRoot;
  }

  /** Shooter only: used as the touch fire-zone's aim when the player hasn't
   * dragged the aim dial yet, so tapping to shoot is useful immediately. */
  setNearestEnemyProvider(fn: () => { x: number; y: number } | null) {
    this.nearestEnemyProvider = fn;
  }

  attach() {
    window.addEventListener("keydown", this.keydownHandler);
    window.addEventListener("keyup", this.keyupHandler);
    if (this.mode === "shooter") {
      this.canvas.addEventListener("mousemove", this.mouseMoveHandler);
      this.canvas.addEventListener("mousedown", this.mouseDownHandler);
      window.addEventListener("mouseup", this.mouseUpHandler);
    } else if (this.mode === "course") {
      // Course mode: press anywhere (mouse, touch, or keyboard) to jump —
      // the character runs forward on its own.
      this.canvas.addEventListener("pointerdown", this.holdDownHandler);
      window.addEventListener("pointerup", this.holdUpHandler);
      window.addEventListener("pointercancel", this.holdUpHandler);
    }
    // Kart mode needs neither: it steers via keyboard arrows/AD (handled
    // generically in onKey) plus its own touch joystick built below.
    this.buildTouchControls();
  }

  detach() {
    window.removeEventListener("keydown", this.keydownHandler);
    window.removeEventListener("keyup", this.keyupHandler);
    this.canvas.removeEventListener("mousemove", this.mouseMoveHandler);
    this.canvas.removeEventListener("mousedown", this.mouseDownHandler);
    window.removeEventListener("mouseup", this.mouseUpHandler);
    this.canvas.removeEventListener("pointerdown", this.holdDownHandler);
    window.removeEventListener("pointerup", this.holdUpHandler);
    window.removeEventListener("pointercancel", this.holdUpHandler);
    for (const n of this.touchNodes) n.remove();
    this.touchNodes = [];
  }

  getInput(): InputState {
    if (this.mode === "shooter" && this.state.shoot && !this.aimDialTouched) {
      const target = this.nearestEnemyProvider();
      if (target) {
        const l = Math.hypot(target.x, target.y) || 1;
        this.state.aimX = target.x / l;
        this.state.aimY = target.y / l;
      }
    }
    return { ...this.state };
  }

  private onKey(e: KeyboardEvent, down: boolean) {
    switch (e.code) {
      case "ArrowLeft":
      case "KeyA":
        this.state.left = down;
        break;
      case "ArrowRight":
      case "KeyD":
        this.state.right = down;
        break;
      case "ArrowUp":
      case "KeyW":
        this.state.up = down;
        break;
      case "ArrowDown":
      case "KeyS":
        this.state.down = down;
        break;
      case "Space":
        this.state.up = down || this.state.up;
        this.state.jump = down;
        if (this.mode === "shooter") this.state.shoot = down;
        e.preventDefault();
        break;
    }
  }

  private onMouseMove(e: MouseEvent) {
    const rect = this.canvas.getBoundingClientRect();
    const dx = e.clientX - rect.left - rect.width / 2;
    const dy = e.clientY - rect.top - rect.height / 2;
    const l = Math.hypot(dx, dy) || 1;
    this.state.aimX = dx / l;
    this.state.aimY = dy / l;
  }

  private buildTouchControls() {
    if (this.mode === "course") return; // whole canvas already acts as the control

    if (this.mode === "kart") {
      const wrap = document.createElement("div");
      wrap.className = "touch-controls kart-controls";
      const wheel = this.makeWheel();
      wrap.append(wheel);
      this.attachSteeringWheel(wheel);
      this.touchRoot.append(wrap);
      this.touchNodes.push(wrap);
      return;
    }

    const fireZone = document.createElement("div");
    fireZone.className = "fire-zone";
    fireZone.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      this.fireZoneHeld = true;
      this.updateShoot();
    });
    fireZone.addEventListener("pointerup", (e) => {
      e.preventDefault();
      this.fireZoneHeld = false;
      this.updateShoot();
    });
    fireZone.addEventListener("pointercancel", () => {
      this.fireZoneHeld = false;
      this.updateShoot();
    });

    const wrap = document.createElement("div");
    wrap.className = "touch-controls";

    const pad = document.createElement("div");
    pad.className = "pad";
    const moveStick = this.makeStick();
    pad.append(moveStick.el);
    this.attachMoveJoystick(moveStick.el, moveStick.knob);

    const actions = document.createElement("div");
    actions.className = "actions";
    const aimStick = this.makeStick();
    actions.append(aimStick.el);
    this.attachAimDial(aimStick.el, aimStick.knob);

    wrap.append(pad, actions);
    this.touchRoot.append(fireZone, wrap);
    this.touchNodes.push(fireZone, wrap);
  }

  private makeStick(): { el: HTMLElement; knob: HTMLElement } {
    const el = document.createElement("div");
    el.className = "touch-btn joystick";
    const knob = document.createElement("div");
    knob.className = "knob";
    el.appendChild(knob);
    return { el, knob };
  }

  private makeWheel(): HTMLElement {
    const el = document.createElement("div");
    el.className = "wheel";
    const spoke = document.createElement("div");
    spoke.className = "spoke-v";
    el.appendChild(spoke);
    return el;
  }

  private attachMoveJoystick(el: HTMLElement, knob: HTMLElement) {
    let active = false;
    const radius = 30;
    const setKnob = (dx: number, dy: number) => {
      const d = Math.hypot(dx, dy);
      const scale = d > radius ? radius / d : 1;
      knob.style.transform = `translate(${dx * scale}px, ${dy * scale}px)`;
    };
    const reset = () => {
      active = false;
      this.state.left = this.state.right = this.state.up = this.state.down = false;
      el.classList.remove("engaged");
      knob.style.transform = "translate(0px, 0px)";
    };
    const onMove = (clientX: number, clientY: number) => {
      const rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = clientX - cx;
      const dy = clientY - cy;
      const r = rect.width / 2;
      this.state.left = dx < -r * 0.25;
      this.state.right = dx > r * 0.25;
      this.state.up = dy < -r * 0.25;
      this.state.down = dy > r * 0.25;
      setKnob(dx, dy);
    };
    el.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      e.stopPropagation();
      active = true;
      el.classList.add("engaged");
      el.setPointerCapture(e.pointerId);
      onMove(e.clientX, e.clientY);
    });
    el.addEventListener("pointermove", (e) => {
      e.preventDefault();
      if (active) onMove(e.clientX, e.clientY);
    });
    el.addEventListener("pointerup", reset);
    el.addEventListener("pointercancel", reset);
  }

  private attachSteeringWheel(el: HTMLElement) {
    // Simplest possible model, like a basic on-screen wheel: wherever your
    // finger currently is, left or right of the wheel's center, is exactly
    // how much you're steering — no gesture to learn, no dragging a precise
    // amount, no tracking where you first touched. Move your finger and the
    // wheel (and the car's turn) follows it immediately; let go and it
    // snaps straight back to center. The kart always drives forward on its
    // own regardless of steering, and the track has hard walls so
    // oversteering can't send it off the road.
    const MAX_ROTATION_DEG = 45;
    const FULL_LOCK_PX = 55; // horizontal distance from center for full lock
    let active = false;

    const apply = (ratio: number) => {
      const clamped = Math.max(-1, Math.min(1, ratio));
      this.state.steer = clamped;
      el.style.transform = `rotate(${clamped * MAX_ROTATION_DEG}deg)`;
    };
    const reset = () => {
      active = false;
      el.classList.remove("engaged");
      apply(0);
    };
    const onMove = (clientX: number) => {
      const rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      apply((clientX - cx) / FULL_LOCK_PX);
    };

    el.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      active = true;
      el.classList.add("engaged");
      el.setPointerCapture(e.pointerId);
      onMove(e.clientX);
    });
    el.addEventListener("pointermove", (e) => {
      e.preventDefault();
      if (active) onMove(e.clientX);
    });
    el.addEventListener("pointerup", reset);
    el.addEventListener("pointercancel", reset);
  }

  private updateShoot() {
    this.state.shoot = this.fireZoneHeld || this.aimDialHeld;
  }

  private attachAimDial(el: HTMLElement, knob: HTMLElement) {
    // Touching the dial aims the cannon that way and fires immediately —
    // dragging keeps re-aiming and keeps firing continuously the whole time
    // it's held, like a classic twin-stick aim-and-shoot control.
    const radius = 30;
    const setKnob = (dx: number, dy: number) => {
      const d = Math.hypot(dx, dy);
      const scale = d > radius ? radius / d : 1;
      knob.style.transform = `translate(${dx * scale}px, ${dy * scale}px)`;
    };
    const onMove = (clientX: number, clientY: number) => {
      const rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = clientX - cx;
      const dy = clientY - cy;
      const l = Math.hypot(dx, dy) || 1;
      this.state.aimX = dx / l;
      this.state.aimY = dy / l;
      this.aimDialTouched = true;
      setKnob(dx, dy);
    };
    el.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      e.stopPropagation();
      el.classList.add("engaged");
      el.setPointerCapture(e.pointerId);
      this.aimDialHeld = true;
      this.updateShoot();
      onMove(e.clientX, e.clientY);
    });
    el.addEventListener("pointermove", (e) => {
      e.preventDefault();
      onMove(e.clientX, e.clientY);
    });
    const release = () => {
      el.classList.remove("engaged");
      this.aimDialHeld = false;
      this.updateShoot();
    };
    el.addEventListener("pointerup", release);
    el.addEventListener("pointercancel", release);
  }
}
