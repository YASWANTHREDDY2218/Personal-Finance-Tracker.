/* ============================================================
   app.js  –  Personal Finance Tracker SPA
   Vanilla JS, no framework.
   ============================================================ */

'use strict';

// ============================================================
// STATE
// ============================================================
const STATE = {
  username: null,
  txns: [],
  txnSort: { by: 'date', dir: 'desc' },
  depositGoalIndex: null,  // 1-based goal number for deposit modal
};

// ============================================================
// API HELPER
// ============================================================
async function api(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
    credentials: 'same-origin',
  };
  if (body !== null) opts.body = JSON.stringify(body);
  const res = await fetch(path, opts);
  const json = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(json.error || 'Request failed');
  return json;
}

// ============================================================
// TOAST NOTIFICATIONS
// ============================================================
function toast(message, type = 'info') {
  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const el = document.createElement('div');
  el.className = `toast ${type}`;
  el.innerHTML = `<span class="toast-icon">${icons[type]}</span><span>${message}</span>`;
  document.getElementById('toast-container').appendChild(el);
  setTimeout(() => {
    el.classList.add('toast-out');
    el.addEventListener('animationend', () => el.remove());
  }, 3500);
}

// ============================================================
// CONFIRMATION DIALOG
// ============================================================
function confirmDialog(title, message, okLabel = 'Delete') {
  return new Promise(resolve => {
    const overlay = document.getElementById('confirm-overlay');
    document.getElementById('confirm-title').textContent = title;
    document.getElementById('confirm-message').textContent = message;
    document.getElementById('confirm-ok').textContent = okLabel;
    overlay.classList.remove('hidden');

    const cleanup = ok => {
      overlay.classList.add('hidden');
      resolve(ok);
    };
    document.getElementById('confirm-ok').onclick = () => cleanup(true);
    document.getElementById('confirm-cancel').onclick = () => cleanup(false);
  });
}

// ============================================================
// CURRENCY FORMAT
// ============================================================
const fmt = n => '₹' + Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const fmtDate = d => d ? new Date(d + 'T00:00:00').toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '';

// ============================================================
// AUTH: CHECK SESSION ON LOAD
// ============================================================
async function checkSession() {
  try {
    const data = await api('GET', '/api/auth/me');
    if (data.username) {
      STATE.username = data.username;
      showApp();
    } else {
      showAuth();
    }
  } catch (_) {
    showAuth();
  }
}

function showAuth() {
  document.getElementById('auth-screen').classList.remove('hidden');
  document.getElementById('app').classList.add('hidden');
}

function showApp() {
  document.getElementById('auth-screen').classList.add('hidden');
  document.getElementById('app').classList.remove('hidden');
  document.getElementById('sidebar-username').textContent = STATE.username;
  document.getElementById('mobile-user-name').textContent = STATE.username;
  document.getElementById('dashboard-date').textContent =
    new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' });
  navigate('dashboard');
}

// ============================================================
// AUTH TABS
// ============================================================
function switchAuthTab(tab) {
  document.getElementById('login-form').classList.toggle('hidden', tab !== 'login');
  document.getElementById('register-form').classList.toggle('hidden', tab !== 'register');
  document.getElementById('tab-login').classList.toggle('active', tab === 'login');
  document.getElementById('tab-register').classList.toggle('active', tab === 'register');
  document.getElementById('login-error').classList.add('hidden');
  document.getElementById('reg-error').classList.add('hidden');
}

