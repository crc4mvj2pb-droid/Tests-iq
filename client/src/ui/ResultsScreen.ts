export interface ResultsData {
  timeMs: number;
  checkpoints: number;
  checkpointsTotal: number;
}

export interface ResultsCallbacks {
  onMenu: () => void;
}

function formatTime(ms: number): string {
  const totalSeconds = Math.floor(ms / 1000);
  const m = Math.floor(totalSeconds / 60);
  const s = totalSeconds % 60;
  return `${m}:${String(s).padStart(2, '0')}`;
}

export function renderResults(root: HTMLElement, data: ResultsData & ResultsCallbacks): () => void {
  const el = document.createElement('div');
  el.className = 'screen';
  el.innerHTML = `
    <div class="panel results-card">
      <h2>Sommet atteint !</h2>
      <div class="results-time">${formatTime(data.timeMs)}</div>
      <p class="results-stat">Checkpoints collectés : ${data.checkpoints}/${data.checkpointsTotal}</p>
      <div class="menu-buttons" style="margin-top:20px;">
        <button class="btn btn-primary" data-action="menu">Retour au menu</button>
      </div>
    </div>
  `;
  root.appendChild(el);
  el.querySelector('[data-action="menu"]')?.addEventListener('click', () => data.onMenu());
  return () => el.remove();
}
