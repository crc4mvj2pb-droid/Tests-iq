import { h, s } from './dom';
import type { Bin } from '../core/stats';

export const PALETTE = ['#2563eb', '#dc2626', '#059669', '#d97706', '#7c3aed', '#0891b2', '#db2777', '#4b5563'];

const W = 640;
const H = 320;
const M = { top: 16, right: 18, bottom: 46, left: 64 };

export interface LineSeries {
  name: string;
  x: number[];
  y: number[];
  color?: string;
  dashed?: boolean;
  width?: number;
  opacity?: number;
  markers?: boolean;
  /** Barres d'erreur verticales (ex. IC95 %). */
  lo?: number[];
  hi?: number[];
  /** Exclure de la légende et de l'infobulle (courbes « spaghetti »). */
  quiet?: boolean;
}

export interface LineChartOptions {
  xLabel: string;
  yLabel: string;
  xLog?: boolean;
  vline?: { x: number; label: string };
  hline?: { y: number; label: string };
  height?: number;
}

export function niceTicks(lo: number, hi: number, count = 5): number[] {
  if (!Number.isFinite(lo) || !Number.isFinite(hi)) return [];
  if (lo === hi) { lo -= 1; hi += 1; }
  const step0 = (hi - lo) / count;
  const mag = 10 ** Math.floor(Math.log10(step0));
  const norm = step0 / mag;
  const step = (norm >= 5 ? 10 : norm >= 2 ? 5 : norm >= 1 ? 2 : 1) * mag;
  const out: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(Math.abs(v) < step * 1e-9 ? 0 : v);
  return out;
}

export function tickLabel(v: number): string {
  const a = Math.abs(v);
  if (a !== 0 && (a >= 1e5 || a < 1e-3)) return v.toExponential(1).replace('e+', 'e');
  return (+v.toPrecision(6)).toLocaleString('fr-FR', { maximumFractionDigits: 4 });
}

function extent(values: number[], pad = 0.05): [number, number] {
  let lo = Infinity, hi = -Infinity;
  for (const v of values) if (Number.isFinite(v)) { if (v < lo) lo = v; if (v > hi) hi = v; }
  if (lo === Infinity) return [0, 1];
  if (lo === hi) return [lo - Math.abs(lo || 1) * 0.1, hi + Math.abs(hi || 1) * 0.1];
  const d = (hi - lo) * pad;
  return [lo - d, hi + d];
}

function frame(height: number) {
  const svg = s('svg', { viewBox: `0 0 ${W} ${height}`, class: 'chart', role: 'img' });
  const pw = W - M.left - M.right;
  const ph = height - M.top - M.bottom;
  return { svg, pw, ph };
}

function axes(svg: SVGSVGElement, ph: number, pw: number, xt: number[], yt: number[], sx: (v: number) => number, sy: (v: number) => number, xLabel: string, yLabel: string, xFmt = tickLabel) {
  const g = s('g', { class: 'axes' });
  for (const v of yt) {
    const y = sy(v);
    g.append(s('line', { x1: M.left, x2: M.left + pw, y1: y, y2: y, class: 'grid' }));
    g.append(s('text', { x: M.left - 8, y: y + 4, 'text-anchor': 'end', class: 'tick' }, tickLabel(v)));
  }
  for (const v of xt) {
    const x = sx(v);
    g.append(s('line', { x1: x, x2: x, y1: M.top, y2: M.top + ph, class: 'grid' }));
    g.append(s('text', { x, y: M.top + ph + 16, 'text-anchor': 'middle', class: 'tick' }, xFmt(v)));
  }
  g.append(s('line', { x1: M.left, x2: M.left + pw, y1: M.top + ph, y2: M.top + ph, class: 'axis' }));
  g.append(s('line', { x1: M.left, x2: M.left, y1: M.top, y2: M.top + ph, class: 'axis' }));
  g.append(s('text', { x: M.left + pw / 2, y: M.top + ph + 38, 'text-anchor': 'middle', class: 'label' }, xLabel));
  g.append(s('text', { x: 14, y: M.top + ph / 2, 'text-anchor': 'middle', class: 'label', transform: `rotate(-90 14 ${M.top + ph / 2})` }, yLabel));
  svg.append(g);
}

