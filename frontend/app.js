"use strict";
// Dashboard del dispensador. Todo texto externo se inserta con textContent (nunca innerHTML).
const $ = (id) => document.getElementById(id);
const H = { "X-Requested-With": "dashboard", "Content-Type": "application/json" };
let status = null, es = null, lastMsg = 0, distSamples = [], camShown = false, streamKey = 0;

function set(id, text) { const e = $(id); if (e) e.textContent = text; }
function dot(id, cls, text) {
  const e = $(id); e.replaceChildren();
  const d = document.createElement("span"); d.className = "dot " + cls;
  e.append(d, document.createTextNode(text));
}
function fmtDur(s) {
  if (s == null || s < 0) return "—";
  s = Math.floor(s); const d = Math.floor(s / 86400), h = Math.floor(s % 86400 / 3600), m = Math.floor(s % 3600 / 60);
  return (d ? d + " d " : "") + (h || d ? h + " h " : "") + m + " min" + (s < 60 ? " " + s + " s" : "");
}
function fmtTs(iso) { const d = new Date(iso); return isNaN(d) ? iso : d.toLocaleString(); }
async function api(method, path, body, extra) {
  const r = await fetch(path, { method, headers: { ...H, ...(extra || {}) }, body: body ? JSON.stringify(body) : undefined });
  let data = {}; try { data = await r.json(); } catch (_) {}
  return { ok: r.ok, status: r.status, data };
}

// ---------- navegación ----------
document.querySelectorAll(".nav").forEach((b) => b.addEventListener("click", () => show(b.dataset.view)));
function show(v) {
  document.querySelectorAll(".nav").forEach((b) => b.classList.toggle("active", b.dataset.view === v));
  document.querySelectorAll(".view").forEach((s) => s.classList.toggle("active", s.id === "view-" + v));
  if (v === "galeria") loadGallery();
  if (v === "historial") loadHistory();
  updateCamera();
}

// ---------- estado en tiempo real (SSE con reintento + sondeo de respaldo) ----------
function connect() {
  es = new EventSource("/api/events");
  es.addEventListener("status", (e) => { lastMsg = Date.now(); status = JSON.parse(e.data); render(); });
  es.addEventListener("evento", () => { lastMsg = Date.now(); if ($("view-historial").classList.contains("active")) loadHistory(); });
  es.onerror = () => { es.close(); setLink(false); setTimeout(connect, 3000); };
  es.onopen = () => setLink(true);
}
function setLink(ok) {
  const e = $("link-state"); e.replaceChildren();
  const d = document.createElement("span"); d.className = "dot " + (ok ? "on" : "off");
  e.append(d, document.createTextNode(ok ? "Dashboard en vivo" : "Sin conexión con el servidor"));
  const b = $("banner"); b.hidden = ok; b.textContent = ok ? "" : "No hay conexión con el servidor local. Los datos mostrados no están actualizados.";
  if (!ok) { status = null; render(); }
}

