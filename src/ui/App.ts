import { HostNetwork, ClientNetwork } from "../net/PeerNetwork";
import type { GameMode, PlayerMeta, ResultEntry, HostToClientMessage, BotDifficulty } from "../net/protocol";
import { generateRoomCode, randomColor } from "../utils/id";
import { GameController } from "../game/GameController";
import { CIRCUITS } from "../game/course/circuits";
import { SHOOTER_MAPS } from "../game/shooter/maps";
import { KART_TRACKS } from "../game/kart/tracks";
import { LAPS_TOTAL } from "../game/kart/sim";

const PROFILE_KEY = "party-arena-profile-v1";
const MAX_PLAYERS = 10;
const BOT_NAMES = ["Robo-Lea", "Ricochet", "Turbo-Max", "Nina-Bot", "Ombre", "Static", "Ecco", "Ziggy", "Volt", "Pixel"];
const AVATAR_COLORS = ["#ff5d73", "#4dd6ff", "#ffd166", "#8b5cf6", "#4ade80", "#fb923c", "#f472b6", "#38bdf8", "#a3e635", "#c084fc"];

interface Profile {
  name: string;
  color: string;
}

type Screen = "profile" | "home" | "lobby" | "game";

export class App {
  private root: HTMLElement;
  private profile: Profile;
  private screen: Screen = "profile";

  private isHost = false;
  private solo = false;
  private roomCode = "";
  private localId = "";
  private hostNetwork: HostNetwork | null = null;
  private clientNetwork: ClientNetwork | null = null;

  private players: PlayerMeta[] = [];
  private mode: GameMode | null = null;
  private levelId: string | null = null;
  private botDifficulty: BotDifficulty = "normal";

  private gameController: GameController | null = null;
  private hudTimer = 0;
  private lastResults: ResultEntry[] | null = null;

  constructor(root: HTMLElement) {
    this.root = root;
    this.profile = this.loadProfile();
  }

  start() {
    const params = new URLSearchParams(location.search);
    const roomFromUrl = params.get("room");
    if (this.profile.name) {
      this.screen = "home";
      this.renderHome(roomFromUrl ?? "");
    } else {
      this.renderProfile(() => {
        this.screen = "home";
        this.renderHome(roomFromUrl ?? "");
      });
    }
  }

  // ---------------------------------------------------------------------
  // Persistence
  // ---------------------------------------------------------------------
  private loadProfile(): Profile {
    try {
      const raw = localStorage.getItem(PROFILE_KEY);
      if (raw) return JSON.parse(raw);
    } catch {
      /* ignore */
    }
    return { name: "", color: AVATAR_COLORS[Math.floor(Math.random() * AVATAR_COLORS.length)] };
  }

  private saveProfile() {
    try {
      localStorage.setItem(PROFILE_KEY, JSON.stringify(this.profile));
    } catch {
      /* ignore */
    }
  }

