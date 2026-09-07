/**
 * Toast notification system.
 */
function showToast(type, title, msg = '') {
  const container = document.getElementById('toast-container');
  const icons = { success: '✅', error: '❌', info: 'ℹ️' };

  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.innerHTML = `
    <span class="toast-icon">${icons[type] || 'ℹ️'}</span>
    <div class="toast-content">
      <div class="toast-title">${title}</div>
      ${msg ? `<div class="toast-msg">${msg}</div>` : ''}
    </div>`;

  container.appendChild(toast);

  setTimeout(() => {
    toast.classList.add('hiding');
    toast.addEventListener('animationend', () => toast.remove());
  }, 4200);
}

/**
 * Navigation system.
 */
function initNav() {
  document.querySelectorAll('.nav-item[data-section]').forEach(item => {
    item.addEventListener('click', () => {
      const target = item.dataset.section;

      document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
      document.querySelectorAll('.section').forEach(s => s.classList.remove('active'));

      item.classList.add('active');
      document.getElementById(`section-${target}`)?.classList.add('active');
    });
  });
}

/**
 * App bootstrap — load data into all sections.
 */
async function initApp() {
  initNav();

  // Load initial data
  try {
    await Promise.all([loadSyncPairs(), loadEnvironments()]);
  } catch (e) {
    showToast('error', 'Error al cargar datos', e.message);
  }
}

window.addEventListener('DOMContentLoaded', initApp);
