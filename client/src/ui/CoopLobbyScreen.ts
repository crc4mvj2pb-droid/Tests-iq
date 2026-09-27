import { NetClient } from '../net/NetClient';
import { loadProfile, saveProfile, COLORS } from '../state/Profile';
import type { PlayerInfo } from '../../../shared/types';

export interface CoopLobbyCallbacks {
  onBack: () => void;
  onEnterGame: (net: NetClient, seed: number, roster: PlayerInfo[]) => void;
}

export function renderCoopLobby(root: HTMLElement, cb: CoopLobbyCallbacks): () => void {
  const profile = loadProfile();
  let color = profile.color;
  let net: NetClient | null = null;
  let roster: PlayerInfo[] = [];
  let localId = '';
  let disposed = false;
  let countdownTimer: number | null = null;

  const el = document.createElement('div');
  el.className = 'screen';
  root.appendChild(el);

  function renderSetup() {
    el.innerHTML = `
      <div class="panel">
        <h2>Partie entre amis</h2>
        <div class="field">
          <label>Ton nom</label>
          <input id="name-input" maxlength="18" value="${profile.name}" />
        </div>
        <div class="field">
          <label>Couleur</label>
          <div class="color-row" id="color-row">
            ${COLORS.map((c) => `<button class="color-dot${c === color ? ' selected' : ''}" style="background:${c}" data-color="${c}"></button>`).join('')}
          </div>
        </div>
        <div class="menu-buttons">
          <button class="btn btn-primary" data-action="create">Créer un salon</button>
        </div>
        <div class="field" style="margin-top:18px;">
          <label>Rejoindre avec un code</label>
          <input id="code-input" maxlength="4" placeholder="1234" inputmode="numeric" />
        </div>
        <div class="menu-buttons">
          <button class="btn btn-secondary" data-action="join">Rejoindre</button>
          <button class="btn btn-ghost" data-action="back">Retour</button>
        </div>
        <p class="error-text" id="error-text"></p>
      </div>
    `;

    el.querySelector('#color-row')?.addEventListener('click', (e) => {
      const target = e.target as HTMLElement;
      const c = target.dataset.color;
      if (!c) return;
      color = c;
      profile.color = c;
      saveProfile(profile);
      el.querySelectorAll('.color-dot').forEach((d) => d.classList.remove('selected'));
      target.classList.add('selected');
    });

    el.querySelector('[data-action="back"]')?.addEventListener('click', () => cb.onBack());
    el.querySelector('[data-action="create"]')?.addEventListener('click', () => startConnect('create'));
    el.querySelector('[data-action="join"]')?.addEventListener('click', () => startConnect('join'));
  }

  function currentName(): string {
    const input = el.querySelector<HTMLInputElement>('#name-input');
    const name = input?.value.trim() || profile.name;
    profile.name = name;
    saveProfile(profile);
    return name;
  }

  function setError(msg: string) {
    const errorEl = el.querySelector('#error-text');
    if (errorEl) errorEl.textContent = msg;
  }

  async function startConnect(mode: 'create' | 'join') {
    const name = currentName();
    const code = el.querySelector<HTMLInputElement>('#code-input')?.value.trim() ?? '';
    if (mode === 'join' && code.length !== 4) {
      setError('Entre un code à 4 chiffres.');
      return;
    }
    setError('Connexion…');

    net = new NetClient({
      onRoomCreated: (roomCode, playerId, players) => {
        localId = playerId;
        roster = [...players];
        renderLobby(roomCode);
      },
      onRoomJoined: (roomCode, playerId, players) => {
        localId = playerId;
        roster = [...players];
        renderLobby(roomCode);
      },
      onPlayerJoined: (p) => {
        roster = [...roster, p];
        renderLobby(net?.code ?? '');
      },
      onPlayerLeft: (id) => {
        roster = roster.filter((p) => p.id !== id);
        renderLobby(net?.code ?? '');
      },
      onReadyUpdate: (id, ready) => {
        roster = roster.map((p) => (p.id === id ? { ...p, ready } : p));
        renderLobby(net?.code ?? '');
      },
      onRunStarted: (seed, startAt) => {
        if (disposed || !net) return;
        showCountdown(seed, startAt);
      },
      onError: (message) => setError(message),
      onDisconnected: () => {
        if (!disposed) setError('Connexion au serveur perdue.');
      },
    });

    try {
      await net.connect();
      if (mode === 'create') net.createRoom(name, color);
      else net.joinRoom(code, name, color);
    } catch {
      setError("Impossible de joindre le serveur. Réessaie dans un instant.");
    }
  }

  function renderLobby(code: string) {
    if (disposed) return;
    const isHost = roster.find((p) => p.id === localId)?.isHost ?? false;
    const allReady = roster.length > 0 && roster.every((p) => p.ready);
    el.innerHTML = `
      <div class="panel">
        <h2>Salon coop</h2>
        <div class="room-code">${code}</div>
        <div class="player-list">
          ${roster
            .map(
              (p) => `
            <div class="player-row">
              <span class="player-dot" style="background:${p.color}"></span>
              <span>${p.name}${p.id === localId ? ' (toi)' : ''}${p.isHost ? ' · hôte' : ''}</span>
              <span class="player-ready${p.ready ? ' is-ready' : ''}">${p.ready ? 'Prêt' : 'En attente'}</span>
            </div>`,
            )
            .join('')}
        </div>
        <div class="menu-buttons">
          <button class="btn btn-secondary" data-action="ready">${roster.find((p) => p.id === localId)?.ready ? 'Annuler prêt' : 'Je suis prêt'}</button>
          ${isHost ? `<button class="btn btn-primary" data-action="start" ${allReady ? '' : 'disabled'}>Démarrer l'ascension</button>` : ''}
          <button class="btn btn-ghost" data-action="leave">Quitter le salon</button>
        </div>
        <p class="error-text" id="error-text"></p>
      </div>
    `;
    el.querySelector('[data-action="ready"]')?.addEventListener('click', () => {
      const mine = roster.find((p) => p.id === localId);
      net?.setReady(!(mine?.ready ?? false));
    });
    el.querySelector('[data-action="start"]')?.addEventListener('click', () => net?.startRun());
    el.querySelector('[data-action="leave"]')?.addEventListener('click', () => {
      net?.leave();
      cb.onBack();
    });
  }

  function showCountdown(seed: number, startAt: number) {
    el.innerHTML = `<div class="panel"><h2>Départ imminent…</h2><p class="results-time" id="countdown">3</p></div>`;
    const tick = () => {
      const remaining = Math.max(0, startAt - Date.now());
      const seconds = Math.ceil(remaining / 1000);
      const c = el.querySelector('#countdown');
      if (c) c.textContent = String(seconds);
      if (remaining <= 0) {
        if (countdownTimer) window.clearInterval(countdownTimer);
        if (net) cb.onEnterGame(net, seed, roster);
        return;
      }
    };
    tick();
    countdownTimer = window.setInterval(tick, 200);
  }

  renderSetup();

  return () => {
    disposed = true;
    if (countdownTimer) window.clearInterval(countdownTimer);
    el.remove();
  };
}
