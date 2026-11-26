const { chromium } = require('playwright'); const fs = require('fs'), path = require('path');
(async () => { const dir = process.argv[2]; const b = await chromium.launch();
  for (const f of fs.readdirSync(dir).filter(x => x.endsWith('.html'))) {
    const html = fs.readFileSync(path.join(dir, f), 'utf8'); const m = html.match(/width:(\d+)px;height:(\d+)px/);
    const p = await b.newPage({viewport: {width: +m[1], height: +m[2]}, deviceScaleFactor: 1});
    await p.setContent(html, {waitUntil: 'networkidle'}); await p.waitForTimeout(500);
    await p.screenshot({path: path.join(dir, f.replace('.html', '.png'))}); await p.close(); }
  await b.close(); })();
