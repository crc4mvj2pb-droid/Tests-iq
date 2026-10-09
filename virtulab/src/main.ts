import './styles.css';
import { store } from './engine/store';
import { h } from './ui/dom';
import { dashboardView } from './views/dashboard';
import { designerView } from './views/designer';
import { experimentView } from './views/experiment';
import { experimentsView } from './views/experiments';
import { modelDetailView, modelsView } from './views/models';
import { validationView } from './views/validation';

interface Route {
  pattern: RegExp;
  nav: string;
  render: (m: RegExpMatchArray, query: URLSearchParams) => HTMLElement;
}

const ROUTES: Route[] = [
  { pattern: /^\/?$/, nav: 'dashboard', render: () => dashboardView() },
  { pattern: /^\/models$/, nav: 'models', render: (_m, q) => modelsView(q.get('discipline') ?? '') },
  { pattern: /^\/models\/([\w-]+)$/, nav: 'models', render: (m) => modelDetailView(m[1]) },
  { pattern: /^\/new$/, nav: 'new', render: (_m, q) => designerView({ modelId: q.get('model') ?? undefined, from: q.get('from') ?? undefined }) },
  { pattern: /^\/experiments$/, nav: 'experiments', render: () => experimentsView() },
  { pattern: /^\/exp\/([\w-]+)$/, nav: 'experiments', render: (m) => experimentView(m[1]) },
  { pattern: /^\/validation$/, nav: 'validation', render: () => validationView() },
];

const NAV = [
  { id: 'dashboard', href: '#/', icon: '◧', label: 'Tableau de bord' },
  { id: 'new', href: '#/new', icon: '＋', label: 'Nouvelle expérience' },
  { id: 'experiments', href: '#/experiments', icon: '☰', label: 'Cahier de laboratoire' },
  { id: 'models', href: '#/models', icon: '◈', label: 'Bibliothèque de modèles' },
  { id: 'validation', href: '#/validation', icon: '✓', label: 'Vérification des modèles' },
];

const main = h('main', { id: 'main', tabindex: '-1' });
const navEl = h('nav', { class: 'nav', 'aria-label': 'Navigation principale' });
let cleanup: (() => void) | undefined;

function render(): void {
  const raw = location.hash.replace(/^#/, '') || '/';
  const [path, qs] = raw.split('?');
  const query = new URLSearchParams(qs ?? '');
  const route = ROUTES.find((r) => r.pattern.test(path)) ?? ROUTES[0];
  const match = path.match(route.pattern) ?? ([] as unknown as RegExpMatchArray);
  cleanup?.();
  cleanup = undefined;
  const view = route.render(match, query) as HTMLElement & { cleanup?: () => void };
  cleanup = view.cleanup;
  main.replaceChildren(view);
  navEl.replaceChildren(...NAV.map((n) => h('a', { href: n.href, class: n.id === route.nav ? 'active' : '', 'aria-current': n.id === route.nav ? 'page' : undefined },
    h('span', { class: 'nav-icon', 'aria-hidden': 'true' }, n.icon), h('span', null, n.label))));
  document.body.classList.remove('menu-open');
  window.scrollTo(0, 0);
}

async function boot(): Promise<void> {
  const shell = h('div', { class: 'shell' },
    h('aside', { class: 'sidebar' },
      h('a', { class: 'brand', href: '#/' },
        h('span', { class: 'brand-mark', 'aria-hidden': 'true' }, 'VL'),
        h('span', null, h('strong', null, 'VirtuLab'), h('small', null, 'Recherche scientifique virtuelle'))),
      navEl,
      h('div', { class: 'sidebar-foot' }, 'Simulations déterministes et reproductibles — calcul local dans votre navigateur.')),
    h('div', { class: 'content' },
      h('header', { class: 'topbar' },
        h('button', { class: 'menu-btn', 'aria-label': 'Menu', onclick: () => document.body.classList.toggle('menu-open') }, '☰'),
        h('span', { class: 'topbar-title' }, 'VirtuLab')),
      main));
  document.getElementById('app')!.replaceChildren(shell);
  await store.load();
  window.addEventListener('hashchange', render);
  render();
}

void boot();