// ---------- render ----------
function render() {
  const s = status;
  const esp = s && s.esp32, cam = s && s.camera, d = esp && esp.data;
  dot("k-esp", esp && esp.online ? "on" : "off", esp && esp.online ? "Conectado" : "Desconectado");
  set("k-esp-sub", !esp ? "Sin datos del servidor" : esp.online ? (esp.ip || "") : esp.age_s != null ? "Último dato hace " + fmtDur(esp.age_s) : "Nunca se ha conectado");
  dot("k-cam", cam && cam.online ? "on" : "off", cam && cam.online ? "Conectada" : "Desconectada");
  set("k-cam-sub", cam ? cam.url : "");
  if (d) {
    set("k-wifi", d.wifi_conectado ? "Conectado" : "Sin Wi-Fi");
    set("k-wifi-sub", d.rssi ? d.rssi + " dBm" + (d.backend ? " · servidor enlazado" : "") : "");
    const nv = d.nivel_tolva, ok = d.sensor_nivel_ok && nv >= 0;
    set("k-nivel", ok ? Math.round(nv) + " %" : "Sin lectura");
    set("k-nivel-sub", d.alerta_tolva && d.alerta_tolva !== "NINGUNA" ? "Alerta: " + d.alerta_tolva : ok ? "Nivel estimado" : "Revise el sensor de la tolva");
    const f = $("g-fill"); f.style.width = (ok ? Math.max(0, Math.min(100, nv)) : 0) + "%";
    f.style.background = !ok ? "var(--muted)" : nv < 20 ? "var(--bad)" : nv < 35 ? "var(--warn)" : "var(--ok)";
    set("k-dist", d.sensor_nivel_ok ? d.distancia_nivel_cm.toFixed(1) + " cm" : "—");
    set("k-servo", d.servo === "DISPENSANDO" ? "Dispensando" : d.servo === "ERROR" ? "Error" : "En reposo");
    set("k-servo-sub", "Pulso " + d.pulso_servo_us + " µs");
    set("k-last", d.ultima_dispensacion_hace_s >= 0 ? "hace " + fmtDur(d.ultima_dispensacion_hace_s) : "Ninguna");
    set("k-last-sub", d.ultima_dispensacion_hace_s >= 0 ? d.ultimas_porciones + " porc. · " + d.ultimo_origen + " · " + d.dispensaciones_total + " en total" : "");
    set("k-up", fmtDur(d.uptime_s)); set("k-up-sub", "ESP32 · servidor " + fmtDur(s.backend_uptime_s));
    const err = d.error;
    set("k-general", err ? "Atención" : d.dispensando ? "Dispensando" : "Operativo");
    set("k-general-sub", err ? err : "Estado: " + d.estado);
    pushDist(d);
  } else {
    ["k-wifi", "k-nivel", "k-dist", "k-servo", "k-last", "k-up"].forEach((i) => set(i, "—"));
    ["k-wifi-sub", "k-nivel-sub", "k-servo-sub", "k-last-sub"].forEach((i) => set(i, ""));
    $("g-fill").style.width = "0";
    set("k-up-sub", s ? "servidor " + fmtDur(s.backend_uptime_s) : "");
    set("k-general", s ? "ESP32 desconectado" : "Sin datos"); set("k-general-sub", "No se muestran valores antiguos como actuales");
  }
  renderPhoto(s && s.last_photo); renderAlerts(s); renderControl(); updateCamera(); drawSpark();
  const sel = $("auto-sel"); if (s && document.activeElement !== sel) sel.value = String(s.auto_capture_s);
}
function pushDist(d) {
  if (!d.sensor_nivel_ok) return;
  const last = distSamples[distSamples.length - 1];
  if (last && Date.now() - last.t < 1500) return;
  distSamples.push({ t: Date.now(), v: d.distancia_nivel_cm }); if (distSamples.length > 60) distSamples.shift();
}
function drawSpark() {
  const c = $("spark"), g = c.getContext("2d"); g.clearRect(0, 0, c.width, c.height);
  if (distSamples.length < 2) return;
  const vs = distSamples.map((x) => x.v), mn = Math.min(...vs), mx = Math.max(...vs, mn + 1);
  g.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue("--accent") || "#3da9fc"; g.lineWidth = 2; g.beginPath();
  vs.forEach((v, i) => { const x = i / (vs.length - 1) * (c.width - 4) + 2, y = c.height - 4 - (v - mn) / (mx - mn) * (c.height - 8); i ? g.lineTo(x, y) : g.moveTo(x, y); });
  g.stroke();
}
function renderPhoto(p) {
  const box = $("k-photo"); box.replaceChildren();
  if (!p) { box.textContent = "Sin fotografías todavía."; return; }
  const img = document.createElement("img"); img.src = "/api/gallery/" + encodeURIComponent(p.name); img.alt = "Última captura";
  img.style.cssText = "max-width:260px;width:100%;border-radius:8px;display:block;cursor:zoom-in"; img.onclick = () => openPhoto(p.name);
  const t = document.createElement("div"); t.className = "sub"; t.textContent = fmtTs(p.ts);
  box.append(img, t);
}
function renderAlerts(s) {
  const ul = $("k-alerts"); ul.replaceChildren(); const items = [];
  if (!s) items.push("Sin conexión con el servidor local.");
  else {
    if (!s.esp32.online) items.push("ESP32 desconectado.");
    if (!s.camera.online) items.push("ESP32-CAM desconectada.");
    const d = s.esp32.data;
    if (d) {
      if (d.error) items.push("Error del ESP32: " + d.error);
      if (d.alerta_tolva && d.alerta_tolva !== "NINGUNA") items.push("Tolva: " + d.alerta_tolva);
      if (!d.sensor_nivel_ok) items.push("El sensor de nivel no entrega lectura.");
      if (!d.wifi_conectado) items.push("El ESP32 perdió el Wi-Fi.");
    }
  }
  if (!items.length) items.push("Sin alertas.");
  items.forEach((t) => { const li = document.createElement("li"); li.textContent = t; ul.append(li); });
}

