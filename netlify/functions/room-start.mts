import type { Config } from '@netlify/functions';
import { roomStore, metaKey, json } from './_lib/store';
import type { RoomMeta, StartRoomRequest } from '../../shared/protocol';

export default async (req: Request): Promise<Response> => {
  if (req.method !== 'POST') return json(405, { error: 'method not allowed' });
  let body: StartRoomRequest;
  try {
    body = await req.json();
  } catch {
    return json(400, { error: 'bad json' });
  }
  const store = roomStore();
  const meta = (await store.get(metaKey(body.code), { type: 'json' })) as RoomMeta | null;
  if (!meta) return json(404, { error: 'not found' });
  const player = meta.players[body.playerId];
  if (!player?.isHost) return json(403, { error: 'only the host can start' });
  if (!meta.started) {
    meta.started = true;
    meta.startAt = Date.now() + 2500;
    meta.updatedAt = Date.now();
    await store.setJSON(metaKey(body.code), meta);
  }
  return json(200, { ok: true, startAt: meta.startAt });
};

export const config: Config = { path: '/api/room/start' };
