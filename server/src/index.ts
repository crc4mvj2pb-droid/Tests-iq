import { WebSocketServer, type WebSocket } from 'ws';
import { randomUUID } from 'node:crypto';
import type { ClientMessage } from '../../shared/protocol';
import { DEFAULT_PORT } from '../../shared/constants';
import { CoopRoom } from './rooms/CoopRoom';

const PORT = Number(process.env.PORT) || DEFAULT_PORT;

const rooms = new Map<string, CoopRoom>();
const connections = new Map<string, { socket: WebSocket; roomCode: string | null }>();

function generateCode(): string {
  let code: string;
  do {
    code = String(Math.floor(1000 + Math.random() * 9000));
  } while (rooms.has(code));
  return code;
}

function sendError(socket: WebSocket, message: string) {
  socket.send(JSON.stringify({ type: 'error', message }));
}

const wss = new WebSocketServer({ port: PORT });
console.log(`[talus-server] WebSocket en écoute sur le port ${PORT}`);

wss.on('connection', (socket: WebSocket) => {
  const id = randomUUID();
  connections.set(id, { socket, roomCode: null });

  socket.on('message', (raw) => {
    let msg: ClientMessage;
    try {
      msg = JSON.parse(raw.toString());
    } catch {
      return;
    }

    const conn = connections.get(id);
    if (!conn) return;

    if (msg.type === 'create_room') {
      const code = generateCode();
      const room = new CoopRoom(code);
      rooms.set(code, room);
      room.join(id, socket, msg.name, msg.color);
      conn.roomCode = code;
      room.handleJoinedNotifications(id, true);
      return;
    }

    if (msg.type === 'join_room') {
      const room = rooms.get(msg.code.trim());
      if (!room) {
        sendError(socket, "Salon introuvable. Vérifie le code à 4 chiffres.");
        return;
      }
      const ok = room.join(id, socket, msg.name, msg.color);
      if (!ok) {
        sendError(socket, 'Ce salon est complet ou la partie a déjà commencé.');
        return;
      }
      conn.roomCode = room.code;
      room.handleJoinedNotifications(id, false);
      return;
    }

    if (conn.roomCode) {
      const room = rooms.get(conn.roomCode);
      room?.handleMessage(id, msg);
      if (msg.type === 'leave') {
        conn.roomCode = null;
        if (room && room.isEmpty()) rooms.delete(room.code);
      }
    }
  });

  socket.on('close', () => {
    const conn = connections.get(id);
    if (conn?.roomCode) {
      const room = rooms.get(conn.roomCode);
      room?.leave(id);
      if (room && room.isEmpty()) rooms.delete(room.code);
    }
    connections.delete(id);
  });
});
