import type { Config } from '@netlify/functions';
import { roomStore, metaKey, posKey, json } from './_lib/store';
import type { RoomMeta, LeaveRoomRequest } from '../../shared/protocol';

export default async (req: Request): Promise<Response> => {
  if (req.method !== 'POST') return json(405, { error: 'method not allowed' });
  let body: LeaveRoomRequest;
  try {
    body = await req.json();
  } catch {
    return json(400, { error: 'bad json' });
  }
  const store = roomStore();
  const meta = (await store.get(metaKey(body.code), { type: 'json' })) as RoomMeta | null;
  if (!meta) return json(200, { ok: true });

  const wasHost = meta.players[body.playerId]?.isHost;
  delete meta.players[body.playerId];
  await store.delete(posKey(body.code, body.playerId));

  const remaining = Object.values(meta.players);
  if (remaining.length === 0) {
    await store.delete(metaKey(body.code));
    return json(200, { ok: true });
  }
  if (wasHost) remaining[0].isHost = true;
  meta.updatedAt = Date.now();
  await store.setJSON(metaKey(body.code), meta);
  return json(200, { ok: true });
};

export const config: Config = { path: '/api/room/leave' };
