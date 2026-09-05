import { el, type ScreenFn } from './router';
import { CARS } from '../data/cars';
import { SaveManager } from '../state/SaveManager';
import { describeUnlock } from '../data/unlocks';
import { renderMenu } from './menu';

function statBar(label: string, value: number, color: string): string {
  return `<div class="stat-row"><span class="label">${label}</span><div class="stat-bar"><div class="stat-fill" style="width:${(value / 5) * 100}%;background:${color}"></div></div></div>`;
}

export const renderGarage: ScreenFn = (root, nav) => {
  const screen = el('div', 'screen');
  const top = el('div', 'topbar');
  top.innerHTML = `<h2>Garage</h2>`;
  const back = el('button', 'btn small ghost', '← Menu');
  back.onclick = () => nav(renderMenu);
  top.appendChild(back);
  screen.appendChild(top);

  const grid = el('div', 'car-grid');

  const draw = () => {
    grid.innerHTML = '';
    for (const car of CARS) {
      const unlocked = SaveManager.data.unlockedCars.includes(car.id);
      const selected = SaveManager.data.selectedCar === car.id;
      const card = el('div', `car-card${selected ? ' selected' : ''}${unlocked ? '' : ' locked'}`);
      card.innerHTML = `
        <div class="car-name" style="color:${car.colorPrimary}">${car.name}</div>
        <div class="car-tag">${unlocked ? car.tagline : `🔒 ${describeUnlock(car.unlock)}`}</div>
        ${statBar('Vitesse', car.stars.speed, car.colorPrimary)}
        ${statBar('Accél.', car.stars.accel, car.colorPrimary)}
        ${statBar('Stabilité', car.stars.stability, car.colorPrimary)}
        ${statBar('Rotation', car.stars.rotation, car.colorPrimary)}
        ${statBar('Adhérence', car.stars.grip, car.colorPrimary)}
        ${statBar('Air', car.stars.air, car.colorPrimary)}
      `;
      if (unlocked) {
        card.onclick = () => {
          SaveManager.selectCar(car.id);
          draw();
        };
      }
      grid.appendChild(card);
    }
  };
  draw();

  screen.appendChild(grid);
  root.appendChild(screen);
};
