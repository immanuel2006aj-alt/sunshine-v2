// HARDCODED – API_BASE points to your live Render backend
const API_BASE = "https://sunshine-v2.onrender.com";
const SUPPORT_USERNAME = "Imgraceladie";
const GROUP_INVITE = "https://t.me/+Xz1vJc0kzKs1M2Nl";
const FRONTEND_URL = "https://sunshine-work-from-home.site.je";

function getUserId() { return localStorage.getItem('userId'); }

// Signup
document.getElementById('signupForm')?.addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('signupUsername').value;
  const password = document.getElementById('signupPassword').value;
  const upi = document.getElementById('signupUpi').value;
  const usdt = document.getElementById('signupUsdt').value;
  try {
    console.log("Sending signup request to:", `${API_BASE}/signup`);
    const res = await fetch(`${API_BASE}/signup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password, upi, usdt })
    });
    if (!res.ok) {
      const errorText = await res.text();
      console.error("Signup HTTP error:", res.status, errorText);
      alert('Signup failed: ' + res.status + ' ' + errorText);
      return;
    }
    const data = await res.json();
    if (data.user_id) {
      localStorage.setItem('userId', data.user_id);
      window.location.href = '/dashboard.html';
    } else {
      alert('Signup failed: ' + (data.detail || data.error || 'unknown error'));
    }
  } catch (err) {
    console.error("Signup network error:", err);
    alert('Network error: ' + err.message);
  }
});

// Dashboard logic
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
      document.getElementById('userIdDisplay').textContent = data.user_id;
      document.getElementById('usernameDisplay').textContent = data.username;
      document.getElementById('balanceDisplay').textContent = '₹' + data.balance;
      document.getElementById('dayDisplay').textContent = data.days + ' / 21';
      document.getElementById('statusDisplay').textContent = data.status;
      document.getElementById('withdrawBalance').textContent = '₹' + data.balance;
      const dailyCount = data.daily_captcha_count || 0;
      const quota = 262;
      document.getElementById('dailyCountDisplay').textContent = dailyCount + ' / ' + quota;
      const percent = Math.min((dailyCount / quota) * 100, 100);
      document.getElementById('progressBar').style.width = percent + '%';
      
      const withdrawBtn = document.getElementById('withdrawBtn');
      if (data.days >= 21) {
        withdrawBtn.disabled = false;
        withdrawBtn.title = '';
      } else {
        withdrawBtn.disabled = true;
        withdrawBtn.title = 'Withdraw available after 21 days';
      }
      
      generateCaptcha();
      document.getElementById('groupJoinLink').href = GROUP_INVITE;
      document.getElementById('contactDeepLink').href = `tg://resolve?domain=${SUPPORT_USERNAME}`;
    } catch (err) {
      console.error("Dashboard load error:", err);
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
    document.getElementById('captchaText').dataset.captcha = code;
    document.getElementById('captchaInput').value = '';
    document.getElementById('captchaFeedback').textContent = '';
  }

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
      console.error("Captcha solve error:", err);
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
    navigator.clipboard.writeText(id).then(() => {
      alert('User ID copied!');
    }).catch(() => {
      const textArea = document.createElement('textarea');
      textArea.value = id;
      document.body.appendChild(textArea);
      textArea.select();
      document.execCommand('copy');
      document.body.removeChild(textArea);
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
      console.error("Withdraw error:", err);
      alert('Network error: ' + err.message);
    }
  });
}