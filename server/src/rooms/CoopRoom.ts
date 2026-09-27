import type { WebSocket } from 'ws';
import type { ClientMessage, ServerMessage } from '../../../shared/protocol';
import type { PlayerInfo } from '../../../shared/types';
import { randomSeed } from '../../../shared/rng';
import { MAX_PLAYERS_PER_ROOM } from '../../../shared/constants';

export interface RoomPlayer extends PlayerInfo {
  socket: WebSocket;
}

export class CoopRoom {
  readonly code: string;
  readonly seed: number;
  players = new Map<string, RoomPlayer>();
  started = false;

  constructor(code: string) {
    this.code = code;
    this.seed = randomSeed();
  }

  private send(socket: WebSocket, msg: ServerMessage) {
    if (socket.readyState === socket.OPEN) socket.send(JSON.stringify(msg));
  }

  private broadcast(msg: ServerMessage, exceptId?: string) {
    for (const p of this.players.values()) {
      if (p.id !== exceptId) this.send(p.socket, msg);
    }
  }

  private roster(): PlayerInfo[] {
    return Array.from(this.players.values()).map(({ id, name, color, ready, isHost }) => ({
      id,
      name,
      color,
      ready,
      isHost,
    }));
  }

  join(id: string, socket: WebSocket, name: string, color: string): boolean {
    if (this.players.size >= MAX_PLAYERS_PER_ROOM || this.started) return false;
    const isHost = this.players.size === 0;
    const player: RoomPlayer = { id, socket, name: name.slice(0, 18) || 'Grimpeur', color, ready: false, isHost };
    this.players.set(id, player);
    return true;
  }

  handleJoinedNotifications(id: string, isCreator: boolean) {
    const player = this.players.get(id);
    if (!player) return;
    if (isCreator) {
      this.send(player.socket, { type: 'room_created', code: this.code, playerId: id, players: this.roster() });
    } else {
      this.send(player.socket, {
        type: 'room_joined',
        code: this.code,
        playerId: id,
        players: this.roster(),
        seed: this.seed,
      });
      this.broadcast({ type: 'player_joined', player: { id: player.id, name: player.name, color: player.color, ready: player.ready, isHost: player.isHost } }, id);
    }
  }

  leave(id: string) {
    const wasHost = this.players.get(id)?.isHost;
    this.players.delete(id);
    if (wasHost && this.players.size > 0) {
      const next = this.players.values().next().value as RoomPlayer;
      next.isHost = true;
    }
    this.broadcast({ type: 'player_left', playerId: id });
  }

  isEmpty(): boolean {
    return this.players.size === 0;
  }

  handleMessage(id: string, msg: ClientMessage) {
    const player = this.players.get(id);
    if (!player) return;

    switch (msg.type) {
      case 'set_ready':
        player.ready = msg.ready;
        this.broadcast({ type: 'ready_update', playerId: id, ready: msg.ready });
        break;
      case 'start_run':
        if (player.isHost && !this.started) {
          this.started = true;
          this.broadcast({ type: 'run_started', seed: this.seed, startAt: Date.now() + 2000 });
        }
        break;
      case 'state':
        this.broadcast({ type: 'state_update', playerId: id, s: msg.s }, id);
        break;
      case 'reached_summit':
        this.broadcast({ type: 'player_summited', playerId: id, timeMs: msg.timeMs });
        break;
      case 'downed':
        this.broadcast({ type: 'player_downed', playerId: id });
        break;
      case 'revive_request': {
        const target = this.players.get(msg.targetId);
        if (target) this.broadcast({ type: 'player_revived', playerId: target.id });
        break;
      }
      case 'leave':
        this.leave(id);
        break;
    }
  }
}
