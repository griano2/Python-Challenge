/**
 * sync_configs.js — Sync Configs section logic.
 *
 * A Sync Config sets a direction + source/target directory once, then holds
 * one or more group mappings (source group -> target group), each of which
 * can be individually enabled/disabled.
 */

let syncConfigs = [];

// In-memory mapping rows while the config modal is open.
let currentMappings = [];

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
  const dirs = window.directories || [];
  return dirs.map(d => d.name);
}

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, c => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  }[c]));
}

// ── Load & Render ────────────────────────────────────────────────────────────

async function loadSyncConfigs() {
  syncConfigs = await API.getSyncConfigs();
  renderSyncConfigsList();
}

function renderSyncConfigsList() {
  const container = document.getElementById('sync-configs-list');
  if (!container) return;

  if (!syncConfigs.length) {
    container.innerHTML = `<div class="empty-state"><div class="empty-icon">🔄</div><p>No sync configs configured.</p></div>`;
    return;
  }

  container.innerHTML = syncConfigs.map((c, i) => {
    const enabledCount = c.mappings.filter(m => m.enabled).length;
    const mappingRows = c.mappings.length
      ? c.mappings.map(m => `
        <div class="mapping-summary-row ${m.enabled ? '' : 'mapping-row-disabled'}">
          <span class="mapping-summary-group">${escapeHtml(m.source_group)}</span>
          <span class="mapping-summary-arrow">→</span>
          <span class="mapping-summary-group">${escapeHtml(m.target_group)}</span>
          <span class="badge ${m.enabled ? 'badge-enabled' : 'badge-disabled'}">${m.enabled ? '● Enabled' : '○ Disabled'}</span>
        </div>`).join('')
      : `<div class="mapping-summary-row"><span class="mapping-summary-group" style="color:var(--text-muted)">No mappings yet</span></div>`;

    return `
    <div class="config-card" data-index="${i}">
      <div class="config-card-header">
        <div class="config-card-title">
          <span class="config-card-name">${escapeHtml(c.name)}</span>
          ${directionLabel(c.direction)}
          <span class="config-card-route">${escapeHtml(c.source_directory)} → ${escapeHtml(c.target_directory)}</span>
          <span class="config-card-count">${enabledCount}/${c.mappings.length} mapping${c.mappings.length === 1 ? '' : 's'} enabled</span>
          <span class="badge ${c.enabled ? 'badge-enabled' : 'badge-disabled'}">${c.enabled ? '● Active' : '○ Disabled'}</span>
        </div>
        <div class="config-card-actions">
          <button class="btn btn-success btn-sm btn-icon" onclick="runConfig('${c.name}')" title="Run">▶</button>
          <button class="btn btn-secondary btn-sm" onclick="openEditConfigModal(${i})">✏ Edit</button>
          <button class="btn btn-danger btn-sm btn-icon" onclick="deleteConfig('${c.name}')" title="Delete">🗑</button>
        </div>
      </div>
      <div class="config-card-body">${mappingRows}</div>
    </div>`;
  }).join('');
}

// ── Run ──────────────────────────────────────────────────────────────────────

function summarizeRun(res) {
  const total = res.mappings.length;
  const ok = res.mappings.filter(m => m.status === 'success').length;
  const failed = res.mappings.filter(m => m.status === 'error');
  if (res.status === 'success') return { type: 'success', title: 'Sync completed', msg: `${ok}/${total} mappings synced` };
  if (res.status === 'skipped') return { type: 'info', title: 'Nothing to run', msg: 'No enabled mappings in this config' };
  if (res.status === 'partial') return { type: 'error', title: `${failed.length} of ${total} mappings failed`, msg: failed.map(m => `${m.source_group}→${m.target_group}`).join(', ') };
  return { type: 'error', title: 'Sync failed', msg: failed.map(m => m.detail).join(', ') || 'Unknown error' };
}

async function runConfig(name) {
  showToast('info', 'Running...', name);
  try {
    const res = await API.runSyncConfig(name);
    const s = summarizeRun(res);
    showToast(s.type, `${s.title}: ${name}`, s.msg);
  } catch (e) {
    showToast('error', `Sync failed: ${name}`, e.message);
  }
}

