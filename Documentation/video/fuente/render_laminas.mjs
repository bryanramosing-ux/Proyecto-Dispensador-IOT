// Renderiza cada lámina a PNG de 1280x720 (las de paneo, con fondo transparente).
//   node render_laminas.mjs carpeta_salida      (servidor en http://127.0.0.1:8099 sirviendo web/)
import { chromium } from 'playwright';
const [, , dir] = process.argv;
const b = await chromium.launch();
const p = await b.newPage({ viewport: { width: 1280, height: 720 } });
await p.goto('http://127.0.0.1:8099/laminas.html');
await p.waitForFunction(() => window.listo === true);
const laminas = await (await fetch('http://127.0.0.1:8099/laminas.json')).json();
for (const d of laminas) {
  await p.evaluate(async (d) => await window.lamina(d), d);
  await p.waitForTimeout(150);
  await p.screenshot({ path: `${dir}/${d.id}.png`, omitBackground: !!d.transparente });
  console.log('ok', d.id);
}
await b.close();
