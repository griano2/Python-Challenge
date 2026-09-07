/**
 * environments.js — Environments section logic.
 */

// environments[] is shared with sync_pairs.js via the global reference.

const ENV_TYPES = ['AD', 'LDS', 'ENTRA'];

// ── Load & Render ────────────────────────────────────────────────────────────

async function loadEnvironments() {
  environments = await API.getEnvironments();
  renderEnvironmentsTable();
}

function envTypeBadge(type) {
  const map = { AD: 'badge-ad', LDS: 'badge-lds', ENTRA: 'badge-entra' };
  return `<span class="badge ${map[type] || 'badge-ad'}">${type}</span>`;
}

function renderEnvironmentsTable() {
  const tbody = document.querySelector('#envs-table tbody');
  if (!tbody) return;

  if (!environments.length) {
    tbody.innerHTML = `<tr><td colspan="5"><div class="empty-state"><div class="empty-icon">🌐</div><p>No hay environments configurados.</p></div></td></tr>`;
    return;
  }

  tbody.innerHTML = environments.map((env, i) => {
    const hostOrTenant = env.host
      ? `${env.host}:${env.port || ''}`
      : env.tenant_id || '—';

    return `<tr data-index="${i}">
      <td class="td-name">${env.name}</td>
      <td>${envTypeBadge(env.env_type)}</td>
      <td class="td-mono">${hostOrTenant}</td>
      <td><span class="badge ${env.enabled !== false ? 'badge-enabled' : 'badge-disabled'}">${env.enabled !== false ? '● Activo' : '○ Inactivo'}</span></td>
      <td>
        <div class="td-actions">
          <button class="btn btn-secondary btn-sm" onclick="openEditEnvModal(${i})">✏ Editar</button>
          <button class="btn btn-danger btn-sm btn-icon" onclick="deleteEnv('${env.name}')" title="Eliminar">🗑</button>
        </div>
      </td>
    </tr>`;
  }).join('');
}

// ── Modal — Create / Edit ────────────────────────────────────────────────────

function buildEnvModalContent(env = null) {
  const typeOptions = ENV_TYPES.map(t =>
    `<option value="${t}" ${env?.env_type === t ? 'selected' : ''}>${t}</option>`).join('');

  const isEntra = env?.env_type === 'ENTRA';
  const isLdap  = !isEntra;

  return `
    <form id="env-form" class="form-grid">
      <div class="form-group">
        <label class="form-label">Nombre *</label>
        <input class="form-input" name="name" value="${env?.name || ''}" required ${env ? 'readonly' : ''}>
      </div>
      <div class="form-group">
        <label class="form-label">Tipo *</label>
        <select class="form-select" name="env_type" onchange="refreshEnvFields(this.value)">${typeOptions}</select>
      </div>
      <div class="form-group span-2">
        <label class="form-label">Display Name</label>
        <input class="form-input" name="display_name" value="${env?.display_name || ''}">
      </div>
      <div class="form-group span-2">
        <label class="form-label">Estado</label>
        <label class="form-toggle">
          <input type="checkbox" id="env-enabled" name="enabled" ${env?.enabled !== false ? 'checked' : ''}>
          <div class="toggle-track"><div class="toggle-thumb"></div></div>
          <span>Habilitado</span>
        </label>
      </div>

      <!-- LDAP / AD / LDS fields -->
      <div id="ldap-fields" style="display:${isLdap ? 'contents' : 'none'}">
        <div class="section-divider">Conexión LDAP</div>
        <div class="form-group">
          <label class="form-label">Host</label>
          <input class="form-input" name="host" value="${env?.host || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">Puerto</label>
          <input class="form-input" name="port" type="number" value="${env?.port || 636}">
        </div>
        <div class="form-group">
          <label class="form-label">Search Base</label>
          <input class="form-input" name="search_base" value="${env?.search_base || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">Group Filter Attribute</label>
          <input class="form-input" name="group_filter_attribute" value="${env?.group_filter_attribute || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">Member Attribute</label>
          <input class="form-input" name="member_attribute" value="${env?.member_attribute || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">User ID Attribute</label>
          <input class="form-input" name="user_id_attribute" value="${env?.user_id_attribute || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">UID Attribute</label>
          <input class="form-input" name="uid_attribute" value="${env?.uid_attribute || 'uidNumber'}">
        </div>
        <div class="form-group">
          <label class="form-label">SSL</label>
          <label class="form-toggle">
            <input type="checkbox" id="env-ssl" name="use_ssl" ${env?.use_ssl !== false ? 'checked' : ''}>
            <div class="toggle-track"><div class="toggle-thumb"></div></div>
            <span>Usar SSL</span>
          </label>
        </div>
        <div class="form-group">
          <label class="form-label">Group name is alias</label>
          <label class="form-toggle">
            <input type="checkbox" id="env-alias" name="group_name_is_alias" ${env?.group_name_is_alias ? 'checked' : ''}>
            <div class="toggle-track"><div class="toggle-thumb"></div></div>
            <span>Sí</span>
          </label>
        </div>
        <div class="form-group">
          <label class="form-label">Secret Name (Vault)</label>
          <input class="form-input" name="secret_name" value="${env?.secret_name || ''}">
        </div>
      </div>

      <!-- Entra ID fields -->
      <div id="entra-fields" style="display:${isEntra ? 'contents' : 'none'}">
        <div class="section-divider">Entra ID (Azure AD)</div>
        <div class="form-group">
          <label class="form-label">Tenant ID</label>
          <input class="form-input" name="tenant_id" value="${env?.tenant_id || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">Client ID</label>
          <input class="form-input" name="client_id" value="${env?.client_id || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">Authority URL</label>
          <input class="form-input" name="authority" value="${env?.authority || ''}">
        </div>
        <div class="form-group">
          <label class="form-label">Graph Base URL</label>
          <input class="form-input" name="graph_base_url" value="${env?.graph_base_url || 'https://graph.microsoft.com/v1.0'}">
        </div>
        <div class="form-group span-2">
          <label class="form-label">Scopes (separados por coma)</label>
          <input class="form-input" name="scopes" value="${env?.scopes ? env.scopes.join(', ') : 'Group.ReadWrite.All'}">
        </div>
      </div>
    </form>`;
}

