import { launch, navigate } from '../app';
import { impact } from '../engine/analysis';
import { store } from '../engine/store';
import { DESIGN_LABELS, type ExperimentSpec } from '../engine/types';
import { MODELS, getModel } from '../models';
import { dateTime, euros, h, toast } from '../ui/dom';
import { empty, pageHeader, statusBadge, table } from './common';

export function experimentsView(): HTMLElement {
  const root = h('div', { class: 'page' });
  let filter = '';
  const fileInput = h('input', {
    type: 'file', accept: '.json,application/json', hidden: true,
    onchange: async (e: Event) => {
      const file = (e.target as HTMLInputElement).files?.[0];
      if (!file) return;
      try {
        const data = JSON.parse(await file.text()) as { spec?: ExperimentSpec };
        const spec = data.spec;
        if (!spec || !MODELS.some((m) => m.id === spec.modelId) || !spec.design) throw new Error('Fichier non reconnu');
        // Ré-exécution à l'identique grâce à la graine : les résultats sont recalculés, pas copiés.
        const id = await launch({ ...spec, id: undefined, createdAt: undefined, name: `${spec.name} (importée)` });
        toast('Expérience importée et ré-exécutée à l\'identique');
        navigate(`#/exp/${id}`);
      } catch (err) {
        toast(`Import impossible : ${(err as Error).message}`, 'error');
      }
    },
  });

  const draw = () => {
    const all = store.list();
    const list = all.filter((e) => !filter || e.spec.name.toLowerCase().includes(filter) || getModel(e.spec.modelId).discipline.toLowerCase().includes(filter));
    const body = list.length
      ? table(['Expérience', 'Discipline', 'Plan', 'Simulations', 'Coût évité', 'Date', 'Statut'],
        list.map((e) => {
          const m = getModel(e.spec.modelId);
          return [
            h('a', { href: `#/exp/${e.spec.id}` }, h('strong', null, e.spec.name)),
            `${m.icon} ${m.discipline}`,
            DESIGN_LABELS[e.spec.design.kind].name,
            e.result ? e.result.runs.length.toLocaleString('fr-FR') : '—',
            e.result ? euros(impact(m, e.spec, e.result).costAvoided) : '—',
            dateTime(e.spec.createdAt),
            statusBadge(e),
          ];
        }), { numeric: [3, 4] })
      : empty(all.length ? 'Aucune expérience ne correspond à la recherche.' : 'Le cahier de laboratoire est vide.', h('a', { class: 'btn primary', href: '#/new' }, 'Concevoir une expérience'));
    listBox.replaceChildren(body);
  };

  const listBox = h('div', { class: 'card' });
  root.append(
    pageHeader('Cahier de laboratoire', 'Toutes vos expériences, leurs paramètres exacts et leurs résultats — stockés localement dans ce navigateur.',
      h('button', { class: 'btn', onclick: () => fileInput.click() }, 'Importer (JSON)'),
      h('a', { class: 'btn primary', href: '#/new' }, 'Nouvelle expérience')),
    fileInput,
    h('input', { type: 'search', class: 'search', placeholder: 'Rechercher par nom ou discipline…', 'aria-label': 'Rechercher', oninput: (e: Event) => { filter = (e.target as HTMLInputElement).value.toLowerCase(); draw(); } }),
    listBox);
  draw();
  const unsub = store.subscribe(draw);
  return Object.assign(root, { cleanup: unsub });
}
