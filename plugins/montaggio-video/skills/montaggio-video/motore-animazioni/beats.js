// Foglio di fotogrammi di una clip ai tempi indicati, per controllarla prima del render.
// uso: NODE_PATH=<node_modules> node beats.js dist/clip.html foglio.png t1 t2 ...
// Le clip trasparenti vengono mostrate su nero. Da motion-broll (MIT), adattato.
const {chromium} = require('playwright');
const path = require('path'); const os = require('os'); const fs = require('fs');
const {execFileSync} = require('child_process'); const {pathToFileURL} = require('url');
(async () => {
  const [html, out, ...ts] = process.argv.slice(2);
  if (!html || !out || !ts.length) { console.error('uso: node beats.js clip.html foglio.png t1 t2 ...'); process.exit(2); }
  const opts = process.env.MONTAGGIO_CHROMIUM ? {executablePath: process.env.MONTAGGIO_CHROMIUM} : {};
  const b = await chromium.launch(opts); const p = await b.newPage({viewport: {width: 1920, height: 1080}});
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(pathToFileURL(path.resolve(html)).href + '?render'); await p.evaluate(() => document.fonts.ready);
  const size = await p.evaluate(() => ({W: document.getElementById('stage').offsetWidth, H: document.getElementById('stage').offsetHeight}));
  await p.setViewportSize({width: size.W, height: size.H});
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'fogli-'));
  await p.evaluate(() => { if (document.documentElement.classList.contains('alpha')) {
    document.documentElement.style.background = '#000'; document.body.style.background = '#000'; } });
  for (let i = 0; i < ts.length; i++) { await p.evaluate(t => seek(t), +ts[i]);
    await p.screenshot({path: path.join(dir, `${String(i).padStart(3, '0')}.png`)}); }
  await b.close();
  const cols = Math.min(4, ts.length), rows = Math.ceil(ts.length / cols);
  execFileSync('ffmpeg', ['-loglevel', 'error', '-y', '-i', path.join(dir, '%03d.png'), '-vf',
    `scale=640:-1,tile=${cols}x${rows}:padding=4:color=white`, '-frames:v', '1', out]);
  fs.rmSync(dir, {recursive: true, force: true});
  if (errs.length) { console.log('ERRORI NELLA PAGINA:', errs); process.exit(1); }
  console.log('creato', out);
})();