function legend(series: { name: string; color: string; dashed?: boolean }[]): HTMLElement | null {
  if (series.length < 2) return null;
  return h('div', { class: 'legend' }, series.map((se) =>
    h('span', { class: 'legend-item' }, h('i', { style: `background:${se.color};${se.dashed ? 'opacity:.6' : ''}` }), se.name)));
}

export function lineChart(series: LineSeries[], opts: LineChartOptions): HTMLElement {
  const height = opts.height ?? H;
  const { svg, pw, ph } = frame(height);
  const tx = (v: number) => (opts.xLog ? Math.log10(Math.max(v, 1e-300)) : v);
  const allX = series.flatMap((se) => se.x.map(tx));
  const allY = series.flatMap((se) => [...se.y, ...(se.lo ?? []), ...(se.hi ?? [])]);
  if (opts.hline) allY.push(opts.hline.y);
  const [x0, x1] = extent(allX, 0);
  const [y0, y1] = extent(allY);
  const sx = (v: number) => M.left + ((tx(v) - x0) / (x1 - x0 || 1)) * pw;
  const sy = (v: number) => M.top + ph - ((v - y0) / (y1 - y0 || 1)) * ph;
  const xt = opts.xLog
    ? niceTicks(x0, x1, 5).map((v) => 10 ** v)
    : niceTicks(x0, x1, 6);
  axes(svg, ph, pw, xt, niceTicks(y0, y1, 5), sx, sy, opts.xLabel, opts.yLabel);

  const colored = series.map((se, i) => ({ ...se, color: se.color ?? PALETTE[i % PALETTE.length] }));
  const plot = s('g', { 'clip-path': undefined });
  for (const se of colored) {
    let d = '';
    let pen = false;
    for (let i = 0; i < se.x.length; i++) {
      if (!Number.isFinite(se.y[i]) || !Number.isFinite(tx(se.x[i]))) { pen = false; continue; }
      d += `${pen ? 'L' : 'M'}${sx(se.x[i]).toFixed(1)},${sy(se.y[i]).toFixed(1)}`;
      pen = true;
    }
    plot.append(s('path', {
      d, fill: 'none', stroke: se.color, 'stroke-width': se.width ?? 2, 'stroke-dasharray': se.dashed ? '6 4' : undefined,
      'stroke-opacity': se.opacity ?? 1, 'stroke-linejoin': 'round',
    }));
    if (se.lo && se.hi) {
      for (let i = 0; i < se.x.length; i++) {
        if (!Number.isFinite(se.lo[i]) || !Number.isFinite(se.hi[i])) continue;
        const x = sx(se.x[i]);
        plot.append(s('path', { d: `M${x - 4},${sy(se.lo[i])}H${x + 4}M${x},${sy(se.lo[i])}V${sy(se.hi[i])}M${x - 4},${sy(se.hi[i])}H${x + 4}`, stroke: se.color, 'stroke-width': 1.3, fill: 'none' }));
      }
    }
    if (se.markers) for (let i = 0; i < se.x.length; i++) {
      if (Number.isFinite(se.y[i])) plot.append(s('circle', { cx: sx(se.x[i]), cy: sy(se.y[i]), r: 3.5, fill: se.color }));
    }
  }
  if (opts.hline) {
    const y = sy(opts.hline.y);
    plot.append(s('line', { x1: M.left, x2: M.left + pw, y1: y, y2: y, class: 'refline' }));
    plot.append(s('text', { x: M.left + pw - 4, y: y - 5, 'text-anchor': 'end', class: 'reflabel' }, opts.hline.label));
  }
  if (opts.vline) {
    const x = sx(opts.vline.x);
    plot.append(s('line', { x1: x, x2: x, y1: M.top, y2: M.top + ph, class: 'refline' }));
    plot.append(s('text', { x: x + 4, y: M.top + 12, class: 'reflabel' }, opts.vline.label));
  }
  svg.append(plot);

  // Infobulle : valeurs de chaque courbe au point le plus proche.
  const wrap = h('div', { class: 'chart-wrap' });
  const tip = h('div', { class: 'chart-tip' });
  const guide = s('line', { y1: M.top, y2: M.top + ph, class: 'guide', visibility: 'hidden' });
  svg.append(guide);
  const visible = colored.filter((se) => !se.quiet);
  const overlay = s('rect', { x: M.left, y: M.top, width: pw, height: ph, fill: 'transparent' });
  overlay.addEventListener('pointermove', (ev) => {
    const rect = svg.getBoundingClientRect();
    const vx = ((ev.clientX - rect.left) / rect.width) * W;
    const xv = x0 + ((vx - M.left) / pw) * (x1 - x0);
    const rows: string[] = [];
    let xShown = NaN;
    for (const se of visible) {
      let best = -1, bd = Infinity;
      for (let i = 0; i < se.x.length; i++) {
        const dd = Math.abs(tx(se.x[i]) - xv);
        if (dd < bd) { bd = dd; best = i; }
      }
      if (best < 0) continue;
      if (Number.isNaN(xShown)) xShown = se.x[best];
      rows.push(`<span style="color:${se.color}">●</span> ${se.name} : <b>${tickLabel(se.y[best])}</b>`);
    }
    if (!rows.length) return;
    guide.setAttribute('x1', String(sx(xShown)));
    guide.setAttribute('x2', String(sx(xShown)));
    guide.setAttribute('visibility', 'visible');
    tip.innerHTML = `<div class="tip-x">${opts.xLabel} : ${tickLabel(xShown)}</div>${rows.join('<br>')}`;
    tip.style.display = 'block';
    const px = (sx(xShown) / W) * rect.width;
    tip.style.left = `${Math.min(px + 12, rect.width - tip.offsetWidth - 4)}px`;
    tip.style.top = `${8}px`;
  });
  overlay.addEventListener('pointerleave', () => { tip.style.display = 'none'; guide.setAttribute('visibility', 'hidden'); });
  svg.append(overlay);
  wrap.append(svg, tip);
  const lg = legend(visible);
  return h('div', { class: 'chart-box' }, wrap, lg);
}

