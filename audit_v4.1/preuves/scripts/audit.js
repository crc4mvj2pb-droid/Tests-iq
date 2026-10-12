const { chromium } = require('playwright');
const fs = require('fs');
const OUT = process.argv[2]; const U = 'http://127.0.0.1:8765/';
const log = []; const rec = (step, status, detail) => { log.push({ step, status, detail }); console.log(`[${status}] ${step} :: ${detail}`); };
(async () => {
  const browser = await chromium.launch();
  const ctx = await browser.newContext({ acceptDownloads: true, viewport: { width: 1400, height: 1000 } });
  const page = await ctx.newPage();
  const consoleErrors = [];
  page.on('console', m => { if (m.type() === 'error') consoleErrors.push(m.text()); });
  page.on('pageerror', e => consoleErrors.push('PAGEERROR: ' + e.message));
  page.on('dialog', d => d.accept());
  await page.goto(U); await page.waitForTimeout(1200);
  rec('load', 'INFO', `title="${await page.title()}"`);
  rec('api status badge', 'INFO', await page.locator('#apiConnectionStatus').innerText().catch(() => 'n/a'));
  // Duplicate function check: which versions are live?
  const live = await page.evaluate(() => ({ download: download.toString().slice(0, 30), renderCatalog: renderCatalog.toString().slice(0, 60), visualFor: visualFor.toString().slice(0, 40) }));
  rec('live global functions', 'INFO', JSON.stringify(live));
  const catalogText = (await page.locator('#catalog').innerText().catch(() => '')).slice(0, 150).replace(/\n/g, ' | ');
  rec('model catalog panel #catalog', catalogText ? 'INFO' : 'FAIL', catalogText || '(empty)');
  // Workbench: electrical tab
  await page.click('#wbTabs [data-cat="electrical"]');
  for (const id of ['dc-source', 'resistor', 'ground']) await page.click(`#wbCatalog [data-add="${id}"]`);
  const exportState = async () => { const d = await Promise.all([page.waitForEvent('download', { timeout: 3000 }), page.click('#wbExport')]).then(r => r[0]); return JSON.parse(fs.readFileSync(await d.path(), 'utf8')); };
  let st = await exportState();
  const benchItems = st.items.map(x => ({ id: x.id, qty: x.qty, unit: x.unit, iid: x.instanceId }));
  rec('add 3 components', benchItems.length === 3 ? 'PASS' : 'FAIL', JSON.stringify(benchItems.map(b => `${b.id}=${b.qty}${b.unit || ''}`)));
  const iid = Object.fromEntries(benchItems.map(b => [b.id, b.iid]));
  // edit values via inspector
  await page.click(`[data-instance="${iid['resistor']}"] strong`);
  await page.fill('#wbPropQty', '1000');
  await page.click(`[data-instance="${iid['dc-source']}"] strong`);
  await page.fill('#wbPropQty', '9');
  st = await exportState(); const q = st.items.map(x => `${x.id}=${x.qty}`);
  rec('edit values in Properties', q.includes('resistor=1000') && q.includes('dc-source=9') ? 'PASS' : 'FAIL', q.join(','));
  // wire by clicking terminals
  const pin = (k, p) => page.click(`[data-terminal-instance="${iid[k]}"][data-terminal-pin="${p}"]`);
  await pin('dc-source', 'P'); await pin('resistor', 'A');
  await pin('resistor', 'B'); await pin('ground', 'GND');
  await pin('dc-source', 'N'); await pin('ground', 'GND');
  st = await exportState(); const edges = st.connections.map(e => `${e.pinA}-${e.pinB}`);
  rec('wire 3 connections by clicking terminals', edges.length === 3 ? 'PASS' : 'FAIL', edges.join(','));
  await page.screenshot({ path: OUT + '/01_wired.png', fullPage: false });
  // solve
  await page.click('#wbSolveCircuit'); await page.waitForTimeout(800);
  const res = await page.locator('#wbResult').innerText();
  const ok = /9\.0000 mA|0\.0090000 A|9\.0000e-3 A/.test(res) || res.includes('0.0090000');
  rec('solve circuit from UI', ok ? 'PASS' : 'FAIL', res.split('\n').slice(0, 6).join(' | '));
  await page.locator('#wbResult').screenshot({ path: OUT + '/02_result.png' });
  // history
  await page.waitForTimeout(600);
  let hist = await (await page.request.get(U + 'api/history')).json();
  rec('dossier saved in SQLite', hist.experiments.length === 1 ? 'PASS' : 'FAIL', `${hist.experiments.length} record(s)`);
  const verifyBtn = page.locator('[data-history-verify]').first();
  if (await verifyBtn.count()) {
    await verifyBtn.click(); await page.waitForTimeout(500);
    rec('verify integrity button', 'INFO', await page.locator('[data-history-message]').first().innerText());
    await page.locator('[data-history-replay]').first().click(); await page.waitForTimeout(800);
    rec('replay button', 'INFO', await page.locator('[data-history-message]').first().innerText().catch(() => '?'));
    hist = await (await page.request.get(U + 'api/history')).json();
    rec('replay created new dossier', hist.experiments.length === 2 ? 'PASS' : 'FAIL', `${hist.experiments.length} record(s)`);
  } else rec('history buttons visible', 'FAIL', 'no [data-history-verify] button rendered');
  // double click solve
  const before = hist.experiments.length;
  await page.dblclick('#wbSolveCircuit'); await page.waitForTimeout(1200);
  hist = await (await page.request.get(U + 'api/history')).json();
  rec('double-click on Solve', hist.experiments.length - before === 1 ? 'PASS' : 'WARN', `created ${hist.experiments.length - before} dossier(s) for one double-click`);
  // export workbench (block-2 download)
  let dl = await Promise.all([page.waitForEvent('download', { timeout: 3000 }), page.click('#wbExport')]).then(r => r[0]).catch(() => null);
  if (dl) { const p = await dl.path(); const j = JSON.parse(fs.readFileSync(p, 'utf8')); rec('export workbench JSON', j.items?.length === 3 && j.connections?.length === 3 ? 'PASS' : 'FAIL', `file=${dl.suggestedFilename()} items=${j.items?.length} wires=${j.connections?.length}`); }
  else rec('export workbench JSON', 'FAIL', 'no download');
  // save + reload + restore
  await page.click('#wbSave'); await page.waitForTimeout(300);
  await page.reload(); await page.waitForTimeout(1200);
  st = await exportState(); const after = { n: st.items.length, w: st.connections.length, q: st.items.map(x => `${x.id}=${x.qty}`) };
  rec('save → reload → auto-restore', after.n === 3 && after.w === 3 ? 'PASS' : 'FAIL', JSON.stringify(after));
  await page.click('#wbSolveCircuit'); await page.waitForTimeout(800);
  rec('solve after reload', /0\.0090000|9\.0000/.test(await page.locator('#wbResult').innerText()) ? 'PASS' : 'FAIL', (await page.locator('#wbResult').innerText()).split('\n')[0]);
  // delete resistor -> wires removed
  await page.click(`[data-remove="${iid['resistor']}"]`);
  st = await exportState(); const del = { n: st.items.length, w: st.connections.length, orphan: st.connections.filter(e => !st.items.some(b => b.instanceId === e.a) || !st.items.some(b => b.instanceId === e.b)).length };
  rec('delete component removes its wires', del.orphan === 0 ? 'PASS' : 'FAIL', JSON.stringify(del));
  // network failure
  await page.reload(); await page.waitForTimeout(1000);
  await page.route('**/api/electrical/workbench-run', r => r.abort());
  await page.click('#wbSolveCircuit'); await page.waitForTimeout(600);
  rec('network failure on solve', 'INFO', (await page.locator('#wbResult').innerText()).split('\n').slice(0, 2).join(' | '));
  await page.unroute('**/api/electrical/workbench-run');
  // server 500 non-JSON simulation
  await page.route('**/api/electrical/workbench-run', r => r.fulfill({ status: 502, body: '<html>Bad gateway</html>', contentType: 'text/html' }));
  await page.click('#wbSolveCircuit'); await page.waitForTimeout(600);
  rec('non-JSON error response', 'INFO', (await page.locator('#wbResult').innerText()).split('\n').slice(0, 2).join(' | '));
  await page.unroute('**/api/electrical/workbench-run');
  // Negative resistance typed in UI
  // Old-block export (download(filename,data) callers) : run a model experiment and export
  if (await page.locator('#run').count()) {
    await page.click('#run'); await page.waitForTimeout(1200);
    const exp = page.locator('#exportOne');
    if (await exp.count()) {
      dl = await Promise.all([page.waitForEvent('download', { timeout: 3000 }), exp.click()]).then(r => r[0]).catch(e => null);
      if (dl) { const body = fs.readFileSync(await dl.path(), 'utf8'); rec('export experiment dossier (#exportOne)', body.trim().startsWith('{') ? 'PASS' : 'FAIL', `suggested filename starts: "${dl.suggestedFilename().slice(0, 50)}" ; content: ${body.slice(0, 60)}`); }
      else rec('export experiment dossier (#exportOne)', 'FAIL', 'no download event');
    } else rec('run model experiment', 'FAIL', (await page.locator('#result').innerText()).slice(0, 200));
  }
  // lab run via UI? report console
  rec('console errors', consoleErrors.length ? 'WARN' : 'PASS', consoleErrors.length + ' : ' + consoleErrors.slice(0, 6).join(' || '));
  fs.writeFileSync(OUT + '/browser_audit_log.json', JSON.stringify(log, null, 2));
  await browser.close();
})().catch(e => { console.error('SCRIPT ERROR', e); process.exit(1); });
