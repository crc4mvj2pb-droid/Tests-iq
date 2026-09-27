import type { PlayerInfo, PlayerStateSnapshot } from './types';

// Messages client -> serveur
export type ClientMessage =
  | { type: 'create_room'; name: string; color: string }
  | { type: 'join_room'; code: string; name: string; color: string }
  | { type: 'set_ready'; ready: boolean }
  | { type: 'start_run' }
  | { type: 'state'; s: PlayerStateSnapshot }
  | { type: 'reached_summit'; timeMs: number }
  | { type: 'downed' }
  | { type: 'revive_request'; targetId: string }
  | { type: 'leave' };

// Messages serveur -> client
export type ServerMessage =
  | { type: 'room_created'; code: string; playerId: string; players: PlayerInfo[] }
  | { type: 'room_joined'; code: string; playerId: string; players: PlayerInfo[]; seed: number }
  | { type: 'player_joined'; player: PlayerInfo }
  | { type: 'player_left'; playerId: string }
  | { type: 'ready_update'; playerId: string; ready: boolean }
  | { type: 'run_started'; seed: number; startAt: number }
  | { type: 'state_update'; playerId: string; s: PlayerStateSnapshot }
  | { type: 'player_summited'; playerId: string; timeMs: number }
  | { type: 'player_downed'; playerId: string }
  | { type: 'player_revived'; playerId: string }
  | { type: 'error'; message: string };
