import type { Config } from '@netlify/functions';
import { roomStore, metaKey, json, newId, genCode } from './_lib/store';
import type { RoomMeta, CreateRoomRequest, CreateRoomResponse } from '../../shared/protocol';
import { randSeed } from '../../shared/rng';

export default async (req: Request): Promise<Response> => {
  if (req.method !== 'POST') return json(405, { error: 'method not allowed' });
  let body: CreateRoomRequest;
  try {
    body = await req.json();
  } catch {
    return json(400, { error: 'bad json' });
  }
  const name = (body.name || 'Aventurier').slice(0, 16);
  const character = body.character;
  const store = roomStore();

  let code = genCode();
  for (let i = 0; i < 5; i++) {
    const existing = await store.get(metaKey(code));
    if (!existing) break;
    code = genCode();
  }

  const playerId = newId();
  const seed = randSeed();
  const meta: RoomMeta = {
    code,
    seed,
    started: false,
    startAt: null,
    players: { [playerId]: { id: playerId, name, character, ready: false, isHost: true, summited: false } },
    updatedAt: Date.now(),
  };
  await store.setJSON(metaKey(code), meta);

  const res: CreateRoomResponse = { code, playerId, seed };
  return json(200, res);
};

export const config: Config = { path: '/api/room/create' };
