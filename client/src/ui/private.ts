import { el, type ScreenFn, type Navigate } from './router';
import { netClient, getPlayerName, setPlayerName } from '../net';
import type { PlayerInfo, RoundResult, ServerMessage } from '@shared/protocol';
import { ROUND_TARGET_DISTANCE_M } from '@shared/constants';
import { SaveManager } from '../state/SaveManager';
import { getCar } from '../data/cars';
import { RaceSession } from '../core/game/GameEngine';
import { buildRaceScreen, formatTime, showCenterMsg } from './raceHud';
import { renderMenu } from './menu';

const GHOST_COLORS = ['#4fd1ff', '#ff4fd6', '#a6ff4f', '#ffb84f', '#c14fff', '#4fffe0', '#ff9d4f', '#8f9bff'];

function showError(root: HTMLElement, message: string) {
  const toast = el('div', 'hud-chip', message);
  toast.style.position = 'absolute';
  toast.style.top = '16px';
  toast.style.left = '50%';
  toast.style.transform = 'translateX(-50%)';
  toast.style.background = 'rgba(255,79,109,0.9)';
  toast.style.zIndex = '10';
  root.appendChild(toast);
  setTimeout(() => toast.remove(), 3200);
}

export const renderPrivateHome: ScreenFn = (root, nav) => {
  const screen = el('div', 'screen');
  const top = el('div', 'topbar');
  top.innerHTML = `<h2>Partie Privée</h2>`;
  const back = el('button', 'btn small ghost', '← Menu');
  back.onclick = () => nav(renderMenu);
  top.appendChild(back);
  screen.appendChild(top);

  const panel = el('div', 'panel');
  panel.innerHTML = `<div class="form-row"><label>Ton pseudo</label></div>`;
  const nameInput = el('input');
  nameInput.value = getPlayerName();
  nameInput.maxLength = 20;
  nameInput.oninput = () => setPlayerName(nameInput.value);
  panel.querySelector('.form-row')!.appendChild(nameInput);

  const createBtn = el('button', 'btn primary', 'CREATE GAME');
  const roundsRow = el('div', 'menu-secondary');
  let rounds: 3 | 5 = 3;
  const r3 = el('button', 'btn small', '3 manches');
  const r5 = el('button', 'btn small ghost', '5 manches');
  r3.onclick = () => { rounds = 3; r3.classList.remove('ghost'); r5.classList.add('ghost'); };
  r5.onclick = () => { rounds = 5; r5.classList.remove('ghost'); r3.classList.add('ghost'); };
  roundsRow.appendChild(r3);
  roundsRow.appendChild(r5);
  panel.appendChild(roundsRow);
  panel.appendChild(createBtn);

  createBtn.onclick = async () => {
    createBtn.disabled = true;
    await netClient.connect().catch(() => showError(root, 'Impossible de contacter le serveur.'));
    const off = netClient.on((msg) => {
      if (msg.type === 'private:created') {
        off();
        nav((r, n) => renderPrivateLobby(r, n, msg.code, msg.you, true));
      }
    });
    netClient.send({ type: 'private:create', name: getPlayerName(), carId: SaveManager.data.selectedCar, rounds });
  };

  const divider = el('h3', undefined, 'Rejoindre une partie');
  divider.style.marginTop = '20px';
  panel.appendChild(divider);
  const joinRow = el('div', 'form-row');
  const codeInput = el('input');
  codeInput.placeholder = 'Code à 4 chiffres';
  codeInput.maxLength = 4;
  joinRow.appendChild(codeInput);
  panel.appendChild(joinRow);
  const joinBtn = el('button', 'btn accent2', 'JOIN GAME');
  joinBtn.onclick = async () => {
    if (codeInput.value.trim().length !== 4) {
      showError(root, 'Entre un code à 4 chiffres.');
      return;
    }
    await netClient.connect().catch(() => showError(root, 'Impossible de contacter le serveur.'));
    const off = netClient.on((msg) => {
      if (msg.type === 'private:joined') {
        off();
        nav((r, n) => renderPrivateLobby(r, n, codeInput.value.trim(), msg.you, false));
      } else if (msg.type === 'private:error') {
        off();
        showError(root, msg.message);
      }
    });
    netClient.send({ type: 'private:join', code: codeInput.value.trim(), name: getPlayerName(), carId: SaveManager.data.selectedCar });
  };
  panel.appendChild(joinBtn);

  screen.appendChild(panel);
  root.appendChild(screen);
};

function renderPrivateLobby(root: HTMLElement, nav: Navigate, code: string, you: string, isHost: boolean) {
  const screen = el('div', 'screen');
  screen.innerHTML = `<h2>Salon privé</h2><div class="code-display">${code}</div><div class="subtitle">Partage ce code — ou l'URL de cette page — à tes amis.</div>`;

  const panel = el('div', 'panel');
  const list = el('ul', 'lobby-list');
  panel.appendChild(list);
  const readyBtn = el('button', 'btn primary', 'PRÊT');
  const startBtn = el('button', 'btn accent2', 'START');
  startBtn.style.display = isHost ? 'inline-block' : 'none';
  startBtn.disabled = true;

  let ready = false;
  readyBtn.onclick = () => {
    ready = !ready;
    readyBtn.textContent = ready ? 'PRÊT ✓' : 'PRÊT';
    netClient.send({ type: 'private:setReady', ready });
  };
  if (isHost) readyBtn.style.display = 'none';
  startBtn.onclick = () => netClient.send({ type: 'private:start' });

  const row = el('div', 'menu-secondary');
  row.appendChild(readyBtn);
  row.appendChild(startBtn);
  panel.appendChild(row);
  screen.appendChild(panel);
  root.appendChild(screen);

  let currentPlayers: PlayerInfo[] = [];

  const off = netClient.on((msg: ServerMessage) => {
    if (msg.type === 'private:lobby') {
      currentPlayers = msg.players;
      list.innerHTML = '';
      for (const p of msg.players) {
        const li = el('li', 'lobby-row');
        li.innerHTML = `<span>${p.name}${p.isHost ? '<span class="tag-host">HOST</span>' : ''}</span><span class="${p.ready || p.isHost ? 'tag-ready' : 'tag-wait'}">${p.isHost ? 'PRÊT' : p.ready ? 'PRÊT' : 'EN ATTENTE'}</span>`;
        list.appendChild(li);
      }
      if (isHost) startBtn.disabled = !msg.players.every((p) => p.ready || p.isHost) || msg.players.length < 1;
    } else if (msg.type === 'race:start') {
      off();
      nav((r, n) => renderPrivateRace(r, n, msg, currentPlayers, you));
    }
  });

  return () => off();
}

