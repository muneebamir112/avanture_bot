import os
import sqlite3
import hashlib
import binascii
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any
from pydantic import BaseModel

from fastapi import FastAPI, Request, HTTPException, Depends, status, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "auth_cloud.db"

app = FastAPI(title="Avanture Central Authentication & Access Control Server", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# Database Management
# -------------------------------------------------------------
def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
    if not salt:
        salt = binascii.hexlify(os.urandom(16)).decode("utf-8")
    dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
    password_hash = binascii.hexlify(dk).decode("utf-8")
    return password_hash, salt

def init_db():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('SUPER_ADMIN', 'ADMIN')),
                status TEXT NOT NULL DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'REVOKED')),
                created_at DATETIME NOT NULL,
                last_login DATETIME,
                created_by TEXT
            )
        """)
        conn.commit()

        # Seed default Super Admin
        cursor.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'SUPER_ADMIN'")
        if cursor.fetchone()["count"] == 0:
            p_hash, salt = hash_password("admin123")
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("""
                INSERT INTO users (username, password_hash, salt, role, status, created_at, created_by)
                VALUES (?, ?, ?, 'SUPER_ADMIN', 'ACTIVE', ?, 'SYSTEM')
            """, ("superadmin", p_hash, salt, now))
            conn.commit()

init_db()

# -------------------------------------------------------------
# Request Schemas
# -------------------------------------------------------------
class ClientLoginRequest(BaseModel):
    username: str
    password: str

class CreateAdminRequest(BaseModel):
    username: str
    password: str

class StatusUpdateRequest(BaseModel):
    status: str  # ACTIVE or REVOKED

class PasswordUpdateRequest(BaseModel):
    password: str

class ChangeSuperAdminPasswordRequest(BaseModel):
    current_password: str
    new_password: str

# -------------------------------------------------------------
# Web HTML Templates
# -------------------------------------------------------------
LOGIN_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Avanture — Super Admin Access</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>body { font-family: 'Plus Jakarta Sans', sans-serif; }</style>
</head>
<body class="bg-[#0b0f19] text-slate-100 min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-md bg-[#111827] border border-slate-800 rounded-2xl shadow-2xl p-8">
        <div class="text-center mb-8">
            <div class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-indigo-950/80 border border-indigo-700/50 text-indigo-400 text-2xl mb-4 shadow-inner">
                ⚡
            </div>
            <h1 class="text-2xl font-bold tracking-tight text-white">Avanture Control Hub</h1>
            <p class="text-sm text-slate-400 mt-1">Super Admin Central Authentication</p>
        </div>

        <div id="errorAlert" class="hidden mb-6 p-3.5 rounded-xl bg-rose-950/50 border border-rose-800/60 text-rose-300 text-sm"></div>

        <form id="loginForm" onsubmit="handleLogin(event)" class="space-y-5">
            <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">Master Username</label>
                <input type="text" id="username" required placeholder="superadmin"
                    class="w-full px-4 py-3 rounded-xl bg-[#0b0f19] border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none text-white text-sm transition-all" />
            </div>

            <div>
                <label class="block text-xs font-semibold uppercase tracking-wider text-slate-400 mb-1.5">Master Password</label>
                <input type="password" id="password" required placeholder="••••••••"
                    class="w-full px-4 py-3 rounded-xl bg-[#0b0f19] border border-slate-800 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 outline-none text-white text-sm transition-all" />
            </div>

            <button type="submit" id="submitBtn"
                class="w-full py-3.5 px-4 rounded-xl bg-indigo-600 hover:bg-indigo-500 font-semibold text-white text-sm shadow-lg shadow-indigo-600/30 transition-all flex items-center justify-center">
                Sign In to Console
            </button>
        </form>

        <div class="mt-8 pt-6 border-t border-slate-800/80 text-center text-xs text-slate-500">
            Real-time multi-device license & access revocation system
        </div>
    </div>

    <script>
        async function handleLogin(e) {
            e.preventDefault();
            const errBox = document.getElementById('errorAlert');
            const btn = document.getElementById('submitBtn');
            errBox.classList.add('hidden');
            btn.disabled = true;
            btn.innerText = 'Authenticating...';

            try {
                const res = await fetch('/api/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        username: document.getElementById('username').value,
                        password: document.getElementById('password').value
                    })
                });
                const data = await res.json();
                if (!res.ok) throw new Error(data.detail || 'Authentication failed');

                if (data.role !== 'SUPER_ADMIN') {
                    throw new Error('Access denied: Web Console is reserved for Super Admin.');
                }

                localStorage.setItem('avanture_token', data.token);
                localStorage.setItem('avanture_user', JSON.stringify(data.user));
                window.location.href = '/dashboard';
            } catch (err) {
                errBox.innerText = err.message;
                errBox.classList.remove('hidden');
            } finally {
                btn.disabled = false;
                btn.innerText = 'Sign In to Console';
            }
        }
    </script>
</body>
</html>
"""

