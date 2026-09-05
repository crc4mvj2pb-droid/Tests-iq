import { el, type ScreenFn } from './router';
import { CHALLENGES, getChallengeState } from '../data/challenges';
import { SaveManager } from '../state/SaveManager';
import { renderMenu } from './menu';

export const renderChallenges: ScreenFn = (root, nav) => {
  const screen = el('div', 'screen');
  const top = el('div', 'topbar');
  top.innerHTML = `<h2>Challenges</h2>`;
  const back = el('button', 'btn small ghost', '← Menu');
  back.onclick = () => nav(renderMenu);
  top.appendChild(back);
  screen.appendChild(top);

  const panel = el('div', 'panel');
  for (const c of CHALLENGES) {
    const state = getChallengeState(c);
    const already = SaveManager.data.challengeCompleted[c.id];
    if (state.completed && !already) {
      SaveManager.data.challengeCompleted[c.id] = true;
      SaveManager.addXp(c.xp);
    }
    const row = el('div', 'challenge-row');
    row.innerHTML = `
      <div class="challenge-icon">${c.icon}</div>
      <div class="challenge-body">
        <div>${c.label} ${state.completed ? '✅' : ''}</div>
        <div class="progress-track"><div class="progress-fill" style="width:${state.ratio * 100}%"></div></div>
        <div class="challenge-meta">${state.progress} / ${c.target} — récompense : +${c.xp} XP</div>
      </div>
    `;
    panel.appendChild(row);
  }
  screen.appendChild(panel);
  root.appendChild(screen);
};
