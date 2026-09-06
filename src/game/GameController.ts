import type {
  GameMode,
  PlayerMeta,
  InputState,
  ResultEntry,
  HostToClientMessage,
  CourseSnapshot,
  ShooterSnapshot,
  KartSnapshot,
  BotDifficulty,
} from "../net/protocol";
import type { HostNetwork, ClientNetwork } from "../net/PeerNetwork";
import { CourseSimulation } from "./course/sim";
import { CourseRenderer } from "./course/renderer";
import { CourseBotController } from "./course/bots";
import { getCircuit, type CircuitDef } from "./course/circuits";
import { ShooterSimulation } from "./shooter/sim";
import { ShooterRenderer } from "./shooter/renderer";
import { ShooterBotController } from "./shooter/bots";
import { getMap, type ShooterMap } from "./shooter/maps";
import { KartSimulation } from "./kart/sim";
import { KartRenderer } from "./kart/renderer";
import { KartBotController } from "./kart/bots";
import { getTrack, type KartTrack } from "./kart/tracks";
import { InputCapture } from "../input/InputCapture";

export interface GameStartInfo {
  mode: GameMode;
  levelId: string;
  seed: number;
  players: PlayerMeta[];
  startAt: number;
  botDifficulty: BotDifficulty;
}

const FIXED_DT = 1000 / 60;

export class GameController {
  private raf = 0;
  private input: InputCapture;
  public readonly metas = new Map<string, PlayerMeta>();
  private remoteInputs = new Map<string, InputState>();
  private ctx: CanvasRenderingContext2D;
  private circuit: CircuitDef | null = null;
  private map: ShooterMap | null = null;
  private track: KartTrack | null = null;

  private courseSim: CourseSimulation | null = null;
  private shooterSim: ShooterSimulation | null = null;
  private kartSim: KartSimulation | null = null;
  private courseBots: CourseBotController | null = null;
  private shooterBots: ShooterBotController | null = null;
  private kartBots: KartBotController | null = null;
  private lastFrameTime = 0;
  private accumulator = 0;
  private gameOverFired = false;

  private lastCourseSnap: CourseSnapshot | null = null;
  private lastShooterSnap: ShooterSnapshot | null = null;
  private lastKartSnap: KartSnapshot | null = null;

  private courseRenderer = new CourseRenderer();
  private shooterRenderer = new ShooterRenderer();
  private kartRenderer = new KartRenderer();

  constructor(
    private isHost: boolean,
    private localId: string,
    public readonly info: GameStartInfo,
    private canvas: HTMLCanvasElement,
    touchRoot: HTMLElement,
    private countdownEl: HTMLElement,
    private hostNetwork: HostNetwork | null,
    private clientNetwork: ClientNetwork | null,
    private onGameOver: (results: ResultEntry[]) => void
  ) {
    this.ctx = canvas.getContext("2d")!;
    for (const p of info.players) this.metas.set(p.id, p);
    if (info.mode === "course") this.circuit = getCircuit(info.levelId);
    else if (info.mode === "shooter") this.map = getMap(info.levelId);
    else this.track = getTrack(info.levelId);

    this.input = new InputCapture(info.mode, canvas, touchRoot);
    if (info.mode === "shooter") {
      this.input.setNearestEnemyProvider(() => this.findNearestEnemyOffset());
    }
  }

  start() {
    this.resizeCanvas();
    window.addEventListener("resize", this.resizeCanvas);
    this.input.attach();
    (screen.orientation as ScreenOrientation & { lock?: (o: string) => Promise<void> })?.lock?.("landscape").catch(() => {});

    if (this.isHost) {
      const difficulty = this.info.botDifficulty;
      if (this.info.mode === "course" && this.circuit) {
        this.courseSim = new CourseSimulation(this.circuit, this.info.players);
        this.courseBots = new CourseBotController(this.circuit, difficulty);
        for (const p of this.info.players) if (p.isBot) this.courseBots.register(p.id);
      } else if (this.info.mode === "shooter" && this.map) {
        this.shooterSim = new ShooterSimulation(this.map, this.info.seed, this.info.players);
        this.shooterBots = new ShooterBotController();
        for (const p of this.info.players) if (p.isBot) this.shooterBots.register(p.id, difficulty);
      } else if (this.track) {
        this.kartSim = new KartSimulation(this.track, this.info.players);
        this.kartBots = new KartBotController(this.track, difficulty);
        for (const p of this.info.players) if (p.isBot) this.kartBots.register(p.id);
      }
    }

    this.lastFrameTime = performance.now();
    this.raf = requestAnimationFrame(this.loop);
  }

