import { MODELS } from '../models';
import type { Model } from '../models/types';
import { h } from '../ui/dom';
import { card, pageHeader, table } from './common';

export function runValidation(models: Model[]): HTMLElement {
  let pass = 0, total = 0;
  const rows = models.flatMap((m) => m.validation.map((v) => {
    total++;
    const t0 = performance.now();
    const { expected, obtained } = v.run();
    const ms = performance.now() - t0;
    const err = Math.abs(obtained - expected) / Math.max(Math.abs(expected), 1e-300);
    const ok = err <= v.tolerance;
    if (ok) pass++;
    return [
      h('span', null, h('strong', null, v.name), h('small', { class: 'muted block' }, `${m.icon} ${m.name}`)),
      h('small', null, v.reference),
      expected.toPrecision(8), obtained.toPrecision(8),
      err.toExponential(2), v.tolerance.toExponential(0),
      h('span', { class: `badge ${ok ? 'good' : 'bad'}` }, ok ? 'Conforme' : 'Non conforme'),
      `${ms.toFixed(0)} ms`,
    ];
  }));
  return h('div', null,
    h('p', { class: `verdict ${pass === total ? 'supported' : 'rejected'}` }, `${pass} / ${total} cas de validation conformes`),
    table(['Cas', 'Référence', 'Attendu', 'Obtenu', 'Erreur relative', 'Tolérance', 'Statut', 'Calcul'], rows, { numeric: [2, 3, 4, 5, 7] }));
}

export function validationView(): HTMLElement {
  const box = h('div', null, h('p', { class: 'muted' }, 'Calcul en cours…'));
  setTimeout(() => box.replaceChildren(runValidation(MODELS)), 30);
  return h('div', { class: 'page' },
    pageHeader('Vérification des modèles', 'Chaque modèle est confronté à des solutions analytiques ou à des lois établies. Une plateforme virtuelle ne vaut que par la fiabilité de ses solveurs.',
      h('button', { class: 'btn', onclick: () => { box.replaceChildren(h('p', { class: 'muted' }, 'Calcul en cours…')); setTimeout(() => box.replaceChildren(runValidation(MODELS)), 30); } }, 'Relancer')),
    card('Résultats de vérification', box),
    card('Méthodes numériques',
      h('ul', null,
        h('li', null, h('strong', null, 'Runge-Kutta 4 '), '(pas fixe, erreur globale O(h⁴)) — balistique, épidémiologie.'),
        h('li', null, h('strong', null, 'Dormand-Prince 5(4) '), '(pas adaptatif, contrôle d\'erreur relative/absolue) — réacteur raide, écologie, bioréacteur.'),
        h('li', null, h('strong', null, 'Différences finies implicites '), '(Euler implicite + algorithme de Thomas, inconditionnellement stable) — conduction thermique.'),
        h('li', null, h('strong', null, 'Solutions exactes superposées '), '(fonctions de Bateman) — pharmacocinétique.'),
        h('li', null, h('strong', null, 'Générateur pseudo-aléatoire à graine '), '(mulberry32) — chaque expérience est intégralement reproductible.'))));
}