async function handleLogin(e) {
  e.preventDefault();
  const errEl = document.getElementById('login-error');
  errEl.classList.add('hidden');

  // Simple inline loading toggle
  const btn = document.getElementById('login-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-spinner"></span>';

  try {
    const data = await api('POST', '/api/auth/login', {
      username: document.getElementById('login-username').value.trim(),
      password: document.getElementById('login-password').value,
    });
    STATE.username = data.username;
    toast(`Welcome back, ${data.username}!`, 'success');
    showApp();
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-text">Sign In</span>';
  }
}

async function handleRegister(e) {
  e.preventDefault();
  const errEl = document.getElementById('reg-error');
  errEl.classList.add('hidden');
  const btn = document.getElementById('reg-btn');
  btn.disabled = true;
  btn.innerHTML = '<span class="btn-spinner"></span>';

  try {
    await api('POST', '/api/auth/register', {
      username: document.getElementById('reg-username').value.trim(),
      password: document.getElementById('reg-password').value,
    });
    toast('Account created! Please log in.', 'success');
    document.getElementById('reg-username').value = '';
    document.getElementById('reg-password').value = '';
    switchAuthTab('login');
  } catch (err) {
    errEl.textContent = err.message;
    errEl.classList.remove('hidden');
  } finally {
    btn.disabled = false;
    btn.innerHTML = '<span class="btn-text">Create Account</span>';
  }
}

async function handleLogout() {
  await api('POST', '/api/auth/logout').catch(() => {});
  STATE.username = null;
  toast('Logged out.', 'info');
  showAuth();
}

// ============================================================
// ROUTER / NAV
// ============================================================
function navigate(page) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + page)?.classList.add('active');
  document.querySelector(`.nav-item[data-page="${page}"]`)?.classList.add('active');
  closeSidebar();

  switch (page) {
    case 'dashboard':    loadDashboard();    break;
    case 'transactions': loadTransactions(); break;
    case 'budgets':      loadBudgets();      break;
    case 'goals':        loadGoals();        break;
  }
  // prevent href scroll
  return false;
}

// ============================================================
// MOBILE SIDEBAR
// ============================================================
function toggleSidebar() {
  document.getElementById('sidebar').classList.toggle('open');
  document.getElementById('sidebar-overlay').classList.toggle('visible');
}
function closeSidebar() {
  document.getElementById('sidebar').classList.remove('open');
  document.getElementById('sidebar-overlay').classList.remove('visible');
}

// ============================================================
// CHART.JS INSTANCES (prevent duplicate canvas error)
// ============================================================
let monthlyChart = null;
let donutChart   = null;

// ============================================================
// DASHBOARD
// ============================================================
async function loadDashboard() {
  // Show skeleton placeholders
  ['card-income','card-expenses','card-balance','card-savings'].forEach(id => {
    document.getElementById(id)?.classList.add('skeleton');
  });

  try {
    const data = await api('GET', '/api/dashboard');

    // Remove skeletons
    ['card-income','card-expenses','card-balance','card-savings'].forEach(id => {
      document.getElementById(id)?.classList.remove('skeleton');
    });

    const t = data.totals;
    document.getElementById('val-income').textContent = fmt(t.income);
    document.getElementById('val-expenses').textContent = fmt(t.expenses);
    document.getElementById('val-balance').textContent = fmt(t.available_balance);
    document.getElementById('val-savings-rate').textContent = t.savings_rate + '%';

    // Color the balance red if negative
    const balEl = document.getElementById('val-balance');
    balEl.style.color = t.available_balance < 0 ? 'var(--expense-clr)' : '';

    renderMonthlyChart(data.monthly_report);
    renderDonutChart(data.category_spending);
    renderInsights(data.insights);

  } catch (err) {
    toast('Failed to load dashboard: ' + err.message, 'error');
  }
}

