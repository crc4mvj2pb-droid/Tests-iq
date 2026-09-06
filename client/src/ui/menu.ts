import { el, type ScreenFn } from './router';
import { renderClassicIntro } from './classic';
import { renderGarage } from './garage';
import { renderProfile } from './profile';
import { renderPrivateHome } from './private';

export const renderMenu: ScreenFn = (root, nav) => {
  const screen = el('div', 'screen');
  screen.innerHTML = `
    <div class="brand">FLIPRUSH</div>
    <div class="subtitle">Course arcade à physique. Accélère, envole-toi, flip, atterris parfaitement.</div>
  `;

  const grid = el('div', 'menu-grid');
  const modes: [string, string, ScreenFn][] = [
    ['▶ JOUER', 'primary', renderClassicIntro],
    ['🔒 PRIVATE', 'accent2', renderPrivateHome],
  ];
  for (const [label, cls, target] of modes) {
    const btn = el('button', `btn ${cls}`.trim(), label);
    btn.onclick = () => nav(target);
    grid.appendChild(btn);
  }
  screen.appendChild(grid);

  const secondary = el('div', 'menu-secondary');
  const links: [string, ScreenFn][] = [
    ['🚗 Garage', renderGarage],
    ['👤 Profil', renderProfile],
  ];
  for (const [label, target] of links) {
    const btn = el('button', 'btn small ghost', label);
    btn.onclick = () => nav(target);
    secondary.appendChild(btn);
  }
  screen.appendChild(secondary);

  root.appendChild(screen);
};
