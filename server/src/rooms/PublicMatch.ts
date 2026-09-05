import type { RoundResult } from '../../../shared/protocol';
import { COUNTDOWN_MS, ENVIRONMENTS, PRIVATE_LEAD_MS, PUBLIC_ROUND_DISTANCE_M, roundPoints } from '../../../shared/constants';
import { randSeed } from '../../../shared/rng';
import { send, type ClientSession } from '../session';
import { botProgressAt, randomTier, simulateBotRace, type BotRaceProfile, type BotTier } from '../bots/BotSimulator';

const HEAT_TIMEOUT_MS = 70_000;
const BOT_NAMES = [
  'Raye', 'Kestrel', 'Vox', 'Nyra', 'Dash', 'Orin', 'Pixel', 'Zeno', 'Quill', 'Juno',
  'Talon', 'Echo', 'Wren', 'Kite', 'Sable', 'Nix', 'Vega', 'Ryo', 'Ashen', 'Blaze',
];

interface RealParticipant {
  session: ClientSession;
  name: string;
  carId: string;
  eliminated: boolean;
}

interface BotParticipant {
  id: string;
  name: string;
  tier: BotTier;
  eliminated: boolean;
}

export class PublicMatch {
  id: string;
  private real: RealParticipant[];
  private bots: BotParticipant[] = [];
  private heatIndex = 0;
  private finishTimes = new Map<string, number>();
  private botProfiles = new Map<string, BotRaceProfile>();
  private heatStartAt = 0;
  private heatTimer: NodeJS.Timeout | null = null;
  private ghostBroadcast: NodeJS.Timeout | null = null;
  private points = new Map<string, number>();

  constructor(id: string, realPlayers: { session: ClientSession; name: string; carId: string }[], targetTotal: number) {
    this.id = id;
    this.real = realPlayers.map((r) => ({ ...r, eliminated: false }));
    const botCount = Math.max(0, targetTotal - this.real.length);
    for (let i = 0; i < botCount; i++) {
      this.bots.push({ id: `bot_${id}_${i}`, name: pickBotName(i), tier: randomTier(), eliminated: false });
    }
    for (const p of [...this.real.map((r) => r.session.id), ...this.bots.map((b) => b.id)]) this.points.set(p, 0);
  }

  private activeReal() {
    return this.real.filter((r) => !r.eliminated);
  }
  private activeBots() {
    return this.bots.filter((b) => !b.eliminated);
  }
  private totalActive() {
    return this.activeReal().length + this.activeBots().length;
  }

  begin() {
    const info = [
      ...this.real.map((r) => ({ id: r.session.id, name: r.name, carId: r.carId, ready: true, isHost: false })),
      ...this.bots.map((b) => ({ id: b.id, name: b.name, carId: 'balanced', ready: true, isHost: false, isBot: true, botTier: b.tier })),
    ];
    for (const r of this.real) {
      send(r.session, { type: 'public:matchFound', matchId: this.id, you: r.session.id, totalPlayers: info.length, players: info });
    }
    setTimeout(() => this.runHeat(), 1200);
  }

  private qualifyCount(remaining: number): number {
    if (remaining <= 4) return 1; // this heat is the final
    if (remaining <= 12) return Math.max(3, Math.ceil(remaining / 4));
    return Math.ceil(remaining / 2);
  }

  private runHeat() {
    this.heatIndex++;
    this.finishTimes.clear();
    this.botProfiles.clear();
    const remaining = this.totalActive();
    const qualifying = this.qualifyCount(remaining);
    const isFinal = qualifying <= 1 || remaining <= 1;

    const seed = randSeed();
    const environment = ENVIRONMENTS[Math.floor(Math.random() * ENVIRONMENTS.length)];
    this.heatStartAt = Date.now() + PRIVATE_LEAD_MS;

    for (const b of this.activeBots()) {
      this.botProfiles.set(b.id, simulateBotRace(b.tier, PUBLIC_ROUND_DISTANCE_M));
    }

    const msg = {
      type: 'public:heatStart' as const,
      heat: this.heatIndex,
      totalHeats: -1,
      qualifying,
      trackSeed: seed,
      environment,
      serverStartAt: this.heatStartAt,
    };
    for (const r of this.activeReal()) send(r.session, msg);

    this.ghostBroadcast = setInterval(() => this.broadcastBotGhosts(), 150);
    this.heatTimer = setTimeout(() => this.finalizeHeat(isFinal), PRIVATE_LEAD_MS + COUNTDOWN_MS + HEAT_TIMEOUT_MS);
  }

