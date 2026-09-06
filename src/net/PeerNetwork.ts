import Peer, { DataConnection } from "peerjs";
import type { ClientToHostMessage, HostToClientMessage } from "./protocol";
import { roomCodeToPeerId } from "../utils/id";

export type ConnStatus = "connecting" | "open" | "error" | "closed";

/**
 * Runs on the machine that created the room. Owns the authoritative game
 * simulation and relays state to every connected browser over WebRTC data
 * channels (signaled through PeerJS's free public broker — no server of
 * our own to host or pay for).
 */
export class HostNetwork {
  peer: Peer | null = null;
  private conns = new Map<string, DataConnection>();
  onPeerJoin: (peerId: string) => void = () => {};
  onPeerLeave: (peerId: string) => void = () => {};
  onMessage: (peerId: string, msg: ClientToHostMessage) => void = () => {};
  onStatus: (status: ConnStatus, detail?: string) => void = () => {};

  start(roomCode: string): void {
    const id = roomCodeToPeerId(roomCode);
    this.onStatus("connecting");
    const peer = new Peer(id, { debug: 0 });
    this.peer = peer;

    peer.on("open", () => this.onStatus("open"));
    peer.on("error", (err) => {
      this.onStatus("error", (err && (err as any).type) || String(err));
    });

    peer.on("connection", (conn) => {
      this.conns.set(conn.peer, conn);
      conn.on("data", (data) => {
        this.onMessage(conn.peer, data as ClientToHostMessage);
      });
      conn.on("open", () => {
        this.onPeerJoin(conn.peer);
      });
      conn.on("close", () => {
        this.conns.delete(conn.peer);
        this.onPeerLeave(conn.peer);
      });
      conn.on("error", () => {
        this.conns.delete(conn.peer);
        this.onPeerLeave(conn.peer);
      });
    });
  }

  send(peerId: string, msg: HostToClientMessage): void {
    const conn = this.conns.get(peerId);
    if (conn && conn.open) conn.send(msg);
  }

  broadcast(msg: HostToClientMessage): void {
    for (const conn of this.conns.values()) {
      if (conn.open) conn.send(msg);
    }
  }

  kick(peerId: string): void {
    const conn = this.conns.get(peerId);
    if (conn) conn.close();
    this.conns.delete(peerId);
  }

  destroy(): void {
    for (const conn of this.conns.values()) conn.close();
    this.conns.clear();
    this.peer?.destroy();
    this.peer = null;
  }
}

/**
 * Runs on every joining player's machine. Connects directly to the host's
 * peer, sends local input, and receives authoritative state snapshots.
 */
export class ClientNetwork {
  peer: Peer | null = null;
  private conn: DataConnection | null = null;
  onMessage: (msg: HostToClientMessage) => void = () => {};
  onStatus: (status: ConnStatus, detail?: string) => void = () => {};

  join(roomCode: string): void {
    this.onStatus("connecting");
    const peer = new Peer({ debug: 0 });
    this.peer = peer;

    peer.on("open", () => {
      const conn = peer.connect(roomCodeToPeerId(roomCode), { reliable: true });
      this.conn = conn;
      conn.on("open", () => this.onStatus("open"));
      conn.on("data", (data) => this.onMessage(data as HostToClientMessage));
      conn.on("close", () => this.onStatus("closed"));
      conn.on("error", (err) => this.onStatus("error", String((err as any)?.type || err)));
    });
    peer.on("error", (err) => {
      this.onStatus("error", (err && (err as any).type) || String(err));
    });
  }

  send(msg: ClientToHostMessage): void {
    if (this.conn && this.conn.open) this.conn.send(msg);
  }

  destroy(): void {
    this.conn?.close();
    this.peer?.destroy();
    this.conn = null;
    this.peer = null;
  }
}
