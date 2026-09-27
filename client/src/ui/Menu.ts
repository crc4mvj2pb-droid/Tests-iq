import { CHARACTER_DEFS } from '../player/characters';
import type { CharacterId, PlayerMeta } from '@shared/protocol';

export interface MenuCallbacks {
  onSolo: (name: string, character: CharacterId) => void;
  onCreateRoom: (name: string, character: CharacterId) => void;
  onJoinRoom: (code: string, name: string, character: CharacterId) => void;
  onToggleReady: (ready: boolean) => void;
  onStart: () => void;
  onLeaveLobby: () => void;
  onRestart: () => void;
  onBackToMenu: () => void;
}

type ScreenName = 'main' | 'mp-choice' | 'join' | 'lobby' | 'victory';

const NAME_KEY = 'sommet.name';
const CHAR_KEY = 'sommet.character';

export class Menu {
  private root: HTMLElement;
  private screens = new Map<ScreenName, HTMLElement>();
  private selectedCharacter: CharacterId = (localStorage.getItem(CHAR_KEY) as CharacterId) || 'renard';
  private nameInput!: HTMLInputElement;
  private joinInput!: HTMLInputElement;
  private lobbyCodeEl!: HTMLElement;
  private lobbyListEl!: HTMLElement;
  private lobbyStartBtn!: HTMLButtonElement;
  private lobbyReadyBtn!: HTMLButtonElement;
  private mpChoiceErrorEl!: HTMLElement;
  private joinErrorEl!: HTMLElement;
  private victoryStatsEl!: HTMLElement;
  private isHost = false;

  constructor(container: HTMLElement, private cb: MenuCallbacks) {
    this.root = document.createElement('div');
    container.appendChild(this.root);
    this.buildMain();
    this.buildMpChoice();
    this.buildJoin();
    this.buildLobby();
    this.buildVictory();
    this.showScreen('main');
  }

  private charGrid(onPick?: () => void): HTMLElement {
    const grid = document.createElement('div');
    grid.className = 'char-grid';
    const cards: HTMLElement[] = [];
    for (const def of Object.values(CHARACTER_DEFS)) {
      const card = document.createElement('div');
      card.className = 'char-card' + (def.id === this.selectedCharacter ? ' selected' : '');
      const swatch = document.createElement('div');
      swatch.className = 'swatch';
      swatch.style.background = def.primary;
      card.appendChild(swatch);
      const label = document.createElement('div');
      label.textContent = def.label;
      card.appendChild(label);
      card.addEventListener('click', () => {
        this.selectedCharacter = def.id;
        localStorage.setItem(CHAR_KEY, def.id);
        cards.forEach((c) => c.classList.remove('selected'));
        card.classList.add('selected');
        onPick?.();
      });
      grid.appendChild(card);
      cards.push(card);
    }
    return grid;
  }

  private screen(name: ScreenName): HTMLElement {
    const el = document.createElement('div');
    el.className = 'screen hidden interactive';
    this.root.appendChild(el);
    this.screens.set(name, el);
    return el;
  }

  showScreen(name: ScreenName) {
    for (const [n, el] of this.screens) el.classList.toggle('hidden', n !== name);
  }

  hideAll() {
    for (const el of this.screens.values()) el.classList.add('hidden');
  }

  getName(): string {
    return this.nameInput.value.trim().slice(0, 16) || 'Aventurier';
  }

  getCharacter(): CharacterId {
    return this.selectedCharacter;
  }

  showMpError(msg: string) {
    this.mpChoiceErrorEl.textContent = msg;
    this.joinErrorEl.textContent = msg;
  }