  stop() {
    cancelAnimationFrame(this.raf);
    window.removeEventListener("resize", this.resizeCanvas);
    this.input.detach();
  }

  getHudSnapshot(): { course: CourseSnapshot | null; shooter: ShooterSnapshot | null; kart: KartSnapshot | null } {
    if (this.info.mode === "course") {
      return { course: this.isHost ? this.courseSim?.snapshot() ?? null : this.lastCourseSnap, shooter: null, kart: null };
    }
    if (this.info.mode === "shooter") {
      return { course: null, shooter: this.isHost ? this.shooterSim?.snapshot() ?? null : this.lastShooterSnap, kart: null };
    }
    return { course: null, shooter: null, kart: this.isHost ? this.kartSim?.snapshot() ?? null : this.lastKartSnap };
  }

  handleSnapshotMessage(msg: HostToClientMessage) {
    if (msg.t === "courseState") this.lastCourseSnap = msg.snapshot;
    else if (msg.t === "shooterState") this.lastShooterSnap = msg.snapshot;
    else if (msg.t === "kartState") this.lastKartSnap = msg.snapshot;
  }

  handlePeerInput(peerId: string, input: InputState) {
    this.remoteInputs.set(peerId, input);
  }

  private resizeCanvas = () => {
    this.canvas.width = this.canvas.clientWidth;
    this.canvas.height = this.canvas.clientHeight;
  };

  private findNearestEnemyOffset(): { x: number; y: number } | null {
    const snap = this.isHost ? this.shooterSim?.snapshot() : this.lastShooterSnap;
    if (!snap) return null;
    const me = snap.entities.find((e) => e.id === this.localId);
    if (!me) return null;
    let best: { x: number; y: number } | null = null;
    let bestDist = Infinity;
    for (const e of snap.entities) {
      if (e.id === this.localId || !e.alive) continue;
      const d = Math.hypot(e.x - me.x, e.y - me.y);
      if (d < bestDist) {
        bestDist = d;
        best = { x: e.x - me.x, y: e.y - me.y };
      }
    }
    return best;
  }

  private stepHostSimulation() {
    if (this.info.mode === "course" && this.courseSim && this.courseBots) {
      const snapNow = this.courseSim.snapshot();
      const positions = new Map(snapNow.entities.map((e) => [e.id, { x: e.x, onGround: e.onGround }]));
      const inputs = new Map<string, InputState>(this.remoteInputs);
      inputs.set(this.localId, this.input.getInput());
      for (const p of this.info.players) {
        if (p.isBot) {
          const pos = positions.get(p.id) ?? { x: this.circuit!.startX, onGround: true };
          inputs.set(p.id, this.courseBots.computeInput(p.id, pos.x, pos.onGround));
        }
      }
      this.courseSim.step(FIXED_DT, inputs);
    } else if (this.info.mode === "shooter" && this.shooterSim && this.shooterBots && this.map) {
      const players = this.shooterSim.getPlayersPublic();
      const inputs = new Map<string, InputState>(this.remoteInputs);
      inputs.set(this.localId, this.input.getInput());
      for (const p of this.info.players) {
        if (p.isBot) inputs.set(p.id, this.shooterBots.computeInput(p.id, this.map, players));
      }
      this.shooterSim.step(FIXED_DT, inputs);
    } else if (this.kartSim && this.kartBots) {
      const positions = this.kartSim.getPlayersPublic();
      const byId = new Map(positions.map((p) => [p.id, p]));
      const inputs = new Map<string, InputState>(this.remoteInputs);
      inputs.set(this.localId, this.input.getInput());
      for (const p of this.info.players) {
        if (p.isBot) {
          const pos = byId.get(p.id);
          if (pos) inputs.set(p.id, this.kartBots.computeInput(p.id, pos.x, pos.y, pos.heading, pos.nextWaypoint));
        }
      }
      this.kartSim.step(FIXED_DT, inputs);
    }
  }

