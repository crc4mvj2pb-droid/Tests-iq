// Shared WebSocket protocol between client and server for Private and Public
// multiplayer. Every message is a JSON object with a `type` discriminator.

export type CarStats = {
  id: string;
};

export interface PlayerInfo {
  id: string;
  name: string;
  carId: string;
  ready: boolean;
  isHost: boolean;
  isBot?: boolean;
  botTier?: 'easy' | 'normal' | 'hard' | 'expert';
}

export interface RoundResult {
  playerId: string;
  name: string;
  timeMs: number | null; // null = DNF / crashed out permanently
  points: number;
}

// ---------- Client -> Server ----------

export type ClientMessage =
  | { type: 'private:create'; name: string; carId: string; rounds: 3 | 5 }
  | { type: 'private:join'; code: string; name: string; carId: string }
  | { type: 'private:setReady'; ready: boolean }
  | { type: 'private:setCar'; carId: string }
  | { type: 'private:start' }
  | { type: 'race:state'; x: number; y: number; angle: number; speed: number }
  | { type: 'race:finish' }
  | { type: 'race:crashedOut' }
  | { type: 'public:queue'; name: string; carId: string }
  | { type: 'public:leaveQueue' }
  | { type: 'ping' };

// ---------- Server -> Client ----------

export type ServerMessage =
  | { type: 'private:created'; code: string; roomId: string; you: string }
  | { type: 'private:joined'; roomId: string; you: string }
  | { type: 'private:error'; message: string }
  | { type: 'private:lobby'; code: string; players: PlayerInfo[]; rounds: number }
  | {
      type: 'race:start';
      round: number;
      totalRounds: number;
      trackSeed: number;
      environment: string;
      serverStartAt: number; // epoch ms, all clients start the countdown from this
    }
  | { type: 'race:ghost'; playerId: string; x: number; y: number; angle: number; speed: number }
  | { type: 'race:roundResult'; round: number; results: RoundResult[]; standings: RoundResult[] }
  | { type: 'race:matchOver'; standings: RoundResult[] }
  | { type: 'public:queued'; position: number; queueSize: number }
  | {
      type: 'public:matchFound';
      matchId: string;
      you: string;
      totalPlayers: number;
      players: PlayerInfo[];
    }
  | {
      type: 'public:heatStart';
      heat: number;
      totalHeats: number;
      qualifying: number;
      trackSeed: number;
      environment: string;
      serverStartAt: number;
    }
  | {
      type: 'public:heatResult';
      heat: number;
      results: RoundResult[];
      qualifiedIds: string[];
      eliminatedIds: string[];
    }
  | { type: 'public:matchOver'; winnerId: string; winnerName: string; standings: RoundResult[] }
  | { type: 'pong' };