  private buildMain() {
    const el = this.screen('main');
    const panel = document.createElement('div');
    panel.className = 'panel';
    panel.innerHTML = `
      <div class="title">SOMMET</div>
      <div class="subtitle">Escalade la montagne, seul ou en famille. Gère ton endurance, ramasse des objets, et atteins le sommet avant la tempête.</div>
    `;
    const label1 = document.createElement('div');
    label1.className = 'section-label';
    label1.textContent = 'Ton nom';
    panel.appendChild(label1);

    this.nameInput = document.createElement('input');
    this.nameInput.className = 'field';
    this.nameInput.maxLength = 16;
    this.nameInput.placeholder = 'Aventurier';
    this.nameInput.value = localStorage.getItem(NAME_KEY) || '';
    this.nameInput.addEventListener('input', () => localStorage.setItem(NAME_KEY, this.nameInput.value));
    panel.appendChild(this.nameInput);

    const label2 = document.createElement('div');
    label2.className = 'section-label';
    label2.textContent = 'Ton personnage';
    panel.appendChild(label2);
    panel.appendChild(this.charGrid());

    const soloBtn = document.createElement('button');
    soloBtn.className = 'btn btn-primary';
    soloBtn.textContent = '🏔 Jouer en solo';
    soloBtn.style.marginTop = '18px';
    soloBtn.addEventListener('click', () => this.cb.onSolo(this.getName(), this.selectedCharacter));
    panel.appendChild(soloBtn);

    const mpBtn = document.createElement('button');
    mpBtn.className = 'btn';
    mpBtn.textContent = '👨‍👩‍👧 Multijoueur avec ta famille';
    mpBtn.addEventListener('click', () => this.showScreen('mp-choice'));
    panel.appendChild(mpBtn);

    const hint = document.createElement('div');
    hint.className = 'hint-text';
    hint.textContent = 'Sur téléphone : joystick à gauche, glisse à droite pour la caméra. Sur ordinateur : ZQSD/WASD + souris.';
    panel.appendChild(hint);

    el.appendChild(panel);
  }

  private buildMpChoice() {
    const el = this.screen('mp-choice');
    const panel = document.createElement('div');
    panel.className = 'panel';
    panel.innerHTML = `<div class="title" style="font-size:28px">Multijoueur</div>
      <div class="subtitle">Crée une partie et partage le code à 4 chiffres avec ta famille, ou rejoins une partie existante.</div>`;

    this.mpChoiceErrorEl = document.createElement('div');
    this.mpChoiceErrorEl.className = 'error-text';
    panel.appendChild(this.mpChoiceErrorEl);

    const createBtn = document.createElement('button');
    createBtn.className = 'btn btn-primary';
    createBtn.textContent = '➕ Créer une partie';
    createBtn.addEventListener('click', () => this.cb.onCreateRoom(this.getName(), this.selectedCharacter));
    panel.appendChild(createBtn);

    const joinBtn = document.createElement('button');
    joinBtn.className = 'btn';
    joinBtn.textContent = '🔑 Rejoindre avec un code';
    joinBtn.addEventListener('click', () => this.showScreen('join'));
    panel.appendChild(joinBtn);

    const backBtn = document.createElement('button');
    backBtn.className = 'btn btn-ghost';
    backBtn.textContent = '← Retour';
    backBtn.addEventListener('click', () => this.showScreen('main'));
    panel.appendChild(backBtn);

    el.appendChild(panel);
  }

  private buildJoin() {
    const el = this.screen('join');
    const panel = document.createElement('div');
    panel.className = 'panel';
    panel.innerHTML = `<div class="title" style="font-size:28px">Rejoindre</div>`;

    const label = document.createElement('div');
    label.className = 'section-label';
    label.textContent = 'Ton personnage';
    panel.appendChild(label);
    panel.appendChild(this.charGrid());

    this.joinInput = document.createElement('input');
    this.joinInput.className = 'field';
    this.joinInput.placeholder = 'Code à 4 chiffres';
    this.joinInput.inputMode = 'numeric';
    this.joinInput.maxLength = 4;
    panel.appendChild(this.joinInput);

    const err = document.createElement('div');
    err.className = 'error-text';
    this.joinErrorEl = err;
    panel.appendChild(err);

    const goBtn = document.createElement('button');
    goBtn.className = 'btn btn-primary';
    goBtn.textContent = 'Rejoindre';
    goBtn.addEventListener('click', () => this.cb.onJoinRoom(this.joinInput.value.trim(), this.getName(), this.selectedCharacter));
    panel.appendChild(goBtn);

    const backBtn = document.createElement('button');
    backBtn.className = 'btn btn-ghost';
    backBtn.textContent = '← Retour';
    backBtn.addEventListener('click', () => this.showScreen('mp-choice'));
    panel.appendChild(backBtn);

    el.appendChild(panel);
  }