function renderPrivateRace(
  root: HTMLElement,
  nav: Navigate,
  startMsg: Extract<ServerMessage, { type: 'race:start' }>,
  players: { id: string; name: string }[],
  you: string,
) {
  const dom = buildRaceScreen(root, 'Rejoins la ligne d\'arrivée le plus vite possible');
  const car = getCar(SaveManager.data.selectedCar);
  const ghostStates = new Map<string, { x: number; y: number; angle: number }>();

  const offGhost = netClient.on((msg) => {
    if (msg.type === 'race:ghost') {
      ghostStates.set(msg.playerId, { x: msg.x, y: msg.y, angle: msg.angle });
    }
  });

  const session = new RaceSession(
    dom.canvas,
    car,
    { mode: 'multiplayer', seed: startMsg.trackSeed, targetDistanceM: ROUND_TARGET_DISTANCE_M, environment: startMsg.environment },
    {
      onTick: (s) => {
        dom.timeChip.textContent = formatTime(s.timeMs);
        dom.metaChip.textContent = `Manche ${startMsg.round}/${startMsg.totalRounds} · ${s.speedKmh} km/h`;
      },
      onCountdown: (stage) => showCenterMsg(dom, stage),
      onFinish: () => {
        showCenterMsg(dom, 'ARRIVÉE !');
        netClient.send({ type: 'race:finish' });
      },
      onStateUpdate: (x, y, angle, speed) => netClient.send({ type: 'race:state', x, y, angle, speed }),
    },
  );
  session.ghosts = players
    .filter((p) => p.id !== you)
    .map((p, i) => ({
      id: p.id,
      name: p.name,
      color: GHOST_COLORS[i % GHOST_COLORS.length],
      get: () => ghostStates.get(p.id) ?? null,
    }));

  const delay = Math.max(0, startMsg.serverStartAt - Date.now());
  const startTimer = setTimeout(() => session.start(), delay);

  const offResult = netClient.on((msg) => {
    if (msg.type === 'race:roundResult') {
      cleanup();
      nav((r, n) => renderPrivateRoundResult(r, n, msg.round, startMsg.totalRounds, msg.results, msg.standings, you));
    } else if (msg.type === 'race:matchOver') {
      cleanup();
      nav((r, n) => renderPrivateMatchOver(r, n, msg.standings, you));
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

function resultTable(results: RoundResult[], you: string): string {
  return `<ul class="lobby-list">${results
    .map(
      (r, i) =>
        `<li class="lobby-row"><span>${i + 1}. ${r.name}${r.playerId === you ? ' (toi)' : ''}</span><span>${r.timeMs !== null ? formatTime(r.timeMs) : 'DNF'} · +${r.points} pts</span></li>`,
    )
    .join('')}</ul>`;
}

function renderPrivateRoundResult(
  root: HTMLElement,
  nav: Navigate,
  round: number,
  totalRounds: number,
  results: RoundResult[],
  standings: RoundResult[],
  you: string,
) {
  const screen = el('div', 'screen');
  screen.innerHTML = `<h2>Résultats — Manche ${round}/${totalRounds}</h2>`;
  const panel = el('div', 'panel');
  panel.innerHTML = `<h3>Cette manche</h3>${resultTable(results, you)}<h3>Classement général</h3>${resultTable(standings, you)}`;
  const hint = el('div', 'subtitle', round < totalRounds ? 'Manche suivante dans quelques secondes...' : 'Calcul du classement final...');
  panel.appendChild(hint);
  screen.appendChild(panel);
  root.appendChild(screen);

  const off = netClient.on((msg) => {
    if (msg.type === 'race:start') {
      off();
      const roster = standings.map((s) => ({ id: s.playerId, name: s.name }));
      nav((r, n) => renderPrivateRace(r, n, msg, roster, you));
    } else if (msg.type === 'race:matchOver') {
      off();
      nav((r, n) => renderPrivateMatchOver(r, n, msg.standings, you));
    }
  });
  return () => off();
}

function renderPrivateMatchOver(root: HTMLElement, nav: Navigate, standings: RoundResult[], you: string) {
  const won = standings[0]?.playerId === you;
  if (won) {
    SaveManager.addTotals({ privateWins: 1, victories: 1 });
  }
  const screen = el('div', 'screen');
  screen.innerHTML = `<h2>🏁 Classement final</h2>`;
  const panel = el('div', 'panel');
  panel.innerHTML = `${won ? '<div class="record-badge">🏆 Tu as gagné cette partie !</div>' : ''}${resultTable(standings, you)}`;
  const menuBtn = el('button', 'btn primary', 'Retour au menu');
  menuBtn.style.marginTop = '16px';
  menuBtn.onclick = () => nav(renderMenu);
  panel.appendChild(menuBtn);
  screen.appendChild(panel);
  root.appendChild(screen);
}