DASHBOARD_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en" class="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Avanture — Super Admin Control Center</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
    <style>body { font-family: 'Plus Jakarta Sans', sans-serif; }</style>
</head>
<body class="bg-[#0b0f19] text-slate-100 min-h-screen">

    <!-- Top Navigation -->
    <header class="bg-[#111827] border-b border-slate-800 sticky top-0 z-30">
        <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="w-10 h-10 rounded-xl bg-indigo-950/80 border border-indigo-700/60 flex items-center justify-center text-indigo-400 text-lg shadow-sm">
                    ⚡
                </div>
                <div>
                    <span class="font-bold text-base tracking-tight text-white">AVANTURE</span>
                    <span class="text-xs text-indigo-400 font-semibold ml-2 px-2 py-0.5 rounded-full bg-indigo-950 border border-indigo-800">SUPER ADMIN</span>
                </div>
            </div>

            <div class="flex items-center space-x-3">
                <button onclick="openChangePasswordModal()" class="px-3.5 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-xs font-semibold text-slate-200 border border-slate-700 transition">
                    🔑 Change Password
                </button>
                <button onclick="logout()" class="px-3.5 py-1.5 rounded-lg bg-rose-950/40 hover:bg-rose-900/60 text-xs font-semibold text-rose-300 border border-rose-800/60 transition">
                    Sign Out
                </button>
            </div>
        </div>
    </header>

    <!-- Main Container -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-8">

        <!-- Header Actions & Metric Cards -->
        <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
            <div>
                <h1 class="text-2xl font-bold tracking-tight text-white">Remote Access Management</h1>
                <p class="text-sm text-slate-400 mt-1">Manage operators, issue credentials, or instantly revoke access across all laptops.</p>
            </div>
            <div class="flex items-center space-x-3">
                <button onclick="loadUsers()" class="px-4 py-2.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-sm font-medium text-slate-200 border border-slate-700 transition flex items-center space-x-2">
                    <span>↻</span>
                    <span>Refresh</span>
                </button>
                <button onclick="openCreateModal()" class="px-4 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-sm font-semibold text-white shadow-lg shadow-emerald-600/20 transition flex items-center space-x-2">
                    <span>➕</span>
                    <span>Create Admin Profile</span>
                </button>
            </div>
        </div>

        <!-- Metrics Grid -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-5">
            <div class="bg-[#111827] border border-slate-800 rounded-2xl p-5 shadow-sm">
                <div class="text-xs font-semibold tracking-wider text-slate-400 uppercase">Total Operators</div>
                <div id="statTotal" class="text-3xl font-bold text-white mt-2">0</div>
            </div>
            <div class="bg-[#111827] border border-slate-800 rounded-2xl p-5 shadow-sm">
                <div class="text-xs font-semibold tracking-wider text-slate-400 uppercase">Active Allowed Laptops</div>
                <div id="statActive" class="text-3xl font-bold text-emerald-400 mt-2">0</div>
            </div>
            <div class="bg-[#111827] border border-slate-800 rounded-2xl p-5 shadow-sm">
                <div class="text-xs font-semibold tracking-wider text-slate-400 uppercase">Revoked / Locked Out</div>
                <div id="statRevoked" class="text-3xl font-bold text-rose-400 mt-2">0</div>
            </div>
        </div>

        <!-- Directory Table Card -->
        <div class="bg-[#111827] border border-slate-800 rounded-2xl overflow-hidden shadow-sm">
            <div class="p-5 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
                <h2 class="text-base font-bold text-white flex items-center space-x-2">
                    <span>👥</span>
                    <span>Admin Accounts Directory</span>
                </h2>
                <div class="relative">
                    <input type="text" id="searchInput" oninput="filterUsers()" placeholder="Search username..." 
                        class="px-3.5 py-1.5 pl-8 rounded-lg bg-[#0b0f19] border border-slate-800 text-xs text-white placeholder-slate-500 focus:border-indigo-500 outline-none" />
                    <span class="absolute left-2.5 top-1.5 text-xs text-slate-500">🔍</span>
                </div>
            </div>

            <div class="overflow-x-auto">
                <table class="w-full text-left border-collapse text-sm">
                    <thead>
                        <tr class="border-b border-slate-800 bg-[#0d1322] text-xs font-semibold text-slate-400 uppercase tracking-wider">
                            <th class="py-3 px-5">Operator</th>
                            <th class="py-3 px-5">Role</th>
                            <th class="py-3 px-5">Status</th>
                            <th class="py-3 px-5">Last Active</th>
                            <th class="py-3 px-5">Created</th>
                            <th class="py-3 px-5 text-right">Actions</th>
                        </tr>
                    </thead>
                    <tbody id="userTableBody" class="divide-y divide-slate-800/80 text-slate-300">
                        <tr>
                            <td colspan="6" class="text-center py-8 text-slate-500">Loading directory...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <!-- Modal: Create Admin -->
    <div id="createModal" class="hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-[#111827] border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-5 shadow-2xl">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 class="font-bold text-lg text-white">➕ Create Admin Profile</h3>
                <button onclick="closeCreateModal()" class="text-slate-400 hover:text-white text-lg">&times;</button>
            </div>
            <form onsubmit="submitCreateAdmin(event)" class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold text-slate-400 mb-1">Username *</label>
                    <input type="text" id="newUsername" required placeholder="e.g. operator1"
                        class="w-full px-3.5 py-2.5 rounded-xl bg-[#0b0f19] border border-slate-800 text-sm text-white outline-none focus:border-indigo-500" />
                </div>
                <div>
                    <label class="block text-xs font-semibold text-slate-400 mb-1">Password *</label>
                    <input type="password" id="newPassword" required placeholder="min 4 chars"
                        class="w-full px-3.5 py-2.5 rounded-xl bg-[#0b0f19] border border-slate-800 text-sm text-white outline-none focus:border-indigo-500" />
                </div>
                <div class="flex justify-end space-x-3 pt-2">
                    <button type="button" onclick="closeCreateModal()" class="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700">Cancel</button>
                    <button type="submit" class="px-4 py-2 rounded-xl bg-emerald-600 text-white text-xs font-semibold hover:bg-emerald-500 shadow-md">Create Profile</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Modal: Reset Password -->
    <div id="resetPwdModal" class="hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-[#111827] border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-5 shadow-2xl">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 class="font-bold text-lg text-white">🔑 Reset Password</h3>
                <button onclick="closeResetPwdModal()" class="text-slate-400 hover:text-white text-lg">&times;</button>
            </div>
            <form onsubmit="submitResetPassword(event)" class="space-y-4">
                <input type="hidden" id="resetUserId" />
                <div>
                    <label class="block text-xs font-semibold text-slate-400 mb-1">Target Operator</label>
                    <input type="text" id="resetUsernameDisplay" disabled
                        class="w-full px-3.5 py-2 rounded-xl bg-[#0b0f19] border border-slate-800 text-sm text-slate-400 cursor-not-allowed" />
                </div>
                <div>
                    <label class="block text-xs font-semibold text-slate-400 mb-1">New Password *</label>
                    <input type="password" id="resetNewPassword" required placeholder="Enter new password"
                        class="w-full px-3.5 py-2.5 rounded-xl bg-[#0b0f19] border border-slate-800 text-sm text-white outline-none focus:border-indigo-500" />
                </div>
                <div class="flex justify-end space-x-3 pt-2">
                    <button type="button" onclick="closeResetPwdModal()" class="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700">Cancel</button>
                    <button type="submit" class="px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-500 shadow-md">Update Password</button>
                </div>
            </form>
        </div>
    </div>

    <!-- Modal: Change Master Password -->
    <div id="masterPwdModal" class="hidden fixed inset-0 bg-black/60 backdrop-blur-sm z-50 flex items-center justify-center p-4">
        <div class="bg-[#111827] border border-slate-800 rounded-2xl w-full max-w-md p-6 space-y-5 shadow-2xl">
            <div class="flex items-center justify-between border-b border-slate-800 pb-3">
                <h3 class="font-bold text-lg text-white">🔑 Change Super Admin Password</h3>
                <button onclick="closeChangePasswordModal()" class="text-slate-400 hover:text-white text-lg">&times;</button>
            </div>
            <form onsubmit="submitMasterPassword(event)" class="space-y-4">
                <div>
                    <label class="block text-xs font-semibold text-slate-400 mb-1">Current Password *</label>
                    <input type="password" id="masterCurrentPassword" required
                        class="w-full px-3.5 py-2.5 rounded-xl bg-[#0b0f19] border border-slate-800 text-sm text-white outline-none focus:border-indigo-500" />
                </div>
                <div>
                    <label class="block text-xs font-semibold text-slate-400 mb-1">New Password *</label>
                    <input type="password" id="masterNewPassword" required
                        class="w-full px-3.5 py-2.5 rounded-xl bg-[#0b0f19] border border-slate-800 text-sm text-white outline-none focus:border-indigo-500" />
                </div>
                <div class="flex justify-end space-x-3 pt-2">
                    <button type="button" onclick="closeChangePasswordModal()" class="px-4 py-2 rounded-xl bg-slate-800 text-slate-300 text-xs font-semibold hover:bg-slate-700">Cancel</button>
                    <button type="submit" class="px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-semibold hover:bg-indigo-500 shadow-md">Update Master Password</button>
                </div>
            </form>
        </div>
    </div>

    <script>
        let allUsers = [];

        async function fetchWithAuth(url, options = {}) {
            const token = localStorage.getItem('avanture_token');
            if (!token) {
                window.location.href = '/login';
                return null;
            }
            options.headers = options.headers || {};
            options.headers['Authorization'] = 'Bearer ' + token;
            const res = await fetch(url, options);
            if (res.status === 401) {
                localStorage.removeItem('avanture_token');
                window.location.href = '/login';
                return null;
            }
            return res;
        }

        async function loadUsers() {
            const res = await fetchWithAuth('/api/users');
            if (!res) return;
            allUsers = await res.json();
            const searchInput = document.getElementById('searchInput');
            if (searchInput && searchInput.value.trim().length > 0) {
                filterUsers();
            } else {
                renderTable(allUsers);
            }
        }

        function renderTable(users) {
            const tbody = document.getElementById('userTableBody');
            tbody.innerHTML = '';

            const admins = users.filter(u => u.role === 'ADMIN');
            const activeCount = admins.filter(u => u.status === 'ACTIVE').length;
            const revokedCount = admins.filter(u => u.status === 'REVOKED').length;

            document.getElementById('statTotal').innerText = admins.length;
            document.getElementById('statActive').innerText = activeCount;
            document.getElementById('statRevoked').innerText = revokedCount;

            if (users.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" class="text-center py-8 text-slate-500">No accounts found.</td></tr>';
                return;
            }

            users.forEach(u => {
                const isMaster = (u.role === 'SUPER_ADMIN');
                const isActive = (u.status === 'ACTIVE');

                const tr = document.createElement('tr');
                tr.className = 'hover:bg-slate-800/40 transition';

                tr.innerHTML = `
                    <td class="py-3.5 px-5 font-medium text-white flex items-center space-x-2">
                        <span>${isMaster ? '👑' : '👤'}</span>
                        <span>@${u.username}</span>
                    </td>
                    <td class="py-3.5 px-5">
                        <span class="px-2 py-0.5 rounded text-xs font-semibold ${isMaster ? 'bg-indigo-950 text-indigo-300 border border-indigo-800' : 'bg-slate-800 text-slate-300'}">
                            ${isMaster ? 'SUPER ADMIN' : 'ADMIN OPERATOR'}
                        </span>
                    </td>
                    <td class="py-3.5 px-5">
                        <span class="px-2.5 py-0.5 rounded-full text-xs font-semibold ${isActive ? 'bg-emerald-950 text-emerald-400 border border-emerald-800/50' : 'bg-rose-950 text-rose-400 border border-rose-800/50'}">
                            ${isActive ? '● ACTIVE' : '✕ REVOKED'}
                        </span>
                    </td>
                    <td class="py-3.5 px-5 text-xs text-slate-400">${u.last_login || 'Never'}</td>
                    <td class="py-3.5 px-5 text-xs text-slate-400">${u.created_at || '—'}</td>
                    <td class="py-3.5 px-5 text-right space-x-2">
                        ${isMaster ? '<span class="text-xs text-slate-500 italic">Primary Account</span>' : `
                            <button onclick="toggleStatus(${u.id}, '${u.username}', '${isActive ? 'REVOKED' : 'ACTIVE'}')"
                                class="px-3 py-1 rounded-lg text-xs font-semibold transition ${isActive ? 'bg-rose-950/50 hover:bg-rose-900/80 text-rose-300 border border-rose-800/50' : 'bg-emerald-950/50 hover:bg-emerald-900/80 text-emerald-300 border border-emerald-800/50'}">
                                ${isActive ? '🔒 Revoke' : '🔓 Restore'}
                            </button>
                            <button onclick="openResetPwdModal(${u.id}, '${u.username}')"
                                class="px-3 py-1 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700">
                                🔑 Reset
                            </button>
                            <button onclick="deleteUser(${u.id}, '${u.username}')"
                                class="px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-rose-600 text-slate-400 hover:text-white transition">
                                🗑️
                            </button>
                        `}
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        function filterUsers() {
            const query = document.getElementById('searchInput').value.toLowerCase().trim();
            if (!query) {
                renderTable(allUsers);
                return;
            }
            const filtered = allUsers.filter(u => u.username.toLowerCase().includes(query));
            renderTable(filtered);
        }

        async function toggleStatus(id, username, newStatus) {
            const action = newStatus === 'REVOKED' ? 'REVOKE ACCESS for' : 'RESTORE ACCESS for';
            if (!confirm(`Are you sure you want to ${action} @${username}?`)) return;

            const res = await fetchWithAuth(`/api/users/${id}/status`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ status: newStatus })
            });
            if (res && res.ok) {
                loadUsers();
            } else {
                alert('Failed to update status');
            }
        }

        async function deleteUser(id, username) {
            if (!confirm(`Permanently delete admin profile @${username}?`)) return;
            const res = await fetchWithAuth(`/api/users/${id}`, { method: 'DELETE' });
            if (res && res.ok) {
                loadUsers();
            } else {
                alert('Failed to delete user');
            }
        }

        // Modals
        function openCreateModal() { document.getElementById('createModal').classList.remove('hidden'); }
        function closeCreateModal() { document.getElementById('createModal').classList.add('hidden'); }

        async function submitCreateAdmin(e) {
            e.preventDefault();
            const u = document.getElementById('newUsername').value.trim();
            const p = document.getElementById('newPassword').value.trim();
            const res = await fetchWithAuth('/api/users', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username: u, password: p })
            });
            if (res && res.ok) {
                closeCreateModal();
                loadUsers();
            } else {
                const data = await res.json();
                alert(data.detail || 'Error creating user');
            }
        }

        function openResetPwdModal(id, username) {
            document.getElementById('resetUserId').value = id;
            document.getElementById('resetUsernameDisplay').value = '@' + username;
            document.getElementById('resetNewPassword').value = '';
            document.getElementById('resetPwdModal').classList.remove('hidden');
        }
        function closeResetPwdModal() { document.getElementById('resetPwdModal').classList.add('hidden'); }

        async function submitResetPassword(e) {
            e.preventDefault();
            const id = document.getElementById('resetUserId').value;
            const p = document.getElementById('resetNewPassword').value.trim();
            const res = await fetchWithAuth(`/api/users/${id}/password`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ password: p })
            });
            if (res && res.ok) {
                alert('Password reset successfully!');
                closeResetPwdModal();
            } else {
                alert('Failed to update password');
            }
        }

        function openChangePasswordModal() { document.getElementById('masterPwdModal').classList.remove('hidden'); }
        function closeChangePasswordModal() { document.getElementById('masterPwdModal').classList.add('hidden'); }

        async function submitMasterPassword(e) {
            e.preventDefault();
            const curr = document.getElementById('masterCurrentPassword').value;
            const nxt = document.getElementById('masterNewPassword').value;
            const res = await fetchWithAuth('/api/change-password', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ current_password: curr, new_password: nxt })
            });
            if (res && res.ok) {
                alert('Super Admin password updated successfully!');
                closeChangePasswordModal();
            } else {
                const data = await res.json();
                alert(data.detail || 'Failed to update password');
            }
        }

        function logout() {
            localStorage.removeItem('avanture_token');
            localStorage.removeItem('avanture_user');
            window.location.href = '/login';
        }

        // Initialize on load
        loadUsers();
        setInterval(loadUsers, 12000); // Polling interval (12s) to prevent DOM churn
    </script>
</body>
</html>
"""

# -------------------------------------------------------------
# Web Routes
# -------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    return RedirectResponse("/dashboard")

@app.get("/login", response_class=HTMLResponse)
def login_page():
    return LOGIN_PAGE_HTML

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page():
    return DASHBOARD_PAGE_HTML

# -------------------------------------------------------------
# REST API Endpoints
# -------------------------------------------------------------
@app.post("/api/auth/login")
def api_auth_login(req: ClientLoginRequest):
    u = req.username.strip().lower()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (u,))
        user = cursor.fetchone()

        if not user:
            raise HTTPException(status_code=400, detail="Invalid username or password.")

        check_hash, _ = hash_password(req.password, user["salt"])
        if check_hash != user["password_hash"]:
            raise HTTPException(status_code=400, detail="Invalid username or password.")

        if user["status"] == "REVOKED":
            raise HTTPException(status_code=403, detail="Access Denied: Account privileges have been revoked.")

        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user["id"]))
        conn.commit()

        # Simple signed token representation
        token = f"{user['id']}:{user['username']}:{user['role']}"
        return {
            "token": token,
            "role": user["role"],
            "user": {
                "id": user["id"],
                "username": user["username"],
                "role": user["role"],
                "status": user["status"]
            }
        }

@app.get("/api/client/check-status")
def client_check_status(username: str):
    """
    Heartbeat endpoint called by desktop AvantureAutomation.exe every 4s.
    Returns status: ACTIVE or REVOKED.
    """
    u = username.strip().lower()
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT status FROM users WHERE username = ?", (u,))
        row = cursor.fetchone()
        if not row:
            return {"active": False, "status": "REVOKED", "message": "User not found"}
        is_active = (row["status"] == "ACTIVE")
        return {"active": is_active, "status": row["status"]}

@app.get("/api/users")
def list_users():
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, role, status, created_at, last_login, created_by FROM users ORDER BY id ASC")
        return [dict(row) for row in cursor.fetchall()]

@app.post("/api/users")
def create_admin(req: CreateAdminRequest):
    u = req.username.strip().lower()
    if not u or not req.password:
        raise HTTPException(status_code=400, detail="Username and password required.")
    if len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 chars.")

    p_hash, salt = hash_password(req.password)
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO users (username, password_hash, salt, role, status, created_at, created_by)
                VALUES (?, ?, ?, 'ADMIN', 'ACTIVE', ?, 'WEB_SUPERADMIN')
            """, (u, p_hash, salt, now))
            conn.commit()
            return {"message": f"Admin @{u} created successfully."}
    except sqlite3.IntegrityError:
        raise HTTPException(status_code=400, detail=f"Username '@{u}' already exists.")

@app.post("/api/users/{user_id}/status")
def update_user_status(user_id: int, req: StatusUpdateRequest):
    if req.status not in ("ACTIVE", "REVOKED"):
        raise HTTPException(status_code=400, detail="Invalid status.")

    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username, role FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        if user["username"] == "superadmin":
            raise HTTPException(status_code=400, detail="Cannot revoke primary superadmin account.")

        cursor.execute("UPDATE users SET status = ? WHERE id = ?", (req.status, user_id))
        conn.commit()
        return {"message": f"Status updated to {req.status} for @{user['username']}."}

@app.post("/api/users/{user_id}/password")
def reset_user_password(user_id: int, req: PasswordUpdateRequest):
    if not req.password or len(req.password) < 4:
        raise HTTPException(status_code=400, detail="Password must be at least 4 chars.")

    p_hash, salt = hash_password(req.password)
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (p_hash, salt, user_id))
        conn.commit()
        return {"message": "Password updated successfully."}

@app.delete("/api/users/{user_id}")
def delete_user(user_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        if user["username"] == "superadmin":
            raise HTTPException(status_code=400, detail="Cannot delete master account.")

        cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
        return {"message": f"User @{user['username']} deleted successfully."}

@app.post("/api/change-password")
def change_superadmin_password(req: ChangeSuperAdminPasswordRequest):
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE username = 'superadmin'")
        master = cursor.fetchone()

        check_hash, _ = hash_password(req.current_password, master["salt"])
        if check_hash != master["password_hash"]:
            raise HTTPException(status_code=400, detail="Current master password incorrect.")

        if len(req.new_password) < 4:
            raise HTTPException(status_code=400, detail="New password must be at least 4 chars.")

        p_hash, salt = hash_password(req.new_password)
        cursor.execute("UPDATE users SET password_hash = ?, salt = ? WHERE username = 'superadmin'", (p_hash, salt))
        conn.commit()
        return {"message": "Super Admin master password changed successfully."}

if __name__ == "__main__":
    import uvicorn
    import webbrowser
    import threading
    import time

    print("\n" + "="*60)
    print(" ⚡ Avanture Central Web Server is RUNNING!")
    print(" 🌐 Opening Web Dashboard in your browser: http://localhost:8000")
    print(" 💡 Keep this terminal window open while using the dashboard.")
    print("    (Press Ctrl+C to stop the server)")
    print("="*60 + "\n")

    def open_browser():
        time.sleep(1.2)
        try:
            webbrowser.open("http://localhost:8000")
        except Exception:
            pass

    threading.Thread(target=open_browser, daemon=True).start()
    uvicorn.run(app, host="0.0.0.0", port=8000)