  // ---------------------------------------------------------------------
  // Screen: Profile
  // ---------------------------------------------------------------------
  private renderProfile(onDone: () => void) {
    this.root.innerHTML = `
      <div class="screen">
        <div class="logo">Party Arena</div>
        <div class="tagline">Choisis ton pseudo et ta couleur avant de jouer</div>
        <div class="card">
          <h2>Ton profil</h2>
          <input type="text" id="name-input" placeholder="Ton pseudo" maxlength="16" value="${escapeHtml(this.profile.name)}" />
          <div class="row" id="color-row" style="flex-wrap:wrap;margin-bottom:16px;">
            ${AVATAR_COLORS.map((c) => `<button type="button" class="color-swatch" data-color="${c}" style="background:${c};height:38px;border-radius:50%;flex:0 0 38px;${c === this.profile.color ? "outline:3px solid #fff;" : ""}"></button>`).join("")}
          </div>
          <button class="primary" id="continue-btn">Continuer</button>
          <div class="error-msg" id="profile-error"></div>
        </div>
      </div>
    `;
    let chosenColor = this.profile.color;
    this.root.querySelectorAll<HTMLButtonElement>(".color-swatch").forEach((btn) => {
      btn.addEventListener("click", () => {
        chosenColor = btn.dataset.color!;
        this.root.querySelectorAll<HTMLButtonElement>(".color-swatch").forEach((b) => (b.style.outline = "none"));
        btn.style.outline = "3px solid #fff";
      });
    });
    const nameInput = this.root.querySelector<HTMLInputElement>("#name-input")!;
    this.root.querySelector("#continue-btn")!.addEventListener("click", () => {
      const name = nameInput.value.trim();
      const err = this.root.querySelector("#profile-error")!;
      if (!name) {
        err.textContent = "Entre un pseudo pour continuer.";
        return;
      }
      this.profile = { name: name.slice(0, 16), color: chosenColor };
      this.saveProfile();
      onDone();
    });
  }

  // ---------------------------------------------------------------------
  // Screen: Home
  // ---------------------------------------------------------------------
  private renderHome(prefillCode: string) {
    this.screen = "home";
    this.root.innerHTML = `
      <div class="screen">
        <div class="logo">Party Arena</div>
        <div class="tagline">Course ou tir, entre amis ou contre des bots — jusqu'à ${MAX_PLAYERS} joueurs</div>
        <div class="card">
          <h2>Ton profil</h2>
          <div class="row" style="align-items:center;">
            <div style="width:34px;height:34px;border-radius:50%;background:${this.profile.color};flex:0 0 34px;"></div>
            <div style="flex:1;font-weight:700;">${escapeHtml(this.profile.name)}</div>
            <button class="ghost small" id="edit-profile">Modifier</button>
          </div>
        </div>
        <div class="card">
          <h2>Créer une partie</h2>
          <button class="primary" id="create-btn">Créer une partie</button>
          <div class="hint">Tu deviens l'hôte : ton navigateur fait tourner la partie et tu obtiens un lien à partager.</div>
        </div>
        <div class="card">
          <h2>Rejoindre une partie</h2>
          <input type="text" id="join-code" placeholder="Code de la partie (ex: AB3XZ)" maxlength="8" value="${escapeHtml(prefillCode)}" style="text-transform:uppercase;" />
          <button class="accent" id="join-btn">Rejoindre</button>
          <div class="error-msg" id="join-error"></div>
        </div>
        <div class="card">
          <h2>Pas assez de monde ?</h2>
          <button class="ghost" id="solo-btn">Jouer seul contre des bots</button>
          <div class="hint">Aucune connexion requise, tout tourne dans ton navigateur.</div>
        </div>
      </div>
    `;

    this.root.querySelector("#edit-profile")!.addEventListener("click", () => {
      this.renderProfile(() => this.renderHome(""));
    });
    this.root.querySelector("#create-btn")!.addEventListener("click", () => this.createRoom());
    this.root.querySelector("#solo-btn")!.addEventListener("click", () => this.startSolo());
    const joinInput = this.root.querySelector<HTMLInputElement>("#join-code")!;
    this.root.querySelector("#join-btn")!.addEventListener("click", () => {
      const code = joinInput.value.trim();
      if (!code) {
        this.root.querySelector("#join-error")!.textContent = "Entre un code de partie.";
        return;
      }
      this.joinRoom(code);
    });
  }

  // ---------------------------------------------------------------------
  // Networking: create / join
  // ---------------------------------------------------------------------
  private createRoom() {
    this.isHost = true;
    this.solo = false;
    this.roomCode = generateRoomCode();
    this.mode = null;
    this.levelId = null;
    const net = new HostNetwork();
    this.hostNetwork = net;

    net.onStatus = (status, detail) => {
      if (status === "open") {
        this.localId = net.peer!.id;
        this.players = [{ id: this.localId, name: this.profile.name, color: this.profile.color, isBot: false }];
        this.renderLobby();
      } else if (status === "error") {
        this.showFatalError(`Impossible de créer la partie (${detail ?? "erreur inconnue"}). Réessaie.`);
      }
    };
    net.onPeerJoin = () => {
      /* wait for their "hello" before listing them */
    };
    net.onPeerLeave = (peerId) => {
      this.players = this.players.filter((p) => p.id !== peerId);
      this.broadcastLobby();
      if (this.screen === "lobby") this.renderLobby();
    };
    net.onMessage = (peerId, msg) => {
      if (msg.t === "hello" || msg.t === "profile") {
        const existing = this.players.find((p) => p.id === peerId);
        if (existing) {
          existing.name = msg.name.slice(0, 16);
          existing.color = msg.color;
        } else if (this.players.length < MAX_PLAYERS) {
          this.players.push({ id: peerId, name: msg.name.slice(0, 16), color: msg.color, isBot: false });
        }
        this.broadcastLobby();
        if (this.screen === "lobby") this.renderLobby();
      } else if (msg.t === "input") {
        this.gameController?.handlePeerInput(peerId, msg.input);
      }
    };
    net.start(this.roomCode);
    this.screen = "lobby";
    this.renderConnectingLobby("Création de la partie...");
  }

  private startSolo() {
    this.isHost = true;
    this.solo = true;
    this.roomCode = "";
    this.localId = "solo-player";
    this.mode = null;
    this.levelId = null;
    this.players = [{ id: this.localId, name: this.profile.name, color: this.profile.color, isBot: false }];
    this.renderLobby();
  }

  private joinRoom(code: string) {
    this.isHost = false;
    this.solo = false;
    this.roomCode = code.trim().toUpperCase();
    const net = new ClientNetwork();
    this.clientNetwork = net;

    net.onStatus = (status, detail) => {
      if (status === "open") {
        this.localId = net.peer!.id;
        net.send({ t: "hello", name: this.profile.name, color: this.profile.color });
      } else if (status === "error") {
        const msg =
          detail === "peer-unavailable"
            ? "Aucune partie trouvée avec ce code. Vérifie le code ou demande un nouveau lien."
            : `Connexion impossible (${detail ?? "erreur"}).`;
        this.showFatalError(msg);
      } else if (status === "closed") {
        if (this.screen !== "game") this.showFatalError("La connexion à l'hôte a été fermée.");
      }
    };
    net.onMessage = (msg) => this.handleClientMessage(msg);
    net.join(this.roomCode);
    this.screen = "lobby";
    this.renderConnectingLobby("Connexion à la partie...");
  }

  private handleClientMessage(msg: HostToClientMessage) {
    switch (msg.t) {
      case "lobby":
        this.players = msg.players;
        this.mode = msg.mode;
        this.levelId = msg.levelId;
        if (this.screen === "lobby") this.renderLobby();
        break;
      case "gameStart":
        this.beginGame(msg.mode, msg.levelId, msg.seed, msg.players, msg.startAt, msg.botDifficulty);
        break;
      case "courseState":
      case "shooterState":
      case "kartState":
        this.gameController?.handleSnapshotMessage(msg);
        break;
      case "gameOver":
        this.showResults(msg.results);
        break;
      case "toLobby":
        this.gameController?.stop();
        this.gameController = null;
        this.screen = "lobby";
        this.renderLobby();
        break;
    }
  }

  private broadcastLobby() {
    this.hostNetwork?.broadcast({ t: "lobby", players: this.players, hostId: this.localId, mode: this.mode, levelId: this.levelId });
  }

  private showFatalError(message: string) {
    this.hostNetwork?.destroy();
    this.clientNetwork?.destroy();
    this.hostNetwork = null;
    this.clientNetwork = null;
    this.root.innerHTML = `
      <div class="screen">
        <div class="logo">Party Arena</div>
        <div class="card">
          <h2>Oups</h2>
          <div class="error-msg" style="min-height:auto;margin-bottom:12px;">${escapeHtml(message)}</div>
          <button class="primary" id="back-home">Retour à l'accueil</button>
        </div>
      </div>
    `;
    this.root.querySelector("#back-home")!.addEventListener("click", () => {
      history.replaceState(null, "", location.pathname);
      this.renderHome("");
    });
  }

  // ---------------------------------------------------------------------
  // Screen: Lobby
  // ---------------------------------------------------------------------
  private renderConnectingLobby(text: string) {
    this.root.innerHTML = `
      <div class="screen">
        <div class="logo">Party Arena</div>
        <div class="card"><h2>${escapeHtml(text)}</h2><div class="hint">Un instant...</div></div>
      </div>
    `;
  }

  private renderLobby() {
    this.screen = "lobby";
    const shareUrl = `${location.origin}${location.pathname}?room=${this.roomCode}`;
    const canStart = !!this.mode && !!this.levelId && this.players.length >= 1;

    const modeMeta: Record<GameMode, { emoji: string; name: string }> = {
      course: { emoji: "🏃", name: "Parkour" },
      shooter: { emoji: "🔫", name: "Tir" },
      kart: { emoji: "🏎️", name: "Course" },
    };
    const modeCards = (["course", "shooter", "kart"] as GameMode[])
      .map(
        (m) => `
        <div class="mode-card ${this.mode === m ? "selected" : ""}" data-mode="${m}">
          <span class="emoji">${modeMeta[m].emoji}</span>
          <span class="name">${modeMeta[m].name}</span>
        </div>`
      )
      .join("");

    const botDifficultyMeta: Record<BotDifficulty, { emoji: string; name: string }> = {
      easy: { emoji: "🙂", name: "Facile" },
      normal: { emoji: "😐", name: "Normal" },
      hard: { emoji: "😈", name: "Difficile" },
    };
    const botDifficultyCards = (["easy", "normal", "hard"] as BotDifficulty[])
      .map(
        (d) => `
        <div class="mode-card ${this.botDifficulty === d ? "selected" : ""}" data-bot-difficulty="${d}">
          <span class="emoji">${botDifficultyMeta[d].emoji}</span>
          <span class="name">${botDifficultyMeta[d].name}</span>
        </div>`
      )
      .join("");

    const levels = this.mode === "shooter" ? SHOOTER_MAPS : this.mode === "course" ? CIRCUITS : this.mode === "kart" ? KART_TRACKS : [];
    const levelCards = levels
      .map(
        (l) => `
        <div class="mode-card ${this.levelId === l.id ? "selected" : ""}" data-level="${l.id}">
          <span class="emoji">${this.mode === "course" ? "🏁" : this.mode === "kart" ? "🏁" : "🗺️"}</span>
          <span class="name">${escapeHtml(l.name)}</span>
        </div>`
      )
      .join("");

    const playerRows = this.players
      .map(
        (p) => `
        <div class="player-row ${p.isBot ? "bot" : ""}">
          <div class="dot" style="background:${p.color}"></div>
          <div class="name">${escapeHtml(p.name)}</div>
          ${p.id === this.localId ? '<span class="tag">toi</span>' : ""}
          ${p.isBot ? '<span class="tag">bot</span>' : ""}
          ${this.isHost && p.isBot ? `<button class="ghost small remove-bot" data-id="${p.id}">Retirer</button>` : ""}
        </div>`
      )
      .join("");

    this.root.innerHTML = `
      <div class="screen">
        <div class="logo" style="font-size:1.8rem;">Party Arena</div>
        ${
          this.solo
            ? ""
            : `<div class="card">
          <h2>Inviter des joueurs</h2>
          <div class="share-box">
            <code id="share-url">${shareUrl}</code>
            <button class="small accent" id="copy-link">Copier</button>
          </div>
          <div class="hint">Code de la partie : <b>${this.roomCode}</b></div>
        </div>`
        }
        <div class="card">
          <h2>Joueurs (${this.players.length}/${MAX_PLAYERS})</h2>
          <div class="player-list">${playerRows}</div>
          ${this.isHost ? `<button class="ghost" id="add-bot" ${this.players.length >= MAX_PLAYERS ? "disabled" : ""}>+ Ajouter un bot</button>` : ""}
          ${
            this.isHost && this.players.some((p) => p.isBot)
              ? `<div class="hint" style="margin-top:12px;">Difficulté des bots</div>
                 <div class="mode-select" style="margin-bottom:0;">${botDifficultyCards}</div>`
              : ""
          }
        </div>
        ${
          this.isHost
            ? `<div class="card">
                <h2>Mode de jeu</h2>
                <div class="mode-select">${modeCards}</div>
                ${this.mode ? `<div class="mode-select">${levelCards}</div>` : ""}
                <button class="primary" id="start-btn" ${canStart ? "" : "disabled"}>Démarrer la partie</button>
              </div>`
            : `<div class="card">
                <h2>Mode de jeu</h2>
                <div class="hint">${this.mode ? `${modeMeta[this.mode].name} — ${this.levelId ?? "..."}` : "En attente du choix de l'hôte..."}</div>
                <div class="hint" style="margin-top:8px;">En attente que l'hôte démarre la partie...</div>
              </div>`
        }
        <button class="ghost small" id="leave-lobby-btn" style="width:auto;margin-top:4px;">Quitter la partie</button>
      </div>
    `;

    this.root.querySelector("#leave-lobby-btn")?.addEventListener("click", () => this.leaveToHome());
    this.root.querySelector("#copy-link")?.addEventListener("click", () => {
      navigator.clipboard?.writeText(shareUrl).catch(() => {});
      const btn = this.root.querySelector("#copy-link")!;
      btn.textContent = "Copié !";
      setTimeout(() => (btn.textContent = "Copier"), 1500);
    });

    if (this.isHost) {
      this.root.querySelector("#add-bot")?.addEventListener("click", () => {
        if (this.players.length >= MAX_PLAYERS) return;
        const botIndex = this.players.filter((p) => p.isBot).length;
        const id = `bot-${Date.now()}-${botIndex}`;
        this.players.push({
          id,
          name: BOT_NAMES[botIndex % BOT_NAMES.length],
          color: randomColor(this.players.length),
          isBot: true,
        });
        this.broadcastLobby();
        this.renderLobby();
      });
      this.root.querySelectorAll<HTMLButtonElement>(".remove-bot").forEach((btn) => {
        btn.addEventListener("click", () => {
          this.players = this.players.filter((p) => p.id !== btn.dataset.id);
          this.broadcastLobby();
          this.renderLobby();
        });
      });
      this.root.querySelectorAll<HTMLElement>("[data-bot-difficulty]").forEach((el) => {
        el.addEventListener("click", () => {
          this.botDifficulty = el.dataset.botDifficulty as BotDifficulty;
          this.renderLobby();
        });
      });
      this.root.querySelectorAll<HTMLElement>("[data-mode]").forEach((el) => {
        el.addEventListener("click", () => {
          this.mode = el.dataset.mode as GameMode;
          this.levelId = this.mode === "course" ? CIRCUITS[0].id : this.mode === "kart" ? KART_TRACKS[0].id : SHOOTER_MAPS[0].id;
          this.broadcastLobby();
          this.renderLobby();
        });
      });
      this.root.querySelectorAll<HTMLElement>("[data-level]").forEach((el) => {
        el.addEventListener("click", () => {
          this.levelId = el.dataset.level!;
          this.broadcastLobby();
          this.renderLobby();
        });
      });
      this.root.querySelector("#start-btn")?.addEventListener("click", () => {
        if (!this.mode || !this.levelId) return;
        this.startGameAsHost(this.mode, this.levelId);
      });
    }
  }

  // ---------------------------------------------------------------------
  // Game lifecycle
  // ---------------------------------------------------------------------
  private startGameAsHost(mode: GameMode, levelId: string) {
    const seed = Math.floor(Math.random() * 1_000_000_000);
    const startAt = Date.now() + 3000;
    const players = [...this.players];
    const botDifficulty = this.botDifficulty;
    this.hostNetwork?.broadcast({ t: "gameStart", mode, levelId, seed, players, startAt, botDifficulty });
    this.beginGame(mode, levelId, seed, players, startAt, botDifficulty);
  }

  private beginGame(
    mode: GameMode,
    levelId: string,
    seed: number,
    players: PlayerMeta[],
    startAt: number,
    botDifficulty: BotDifficulty
  ) {
    this.mode = mode;
    this.levelId = levelId;
    this.players = players;
    this.lastResults = null;
    this.screen = "game";
    this.renderGameShell(mode);

    const canvas = this.root.querySelector<HTMLCanvasElement>("#game-canvas")!;
    const touchRoot = this.root.querySelector<HTMLElement>("#touch-root")!;
    const countdownEl = this.root.querySelector<HTMLElement>("#countdown")!;

    this.gameController = new GameController(
      this.isHost,
      this.localId,
      { mode, levelId, seed, players, startAt, botDifficulty },
      canvas,
      touchRoot,
      countdownEl,
      this.hostNetwork,
      this.clientNetwork,
      (results) => this.showResults(results)
    );
    this.gameController.start();

    clearInterval(this.hudTimer);
    this.hudTimer = window.setInterval(() => this.updateHud(), 300);
  }

  private renderGameShell(mode: GameMode) {
    this.root.innerHTML = `
      <div class="screen" id="game-screen">
        <canvas id="game-canvas"></canvas>
        <div class="hud">
          <div class="hud-panel leaderboard" id="hud-leaderboard"></div>
          <div class="hud-right">
            <button class="ghost small" id="quit-btn">Quitter</button>
            <div class="hud-panel" id="hud-timer">0:00</div>
          </div>
        </div>
        <div class="countdown" id="countdown" hidden>3</div>
        <div id="touch-root"></div>
        ${mode === "course" ? '<div class="course-hint">Ton personnage avance tout seul — appuie n\'importe où pour sauter</div>' : ""}
        ${mode === "kart" ? '<div class="course-hint">Ta voiture avance toute seule — dirige avec les flèches ou le volant</div>' : ""}
        <div class="rotate-hint">🔄 Tourne ton téléphone en paysage pour jouer</div>
        <div class="results-overlay" id="results-overlay" hidden></div>
      </div>
    `;
    this.root.querySelector("#quit-btn")!.addEventListener("click", () => this.returnToLobby());
  }

  private updateHud() {
    if (!this.gameController || this.screen !== "game") return;
    const { course, shooter, kart } = this.gameController.getHudSnapshot();
    const board = this.root.querySelector("#hud-leaderboard");
    const timerEl = this.root.querySelector("#hud-timer");
    if (!board || !timerEl) return;

    if (course) {
      timerEl.textContent = formatTime(course.elapsedMs);
      const ranked = [...course.entities].sort((a, b) => {
        if (a.finished && b.finished) return (a.finishTimeMs ?? 0) - (b.finishTimeMs ?? 0);
        if (a.finished) return -1;
        if (b.finished) return 1;
        return b.distance - a.distance;
      });
      board.innerHTML = ranked
        .slice(0, 6)
        .map((e, i) => {
          const meta = this.gameController!.metas.get(e.id);
          const cls = e.id === this.localId ? "me" : "";
          const label = e.finished ? "🏁" : `${Math.round(e.distance)}m`;
          return `<div class="${cls}">${i + 1}. ${escapeHtml(meta?.name ?? "?")} — ${label}</div>`;
        })
        .join("");
    } else if (shooter) {
      timerEl.textContent = formatTime(shooter.elapsedMs);
      const ranked = [...shooter.entities].sort((a, b) => b.kills - a.kills);
      board.innerHTML = ranked
        .slice(0, 6)
        .map((e, i) => {
          const meta = this.gameController!.metas.get(e.id);
          const cls = e.id === this.localId ? "me" : "";
          return `<div class="${cls}">${i + 1}. ${escapeHtml(meta?.name ?? "?")} — ${e.kills} 🎯</div>`;
        })
        .join("");
    } else if (kart) {
      timerEl.textContent = formatTime(kart.elapsedMs);
      const ranked = [...kart.entities].sort((a, b) => {
        if (a.finished && b.finished) return (a.finishTimeMs ?? 0) - (b.finishTimeMs ?? 0);
        if (a.finished) return -1;
        if (b.finished) return 1;
        return b.lap - a.lap || b.nextWaypoint - a.nextWaypoint;
      });
      board.innerHTML = ranked
        .slice(0, 6)
        .map((e, i) => {
          const meta = this.gameController!.metas.get(e.id);
          const cls = e.id === this.localId ? "me" : "";
          const label = e.finished ? "🏁" : `Tour ${Math.min(e.lap + 1, LAPS_TOTAL)}/${LAPS_TOTAL}`;
          return `<div class="${cls}">${i + 1}. ${escapeHtml(meta?.name ?? "?")} — ${label}</div>`;
        })
        .join("");
    }
  }

  private showResults(results: ResultEntry[]) {
    this.lastResults = results;
    const overlay = this.root.querySelector<HTMLElement>("#results-overlay");
    if (!overlay) return;
    const medals = ["🥇", "🥈", "🥉"];
    overlay.innerHTML = `
      <h2>Résultats</h2>
      <div class="results-list">
        ${results
          .map(
            (r) => `
          <div class="result-row ${r.id === this.localId ? "me" : ""}">
            <span class="rank">${medals[r.rank - 1] ?? r.rank}</span>
            <div style="width:12px;height:12px;border-radius:50%;background:${r.color};"></div>
            <div style="flex:1;">${escapeHtml(r.name)}</div>
            <div>${
              r.kills !== undefined
                ? `${r.kills} 🎯 / ${r.deaths} 💀`
                : r.laps !== undefined
                  ? r.finished
                    ? formatTime(r.timeMs ?? 0)
                    : `${r.laps}/${LAPS_TOTAL} tours`
                  : r.finished
                    ? formatTime(r.timeMs ?? 0)
                    : `${r.distance}m`
            }</div>
          </div>`
          )
          .join("")}
      </div>
      ${this.isHost ? '<button class="primary" id="back-to-lobby-btn" style="width:min(420px,92vw);">Retour au lobby</button>' : '<div class="hint">En attente que l\'hôte relance...</div>'}
    `;
    overlay.hidden = false;
    if (this.isHost) {
      overlay.querySelector("#back-to-lobby-btn")!.addEventListener("click", () => this.returnToLobby());
    }
  }

  private returnToLobby() {
    this.gameController?.stop();
    this.gameController = null;
    clearInterval(this.hudTimer);
    if (this.isHost) {
      this.hostNetwork?.broadcast({ t: "toLobby" });
      this.broadcastLobby();
    }
    this.screen = "lobby";
    this.renderLobby();
  }

  private leaveToHome() {
    this.gameController?.stop();
    this.gameController = null;
    clearInterval(this.hudTimer);
    this.hostNetwork?.destroy();
    this.clientNetwork?.destroy();
    this.hostNetwork = null;
    this.clientNetwork = null;
    this.solo = false;
    this.players = [];
    this.mode = null;
    this.levelId = null;
    history.replaceState(null, "", location.pathname);
    this.renderHome("");
  }
}

function formatTime(ms: number): string {
  const totalSec = Math.floor(ms / 1000);
  const m = Math.floor(totalSec / 60);
  const s = totalSec % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
}
