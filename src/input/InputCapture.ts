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
    // Steering is driven by how far you've dragged horizontally from where
    // you first touched down — not by your touch's absolute position (which
    // would snap the wheel to an angle the instant you tap it, wherever that
    // happened to land) and not by tracking the exact angle around the
    // wheel's center (which gets wildly oversensitive if you touch anywhere
    // near the middle rather than right on the rim). A plain horizontal
    // delta is predictable no matter where on the wheel you grab it. The
    // wheel graphic still rotates for visual feedback and springs back to
    // center on release. The kart always drives forward on its own
    // regardless of steering, and the track has hard walls so oversteering
    // can't send it off the road.
    const MAX_ROTATION_DEG = 120;
    const DRAG_RANGE_PX = 85; // horizontal drag distance for full lock
    let active = false;
    let grabX = 0;
    let grabRotationDeg = 0;
    let currentRotationDeg = 0;

    const apply = (rotationDeg: number) => {
      currentRotationDeg = Math.max(-MAX_ROTATION_DEG, Math.min(MAX_ROTATION_DEG, rotationDeg));
      this.state.steer = currentRotationDeg / MAX_ROTATION_DEG;
      el.style.transform = `rotate(${currentRotationDeg}deg)`;
    };
    const reset = () => {
      active = false;
      el.classList.remove("engaged");
      apply(0);
      this.state.steer = 0;
    };

    el.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      active = true;
      el.classList.add("engaged");
      el.setPointerCapture(e.pointerId);
      grabX = e.clientX;
      grabRotationDeg = currentRotationDeg;
    });
    el.addEventListener("pointermove", (e) => {
      e.preventDefault();
      if (!active) return;
      const dx = e.clientX - grabX;
      apply(grabRotationDeg + (dx / DRAG_RANGE_PX) * MAX_ROTATION_DEG);
    });
    el.addEventListener("pointerup", reset);
    el.addEventListener("pointercancel", reset);
  }

  private updateShoot() {
    this.state.shoot = this.fireZoneHeld || this.aimDialHeld;
  }

  private attachAimDial(el: HTMLElement, knob: HTMLElement) {
    // Dragging the dial only re-aims the cannon — it does not fire, so you
    // can sweep it around freely without spraying shots. It fires once you
    // press and hold it still (a short grace period after the last actual
    // movement); moving it again immediately stops the fire and goes back
    // to pure aiming.
    const radius = 30;
    const STILL_DELAY_MS = 130;
    let stillTimer: ReturnType<typeof setTimeout> | null = null;
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
    const clearStillTimer = () => {
      if (stillTimer !== null) {
        clearTimeout(stillTimer);
        stillTimer = null;
      }
    };
    const armStillTimer = () => {
      clearStillTimer();
      stillTimer = setTimeout(() => {
        this.aimDialHeld = true;
        this.updateShoot();
      }, STILL_DELAY_MS);
    };
    el.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      e.stopPropagation();
      el.classList.add("engaged");
      el.setPointerCapture(e.pointerId);
      this.aimDialHeld = false;
      this.updateShoot();
      onMove(e.clientX, e.clientY);
      armStillTimer();
    });
    el.addEventListener("pointermove", (e) => {
      e.preventDefault();
      this.aimDialHeld = false;
      this.updateShoot();
      onMove(e.clientX, e.clientY);
      armStillTimer();
    });
    const release = () => {
      clearStillTimer();
      el.classList.remove("engaged");
      this.aimDialHeld = false;
      this.updateShoot();
    };
    el.addEventListener("pointerup", release);
    el.addEventListener("pointercancel", release);
  }
}
