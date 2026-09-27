import './style.css';
import { renderMenu } from './ui/MenuScreen';
import { renderCoopLobby } from './ui/CoopLobbyScreen';
import { renderGame, type GameSummitResult } from './ui/GameScreen';
import { renderResults } from './ui/ResultsScreen';
import { loadProfile } from './state/Profile';
import { randomSeed } from '../../shared/rng';
import type { PlayerInfo } from '../../shared/types';
import { NetClient } from './net/NetClient';

type Screen =
  | { name: 'menu' }
  | { name: 'coop-lobby' }
  | { name: 'game'; seed: number; net: NetClient | null; roster: PlayerInfo[] }
  | { name: 'results'; result: GameSummitResult };

const root = document.getElementById('app');
if (!root) throw new Error('#app introuvable');

let cleanup: (() => void) | null = null;

function show(screen: Screen) {
  if (cleanup) {
    cleanup();
    cleanup = null;
  }
  root!.innerHTML = '';

  if (screen.name === 'menu') {
    cleanup = renderMenu(root!, {
      onSolo: () => show({ name: 'game', seed: randomSeed(), net: null, roster: [] }),
      onCoop: () => show({ name: 'coop-lobby' }),
    });
  } else if (screen.name === 'coop-lobby') {
    cleanup = renderCoopLobby(root!, {
      onBack: () => show({ name: 'menu' }),
      onEnterGame: (net, seed, roster) => show({ name: 'game', seed, net, roster }),
    });
  } else if (screen.name === 'game') {
    cleanup = renderGame(root!, {
      seed: screen.seed,
      net: screen.net,
      roster: screen.roster,
      profile: loadProfile(),
      onSummit: (result) => show({ name: 'results', result }),
      onQuit: () => show({ name: 'menu' }),
    });
  } else if (screen.name === 'results') {
    cleanup = renderResults(root!, {
      ...screen.result,
      onMenu: () => show({ name: 'menu' }),
    });
  }
}

show({ name: 'menu' });
