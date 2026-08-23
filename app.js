// API base – change to your Render backend URL if needed
const API_BASE = "https://sunshine-v2.onrender.com";
const SUPPORT_USERNAME = "Imgraceladie";

function getUserId() { return localStorage.getItem('userId'); }

// ---- Toggle between Signup and Login ----
const signupSection = document.getElementById('signupSection');
const loginSection = document.getElementById('loginSection');
const switchToLogin = document.getElementById('switchToLogin');
const switchToSignup = document.getElementById('switchToSignup');
const toggleAuthBtn = document.getElementById('toggleAuthBtn');

function showSignup() {
  signupSection?.classList.remove('hidden');
  loginSection?.classList.add('hidden');
  if (toggleAuthBtn) toggleAuthBtn.textContent = 'Login';
}
function showLogin() {
  signupSection?.classList.add('hidden');
  loginSection?.classList.remove('hidden');
  if (toggleAuthBtn) toggleAuthBtn.textContent = 'Sign Up';
}

switchToLogin?.addEventListener('click', showLogin);
switchToSignup?.addEventListener('click', showSignup);
toggleAuthBtn?.addEventListener('click', () => {
  if (signupSection?.classList.contains('hidden')) showSignup();
  else showLogin();
});

// ---- Signup ----
document.getElementById('signupForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('signupUsername').value.trim();
  const password = document.getElementById('signupPassword').value;
  const upi = document.getElementById('signupUpi').value.trim();
  const email = document.getElementById('signupEmail').value.trim();
  const usdt = document.getElementById('signupUsdt').value.trim() || '';

  if (!username || !password || !upi || !email) {
    alert('All fields marked * are required.');
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, upi, email, usdt })
    });
    if (!res.ok) {
      const err = await res.text();
      alert('Signup failed: ' + err);
      return;
    }
    const data = await res.json();
    if (data.user_id) {
      localStorage.setItem('userId', data.user_id);
      window.location.href = '/dashboard.html';
    } else {
      alert('Signup failed: ' + (data.detail || 'unknown error'));
    }
  } catch (err) {
    alert('Network error: ' + err.message);
  }
});