export function scatterChart(
  points: { x: number; y: number; highlight?: boolean }[],
  opts: { xLabel: string; yLabel: string; trend?: { slope: number; intercept: number } },
): HTMLElement {
  const { svg, pw, ph } = frame(H);
  const [x0, x1] = extent(points.map((p) => p.x));
  const [y0, y1] = extent(points.map((p) => p.y));
  const sx = (v: number) => M.left + ((v - x0) / (x1 - x0 || 1)) * pw;
  const sy = (v: number) => M.top + ph - ((v - y0) / (y1 - y0 || 1)) * ph;
  axes(svg, ph, pw, niceTicks(x0, x1, 6), niceTicks(y0, y1, 5), sx, sy, opts.xLabel, opts.yLabel);
  const g = s('g');
  for (const p of points) {
    if (!Number.isFinite(p.x) || !Number.isFinite(p.y)) continue;
    g.append(s('circle', { cx: sx(p.x), cy: sy(p.y), r: p.highlight ? 6 : 3, class: p.highlight ? 'pt-best' : 'pt' }));
  }
  if (opts.trend) {
    const { slope, intercept } = opts.trend;
    g.append(s('line', { x1: sx(x0), y1: sy(intercept + slope * x0), x2: sx(x1), y2: sy(intercept + slope * x1), class: 'refline' }));
  }
  svg.append(g);
  return h('div', { class: 'chart-box' }, h('div', { class: 'chart-wrap' }, svg));
}

