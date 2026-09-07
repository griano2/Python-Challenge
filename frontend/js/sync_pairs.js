/**
 * sync_pairs.js — Sync Pairs section logic.
 */

let syncPairs = [];
let directories = [];  // shared reference filled by directories.js

// ── Helpers ─────────────────────────────────────────────────────────────────

const DIRECTIONS = ['AD_TO_AD', 'AD_TO_LDS', 'LDS_TO_AD', 'ENTRA_TO_AD', 'AD_TO_ENTRA'];

function directionLabel(dir) {
  const map = {
    AD_TO_AD:     { label: 'AD → AD',    color: 'ad' },
    AD_TO_LDS:    { label: 'AD → LDS',   color: 'ad' },
    LDS_TO_AD:    { label: 'LDS → AD',   color: 'lds' },
    ENTRA_TO_AD:  { label: 'Entra → AD', color: 'entra' },
    AD_TO_ENTRA:  { label: 'AD → Entra', color: 'entra' },
  };
  const d = map[dir] || { label: dir, color: 'ad' };
  return `<span class="badge badge-${d.color}">${d.label}</span>`;
}

function getDirNames() {
  return directories.map(d => d.name);
}

// ── Load & Render ────────────────────────────────────────────────────────────

async function loadSyncPairs() {
  syncPairs = await API.getSyncPairs();
  renderSyncPairsTable();
}

function renderSyncPairsTable() {
  const tbody = document.querySelector('#sync-pairs-table tbody');
  if (!tbody) return;

  if (!syncPairs.length) {
    tbody.innerHTML = `<tr><td colspan="7"><div class="empty-state"><div class="empty-icon">🔄</div><p>No hay sync pairs configurados.</p></div></td></tr>`;
    return;
  }

  tbody.innerHTML = syncPairs.map((p, i) => `
    <tr data-index="${i}">
      <td><input type="checkbox" class="row-check" data-name="${p.name}"></td>
      <td class="td-name">${p.name}</td>
      <td class="td-mono">${p.source_directory}<br><small>${p.source_group}</small></td>
      <td>${directionLabel(p.direction)}</td>
      <td class="td-mono">${p.target_directory}<br><small>${p.target_group}</small></td>
      <td><span class="badge ${p.enabled ? 'badge-enabled' : 'badge-disabled'}">${p.enabled ? '● Habilitado' : '○ Disabled'}</span></td>
      <td>
        <div class="td-actions">
          <button class="btn btn-success btn-sm btn-icon" onclick="runSinglePair('${p.name}')" title="Ejecutar">▶</button>
          <button class="btn btn-secondary btn-sm" onclick="openEditPairModal(${i})">✏ Editar</button>
          <button class="btn btn-danger btn-sm btn-icon" onclick="deletePair('${p.name}')" title="Eliminar">🗑</button>
        </div>
      </td>
    </tr>`).join('');
}

// ── Run ──────────────────────────────────────────────────────────────────────

async function runSinglePair(name) {
  showToast('info', 'Ejecutando...', name);
  const res = await API.runSyncPair(name);
  if (res.status === 'success') {
    showToast('success', 'Sync completado', name);
  } else {
    showToast('error', `Sync falló: ${name}`, res.detail || 'Error desconocido');
  }
}

async function runSelectedPairs() {
  const checked = [...document.querySelectorAll('.row-check:checked')].map(cb => cb.dataset.name);
  if (!checked.length) { showToast('info', 'Selecciona al menos un par'); return; }

  for (const name of checked) {
    await runSinglePair(name);
  }
}

async function runAllEnabled() {
  showToast('info', 'Ejecutando todos los pares habilitados...');
  try {
    const res = await API.runAllEnabled();
    const ok = res.results.filter(r => r.status === 'success').length;
    const fail = res.results.filter(r => r.status === 'error').length;
    if (fail === 0) {
      showToast('success', 'Todos completados', `${ok} pares ejecutados`);
    } else {
      showToast('error', `${fail} fallos, ${ok} éxitos`, res.results.filter(r => r.status === 'error').map(r => r.pair).join(', '));
    }
  } catch (e) {
    showToast('error', 'Error al ejecutar', e.message);
  }
}

// ── Modal — Create / Edit ────────────────────────────────────────────────────

