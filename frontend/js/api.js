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
  // ── Directories ─────────────────────────────────────────────────────────
  getDirectories:       () => apiFetch('/api/directories'),
  createDirectory: (payload) => apiFetch('/api/directories', { method: 'POST', body: JSON.stringify(payload) }),
  updateDirectory: (name, payload) => apiFetch(`/api/directories/${encodeURIComponent(name)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteDirectory: (name) => apiFetch(`/api/directories/${encodeURIComponent(name)}`, { method: 'DELETE' }),

  // ── Sync Pairs ──────────────────────────────────────────────────────────
  getSyncPairs:          () => apiFetch('/api/sync-pairs'),
  createSyncPair:   (payload) => apiFetch('/api/sync-pairs', { method: 'POST', body: JSON.stringify(payload) }),
  updateSyncPair:   (name, payload) => apiFetch(`/api/sync-pairs/${encodeURIComponent(name)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteSyncPair:   (name) => apiFetch(`/api/sync-pairs/${encodeURIComponent(name)}`, { method: 'DELETE' }),
  runSyncPair:      (name) => apiFetch(`/api/sync-pairs/${encodeURIComponent(name)}/run`, { method: 'POST' }),
  runAllEnabled:         () => apiFetch('/api/sync-pairs/run-enabled', { method: 'POST' }),
};
