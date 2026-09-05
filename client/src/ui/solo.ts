import { el, type ScreenFn } from './router';
import { LEVELS } from '../core/track/levels';
import { SaveManager } from '../state/SaveManager';
import { CARS, getCar } from '../data/cars';
import { checkUnlocks } from '../data/unlocks';
import { RaceSession, type RaceStats } from '../core/game/GameEngine';
import { buildRaceScreen, formatTime, showCenterMsg } from './raceHud';
import { XP_REWARDS } from '../state/Progression';
import { renderMenu } from './menu';

function starsStr(n: number): string {
  return `<span class="star-lit">${'★'.repeat(n)}</span><span class="star-dim">${'★'.repeat(3 - n)}</span>`;
}

export const renderSoloLevelSelect: ScreenFn = (root, nav) => {
  const screen = el('div', 'screen');
  const top = el('div', 'topbar');
  top.innerHTML = `<h2>Mode Solo</h2>`;
  const back = el('button', 'btn small ghost', '← Menu');
  back.onclick = () => nav(renderMenu);
  top.appendChild(back);
  screen.appendChild(top);

  const car = getCar(SaveManager.data.selectedCar);
  const carInfo = el('div', 'subtitle', `Voiture actuelle : <b style="color:${car.colorPrimary}">${car.name}</b> — change-la dans le Garage.`);
  screen.appendChild(carInfo);

  const grid = el('div', 'level-grid');
  LEVELS.forEach((level, i) => {
    const prevStars = i === 0 ? 3 : SaveManager.data.levelStars[LEVELS[i - 1].id] ?? 0;
    const unlocked = i === 0 || prevStars >= 1;
    const stars = SaveManager.data.levelStars[level.id] ?? 0;
    const best = SaveManager.data.levelBestTimeMs[level.id];
    const card = el(
      'div',
      `level-card${unlocked ? '' : ' locked'}`,
      `<div class="lname">${level.id}. ${level.name}</div>
       <div class="stars">${unlocked ? starsStr(stars) : '🔒'}</div>
       <div class="lmeta">${unlocked ? (best ? `Meilleur : ${formatTime(best)}` : 'Pas encore joué') : 'Terminer le niveau précédent'}</div>`,
    );
    if (unlocked) card.onclick = () => nav((r, n) => renderSoloRace(r, n, level.id));
    grid.appendChild(card);
  });
  screen.appendChild(grid);
  root.appendChild(screen);
};

function renderSoloRace(root: HTMLElement, nav: Parameters<ScreenFn>[1], levelId: number) {
  const level = LEVELS.find((l) => l.id === levelId)!;
  const dom = buildRaceScreen(root, 'Maintiens pour accélérer et tourner en vol');
  const car = getCar(SaveManager.data.selectedCar);
  let crashes = 0;

  const session = new RaceSession(dom.canvas, car, { mode: 'solo', level }, {
    onTick: (s) => {
      dom.timeChip.textContent = formatTime(s.timeMs);
      dom.metaChip.textContent = `${s.speedKmh} km/h`;
    },
    onCountdown: (stage) => showCenterMsg(dom, stage),
    onCheckpoint: (idx, total) => {
      dom.metaChip.textContent = `Checkpoint ${idx + 1}/${total}`;
    },
    onCrash: () => {
      crashes++;
    },
    onFinish: (stats, stars) => showSoloResults(root, nav, level, stats, stars, crashes),
  });
  session.start();

  const throttlePoll = window.setInterval(() => {
    dom.throttleBtn.classList.toggle('active', session.isThrottleHeld());
  }, 80);

  return () => {
    window.clearInterval(throttlePoll);
    session.destroy();
  };
}

function showSoloResults(
  root: HTMLElement,
  nav: Parameters<ScreenFn>[1],
  level: (typeof LEVELS)[number],
  stats: RaceStats,
  stars: 0 | 1 | 2 | 3,
  crashes: number,
) {
  const prevStars = SaveManager.data.levelStars[level.id] ?? 0;
  SaveManager.recordLevelResult(level.id, stats.timeMs, stars, crashes === 0);
  SaveManager.addTotals({ races: 1, flips: stats.flips, distanceM: stats.distanceM, crashes });
  const xpGain = XP_REWARDS.levelComplete + Math.max(0, stars - prevStars) * XP_REWARDS.starBonus;
  SaveManager.addXp(xpGain);
  const newlyUnlocked = checkUnlocks();

  const panel = el('div', 'results-panel');
  const card = el('div', 'results-card');
  card.innerHTML = `
    <h2>${stars > 0 ? 'Niveau terminé !' : 'Course terminée'}</h2>
    <div class="big-stars">${starsStr(stars)}</div>
    <div class="stat-line"><span>Temps</span><b>${formatTime(stats.timeMs)}</b></div>
    <div class="stat-line"><span>Or</span><b>${formatTime(level.goldMs)}</b></div>
    <div class="stat-line"><span>Argent</span><b>${formatTime(level.silverMs)}</b></div>
    <div class="stat-line"><span>Bronze</span><b>${formatTime(level.bronzeMs)}</b></div>
    <div class="stat-line"><span>Flips réalisés</span><b>${stats.flips}</b></div>
    <div class="stat-line"><span>XP gagné</span><b>+${xpGain}</b></div>
    ${newlyUnlocked.length ? `<p class="record-badge">🚗 Nouvelle voiture débloquée : ${newlyUnlocked.map((id) => CARS.find((c) => c.id === id)?.name).join(', ')}</p>` : ''}
  `;
  const row = el('div', 'menu-secondary');
  const retry = el('button', 'btn primary', 'Réessayer');
  retry.onclick = () => nav((r, n) => renderSoloRace(r, n, level.id));
  const nextLevel = LEVELS.find((l) => l.id === level.id + 1);
  if (nextLevel && stars > 0) {
    const nextBtn = el('button', 'btn accent2', 'Niveau suivant');
    nextBtn.onclick = () => nav((r, n) => renderSoloRace(r, n, nextLevel.id));
    row.appendChild(nextBtn);
  }
  const menuBtn = el('button', 'btn ghost', 'Sélection des niveaux');
  menuBtn.onclick = () => nav(renderSoloLevelSelect);
  row.appendChild(retry);
  row.appendChild(menuBtn);
  card.appendChild(row);
  panel.appendChild(card);
  root.appendChild(panel);
}
