import { GameEngine } from '../core/game/GameEngine';
import { mountHud } from './Hud';
import { mountTouchControls, type TouchControlsHandle } from './TouchControls';
import { NetClient } from '../net/NetClient';
import type { PlayerInfo } from '../../../shared/types';
import type { Profile } from '../state/Profile';

export interface GameSummitResult {
  timeMs: number;
  checkpoints: number;
  checkpointsTotal: number;
}

export interface GameScreenOptions {
  seed: number;
  net: NetClient | null;
  roster: PlayerInfo[];
  profile: Profile;
  onSummit: (result: GameSummitResult) => void;
  onQuit: () => void;
}

export function renderGame(root: HTMLElement, opts: GameScreenOptions): () => void {
  const container = document.createElement('div');
  container.className = 'game-container';
  const canvasHost = document.createElement('div');
  canvasHost.className = 'game-canvas-host';
  container.appendChild(canvasHost);
  root.appendChild(container);

  const localId = opts.net?.localId || 'local';
  const localName = opts.net ? opts.roster.find((p) => p.id === localId)?.name ?? opts.profile.name : opts.profile.name;
  const localColor = opts.net ? opts.roster.find((p) => p.id === localId)?.color ?? opts.profile.color : opts.profile.color;

  const hud = mountHud(container);
  hud.onExit(() => {
    opts.net?.leave();
    opts.onQuit();
  });

  let checkpointsCollected = 0;
  let checkpointsTotal = 0;
  let touch: TouchControlsHandle | null = null;

  const engine = new GameEngine({
    container: canvasHost,
    seed: opts.seed,
    localId,
    localName,
    localColor,
    initialRoster: opts.roster,
    net: opts.net,
    onHud: (state) => {
      checkpointsCollected = state.checkpointsCollected;
      checkpointsTotal = state.checkpointsTotal;
      hud.update(state);
      touch?.updateJoystick();
    },
    onToast: (msg) => hud.toast(msg),
    onSummit: (timeMs) => {
      window.setTimeout(() => {
        opts.onSummit({ timeMs, checkpoints: checkpointsCollected, checkpointsTotal });
      }, 1400);
    },
  });

  touch = engine.inputManager.isTouch ? mountTouchControls(container, engine.inputManager) : null;

  return () => {
    engine.dispose();
    touch?.destroy();
    hud.destroy();
    container.remove();
  };
}