// ---- Login ----
document.getElementById('loginForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('loginUsername').value.trim();
  const password = document.getElementById('loginPassword').value;
  if (!username || !password) {
    alert('Please enter username and password.');
    return;
  }
  try {
    const res = await fetch(`${API_BASE}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    if (!res.ok) {
      const err = await res.text();
      alert('Login failed: ' + err);
      return;
    }
    const data = await res.json();
    if (data.user_id) {
      localStorage.setItem('userId', data.user_id);
      window.location.href = '/dashboard.html';
    } else {
      alert('Login failed: ' + (data.detail || 'unknown error'));
    }
  } catch (err) {
    alert('Network error: ' + err.message);
  }
});

// ---- Dashboard ----
if (window.location.pathname.includes('dashboard.html')) {
  const userId = getUserId();
  if (!userId) { window.location.href = '/'; }

  async function loadDashboard() {
    try {
      const res = await fetch(`${API_BASE}/dashboard/${userId}`);
      if (!res.ok) {
        if (res.status === 404) { 
          localStorage.removeItem('userId');
          window.location.href = '/';
          return;
        }
        throw new Error('Failed to load dashboard: ' + res.status);
      }
      const data = await res.json();

      // --- BAN CHECK ---
      if (data.status === 'Banned') {
        document.getElementById('statusDisplay').textContent = 'Banned';
        document.getElementById('statusDisplay').className = 'text-lg font-medium text-red-600';
        document.getElementById('captchaInput').disabled = true;
        document.getElementById('solveCaptchaBtn').disabled = true;
        document.getElementById('captchaInput').placeholder = 'Account suspended';
        document.getElementById('captchaFeedback').textContent = 'Your account has been suspended. Contact support.';
        document.getElementById('withdrawBtn').disabled = true;
        document.getElementById('withdrawBtn').classList.add('opacity-50', 'cursor-not-allowed');
        document.getElementById('userIdDisplay').textContent = data.user_id;
        document.getElementById('usernameDisplay').textContent = data.username;
        document.getElementById('balanceDisplay').textContent = '₹' + data.balance;
        document.getElementById('dayDisplay').textContent = data.days + ' / 21';
        document.getElementById('withdrawBalance').textContent = '₹' + data.balance;
        document.getElementById('dailyCountDisplay').textContent = '—';
        document.getElementById('progressBar').style.width = '0%';
        document.getElementById('contactDeepLink').href = `tg://resolve?domain=${SUPPORT_USERNAME}`;
        return;
      }

      // Normal display
      document.getElementById('userIdDisplay').textContent = data.user_id;
      document.getElementById('usernameDisplay').textContent = data.username;
      document.getElementById('balanceDisplay').textContent = '₹' + data.balance;
      document.getElementById('dayDisplay').textContent = data.days + ' / 21';
      document.getElementById('statusDisplay').textContent = data.status;
      document.getElementById('statusDisplay').className = 'text-lg font-medium text-green-600';
      document.getElementById('withdrawBalance').textContent = '₹' + data.balance;
      const dailyCount = data.daily_captcha_count || 0;
      const quota = 262;
      document.getElementById('dailyCountDisplay').textContent = dailyCount + ' / ' + quota;
      const percent = Math.min((dailyCount / quota) * 100, 100);
      document.getElementById('progressBar').style.width = percent + '%';

      const withdrawBtn = document.getElementById('withdrawBtn');
      if (data.days >= 21) {
        withdrawBtn.disabled = false;
        withdrawBtn.classList.remove('opacity-50', 'cursor-not-allowed');
      } else {
        withdrawBtn.disabled = true;
        withdrawBtn.classList.add('opacity-50', 'cursor-not-allowed');
      }

      // Re-enable captcha inputs (in case previously banned)
      document.getElementById('captchaInput').disabled = false;
      document.getElementById('solveCaptchaBtn').disabled = false;
      document.getElementById('captchaInput').placeholder = 'Type the code';
      document.getElementById('captchaFeedback').textContent = '';

      generateCaptcha();
      document.getElementById('contactDeepLink').href = `tg://resolve?domain=${SUPPORT_USERNAME}`;
    } catch (err) {
      alert('Failed to load dashboard: ' + err.message);
    }
  }

  function generateCaptcha() {
    const chars = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789';
    let code = '';
    for (let i = 0; i < 5; i++) {
      code += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    document.getElementById('captchaText').textContent = code;
    document.getElementById('captchaInput').value = '';
    document.getElementById('captchaFeedback').textContent = '';
  }

  // Solve captcha
  document.getElementById('solveCaptchaBtn')?.addEventListener('click', async () => {
    const input = document.getElementById('captchaInput').value.trim();
    if (!input) {
      document.getElementById('captchaFeedback').textContent = 'Please type the code.';
      return;
    }
    try {
      const res = await fetch(`${API_BASE}/solve_captcha`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      });
      if (!res.ok) {
        const errText = await res.text();
        document.getElementById('captchaFeedback').textContent = 'Error: ' + errText;
        return;
      }
      const data = await res.json();
      if (data.success) {
        document.getElementById('captchaFeedback').textContent = 'Verified! +₹1 added.';
        setTimeout(loadDashboard, 500);
      } else {
        document.getElementById('captchaFeedback').textContent = data.detail || 'Error, try again.';
      }
    } catch (err) {
      document.getElementById('captchaFeedback').textContent = 'Network error.';
    }
  });

  document.getElementById('captchaInput')?.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') document.getElementById('solveCaptchaBtn').click();
  });

  // Initial load
  loadDashboard();

  // Copy ID
  document.getElementById('copyIdBtn')?.addEventListener('click', () => {
    const id = document.getElementById('userIdDisplay').textContent;
    navigator.clipboard.writeText(id).then(() => alert('User ID copied!'))
      .catch(() => {
        const ta = document.createElement('textarea');
        ta.value = id;
        document.body.appendChild(ta);
        ta.select();
        document.execCommand('copy');
        document.body.removeChild(ta);
        alert('User ID copied!');
      });
  });

  // Logout
  document.getElementById('logoutBtn')?.addEventListener('click', () => {
    localStorage.removeItem('userId');
    window.location.href = '/';
  });

  // Contact modal
  document.getElementById('contactBtn')?.addEventListener('click', () => {
    document.getElementById('contactModal').classList.remove('hidden');
  });
  document.getElementById('closeContactModal')?.addEventListener('click', () => {
    document.getElementById('contactModal').classList.add('hidden');
  });

  // Withdraw modal
  document.getElementById('withdrawBtn')?.addEventListener('click', () => {
    if (document.getElementById('withdrawBtn').disabled) {
      alert('Withdrawals only after 21 days.');
      return;
    }
    document.getElementById('withdrawModal').classList.remove('hidden');
  });
  document.getElementById('closeWithdrawModal')?.addEventListener('click', () => {
    document.getElementById('withdrawModal').classList.add('hidden');
  });
  document.getElementById('submitWithdrawBtn')?.addEventListener('click', async () => {
    const userId = getUserId();
    try {
      const res = await fetch(`${API_BASE}/withdraw`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ user_id: userId })
      });
      if (res.ok) {
        alert('Withdrawal request submitted!');
        document.getElementById('withdrawModal').classList.add('hidden');
      } else {
        const err = await res.json();
        alert('Withdrawal failed: ' + (err.detail || 'unknown error'));
      }
    } catch (err) {
      alert('Network error: ' + err.message);
    }
  });
}