function buildPairModalContent(pair = null) {
  const dirOptionsSource = getDirNames().map(n => `<option value="${n}" ${pair?.source_directory === n ? 'selected' : ''}>${n}</option>`).join('');
  const dirOptionsTarget = getDirNames().map(n => `<option value="${n}" ${pair?.target_directory === n ? 'selected' : ''}>${n}</option>`).join('');
  const dirOptions = DIRECTIONS.map(d => `<option value="${d}" ${pair?.direction === d ? 'selected' : ''}>${d}</option>`).join('');

  return `
    <form id="pair-form" class="form-grid">
      <div class="form-group span-2">
        <label class="form-label">Nombre del par *</label>
        <input class="form-input" name="name" value="${pair?.name || ''}" required ${pair ? 'readonly' : ''}>
      </div>
      <div class="section-divider">Origen</div>
      <div class="form-group">
        <label class="form-label">Directory origen *</label>
        <select class="form-select" name="source_directory">${dirOptionsSource}</select>
      </div>
      <div class="form-group">
        <label class="form-label">Grupo origen *</label>
        <input class="form-input" name="source_group" value="${pair?.source_group || ''}" required>
      </div>
      <div class="section-divider">Destino</div>
      <div class="form-group">
        <label class="form-label">Directory destino *</label>
        <select class="form-select" name="target_directory">${dirOptionsTarget}</select>
      </div>
      <div class="form-group">
        <label class="form-label">Grupo destino *</label>
        <input class="form-input" name="target_group" value="${pair?.target_group || ''}" required>
      </div>
      <div class="section-divider">Configuración</div>
      <div class="form-group">
        <label class="form-label">Dirección *</label>
        <select class="form-select" name="direction">${dirOptions}</select>
      </div>
      <div class="form-group">
        <label class="form-label">Estado</label>
        <label class="form-toggle">
          <input type="checkbox" id="pair-enabled" name="enabled" ${pair?.enabled !== false ? 'checked' : ''}>
          <div class="toggle-track"><div class="toggle-thumb"></div></div>
          <span>Habilitado</span>
        </label>
      </div>
    </form>`;
}

function openNewPairModal() {
  const modal = document.getElementById('pair-modal');
  document.getElementById('pair-modal-title').textContent = 'Nuevo Sync Pair';
  document.getElementById('pair-modal-body').innerHTML = buildPairModalContent();
  document.getElementById('pair-modal-save').onclick = savePair;
  document.getElementById('pair-modal-save').dataset.editing = '';
  modal.classList.add('open');
}

function openEditPairModal(index) {
  const pair = syncPairs[index];
  const modal = document.getElementById('pair-modal');
  document.getElementById('pair-modal-title').textContent = 'Editar Sync Pair';
  document.getElementById('pair-modal-body').innerHTML = buildPairModalContent(pair);
  document.getElementById('pair-modal-save').dataset.editing = pair.name;
  document.getElementById('pair-modal-save').onclick = savePair;
  modal.classList.add('open');
}

function closePairModal() {
  document.getElementById('pair-modal').classList.remove('open');
}

async function savePair() {
  const form = document.getElementById('pair-form');
  if (!form.checkValidity()) { form.reportValidity(); return; }

  const fd = new FormData(form);
  const payload = {
    name: fd.get('name'),
    source_directory: fd.get('source_directory'),
    source_group: fd.get('source_group'),
    target_directory: fd.get('target_directory'),
    target_group: fd.get('target_group'),
    direction: fd.get('direction'),
    enabled: document.getElementById('pair-enabled').checked,
  };

  const editingName = document.getElementById('pair-modal-save').dataset.editing;

  try {
    if (editingName) {
      await API.updateSyncPair(editingName, payload);
      showToast('success', 'Par actualizado', payload.name);
    } else {
      await API.createSyncPair(payload);
      showToast('success', 'Par creado', payload.name);
    }
    closePairModal();
    await loadSyncPairs();
  } catch (e) {
    showToast('error', 'Error al guardar', e.message);
  }
}

async function deletePair(name) {
  if (!confirm(`¿Eliminar el sync pair "${name}"?`)) return;
  try {
    await API.deleteSyncPair(name);
    showToast('success', 'Par eliminado', name);
    await loadSyncPairs();
  } catch (e) {
    showToast('error', 'Error al eliminar', e.message);
  }
}
