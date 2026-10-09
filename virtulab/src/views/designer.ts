import { launch, navigate } from '../app';
import { variedFactors } from '../engine/analysis';
import { buildPlan } from '../engine/plan';
import { store } from '../engine/store';
import { DESIGN_LABELS, type Design, type DesignKind, type ExperimentSpec } from '../engine/types';
import { MODELS, getModel } from '../models';
import { defaults, type Model, type ParamDef } from '../models/types';
import { euros, h, hours } from '../ui/dom';
import { card, pageHeader } from './common';

type Draft = Omit<ExperimentSpec, 'id' | 'createdAt'>;

const benchCache = new Map<string, number>();
function msPerRun(model: Model, draft: Draft): number {
  if (!benchCache.has(model.id)) {
    const t0 = performance.now();
    model.simulate(draft.base);
    benchCache.set(model.id, Math.max(0.2, performance.now() - t0));
  }
  return benchCache.get(model.id)!;
}

function defaultDesign(model: Model, kind: DesignKind): Design {
  const controls = model.params.filter((p) => p.kind === 'control');
  const range = (p: ParamDef, levels: number) => ({ key: p.key, from: p.min, to: p.max, levels, scale: (p.log ? 'log' : 'lin') as 'lin' | 'log' });
  switch (kind) {
    case 'single': return { kind };
    case 'sweep': return { kind, factor: range(controls[0] ?? model.params[0], 11) };
    case 'factorial': return { kind, factors: [range(controls[0] ?? model.params[0], 6), range(controls[1] ?? model.params[1], 6)] };
    case 'montecarlo': return { kind, samples: 500, uncertain: model.params.filter((p) => p.kind === 'property').slice(0, 5).map((p) => ({ key: p.key, relSd: 0.1 })) };
    case 'lhs': return { kind, samples: 200, factors: controls.slice(0, 4).map((p) => ({ key: p.key, from: p.min, to: p.max })) };
  }
}

function freshDraft(model: Model): Draft {
  const objective = model.metrics[0].key;
  return {
    name: `Étude — ${model.name}`,
    hypothesis: '',
    criterion: undefined,
    objective: { metric: objective, goal: 'max' },
    modelId: model.id,
    base: defaults(model),
    design: defaultDesign(model, 'sweep'),
    replicates: 3,
    measurementNoise: true,
    seed: Math.floor(Math.random() * 1e9),
  };
}

function num(value: number, onInput: (v: number) => void, attrs: Record<string, unknown> = {}): HTMLInputElement {
  return h('input', {
    type: 'number', value: String(value), step: 'any', ...attrs,
    oninput: (e: Event) => { const v = parseFloat((e.target as HTMLInputElement).value); if (Number.isFinite(v)) onInput(v); },
  });
}

function field(label: string, control: HTMLElement, hint?: string): HTMLElement {
  return h('label', { class: 'field' }, h('span', null, label), control, hint ? h('small', { class: 'muted' }, hint) : null);
}

