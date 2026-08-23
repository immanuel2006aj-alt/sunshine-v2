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

// Dashboard logic (unchanged)
// ... rest of dashboard code from earlier