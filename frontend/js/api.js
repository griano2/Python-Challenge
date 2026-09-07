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
  // ── Environments ────────────────────────────────────────────────────────
  getEnvironments:       () => apiFetch('/api/environments'),
  createEnvironment: (payload) => apiFetch('/api/environments', { method: 'POST', body: JSON.stringify(payload) }),
  updateEnvironment: (name, payload) => apiFetch(`/api/environments/${encodeURIComponent(name)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteEnvironment: (name) => apiFetch(`/api/environments/${encodeURIComponent(name)}`, { method: 'DELETE' }),

  // ── Sync Pairs ──────────────────────────────────────────────────────────
  getSyncPairs:          () => apiFetch('/api/sync-pairs'),
  createSyncPair:   (payload) => apiFetch('/api/sync-pairs', { method: 'POST', body: JSON.stringify(payload) }),
  updateSyncPair:   (name, payload) => apiFetch(`/api/sync-pairs/${encodeURIComponent(name)}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteSyncPair:   (name) => apiFetch(`/api/sync-pairs/${encodeURIComponent(name)}`, { method: 'DELETE' }),
  runSyncPair:      (name) => apiFetch(`/api/sync-pairs/${encodeURIComponent(name)}/run`, { method: 'POST' }),
  runAllEnabled:         () => apiFetch('/api/sync-pairs/run-enabled', { method: 'POST' }),
};