function renderMonthlyChart(report) {
  const ctx = document.getElementById('chart-monthly').getContext('2d');
  if (monthlyChart) monthlyChart.destroy();

  const labels = report.map(r => r.month);
  const incomes   = report.map(r => r.income);
  const expenses  = report.map(r => r.expenses);

  monthlyChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [
        {
          label: 'Income',
          data: incomes,
          backgroundColor: 'rgba(0,212,180,0.7)',
          borderColor: '#00d4b4',
          borderWidth: 1,
          borderRadius: 6,
        },
        {
          label: 'Expenses',
          data: expenses,
          backgroundColor: 'rgba(255,107,138,0.7)',
          borderColor: '#ff6b8a',
          borderWidth: 1,
          borderRadius: 6,
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#8892b0', font: { family: 'Inter' } } },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.dataset.label}: ₹${ctx.parsed.y.toLocaleString('en-IN')}`
          }
        }
      },
      scales: {
        x: { ticks: { color: '#8892b0' }, grid: { color: 'rgba(255,255,255,0.04)' } },
        y: {
          ticks: {
            color: '#8892b0',
            callback: v => '₹' + (v >= 1000 ? (v/1000)+'k' : v)
          },
          grid: { color: 'rgba(255,255,255,0.04)' }
        }
      }
    }
  });
}

function renderDonutChart(catSpending) {
  const ctx = document.getElementById('chart-donut').getContext('2d');
  if (donutChart) donutChart.destroy();

  const emptyEl = document.getElementById('donut-empty');
  if (!catSpending || catSpending.length === 0) {
    emptyEl.classList.remove('hidden');
    document.getElementById('chart-donut').style.display = 'none';
    return;
  }
  emptyEl.classList.add('hidden');
  document.getElementById('chart-donut').style.display = '';

  const palette = ['#7c5cfc','#00d4b4','#ff6b8a','#ffc94a','#3b82f6','#a78bfa','#34d399','#f87171'];

  donutChart = new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels: catSpending.map(c => c.category),
      datasets: [{
        data: catSpending.map(c => c.amount),
        backgroundColor: catSpending.map((_, i) => palette[i % palette.length]),
        borderColor: 'transparent',
        hoverOffset: 12,
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: '68%',
      plugins: {
        legend: {
          position: 'right',
          labels: {
            color: '#8892b0', font: { family: 'Inter', size: 11 },
            boxWidth: 12, padding: 12,
          }
        },
        tooltip: {
          callbacks: {
            label: ctx => ` ₹${ctx.parsed.toLocaleString('en-IN')}`
          }
        }
      }
    }
  });
}

function renderInsights(insights) {
  const el = document.getElementById('insights-list');
  if (!insights || insights.length === 0) {
    el.innerHTML = '<div class="insight-item info">📊 Add transactions to get personalized insights.</div>';
    return;
  }
  el.innerHTML = insights.map(i => `
    <div class="insight-item ${i.type}">
      ${{ success:'✅', warning:'⚠️', danger:'🚨', info:'💡' }[i.type] || 'ℹ️'}
      ${i.text}
    </div>`).join('');
}

// ============================================================
// TRANSACTIONS
// ============================================================
function toggleAddTxnForm() {
  const f = document.getElementById('add-txn-form');
  f.classList.toggle('hidden');
  if (!f.classList.contains('hidden')) {
    // set today's date by default
    document.getElementById('txn-date').value = new Date().toISOString().split('T')[0];
    document.getElementById('txn-amount').focus();
  }
}

async function loadTransactions(filters = {}) {
  try {
    const params = new URLSearchParams();
    if (filters.search) params.set('search', filters.search);
    if (filters.type)   params.set('type', filters.type);
    if (filters.from)   params.set('date_from', filters.from);
    if (filters.to)     params.set('date_to', filters.to);
    params.set('sort', STATE.txnSort.by);
    params.set('order', STATE.txnSort.dir);

    const data = await api('GET', '/api/transactions?' + params.toString());
    STATE.txns = data.transactions;
    renderTransactions(STATE.txns);
  } catch (err) {
    toast('Failed to load transactions: ' + err.message, 'error');
  }
}