// ---------- cámara ----------
function updateCamera() {
  const active = $("view-camara").classList.contains("active");
  const online = !!(status && status.camera.online);
  const img = $("cam-img");
  const streamMode = !!(status && status.camera.data && status.camera.data.stream);
  // Si el dispositivo no transmite video (stream:false): "en vivo" = un fotograma nuevo cada 3 s, sin guardarlo.
  if (active && online && !streamMode) { if (!frameTimer) { loadFrame(); frameTimer = setInterval(loadFrame, 3000); } } else stopFrames();
  if (!streamMode) { /* sin flujo MJPEG */ } else if (active && online && !camShown) { img.src = "/api/camera/stream?k=" + (++streamKey); img.hidden = false; $("cam-off").hidden = true; camShown = true; }
  if ((!active || !online || !streamMode) && camShown) { img.removeAttribute("src"); img.hidden = true; camShown = false; }  // cerrar el flujo libera la cámara
  if (!online) { $("cam-img").hidden = true; $("cam-off").hidden = false; set("cam-off", status ? "Cámara desconectada. Revise alimentación y Wi-Fi y pulse «Actualizar conexión»." : "Sin conexión con el servidor."); }
  $("btn-capture").disabled = !online;
  const c = status && status.camera, m = $("cam-meta"); m.replaceChildren();
  const rows = [["Estado", online ? "Conectada" : "Desconectada"], ["Dirección", c ? c.url : "—"],
    ["Modo", c && c.data ? (c.data.stream ? "Video MJPEG" : "Solo fotos (un fotograma cada 3 s)") : "—"],
    ["Resolución", c && c.data ? (c.data.camara_res || c.data.resolucion || "n/d") : "—"],
    ["Fotos / fallos", c && c.data ? c.data.fotos_ok + " / " + c.data.fotos_fallidas : "—"]];
  rows.forEach(([k, v]) => { const dt = document.createElement("dt"), dd = document.createElement("dd"); dt.textContent = k; dd.textContent = v; m.append(dt, dd); });
}
let frameTimer = null, frameBusy = false;
function stopFrames() { if (frameTimer) { clearInterval(frameTimer); frameTimer = null; } }
function loadFrame() {
  if (frameBusy) return; frameBusy = true;
  const im = new Image();
  im.onload = () => { $("cam-img").src = im.src; $("cam-img").hidden = false; $("cam-off").hidden = true; frameBusy = false; };
  im.onerror = () => { frameBusy = false; const f = $("cam-flash"); f.textContent = "✕ Sin fotograma (¿dispensando?)"; f.hidden = false; setTimeout(() => (f.hidden = true), 2500); };
  im.src = "/api/camera/frame?t=" + Date.now();
}
$("cam-img").addEventListener("error", () => { if (camShown) { camShown = false; setTimeout(updateCamera, 2000); } });
$("btn-cam-refresh").onclick = async () => { await api("POST", "/api/camera/refresh"); };
$("btn-capture").onclick = async () => {
  const b = $("btn-capture"); b.disabled = true; b.textContent = "Capturando…";
  const r = await api("POST", "/api/capture");
  b.textContent = "Capturar fotografía"; b.disabled = false;
  const f = $("cam-flash"); f.textContent = r.ok ? "● Captura guardada" : "✕ " + (r.data.error || "falló");
  f.hidden = false; setTimeout(() => (f.hidden = true), 2500);
};
$("auto-sel").onchange = async (e) => { const r = await api("POST", "/api/auto-capture", { interval_s: parseInt(e.target.value, 10) }); if (!r.ok) alert(r.data.error); };

// ---------- galería ----------
let photos = [];
async function loadGallery() { const r = await api("GET", "/api/gallery"); if (r.ok) { photos = r.data.items; renderGallery(); } }
function renderGallery() {
  const g = $("gal-grid"); g.replaceChildren();
  const list = photos.slice(); if ($("gal-order").value === "asc") list.reverse();
  $("gal-empty").hidden = list.length > 0; set("gal-count", list.length + " fotos");
  list.forEach((p) => {
    const card = document.createElement("div"); card.className = "thumb";
    const img = document.createElement("img"); img.loading = "lazy"; img.alt = p.name; img.src = "/api/gallery/" + encodeURIComponent(p.name); img.onclick = () => openPhoto(p.name);
    const info = document.createElement("div"); info.className = "info";
    const t = document.createElement("span"); t.textContent = fmtTs(p.ts) + " · " + Math.round(p.size / 1024) + " kB";
    const acts = document.createElement("div"); acts.className = "acts";
    const dl = document.createElement("a"); dl.className = "btn"; dl.textContent = "Descargar"; dl.href = "/api/gallery/" + encodeURIComponent(p.name) + "?download=1";
    const del = document.createElement("button"); del.className = "btn"; del.textContent = "Eliminar";
    del.onclick = async () => {
      if (!(await confirmDlg("Eliminar fotografía", "Se borrará " + p.name + " de forma permanente. ¿Continuar?"))) return;
      const r = await api("DELETE", "/api/gallery/" + encodeURIComponent(p.name), null, { "X-Confirm": "delete" });
      if (r.ok) loadGallery(); else alert(r.data.error || "No se pudo eliminar");
    };
    acts.append(dl, del); info.append(t, acts); card.append(img, info); g.append(card);
  });
}
function openPhoto(name) {
  $("dlg-img").src = "/api/gallery/" + encodeURIComponent(name); $("dlg-dl").href = "/api/gallery/" + encodeURIComponent(name) + "?download=1";
  $("dlg-photo").showModal();
}
$("dlg-close").onclick = () => $("dlg-photo").close();
$("btn-gal-refresh").onclick = loadGallery; $("gal-order").onchange = renderGallery;

