import { el, type ScreenFn } from './router';
import { SaveManager } from '../state/SaveManager';
import { levelFromXp } from '../state/Progression';
import { renderMenu } from './menu';

export const renderProfile: ScreenFn = (root, nav) => {
  const screen = el('div', 'screen');
  const top = el('div', 'topbar');
  top.innerHTML = `<h2>Profil</h2>`;
  const back = el('button', 'btn small ghost', '← Menu');
  back.onclick = () => nav(renderMenu);
  top.appendChild(back);
  screen.appendChild(top);

  const d = SaveManager.data;
  const { level, xpIntoLevel, xpForNext } = levelFromXp(d.xp);

  const panel = el('div', 'panel');
  panel.innerHTML = `
    <h3>Niveau ${level}</h3>
    <div class="progress-track"><div class="progress-fill" style="width:${(xpIntoLevel / xpForNext) * 100}%"></div></div>
    <div class="challenge-meta">${xpIntoLevel} / ${xpForNext} XP</div>
    <div style="height:16px"></div>
    <div class="stat-line"><span>Meilleur score Classic</span><b>${d.classicBest.score}</b></div>
    <div class="stat-line"><span>Meilleure distance Classic</span><b>${d.classicBest.distanceM} m</b></div>
    <div class="stat-line"><span>Victoires Private</span><b>${d.totals.privateWins}</b></div>
    <div class="stat-line"><span>Victoires Public</span><b>${d.totals.publicWins}</b></div>
    <div class="stat-line"><span>Flips réalisés</span><b>${d.totals.flips}</b></div>
    <div class="stat-line"><span>Courses jouées</span><b>${d.totals.races}</b></div>
    <div class="stat-line"><span>Étoiles obtenues</span><b>${SaveManager.totalStars()} / ${20 * 3}</b></div>
    <div class="stat-line"><span>Voitures débloquées</span><b>${d.unlockedCars.length} / 10</b></div>
  `;
  screen.appendChild(panel);
  root.appendChild(screen);
};
