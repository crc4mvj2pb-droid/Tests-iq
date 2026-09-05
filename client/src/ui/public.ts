import { el, type ScreenFn, type Navigate } from './router';
import { netClient, getPlayerName, setPlayerName } from '../net';
import type { ServerMessage } from '@shared/protocol';
import { PUBLIC_ROUND_DISTANCE_M } from '@shared/constants';
import { SaveManager } from '../state/SaveManager';
import { getCar } from '../data/cars';
import { RaceSession } from '../core/game/GameEngine';
import { buildRaceScreen, formatTime, showCenterMsg } from './raceHud';
import { renderMenu } from './menu';

const GHOST_COLORS = ['#4fd1ff', '#ff4fd6', '#a6ff4f', '#ffb84f', '#c14fff', '#4fffe0', '#ff9d4f', '#8f9bff'];

export const renderPublicHome: ScreenFn = (root, nav) => {
  const screen = el('div', 'screen');
  const top = el('div', 'topbar');
  top.innerHTML = `<h2>Course Publique</h2>`;
  const back = el('button', 'btn small ghost', '← Menu');
  back.onclick = () => nav(renderMenu);
  top.appendChild(back);
  screen.appendChild(top);

  const panel = el('div', 'panel');
  panel.innerHTML = `<p>Jusqu'à 50 pilotes. Les places restantes sont comblées par des bots pour garantir une course pleine.</p>`;
  const nameInput = el('input');
  nameInput.value = getPlayerName();
  nameInput.maxLength = 20;
  nameInput.oninput = () => setPlayerName(nameInput.value);
  const nameRow = el('div', 'form-row', '<label>Ton pseudo</label>');
  nameRow.appendChild(nameInput);
  panel.appendChild(nameRow);

  const status = el('div', 'subtitle', 'Prêt à chercher une course.');
  panel.appendChild(status);
  const searchBtn = el('button', 'btn primary', '🔍 Chercher une partie');
  panel.appendChild(searchBtn);
  screen.appendChild(panel);
  root.appendChild(screen);

  let off: (() => void) | null = null;
  searchBtn.onclick = async () => {
    searchBtn.disabled = true;
    status.textContent = 'Connexion au serveur...';
    await netClient.connect().catch(() => {
      status.textContent = 'Serveur injoignable.';
    });
    netClient.send({ type: 'public:queue', name: getPlayerName(), carId: SaveManager.data.selectedCar });
    off = netClient.on((msg) => {
      if (msg.type === 'public:queued') {
        status.textContent = `En file d'attente... position ${msg.position}/${msg.queueSize}`;
      } else if (msg.type === 'public:matchFound') {
        off?.();
        nav((r, n) => renderPublicBriefing(r, n, msg));
      }
    });
  };

  return () => {
    off?.();
    if (searchBtn.disabled) netClient.send({ type: 'public:leaveQueue' });
  };
};

function renderPublicBriefing(root: HTMLElement, nav: Navigate, msg: Extract<ServerMessage, { type: 'public:matchFound' }>) {
  const you = msg.you;
  const screen = el('div', 'screen');
  screen.innerHTML = `<h2>Course trouvée !</h2><div class="subtitle">${msg.totalPlayers} concurrents. Élimination directe jusqu'à la finale.</div>`;
  const panel = el('div', 'panel');
  const list = el('ul', 'lobby-list');
  for (const p of msg.players) {
    const li = el('li', 'lobby-row');
    li.innerHTML = `<span>${p.name}${p.id === you ? ' (toi)' : ''}${p.isBot ? ` <span class="tag-wait">(bot ${p.botTier})</span>` : ''}</span>`;
    list.appendChild(li);
  }
  panel.appendChild(list);
  screen.appendChild(panel);
  root.appendChild(screen);

  const roster = msg.players.map((p) => ({ id: p.id, name: p.name }));
  const off = netClient.on((m) => {
    if (m.type === 'public:heatStart') {
      off();
      nav((r, n) => renderPublicHeatRace(r, n, m, roster, you));
    }
  });
  return () => off();
}

