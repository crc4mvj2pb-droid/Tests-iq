export interface PlayerInfo {
  id: string;
  name: string;
  color: string;
  ready: boolean;
  isHost: boolean;
}

export type PlayerAnim = 'idle' | 'walk' | 'run' | 'climb' | 'air' | 'downed';

export interface PlayerStateSnapshot {
  pos: [number, number, number];
  yaw: number;
  anim: PlayerAnim;
  health: number;
  stamina: number;
  hunger: number;
}
