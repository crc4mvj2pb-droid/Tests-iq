import { NetClient } from './NetClient';

export const netClient = new NetClient();

export function getPlayerName(): string {
  return localStorage.getItem('fliprush_name') || 'Pilote';
}

export function setPlayerName(name: string) {
  localStorage.setItem('fliprush_name', name.slice(0, 20) || 'Pilote');
}
