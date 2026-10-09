import { runInWorker } from './engine/runner';
import { newId, store } from './engine/store';
import type { Experiment, ExperimentSpec } from './engine/types';
import { toast } from './ui/dom';

const progress = new Map<string, { done: number; total: number; cancel: () => void }>();
const progressListeners = new Set<(id: string) => void>();

export function getProgress(id: string) {
  return progress.get(id);
}

export function onProgress(fn: (id: string) => void): () => void {
  progressListeners.add(fn);
  return () => progressListeners.delete(fn);
}

export function navigate(hash: string): void {
  if (location.hash === hash) window.dispatchEvent(new HashChangeEvent('hashchange'));
  else location.hash = hash;
}

/** Enregistre puis exécute une expérience dans un Web Worker. */
export async function launch(spec: Omit<ExperimentSpec, 'id' | 'createdAt'> & Partial<Pick<ExperimentSpec, 'id' | 'createdAt'>>): Promise<string> {
  const full: ExperimentSpec = { ...spec, id: spec.id ?? newId(), createdAt: spec.createdAt ?? Date.now() };
  const prev = store.get(full.id);
  const exp: Experiment = { spec: full, status: 'running', notes: prev?.notes };
  await store.save(exp);
  const job = runInWorker(full, (done, total) => {
    const p = progress.get(full.id);
    if (p) { p.done = done; p.total = total; }
    for (const fn of progressListeners) fn(full.id);
  });
  progress.set(full.id, { done: 0, total: 1, cancel: job.cancel });
  job.promise
    .then(async (result) => {
      progress.delete(full.id);
      await store.save({ ...exp, notes: store.get(full.id)?.notes, status: 'done', result });
      toast(`Expérience terminée : ${full.name}`);
    })
    .catch(async (err: Error) => {
      progress.delete(full.id);
      await store.save({ ...exp, notes: store.get(full.id)?.notes, status: 'error', error: err.message });
      toast(err.message, 'error');
    });
  return full.id;
}