async function runAllEnabledConfigs() {
  showToast('info', 'Running all enabled configs...');
  try {
    const res = await API.runAllEnabledConfigs();
    const ok = res.results.filter(r => r.status === 'success' || r.status === 'skipped').length;
    const fail = res.results.filter(r => r.status === 'error' || r.status === 'partial').length;
    if (fail === 0) {
      showToast('success', 'All completed', `${ok} configs executed`);
    } else {
      showToast('error', `${fail} config(s) had failures, ${ok} clean`, res.results.filter(r => r.status === 'error' || r.status === 'partial').map(r => r.config).join(', '));
    }
  } catch (e) {
    showToast('error', 'Execution error', e.message);
  }
}

// ── Mapping editor (inside modal) ───────────────────────────────────────────

function renderMappingEditor() {
  const body = document.getElementById('mapping-editor-body');
  if (!body) return;

  if (!currentMappings.length) {
    body.innerHTML = `<div class="mapping-editor-row"><span style="color:var(--text-muted);font-size:12px;grid-column:1/4">No mappings yet — add one below.</span></div>`;
    return;
  }

  body.innerHTML = currentMappings.map((m, i) => `
    <div class="mapping-editor-row" data-idx="${i}">
      <input class="form-input" placeholder="Source group *" value="${escapeHtml(m.source_group)}" oninput="updateMappingField(${i}, 'source_group', this.value)">
      <input class="form-input" placeholder="= source group" value="${escapeHtml(m.target_group)}" oninput="updateMappingField(${i}, 'target_group', this.value)">
      <label class="mapping-row-toggle form-toggle">
        <input type="checkbox" ${m.enabled ? 'checked' : ''} onchange="updateMappingField(${i}, 'enabled', this.checked)">
        <div class="toggle-track"><div class="toggle-thumb"></div></div>
      </label>
      <button type="button" class="mapping-row-remove" title="Remove row" onclick="removeMappingRow(${i})">🗑</button>
    </div>`).join('');
}

function addMappingRow() {
  currentMappings.push({ source_group: '', target_group: '', enabled: true });
  renderMappingEditor();
}

function removeMappingRow(i) {
  currentMappings.splice(i, 1);
  renderMappingEditor();
}

function updateMappingField(i, field, value) {
  if (!currentMappings[i]) return;
  currentMappings[i][field] = value;
}

// ── Modal — Create / Edit ────────────────────────────────────────────────────

function buildConfigModalContent(config = null) {
  let dirNames = getDirNames();
  if (config?.source_directory && !dirNames.includes(config.source_directory)) dirNames.push(config.source_directory);
  if (config?.target_directory && !dirNames.includes(config.target_directory)) dirNames.push(config.target_directory);

  const dirOptions = (selected) => dirNames.length
    ? dirNames.map(n => `<option value="${n}" ${selected === n ? 'selected' : ''}>${n}</option>`).join('')
    : '<option value="" disabled selected>No directories available</option>';

  const directionOptions = DIRECTIONS.map(d => `<option value="${d}" ${config?.direction === d ? 'selected' : ''}>${d}</option>`).join('');

  return `
    <form id="config-form" class="form-grid">
      <div class="form-group span-2">
        <label class="form-label">Config name *</label>
        <input class="form-input" name="name" value="${escapeHtml(config?.name || '')}" required ${config ? 'readonly' : ''}>
      </div>

      <div class="form-group">
        <label class="form-label">Source directory *</label>
        <select class="form-select" name="source_directory" required>${dirOptions(config?.source_directory)}</select>
      </div>
      <div class="form-group">
        <label class="form-label">Target directory *</label>
        <select class="form-select" name="target_directory" required>${dirOptions(config?.target_directory)}</select>
      </div>

      <div class="form-group">
        <label class="form-label">Sync type (direction) *</label>
        <select class="form-select" name="direction">${directionOptions}</select>
      </div>
      <div class="form-group">
        <label class="form-label">Status</label>
        <label class="form-toggle">
          <input type="checkbox" id="config-enabled" ${config?.enabled !== false ? 'checked' : ''}>
          <div class="toggle-track"><div class="toggle-thumb"></div></div>
          <span>Active</span>
        </label>
      </div>

      <div class="section-divider">Group mappings</div>
      <div class="form-group span-2">
        <div class="mapping-editor">
          <div class="mapping-editor-head">
            <span>Source group</span><span>Target group</span><span>Enabled</span><span></span>
          </div>
          <div id="mapping-editor-body"></div>
          <button type="button" class="mapping-editor-add" onclick="addMappingRow()">+ Add mapping</button>
        </div>
      </div>
    </form>`;
}