  private buildLobby() {
    const el = this.screen('lobby');
    const panel = document.createElement('div');
    panel.className = 'panel';
    panel.innerHTML = `<div class="title" style="font-size:24px">Salle d'attente</div>
      <div class="subtitle">Partage ce code avec ta famille pour qu'elle te rejoigne depuis son téléphone, sa tablette ou son ordinateur.</div>`;

    this.lobbyCodeEl = document.createElement('div');
    this.lobbyCodeEl.className = 'code-display';
    panel.appendChild(this.lobbyCodeEl);

    this.lobbyListEl = document.createElement('div');
    this.lobbyListEl.className = 'lobby-list';
    panel.appendChild(this.lobbyListEl);

    this.lobbyReadyBtn = document.createElement('button');
    this.lobbyReadyBtn.className = 'btn';
    this.lobbyReadyBtn.textContent = '✅ Je suis prêt';
    let ready = false;
    this.lobbyReadyBtn.addEventListener('click', () => {
      ready = !ready;
      this.lobbyReadyBtn.textContent = ready ? '⏳ En attente...' : '✅ Je suis prêt';
      this.cb.onToggleReady(ready);
    });
    panel.appendChild(this.lobbyReadyBtn);

    this.lobbyStartBtn = document.createElement('button');
    this.lobbyStartBtn.className = 'btn btn-primary';
    this.lobbyStartBtn.textContent = "🚀 Lancer l'ascension";
    this.lobbyStartBtn.addEventListener('click', () => this.cb.onStart());
    panel.appendChild(this.lobbyStartBtn);

    const leaveBtn = document.createElement('button');
    leaveBtn.className = 'btn btn-ghost';
    leaveBtn.textContent = 'Quitter';
    leaveBtn.addEventListener('click', () => this.cb.onLeaveLobby());
    panel.appendChild(leaveBtn);

    el.appendChild(panel);
  }

  setLobby(code: string, players: PlayerMeta[], selfId: string) {
    this.lobbyCodeEl.textContent = code;
    this.lobbyListEl.innerHTML = '';
    this.isHost = players.find((p) => p.id === selfId)?.isHost ?? false;
    for (const p of players) {
      const row = document.createElement('div');
      row.className = 'lobby-row' + (p.ready || p.isHost ? ' ready' : '');
      row.innerHTML = `<div class="dot"></div><div class="name">${p.name}${p.id === selfId ? ' (toi)' : ''}</div><div class="tag">${p.isHost ? 'Hôte' : p.ready ? 'Prêt' : 'En attente'}</div>`;
      this.lobbyListEl.appendChild(row);
    }
    this.lobbyStartBtn.style.display = this.isHost ? 'block' : 'none';
    this.lobbyReadyBtn.style.display = this.isHost ? 'none' : 'block';
    const allReady = players.every((p) => p.ready || p.isHost);
    this.lobbyStartBtn.disabled = !allReady;
  }

  private buildVictory() {
    const el = this.screen('victory');
    const panel = document.createElement('div');
    panel.className = 'panel';
    panel.innerHTML = `<div class="title" style="font-size:32px">🏔 Sommet atteint !</div>`;
    this.victoryStatsEl = document.createElement('div');
    this.victoryStatsEl.className = 'subtitle';
    panel.appendChild(this.victoryStatsEl);

    const restartBtn = document.createElement('button');
    restartBtn.className = 'btn btn-primary';
    restartBtn.textContent = '🔁 Recommencer';
    restartBtn.addEventListener('click', () => this.cb.onRestart());
    panel.appendChild(restartBtn);

    const menuBtn = document.createElement('button');
    menuBtn.className = 'btn btn-ghost';
    menuBtn.textContent = 'Menu principal';
    menuBtn.addEventListener('click', () => this.cb.onBackToMenu());
    panel.appendChild(menuBtn);

    el.appendChild(panel);
  }

  showVictory(timeSec: number) {
    const m = Math.floor(timeSec / 60);
    const s = Math.floor(timeSec % 60);
    this.victoryStatsEl.textContent = `Temps d'ascension : ${m}m ${s.toString().padStart(2, '0')}s`;
    this.showScreen('victory');
  }
}
