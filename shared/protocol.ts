// HTTP protocol between the client and the Netlify Functions that back
// multiplayer rooms. There is no persistent server: clients poll these
// endpoints every ~500ms and Netlify Blobs hold the room/player state.

export const CHARACTER_IDS = ['marmotte', 'corbeau', 'renard', 'chevre', 'ourson', 'lynx'] as const;
export type CharacterId = (typeof CHARACTER_IDS)[number];

export type AnimState = 'idle' | 'walk' | 'run' | 'jump' | 'climb' | 'fall' | 'tumble';

export interface PlayerMeta {
  id: string;
  name: string;
  character: CharacterId;
  ready: boolean;
  isHost: boolean;
  summited: boolean;
}

export interface RoomMeta {
  code: string;
  seed: number;
  started: boolean;
  startAt: number | null;
  players: Record<string, PlayerMeta>;
  updatedAt: number;
}

export interface PlayerLiveState {
  id: string;
  name: string;
  character: CharacterId;
  x: number;
  y: number;
  z: number;
  ry: number;
  anim: AnimState;
  stamina: number;
  health: number;
  altitudePct: number;
  holding: string | null;
  flareUntil: number;
  ts: number;
}

export interface CreateRoomRequest {
  name: string;
  character: CharacterId;
}
export interface CreateRoomResponse {
  code: string;
  playerId: string;
  seed: number;
}

export interface JoinRoomRequest {
  code: string;
  name: string;
  character: CharacterId;
}
export type JoinRoomResponse = { ok: true; playerId: string; seed: number } | { ok: false; error: string };

export interface RoomSnapshotResponse {
  meta: RoomMeta | null;
  players: PlayerLiveState[];
}

export interface SetReadyRequest {
  code: string;
  playerId: string;
  ready: boolean;
}

export interface StartRoomRequest {
  code: string;
  playerId: string;
}

export interface PushStateRequest extends Omit<PlayerLiveState, 'ts'> {
  code: string;
}

export interface LeaveRoomRequest {
  code: string;
  playerId: string;
}

export const ROOM_STALE_MS = 12_000;
