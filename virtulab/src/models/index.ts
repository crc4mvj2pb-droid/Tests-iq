import { bioreactor } from './bioreactor';
import { ecology } from './ecology';
import { pharmacokinetics } from './pharmacokinetics';
import { projectile } from './projectile';
import { reactor } from './reactor';
import { seir } from './seir';
import type { Model } from './types';
import { wall } from './wall';

export const MODELS: Model[] = [projectile, reactor, seir, pharmacokinetics, wall, ecology, bioreactor];

export function getModel(id: string): Model {
  const m = MODELS.find((x) => x.id === id);
  if (!m) throw new Error(`Modèle inconnu : ${id}`);
  return m;
}