export function designerView(opts: { modelId?: string; from?: string }): HTMLElement {
  let draft: Draft;
  const source = opts.from ? store.get(opts.from) : undefined;
  if (source) {
    const { id: _id, createdAt: _c, ...rest } = structuredClone(source.spec);
    draft = { ...rest, name: `${rest.name} (variante)` };
  } else {
    draft = freshDraft(getModel(opts.modelId && MODELS.some((m) => m.id === opts.modelId) ? opts.modelId : MODELS[0].id));
  }

  const root = h('div', { class: 'page' });
  const summary = h('aside', { class: 'card summary' });
  const formBox = h('div', { class: 'stack' });

  const refreshSummary = () => {
    const model = getModel(draft.modelId);
    const problems: string[] = [];
    let points = 0;
    try { points = buildPlan(model, { ...draft, id: 'x', createdAt: 0 }).length; } catch { problems.push('Plan invalide'); }
    const d = draft.design;
    if (d.kind === 'sweep' && d.factor.from === d.factor.to) problems.push('La plage du facteur balayé est nulle.');
    if (d.kind === 'factorial' && d.factors[0].key === d.factors[1].key) problems.push('Les deux facteurs doivent être différents.');
    if ((d.kind === 'montecarlo' && !d.uncertain.length) || (d.kind === 'lhs' && !d.factors.length)) problems.push('Sélectionnez au moins un paramètre.');
    if (!draft.name.trim()) problems.push('Donnez un nom à l\'expérience.');
    const runs = points * Math.max(1, draft.replicates);
    if (runs > 20000) problems.push('Plus de 20 000 simulations : réduisez la taille du plan.');
    const est = (runs * msPerRun(model, draft)) / 1000;
    const launchBtn = h('button', {
      class: 'btn primary block', disabled: problems.length > 0,
      onclick: async () => { const id = await launch(draft); navigate(`#/exp/${id}`); },
    }, 'Lancer l\'expérience');
    summary.replaceChildren(
      h('h2', null, 'Synthèse du plan'),
      h('dl', { class: 'summary-list' },
        h('dt', null, 'Modèle'), h('dd', null, `${model.icon} ${model.name}`),
        h('dt', null, 'Plan'), h('dd', null, DESIGN_LABELS[d.kind].name),
        h('dt', null, 'Points du plan'), h('dd', null, points.toLocaleString('fr-FR')),
        h('dt', null, 'Simulations'), h('dd', null, h('strong', null, runs.toLocaleString('fr-FR'))),
        h('dt', null, 'Temps de calcul estimé'), h('dd', null, est < 1 ? '< 1 s' : `≈ ${Math.ceil(est)} s`)),
      h('div', { class: 'equiv' },
        h('span', { class: 'kpi-label' }, 'Équivalent en laboratoire'),
        h('strong', null, euros(runs * model.physical.costPerRun)),
        h('small', null, `${hours(runs * model.physical.hoursPerRun)} d'essais physiques`)),
      ...(problems.length ? [h('ul', { class: 'problems' }, problems.map((p) => h('li', null, p)))] : []),
      launchBtn);
  };

  const renderForm = () => {
    const model = getModel(draft.modelId);
    const varied = new Set(variedFactors({ ...draft, id: 'x', createdAt: 0 }));
    const paramOptions = (selected: string) => model.params.map((p) => h('option', { value: p.key, selected: p.key === selected }, `${p.label} (${p.unit})`));
    const metricOptions = (selected: string) => model.metrics.map((m) => h('option', { value: m.key, selected: m.key === selected }, `${m.label} (${m.unit})`));

    // 1. Modèle
    const modelSel = h('select', {
      onchange: (e: Event) => { draft = freshDraft(getModel((e.target as HTMLSelectElement).value)); renderForm(); },
    }, [...new Set(MODELS.map((m) => m.discipline))].map((disc) =>
      h('optgroup', { label: disc }, MODELS.filter((m) => m.discipline === disc).map((m) => h('option', { value: m.id, selected: m.id === draft.modelId }, `${m.icon} ${m.name}`)))));

    // 2. Question de recherche
    const crit = draft.criterion;
    const critBox = h('div', { class: 'row' },
      crit ? [
        field('Indicateur', h('select', { onchange: (e: Event) => { crit.metric = (e.target as HTMLSelectElement).value; refreshSummary(); } }, metricOptions(crit.metric))),
        field('Condition', h('select', { onchange: (e: Event) => { crit.op = (e.target as HTMLSelectElement).value as '>' | '<'; } },
          h('option', { value: '>', selected: crit.op === '>' }, 'supérieur à'), h('option', { value: '<', selected: crit.op === '<' }, 'inférieur à'))),
        field('Seuil', num(crit.threshold, (v) => (crit.threshold = v))),
      ] : null);

    // 3. Plan d'expériences
    const d = draft.design;
    const factorEditor = (f: { key: string; from: number; to: number; levels: number; scale: 'lin' | 'log' }, title: string) => h('div', { class: 'subcard' },
      h('h4', null, title),
      h('div', { class: 'row' },
        field('Paramètre', h('select', { onchange: (e: Event) => {
          const p = model.params.find((x) => x.key === (e.target as HTMLSelectElement).value)!;
          Object.assign(f, { key: p.key, from: p.min, to: p.max, scale: p.log ? 'log' : 'lin' });
          renderForm();
        } }, paramOptions(f.key))),
        field('De', num(f.from, (v) => { f.from = v; refreshSummary(); })),
        field('À', num(f.to, (v) => { f.to = v; refreshSummary(); })),
        field('Niveaux', num(f.levels, (v) => { f.levels = Math.max(2, Math.min(200, Math.round(v))); refreshSummary(); }, { min: 2, max: 200, step: 1 })),
        field('Échelle', h('select', { onchange: (e: Event) => { f.scale = (e.target as HTMLSelectElement).value as 'lin' | 'log'; } },
          h('option', { value: 'lin', selected: f.scale === 'lin' }, 'Linéaire'), h('option', { value: 'log', selected: f.scale === 'log' }, 'Logarithmique')))));

    let designConfig: HTMLElement | null = null;
    if (d.kind === 'sweep') designConfig = factorEditor(d.factor, 'Facteur balayé');
    if (d.kind === 'factorial') designConfig = h('div', { class: 'stack' }, factorEditor(d.factors[0], 'Facteur A (axe horizontal)'), factorEditor(d.factors[1], 'Facteur B (axe vertical)'));
    if (d.kind === 'montecarlo') {
      designConfig = h('div', { class: 'stack' },
        field('Nombre de tirages', num(d.samples, (v) => { d.samples = Math.max(10, Math.min(20000, Math.round(v))); refreshSummary(); }, { min: 10, step: 10 })),
        h('p', { class: 'muted' }, 'Cochez les paramètres incertains et indiquez leur écart-type relatif (loi log-normale centrée sur la valeur nominale).'),
        h('div', { class: 'param-picks' }, model.params.map((p) => {
          const u = d.uncertain.find((x) => x.key === p.key);
          return h('div', { class: `pick ${u ? 'on' : ''}` },
            h('label', null, h('input', { type: 'checkbox', checked: !!u, onchange: (e: Event) => {
              if ((e.target as HTMLInputElement).checked) d.uncertain.push({ key: p.key, relSd: 0.1 });
              else d.uncertain = d.uncertain.filter((x) => x.key !== p.key);
              renderForm();
            } }), ` ${p.label}`),
            u ? h('span', { class: 'pick-input' }, '± ', num(u.relSd * 100, (v) => (u.relSd = Math.max(0, v) / 100), { min: 0, max: 200 }), ' %') : null);
        })));
    }
    if (d.kind === 'lhs') {
      designConfig = h('div', { class: 'stack' },
        field('Nombre d\'échantillons', num(d.samples, (v) => { d.samples = Math.max(10, Math.min(20000, Math.round(v))); refreshSummary(); }, { min: 10, step: 10 })),
        h('p', { class: 'muted' }, 'Cochez les facteurs à explorer et leur plage. L\'hypercube latin couvre l\'espace uniformément avec peu de points.'),
        h('div', { class: 'param-picks' }, model.params.map((p) => {
          const f = d.factors.find((x) => x.key === p.key);
          return h('div', { class: `pick ${f ? 'on' : ''}` },
            h('label', null, h('input', { type: 'checkbox', checked: !!f, onchange: (e: Event) => {
              if ((e.target as HTMLInputElement).checked) d.factors.push({ key: p.key, from: p.min, to: p.max });
              else d.factors = d.factors.filter((x) => x.key !== p.key);
              renderForm();
            } }), ` ${p.label} (${p.unit})`),
            f ? h('span', { class: 'pick-input' }, num(f.from, (v) => (f.from = v)), ' → ', num(f.to, (v) => (f.to = v))) : null);
        })));
    }

    // 4. Conditions nominales
    const paramsGrid = h('div', { class: 'param-grid' }, model.params.map((p) => {
      const isVaried = varied.has(p.key);
      const numInput = num(draft.base[p.key], (v) => { draft.base[p.key] = v; slider.value = String(v); refreshSummary(); }, { min: p.min, max: p.max, disabled: isVaried && d.kind !== 'montecarlo' });
      const slider: HTMLInputElement = h('input', {
        type: 'range', min: p.min, max: p.max, step: p.step ?? (p.max - p.min) / 200, value: String(draft.base[p.key]),
        disabled: isVaried && d.kind !== 'montecarlo', 'aria-label': p.label,
        oninput: (e: Event) => { const v = parseFloat((e.target as HTMLInputElement).value); draft.base[p.key] = v; numInput.value = String(+v.toPrecision(6)); },
      });
      return h('div', { class: `param ${isVaried ? 'varied' : ''}` },
        h('div', { class: 'param-head' }, h('span', null, p.label), h('small', null, p.unit)),
        h('div', { class: 'param-inputs' }, slider, numInput),
        isVaried ? h('small', { class: 'tag' }, d.kind === 'montecarlo' ? 'valeur nominale (incertaine)' : 'varié par le plan') : p.help ? h('small', { class: 'muted' }, p.help) : null);
    }));

    formBox.replaceChildren(
      card('1 · Modèle scientifique', field('Système étudié', modelSel), h('p', { class: 'muted' }, model.summary, ' ', h('a', { href: `#/models/${model.id}` }, 'Fiche du modèle →'))),
      card('2 · Question de recherche',
        field('Nom de l\'expérience', h('input', { type: 'text', value: draft.name, oninput: (e: Event) => { draft.name = (e.target as HTMLInputElement).value; refreshSummary(); } })),
        field('Hypothèse', h('textarea', { rows: 2, placeholder: 'Ex. : augmenter la température au-delà de 60 °C dégrade la sélectivité.', oninput: (e: Event) => (draft.hypothesis = (e.target as HTMLTextAreaElement).value) }, draft.hypothesis)),
        h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: !!crit, onchange: (e: Event) => {
          draft.criterion = (e.target as HTMLInputElement).checked ? { metric: draft.objective.metric, op: '>', threshold: 0 } : undefined;
          renderForm();
        } }), ' Formuler un critère de succès quantitatif (test statistique automatique)'),
        critBox,
        h('div', { class: 'row' },
          field('Objectif à optimiser', h('select', { onchange: (e: Event) => (draft.objective.metric = (e.target as HTMLSelectElement).value) }, metricOptions(draft.objective.metric))),
          field('Sens', h('select', { onchange: (e: Event) => (draft.objective.goal = (e.target as HTMLSelectElement).value as 'max' | 'min') },
            h('option', { value: 'max', selected: draft.objective.goal === 'max' }, 'Maximiser'), h('option', { value: 'min', selected: draft.objective.goal === 'min' }, 'Minimiser'))))),
      card('3 · Plan d\'expériences',
        h('div', { class: 'design-kinds', role: 'radiogroup' }, (Object.keys(DESIGN_LABELS) as DesignKind[]).map((k) =>
          h('button', { type: 'button', role: 'radio', 'aria-checked': String(d.kind === k), class: `design-kind ${d.kind === k ? 'active' : ''}`,
            onclick: () => { draft.design = defaultDesign(model, k); if (k === 'montecarlo' || k === 'lhs') draft.replicates = 1; renderForm(); } },
          h('strong', null, DESIGN_LABELS[k].name), h('small', null, DESIGN_LABELS[k].description)))),
        designConfig,
        h('div', { class: 'row' },
          field('Réplicats par point', num(draft.replicates, (v) => { draft.replicates = Math.max(1, Math.min(50, Math.round(v))); refreshSummary(); }, { min: 1, max: 50, step: 1 }), 'Utile avec le bruit de mesure'),
          field('Graine aléatoire', h('div', { class: 'inline' },
            num(draft.seed, (v) => (draft.seed = Math.round(v))),
            h('button', { type: 'button', class: 'btn small', onclick: () => { draft.seed = Math.floor(Math.random() * 1e9); renderForm(); } }, '↻')), 'Même graine = mêmes résultats')),
        h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: draft.measurementNoise, onchange: (e: Event) => (draft.measurementNoise = (e.target as HTMLInputElement).checked) }),
          ' Simuler le bruit des instruments de mesure (réalisme expérimental)')),
      card('4 · Conditions nominales', h('p', { class: 'muted' }, 'Valeurs utilisées pour tous les paramètres non variés par le plan.'), paramsGrid),
    );
    refreshSummary();
  };

  renderForm();
  root.replaceChildren(
    pageHeader(source ? 'Variante d\'expérience' : 'Nouvelle expérience', 'Définissez la question, le plan d\'expériences et les conditions — la plateforme exécute et analyse.'),
    h('div', { class: 'designer' }, formBox, summary));
  return root;
}
