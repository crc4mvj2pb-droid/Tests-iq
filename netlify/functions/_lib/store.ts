import { getStore } from '@netlify/blobs';

export function roomStore() {
  return getStore('rooms', { consistency: 'strong' });
}

export const metaKey = (code: string) => `meta:${code}`;
export const posKey = (code: string, playerId: string) => `pos:${code}:${playerId}`;
export const itemsKey = (code: string) => `items:${code}`;

export function json(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } });
}

export function newId(): string {
  return Math.random().toString(36).slice(2, 10);
}

export function genCode(): string {
  return String(Math.floor(1000 + Math.random() * 9000));
}