  private broadcastBotGhosts() {
    const elapsed = Date.now() - (this.heatStartAt + COUNTDOWN_MS);
    if (elapsed < 0) return;
    for (const [id, profile] of this.botProfiles) {
      const frac = botProgressAt(profile, elapsed);
      const msg = { type: 'race:ghost' as const, playerId: id, x: frac * PUBLIC_ROUND_DISTANCE_M * 22, y: 0, angle: 0, speed: 0 };
      for (const r of this.activeReal()) send(r.session, msg);
    }
  }

  handleFinish(sessionId: string) {
    if (this.finishTimes.has(sessionId)) return;
    const elapsed = Math.max(0, Date.now() - (this.heatStartAt + COUNTDOWN_MS));
    this.finishTimes.set(sessionId, elapsed);
    if (this.finishTimes.size >= this.activeReal().length && this.botProfiles.size === this.activeBots().length) {
      this.tryEarlyFinish();
    }
  }

  private tryEarlyFinish() {
    // All real players in this heat have finished; bots already have
    // predetermined times, so we can resolve without waiting for the timeout.
    if (this.heatTimer) {
      clearTimeout(this.heatTimer);
      const remaining = this.totalActive();
      const qualifying = this.qualifyCount(remaining);
      const isFinal = qualifying <= 1 || remaining <= 1;
      this.finalizeHeat(isFinal);
    }
  }

  private finalizeHeat(isFinal: boolean) {
    if (this.ghostBroadcast) clearInterval(this.ghostBroadcast);
    const activeReal = this.activeReal();
    const activeBots = this.activeBots();
    const realResults = activeReal.map((r) => ({
      id: r.session.id,
      name: r.name,
      time: this.finishTimes.get(r.session.id) ?? null,
    }));
    const botResults = activeBots.map((b) => {
      const prof = this.botProfiles.get(b.id)!;
      return { id: b.id, name: b.name, time: prof.finishTimeMs };
    });
    const all = [...realResults, ...botResults].sort((a, b) => (a.time ?? Infinity) - (b.time ?? Infinity));

    const remaining = this.totalActive();
    const qualifyN = isFinal ? 1 : this.qualifyCount(remaining);
    const qualifiedIds = all.slice(0, qualifyN).map((a) => a.id);
    const eliminatedIds = all.slice(qualifyN).map((a) => a.id);

    all.forEach((a, i) => {
      const pts = roundPoints(i + 1);
      this.points.set(a.id, (this.points.get(a.id) ?? 0) + pts);
    });

    for (const r of this.real) if (eliminatedIds.includes(r.session.id)) r.eliminated = true;
    for (const b of this.bots) if (eliminatedIds.includes(b.id)) b.eliminated = true;

    const results: RoundResult[] = all.map((a, i) => ({ playerId: a.id, name: a.name, timeMs: a.time, points: roundPoints(i + 1) }));
    const heatMsg = { type: 'public:heatResult' as const, heat: this.heatIndex, results, qualifiedIds, eliminatedIds };
    for (const r of this.real) send(r.session, heatMsg);

    if (isFinal || this.totalActive() <= 1) {
      const winner = all[0];
      const standings: RoundResult[] = [...this.points.entries()]
        .map(([id, pts]) => ({ playerId: id, name: this.nameOf(id), timeMs: null, points: pts }))
        .sort((a, b) => b.points - a.points);
      setTimeout(() => {
        const overMsg = { type: 'public:matchOver' as const, winnerId: winner.id, winnerName: winner.name, standings };
        for (const r of this.real) send(r.session, overMsg);
      }, 1500);
    } else {
      setTimeout(() => this.runHeat(), 4500);
    }
  }

  private nameOf(id: string): string {
    return this.real.find((r) => r.session.id === id)?.name ?? this.bots.find((b) => b.id === id)?.name ?? id;
  }

  removeSession(id: string) {
    const r = this.real.find((x) => x.session.id === id);
    if (r) r.eliminated = true;
  }
}

function pickBotName(i: number): string {
  return BOT_NAMES[i % BOT_NAMES.length] + (i >= BOT_NAMES.length ? `-${Math.floor(i / BOT_NAMES.length) + 1}` : '');
}
