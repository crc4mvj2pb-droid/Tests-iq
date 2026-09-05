export class Input {
  held = false;
  private listeners: Array<() => void> = [];

  constructor(private target: HTMLElement) {
    const press = (e: Event) => {
      e.preventDefault();
      this.held = true;
    };
    const release = (e: Event) => {
      e.preventDefault();
      this.held = false;
    };
    target.addEventListener('pointerdown', press);
    window.addEventListener('pointerup', release);
    window.addEventListener('pointercancel', release);
    const key = (e: KeyboardEvent, val: boolean) => {
      if (e.code === 'Space' || e.code === 'ArrowUp') {
        e.preventDefault();
        this.held = val;
      }
    };
    const kd = (e: KeyboardEvent) => key(e, true);
    const ku = (e: KeyboardEvent) => key(e, false);
    window.addEventListener('keydown', kd);
    window.addEventListener('keyup', ku);
    const blur = () => {
      this.held = false;
    };
    window.addEventListener('blur', blur);
    document.addEventListener('visibilitychange', blur);

    this.listeners.push(() => {
      target.removeEventListener('pointerdown', press);
      window.removeEventListener('pointerup', release);
      window.removeEventListener('pointercancel', release);
      window.removeEventListener('keydown', kd);
      window.removeEventListener('keyup', ku);
      window.removeEventListener('blur', blur);
      document.removeEventListener('visibilitychange', blur);
    });
  }

  destroy() {
    this.listeners.forEach((fn) => fn());
    this.listeners = [];
  }
}
