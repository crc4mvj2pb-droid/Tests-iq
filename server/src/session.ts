import type { WebSocket } from 'ws';
import type { ServerMessage } from '../../shared/protocol';

export interface ClientSession {
  id: string;
  ws: WebSocket;
  name: string;
  carId: string;
  roomCode: string | null;
  publicMatchId: string | null;
}

export function send(session: ClientSession, msg: ServerMessage) {
  if (session.ws.readyState === session.ws.OPEN) {
    session.ws.send(JSON.stringify(msg));
  }
}

let counter = 0;
export function newId(prefix: string): string {
  counter++;
  return `${prefix}_${Date.now().toString(36)}_${counter}`;
}
