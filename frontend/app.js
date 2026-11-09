async function fetchJson(url, options = {}) {
  const res = await fetch(url, options);
  if (!res.ok) {
    throw new Error(`${res.status}: ${res.statusText}`);
  }
  return res.json();
}

async function refreshDashboard() {
  try {
    const status = await fetchJson('/api/status');
    const camera = status.camera || {};
    const esp32 = status.esp32 || {};

    const generic = !camera.error && !esp32.error ? 'Sistema OK' : 'Requiere revisión';
    document.getElementById('system-status').textContent = generic;

    const espText = esp32.error
      ? `ESP32: ${esp32.error}`
      : `Wi-Fi: ${esp32.wifi_connected ?? 'desconocido'} · Estado: ${esp32.estado ?? 'sin datos'}`;
    document.getElementById('esp32-status').textContent = espText;

    const camText = camera.error
      ? `Cámara: ${camera.error}`
      : `Cámara: ${camera.camara ? 'activa' : 'inactiva'} · RSSI: ${camera.rssi ?? 'n/d'}`;
    document.getElementById('camera-status').textContent = camText;

    const level = esp32.nivel_tolva ?? 'n/d';
    document.getElementById('food-level').textContent = `${level}%`;

    const cameraImg = document.getElementById('camera-stream');
    if (camera.camara) {
      cameraImg.src = '/api/camera/stream?t=' + Date.now();
      cameraImg.style.display = 'block';
    } else {
      cameraImg.src = 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent('<svg xmlns="http://www.w3.org/2000/svg" width="800" height="450"><rect width="100%" height="100%" fill="#0d1425"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" fill="#7ea8ff" font-size="30">Cámara desconectada</text></svg>');
    }
  } catch (error) {
    document.getElementById('system-status').textContent = 'Sin respuesta del backend';
    document.getElementById('esp32-status').textContent = error.message;
    document.getElementById('camera-status').textContent = 'Sin datos';
    document.getElementById('food-level').textContent = 'n/d';
  }
}

async function loadGallery() {
  try {
    const data = await fetchJson('/api/gallery');
    const grid = document.getElementById('gallery-grid');
    grid.innerHTML = '';
    if (!data.items || !data.items.length) {
      grid.innerHTML = '<p>No hay capturas aún.</p>';
      return;
    }

    data.items.forEach((item) => {
      const cell = document.createElement('div');
      cell.className = 'gallery-item';
      cell.innerHTML = `
        <img src="/api/gallery/${encodeURIComponent(item.name)}" alt="${item.name}" />
        <div style="padding:10px;">
          <strong>${item.name}</strong><br />
          <small>${item.mtime}</small>
        </div>
      `;
      grid.appendChild(cell);
    });
  } catch (error) {
    console.error(error);
  }
}

async function captureNow() {
  try {
    const result = await fetchJson('/api/capture', { method: 'POST' });
    if (result.ok) {
      await loadGallery();
      await refreshDashboard();
    }
  } catch (error) {
    console.error(error);
  }
}

async function dispenseNow() {
  const msg = document.getElementById('dispense-message');
  msg.textContent = 'La dispensación manual está deshabilitada en esta versión por seguridad.';
  try {
    const result = await fetchJson('/api/dispense', { method: 'POST' });
    msg.textContent = result.message || 'La acción no está habilitada.';
  } catch (error) {
    msg.textContent = 'La acción no está habilitada por seguridad.';
  }
}

document.getElementById('capture-btn').addEventListener('click', captureNow);
document.getElementById('refresh-btn').addEventListener('click', refreshDashboard);
document.getElementById('dispense-btn').addEventListener('click', dispenseNow);

refreshDashboard();
loadGallery();
setInterval(() => {
  refreshDashboard();
  loadGallery();
}, 5000);
