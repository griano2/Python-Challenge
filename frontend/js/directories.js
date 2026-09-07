/**
 * directories.js — Directories section logic.
 */

// directories[] is shared with sync_pairs.js via the global reference.
let directories = [];

const DIR_TYPES = ['AD', 'LDS', 'ENTRA'];

// ── Load & Render ────────────────────────────────────────────────────────────

async function loadDirectories() {
  directories = await API.getDirectories();
  renderDirectoriesTable();
}

function dirTypeBadge(type) {
  const map = { AD: 'badge-ad', LDS: 'badge-lds', ENTRA: 'badge-entra' };
  return `<span class="badge ${map[type] || 'badge-ad'}">${type}</span>`;
}

function renderDirectoriesTable() {
  const tbody = document.querySelector('#dirs-table tbody');
  if (!tbody) return;

  if (!directories.length) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">🌐</div><p>No hay directorios configurados.</p></div></td></tr>`;
    return;
  }

  tbody.innerHTML = directories.map((dir, i) => {
    const hostOrTenant = dir.host
      ? `${dir.host}:${dir.port || ''}`
      : dir.tenant_id || '—';

    return `<tr data-index="${i}">
      <td class="td-name">${dir.name}</td>
      <td>${dirTypeBadge(dir.dir_type)}</td>
      <td class="td-mono">${hostOrTenant}</td>
      <td><span class="badge ${dir.enabled !== false ? 'badge-enabled' : 'badge-disabled'}">${dir.enabled !== false ? '● Activo' : '○ Inactivo'}</span></td>
      <td>
        <div class="td-actions">
          <button class="btn btn-secondary btn-sm" onclick="openEditDirModal(${i})">✏ Editar</button>
          <button class="btn btn-danger btn-sm btn-icon" onclick="deleteDir('${dir.name}')" title="Eliminar">🗑</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

// ── Modal — Create / Edit ────────────────────────────────────────────────────

function buildDirModalContent(dir = null) {
  const typeOptions = DIR_TYPES.map(t =>
    `<option value="${t}" ${dir?.dir_type === t ? 'selected' : ''}>${t}</option>`).join('');

  const isEntra = dir?.dir_type === 'ENTRA';
  const isLdap  = !isEntra;

  return `
    <form id="dir-form" class="form-grid">
      <div class="form-group">
        <label class="form-label">Nombre *</label>
        <input class="form-input" name="name" value="${dir?.name || ''}" required ${dir ? 'readonly' : ''}>
      </div>
      <div class="form-group">
        <label class="form-label">Tipo *</label>
        <select class="form-select" name="dir_type" onchange="refreshDirFields(this.value)">${typeOptions}</select>
      </div>
      <div class="form-group span-2">
        <label class="form-label">Display Name</label>
        <input class="form-input" name="display_name" value="${dir?.display_name || ''}">
      </div>
      <div class="form-group span-2">
        <label class="form-label">Estado</label>
        <label class="form-toggle">
          <input type="checkbox" id="dir-enabled" name="enabled" ${dir?.enabled !== false ? 'checked' : ''}>
          <div class="toggle-track"><div class="toggle-thumb"></div></div>
          <span>Habilitado</span>
        </label>
      </div>

      <!-- LDAP / AD / LDS fields -->
      <div id="ldap-fields" style="display:${isLdap ? 'contents' : 'none'}">
        <div class="section-divider">Conexión LDAP</div>
        <div class="form-group">
          <label class="form-label">Host</label>
          <input class="form-input" name="host" value="${dir?.host || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">Puerto</label>
          <input class="form-input" name="port" type="number" value="${dir?.port || 636}">
        </div>
        <div class="form-group">
          <label class="form-label">Search Base</label>
          <input class="form-input" name="search_base" value="${dir?.search_base || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">Group Filter Attribute</label>
          <input class="form-input" name="group_filter_attribute" value="${dir?.group_filter_attribute || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">Member Attribute</label>
          <input class="form-input" name="member_attribute" value="${dir?.member_attribute || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">User ID Attribute</label>
          <input class="form-input" name="user_id_attribute" value="${dir?.user_id_attribute || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">UID Attribute</label>
          <input class="form-input" name="uid_attribute" value="${dir?.uid_attribute || 'uidNumber'}">
        </div>
        <div class="form-group">
          <label class="form-label">SSL</label>
          <label class="form-toggle">
            <input type="checkbox" id="dir-ssl" name="use_ssl" ${dir?.use_ssl !== false ? 'checked' : ''}>
            <div class="toggle-track"><div class="toggle-thumb"></div></div>
            <span>Usar SSL</span>
          </label>
        </div>
        <div class="form-group">
          <label class="form-label">Group name is alias</label>
          <label class="form-toggle">
            <input type="checkbox" id="dir-alias" name="group_name_is_alias" ${dir?.group_name_is_alias ? 'checked' : ''}>
            <div class="toggle-track"><div class="toggle-thumb"></div></div>
            <span>Sí</span>
          </label>
        </div>
        <div class="form-group">
          <label class="form-label">Secret Name (Vault)</label>
          <input class="form-input" name="secret_name" value="${dir?.secret_name || ''}">
        </div>
      </div>

      <!-- Entra ID fields -->
      <div id="entra-fields" style="display:${isEntra ? 'contents' : 'none'}">
        <div class="section-divider">Entra ID (Azure AD)</div>
        <div class="form-group">
          <label class="form-label">Tenant ID</label>
          <input class="form-input" name="tenant_id" value="${dir?.tenant_id || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">Client ID</label>
          <input class="form-input" name="client_id" value="${dir?.client_id || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">Authority URL</label>
          <input class="form-input" name="authority" value="${dir?.authority || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">Graph Base URL</label>
          <input class="form-input" name="graph_base_url" value="${dir?.graph_base_url || 'https://graph.microsoft.com/v1.0'}">
        </div>
        <div class="form-group span-2">
          <label class="form-label">Scopes (separados por coma)</label>
          <input class="form-input" name="scopes" value="${dir?.scopes ? dir.scopes.join(', ') : 'Group.ReadWrite.All'}">
        </div>
      </div>
    </form>`;
}

function refreshDirFields(type) {
  const ldap  = document.getElementById('ldap-fields');
  const entra = document.getElementById('entra-fields');
  if (!ldap || !entra) return;
  ldap.style.display  = type === 'ENTRA' ? 'none' : 'contents';
  entra.style.display = type === 'ENTRA' ? 'contents' : 'none';
}

function openNewDirModal() {
  const modal = document.getElementById('dir-modal');
  document.getElementById('dir-modal-title').textContent = 'Nuevo Directory';
  document.getElementById('dir-modal-body').innerHTML = buildDirModalContent();
  document.getElementById('dir-modal-save').dataset.editing = '';
  document.getElementById('dir-modal-save').onclick = saveDir;
  modal.classList.add('open');
}

function openEditDirModal(index) {
  const dir = directories[index];
  const modal = document.getElementById('dir-modal');
  document.getElementById('dir-modal-title').textContent = 'Editar Directory';
  document.getElementById('dir-modal-body').innerHTML = buildDirModalContent(dir);
  document.getElementById('dir-modal-save').dataset.editing = dir.name;
  document.getElementById('dir-modal-save').onclick = saveDir;
  modal.classList.add('open');
}

function closeDirModal() {
  document.getElementById('dir-modal').classList.remove('open');
}

async function saveDir() {
  const form = document.getElementById('dir-form');
  if (!form.checkValidity()) { form.reportValidity(); return; }

  const fd = new FormData(form);
  const dirType = fd.get('dir_type');
  const isEntra = dirType === 'ENTRA';

  const payload = {
    name: fd.get('name'),
    dir_type: dirType,
    display_name: fd.get('display_name') || null,
    enabled: document.getElementById('dir-enabled').checked,
  };

  if (isEntra) {
    payload.tenant_id      = fd.get('tenant_id') || null;
    payload.client_id      = fd.get('client_id') || null;
    payload.authority      = fd.get('authority') || null;
    payload.graph_base_url = fd.get('graph_base_url') || null;
    const scopesRaw        = fd.get('scopes') || '';
    payload.scopes         = scopesRaw.split(',').map(s => s.trim()).filter(Boolean);
    payload.secret_name    = null;
  } else {
    payload.host                  = fd.get('host') || null;
    payload.port                  = parseInt(fd.get('port')) || null;
    payload.search_base           = fd.get('search_base') || null;
    payload.group_filter_attribute = fd.get('group_filter_attribute') || null;
    payload.member_attribute      = fd.get('member_attribute') || null;
    payload.user_id_attribute     = fd.get('user_id_attribute') || null;
    payload.uid_attribute         = fd.get('uid_attribute') || 'uidNumber';
    payload.use_ssl               = document.getElementById('dir-ssl')?.checked ?? true;
    payload.group_name_is_alias   = document.getElementById('dir-alias')?.checked ?? false;
    payload.secret_name           = fd.get('secret_name') || null;
  }

  const editingName = document.getElementById('dir-modal-save').dataset.editing;

  try {
    if (editingName) {
      await API.updateDirectory(editingName, payload);
      showToast('success', 'Directory actualizado', payload.name);
    } else {
      await API.createDirectory(payload);
      showToast('success', 'Directory creado', payload.name);
    }
    closeDirModal();
    await loadDirectories();
  } catch (e) {
    showToast('error', 'Error al guardar', e.message);
  }
}

async function deleteDir(name) {
  if (!confirm(`¿Eliminar el directory "${name}"? Esta acción puede romper sync pairs que lo referencien.`)) return;
  try {
    await API.deleteDirectory(name);
    showToast('success', 'Directory eliminado', name);
    await loadDirectories();
  } catch (e) {
    showToast('error', 'Error al eliminar', e.message);
  }
}
