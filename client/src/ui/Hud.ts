import type { HudState } from '../core/game/HudState';
import type { Inventory } from '../core/player/Inventory';

export interface HudHandle {
  update: (hud: HudState) => void;
  toast: (message: string) => void;
  destroy: () => void;
  onExit: (cb: () => void) => void;
}

function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

function inventoryHtml(inv: Inventory): string {
  const items: string[] = [];
  if (inv.berries > 0) items.push(`<div class="inv-item"><div class="inv-icon" style="background:#c23b4a"></div>x${inv.berries}</div>`);
  if (inv.chalk > 0) items.push(`<div class="inv-item"><div class="inv-icon" style="background:#e8e2d0"></div>x${inv.chalk}</div>`);
  if (inv.anchors > 0) items.push(`<div class="inv-item"><div class="inv-icon" style="background:#caa23a"></div>x${inv.anchors}</div>`);
  if (inv.cloakEquipped) items.push(`<div class="inv-item"><div class="inv-icon" style="background:#3b6ea5"></div>manteau</div>`);
  return items.join('');
}

export function mountHud(root: HTMLElement): HudHandle {
  const el = document.createElement('div');
  el.className = 'hud';
  el.innerHTML = `
    <button class="exit-btn" id="hud-exit" style="pointer-events:all">Quitter</button>
    <div class="hud-top">
      <div class="hud-bars">
        <div class="bar-row"><span class="bar-label">❤</span><div class="bar-track"><div class="bar-fill health" id="bar-health"></div></div></div>
        <div class="bar-row"><span class="bar-label">💪</span><div class="bar-track"><div class="bar-fill stamina" id="bar-stamina"></div></div></div>
        <div class="bar-row"><span class="bar-label">🍞</span><div class="bar-track"><div class="bar-fill hunger" id="bar-hunger"></div></div></div>
        <div class="bar-row"><span class="bar-label">❄</span><div class="bar-track"><div class="bar-fill cold" id="bar-cold"></div></div></div>
      </div>
      <div class="hud-inventory" id="hud-inventory"></div>
    </div>
    <div class="hud-roster" id="hud-roster"></div>
    <div class="hud-altitude"><div class="hud-altitude-fill" id="hud-altitude-fill"></div></div>
    <div class="hud-center">
      <div class="hud-timer" id="hud-timer">0:00</div>
      <div class="hud-checkpoints" id="hud-checkpoints"></div>
    </div>
    <div class="toast-stack" id="toast-stack"></div>
    <div id="revive-slot"></div>
    <div id="downed-slot"></div>
  `;
  root.appendChild(el);

  let exitCb: (() => void) | null = null;
  el.querySelector('#hud-exit')?.addEventListener('click', () => exitCb?.());

  const barHealth = el.querySelector<HTMLElement>('#bar-health')!;
  const barStamina = el.querySelector<HTMLElement>('#bar-stamina')!;
  const barHunger = el.querySelector<HTMLElement>('#bar-hunger')!;
  const barCold = el.querySelector<HTMLElement>('#bar-cold')!;
  const inventoryEl = el.querySelector<HTMLElement>('#hud-inventory')!;
  const rosterEl = el.querySelector<HTMLElement>('#hud-roster')!;
  const altitudeFill = el.querySelector<HTMLElement>('#hud-altitude-fill')!;
  const timerEl = el.querySelector<HTMLElement>('#hud-timer')!;
  const checkpointsEl = el.querySelector<HTMLElement>('#hud-checkpoints')!;
  const toastStack = el.querySelector<HTMLElement>('#toast-stack')!;
  const reviveSlot = el.querySelector<HTMLElement>('#revive-slot')!;
  const downedSlot = el.querySelector<HTMLElement>('#downed-slot')!;

  function update(hud: HudState) {
    barHealth.style.width = `${Math.max(0, hud.health)}%`;
    barStamina.style.width = `${Math.max(0, hud.stamina)}%`;
    barHunger.style.width = `${Math.max(0, hud.hunger)}%`;
    barCold.style.width = `${Math.max(0, hud.cold)}%`;
    inventoryEl.innerHTML = inventoryHtml(hud.inventory);
    altitudeFill.style.height = `${Math.min(100, hud.altitudeFrac * 100)}%`;
    timerEl.textContent = formatTime(hud.elapsedMs);
    checkpointsEl.textContent = `Checkpoints ${hud.checkpointsCollected}/${hud.checkpointsTotal}${hud.isRaining ? ' · 🌧 pluie (prise glissante)' : ''}`;

    if (hud.remotePlayers.length > 0) {
      rosterEl.innerHTML = hud.remotePlayers
        .map(
          (p) => `
        <div class="roster-row${p.downed ? ' downed' : ''}">
          <span class="player-dot" style="background:${p.color};width:9px;height:9px;border-radius:50%;"></span>
          <span>${p.name}${p.downed ? ' (à terre)' : ''}</span>
          <div class="roster-health"><div class="roster-health-fill" style="width:${Math.max(0, p.health)}%"></div></div>
        </div>`,
        )
        .join('');
    } else {
      rosterEl.innerHTML = '';
    }

    reviveSlot.innerHTML = hud.reviveTargetId
      ? `<div class="revive-prompt">Maintiens E / le bouton ✋ pour relever ton coéquipier</div>`
      : '';

    downedSlot.innerHTML = hud.downed
      ? `<div class="downed-overlay"><span>À terre…</span><span style="font-size:1rem;font-weight:400;">Respawn dans ${Math.ceil(hud.downedTimer)}s</span></div>`
      : '';
  }

  function toast(message: string) {
    const t = document.createElement('div');
    t.className = 'toast';
    t.textContent = message;
    toastStack.appendChild(t);
    window.setTimeout(() => t.remove(), 2600);
  }

  return {
    update,
    toast,
    destroy: () => el.remove(),
    onExit: (cb) => {
      exitCb = cb;
    },
  };
}
