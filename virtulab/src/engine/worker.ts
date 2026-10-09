import { executeExperiment } from './execute';
import type { ExperimentSpec } from './types';

self.onmessage = (e: MessageEvent<ExperimentSpec>) => {
  try {
    const result = executeExperiment(e.data, (done, total) => self.postMessage({ type: 'progress', done, total }));
    self.postMessage({ type: 'done', result });
  } catch (err) {
    self.postMessage({ type: 'error', message: err instanceof Error ? err.message : String(err) });
  }
};
