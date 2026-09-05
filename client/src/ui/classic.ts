import { el, type ScreenFn } from './router';
import { SaveManager } from '../state/SaveManager';
import { getCar } from '../data/cars';
import { checkUnlocks } from '../data/unlocks';
import { CARS } from '../data/cars';
import { RaceSession, type RaceStats } from '../core/game/GameEngine';
import { buildRaceScreen, formatTime, showCenterMsg } from './raceHud';
import { randSeed } from '@shared/rng';
import { XP_REWARDS } from '../state/Progression';
import { renderMenu } from './menu';

export const renderClassicIntro: ScreenFn = (root, nav) => {
  const screen = el('div', 'screen');
  const top = el('div', 'topbar');
  top.innerHTML = `<h2>Mode Classic</h2>`;
  const back = el('button', 'btn small ghost', '← Menu');
  back.onclick = () => nav(renderMenu);
  top.appendChild(back);
  screen.appendChild(top);

  const best = SaveManager.data.classicBest;
  const panel = el('div', 'panel');
  panel.innerHTML = `
    <p>Course sans fin générée procéduralement. Aucune ligne d'arrivée : va le plus loin possible, enchaîne les flips, ne crashe jamais.</p>
    <div class="stat-line"><span>Meilleur score</span><b>${best.score}</b></div>
    <div class="stat-line"><span>Meilleure distance</span><b>${best.distanceM} m</b></div>
    <div class="stat-line"><span>Meilleur combo</span><b>x${best.bestCombo}</b></div>
  `;
  const btn = el('button', 'btn primary', '▶ Démarrer');
  btn.style.marginTop = '16px';
  btn.onclick = () => nav(renderClassicRace);
  panel.appendChild(btn);
  screen.appendChild(panel);
  root.appendChild(screen);
};

const renderClassicRace: ScreenFn = (root, nav) => {
  const dom = buildRaceScreen(root, 'Maintiens pour accélérer — un crash termine la course');
  const car = getCar(SaveManager.data.selectedCar);

  const session = new RaceSession(dom.canvas, car, { mode: 'classic', seed: randSeed() }, {
    onTick: (s) => {
      dom.timeChip.textContent = `${s.distanceM} m`;
      dom.metaChip.textContent = `${s.speedKmh} km/h · ${Math.round(s.score)} pts`;
      if (s.comboNow >= 2) {
        dom.comboChip.style.display = 'block';
        dom.comboChip.textContent = `Combo x${s.comboNow}`;
      } else {
        dom.comboChip.style.display = 'none';
      }
    },
    onCountdown: (stage) => showCenterMsg(dom, stage),
    onGameOver: (stats) => showClassicResults(root, nav, stats),
  });
  session.start();

  const throttlePoll = window.setInterval(() => {
    dom.throttleBtn.classList.toggle('active', session.isThrottleHeld());
  }, 80);

  return () => {
    window.clearInterval(throttlePoll);
    session.destroy();
  };
};

function showClassicResults(root: HTMLElement, nav: Parameters<ScreenFn>[1], stats: RaceStats) {
  const isRecord = SaveManager.recordClassicResult({
    score: stats.score,
    distanceM: stats.distanceM,
    flips: stats.flips,
    bestCombo: stats.bestCombo,
  });
  SaveManager.addTotals({ races: 1, flips: stats.flips, distanceM: stats.distanceM, crashes: 1 });
  const xpGain = XP_REWARDS.classicPer1000m * (stats.distanceM / 1000);
  SaveManager.addXp(Math.round(xpGain));
  const newlyUnlocked = checkUnlocks();

  const panel = el('div', 'results-panel');
  const card = el('div', 'results-card');
  card.innerHTML = `
    <h2>GAME OVER</h2>
    ${isRecord ? '<div class="record-badge">🏆 NOUVEAU RECORD !</div>' : ''}
    <div class="stat-line"><span>Score</span><b>${Math.round(stats.score)}</b></div>
    <div class="stat-line"><span>Distance</span><b>${stats.distanceM} m</b></div>
    <div class="stat-line"><span>Flips</span><b>${stats.flips}</b></div>
    <div class="stat-line"><span>Meilleur combo</span><b>x${stats.bestCombo}</b></div>
    <div class="stat-line"><span>XP gagné</span><b>+${Math.round(xpGain)}</b></div>
    ${newlyUnlocked.length ? `<p class="record-badge">🚗 Nouvelle voiture débloquée : ${newlyUnlocked.map((id) => CARS.find((c) => c.id === id)?.name).join(', ')}</p>` : ''}
  `;
  const row = el('div', 'menu-secondary');
  const retry = el('button', 'btn primary', 'Rejouer');
  retry.onclick = () => nav(renderClassicRace);
  const menuBtn = el('button', 'btn ghost', 'Menu');
  menuBtn.onclick = () => nav(renderMenu);
  row.appendChild(retry);
  row.appendChild(menuBtn);
  card.appendChild(row);
  panel.appendChild(card);
  root.appendChild(panel);
}
