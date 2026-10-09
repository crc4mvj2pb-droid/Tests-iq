import type { Experiment } from './types';

const DB_NAME = 'virtulab';
const STORE = 'experiments';

let dbPromise: Promise<IDBDatabase | null> | null = null;

function openDb(): Promise<IDBDatabase | null> {
  if (!dbPromise) {
    dbPromise = new Promise((resolve) => {
      try {
        const req = indexedDB.open(DB_NAME, 1);
        req.onupgradeneeded = () => req.result.createObjectStore(STORE, { keyPath: 'spec.id' });
        req.onsuccess = () => resolve(req.result);
        req.onerror = () => resolve(null);
      } catch {
        resolve(null); // navigation privée stricte : fonctionnement en mémoire
      }
    });
  }
  return dbPromise;
}

const memory = new Map<string, Experiment>();
const listeners = new Set<() => void>();

export const store = {
  async load(): Promise<void> {
    const db = await openDb();
    if (!db) return;
    const all = await new Promise<Experiment[]>((resolve) => {
      const req = db.transaction(STORE, 'readonly').objectStore(STORE).getAll();
      req.onsuccess = () => resolve(req.result as Experiment[]);
      req.onerror = () => resolve([]);
    });
    for (const e of all) {
      // Une expérience interrompue par la fermeture de l'onglet n'a pas de résultat.
      if (e.status === 'running') e.status = 'draft';
      memory.set(e.spec.id, e);
    }
  },

  list(): Experiment[] {
    return [...memory.values()].sort((a, b) => b.spec.createdAt - a.spec.createdAt);
  },

  get(id: string): Experiment | undefined {
    return memory.get(id);
  },

  async save(e: Experiment): Promise<void> {
    memory.set(e.spec.id, e);
    emit();
    const db = await openDb();
    if (!db) return;
    await new Promise<void>((resolve) => {
      const tx = db.transaction(STORE, 'readwrite');
      tx.objectStore(STORE).put(e);
      tx.oncomplete = () => resolve();
      tx.onerror = () => resolve();
    });
  },

  async remove(id: string): Promise<void> {
    memory.delete(id);
    emit();
    const db = await openDb();
    if (!db) return;
    db.transaction(STORE, 'readwrite').objectStore(STORE).delete(id);
  },

  subscribe(fn: () => void): () => void {
    listeners.add(fn);
    return () => listeners.delete(fn);
  },
};

function emit(): void {
  for (const fn of listeners) fn();
}

export function newId(): string {
  return `exp-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`;
}
