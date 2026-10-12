const { chromium } = require('playwright'); const fs = require('fs'); const OUT = process.argv[2]; const U = 'http://127.0.0.1:8765/';
const rec = (s, st, d) => console.log(`[${st}] ${s} :: ${d}`);
(async () => {
  const b = await chromium.launch(); const page = await (await b.newContext({ acceptDownloads: true, viewport: { width: 1400, height: 1000 } })).newPage();
  const errs = []; page.on('pageerror', e => errs.push(e.message)); page.on('dialog', d => d.accept());
  await page.goto(U); await page.waitForTimeout(1200);
  // result metrics for the restored-or-new circuit
  await page.click('#wbTabs [data-cat="electrical"]');
  for (const id of ['dc-source', 'resistor', 'ground']) await page.click(`#wbCatalog [data-add="${id}"]`);
  const ids = await page.$$eval('#wbBench [data-instance]', els => els.map(e => e.dataset.instance));
  const pin = (i, p) => page.click(`[data-terminal-instance="${ids[i]}"][data-terminal-pin="${p}"]`);
  await pin(0, 'P'); await pin(1, 'A'); await pin(1, 'B'); await pin(2, 'GND'); await pin(0, 'N'); await pin(2, 'GND');
  await page.click('#wbSolveCircuit'); await page.waitForTimeout(800);
  rec('displayed metrics', 'INFO', (await page.$$eval('#wbResult .wb-meta', e => e.map(x => x.innerText.replace(/\n/g, ' '))) ).join(' ; '));
  // network failure: full text
  await page.route('**/api/electrical/workbench-run', r => r.abort());
  await page.click('#wbSolveCircuit'); await page.waitForTimeout(600);
  rec('network failure message', 'INFO', (await page.locator('#wbResult p').first().innerText()));
  await page.unroute('**/api/electrical/workbench-run');
  await page.route('**/api/electrical/workbench-run', r => r.fulfill({ status: 502, body: '<html>Bad gateway</html>', contentType: 'text/html' }));
  await page.click('#wbSolveCircuit'); await page.waitForTimeout(600);
  rec('non-JSON 502 message', 'INFO', (await page.locator('#wbResult p').first().innerText()));
  await page.unroute('**/api/electrical/workbench-run');
  // replay message visibility
  await page.locator('[data-history-replay]').first().click(); await page.waitForTimeout(150);
  const m1 = await page.locator('[data-history-message]').first().innerText(); await page.waitForTimeout(800);
  const m2 = await page.locator('[data-history-message]').first().innerText();
  rec('replay message at 150ms / 950ms', 'INFO', `"${m1}" / "${m2}"`);
  // negative resistance via UI
  await page.click(`[data-instance="${ids[1]}"] strong`); await page.fill('#wbPropQty', '-50');
  await page.click('#wbSolveCircuit'); await page.waitForTimeout(600);
  rec('negative resistance typed', 'INFO', (await page.locator('#wbResult p').first().innerText()));
  await page.fill('#wbPropQty', ''); await page.click('#wbSolveCircuit'); await page.waitForTimeout(600);
  rec('empty resistance field', 'INFO', (await page.locator('#wbResult p').first().innerText()));
  // ---- chemistry: stoichiometry
  const opts = await page.$$eval('#reactionSelect option', o => o.map(x => x.value));
  rec('reaction options', 'INFO', opts.length + ' : ' + opts.slice(0, 6).join(','));
  await page.click('#reactionAddReactants').catch(e => rec('add reactants', 'FAIL', e.message.slice(0, 80)));
  await page.waitForTimeout(300);
  await page.click('#reactionRun').catch(e => rec('reactionRun', 'FAIL', e.message.slice(0, 80))); await page.waitForTimeout(900);
  rec('stoichiometry result', 'INFO', (await page.locator('#reactionResult').innerText()).replace(/\n+/g, ' | ').slice(0, 400));
  // ---- kinetics
  if (await page.locator('#kinExample').count()) { await page.click('#kinExample').catch(() => {}); }
  await page.click('#kinRun'); await page.waitForTimeout(1500);
  rec('kinetics result', 'INFO', (await page.locator('#kinResult').innerText()).replace(/\n+/g, ' | ').slice(0, 400));
  const hist = await (await page.request.get(U + 'api/history')).json();
  rec('history model_ids after chemistry', 'INFO', JSON.stringify(hist.experiments.map(e => e.model_id)));
  // ---- lab run from UI
  await page.locator('#labWorkflow').scrollIntoViewIfNeeded().catch(() => {});
  await page.click('#labRun').catch(e => rec('labRun click', 'FAIL', e.message.slice(0, 80))); await page.waitForTimeout(1200);
  rec('lab run (UI)', 'INFO', (await page.locator('#labStatus').innerText()).slice(0, 300) + ' || ' + (await page.locator('#labResult').innerText()).slice(0, 200).replace(/\n/g, ' '));
  await page.screenshot({ path: OUT + '/03_lab_run.png' });
  rec('page errors', errs.length ? 'WARN' : 'PASS', errs.join(' || ') || 'none');
  await b.close();
})().catch(e => { console.error('SCRIPT ERROR', e); process.exit(1); });
