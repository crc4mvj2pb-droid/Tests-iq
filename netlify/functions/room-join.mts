import type { Config } from '@netlify/functions';
import { roomStore, metaKey, json, newId } from './_lib/store';
import type { RoomMeta, JoinRoomRequest, JoinRoomResponse } from '../../shared/protocol';

export default async (req: Request): Promise<Response> => {
  if (req.method !== 'POST') return json(405, { error: 'method not allowed' });
  let body: JoinRoomRequest;
  try {
    body = await req.json();
  } catch {
    return json(400, { error: 'bad json' });
  }
  const code = (body.code || '').trim();
  const store = roomStore();
  const meta = (await store.get(metaKey(code), { type: 'json' })) as RoomMeta | null;

  if (!meta) {
    const res: JoinRoomResponse = { ok: false, error: 'Code de partie introuvable.' };
    return json(200, res);
  }
  if (meta.started) {
    const res: JoinRoomResponse = { ok: false, error: "Cette ascension a déjà commencé." };
    return json(200, res);
  }
  if (Object.keys(meta.players).length >= 6) {
    const res: JoinRoomResponse = { ok: false, error: 'Cette partie est complète (6 max).' };
    return json(200, res);
  }

  const playerId = newId();
  meta.players[playerId] = {
    id: playerId,
    name: (body.name || 'Aventurier').slice(0, 16),
    character: body.character,
    ready: false,
    isHost: false,
    summited: false,
  };
  meta.updatedAt = Date.now();
  await store.setJSON(metaKey(code), meta);

  const res: JoinRoomResponse = { ok: true, playerId, seed: meta.seed };
  return json(200, res);
};

export const config: Config = { path: '/api/room/join' };
