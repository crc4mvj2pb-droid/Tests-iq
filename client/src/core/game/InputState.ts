export interface InputState {
  moveForward: number; // -1..1
  moveRight: number; // -1..1
  lookDeltaX: number; // radians accumulés depuis la dernière lecture
  lookDeltaY: number;
  jump: boolean; // front montant, consommé après lecture
  grip: boolean; // maintenu
  sprint: boolean; // maintenu
  interact: boolean; // front montant
  placeAnchor: boolean; // front montant
  useBerry: boolean; // front montant
  toggleCloak: boolean; // front montant
}

export function emptyInputState(): InputState {
  return {
    moveForward: 0,
    moveRight: 0,
    lookDeltaX: 0,
    lookDeltaY: 0,
    jump: false,
    grip: false,
    sprint: false,
    interact: false,
    placeAnchor: false,
    useBerry: false,
    toggleCloak: false,
  };
}
