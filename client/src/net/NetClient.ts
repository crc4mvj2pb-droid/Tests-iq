import type { ClientMessage, ServerMessage } from '@shared/protocol';

export type ServerHandler = (msg: ServerMessage) => void;

function resolveServerUrl(): string {
  if (import.meta.env.VITE_SERVER_URL) return import.meta.env.VITE_SERVER_URL;
  const proto = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  return `${proto}//${window.location.hostname}:8787`;
}

export class NetClient {
  private ws: WebSocket | null = null;
  private handlers = new Set<ServerHandler>();
  private queue: ClientMessage[] = [];
  private url: string;
  status: 'idle' | 'connecting' | 'open' | 'closed' | 'error' = 'idle';

  constructor(url = resolveServerUrl()) {
    this.url = url;
  }

  connect(): Promise<void> {
    if (this.ws && this.status === 'open') return Promise.resolve();
    this.status = 'connecting';
    return new Promise((resolve, reject) => {
      try {
        this.ws = new WebSocket(this.url);
      } catch (e) {
        this.status = 'error';
        reject(e);
        return;
      }
      this.ws.onopen = () => {
        this.status = 'open';
        for (const m of this.queue.splice(0)) this.ws!.send(JSON.stringify(m));
        resolve();
      };
      this.ws.onmessage = (evt) => {
        try {
          const msg = JSON.parse(evt.data) as ServerMessage;
          this.handlers.forEach((h) => h(msg));
        } catch {
          /* ignore malformed frame */
        }
      };
      this.ws.onclose = () => {
        this.status = 'closed';
      };
      this.ws.onerror = () => {
        this.status = 'error';
        reject(new Error('WebSocket connection failed'));
      };
    });
  }

  on(handler: ServerHandler) {
    this.handlers.add(handler);
    return () => this.handlers.delete(handler);
  }

  send(msg: ClientMessage) {
    if (this.status === 'open' && this.ws) {
      this.ws.send(JSON.stringify(msg));
    } else {
      this.queue.push(msg);
    }
  }

  close() {
    this.ws?.close();
    this.ws = null;
    this.status = 'closed';
  }
}
