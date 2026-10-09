import { launch, navigate } from '../app';
import { impact } from '../engine/analysis';
import { store } from '../engine/store';
import { TEMPLATES } from '../engine/templates';
import { MODELS, getModel } from '../models';
import { euros, h, hours } from '../ui/dom';
import { card, empty, experimentRow, kpi } from './common';

export function dashboardView(): HTMLElement {
  const root = h('div', { class: 'page' });
  const draw = () => {
    const exps = store.list();
    const done = exps.filter((e) => e.status === 'done' && e.result);
    let runs = 0, avoided = 0, cost = 0, time = 0;
    for (const e of done) {
      const imp = impact(getModel(e.spec.modelId), e.spec, e.result!);
      runs += imp.virtualRuns; avoided += imp.avoidedRuns; cost += imp.costAvoided; time += imp.hoursAvoided;
    }
    const disciplines = [...new Set(MODELS.map((m) => m.discipline))];

    root.replaceChildren(
      h('section', { class: 'hero' },
        h('div', null,
          h('p', { class: 'eyebrow' }, 'Plateforme de recherche virtuelle'),
          h('h1', null, 'Concevoir, simuler et analyser vos expériences avant de les réaliser'),
          h('p', null, 'Des modèles physiques, chimiques, biologiques et médicaux validés contre des solutions analytiques. ',
            'Planifiez des campagnes complètes — balayages, plans factoriels, Monte Carlo, hypercube latin — et ne gardez pour le laboratoire que les essais de confirmation réellement utiles.'),
          h('div', { class: 'hero-actions' },
            h('a', { class: 'btn primary', href: '#/new' }, 'Concevoir une expérience'),
            h('a', { class: 'btn', href: '#/models' }, 'Parcourir les modèles')))),
      h('div', { class: 'kpis' },
        kpi('Expériences menées', done.length.toLocaleString('fr-FR'), `${exps.length} au cahier de laboratoire`),
        kpi('Simulations exécutées', runs.toLocaleString('fr-FR'), 'essais numériques'),
        kpi('Essais physiques évités', avoided.toLocaleString('fr-FR'), 'après confirmations recommandées', 'good'),
        kpi('Coûts évités (estimation)', euros(cost), `${hours(time)} de laboratoire`, 'good')),
      card('Démarrage rapide — expériences types',
        h('p', { class: 'muted' }, 'Questions de recherche prêtes à l\'emploi. Un clic crée l\'expérience, l\'exécute et ouvre l\'analyse.'),
        h('div', { class: 'templates' }, TEMPLATES.map((t) => {
          const spec = t.build();
          const model = getModel(spec.modelId);
          return h('button', {
            class: 'template', onclick: async () => { const id = await launch(t.build()); navigate(`#/exp/${id}`); },
          },
          h('span', { class: 'template-head' }, h('span', { 'aria-hidden': 'true' }, model.icon), h('small', null, model.discipline)),
          h('strong', null, t.title),
          h('span', { class: 'muted' }, t.question));
        }))),
      h('div', { class: 'grid-2' },
        card('Expériences récentes',
          done.length || exps.length
            ? h('div', { class: 'exp-list' }, exps.slice(0, 6).map(experimentRow))
            : empty('Aucune expérience pour l\'instant. Lancez une expérience type ci-dessus.')),
        card('Disciplines couvertes',
          h('div', { class: 'disciplines' }, disciplines.map((d) => {
            const ms = MODELS.filter((m) => m.discipline === d);
            return h('a', { class: 'discipline', href: `#/models?discipline=${encodeURIComponent(d)}` },
              h('span', { 'aria-hidden': 'true' }, ms[0].icon), h('strong', null, d), h('small', null, ms.map((m) => m.name).join(' · ')));
          })))),
    );
  };
  draw();
  const unsub = store.subscribe(draw);
  return Object.assign(root, { cleanup: unsub });
}