export function histogramChart(bins: Bin[], opts: { xLabel: string; markers?: { x: number; label: string; color: string }[] }): HTMLElement {
  const { svg, pw, ph } = frame(H);
  const x0 = bins[0]?.x0 ?? 0, x1 = bins[bins.length - 1]?.x1 ?? 1;
  const total = bins.reduce((a, b) => a + b.count, 0) || 1;
  const maxC = Math.max(...bins.map((b) => b.count / total), 0.01);
  const sx = (v: number) => M.left + ((v - x0) / (x1 - x0 || 1)) * pw;
  const sy = (v: number) => M.top + ph - (v / (maxC * 1.08)) * ph;
  axes(svg, ph, pw, niceTicks(x0, x1, 6), niceTicks(0, maxC * 1.08, 5), sx, sy, opts.xLabel, 'Fréquence', tickLabel);
  const g = s('g');
  for (const b of bins) {
    const y = sy(b.count / total);
    const r = s('rect', { x: sx(b.x0) + 0.5, y, width: Math.max(0, sx(b.x1) - sx(b.x0) - 1), height: M.top + ph - y, class: 'bar' });
    r.append(s('title', {}, `${tickLabel(b.x0)} – ${tickLabel(b.x1)} : ${b.count} tirages`));
    g.append(r);
  }
  for (const m of opts.markers ?? []) {
    if (m.x < x0 || m.x > x1) continue;
    const x = sx(m.x);
    g.append(s('line', { x1: x, x2: x, y1: M.top, y2: M.top + ph, stroke: m.color, 'stroke-width': 2, 'stroke-dasharray': '5 3' }));
  }
  svg.append(g);
  const lg = opts.markers?.length
    ? h('div', { class: 'legend' }, opts.markers.map((m) => h('span', { class: 'legend-item' }, h('i', { style: `background:${m.color}` }), m.label)))
    : null;
  return h('div', { class: 'chart-box' }, h('div', { class: 'chart-wrap' }, svg), lg);
}

/** Carte de chaleur pour un plan factoriel (z[i][j] : i = niveau de x, j = niveau de y). */
export function heatmap(xs: number[], ys: number[], z: number[][], opts: { xLabel: string; yLabel: string; zLabel: string; best?: [number, number] }): HTMLElement {
  const height = 360;
  const { svg, pw, ph } = frame(height);
  const flat = z.flat().filter(Number.isFinite);
  const zmin = flat.reduce((a, b) => Math.min(a, b), Infinity), zmax = flat.reduce((a, b) => Math.max(a, b), -Infinity);
  const cw = pw / xs.length, chh = ph / ys.length;
  const g = s('g');
  xs.forEach((xv, i) => ys.forEach((yv, j) => {
    const v = z[i][j];
    const u = zmax > zmin ? (v - zmin) / (zmax - zmin) : 0.5;
    const x = M.left + i * cw, y = M.top + ph - (j + 1) * chh;
    const r = s('rect', { x, y, width: cw + 0.5, height: chh + 0.5, fill: Number.isFinite(v) ? viridis(u) : '#888' });
    r.append(s('title', {}, `${opts.xLabel} = ${tickLabel(xv)}\n${opts.yLabel} = ${tickLabel(yv)}\n${opts.zLabel} = ${tickLabel(v)}`));
    g.append(r);
    if (xs.length * ys.length <= 64) {
      g.append(s('text', { x: x + cw / 2, y: y + chh / 2 + 4, 'text-anchor': 'middle', class: 'cell', fill: u > 0.55 ? '#111' : '#fff' }, tickLabel(+v.toPrecision(3))));
    }
  }));
  if (opts.best) {
    const [bi, bj] = opts.best;
    g.append(s('rect', { x: M.left + bi * cw + 1.5, y: M.top + ph - (bj + 1) * chh + 1.5, width: cw - 3, height: chh - 3, class: 'cell-best' }));
  }
  svg.append(g);
  const ax = s('g', { class: 'axes' });
  const stepX = Math.ceil(xs.length / 8), stepY = Math.ceil(ys.length / 8);
  xs.forEach((v, i) => { if (i % stepX === 0) ax.append(s('text', { x: M.left + (i + 0.5) * cw, y: M.top + ph + 16, 'text-anchor': 'middle', class: 'tick' }, tickLabel(+v.toPrecision(3)))); });
  ys.forEach((v, j) => { if (j % stepY === 0) ax.append(s('text', { x: M.left - 8, y: M.top + ph - (j + 0.5) * chh + 4, 'text-anchor': 'end', class: 'tick' }, tickLabel(+v.toPrecision(3)))); });
  ax.append(s('text', { x: M.left + pw / 2, y: M.top + ph + 38, 'text-anchor': 'middle', class: 'label' }, opts.xLabel));
  ax.append(s('text', { x: 14, y: M.top + ph / 2, 'text-anchor': 'middle', class: 'label', transform: `rotate(-90 14 ${M.top + ph / 2})` }, opts.yLabel));
  svg.append(ax);
  const scale = h('div', { class: 'colorscale' },
    h('span', null, tickLabel(zmin)),
    h('i', { style: `background:linear-gradient(90deg,${[0, 0.25, 0.5, 0.75, 1].map(viridis).join(',')})` }),
    h('span', null, tickLabel(zmax)),
    h('em', null, opts.zLabel));
  return h('div', { class: 'chart-box' }, h('div', { class: 'chart-wrap' }, svg), scale);
}

