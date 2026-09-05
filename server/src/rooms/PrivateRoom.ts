import type { PlayerInfo, RoundResult } from '../../../shared/protocol';
import { COUNTDOWN_MS, ENVIRONMENTS, MAX_ROUND_DURATION_MS, PRIVATE_LEAD_MS, ROUND_TARGET_DISTANCE_M, roundPoints } from '../../../shared/constants';
import { randSeed } from '../../../shared/rng';
import { send, type ClientSession } from '../session';

interface RoomPlayer {
  session: ClientSession;
  name: string;
  carId: string;
  ready: boolean;
  isHost: boolean;
  points: number;
}

export class PrivateRoom {
  code: string;
  rounds: 3 | 5;
  players = new Map<string, RoomPlayer>();
  started = false;
  currentRound = 0;
  private roundStartAt = 0;
  private roundFinishTimes = new Map<string, number>();
  private roundTimer: NodeJS.Timeout | null = null;

  constructor(code: string, host: ClientSession, hostName: string, carId: string, rounds: 3 | 5) {
    this.code = code;
    this.rounds = rounds;
    this.players.set(host.id, { session: host, name: hostName, carId, ready: false, isHost: true, points: 0 });
  }

  private toPlayerInfo(): PlayerInfo[] {
    return [...this.players.values()].map((p) => ({
      id: p.session.id,
      name: p.name,
      carId: p.carId,
      ready: p.ready,
      isHost: p.isHost,
    }));
  }

  broadcastLobby() {
    const msg = { type: 'private:lobby' as const, code: this.code, players: this.toPlayerInfo(), rounds: this.rounds };
    for (const p of this.players.values()) send(p.session, msg);
  }

  addPlayer(session: ClientSession, name: string, carId: string) {
    this.players.set(session.id, { session, name, carId, ready: false, isHost: false, points: 0 });
    this.broadcastLobby();
  }

  removePlayer(id: string) {
    const wasHost = this.players.get(id)?.isHost;
    this.players.delete(id);
    if (wasHost && this.players.size > 0) {
      const next = this.players.values().next().value as RoomPlayer;
      next.isHost = true;
    }
    if (this.players.size > 0) this.broadcastLobby();
  }

  setReady(id: string, ready: boolean) {
    const p = this.players.get(id);
    if (p) p.ready = ready;
    this.broadcastLobby();
  }

  setCar(id: string, carId: string) {
    const p = this.players.get(id);
    if (p) p.carId = carId;
    this.broadcastLobby();
  }

  canStart(requesterId: string): boolean {
    const requester = this.players.get(requesterId);
    if (!requester?.isHost) return false;
    return [...this.players.values()].every((p) => p.ready || p.isHost);
  }

  start(requesterId: string) {
    if (!this.canStart(requesterId) || this.started) return;
    this.started = true;
    this.currentRound = 0;
    this.startRound();
  }

  private startRound() {
    this.currentRound++;
    this.roundFinishTimes.clear();
    const seed = randSeed();
    const environment = ENVIRONMENTS[Math.floor(Math.random() * ENVIRONMENTS.length)];
    this.roundStartAt = Date.now() + PRIVATE_LEAD_MS;
    const msg = {
      type: 'race:start' as const,
      round: this.currentRound,
      totalRounds: this.rounds,
      trackSeed: seed,
      environment,
      serverStartAt: this.roundStartAt,
    };
    for (const p of this.players.values()) send(p.session, msg);

    if (this.roundTimer) clearTimeout(this.roundTimer);
    this.roundTimer = setTimeout(() => this.finalizeRound(), PRIVATE_LEAD_MS + COUNTDOWN_MS + MAX_ROUND_DURATION_MS);
  }

  handleGhostState(id: string, x: number, y: number, angle: number, speed: number) {
    const msg = { type: 'race:ghost' as const, playerId: id, x, y, angle, speed };
    for (const p of this.players.values()) {
      if (p.session.id !== id) send(p.session, msg);
    }
  }

  handleFinish(id: string) {
    if (this.roundFinishTimes.has(id)) return;
    const elapsed = Math.max(0, Date.now() - (this.roundStartAt + COUNTDOWN_MS));
    this.roundFinishTimes.set(id, elapsed);
    if (this.roundFinishTimes.size >= this.players.size) {
      if (this.roundTimer) clearTimeout(this.roundTimer);
      this.finalizeRound();
    }
  }

  private finalizeRound() {
    const ranked = [...this.players.values()]
      .map((p) => ({ p, time: this.roundFinishTimes.get(p.session.id) ?? null }))
      .sort((a, b) => (a.time ?? Infinity) - (b.time ?? Infinity));

    const results: RoundResult[] = ranked.map((r, i) => {
      const pts = r.time !== null ? roundPoints(i + 1) : 0;
      r.p.points += pts;
      return { playerId: r.p.session.id, name: r.p.name, timeMs: r.time, points: pts };
    });

    const standings: RoundResult[] = [...this.players.values()]
      .map((p) => ({ playerId: p.session.id, name: p.name, timeMs: null, points: p.points }))
      .sort((a, b) => b.points - a.points);

    const msg = { type: 'race:roundResult' as const, round: this.currentRound, results, standings };
    for (const p of this.players.values()) send(p.session, msg);

    if (this.currentRound >= this.rounds) {
      setTimeout(() => {
        const overMsg = { type: 'race:matchOver' as const, standings };
        for (const p of this.players.values()) send(p.session, overMsg);
        this.started = false;
        for (const p of this.players.values()) p.ready = false;
      }, 1500);
    } else {
      setTimeout(() => this.startRound(), 4000);
    }
  }
}
