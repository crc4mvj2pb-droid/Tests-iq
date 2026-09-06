import { createServer } from 'node:http';
import { WebSocketServer, type WebSocket } from 'ws';
import type { ClientMessage } from '../../shared/protocol';
import { newId, send, type ClientSession } from './session';
import { PrivateRoom } from './rooms/PrivateRoom';

const PORT = Number(process.env.PORT) || 8787;

const httpServer = createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ ok: true, rooms: rooms.size }));
    return;
  }
  res.writeHead(404);
  res.end();
});

const wss = new WebSocketServer({ server: httpServer });

const sessions = new Map<string, ClientSession>();
const rooms = new Map<string, PrivateRoom>();

function generateRoomCode(): string {
  let code: string;
  do {
    code = String(Math.floor(1000 + Math.random() * 9000));
  } while (rooms.has(code));
  return code;
}

function roomOf(session: ClientSession): PrivateRoom | undefined {
  return session.roomCode ? rooms.get(session.roomCode) : undefined;
}

wss.on('connection', (ws: WebSocket) => {
  const session: ClientSession = {
    id: newId('p'),
    ws,
    name: 'Pilote',
    carId: 'balanced',
    roomCode: null,
  };
  sessions.set(session.id, session);

  ws.on('message', (raw) => {
    let msg: ClientMessage;
    try {
      msg = JSON.parse(raw.toString());
    } catch {
      return;
    }
    handleMessage(session, msg);
  });

  ws.on('close', () => {
    const room = roomOf(session);
    if (room) {
      room.removePlayer(session.id);
      if (room.players.size === 0) rooms.delete(room.code);
    }
    sessions.delete(session.id);
  });
});

function handleMessage(session: ClientSession, msg: ClientMessage) {
  switch (msg.type) {
    case 'ping':
      send(session, { type: 'pong' });
      return;

    case 'private:create': {
      session.name = msg.name.slice(0, 20) || 'Pilote';
      session.carId = msg.carId;
      const code = generateRoomCode();
      const room = new PrivateRoom(code, session, session.name, session.carId, msg.rounds);
      rooms.set(code, room);
      session.roomCode = code;
      send(session, { type: 'private:created', code, roomId: code, you: session.id });
      room.broadcastLobby();
      return;
    }

    case 'private:join': {
      const room = rooms.get(msg.code.trim());
      if (!room) {
        send(session, { type: 'private:error', message: "Code de partie introuvable." });
        return;
      }
      if (room.started) {
        send(session, { type: 'private:error', message: 'Cette partie a déjà commencé.' });
        return;
      }
      session.name = msg.name.slice(0, 20) || 'Pilote';
      session.carId = msg.carId;
      session.roomCode = room.code;
      room.addPlayer(session, session.name, session.carId);
      send(session, { type: 'private:joined', roomId: room.code, you: session.id });
      return;
    }

    case 'private:setReady': {
      roomOf(session)?.setReady(session.id, msg.ready);
      return;
    }

    case 'private:setCar': {
      session.carId = msg.carId;
      roomOf(session)?.setCar(session.id, msg.carId);
      return;
    }

    case 'private:start': {
      roomOf(session)?.start(session.id);
      return;
    }

    case 'race:state': {
      roomOf(session)?.handleGhostState(session.id, msg.x, msg.y, msg.angle, msg.speed);
      return;
    }

    case 'race:finish': {
      roomOf(session)?.handleFinish(session.id);
      return;
    }
  }
}

httpServer.listen(PORT, () => {
  console.log(`FlipRush server listening on :${PORT}`);
});
