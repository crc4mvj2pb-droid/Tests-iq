import type { ItemId } from './items';

export const HOTBAR_SIZE = 4;

export class Inventory {
  slots: (ItemId | null)[] = new Array(HOTBAR_SIZE).fill(null);
  selected = 0;

  add(itemId: ItemId): boolean {
    const free = this.slots.findIndex((s) => s === null);
    if (free === -1) return false;
    this.slots[free] = itemId;
    return true;
  }

  select(index: number) {
    if (index >= 0 && index < HOTBAR_SIZE) this.selected = index;
  }

  cycle(dir: number) {
    this.selected = (this.selected + dir + HOTBAR_SIZE) % HOTBAR_SIZE;
  }

  consumeSelected(): ItemId | null {
    const id = this.slots[this.selected];
    if (id) this.slots[this.selected] = null;
    return id;
  }

  isFull(): boolean {
    return this.slots.every((s) => s !== null);
  }
}