async function openNewConfigModal() {
  if (!window.directories || !window.directories.length) {
    if (typeof loadDirectories === 'function') await loadDirectories();
  }
  currentMappings = [{ source_group: '', target_group: '', enabled: true }];

  const modal = document.getElementById('config-modal');
  document.getElementById('config-modal-title').textContent = 'New Sync Config';
  document.getElementById('config-modal-body').innerHTML = buildConfigModalContent();
  document.getElementById('config-modal-save').onclick = saveConfig;
  document.getElementById('config-modal-save').dataset.editing = '';
  document.getElementById('config-modal-delete').hidden = true;
  renderMappingEditor();
  modal.classList.add('open');
}

async function openEditConfigModal(index) {
  if (!window.directories || !window.directories.length) {
    if (typeof loadDirectories === 'function') await loadDirectories();
  }
  const config = syncConfigs[index];
  currentMappings = config.mappings.map(m => ({ ...m }));

  const modal = document.getElementById('config-modal');
  document.getElementById('config-modal-title').textContent = 'Edit Sync Config';
  document.getElementById('config-modal-body').innerHTML = buildConfigModalContent(config);
  document.getElementById('config-modal-save').dataset.editing = config.name;
  document.getElementById('config-modal-save').onclick = saveConfig;
  document.getElementById('config-modal-delete').hidden = false;
  document.getElementById('config-modal-delete').dataset.name = config.name;
  renderMappingEditor();
  modal.classList.add('open');
}

function closeConfigModal() {
  document.getElementById('config-modal').classList.remove('open');
  currentMappings = [];
}

async function saveConfig() {
  const form = document.getElementById('config-form');
  if (!form.checkValidity()) { form.reportValidity(); return; }

  const mappings = currentMappings
    .map(m => ({
      source_group: (m.source_group || '').trim(),
      target_group: (m.target_group || '').trim() || (m.source_group || '').trim(),
      enabled: !!m.enabled,
    }))
    .filter(m => m.source_group);

  if (!mappings.length) {
    showToast('error', 'At least one mapping is required', 'Add a source group before saving.');
    return;
  }

  const fd = new FormData(form);
  const payload = {
    name: fd.get('name'),
    source_directory: fd.get('source_directory'),
    target_directory: fd.get('target_directory'),
    direction: fd.get('direction'),
    enabled: document.getElementById('config-enabled').checked,
    mappings,
  };

  const editingName = document.getElementById('config-modal-save').dataset.editing;

  try {
    if (editingName) {
      await API.updateSyncConfig(editingName, payload);
      showToast('success', 'Config updated', payload.name);
    } else {
      await API.createSyncConfig(payload);
      showToast('success', 'Config created', payload.name);
    }
    closeConfigModal();
    await loadSyncConfigs();
  } catch (e) {
    showToast('error', 'Save error', e.message);
  }
}

async function deleteConfig(name) {
  if (!confirm(`Delete sync config "${name}" and all its mappings?`)) return;
  try {
    await API.deleteSyncConfig(name);
    showToast('success', 'Config deleted', name);
    await loadSyncConfigs();
  } catch (e) {
    showToast('error', 'Delete error', e.message);
  }
}

async function deleteConfigFromModal() {
  const name = document.getElementById('config-modal-delete').dataset.name;
  if (!name) return;
  if (!confirm(`Delete sync config "${name}" and all its mappings?`)) return;
  try {
    await API.deleteSyncConfig(name);
    showToast('success', 'Config deleted', name);
    closeConfigModal();
    await loadSyncConfigs();
  } catch (e) {
    showToast('error', 'Delete error', e.message);
  }
}
