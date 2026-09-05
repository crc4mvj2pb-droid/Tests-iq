export type Cleanup = void | (() => void);
export type ScreenFn = (root: HTMLElement, nav: Navigate) => Cleanup;
export type Navigate = (screen: ScreenFn) => void;

export class Router {
  private cleanup: (() => void) | null = null;

  constructor(private root: HTMLElement) {}

  navigate: Navigate = (screen) => {
    if (this.cleanup) {
      try {
        this.cleanup();
      } catch {
        /* ignore cleanup errors */
      }
      this.cleanup = null;
    }
    this.root.innerHTML = '';
    const result = screen(this.root, this.navigate);
    if (typeof result === 'function') this.cleanup = result;
  };
}

export function el<K extends keyof HTMLElementTagNameMap>(
  tag: K,
  className?: string,
  html?: string,
): HTMLElementTagNameMap[K] {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (html !== undefined) node.innerHTML = html;
  return node;
}
