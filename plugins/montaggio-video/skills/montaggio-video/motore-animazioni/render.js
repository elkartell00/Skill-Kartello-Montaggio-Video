// Render di una clip del motore di animazione, fotogramma per fotogramma, con motion blur.
// uso: NODE_PATH=<node_modules> node render.js dist/clip.html out/clip.(mp4|mov) [fps, es. 30000/1001 | 25 | 60]
// 4 sotto-fotogrammi per fotogramma su un otturatore a 180°, fusi con ffmpeg (tmix).
// Clip trasparenti (bg:null) -> ProRes 4444 .mov con canale alfa. Da motion-broll (MIT), adattato.
const {chromium} = require('playwright');
const {spawn} = require('child_process');
const path = require('path');
const {pathToFileURL} = require('url');
(async () => {
  const [html, out, fpsArg] = process.argv.slice(2);
  if (!html || !out) { console.error('uso: node render.js clip.html uscita.mp4|mov [fps]'); process.exit(2); }
  const FPS = !fpsArg ? 30000 / 1001 : (fpsArg.includes('/') ? fpsArg.split('/')[0] / fpsArg.split('/')[1] : +fpsArg);
  const opts = process.env.MONTAGGIO_CHROMIUM ? {executablePath: process.env.MONTAGGIO_CHROMIUM} : {};
  const b = await chromium.launch(opts);
  const p = await b.newPage({viewport: {width: 1920, height: 1080}});
  const errs = []; p.on('pageerror', e => errs.push(e.message));
  await p.goto(pathToFileURL(path.resolve(html)).href + '?render'); await p.evaluate(() => document.fonts.ready);
  const info = await p.evaluate(() => ({T: window.DURATION, W: document.getElementById('stage').offsetWidth,
    H: document.getElementById('stage').offsetHeight, alpha: document.documentElement.classList.contains('alpha')}));
  await p.setViewportSize({width: info.W, height: info.H});
  const N = Math.round(info.T * FPS), K = 4, sub = 1 / (FPS * 2 * K);
  const fr = (fpsArg && fpsArg.includes('/')) ? [fpsArg, `${fpsArg.split('/')[0] * 4}/${fpsArg.split('/')[1]}`]
    : (FPS === 30000 / 1001 ? ['30000/1001', '120000/1001'] : [String(FPS), String(FPS * 4)]);
  const vf = `format=gbrap,tmix=frames=4:weights='1 1 1 1',select='eq(mod(n\\,4)\\,3)',setpts=N/(${fr[0]})/TB`;
  const enc = info.alpha ? ['-c:v', 'prores_ks', '-profile:v', '4', '-pix_fmt', 'yuva444p10le', '-vendor', 'apl0']
    : ['-c:v', 'libx264', '-crf', '14', '-preset', 'medium', '-pix_fmt', 'yuv420p', '-movflags', '+faststart'];
  if (info.alpha && !out.toLowerCase().endsWith('.mov')) { console.error('ERRORE: una clip trasparente va salvata in .mov'); process.exit(2); }
  const ff = spawn('ffmpeg', ['-loglevel', 'error', '-y', '-f', 'image2pipe', '-framerate', fr[1], '-c:v', 'png', '-i', '-',
    '-vf', vf, '-r', fr[0], ...enc, '-color_primaries', 'bt709', '-color_trc', 'bt709', '-colorspace', 'bt709', out]);
  ff.stderr.on('data', d => process.stderr.write(d));
  for (let f = 0; f < N; f++) {
    for (let k = 0; k < K; k++) {
      const t = Math.max(0, f / FPS + (k - 1.5) * sub); await p.evaluate(t => seek(t), t);
      const buf = await p.screenshot({type: 'png', omitBackground: info.alpha});
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
    }
  }
  ff.stdin.end(); const code = await new Promise(r => ff.on('close', r)); await b.close();
  if (code !== 0) { console.error('ERRORE: ffmpeg non è riuscito a scrivere', out); process.exit(1); }
  console.log('creata', out, N, 'fotogrammi', errs.length ? 'ERRORI NELLA PAGINA: ' + errs[0] : '');
  if (errs.length) process.exit(1);
})();
