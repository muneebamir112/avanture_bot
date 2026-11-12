import customtkinter as ctk
from tkinter import messagebox
from typing import Callable
from core.db import UserManager
from core.credentials_store import CredentialsStore

class LoginView(ctk.CTkFrame):
    """Ultra-responsive embedded login view with Remember Me support."""

    def __init__(self, master, on_login_success: Callable[[dict], None]):
        super().__init__(master, fg_color="transparent")

        self.on_login_success = on_login_success
        self.db = UserManager()

        self._build_ui()
        self._load_remembered_credentials()

    def _build_ui(self):
        # ---------------- HERO BRANDING ----------------
        brand_frame = ctk.CTkFrame(self, fg_color="transparent")
        brand_frame.pack(fill="x", padx=36, pady=(32, 14))

        icon_badge = ctk.CTkLabel(
            brand_frame,
            text="⚡",
            font=ctk.CTkFont(size=36),
            width=54,
            height=54,
            corner_radius=16,
            fg_color="#1e1b4b",
            text_color="#818cf8"
        )
        icon_badge.pack(pady=(0, 10))

        title = ctk.CTkLabel(
            brand_frame,
            text="Avanture Automation",
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color="#f8fafc"
        )
        title.pack()

        subtitle = ctk.CTkLabel(
            brand_frame,
            text="Enterprise Classifieds Automation & RBAC Portal",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#64748b"
        )
        subtitle.pack(pady=(2, 0))

        # ---------------- LOGIN CARD ----------------
        card = ctk.CTkFrame(
            self,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
            corner_radius=14
        )
        card.pack(fill="x", padx=36, pady=6)
        card.grid_columnconfigure(0, weight=1)

        # Username Input
        u_lbl = ctk.CTkLabel(
            card,
            text="USERNAME",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        )
        u_lbl.grid(row=0, column=0, padx=24, pady=(18, 4), sticky="w")

        self.user_entry = ctk.CTkEntry(
            card,
            placeholder_text="Enter username",
            height=40,
            corner_radius=8,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            placeholder_text_color="#475569",
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.user_entry.grid(row=1, column=0, padx=24, pady=(0, 12), sticky="ew")
        self.user_entry.bind("<Return>", lambda e: self.pass_entry.focus_set())

        # Password Input
        p_lbl = ctk.CTkLabel(
            card,
            text="PASSWORD",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        )
        p_lbl.grid(row=2, column=0, padx=24, pady=(0, 4), sticky="w")

        self.pass_entry = ctk.CTkEntry(
            card,
            placeholder_text="Enter password",
            show="*",
            height=40,
            corner_radius=8,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            placeholder_text_color="#475569",
            font=ctk.CTkFont(family="Segoe UI", size=13)
        )
        self.pass_entry.grid(row=3, column=0, padx=24, pady=(0, 12), sticky="ew")
        self.pass_entry.bind("<Return>", lambda e: self._on_login())

        # Remember Me Checkbox
        self.remember_var = ctk.BooleanVar(value=True)
        self.remember_chk = ctk.CTkCheckBox(
            card,
            text="Remember my username & password",
            variable=self.remember_var,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#cbd5e1",
            fg_color="#4f46e5",
            hover_color="#4338ca",
            corner_radius=4,
            checkbox_width=18,
            checkbox_height=18
        )
        self.remember_chk.grid(row=4, column=0, padx=24, pady=(0, 16), sticky="w")

        # Submit Button
        self.login_btn = ctk.CTkButton(
            card,
            text="Sign In to Dashboard →",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            height=42,
            corner_radius=8,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            text_color="#ffffff",
            command=self._on_login
        )
        self.login_btn.grid(row=5, column=0, padx=24, pady=(0, 20), sticky="ew")

    def _load_remembered_credentials(self):
        saved_user, saved_pass, is_remembered = CredentialsStore.load()
        if is_remembered and saved_user:
            self.user_entry.insert(0, saved_user)
            self.pass_entry.insert(0, saved_pass)
            self.remember_var.set(True)

    def _on_login(self):
        username = self.user_entry.get().strip()
        password = self.pass_entry.get().strip()

        if not username or not password:
            messagebox.showwarning("Warning", "Please provide both username and password.")
            return

        ok, msg, user = self.db.authenticate(username, password)
        if not ok:
            messagebox.showerror("Access Denied", msg)
            return

        # Save or clear remembered credentials based on checkbox state
        if self.remember_var.get():
            CredentialsStore.save(username, password)
        else:
            CredentialsStore.clear()

        self.on_login_success(user)


class LoginWindow(ctk.CTk):
    """Standalone window fallback."""

    def __init__(self, on_login_success: Callable[[dict], None]):
        super().__init__()
        self.title("Avanture Automation - Sign In")
        self.geometry("460x590")
        self.resizable(False, False)
        self.configure(fg_color="#0a0e17")

        view = LoginView(self, on_login_success=lambda u: (self.destroy(), on_login_success(u)))
        view.pack(fill="both", expand=True)