function renderTransactions(rows) {
  const tbody   = document.getElementById('txn-tbody');
  const emptyEl = document.getElementById('txn-empty');

  if (!rows || rows.length === 0) {
    tbody.innerHTML = '';
    emptyEl.classList.remove('hidden');
    return;
  }
  emptyEl.classList.add('hidden');
  tbody.innerHTML = rows.map(r => `
    <tr>
      <td>${fmtDate(r.date)}</td>
      <td><span class="badge badge-${r.type}">${r.type}</span></td>
      <td>${r.category}</td>
      <td title="${r.description}">${r.description.length > 30 ? r.description.slice(0,30)+'…' : r.description}</td>
      <td class="amt-${r.type}">${fmt(r.amount)}</td>
      <td>
        <button class="btn-icon danger" onclick="deleteTxn('${r.id}')" title="Delete transaction">🗑</button>
      </td>
    </tr>`).join('');
}

function applyTxnFilters() {
  loadTransactions({
    search: document.getElementById('txn-search').value.trim(),
    type:   document.getElementById('txn-filter-type').value,
    from:   document.getElementById('txn-filter-from').value,
    to:     document.getElementById('txn-filter-to').value,
  });
}

function clearTxnFilters() {
  document.getElementById('txn-search').value = '';
  document.getElementById('txn-filter-type').value = '';
  document.getElementById('txn-filter-from').value = '';
  document.getElementById('txn-filter-to').value = '';
  loadTransactions();
}

function sortTxns(field) {
  if (STATE.txnSort.by === field) {
    STATE.txnSort.dir = STATE.txnSort.dir === 'asc' ? 'desc' : 'asc';
  } else {
    STATE.txnSort.by  = field;
    STATE.txnSort.dir = 'desc';
  }
  const arrow = STATE.txnSort.dir === 'asc' ? '↑' : '↓';
  document.getElementById('sort-date-icon').textContent   = field === 'date'   ? arrow : '↕';
  document.getElementById('sort-amount-icon').textContent = field === 'amount' ? arrow : '↕';
  applyTxnFilters();
}

