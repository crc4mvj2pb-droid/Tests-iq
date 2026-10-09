import { getModel } from '../models';
import { defaults } from '../models/types';
import type { ExperimentSpec } from './types';

export interface Template {
  title: string;
  question: string;
  build(): Omit<ExperimentSpec, 'id' | 'createdAt'>;
}

const seed = () => Math.floor(Math.random() * 1e9);

export const TEMPLATES: Template[] = [
  {
    title: 'Température optimale d\'un réacteur',
    question: 'Quelle température de refroidissement maximise le rendement en produit B ?',
    build: () => ({
      name: 'Optimisation de la température du réacteur',
      hypothesis: 'Il existe une température de double enveloppe permettant un rendement en B supérieur à 75 %.',
      criterion: { metric: 'yieldB', op: '>', threshold: 75 },
      objective: { metric: 'yieldB', goal: 'max' },
      modelId: 'reactor',
      base: defaults(getModel('reactor')),
      design: { kind: 'sweep', factor: { key: 'tc', from: 30, to: 90, levels: 25, scale: 'lin' } },
      replicates: 3, measurementNoise: true, seed: seed(),
    }),
  },
  {
    title: 'Cartographie du risque d\'emballement',
    question: 'Quelles combinaisons concentration / refroidissement restent sûres ?',
    build: () => ({
      name: 'Domaine de sécurité thermique du réacteur',
      hypothesis: 'L\'échauffement reste inférieur à 25 K sur tout le domaine opératoire envisagé.',
      criterion: { metric: 'dTMax', op: '<', threshold: 25 },
      objective: { metric: 'bMax', goal: 'max' },
      modelId: 'reactor',
      base: { ...defaults(getModel('reactor')), tc: 55, t0: 55 },
      design: { kind: 'factorial', factors: [
        { key: 'a0', from: 0.5, to: 4, levels: 8, scale: 'lin' },
        { key: 'ua', from: 0.2, to: 4, levels: 8, scale: 'lin' },
      ] },
      replicates: 2, measurementNoise: true, seed: seed(),
    }),
  },
  {
    title: 'Vaccination ou mesures barrières ?',
    question: 'Quelle combinaison évite la saturation des hôpitaux ?',
    build: () => ({
      name: 'Stratégies de contrôle d\'une épidémie',
      hypothesis: 'Une couverture vaccinale modérée combinée à des mesures limitées évite toute saturation hospitalière.',
      criterion: { metric: 'saturationDays', op: '<', threshold: 1 },
      objective: { metric: 'deaths', goal: 'min' },
      modelId: 'seir',
      base: defaults(getModel('seir')),
      design: { kind: 'factorial', factors: [
        { key: 'vaccination', from: 0, to: 80, levels: 9, scale: 'lin' },
        { key: 'npiReduction', from: 0, to: 60, levels: 7, scale: 'lin' },
      ] },
      replicates: 1, measurementNoise: false, seed: seed(),
    }),
  },
  {
    title: 'Posologie sur une population de patients',
    question: 'Le schéma 500 mg / 12 h est-il sûr malgré la variabilité inter-individuelle ?',
    build: () => ({
      name: 'Variabilité pharmacocinétique inter-patients',
      hypothesis: 'Moins de 5 % du temps de traitement au-dessus du seuil toxique chez au moins 95 % des patients.',
      criterion: { metric: 'timeToxic', op: '<', threshold: 5 },
      objective: { metric: 'timeInWindow', goal: 'max' },
      modelId: 'pk',
      base: defaults(getModel('pk')),
      design: { kind: 'montecarlo', samples: 1000, uncertain: [
        { key: 'cl', relSd: 0.3 }, { key: 'v', relSd: 0.25 }, { key: 'ka', relSd: 0.4 },
        { key: 'weight', relSd: 0.2 }, { key: 'bioavailability', relSd: 0.1 },
      ] },
      replicates: 1, measurementNoise: true, seed: seed(),
    }),
  },
  {
    title: 'Conception d\'une paroi performante',
    question: 'Quels paramètres de matériau pilotent les déperditions et le confort ?',
    build: () => ({
      name: 'Exploration de compositions de paroi',
      hypothesis: 'Un flux de chaleur inférieur à 10 W/m² est atteignable dans le domaine des matériaux courants.',
      criterion: { metric: 'avgFlux', op: '<', threshold: 10 },
      objective: { metric: 'heatLoss', goal: 'min' },
      modelId: 'wall',
      base: { ...defaults(getModel('wall')), duration: 96 },
      design: { kind: 'lhs', samples: 300, factors: [
        { key: 'thickness', from: 10, to: 50 }, { key: 'k', from: 0.04, to: 2 },
        { key: 'density', from: 30, to: 2400 }, { key: 'cp', from: 800, to: 2000 },
      ] },
      replicates: 1, measurementNoise: false, seed: seed(),
    }),
  },
  {
    title: 'Dilution optimale d\'un chémostat',
    question: 'Quel taux de dilution maximise la productivité sans lessivage ?',
    build: () => ({
      name: 'Optimisation de la productivité en culture continue',
      hypothesis: 'La productivité dépasse 3 g/(L·h) pour un taux de dilution optimal.',
      criterion: { metric: 'productivity', op: '>', threshold: 3 },
      objective: { metric: 'productivity', goal: 'max' },
      modelId: 'bioreactor',
      base: { ...defaults(getModel('bioreactor')), duration: 300 },
      design: { kind: 'sweep', factor: { key: 'dilution', from: 0.02, to: 0.46, levels: 23, scale: 'lin' } },
      replicates: 3, measurementNoise: true, seed: seed(),
    }),
  },
  {
    title: 'Angle de tir optimal avec traînée',
    question: 'L\'angle optimal est-il encore de 45° quand l\'air freine le projectile ?',
    build: () => ({
      name: 'Angle de portée maximale',
      hypothesis: 'Avec traînée, l\'angle de portée maximale est inférieur à 45°.',
      criterion: { metric: 'range', op: '>', threshold: 45 },
      objective: { metric: 'range', goal: 'max' },
      modelId: 'projectile',
      base: defaults(getModel('projectile')),
      design: { kind: 'sweep', factor: { key: 'angle', from: 10, to: 80, levels: 29, scale: 'lin' } },
      replicates: 3, measurementNoise: true, seed: seed(),
    }),
  },
  {
    title: 'Prélèvement durable',
    question: 'Quel taux de pêche maximise la récolte sans faire disparaître les prédateurs ?',
    build: () => ({
      name: 'Rendement maximal durable',
      hypothesis: 'Au-delà d\'un certain taux de prélèvement, les prédateurs s\'effondrent : le rendement maximal se situe juste avant ce point de bascule.',
      criterion: { metric: 'coexistence', op: '>', threshold: 0.5 },
      objective: { metric: 'harvestYield', goal: 'max' },
      modelId: 'ecology',
      base: { ...defaults(getModel('ecology')), duration: 400 },
      design: { kind: 'sweep', factor: { key: 'harvest', from: 0, to: 100, levels: 41, scale: 'lin' } },
      replicates: 1, measurementNoise: false, seed: seed(),
    }),
  },
];
