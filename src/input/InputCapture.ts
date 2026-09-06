import type { GameMode, InputState } from "../net/protocol";
import { emptyInput } from "../net/protocol";

export class InputCapture {
  private state: InputState = emptyInput();
  private touchShootHeld = false;
  private mode: GameMode;
  private canvas: HTMLCanvasElement;
  private touchRoot: HTMLElement;
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
  private touchNodes: HTMLElement[] = [];

  constructor(mode: GameMode, canvas: HTMLCanvasElement, touchRoot: HTMLElement) {
    this.mode = mode;
    this.canvas = canvas;
    this.touchRoot = touchRoot;
  }

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
    }
    this.buildTouchControls();
  }

  detach() {
    window.removeEventListener("keydown", this.keydownHandler);
    window.removeEventListener("keyup", this.keyupHandler);
    this.canvas.removeEventListener("mousemove", this.mouseMoveHandler);
    this.canvas.removeEventListener("mousedown", this.mouseDownHandler);
    window.removeEventListener("mouseup", this.mouseUpHandler);
    for (const n of this.touchNodes) n.remove();
    this.touchNodes = [];
  }

  getInput(): InputState {
    if (this.mode === "shooter" && this.touchShootHeld) {
      const target = this.nearestEnemyProvider();
      if (target) {
        const l = Math.hypot(target.x, target.y) || 1;
        this.state.aimX = target.x / l;
        this.state.aimY = target.y / l;
      }
      this.state.shoot = true;
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
    const wrap = document.createElement("div");
    wrap.className = "touch-controls";

    if (this.mode === "course") {
      const pad = document.createElement("div");
      pad.className = "pad";
      const flipL = this.makeTouchBtn("↺", () => (this.state.left = true), () => (this.state.left = false));
      const flipR = this.makeTouchBtn("↻", () => (this.state.right = true), () => (this.state.right = false));
      pad.append(flipL, flipR);

      const actions = document.createElement("div");
      actions.className = "actions";
      const go = this.makeTouchBtn(
        "GO",
        () => {
          this.state.up = true;
          this.state.jump = true;
        },
        () => {
          this.state.up = false;
          this.state.jump = false;
        }
      );
      go.classList.add("wide");
      actions.append(go);

      wrap.append(pad, actions);
    } else {
      const pad = document.createElement("div");
      pad.className = "pad";
      const joy = document.createElement("div");
      joy.className = "touch-btn wide";
      joy.style.width = "96px";
      joy.style.height = "96px";
      joy.style.borderRadius = "50%";
      joy.textContent = "🕹";
      pad.append(joy);
      this.attachJoystick(joy);

      const actions = document.createElement("div");
      actions.className = "actions";
      const shoot = this.makeTouchBtn(
        "🔫",
        () => (this.touchShootHeld = true),
        () => {
          this.touchShootHeld = false;
          this.state.shoot = false;
        }
      );
      actions.append(shoot);

      wrap.append(pad, actions);
    }

    this.touchRoot.appendChild(wrap);
    this.touchNodes.push(wrap);
  }

  private attachJoystick(el: HTMLElement) {
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

  private makeTouchBtn(label: string, onDown: () => void, onUp: () => void): HTMLElement {
    const btn = document.createElement("div");
    btn.className = "touch-btn";
    btn.textContent = label;
    btn.addEventListener("pointerdown", (e) => {
      e.preventDefault();
      btn.setPointerCapture(e.pointerId);
      onDown();
    });
    const release = () => onUp();
    btn.addEventListener("pointerup", release);
    btn.addEventListener("pointercancel", release);
    this.touchNodes.push(btn);
    return btn;
  }
}
