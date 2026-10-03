// Renderiza los cuadros de las escenas 3D (three.js + Chromium sin pantalla).
//   node render3d.mjs escenas3d.json carpeta_cuadros [fps] [solo_id]
// Requiere: npm install three playwright (o el Chromium de Playwright) y un servidor HTTP
// sirviendo la carpeta web/ en http://127.0.0.1:8099 (python -m http.server 8099 -d web).
import { chromium } from 'playwright';
import { readFileSync, mkdirSync } from 'fs';
const [, , archivo, dir, fpsTxt = '25', solo] = process.argv;
const fps = +fpsTxt;
const escenas = JSON.parse(readFileSync(archivo, 'utf8')).filter(e => !solo || e.id === solo);
const b = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader'] });
const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
p.on('console', m => console.log('consola:', m.text()));
await p.goto('http://127.0.0.1:8099/escena3d.html');
await p.waitForFunction(() => window.listo === true);
for (const e of escenas) {
  const t0 = Date.now();
  mkdirSync(`${dir}/${e.id}`, { recursive: true });
  await p.evaluate(async (e) => await window.preparar(e), e);
  const n = Math.round(e.duracion * fps);
  for (let i = 0; i < n; i++) {
    await p.evaluate((t) => window.cuadro(t), i / fps);
    await p.screenshot({ path: `${dir}/${e.id}/${String(i).padStart(5, '0')}.jpg`, type: 'jpeg', quality: 92 });
  }
  console.log(`${e.id}: ${n} cuadros en ${((Date.now() - t0) / 1000).toFixed(0)} s`);
}
await b.close();