// ---------- control ----------
const sel = $("portions");
function renderControl() {
  const s = status, d = s && s.esp32.data;
  if (s && sel.options.length !== s.max_portions) { sel.replaceChildren(); for (let i = 1; i <= s.max_portions; i++) sel.append(new Option(i + (i === 1 ? " porción" : " porciones"), i)); }
  const can = !!(s && s.remote_commands && s.esp32.online && d && !d.dispensando);
  $("btn-dispense").disabled = !can; $("btn-reset").disabled = !(s && s.remote_commands && s.esp32.online);
  set("ctl-note", !s ? "Sin conexión con el servidor." : !s.remote_commands ? "Control remoto deshabilitado: defina TOKEN_DISPOSITIVO en backend/.env y en secrets.h del ESP32." : !s.esp32.online ? "El ESP32 está desconectado: no se pueden enviar comandos." : d && d.dispensando ? "Hay una dispensación en curso." : "El dispensador está listo. Cada dispensación pide confirmación.");
  const m = $("ctl-meta"); m.replaceChildren();
  if (d) [["Estado", d.estado], ["Servo", d.servo], ["Espera (cooldown)", d.cooldown_s + " s"], ["Último resultado", d.ultimo_resultado], ["Dispensaciones", d.dispensaciones_total + " (24 h: " + d.dispensaciones_24h + ")"]]
    .forEach(([k, v]) => { const dt = document.createElement("dt"), dd = document.createElement("dd"); dt.textContent = k; dd.textContent = v; m.append(dt, dd); });
}
function msg(t, cls) { const e = $("ctl-msg"); e.textContent = t; e.className = "msg " + (cls || ""); }
$("btn-dispense").onclick = async () => {
  const n = parseInt(sel.value, 10);
  if (!(await confirmDlg("Confirmar dispensación", "Se moverá el servo para entregar " + n + (n === 1 ? " porción" : " porciones") + " de alimento. ¿Continuar?"))) return;
  $("btn-dispense").disabled = true; msg("Enviando comando…");
  const r = await api("POST", "/api/dispense", { porciones: n, confirm: true });
  if (r.ok) msg("Comando aceptado por el ESP32 (" + (r.data.resultado || "OK") + ").", "okc");
  else msg("No se dispensó: " + (r.data.error || r.data.resultado || "error " + r.status), "err");
};
$("btn-reset").onclick = async () => {
  if (!(await confirmDlg("Borrar errores", "Se pedirá al ESP32 borrar sus errores. Confirme que revisó el mecanismo."))) return;
  const r = await api("POST", "/api/reset-errors"); msg(r.ok ? (r.data.resultado || "OK") : (r.data.error || "error " + r.status), r.ok ? "okc" : "err");
};
function confirmDlg(title, text) {
  return new Promise((res) => {
    const d = $("dlg-confirm"); set("dlg-title", title); set("dlg-text", text);
    d.onclose = () => res(d.returnValue === "yes"); d.returnValue = "no"; d.showModal();
  });
}

// ---------- historial ----------
async function loadHistory() {
  const t = $("hist-type").value; const r = await api("GET", "/api/history?limit=200" + (t ? "&tipo=" + t : ""));
  const ul = $("hist-list"); ul.replaceChildren(); if (!r.ok) return;
  if (!r.data.items.length) { const li = document.createElement("li"); li.textContent = "Sin eventos."; ul.append(li); }
  r.data.items.forEach((e) => {
    const li = document.createElement("li"); li.className = e.tipo;
    const ts = document.createElement("span"); ts.className = "t"; ts.textContent = fmtTs(e.ts);
    const k = document.createElement("span"); k.className = "k"; k.textContent = e.tipo;
    const m = document.createElement("span"); m.textContent = e.mensaje; li.append(ts, k, m); ul.append(li);
  });
}
$("hist-type").onchange = loadHistory; $("btn-hist-refresh").onclick = loadHistory;

// Si el flujo SSE se queda mudo (red caída sin cierre), se marca como desconectado.
setInterval(() => { if (lastMsg && Date.now() - lastMsg > 20000) { setLink(false); lastMsg = 0; } }, 5000);
setLink(false); connect(); renderControl();
