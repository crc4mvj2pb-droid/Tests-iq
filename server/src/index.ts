import { createServer } from 'node:http';
import { WebSocketServer, type WebSocket } from 'ws';
import type { ClientMessage } from '../../shared/protocol';
import { PUBLIC_QUEUE_TIMEOUT_MS, PUBLIC_TARGET_LOBBY_SIZE } from '../../shared/constants';
import { newId, send, type ClientSession } from './session';
import { PrivateRoom } from './rooms/PrivateRoom';
import { PublicMatch } from './rooms/PublicMatch';

const PORT = Number(process.env.PORT) || 8787;

const httpServer = createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'content-type': 'application/json' });
    res.end(JSON.stringify({ ok: true, rooms: rooms.size, queue: publicQueue.length }));
    return;
  }
  res.writeHead(404);
  res.end();
});

const wss = new WebSocketServer({ server: httpServer });

const sessions = new Map<string, ClientSession>();
const rooms = new Map<string, PrivateRoom>();
const publicMatches = new Map<string, PublicMatch>();
const publicQueue: { session: ClientSession; name: string; carId: string; queuedAt: number }[] = [];

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

function matchOf(session: ClientSession): PublicMatch | undefined {
  return session.publicMatchId ? publicMatches.get(session.publicMatchId) : undefined;
}

wss.on('connection', (ws: WebSocket) => {
  const session: ClientSession = {
    id: newId('p'),
    ws,
    name: 'Pilote',
    carId: 'balanced',
    roomCode: null,
    publicMatchId: null,
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
    const match = matchOf(session);
    match?.removeSession(session.id);
    const qIdx = publicQueue.findIndex((q) => q.session.id === session.id);
    if (qIdx >= 0) publicQueue.splice(qIdx, 1);
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
      matchOf(session)?.handleFinish(session.id);
      return;
    }

    case 'race:crashedOut':
      return;

    case 'public:queue': {
      session.name = msg.name.slice(0, 20) || 'Pilote';
      session.carId = msg.carId;
      if (!publicQueue.some((q) => q.session.id === session.id)) {
        publicQueue.push({ session, name: session.name, carId: session.carId, queuedAt: Date.now() });
      }
      broadcastQueueStatus();
      return;
    }

    case 'public:leaveQueue': {
      const idx = publicQueue.findIndex((q) => q.session.id === session.id);
      if (idx >= 0) publicQueue.splice(idx, 1);
      return;
    }
  }
}

function broadcastQueueStatus() {
  publicQueue.forEach((q, i) => {
    send(q.session, { type: 'public:queued', position: i + 1, queueSize: publicQueue.length });
  });
}

function tryFormPublicMatch() {
  if (publicQueue.length === 0) return;
  const oldest = publicQueue[0];
  const waited = Date.now() - oldest.queuedAt;
  const ready = publicQueue.length >= PUBLIC_TARGET_LOBBY_SIZE || waited >= PUBLIC_QUEUE_TIMEOUT_MS;
  if (!ready) return;

  const taken = publicQueue.splice(0, PUBLIC_TARGET_LOBBY_SIZE);
  const id = newId('match');
  const match = new PublicMatch(
    id,
    taken.map((t) => ({ session: t.session, name: t.name, carId: t.carId })),
    PUBLIC_TARGET_LOBBY_SIZE,
  );
  for (const t of taken) t.session.publicMatchId = id;
  publicMatches.set(id, match);
  match.begin();
  broadcastQueueStatus();
}

setInterval(tryFormPublicMatch, 1000);

httpServer.listen(PORT, () => {
  console.log(`FlipRush server listening on :${PORT}`);
});
