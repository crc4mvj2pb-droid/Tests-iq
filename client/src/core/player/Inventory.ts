export interface Inventory {
  berries: number;
  chalk: number;
  anchors: number;
  cloakEquipped: boolean;
}

export function emptyInventory(): Inventory {
  return { berries: 0, chalk: 0, anchors: 0, cloakEquipped: false };
}
