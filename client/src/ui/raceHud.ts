import { el } from './router';

export interface RaceDom {
  wrap: HTMLDivElement;
  canvas: HTMLCanvasElement;
  timeChip: HTMLDivElement;
  metaChip: HTMLDivElement;
  comboChip: HTMLDivElement;
  centerMsg: HTMLDivElement;
  flash: HTMLDivElement;
  throttleBtn: HTMLDivElement;
}

export function formatTime(ms: number): string {
  const totalCs = Math.floor(ms / 10);
  const m = Math.floor(totalCs / 6000);
  const s = Math.floor((totalCs % 6000) / 100);
  const cs = totalCs % 100;
  return `${m}:${s.toString().padStart(2, '0')}.${cs.toString().padStart(2, '0')}`;
}

export function buildRaceScreen(root: HTMLElement, hint: string): RaceDom {
  const wrap = el('div', 'race-wrap');
  const canvas = el('canvas');
  canvas.id = 'raceCanvas';
  wrap.appendChild(canvas);

  const hud = el('div', 'hud');
  const top = el('div', 'hud-top');
  const timeChip = el('div', 'hud-chip', '0:00.00');
  const metaChip = el('div', 'hud-chip', '');
  top.appendChild(timeChip);
  top.appendChild(metaChip);
  hud.appendChild(top);

  const comboChip = el('div', 'hud-chip hud-combo');
  comboChip.style.alignSelf = 'flex-end';
  comboChip.style.display = 'none';
  hud.appendChild(comboChip);

  const centerMsg = el('div', 'hud-center-msg');
  centerMsg.style.display = 'none';
  hud.appendChild(centerMsg);

  const flash = el('div', 'hud-flash');
  hud.appendChild(flash);

  const hintEl = el('div', 'hud-bottom-hint', hint);
  hud.appendChild(hintEl);

  const throttleBtn = el('div', 'throttle-btn');
  hud.appendChild(throttleBtn);

  wrap.appendChild(hud);
  root.appendChild(wrap);

  const resize = () => {
    canvas.width = window.innerWidth * Math.min(window.devicePixelRatio || 1, 2);
    canvas.height = window.innerHeight * Math.min(window.devicePixelRatio || 1, 2);
    canvas.style.width = '100%';
    canvas.style.height = '100%';
  };
  resize();
  window.addEventListener('resize', resize);
  (canvas as unknown as { __cleanupResize?: () => void }).__cleanupResize = () => window.removeEventListener('resize', resize);

  return { wrap, canvas, timeChip, metaChip, comboChip, centerMsg, flash, throttleBtn };
}

let flashTimer: number | undefined;
export function showFlash(dom: RaceDom, text: string, ms = 900) {
  dom.flash.textContent = text;
  dom.flash.classList.add('show');
  window.clearTimeout(flashTimer);
  flashTimer = window.setTimeout(() => dom.flash.classList.remove('show'), ms);
}

export function showCenterMsg(dom: RaceDom, text: string | null) {
  if (text === null) {
    dom.centerMsg.style.display = 'none';
    return;
  }
  dom.centerMsg.textContent = text;
  dom.centerMsg.style.display = 'block';
}
