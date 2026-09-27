import type { ClientMessage, ServerMessage } from '../../../shared/protocol';
import type { PlayerInfo, PlayerStateSnapshot } from '../../../shared/types';

export interface NetCallbacks {
  onRoomCreated?: (code: string, playerId: string, players: PlayerInfo[]) => void;
  onRoomJoined?: (code: string, playerId: string, players: PlayerInfo[], seed: number) => void;
  onPlayerJoined?: (player: PlayerInfo) => void;
  onPlayerLeft?: (playerId: string) => void;
  onReadyUpdate?: (playerId: string, ready: boolean) => void;
  onRunStarted?: (seed: number, startAt: number) => void;
  onStateUpdate?: (playerId: string, s: PlayerStateSnapshot) => void;
  onPlayerSummited?: (playerId: string, timeMs: number) => void;
  onPlayerDowned?: (playerId: string) => void;
  onPlayerRevived?: (playerId: string) => void;
  onError?: (message: string) => void;
  onDisconnected?: () => void;
}

function resolveServerUrl(): string {
  const configured = import.meta.env.VITE_SERVER_URL;
  if (configured) return configured;
  const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
  return `${proto}://${window.location.hostname}:8787`;
}

export class NetClient {
  private ws: WebSocket | null = null;
  localId = '';
  code = '';
  players: PlayerInfo[] = [];

  constructor(public callbacks: NetCallbacks) {}

  connect(): Promise<void> {
    return new Promise((resolve, reject) => {
      const ws = new WebSocket(resolveServerUrl());
      this.ws = ws;
      ws.onopen = () => resolve();
      ws.onerror = () => reject(new Error('Connexion au serveur impossible'));
      ws.onclose = () => this.callbacks.onDisconnected?.();
      ws.onmessage = (ev) => this.handleMessage(JSON.parse(ev.data as string));
    });
  }

  private handleMessage(msg: ServerMessage) {
    switch (msg.type) {
      case 'room_created':
        this.localId = msg.playerId;
        this.code = msg.code;
        this.players = msg.players;
        this.callbacks.onRoomCreated?.(msg.code, msg.playerId, msg.players);
        break;
      case 'room_joined':
        this.localId = msg.playerId;
        this.code = msg.code;
        this.players = msg.players;
        this.callbacks.onRoomJoined?.(msg.code, msg.playerId, msg.players, msg.seed);
        break;
      case 'player_joined':
        this.players.push(msg.player);
        this.callbacks.onPlayerJoined?.(msg.player);
        break;
      case 'player_left':
        this.players = this.players.filter((p) => p.id !== msg.playerId);
        this.callbacks.onPlayerLeft?.(msg.playerId);
        break;
      case 'ready_update':
        this.callbacks.onReadyUpdate?.(msg.playerId, msg.ready);
        break;
      case 'run_started':
        this.callbacks.onRunStarted?.(msg.seed, msg.startAt);
        break;
      case 'state_update':
        this.callbacks.onStateUpdate?.(msg.playerId, msg.s);
        break;
      case 'player_summited':
        this.callbacks.onPlayerSummited?.(msg.playerId, msg.timeMs);
        break;
      case 'player_downed':
        this.callbacks.onPlayerDowned?.(msg.playerId);
        break;
      case 'player_revived':
        this.callbacks.onPlayerRevived?.(msg.playerId);
        break;
      case 'error':
        this.callbacks.onError?.(msg.message);
        break;
    }
  }

  private send(msg: ClientMessage) {
    if (this.ws && this.ws.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify(msg));
    }
  }

  createRoom(name: string, color: string) {
    this.send({ type: 'create_room', name, color });
  }
  joinRoom(code: string, name: string, color: string) {
    this.send({ type: 'join_room', code, name, color });
  }
  setReady(ready: boolean) {
    this.send({ type: 'set_ready', ready });
  }
  startRun() {
    this.send({ type: 'start_run' });
  }
  sendState(s: PlayerStateSnapshot) {
    this.send({ type: 'state', s });
  }
  sendSummit(timeMs: number) {
    this.send({ type: 'reached_summit', timeMs });
  }
  sendDowned() {
    this.send({ type: 'downed' });
  }
  sendRevive(targetId: string) {
    this.send({ type: 'revive_request', targetId });
  }
  leave() {
    this.send({ type: 'leave' });
    this.ws?.close();
  }
}
