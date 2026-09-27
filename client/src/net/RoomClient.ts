import type {
  CharacterId,
  CreateRoomResponse,
  JoinRoomResponse,
  PlayerLiveState,
  RoomMeta,
  RoomSnapshotResponse,
} from '@shared/protocol';

const POLL_MS = 600;

async function post<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(path, { method: 'POST', headers: { 'content-type': 'application/json' }, body: JSON.stringify(body) });
  return res.json() as Promise<T>;
}

export class RoomClient {
  code: string | null = null;
  playerId: string | null = null;
  seed: number | null = null;
  meta: RoomMeta | null = null;
  players: PlayerLiveState[] = [];
  collectedItems: string[] = [];

  onLobbyUpdate: ((meta: RoomMeta) => void) | null = null;
  onGameStart: ((startAt: number) => void) | null = null;

  private polling = false;
  private gameStartFired = false;

  async create(name: string, character: CharacterId): Promise<{ code: string; seed: number }> {
    const res = await post<CreateRoomResponse>('/api/room/create', { name, character });
    this.code = res.code;
    this.playerId = res.playerId;
    this.seed = res.seed;
    this.gameStartFired = false;
    this.startPolling();
    return res;
  }

  async join(code: string, name: string, character: CharacterId): Promise<{ ok: boolean; error?: string; seed?: number }> {
    const res = await post<JoinRoomResponse>('/api/room/join', { code, name, character });
    if (!res.ok) return { ok: false, error: res.error };
    this.code = code;
    this.playerId = res.playerId;
    this.seed = res.seed;
    this.gameStartFired = false;
    this.startPolling();
    return { ok: true, seed: res.seed };
  }

  async setReady(ready: boolean) {
    if (!this.code || !this.playerId) return;
    await post('/api/room/ready', { code: this.code, playerId: this.playerId, ready });
  }

  async start() {
    if (!this.code || !this.playerId) return;
    await post('/api/room/start', { code: this.code, playerId: this.playerId });
  }

  async leave() {
    if (!this.code || !this.playerId) return;
    this.polling = false;
    await post('/api/room/leave', { code: this.code, playerId: this.playerId }).catch(() => {});
    this.code = null;
    this.playerId = null;
    this.meta = null;
    this.players = [];
  }

  pushState(state: Omit<PlayerLiveState, 'ts'>, collectItem?: string) {
    if (!this.code) return;
    post('/api/room/state', { code: this.code, ...state, collectItem }).catch(() => {});
  }

  private startPolling() {
    if (this.polling) return;
    this.polling = true;
    const loop = async () => {
      if (!this.polling || !this.code) return;
      try {
        const res = await fetch(`/api/room/state?code=${this.code}`);
        const data = (await res.json()) as RoomSnapshotResponse & { collectedItems: string[] };
        if (data.meta) {
          this.meta = data.meta;
          this.players = data.players;
          this.collectedItems = data.collectedItems || [];
          this.onLobbyUpdate?.(data.meta);
          if (data.meta.started && data.meta.startAt && !this.gameStartFired) {
            this.gameStartFired = true;
            this.onGameStart?.(data.meta.startAt);
          }
        }
      } catch {
        /* transient network hiccup, keep polling */
      }
      if (this.polling) setTimeout(loop, POLL_MS);
    };
    loop();
  }

  stopPolling() {
    this.polling = false;
  }
}
