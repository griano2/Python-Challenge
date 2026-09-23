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
 * Authentication management.
 */
let currentUser = null;

function showLogin() {
  const loginScreen = document.getElementById('login-screen');
  const mainBody = document.querySelector('.main-body');
  const headerUser = document.getElementById('header-user');

  if (loginScreen) loginScreen.classList.remove('hidden');
  if (mainBody) mainBody.style.display = 'none';
  if (headerUser) headerUser.style.display = 'none';
}

function showApp(user) {
  currentUser = user;
  const loginScreen = document.getElementById('login-screen');
  const mainBody = document.querySelector('.main-body');
  const headerUser = document.getElementById('header-user');
  const userDisplayName = document.getElementById('user-display-name');

  if (loginScreen) loginScreen.classList.add('hidden');
  if (mainBody) mainBody.style.display = '';
  if (headerUser) headerUser.style.display = 'flex';
  if (userDisplayName && user) {
    userDisplayName.textContent = user.name || user.username || 'User';
    userDisplayName.title = user.username || '';
  }
}

async function loginWithMicrosoft() {
  const btn = document.getElementById('btn-ms-login');
  const textSpan = document.getElementById('btn-ms-text');
  const originalText = textSpan ? textSpan.textContent : 'Sign in with Microsoft';

  if (btn) btn.disabled = true;
  if (textSpan) textSpan.innerHTML = '<span class="spinner"></span> Waiting for authentication...';

  try {
    const res = await API.loginMicrosoft();
    if (res && res.status === 'success') {
      showToast('success', 'Signed in', `Welcome, ${res.user?.name || res.user?.username || ''}`);
      showApp(res.user);
      await Promise.all([loadSyncPairs(), loadDirectories()]);
    }
  } catch (e) {
    showToast('error', 'Sign-in error', e.message);
  } finally {
    if (btn) btn.disabled = false;
    if (textSpan) textSpan.textContent = originalText;
  }
}

async function logout() {
  try {
    await API.logout();
    showToast('info', 'Signed out', 'You have signed out of Microsoft');
  } catch (e) {
    showToast('error', 'Sign-out error', e.message);
  } finally {
    currentUser = null;
    showLogin();
  }
}

/**
 * App bootstrap — check auth and load data.
 */
async function initApp() {
  initNav();

  try {
    const auth = await API.getAuthStatus();
    if (auth && auth.authenticated) {
      showApp(auth.user);
      await Promise.all([loadSyncPairs(), loadDirectories()]);
    } else {
      showLogin();
    }
  } catch (e) {
    // Si falla el endpoint de auth, mostramos la pantalla de login por seguridad
    showLogin();
  }
}

window.addEventListener('DOMContentLoaded', initApp);
