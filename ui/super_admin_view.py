import customtkinter as ctk
from tkinter import messagebox
from typing import Optional, Callable
from datetime import datetime
from core.db import UserManager

class CreateAdminModal(ctk.CTkToplevel):
    """Clean popup dialog to create a new Admin Profile."""

    def __init__(self, parent, on_created: Optional[Callable[[], None]] = None):
        super().__init__(parent)

        self.title("➕ Create New Admin Profile")
        self.geometry("440x400")
        self.resizable(False, False)
        self.on_created = on_created
        self.db = UserManager()

        self.configure(fg_color="#0f172a")
        self.transient(parent)
        self.grab_set()

        # Center modal relative to parent
        self.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            x = px + max(0, int((pw - 440) / 2))
            y = py + max(0, int((ph - 400) / 2))
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1f2937")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        # Title
        title_row = ctk.CTkFrame(container, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(16, 4))

        ctk.CTkLabel(
            title_row,
            text="➕ New Admin Profile",
            font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
            text_color="#f8fafc"
        ).pack(side="left")

        ctk.CTkLabel(
            container,
            text="Add a new operator who can log in and manage listings.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        ).pack(anchor="w", padx=16, pady=(0, 14))

        # Username
        ctk.CTkLabel(
            container,
            text="Admin Username *",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#cbd5e1"
        ).pack(anchor="w", padx=16, pady=(0, 2))

        self.username_entry = ctk.CTkEntry(
            container,
            placeholder_text="e.g. operator_john",
            height=34,
            corner_radius=6,
            fg_color="#0b0f19",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.username_entry.pack(fill="x", padx=16, pady=(0, 10))

        # Password
        ctk.CTkLabel(
            container,
            text="Password *",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#cbd5e1"
        ).pack(anchor="w", padx=16, pady=(0, 2))

        self.password_entry = ctk.CTkEntry(
            container,
            placeholder_text="Enter secure password",
            show="*",
            height=34,
            corner_radius=6,
            fg_color="#0b0f19",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.password_entry.pack(fill="x", padx=16, pady=(0, 10))

        # Confirm Password
        ctk.CTkLabel(
            container,
            text="Confirm Password *",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#cbd5e1"
        ).pack(anchor="w", padx=16, pady=(0, 2))

        self.confirm_entry = ctk.CTkEntry(
            container,
            placeholder_text="Re-type password",
            show="*",
            height=34,
            corner_radius=6,
            fg_color="#0b0f19",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.confirm_entry.pack(fill="x", padx=16, pady=(0, 16))

        # Action Buttons
        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 14))

        cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            height=34,
            width=90,
            corner_radius=6,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#cbd5e1",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self.destroy
        )
        cancel_btn.pack(side="left")

        create_btn = ctk.CTkButton(
            btn_row,
            text="Create Profile",
            height=34,
            corner_radius=6,
            fg_color="#10b981",
            hover_color="#059669",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._on_submit
        )
        create_btn.pack(side="right")

    def _on_submit(self):
        username = self.username_entry.get().strip().lower()
        password = self.password_entry.get()
        confirm = self.confirm_entry.get()

        if not username or not password:
            messagebox.showwarning("Incomplete Form", "Please fill in all required fields.", parent=self)
            return

        if len(password) < 4:
            messagebox.showwarning("Weak Password", "Password must be at least 4 characters long.", parent=self)
            return

        if password != confirm:
            messagebox.showerror("Password Mismatch", "Passwords do not match.", parent=self)
            return

        ok, msg = self.db.create_user(username, password, role="ADMIN")
        if not ok:
            messagebox.showerror("Error", msg, parent=self)
            return

        messagebox.showinfo("Success", f"Admin profile '@{username}' created successfully!", parent=self)
        if self.on_created:
            self.on_created()
        self.destroy()


class ChangeSuperAdminPasswordModal(ctk.CTkToplevel):
    """Secure popup dialog for the Super Admin to change their master password."""

    def __init__(self, parent, current_user: dict):
        super().__init__(parent)

        self.title("🔑 Change Master Password")
        self.geometry("440x420")
        self.resizable(False, False)
        self.current_user = current_user
        self.db = UserManager()

        self.configure(fg_color="#0f172a")
        self.transient(parent)
        self.grab_set()

        # Center modal relative to parent
        self.update_idletasks()
        try:
            pw = parent.winfo_width()
            ph = parent.winfo_height()
            px = parent.winfo_rootx()
            py = parent.winfo_rooty()
            x = px + max(0, int((pw - 440) / 2))
            y = py + max(0, int((ph - 420) / 2))
            self.geometry(f"+{x}+{y}")
        except Exception:
            pass

        self._build_ui()

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="#111827", corner_radius=12, border_width=1, border_color="#1f2937")
        container.pack(fill="both", expand=True, padx=16, pady=16)

        # Title
        title_row = ctk.CTkFrame(container, fg_color="transparent")
        title_row.pack(fill="x", padx=16, pady=(16, 4))

        ctk.CTkLabel(
            title_row,
            text="🔑 Change Super Admin Password",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#f8fafc"
        ).pack(side="left")

        u_name = self.current_user.get("username", "superadmin")
        ctk.CTkLabel(
            container,
            text=f"Update security credentials for master account '@{u_name}'",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        ).pack(anchor="w", padx=16, pady=(0, 14))

        # Current Password
        ctk.CTkLabel(
            container,
            text="Current Password *",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#cbd5e1"
        ).pack(anchor="w", padx=16, pady=(0, 2))

        self.current_pass_entry = ctk.CTkEntry(
            container,
            placeholder_text="Enter current master password",
            show="*",
            height=34,
            corner_radius=6,
            fg_color="#0b0f19",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.current_pass_entry.pack(fill="x", padx=16, pady=(0, 10))

        # New Password
        ctk.CTkLabel(
            container,
            text="New Password *",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#cbd5e1"
        ).pack(anchor="w", padx=16, pady=(0, 2))

        self.new_pass_entry = ctk.CTkEntry(
            container,
            placeholder_text="Enter new password (min 4 characters)",
            show="*",
            height=34,
            corner_radius=6,
            fg_color="#0b0f19",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.new_pass_entry.pack(fill="x", padx=16, pady=(0, 10))

        # Confirm New Password
        ctk.CTkLabel(
            container,
            text="Confirm New Password *",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#cbd5e1"
        ).pack(anchor="w", padx=16, pady=(0, 2))

        self.confirm_pass_entry = ctk.CTkEntry(
            container,
            placeholder_text="Re-type new password",
            show="*",
            height=34,
            corner_radius=6,
            fg_color="#0b0f19",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.confirm_pass_entry.pack(fill="x", padx=16, pady=(0, 16))

        # Action Buttons
        btn_row = ctk.CTkFrame(container, fg_color="transparent")
        btn_row.pack(fill="x", padx=16, pady=(0, 14))

        cancel_btn = ctk.CTkButton(
            btn_row,
            text="Cancel",
            height=34,
            width=90,
            corner_radius=6,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#cbd5e1",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self.destroy
        )
        cancel_btn.pack(side="left")

        update_btn = ctk.CTkButton(
            btn_row,
            text="Update Password",
            height=34,
            corner_radius=6,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._on_submit
        )
        update_btn.pack(side="right")

    def _on_submit(self):
        curr_pwd = self.current_pass_entry.get().strip()
        new_pwd = self.new_pass_entry.get().strip()
        confirm_pwd = self.confirm_pass_entry.get().strip()

        if not curr_pwd or not new_pwd:
            messagebox.showwarning("Incomplete Form", "Please fill in all fields.", parent=self)
            return

        username = self.current_user.get("username", "superadmin")
        ok_auth, msg, _ = self.db.authenticate(username, curr_pwd)
        if not ok_auth:
            messagebox.showerror("Authentication Failed", "Current password is incorrect.", parent=self)
            return

        if len(new_pwd) < 4:
            messagebox.showwarning("Weak Password", "New password must be at least 4 characters long.", parent=self)
            return

        if new_pwd != confirm_pwd:
            messagebox.showerror("Mismatch", "New password and confirmation do not match.", parent=self)
            return

        user_id = self.current_user.get("id")
        if not user_id:
            all_u = self.db.get_all_users()
            for u in all_u:
                if u["username"].lower() == username.lower():
                    user_id = u["id"]
                    break

        ok_change, change_msg = self.db.change_password(user_id, new_pwd)
        if ok_change:
            messagebox.showinfo("Success", "Super Admin password updated successfully!", parent=self)
            self.destroy()
        else:
            messagebox.showerror("Error", change_msg, parent=self)


class SuperAdminView(ctk.CTkFrame):
    """
    Dedicated Super Admin Management Console.
    Super Admin has NO automation; handles Admin profiles, real-time revocation,
    access control, and password resets.
    """

    def __init__(self, master, current_user: dict, on_logout: Optional[Callable[[], None]] = None):
        super().__init__(master, fg_color="transparent")

        self.current_user = current_user
        self.on_logout = on_logout
        self.db = UserManager()

        self._build_ui()
        self._refresh_profiles()

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        # ==============================================================
        # 1. TOP NAVBAR / BRANDING
        # ==============================================================
        nav_card = ctk.CTkFrame(
            self,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
            corner_radius=12
        )
        nav_card.grid(row=0, column=0, padx=20, pady=(16, 10), sticky="ew")
        nav_card.grid_columnconfigure(1, weight=1)

        # Left Branding
        nav_left = ctk.CTkFrame(nav_card, fg_color="transparent")
        nav_left.grid(row=0, column=0, padx=16, pady=12, sticky="w")

        title_row = ctk.CTkFrame(nav_left, fg_color="transparent")
        title_row.pack(anchor="w")

        emblem = ctk.CTkLabel(
            title_row,
            text="⚡ AVANTURE",
            font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
            text_color="#818cf8"
        )
        emblem.pack(side="left", padx=(0, 6))

        title_sub = ctk.CTkLabel(
            title_row,
            text="Super Admin Security & Access Control Console",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#f8fafc"
        )
        title_sub.pack(side="left")

        # Operator Meta
        user_meta = ctk.CTkFrame(nav_left, fg_color="transparent")
        user_meta.pack(anchor="w", pady=(2, 0))

        u_label = ctk.CTkLabel(
            user_meta,
            text=f"Master Operator: @{self.current_user.get('username')}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        )
        u_label.pack(side="left", padx=(0, 6))

        role_tag = ctk.CTkLabel(
            user_meta,
            text="SUPER ADMIN (MASTER)",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#312e81",
            text_color="#a5b4fc",
            corner_radius=4,
            padx=6,
            pady=1
        )
        role_tag.pack(side="left")

        # Right Actions
        nav_right = ctk.CTkFrame(nav_card, fg_color="transparent")
        nav_right.grid(row=0, column=1, padx=16, pady=12, sticky="e")

        change_pwd_btn = ctk.CTkButton(
            nav_right,
            text="🔑 Change Password",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            height=30,
            corner_radius=6,
            fg_color="#312e81",
            hover_color="#3730a3",
            border_width=1,
            border_color="#4f46e5",
            text_color="#e0e7ff",
            command=self._on_click_change_superadmin_password
        )
        change_pwd_btn.pack(side="left", padx=(0, 8))

        logout_btn = ctk.CTkButton(
            nav_right,
            text="Sign Out",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            width=70,
            height=30,
            corner_radius=6,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#cbd5e1",
            command=self._on_click_logout
        )
        logout_btn.pack(side="left")

        # ==============================================================
        # 2. KPI / STATS BAR & ACTION CONTROLS
        # ==============================================================
        stats_card = ctk.CTkFrame(
            self,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
            corner_radius=12
        )
        stats_card.grid(row=1, column=0, padx=20, pady=(0, 10), sticky="ew")
        stats_card.grid_columnconfigure(0, weight=1)

        stats_top = ctk.CTkFrame(stats_card, fg_color="transparent")
        stats_top.pack(fill="x", padx=16, pady=(12, 8))
        stats_top.grid_columnconfigure(0, weight=1)

        # Title & Subtitle
        header_text_frame = ctk.CTkFrame(stats_top, fg_color="transparent")
        header_text_frame.grid(row=0, column=0, sticky="w")

        ctk.CTkLabel(
            header_text_frame,
            text="🛡️ Admin Operator Profiles Management",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#e2e8f0"
        ).pack(anchor="w")

        ctk.CTkLabel(
            header_text_frame,
            text="Add operator profiles, grant or revoke access anytime in real time.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748b"
        ).pack(anchor="w")

        # Plus Sign Button to Create New Admin Profile
        action_box = ctk.CTkFrame(stats_top, fg_color="transparent")
        action_box.grid(row=0, column=1, sticky="e")

        refresh_btn = ctk.CTkButton(
            action_box,
            text="↻ Refresh",
            width=75,
            height=34,
            corner_radius=6,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#cbd5e1",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._refresh_profiles
        )
        refresh_btn.pack(side="left", padx=(0, 8))

        # Highlighted [+] Button
        self.create_btn = ctk.CTkButton(
            action_box,
            text="➕  Create Admin Profile",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=34,
            corner_radius=8,
            fg_color="#10b981",
            hover_color="#059669",
            text_color="#ffffff",
            command=self._on_click_create_admin
        )
        self.create_btn.pack(side="left")

        # Stats Metric Tiles
        tiles_frame = ctk.CTkFrame(stats_card, fg_color="transparent")
        tiles_frame.pack(fill="x", padx=16, pady=(0, 12))
        tiles_frame.grid_columnconfigure(0, weight=1)
        tiles_frame.grid_columnconfigure(1, weight=1)
        tiles_frame.grid_columnconfigure(2, weight=1)

        self.kpi_total = self._create_kpi_tile(tiles_frame, 0, "TOTAL ADMINS", "0", "#6366f1")
        self.kpi_active = self._create_kpi_tile(tiles_frame, 1, "ACTIVE OPERATORS", "0", "#10b981")
        self.kpi_revoked = self._create_kpi_tile(tiles_frame, 2, "REVOKED / BLOCKED", "0", "#ef4444")

        # ==============================================================
        # 3. SCROLLABLE ADMIN PROFILES DIRECTORY
        # ==============================================================
        directory_card = ctk.CTkFrame(
            self,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
            corner_radius=12
        )
        directory_card.grid(row=2, column=0, padx=20, pady=(0, 16), sticky="nsew")
        directory_card.grid_columnconfigure(0, weight=1)
        directory_card.grid_rowconfigure(1, weight=1)

        # Directory Top Bar
        dir_top = ctk.CTkFrame(directory_card, fg_color="transparent")
        dir_top.grid(row=0, column=0, padx=16, pady=(10, 6), sticky="ew")
        dir_top.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            dir_top,
            text="👥 Active Admin Directory",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#94a3b8"
        ).grid(row=0, column=0, sticky="w")

        self.search_entry = ctk.CTkEntry(
            dir_top,
            placeholder_text="🔍 Filter by username...",
            width=200,
            height=28,
            corner_radius=6,
            fg_color="#0b0f19",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.search_entry.grid(row=0, column=1, sticky="e")
        self.search_entry.bind("<KeyRelease>", lambda e: self._filter_profiles())

        # Scrollable Cards
        self.profiles_scroll = ctk.CTkScrollableFrame(
            directory_card,
            fg_color="transparent",
            corner_radius=0
        )
        self.profiles_scroll.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.profiles_scroll.grid_columnconfigure(0, weight=1)

    def _create_kpi_tile(self, parent, col: int, label: str, value: str, color: str):
        tile = ctk.CTkFrame(parent, fg_color="#0b0f19", corner_radius=8, border_width=1, border_color="#1f2937")
        tile.grid(row=0, column=col, padx=4, sticky="nsew")
        tile.grid_columnconfigure(0, weight=1)

        lbl = ctk.CTkLabel(
            tile,
            text=label,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color="#94a3b8"
        )
        lbl.pack(anchor="w", padx=12, pady=(8, 0))

        val_lbl = ctk.CTkLabel(
            tile,
            text=value,
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=color
        )
        val_lbl.pack(anchor="w", padx=12, pady=(0, 8))
        return val_lbl

    def _on_click_create_admin(self):
        CreateAdminModal(self, on_created=self._refresh_profiles)

    def _refresh_profiles(self):
        self.all_users = self.db.get_all_users()

        # Update KPI tiles
        admins = [u for u in self.all_users if u["role"] == "ADMIN"]
        active_count = sum(1 for u in admins if u["status"] == "ACTIVE")
        revoked_count = sum(1 for u in admins if u["status"] == "REVOKED")

        self.kpi_total.configure(text=str(len(admins)))
        self.kpi_active.configure(text=str(active_count))
        self.kpi_revoked.configure(text=str(revoked_count))

        self._render_profiles(self.all_users)

    def _filter_profiles(self):
        query = self.search_entry.get().strip().lower()
        if not query:
            self._render_profiles(self.all_users)
            return

        filtered = [u for u in self.all_users if query in u["username"].lower()]
        self._render_profiles(filtered)

    def _render_profiles(self, users_list):
        # Clear existing cards
        for widget in self.profiles_scroll.winfo_children():
            widget.destroy()

        if not users_list:
            no_lbl = ctk.CTkLabel(
                self.profiles_scroll,
                text="No admin profiles found. Click '➕ Create Admin Profile' to add one.",
                font=ctk.CTkFont(family="Segoe UI", size=12),
                text_color="#64748b"
            )
            no_lbl.pack(pady=30)
            return

        for user in users_list:
            self._create_user_card(user)

    def _create_user_card(self, user: dict):
        is_master = (user["role"] == "SUPER_ADMIN")
        is_active = (user["status"] == "ACTIVE")

        card = ctk.CTkFrame(
            self.profiles_scroll,
            fg_color="#0f172a",
            border_width=1,
            border_color="#1e293b" if is_active else "#450a0a",
            corner_radius=10
        )
        card.pack(fill="x", padx=4, pady=4)
        card.grid_columnconfigure(1, weight=1)

        # Left: Avatar / Badge
        left_box = ctk.CTkFrame(card, fg_color="transparent")
        left_box.grid(row=0, column=0, padx=14, pady=10, sticky="w")

        avatar_lbl = ctk.CTkLabel(
            left_box,
            text="👑" if is_master else "👤",
            font=ctk.CTkFont(size=20)
        )
        avatar_lbl.pack(side="left", padx=(0, 10))

        info_box = ctk.CTkFrame(left_box, fg_color="transparent")
        info_box.pack(side="left")

        u_row = ctk.CTkFrame(info_box, fg_color="transparent")
        u_row.pack(anchor="w")

        name_lbl = ctk.CTkLabel(
            u_row,
            text=f"@{user['username']}",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#f8fafc"
        )
        name_lbl.pack(side="left", padx=(0, 8))

        role_tag = ctk.CTkLabel(
            u_row,
            text="SUPER ADMIN" if is_master else "ADMIN OPERATOR",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            fg_color="#312e81" if is_master else "#0c4a6e",
            text_color="#a5b4fc" if is_master else "#7dd3fc",
            corner_radius=4,
            padx=6,
            pady=1
        )
        role_tag.pack(side="left", padx=(0, 8))

        # Status Badge
        status_tag = ctk.CTkLabel(
            u_row,
            text="● ACTIVE" if is_active else "✕ REVOKED",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            fg_color="#064e3b" if is_active else "#450a0a",
            text_color="#34d399" if is_active else "#f87171",
            corner_radius=4,
            padx=6,
            pady=1
        )
        status_tag.pack(side="left")

        # Metadata Line
        created_str = user.get("created_at", "—")
        login_str = user.get("last_login") or "Never logged in"
        meta_lbl = ctk.CTkLabel(
            info_box,
            text=f"Created: {created_str}  •  Last Active: {login_str}",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#64748b"
        )
        meta_lbl.pack(anchor="w", pady=(2, 0))

        # Right: Actions (Only for non-superadmin accounts)
        right_box = ctk.CTkFrame(card, fg_color="transparent")
        right_box.grid(row=0, column=2, padx=14, pady=10, sticky="e")

        if is_master:
            master_pwd_btn = ctk.CTkButton(
                right_box,
                text="🔑 Change Password",
                width=135,
                height=28,
                corner_radius=6,
                fg_color="#312e81",
                hover_color="#3730a3",
                border_width=1,
                border_color="#4f46e5",
                text_color="#e0e7ff",
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                command=self._on_click_change_superadmin_password
            )
            master_pwd_btn.pack(side="right")
        else:
            # 1. Delete Button
            del_btn = ctk.CTkButton(
                right_box,
                text="🗑️ Delete",
                width=70,
                height=28,
                corner_radius=6,
                fg_color="#1e293b",
                hover_color="#ef4444",
                text_color="#94a3b8",
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                command=lambda uid=user["id"], un=user["username"]: self._on_delete_user(uid, un)
            )
            del_btn.pack(side="right", padx=(4, 0))

            # 2. Reset Password Button
            pwd_btn = ctk.CTkButton(
                right_box,
                text="🔑 Password",
                width=80,
                height=28,
                corner_radius=6,
                fg_color="#1e293b",
                hover_color="#334155",
                text_color="#cbd5e1",
                font=ctk.CTkFont(family="Segoe UI", size=10),
                command=lambda uid=user["id"], un=user["username"]: self._on_change_password(uid, un)
            )
            pwd_btn.pack(side="right", padx=(4, 0))

            # 3. Revoke / Restore Access Toggle
            if is_active:
                revoke_btn = ctk.CTkButton(
                    right_box,
                    text="🔒 Revoke Access",
                    width=105,
                    height=28,
                    corner_radius=6,
                    fg_color="#7f1d1d",
                    hover_color="#991b1b",
                    text_color="#fca5a5",
                    font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                    command=lambda uid=user["id"], un=user["username"]: self._toggle_status(uid, un, "REVOKED")
                )
                revoke_btn.pack(side="right")
            else:
                restore_btn = ctk.CTkButton(
                    right_box,
                    text="🔓 Restore Access",
                    width=105,
                    height=28,
                    corner_radius=6,
                    fg_color="#064e3b",
                    hover_color="#047857",
                    text_color="#6ee7b7",
                    font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                    command=lambda uid=user["id"], un=user["username"]: self._toggle_status(uid, un, "ACTIVE")
                )
                restore_btn.pack(side="right")

    def _toggle_status(self, user_id: int, username: str, new_status: str):
        action_word = "revoke access for" if new_status == "REVOKED" else "restore access for"
        if not messagebox.askyesno("Confirm Action", f"Are you sure you want to {action_word} admin '@{username}'?"):
            return

        ok, msg = self.db.set_user_status(user_id, new_status)
        if ok:
            messagebox.showinfo("Access Updated", msg)
            self._refresh_profiles()
        else:
            messagebox.showerror("Error", msg)

    def _on_change_password(self, user_id: int, username: str):
        dialog = ctk.CTkInputDialog(
            text=f"Enter new password for @{username} (min 4 chars):",
            title="Reset Admin Password"
        )
        new_pwd = dialog.get_input()
        if new_pwd is not None:
            new_pwd = new_pwd.strip()
            if len(new_pwd) < 4:
                messagebox.showwarning("Invalid Password", "Password must be at least 4 characters long.")
                return
            ok, msg = self.db.change_password(user_id, new_pwd)
            if ok:
                messagebox.showinfo("Success", f"Password for '@{username}' updated successfully.")
            else:
                messagebox.showerror("Error", msg)

    def _on_delete_user(self, user_id: int, username: str):
        if not messagebox.askyesno(
            "Confirm Delete",
            f"Are you sure you want to permanently delete admin profile '@{username}'?\nThis action cannot be undone."
        ):
            return

        ok, msg = self.db.delete_user(user_id)
        if ok:
            messagebox.showinfo("Deleted", msg)
            self._refresh_profiles()
        else:
            messagebox.showerror("Error", msg)

    def _on_click_logout(self):
        if messagebox.askyesno("Sign Out", "Are you sure you want to sign out from Super Admin console?"):
            if self.on_logout:
                self.on_logout()

    def _on_click_change_superadmin_password(self):
        ChangeSuperAdminPasswordModal(self, current_user=self.current_user)

