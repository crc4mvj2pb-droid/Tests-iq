import type { Config } from '@netlify/functions';
import { roomStore, metaKey, posKey, itemsKey, json } from './_lib/store';
import type { RoomMeta, PlayerLiveState, PushStateRequest, RoomSnapshotResponse } from '../../shared/protocol';
import { ROOM_STALE_MS } from '../../shared/protocol';

export default async (req: Request): Promise<Response> => {
  const store = roomStore();

  if (req.method === 'GET') {
    const url = new URL(req.url);
    const code = (url.searchParams.get('code') || '').trim();
    if (!code) return json(400, { error: 'missing code' });

    const meta = (await store.get(metaKey(code), { type: 'json' })) as RoomMeta | null;
    if (!meta) {
      const res: RoomSnapshotResponse = { meta: null, players: [] };
      return json(200, res);
    }

    const { blobs } = await store.list({ prefix: `pos:${code}:` });
    const now = Date.now();
    const players: PlayerLiveState[] = [];
    for (const b of blobs) {
      const state = (await store.get(b.key, { type: 'json' })) as PlayerLiveState | null;
      if (state && now - state.ts < ROOM_STALE_MS) players.push(state);
    }

    const collected = ((await store.get(itemsKey(code), { type: 'json' })) as string[] | null) || [];

    const res: RoomSnapshotResponse & { collectedItems: string[] } = { meta, players, collectedItems: collected };
    return json(200, res);
  }

  if (req.method === 'POST') {
    let body: PushStateRequest & { collectItem?: string };
    try {
      body = await req.json();
    } catch {
      return json(400, { error: 'bad json' });
    }
    const { code, collectItem, ...rest } = body;
    const state: PlayerLiveState = { ...rest, ts: Date.now() };
    await store.setJSON(posKey(code, state.id), state);

    if (collectItem) {
      const key = itemsKey(code);
      const collected = ((await store.get(key, { type: 'json' })) as string[] | null) || [];
      if (!collected.includes(collectItem)) {
        collected.push(collectItem);
        await store.setJSON(key, collected);
      }
    }
    return json(200, { ok: true });
  }

  return json(405, { error: 'method not allowed' });
};

export const config: Config = { path: '/api/room/state' };