async function submitTransaction(e) {
  e.preventDefault();
  try {
    await api('POST', '/api/transactions', {
      type:        document.getElementById('txn-type').value,
      amount:      document.getElementById('txn-amount').value,
      category:    document.getElementById('txn-category').value.trim(),
      description: document.getElementById('txn-desc').value.trim(),
      date:        document.getElementById('txn-date').value,
    });
    toast('Transaction added!', 'success');
    e.target.reset();
    toggleAddTxnForm();
    loadTransactions();
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function deleteTxn(id) {
  const ok = await confirmDialog('Delete Transaction', 'Are you sure you want to delete this transaction? This cannot be undone.');
  if (!ok) return;
  try {
    await api('DELETE', '/api/transactions/' + id);
    toast('Transaction deleted.', 'info');
    loadTransactions();
  } catch (err) {
    toast(err.message, 'error');
  }
}

function exportTransactions() {
  window.location.href = '/api/transactions/export';
  toast('Downloading CSV…', 'info');
}

// ============================================================
// BUDGETS
// ============================================================
function toggleAddBudgetForm() {
  const f = document.getElementById('add-budget-form');
  f.classList.toggle('hidden');
  if (!f.classList.contains('hidden')) document.getElementById('budget-category').focus();
}

async function loadBudgets() {
  try {
    const data = await api('GET', '/api/budgets');
    renderBudgets(data.budgets);
  } catch (err) {
    toast('Failed to load budgets: ' + err.message, 'error');
  }
}

function renderBudgets(budgets) {
  const grid    = document.getElementById('budgets-grid');
  const emptyEl = document.getElementById('budgets-empty');

  if (!budgets || budgets.length === 0) {
    grid.innerHTML = '';
    emptyEl.classList.remove('hidden');
    return;
  }
  emptyEl.classList.add('hidden');

  grid.innerHTML = budgets.map(b => {
    const pct     = b.budget > 0 ? Math.min(100, (b.spent / b.budget) * 100) : 0;
    const isWarn  = pct >= 80 && !b.exceeded;
    const isDanger= b.exceeded;
    const fillCls = isDanger ? 'danger' : isWarn ? 'warn' : '';
    const statusCls  = isDanger ? 'status-danger' : isWarn ? 'status-warn' : 'status-ok';
    const statusText = isDanger ? '⛔ Exceeded' : isWarn ? '⚠️ Nearly Full' : '✅ On Track';

    return `
    <div class="budget-card">
      <div class="budget-header">
        <div class="budget-name">${b.name}</div>
        <div style="display:flex;gap:6px;align-items:center">
          <span class="budget-status-badge ${statusCls}">${statusText}</span>
          <button class="btn-icon danger" onclick="deleteBudget('${encodeURIComponent(b.name)}')" title="Delete budget">🗑</button>
        </div>
      </div>
      <div class="budget-amounts">
        <span>Spent: <span class="budget-spent-val" style="color:${isDanger?'var(--expense-clr)':isWarn?'var(--warning)':'var(--teal)'};">${fmt(b.spent)}</span></span>
        <span>Limit: ${fmt(b.budget)}</span>
      </div>
      <div class="progress-track">
        <div class="progress-fill ${fillCls}" style="width:${pct.toFixed(1)}%"></div>
      </div>
      <div style="font-size:0.78rem;color:var(--text-secondary)">
        ${isDanger ? `Over by ${fmt(Math.abs(b.remaining))}` : `${fmt(b.remaining)} remaining`}
        &nbsp;·&nbsp; ${pct.toFixed(0)}% used
      </div>
    </div>`;
  }).join('');
}

async function submitBudget(e) {
  e.preventDefault();
  try {
    await api('POST', '/api/budgets', {
      category: document.getElementById('budget-category').value.trim(),
      amount:   document.getElementById('budget-amount').value,
    });
    toast('Budget saved!', 'success');
    e.target.reset();
    toggleAddBudgetForm();
    loadBudgets();
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function deleteBudget(category) {
  const ok = await confirmDialog('Delete Budget', `Delete the budget for "${decodeURIComponent(category)}"?`);
  if (!ok) return;
  try {
    await api('DELETE', '/api/budgets/' + category);
    toast('Budget deleted.', 'info');
    loadBudgets();
  } catch (err) {
    toast(err.message, 'error');
  }
}

// ============================================================
// SAVINGS GOALS
// ============================================================
function toggleAddGoalForm() {
  const f = document.getElementById('add-goal-form');
  f.classList.toggle('hidden');
  if (!f.classList.contains('hidden')) document.getElementById('goal-name').focus();
}

async function loadGoals() {
  try {
    const data = await api('GET', '/api/goals');
    renderGoals(data.goals);
  } catch (err) {
    toast('Failed to load goals: ' + err.message, 'error');
  }
}

function buildRingSVG(pct) {
  const R = 54, CX = 60, CY = 60;
  const circumference = 2 * Math.PI * R;
  const offset = circumference - (pct / 100) * circumference;
  return `
    <svg class="ring-svg" width="120" height="120" viewBox="0 0 120 120">
      <defs>
        <linearGradient id="ring-gradient" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stop-color="#7c5cfc"/>
          <stop offset="100%" stop-color="#00d4b4"/>
        </linearGradient>
      </defs>
      <circle class="ring-bg" cx="${CX}" cy="${CY}" r="${R}" stroke-width="10"/>
      <circle class="ring-fill" cx="${CX}" cy="${CY}" r="${R}"
        stroke-width="10"
        stroke-dasharray="${circumference}"
        stroke-dashoffset="${offset}"
      />
    </svg>`;
}

function renderGoals(goals) {
  const grid    = document.getElementById('goals-grid');
  const emptyEl = document.getElementById('goals-empty');

  if (!goals || goals.length === 0) {
    grid.innerHTML = '';
    emptyEl.classList.remove('hidden');
    return;
  }
  emptyEl.classList.add('hidden');

  grid.innerHTML = goals.map((g, i) => {
    const pct = Math.min(100, g.progress_pct);
    const complete = pct >= 100;
    return `
    <div class="goal-card">
      <div class="goal-header">
        <div class="goal-name">${g.name} ${complete ? '🎉' : ''}</div>
        <div class="goal-actions">
          <button class="btn-icon" onclick="openDepositModal(${i+1},'${g.name.replace(/'/g,"\\'")}',${g.remaining})" title="Add savings" ${complete?'disabled':''}>➕</button>
          <button class="btn-icon danger" onclick="deleteGoal(${i+1},'${g.name.replace(/'/g,"\\'")}') " title="Delete goal">🗑</button>
        </div>
      </div>
      <div class="ring-wrap">
        ${buildRingSVG(pct)}
        <div class="ring-pct">${pct.toFixed(0)}%</div>
      </div>
      <div class="goal-stats">
        <div>
          <div class="goal-stat-label">Saved</div>
          <div class="goal-stat-val" style="color:var(--teal)">${fmt(g.saved)}</div>
        </div>
        <div>
          <div class="goal-stat-label">Target</div>
          <div class="goal-stat-val">${fmt(g.target)}</div>
        </div>
        <div>
          <div class="goal-stat-label">Remaining</div>
          <div class="goal-stat-val" style="color:var(--expense-clr)">${fmt(g.remaining)}</div>
        </div>
        <div>
          <div class="goal-stat-label">Status</div>
          <div class="goal-stat-val" style="font-size:0.8rem">${complete ? '✅ Complete' : '🏃 In Progress'}</div>
        </div>
      </div>
    </div>`;
  }).join('');
}

async function submitGoal(e) {
  e.preventDefault();
  try {
    await api('POST', '/api/goals', {
      name:   document.getElementById('goal-name').value.trim(),
      target: document.getElementById('goal-target').value,
    });
    toast('Savings goal created!', 'success');
    e.target.reset();
    toggleAddGoalForm();
    loadGoals();
  } catch (err) {
    toast(err.message, 'error');
  }
}

async function deleteGoal(n, name) {
  const ok = await confirmDialog('Delete Savings Goal', `Delete the goal "${name}"? All saved progress will be removed.`);
  if (!ok) return;
  try {
    await api('DELETE', '/api/goals/' + n);
    toast('Goal deleted.', 'info');
    loadGoals();
  } catch (err) {
    toast(err.message, 'error');
  }
}

// Deposit modal
function openDepositModal(goalN, name, remaining) {
  STATE.depositGoalIndex = goalN;
  document.getElementById('deposit-goal-name').textContent = `Goal: ${name} · Remaining: ${fmt(remaining)}`;
  document.getElementById('deposit-amount').value = '';
  document.getElementById('deposit-date').value = new Date().toISOString().split('T')[0];
  document.getElementById('deposit-modal').classList.remove('hidden');
  setTimeout(() => document.getElementById('deposit-amount').focus(), 100);
}

function closeDepositModal() {
  document.getElementById('deposit-modal').classList.add('hidden');
  STATE.depositGoalIndex = null;
}

async function submitDeposit(e) {
  e.preventDefault();
  try {
    await api('POST', `/api/goals/${STATE.depositGoalIndex}/add`, {
      amount: document.getElementById('deposit-amount').value,
      date:   document.getElementById('deposit-date').value,
    });
    toast('Savings added!', 'success');
    closeDepositModal();
    loadGoals();
  } catch (err) {
    toast(err.message, 'error');
  }
}

// ============================================================
// INIT
// ============================================================
document.addEventListener('DOMContentLoaded', () => {
  // Close deposit modal on overlay click
  document.getElementById('deposit-modal').addEventListener('click', e => {
    if (e.target === e.currentTarget) closeDepositModal();
  });

  // Keyboard shortcuts
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeDepositModal();
      document.getElementById('confirm-overlay').classList.add('hidden');
      closeSidebar();
    }
  });

  checkSession();
});
