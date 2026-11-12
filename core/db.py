import sqlite3
import os
import hashlib
import binascii
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

from config import BASE_DIR, AUTH_SERVER_URL

DB_PATH = BASE_DIR / "auth_system.db"

class UserManager:
    """Manages SQLite-based user authentication, role-based access, and account revocation."""

    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
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

            # Seed default Super Admin if database is brand new
            cursor.execute("SELECT COUNT(*) AS count FROM users WHERE role = 'SUPER_ADMIN'")
            if cursor.fetchone()["count"] == 0:
                self.create_user(
                    username="superadmin",
                    password="admin123",  # User can change this in the admin panel
                    role="SUPER_ADMIN",
                    created_by="SYSTEM"
                )

    @staticmethod
    def _hash_password(password: str, salt: Optional[str] = None) -> tuple[str, str]:
        if not salt:
            salt = binascii.hexlify(os.urandom(16)).decode("utf-8")
        dk = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100000)
        password_hash = binascii.hexlify(dk).decode("utf-8")
        return password_hash, salt

    def create_user(self, username: str, password: str, role: str = "ADMIN", created_by: str = "superadmin") -> tuple[bool, str]:
        username = username.strip().lower()
        if not username or not password:
            return False, "Username and password cannot be empty."

        if role not in ("SUPER_ADMIN", "ADMIN"):
            return False, "Invalid role specified."

        password_hash, salt = self._hash_password(password)
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO users (username, password_hash, salt, role, status, created_at, created_by)
                    VALUES (?, ?, ?, ?, 'ACTIVE', ?, ?)
                """, (username, password_hash, salt, role, now, created_by))
                conn.commit()
                return True, f"User '{username}' created successfully."
        except sqlite3.IntegrityError:
            return False, f"Username '{username}' already exists."
        except Exception as e:
            return False, f"Database error: {str(e)}"

    def _sync_remote_user(self, user_dict: dict):
        if not user_dict or not user_dict.get("username"):
            return
        try:
            with self._get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT id FROM users WHERE username = ?", (user_dict["username"].strip().lower(),))
                existing = cursor.fetchone()
                now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                if existing:
                    cursor.execute(
                        "UPDATE users SET role = ?, status = ?, last_login = ? WHERE id = ?",
                        (user_dict.get("role", "ADMIN"), user_dict.get("status", "ACTIVE"), now, existing["id"])
                    )
                else:
                    p_hash, salt = self._hash_password("synced_account")
                    cursor.execute("""
                        INSERT INTO users (username, password_hash, salt, role, status, created_at, created_by)
                        VALUES (?, ?, ?, ?, ?, ?, 'SERVER_SYNC')
                    """, (user_dict["username"].strip().lower(), p_hash, salt, user_dict.get("role", "ADMIN"), user_dict.get("status", "ACTIVE"), now))
                conn.commit()
        except Exception:
            pass

    def authenticate(self, username: str, password: str) -> tuple[bool, str, Optional[Dict[str, Any]]]:
        username = username.strip().lower()

        # 1. Try Central Cloud Auth Server first
        if AUTH_SERVER_URL:
            try:
                import requests
                r = requests.post(
                    f"{AUTH_SERVER_URL}/api/auth/login",
                    json={"username": username, "password": password},
                    timeout=3.5
                )
                if r.status_code == 200:
                    data = r.json()
                    user_dict = data.get("user", {})
                    self._sync_remote_user(user_dict)
                    return True, "Login successful", user_dict
                elif r.status_code == 403:
                    return False, "Access Denied: Your account access has been revoked by the Super Admin.", None
                elif r.status_code == 400:
                    return False, "Invalid username or password.", None
            except Exception:
                pass  # Fall back to local db if server is unreachable

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = cursor.fetchone()

            if not user:
                return False, "Invalid username or password.", None

            # Verify password
            check_hash, _ = self._hash_password(password, user["salt"])
            if check_hash != user["password_hash"]:
                return False, "Invalid username or password.", None

            # Check if access has been revoked
            if user["status"] == "REVOKED":
                return False, "Access Denied: Your account access has been revoked by the Super Admin.", None

            # Record login timestamp
            now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute("UPDATE users SET last_login = ? WHERE id = ?", (now, user["id"]))
            conn.commit()

            user_dict = dict(user)
            user_dict.pop("password_hash", None)
            user_dict.pop("salt", None)
            return True, "Login successful", user_dict

    def get_all_users(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, username, role, status, created_at, last_login, created_by FROM users ORDER BY id ASC")
            return [dict(row) for row in cursor.fetchall()]

    def set_user_status(self, user_id: int, status: str) -> tuple[bool, str]:
        if status not in ("ACTIVE", "REVOKED"):
            return False, "Invalid status value."

        with self._get_connection() as conn:
            cursor = conn.cursor()
            # Prevent revoking the main super admin account
            cursor.execute("SELECT username, role FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            if not user:
                return False, "User not found."
            if user["username"] == "superadmin" and status == "REVOKED":
                return False, "Cannot revoke the primary Super Admin account."

            cursor.execute("UPDATE users SET status = ? WHERE id = ?", (status, user_id))
            conn.commit()
            action = "revoked" if status == "REVOKED" else "restored"
            return True, f"Access {action} for user '{user['username']}'."

    def delete_user(self, user_id: int) -> tuple[bool, str]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT username FROM users WHERE id = ?", (user_id,))
            user = cursor.fetchone()
            if not user:
                return False, "User not found."
            if user["username"] == "superadmin":
                return False, "Cannot delete the primary Super Admin account."

            cursor.execute("DELETE FROM users WHERE id = ?", (user_id,))
            conn.commit()
            return True, f"User '{user['username']}' deleted successfully."

    def change_password(self, user_id: int, new_password: str) -> tuple[bool, str]:
        if not new_password or len(new_password) < 4:
            return False, "Password must be at least 4 characters long."

        password_hash, salt = self._hash_password(new_password)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET password_hash = ?, salt = ? WHERE id = ?", (password_hash, salt, user_id))
            conn.commit()
            return True, "Password updated successfully."

    def is_user_active(self, username: str) -> bool:
        username_clean = username.strip().lower()

        # 1. Real-time Remote Check against Central Auth Server
        if AUTH_SERVER_URL:
            try:
                import requests
                r = requests.get(
                    f"{AUTH_SERVER_URL}/api/client/check-status?username={username_clean}",
                    timeout=1.0
                )
                if r.status_code == 200:
                    data = r.json()
                    # If server explicitly returns False (e.g. REVOKED or deleted)
                    return bool(data.get("active", False))
                elif r.status_code in (403, 404):
                    return False
            except Exception:
                pass  # Fall back to local check if network unreachable

        # 2. Local database fallback
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT status FROM users WHERE username = ?", (username_clean,))
            row = cursor.fetchone()
            return bool(row and row["status"] == "ACTIVE")

