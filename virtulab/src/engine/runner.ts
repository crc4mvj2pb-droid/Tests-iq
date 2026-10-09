import type { ExperimentResult, ExperimentSpec } from './types';

/** Lance l'expérience dans un Web Worker pour garder l'interface fluide. */
export function runInWorker(
  spec: ExperimentSpec,
  onProgress: (done: number, total: number) => void,
): { promise: Promise<ExperimentResult>; cancel: () => void } {
  const worker = new Worker(new URL('./worker.ts', import.meta.url), { type: 'module' });
  let reject: (e: Error) => void = () => {};
  const promise = new Promise<ExperimentResult>((resolve, rej) => {
    reject = rej;
    worker.onmessage = (e) => {
      const msg = e.data;
      if (msg.type === 'progress') onProgress(msg.done, msg.total);
      else if (msg.type === 'done') { worker.terminate(); resolve(msg.result); }
      else if (msg.type === 'error') { worker.terminate(); rej(new Error(msg.message)); }
    };
    worker.onerror = (e) => { worker.terminate(); rej(new Error(e.message || 'Erreur du moteur de simulation')); };
  });
  worker.postMessage(spec);
  return { promise, cancel: () => { worker.terminate(); reject(new Error('Expérience annulée')); } };
}
