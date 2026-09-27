import type { Inventory } from '../player/Inventory';
import type { PlayerAnimState } from '../player/PlayerController';

export interface RemoteHudInfo {
  id: string;
  name: string;
  color: string;
  health: number;
  downed: boolean;
}

export interface HudState {
  health: number;
  stamina: number;
  hunger: number;
  cold: number;
  altitudeFrac: number;
  inventory: Inventory;
  anim: PlayerAnimState;
  downed: boolean;
  downedTimer: number;
  elapsedMs: number;
  checkpointsCollected: number;
  checkpointsTotal: number;
  isRaining: boolean;
  remotePlayers: RemoteHudInfo[];
  reviveTargetId: string | null;
}