  private loop = (now: number) => {
    this.raf = requestAnimationFrame(this.loop);
    const dt = Math.min(now - this.lastFrameTime, 100);
    this.lastFrameTime = now;

    const remaining = this.info.startAt - Date.now();
    this.countdownEl.hidden = remaining <= 0;
    if (remaining > 0) this.countdownEl.textContent = String(Math.ceil(remaining / 1000));

    if (this.isHost) {
      if (remaining <= 0) {
        this.accumulator = Math.min(this.accumulator + dt, FIXED_DT * 6);
        while (this.accumulator >= FIXED_DT) {
          this.stepHostSimulation();
          this.accumulator -= FIXED_DT;
        }
      } else {
        // keep sending local input while the input capturer is warm, but don't simulate yet
        this.input.getInput();
      }

      if (this.info.mode === "course" && this.courseSim && this.circuit) {
        const snap = this.courseSim.snapshot();
        this.hostNetwork?.broadcast({ t: "courseState", snapshot: snap });
        this.courseRenderer.draw(this.ctx, this.canvas.width, this.canvas.height, this.circuit, snap, this.localId, this.metas);
        if (remaining <= 0 && !this.gameOverFired && this.courseSim.isRaceOver()) {
          this.gameOverFired = true;
          const results = this.courseSim.results();
          this.hostNetwork?.broadcast({ t: "gameOver", results });
          this.onGameOver(results);
        }
      } else if (this.info.mode === "shooter" && this.shooterSim && this.map) {
        const snap = this.shooterSim.snapshot();
        this.hostNetwork?.broadcast({ t: "shooterState", snapshot: snap });
        this.shooterRenderer.draw(this.ctx, this.canvas.width, this.canvas.height, this.map, snap, this.localId, this.metas);
        if (remaining <= 0 && !this.gameOverFired && this.shooterSim.isMatchOver()) {
          this.gameOverFired = true;
          const results = this.shooterSim.results();
          this.hostNetwork?.broadcast({ t: "gameOver", results });
          this.onGameOver(results);
        }
      } else if (this.kartSim && this.track) {
        const snap = this.kartSim.snapshot();
        this.hostNetwork?.broadcast({ t: "kartState", snapshot: snap });
        this.kartRenderer.draw(this.ctx, this.canvas.width, this.canvas.height, this.track, snap, this.localId, this.metas);
        if (remaining <= 0 && !this.gameOverFired && this.kartSim.isRaceOver()) {
          this.gameOverFired = true;
          const results = this.kartSim.results();
          this.hostNetwork?.broadcast({ t: "gameOver", results });
          this.onGameOver(results);
        }
      }
    } else {
      this.clientNetwork?.send({ t: "input", input: this.input.getInput() });
      if (this.info.mode === "course" && this.lastCourseSnap && this.circuit) {
        this.courseRenderer.draw(this.ctx, this.canvas.width, this.canvas.height, this.circuit, this.lastCourseSnap, this.localId, this.metas);
      } else if (this.info.mode === "shooter" && this.lastShooterSnap && this.map) {
        this.shooterRenderer.draw(this.ctx, this.canvas.width, this.canvas.height, this.map, this.lastShooterSnap, this.localId, this.metas);
      } else if (this.info.mode === "kart" && this.lastKartSnap && this.track) {
        this.kartRenderer.draw(this.ctx, this.canvas.width, this.canvas.height, this.track, this.lastKartSnap, this.localId, this.metas);
      }
    }
  };
}
