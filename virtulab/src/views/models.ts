import { MODELS, getModel } from '../models';
import { euros, h, hours } from '../ui/dom';
import { card, pageHeader, table } from './common';
import { runValidation } from './validation';

export function modelsView(discipline: string): HTMLElement {
  const disciplines = [...new Set(MODELS.map((m) => m.discipline))];
  const list = discipline ? MODELS.filter((m) => m.discipline === discipline) : MODELS;
  return h('div', { class: 'page' },
    pageHeader('Bibliothèque de modèles', `${MODELS.length} modèles validés couvrant ${disciplines.length} disciplines.`),
    h('div', { class: 'chips', role: 'group', 'aria-label': 'Filtrer par discipline' },
      h('a', { class: `chip ${discipline ? '' : 'active'}`, href: '#/models' }, 'Toutes'),
      disciplines.map((d) => h('a', { class: `chip ${d === discipline ? 'active' : ''}`, href: `#/models?discipline=${encodeURIComponent(d)}` }, d))),
    h('div', { class: 'model-grid' }, list.map((m) =>
      h('a', { class: 'model-card', href: `#/models/${m.id}` },
        h('div', { class: 'model-card-head' }, h('span', { class: 'model-icon', 'aria-hidden': 'true' }, m.icon), h('span', { class: 'badge neutral' }, m.discipline)),
        h('h3', null, m.name),
        h('p', { class: 'muted' }, m.summary),
        h('div', { class: 'model-card-foot' },
          h('small', null, `${m.params.length} paramètres · ${m.metrics.length} indicateurs`),
          h('small', null, `${m.validation.length} validations`))))));
}

export function modelDetailView(id: string): HTMLElement {
  const m = getModel(id);
  const valBox = h('div');
  return h('div', { class: 'page' },
    pageHeader(`${m.icon} ${m.name}`, `${m.discipline} — ${m.summary}`,
      h('a', { class: 'btn primary', href: `#/new?model=${m.id}` }, 'Concevoir une expérience')),
    h('div', { class: 'grid-2' },
      card('Description',
        h('p', null, m.description),
        h('h3', null, 'Équations'),
        h('div', { class: 'equations' }, m.equations.map((e) => h('code', null, e))),
        h('h3', null, 'Hypothèses de modélisation'),
        h('ul', null, m.assumptions.map((a) => h('li', null, a))),
        h('h3', null, 'Références'),
        h('ul', { class: 'muted' }, m.references.map((a) => h('li', null, a)))),
      h('div', { class: 'stack' },
        card('Équivalent expérimental physique',
          h('div', { class: 'kpis compact' },
            h('div', { class: 'kpi' }, h('span', { class: 'kpi-label' }, 'Coût par essai'), h('strong', null, euros(m.physical.costPerRun))),
            h('div', { class: 'kpi' }, h('span', { class: 'kpi-label' }, 'Durée par essai'), h('strong', null, hours(m.physical.hoursPerRun)))),
          h('p', { class: 'muted' }, m.physical.note)),
        card('Vérification numérique',
          h('p', { class: 'muted' }, 'Le modèle est comparé à des solutions de référence exactes.'),
          h('button', { class: 'btn', onclick: () => valBox.replaceChildren(runValidation([m])) }, 'Exécuter les tests de validation'),
          valBox))),
    card('Paramètres d\'entrée',
      table(['Paramètre', 'Type', 'Unité', 'Défaut', 'Plage'],
        m.params.map((p) => [
          h('span', null, p.label, p.help ? h('small', { class: 'muted block' }, p.help) : null),
          p.kind === 'control' ? 'Pilotable' : 'Propriété',
          p.unit, String(p.default), `${p.min} – ${p.max}`,
        ]), { numeric: [3] })),
    card('Indicateurs mesurés',
      table(['Indicateur', 'Unité', 'Bruit de mesure simulé'],
        m.metrics.map((x) => [x.label, x.unit, x.noise ? `± ${(x.noise * 100).toLocaleString('fr-FR')} % (1σ)` : 'aucun (grandeur calculée)']))));
}
