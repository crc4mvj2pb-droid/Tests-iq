import { DESIGN_LABELS, type Experiment } from '../engine/types';
import { getModel } from '../models';
import type { Model } from '../models/types';
import { h } from '../ui/dom';

export function pageHeader(title: string, subtitle?: string, ...actions: (HTMLElement | null)[]): HTMLElement {
  return h('div', { class: 'page-header' },
    h('div', null, h('h1', null, title), subtitle ? h('p', { class: 'muted' }, subtitle) : null),
    h('div', { class: 'actions' }, actions));
}

export function card(title: string | null, ...children: (Node | string | null | undefined | false)[]): HTMLElement {
  return h('section', { class: 'card' }, title ? h('h2', null, title) : null, ...children);
}

export function kpi(label: string, value: string, sub?: string, tone?: 'good' | 'warn'): HTMLElement {
  return h('div', { class: `kpi ${tone ?? ''}` }, h('span', { class: 'kpi-label' }, label), h('strong', null, value), sub ? h('small', null, sub) : null);
}

export function table(headers: string[], rows: (string | number | Node)[][], opts: { numeric?: number[]; className?: string } = {}): HTMLElement {
  const num = new Set(opts.numeric ?? []);
  return h('div', { class: 'table-wrap' },
    h('table', { class: opts.className ?? '' },
      h('thead', null, h('tr', null, headers.map((x, i) => h('th', { class: num.has(i) ? 'num' : '' }, x)))),
      h('tbody', null, rows.map((r) => h('tr', null, r.map((c, i) => h('td', { class: num.has(i) ? 'num' : '' }, c)))))));
}

export function metricSelect(model: Model, value: string, onChange: (v: string) => void, label = 'Indicateur analysé'): HTMLElement {
  const sel = h('select', { onchange: (e: Event) => onChange((e.target as HTMLSelectElement).value) },
    model.metrics.map((m) => h('option', { value: m.key, selected: m.key === value }, `${m.label} (${m.unit})`)));
  return h('label', { class: 'inline-field' }, h('span', null, label), sel);
}

export function paramLabel(model: Model, key: string, withUnit = true): string {
  const p = model.params.find((x) => x.key === key);
  if (!p) return key;
  return withUnit && p.unit !== '—' ? `${p.label} (${p.unit})` : p.label;
}

export function metricLabel(model: Model, key: string, withUnit = true): string {
  const m = model.metrics.find((x) => x.key === key);
  if (!m) return key;
  return withUnit && m.unit !== '—' ? `${m.label} (${m.unit})` : m.label;
}

export function statusBadge(e: Experiment): HTMLElement {
  const map = { draft: ['Brouillon', 'neutral'], running: ['En cours', 'info'], done: ['Terminée', 'good'], error: ['Erreur', 'bad'] } as const;
  const [label, tone] = map[e.status];
  return h('span', { class: `badge ${tone}` }, label);
}

export function experimentRow(e: Experiment): HTMLElement {
  const model = getModel(e.spec.modelId);
  return h('a', { class: 'exp-row', href: `#/exp/${e.spec.id}` },
    h('span', { class: 'exp-icon', 'aria-hidden': 'true' }, model.icon),
    h('span', { class: 'exp-main' }, h('strong', null, e.spec.name), h('small', null, `${model.discipline} · ${DESIGN_LABELS[e.spec.design.kind].name}`)),
    h('span', { class: 'exp-meta' }, statusBadge(e), h('small', null, e.result ? `${e.result.runs.length.toLocaleString('fr-FR')} simulations` : '')));
}

export function empty(message: string, action?: HTMLElement): HTMLElement {
  return h('div', { class: 'empty' }, h('p', null, message), action ?? null);
}