function refreshEnvFields(type) {
  const ldap  = document.getElementById('ldap-fields');
  const entra = document.getElementById('entra-fields');
  if (!ldap || !entra) return;
  ldap.style.display  = type === 'ENTRA' ? 'none' : 'contents';
  entra.style.display = type === 'ENTRA' ? 'contents' : 'none';
}

function openNewEnvModal() {
  const modal = document.getElementById('env-modal');
  document.getElementById('env-modal-title').textContent = 'Nuevo Environment';
  document.getElementById('env-modal-body').innerHTML = buildEnvModalContent();
  document.getElementById('env-modal-save').dataset.editing = '';
  document.getElementById('env-modal-save').onclick = saveEnv;
  modal.classList.add('open');
}

function openEditEnvModal(index) {
  const env = environments[index];
  const modal = document.getElementById('env-modal');
  document.getElementById('env-modal-title').textContent = 'Editar Environment';
  document.getElementById('env-modal-body').innerHTML = buildEnvModalContent(env);
  document.getElementById('env-modal-save').dataset.editing = env.name;
  document.getElementById('env-modal-save').onclick = saveEnv;
  modal.classList.add('open');
}

function closeEnvModal() {
  document.getElementById('env-modal').classList.remove('open');
}

async function saveEnv() {
  const form = document.getElementById('env-form');
  if (!form.checkValidity()) { form.reportValidity(); return; }

  const fd = new FormData(form);
  const envType = fd.get('env_type');
  const isEntra = envType === 'ENTRA';

  const payload = {
    name: fd.get('name'),
    env_type: envType,
    display_name: fd.get('display_name') || null,
    enabled: document.getElementById('env-enabled').checked,
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
    payload.use_ssl               = document.getElementById('env-ssl')?.checked ?? true;
    payload.group_name_is_alias   = document.getElementById('env-alias')?.checked ?? false;
    payload.secret_name           = fd.get('secret_name') || null;
  }

  const editingName = document.getElementById('env-modal-save').dataset.editing;

  try {
    if (editingName) {
      await API.updateEnvironment(editingName, payload);
      showToast('success', 'Environment actualizado', payload.name);
    } else {
      await API.createEnvironment(payload);
      showToast('success', 'Environment creado', payload.name);
    }
    closeEnvModal();
    await loadEnvironments();
  } catch (e) {
    showToast('error', 'Error al guardar', e.message);
  }
}

async function deleteEnv(name) {
  if (!confirm(`¿Eliminar el environment "${name}"? Esta acción puede romper sync pairs que lo referencien.`)) return;
  try {
    await API.deleteEnvironment(name);
    showToast('success', 'Environment eliminado', name);
    await loadEnvironments();
  } catch (e) {
    showToast('error', 'Error al eliminar', e.message);
  }
}
