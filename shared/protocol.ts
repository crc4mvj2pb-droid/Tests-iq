// Shared WebSocket protocol between client and server for Private
// multiplayer. Every message is a JSON object with a `type` discriminator.

export interface PlayerInfo {
  id: string;
  name: string;
  carId: string;
  ready: boolean;
  isHost: boolean;
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
  | { type: 'pong' };
