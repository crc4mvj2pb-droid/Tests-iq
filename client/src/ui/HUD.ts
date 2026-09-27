import { ITEM_DEFS, ItemId } from '../items/items';
import { HOTBAR_SIZE } from '../items/Inventory';

export interface NametagEntry {
  id: string;
  name: string;
  screen: { x: number; y: number } | null;
}

export class HUD {
  private root: HTMLElement;
  private staminaFill: HTMLElement;
  private healthFill: HTMLElement;
  private altitudeText: HTMLElement;
  private compass: HTMLElement;
  private roomPill: HTMLElement;
  private hotbarEl: HTMLElement;
  private slotEls: HTMLElement[] = [];
  private toastStack: HTMLElement;
  private nametagLayer: HTMLElement;
  private nametagEls = new Map<string, HTMLElement>();
  private promptEl: HTMLElement;

  onHotbarTap: ((index: number) => void) | null = null;

  constructor(container: HTMLElement) {
    this.root = document.createElement('div');
    this.root.id = 'hud';
    this.root.className = 'hidden';
    container.appendChild(this.root);

    const topLeft = document.createElement('div');
    topLeft.className = 'hud-top-left';
    this.staminaFill = document.createElement('div');
    this.staminaFill.className = 'bar-fill stamina';
    const staminaWrap = document.createElement('div');
    staminaWrap.className = 'bar-wrap';
    staminaWrap.appendChild(this.staminaFill);
    this.healthFill = document.createElement('div');
    this.healthFill.className = 'bar-fill health';
    const healthWrap = document.createElement('div');
    healthWrap.className = 'bar-wrap';
    healthWrap.appendChild(this.healthFill);
    topLeft.appendChild(staminaWrap);
    topLeft.appendChild(healthWrap);
    this.root.appendChild(topLeft);

    const topRight = document.createElement('div');
    topRight.className = 'hud-top-right';
    this.altitudeText = document.createElement('div');
    this.altitudeText.className = 'altitude-pill';
    this.compass = document.createElement('div');
    this.compass.className = 'altitude-pill';
    this.roomPill = document.createElement('div');
    this.roomPill.className = 'room-pill';
    topRight.appendChild(this.altitudeText);
    topRight.appendChild(this.compass);
    topRight.appendChild(this.roomPill);
    this.root.appendChild(topRight);

    this.hotbarEl = document.createElement('div');
    this.hotbarEl.className = 'hotbar interactive';
    for (let i = 0; i < HOTBAR_SIZE; i++) {
      const slot = document.createElement('div');
      slot.className = 'hotbar-slot empty';
      const key = document.createElement('span');
      key.className = 'key';
      key.textContent = String(i + 1);
      slot.appendChild(key);
      slot.addEventListener('pointerdown', (e) => {
        e.preventDefault();
        this.onHotbarTap?.(i);
      });
      this.hotbarEl.appendChild(slot);
      this.slotEls.push(slot);
    }
    this.root.appendChild(this.hotbarEl);

    this.promptEl = document.createElement('div');
    this.promptEl.className = 'prompt';
    this.promptEl.style.display = 'none';
    this.root.appendChild(this.promptEl);

    this.toastStack = document.createElement('div');
    this.toastStack.className = 'toast-stack';
    this.root.appendChild(this.toastStack);

    this.nametagLayer = document.createElement('div');
    this.root.appendChild(this.nametagLayer);
  }

  show() {
    this.root.classList.remove('hidden');
  }

  hide() {
    this.root.classList.add('hidden');
  }

  setStamina(pct: number) {
    this.staminaFill.style.width = `${Math.max(0, Math.min(100, pct))}%`;
  }

  setHealth(pct: number) {
    this.healthFill.style.width = `${Math.max(0, Math.min(100, pct))}%`;
  }

  setAltitude(pct: number) {
    this.altitudeText.textContent = `⛰ ${Math.round(pct)}%`;
  }

  setCompass(angleFromCameraRad: number) {
    const deg = (angleFromCameraRad * 180) / Math.PI;
    this.compass.textContent = '⬆';
    this.compass.style.transform = `rotate(${deg}deg)`;
  }

  setRoomCode(code: string | null) {
    this.roomPill.textContent = code ? `Partie ${code}` : '';
    this.roomPill.style.display = code ? 'block' : 'none';
  }

  setHotbar(slots: (ItemId | null)[], selected: number) {
    slots.forEach((id, i) => {
      const el = this.slotEls[i];
      el.classList.toggle('selected', i === selected);
      el.classList.toggle('empty', id === null);
      const icon = id ? ITEM_DEFS[id].icon : '';
      el.innerHTML = `<span class="key">${i + 1}</span>${icon}`;
    });
  }

  setPrompt(text: string | null) {
    this.promptEl.style.display = text ? 'block' : 'none';
    this.promptEl.textContent = text ?? '';
  }

  toast(message: string, ms = 2600) {
    const el = document.createElement('div');
    el.className = 'toast';
    el.textContent = message;
    this.toastStack.appendChild(el);
    setTimeout(() => el.remove(), ms);
  }

  updateNametags(entries: NametagEntry[]) {
    const seen = new Set<string>();
    for (const e of entries) {
      seen.add(e.id);
      let el = this.nametagEls.get(e.id);
      if (!el) {
        el = document.createElement('div');
        el.className = 'nametag';
        this.nametagLayer.appendChild(el);
        this.nametagEls.set(e.id, el);
      }
      if (!e.screen) {
        el.style.display = 'none';
        continue;
      }
      el.style.display = 'block';
      el.style.left = `${e.screen.x}px`;
      el.style.top = `${e.screen.y}px`;
      el.textContent = e.name;
    }
    for (const [id, el] of this.nametagEls) {
      if (!seen.has(id)) {
        el.remove();
        this.nametagEls.delete(id);
      }
    }
  }
}