function renderPublicHeatRace(
  root: HTMLElement,
  nav: Navigate,
  heatMsg: Extract<ServerMessage, { type: 'public:heatStart' }>,
  roster: { id: string; name: string }[],
  you: string,
) {
  const dom = buildRaceScreen(root, "Élimination directe — qualifie-toi pour la manche suivante");
  const car = getCar(SaveManager.data.selectedCar);
  const ghostStates = new Map<string, { x: number; y: number; angle: number }>();

  const offGhost = netClient.on((msg) => {
    if (msg.type === 'race:ghost') ghostStates.set(msg.playerId, { x: msg.x, y: msg.y, angle: msg.angle });
  });

  const session = new RaceSession(
    dom.canvas,
    car,
    { mode: 'multiplayer', seed: heatMsg.trackSeed, targetDistanceM: PUBLIC_ROUND_DISTANCE_M, environment: heatMsg.environment },
    {
      onTick: (s) => {
        dom.timeChip.textContent = formatTime(s.timeMs);
        dom.metaChip.textContent = `Heat ${heatMsg.heat} · Top ${heatMsg.qualifying} qualifiés · ${s.speedKmh} km/h`;
      },
      onCountdown: (stage) => showCenterMsg(dom, stage),
      onFinish: () => {
        showCenterMsg(dom, 'ARRIVÉE !');
        netClient.send({ type: 'race:finish' });
      },
      onStateUpdate: (x, y, angle, speed) => netClient.send({ type: 'race:state', x, y, angle, speed }),
    },
  );
  session.ghosts = roster
    .filter((p) => p.id !== you)
    .map((p, i) => ({
      id: p.id,
      name: p.name,
      color: GHOST_COLORS[i % GHOST_COLORS.length],
      get: () => ghostStates.get(p.id) ?? null,
    }));

  const delay = Math.max(0, heatMsg.serverStartAt - Date.now());
  const startTimer = setTimeout(() => session.start(), delay);

  const offResult = netClient.on((msg) => {
    if (msg.type === 'public:heatResult') {
      cleanup();
      nav((r, n) => renderPublicHeatResult(r, n, msg, you));
    } else if (msg.type === 'public:matchOver') {
      cleanup();
      nav((r, n) => renderPublicMatchOver(r, n, msg, you));
    }
  });

  const throttlePoll = window.setInterval(() => {
    dom.throttleBtn.classList.toggle('active', session.isThrottleHeld());
  }, 80);

  function cleanup() {
    clearTimeout(startTimer);
    window.clearInterval(throttlePoll);
    offGhost();
    offResult();
    session.destroy();
  }
  return cleanup;
}

function renderPublicHeatResult(root: HTMLElement, nav: Navigate, msg: Extract<ServerMessage, { type: 'public:heatResult' }>, you: string) {
  const qualified = msg.qualifiedIds.includes(you);
  const screen = el('div', 'screen');
  const banner = el('div', 'panel');
  banner.style.textAlign = 'center';
  banner.innerHTML = `<h2 style="color:${qualified ? '#a6ff4f' : '#ff4f6d'};font-size:2rem">${qualified ? 'QUALIFIÉ !' : 'ÉLIMINÉ'}</h2>`;
  screen.appendChild(banner);

  const panel = el('div', 'panel');
  panel.innerHTML = `<ul class="lobby-list">${msg.results
    .map(
      (r) =>
        `<li class="lobby-row"><span>${msg.qualifiedIds.includes(r.playerId) ? '✅' : '❌'} ${r.name}${r.playerId === you ? ' (toi)' : ''}</span><span>${r.timeMs !== null ? formatTime(r.timeMs) : 'DNF'}</span></li>`,
    )
    .join('')}</ul>`;
  screen.appendChild(panel);

  if (!qualified) {
    const menuBtn = el('button', 'btn ghost', 'Retour au menu (en attente du résultat final...)');
    menuBtn.onclick = () => nav(renderMenu);
    screen.appendChild(menuBtn);
  }
  root.appendChild(screen);

  const roster = msg.results.map((r) => ({ id: r.playerId, name: r.name }));
  const off = netClient.on((m) => {
    if (m.type === 'public:heatStart' && qualified) {
      off();
      nav((r, n) => renderPublicHeatRace(r, n, m, roster, you));
    } else if (m.type === 'public:matchOver') {
      off();
      nav((r, n) => renderPublicMatchOver(r, n, m, you));
    }
  });
  return () => off();
}

function renderPublicMatchOver(root: HTMLElement, nav: Navigate, msg: Extract<ServerMessage, { type: 'public:matchOver' }>, you: string) {
  const won = msg.winnerId === you;
  if (won) SaveManager.addTotals({ publicWins: 1, victories: 1 });
  const screen = el('div', 'screen');
  screen.innerHTML = `<h2>🏁 Finale</h2>`;
  const panel = el('div', 'panel');
  panel.innerHTML = `<div class="record-badge" style="text-align:center">🏆 ${msg.winnerName} remporte la course !</div>
    <ul class="lobby-list">${msg.standings
      .map((s, i) => `<li class="lobby-row"><span>${i + 1}. ${s.name}${s.playerId === you ? ' (toi)' : ''}</span><span>${s.points} pts</span></li>`)
      .join('')}</ul>`;
  const menuBtn = el('button', 'btn primary', 'Retour au menu');
  menuBtn.style.marginTop = '16px';
  menuBtn.onclick = () => nav(renderMenu);
  panel.appendChild(menuBtn);
  screen.appendChild(panel);
  root.appendChild(screen);
}
