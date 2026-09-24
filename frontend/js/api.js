/**
 * api.js — Thin fetch wrapper for the FastAPI backend.
 */

const BASE = '';

async function apiFetch(path, options = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json', ...options.headers },
    ...options,
  });

  if (res.status === 204) return null;

  const data = await res.json().catch(() => null);

  if (!res.ok) {
    const msg = data?.detail || `HTTP ${res.status}`;
    throw new Error(msg);
  }

  return data;
}

const API = {
  // ── Authentication ──────────────────────────────────────────────────────
  getAuthStatus:        () => apiFetch('/api/auth/status'),
  loginMicrosoft:       () => apiFetch('/api/auth/login', { method: 'POST' }),
  logout:               () => apiFetch('/api/auth/logout', { method: 'POST' }),

  // ── Directories ─────────────────────────────────────────────────────────
  getDirectories:       () => apiFetch('/api/directories'),
  createDirectory: (payload) => apiFetch('/api/directories', { method: 'POST', body: JSON.stringify(payload) }),
  updateDirectory: (name, payload) => apiFetch(`/api/directories/${encodeURIComponent(name)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteDirectory: (name) => apiFetch(`/api/directories/${encodeURIComponent(name)}`, { method: 'DELETE' }),

  // ── Sync Configs ────────────────────────────────────────────────────────
  getSyncConfigs:          () => apiFetch('/api/sync-configs'),
  createSyncConfig:   (payload) => apiFetch('/api/sync-configs', { method: 'POST', body: JSON.stringify(payload) }),
  updateSyncConfig:   (name, payload) => apiFetch(`/api/sync-configs/${encodeURIComponent(name)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteSyncConfig:   (name) => apiFetch(`/api/sync-configs/${encodeURIComponent(name)}`, { method: 'DELETE' }),
  runSyncConfig:      (name) => apiFetch(`/api/sync-configs/${encodeURIComponent(name)}/run`, { method: 'POST' }),
  runAllEnabledConfigs:    () => apiFetch('/api/sync-configs/run-enabled', { method: 'POST' }),
};
