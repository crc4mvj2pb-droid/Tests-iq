import type { GameMode, InputState } from "../net/protocol";
import { emptyInput } from "../net/protocol";

export class InputCapture {
  private state: InputState = emptyInput();
  private mode: GameMode;
  private canvas: HTMLCanvasElement;
  private touchRoot: HTMLElement;
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

  attach() {
    window.addEventListener("keydown", this.keydownHandler);
    window.addEventListener("keyup", this.keyupHandler);
    if (this.mode === "shooter") {
      this.canvas.addEventListener("mousemove", this.mouseMoveHandler);
      this.canvas.addEventListener("mousedown", this.mouseDownHandler);
      window.addEventListener("mouseup", this.mouseUpHandler);
    } else {
      // Course mode: press anywhere (mouse or touch) to accelerate / flip —
      // no need to find a specific button.
      this.canvas.addEventListener("pointerdown", this.holdDownHandler);
      window.addEventListener("pointerup", this.holdUpHandler);
      window.addEventListener("pointercancel", this.holdUpHandler);
    }
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

    const fireZone = document.createElement("div");
    fireZone.className = "fire-zone";
    fireZone.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      this.state.shoot = true;
    });
    fireZone.addEventListener("pointerup", () => (this.state.shoot = false));
    fireZone.addEventListener("pointercancel", () => (this.state.shoot = false));

    const wrap = document.createElement("div");
    wrap.className = "touch-controls";

    const pad = document.createElement("div");
    pad.className = "pad";
    const moveStick = document.createElement("div");
    moveStick.className = "touch-btn wide";
    moveStick.style.width = "96px";
    moveStick.style.height = "96px";
    moveStick.style.borderRadius = "50%";
    moveStick.textContent = "🕹";
    pad.append(moveStick);
    this.attachMoveJoystick(moveStick);

    const actions = document.createElement("div");
    actions.className = "actions";
    const aimStick = document.createElement("div");
    aimStick.className = "touch-btn wide";
    aimStick.style.width = "96px";
    aimStick.style.height = "96px";
    aimStick.style.borderRadius = "50%";
    aimStick.textContent = "🎯";
    actions.append(aimStick);
    this.attachAimDial(aimStick);

    wrap.append(pad, actions);
    this.touchRoot.append(fireZone, wrap);
    this.touchNodes.push(fireZone, wrap);
  }

  private attachMoveJoystick(el: HTMLElement) {
    let active = false;
    const reset = () => {
      active = false;
      this.state.left = this.state.right = this.state.up = this.state.down = false;
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
    };
    el.addEventListener("pointerdown", (e) => {
      e.stopPropagation();
      active = true;
      el.setPointerCapture(e.pointerId);
      onMove(e.clientX, e.clientY);
    });
    el.addEventListener("pointermove", (e) => {
      if (active) onMove(e.clientX, e.clientY);
    });
    el.addEventListener("pointerup", reset);
    el.addEventListener("pointercancel", reset);
  }

  private attachAimDial(el: HTMLElement) {
    // Drag to set a firing direction; it's kept even after release, so a
    // separate tap anywhere else on screen fires that way (see fire-zone).
    const onMove = (clientX: number, clientY: number) => {
      const rect = el.getBoundingClientRect();
      const cx = rect.left + rect.width / 2;
      const cy = rect.top + rect.height / 2;
      const dx = clientX - cx;
      const dy = clientY - cy;
      const l = Math.hypot(dx, dy) || 1;
      this.state.aimX = dx / l;
      this.state.aimY = dy / l;
    };
    el.addEventListener("pointerdown", (e) => {
      e.stopPropagation();
      el.setPointerCapture(e.pointerId);
      onMove(e.clientX, e.clientY);
    });
    el.addEventListener("pointermove", (e) => onMove(e.clientX, e.clientY));
  }
}