/** Diagramme « tornade » : barres horizontales signées dans [−1, 1]. */
export function tornado(rows: { label: string; value: number; secondary?: number }[], opts: { valueLabel: string; secondaryLabel?: string }): HTMLElement {
  const rowH = 30;
  const height = M.top + rows.length * rowH + 40;
  const left = 210;
  const pw = W - left - M.right;
  const svg = s('svg', { viewBox: `0 0 ${W} ${height}`, class: 'chart', role: 'img' });
  const sx = (v: number) => left + ((v + 1) / 2) * pw;
  for (const v of [-1, -0.5, 0, 0.5, 1]) {
    svg.append(s('line', { x1: sx(v), x2: sx(v), y1: M.top, y2: M.top + rows.length * rowH, class: v === 0 ? 'axis' : 'grid' }));
    svg.append(s('text', { x: sx(v), y: M.top + rows.length * rowH + 16, 'text-anchor': 'middle', class: 'tick' }, tickLabel(v)));
  }
  rows.forEach((r, i) => {
    const y = M.top + i * rowH;
    svg.append(s('text', { x: left - 10, y: y + rowH / 2 + 4, 'text-anchor': 'end', class: 'tick strong' }, r.label));
    const v = Math.max(-1, Math.min(1, r.value));
    svg.append(s('rect', { x: Math.min(sx(0), sx(v)), y: y + 5, width: Math.abs(sx(v) - sx(0)), height: r.secondary === undefined ? rowH - 10 : (rowH - 10) / 2, fill: v >= 0 ? PALETTE[0] : PALETTE[1] }));
    if (r.secondary !== undefined && Number.isFinite(r.secondary)) {
      const w = Math.max(-1, Math.min(1, r.secondary));
      svg.append(s('rect', { x: Math.min(sx(0), sx(w)), y: y + 5 + (rowH - 10) / 2, width: Math.abs(sx(w) - sx(0)), height: (rowH - 10) / 2, fill: w >= 0 ? PALETTE[0] : PALETTE[1], 'fill-opacity': 0.4 }));
    }
  });
  const lg = h('div', { class: 'legend' },
    h('span', { class: 'legend-item' }, h('i', { style: `background:${PALETTE[0]}` }), `${opts.valueLabel} (barre pleine)`),
    opts.secondaryLabel ? h('span', { class: 'legend-item' }, h('i', { style: `background:${PALETTE[0]};opacity:.4` }), `${opts.secondaryLabel} (barre claire)`) : null,
    h('span', { class: 'legend-item' }, h('i', { style: `background:${PALETTE[1]}` }), 'effet négatif'));
  return h('div', { class: 'chart-box' }, h('div', { class: 'chart-wrap' }, svg), lg);
}

/** Palette séquentielle perceptuellement uniforme (approximation de viridis). */
export function viridis(u: number): string {
  const stops = [[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]];
  const x = Math.max(0, Math.min(1, u)) * (stops.length - 1);
  const i = Math.min(stops.length - 2, Math.floor(x));
  const f = x - i;
  const c = stops[i].map((v, k) => Math.round(v + f * (stops[i + 1][k] - v)));
  return `rgb(${c[0]},${c[1]},${c[2]})`;
}
