import type { Config } from '@netlify/functions';
import { roomStore, metaKey, json } from './_lib/store';
import type { RoomMeta, SetReadyRequest } from '../../shared/protocol';

export default async (req: Request): Promise<Response> => {
  if (req.method !== 'POST') return json(405, { error: 'method not allowed' });
  let body: SetReadyRequest;
  try {
    body = await req.json();
  } catch {
    return json(400, { error: 'bad json' });
  }
  const store = roomStore();
  const meta = (await store.get(metaKey(body.code), { type: 'json' })) as RoomMeta | null;
  if (!meta || !meta.players[body.playerId]) return json(404, { error: 'not found' });
  meta.players[body.playerId].ready = body.ready;
  meta.updatedAt = Date.now();
  await store.setJSON(metaKey(body.code), meta);
  return json(200, { ok: true });
};

export const config: Config = { path: '/api/room/ready' };
