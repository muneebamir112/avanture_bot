import os
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import customtkinter as ctk
import pandas as pd

from config import DEFAULT_TARGET_URL, SESSION_FILE, DATA_DIR, AVANTURE_SLOVENIA_LOCATIONS
from core.validator import ListingValidator
from core.auth import AuthManager
from core.automation import AutomationWorker
from core.db import UserManager
from core.credentials_store import AvantureCredentialsStore
from ui.admin_panel import AdminManagementWindow

AVANTURE_CATEGORY_OPTIONS = [
    # Female categories (for accounts like venusxxx)
    "She seeks him (Ona išče njega)",
    "She seeks her (Ona išče njo)",
    "She seeks couple (Ona išče par)",
    "Female escort (Ona nudi spremstvo)",
    # Male categories (for male accounts)
    "He seeks her (On išče njo)",
    "He seeks him (On išče njega)",
    "He seeks couple (On išče par)",
    "Male escort (Moški spremljevalec)",
    # Shared categories
    "Seeking Trans (Iščem Trans)",
    "Dominant looking (Dominanten/a išče)",
    "Submissive looking (Submisiven/a išče)",
    "Switch looking (Switch išče)",
    "Kink & Fetish (Kink & Fetiš)",
    "Virtual (Virtualno)",
    "Only Fans",
    "Erotic massage (Erotične masaže)",
    "Serious relationship (Resne zveze)",
    "Short stay (Dnevni počitek)",
    "Sex toys (Erotične igračke)",
    "Events (Dogodki)",
    "Other (Ostalo)"
]

AVANTURE_COUNTRY_OPTIONS = [
    "Slovenia",
    "Croatia",
    "Austria",
    "Italy",
    "Bosnia and Herzegovina",
    "Serbia and Montenegro",
    "Hungary"
]

AVANTURE_STATE_OPTIONS = list(AVANTURE_SLOVENIA_LOCATIONS.keys())


class DashboardView(ctk.CTkFrame):
    """High-performance multi-page dashboard for Avanture Classifieds automation."""

    def __init__(self, master, current_user: dict, on_logout: callable = None):
        super().__init__(master, fg_color="transparent")

        self.current_user = current_user
        self.on_logout = on_logout
        self.db = UserManager()

        self.auth_manager = AuthManager()
        self.worker: AutomationWorker | None = None
        self.worker_thread: threading.Thread | None = None
        self.current_df: pd.DataFrame | None = None
        self.selected_file_path: str | None = None
        self.admin_window: AdminManagementWindow | None = None

        # Dynamic Profiles data store
        self.profiles_list = []
        self.current_profile_index = 0

        # Metrics
        self.total_count = 0
        self.success_count = 0
        self.fail_count = 0

        self._load_saved_data()
        self._build_ui()
        self._show_page("runner")
        self._update_auth_status()
        self.after(4000, self._check_live_access_status)

    def _load_saved_data(self):
        loaded_profiles, proxy, img_path = AvantureCredentialsStore.load()
        self.profiles_list = loaded_profiles if isinstance(loaded_profiles, list) and loaded_profiles else [loaded_profiles]
        self.current_profile_index = 0
        # Fallback template auto-load
        default_file = DATA_DIR / "sample_listings_template.xlsx"
        if default_file.exists():
            valid, msg, df = ListingValidator.load_data(str(default_file))
            if valid and len(df) > 0:
                self.current_df = df

    def _build_ui(self):
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # ==============================================================
        # 1. TOP NAVBAR / PROFILE & PAGE SWITCHER BAR
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
        nav_left.grid(row=0, column=0, padx=16, pady=10, sticky="w")

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
            text="Classifieds Automation System",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#f8fafc"
        )
        title_sub.pack(side="left")

        # User meta
        is_super = (self.current_user.get("role") == "SUPER_ADMIN")
        user_meta = ctk.CTkFrame(nav_left, fg_color="transparent")
        user_meta.pack(anchor="w", pady=(2, 0))

        u_label = ctk.CTkLabel(
            user_meta,
            text=f"Operator: {self.current_user.get('username')}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        )
        u_label.pack(side="left", padx=(0, 6))

        role_tag = ctk.CTkLabel(
            user_meta,
            text="SUPER ADMIN" if is_super else "ADMIN OPERATOR",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color="#312e81" if is_super else "#0c4a6e",
            text_color="#a5b4fc" if is_super else "#7dd3fc",
            corner_radius=4,
            padx=6,
            pady=1
        )
        role_tag.pack(side="left")

        # Center Navigation Tabs
        nav_center = ctk.CTkFrame(nav_card, fg_color="transparent")
        nav_center.grid(row=0, column=1, padx=10, pady=10)

        self.btn_nav_runner = ctk.CTkButton(
            nav_center,
            text="🚀 Automation Runner",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=34,
            corner_radius=8,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            text_color="#ffffff",
            command=lambda: self._show_page("runner")
        )
        self.btn_nav_runner.pack(side="left", padx=5)

        self.btn_nav_profile = ctk.CTkButton(
            nav_center,
            text="⚙️ Profile Management",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            height=34,
            corner_radius=8,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#cbd5e1",
            command=lambda: self._show_page("profile")
        )
        self.btn_nav_profile.pack(side="left", padx=5)

        # Right Actions
        nav_right = ctk.CTkFrame(nav_card, fg_color="transparent")
        nav_right.grid(row=0, column=2, padx=16, pady=10, sticky="e")

        if is_super:
            self.manage_admins_btn = ctk.CTkButton(
                nav_right,
                text="🛡️ Access Control",
                font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                fg_color="#312e81",
                hover_color="#3730a3",
                height=30,
                corner_radius=6,
                command=self._on_click_manage_admins
            )
            self.manage_admins_btn.pack(side="left", padx=5)

        self.auth_badge = ctk.CTkLabel(
            nav_right,
            text="Checking session...",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            corner_radius=6,
            padx=8,
            pady=4
        )
        self.auth_badge.pack(side="left", padx=5)

        self.logout_btn = ctk.CTkButton(
            nav_right,
            text="Sign Out",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            width=65,
            height=30,
            corner_radius=6,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#cbd5e1",
            command=self._on_click_logout
        )
        self.logout_btn.pack(side="left", padx=(5, 0))

        # ==============================================================
        # 2. MAIN CONTAINER FOR PAGES
        # ==============================================================
        self.page_container = ctk.CTkFrame(self, fg_color="transparent")
        self.page_container.grid(row=1, column=0, padx=20, pady=(0, 16), sticky="nsew")
        self.page_container.grid_columnconfigure(0, weight=1)
        self.page_container.grid_rowconfigure(0, weight=1)

        # Page 1: Automation Runner
        self.page_runner = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self._build_runner_page()

        # Page 2: Profile Management
        self.page_profile = ctk.CTkFrame(self.page_container, fg_color="transparent")
        self._build_profile_page()

    def _show_page(self, page_name: str):
        if page_name == "runner":
            self.page_profile.pack_forget()
            self.page_runner.pack(fill="both", expand=True)
            self.btn_nav_runner.configure(fg_color="#4f46e5", text_color="#ffffff")
            self.btn_nav_profile.configure(fg_color="#1e293b", text_color="#94a3b8")
            self._update_runner_summary()
        elif page_name == "profile":
            self.page_runner.pack_forget()
            self.page_profile.pack(fill="both", expand=True)
            self.btn_nav_runner.configure(fg_color="#1e293b", text_color="#94a3b8")
            self.btn_nav_profile.configure(fg_color="#4f46e5", text_color="#ffffff")
            self._load_account_to_ui()

    # ==================================================================
    # PAGE 1: AUTOMATION RUNNER (One Button + Audit Stream)
    # ==================================================================
    def _build_runner_page(self):
        self.page_runner.grid_columnconfigure(0, weight=1)
        self.page_runner.grid_rowconfigure(1, weight=1)

        # 1. Action Header Card
        action_card = ctk.CTkFrame(
            self.page_runner,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
            corner_radius=12
        )
        action_card.grid(row=0, column=0, pady=(0, 10), sticky="ew")

        # Row 0: Action Buttons, Headless toggle & Progress Bar
        row0 = ctk.CTkFrame(action_card, fg_color="transparent")
        row0.pack(fill="x", padx=16, pady=(12, 8))

        # Start button
        self.start_btn = ctk.CTkButton(
            row0,
            text="🚀 START AUTOMATION",
            height=42,
            width=210,
            corner_radius=8,
            fg_color="#10b981",
            hover_color="#059669",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._on_click_start
        )
        self.start_btn.pack(side="left", padx=(0, 10))

        # Stop button
        self.stop_btn = ctk.CTkButton(
            row0,
            text="⏹ Stop",
            height=42,
            width=85,
            corner_radius=8,
            fg_color="#ef4444",
            hover_color="#dc2626",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            state="disabled",
            command=self._on_click_stop
        )
        self.stop_btn.pack(side="left", padx=(0, 14))

        # Headless checkbox
        self.headless_var = ctk.BooleanVar(value=False)
        self.headless_chk = ctk.CTkCheckBox(
            row0,
            text="Silent (Headless)",
            variable=self.headless_var,
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        )
        self.headless_chk.pack(side="left", padx=(0, 16))

        # Progress block (Right aligned)
        progress_box = ctk.CTkFrame(row0, fg_color="transparent")
        progress_box.pack(side="right")

        self.progress_bar = ctk.CTkProgressBar(
            progress_box,
            width=220,
            height=12,
            corner_radius=6,
            fg_color="#1e293b",
            progress_color="#6366f1"
        )
        self.progress_bar.set(0)
        self.progress_bar.pack(side="left", padx=(0, 10))

        self.progress_lbl = ctk.CTkLabel(
            progress_box,
            text="0 / 0 (0%)",
            font=ctk.CTkFont(family="Consolas", size=11, weight="bold"),
            text_color="#cbd5e1",
            width=85
        )
        self.progress_lbl.pack(side="left")

        # Row 1: Dedicated Cycle & Auto-Stop Timer Configuration Bar
        row1 = ctk.CTkFrame(action_card, fg_color="#0d1526", corner_radius=8, border_width=1, border_color="#1e293b")
        row1.pack(fill="x", padx=16, pady=(0, 12))

        # Re-posting delay setting
        relist_box = ctk.CTkFrame(row1, fg_color="transparent")
        relist_box.pack(side="left", padx=(12, 6), pady=6)

        relist_lbl = ctk.CTkLabel(
            relist_box,
            text="🔄 Re-Post Delay:",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#38bdf8"
        )
        relist_lbl.pack(side="left", padx=(0, 6))

        self.relist_entry = ctk.CTkEntry(
            relist_box,
            width=50,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            justify="center"
        )
        self.relist_entry.insert(0, "15")
        self.relist_entry.pack(side="left", padx=(0, 6))

        self.relist_unit_var = ctk.StringVar(value="Minutes")
        self.relist_unit_menu = ctk.CTkOptionMenu(
            relist_box,
            values=["Minutes", "Hours", "Seconds"],
            variable=self.relist_unit_var,
            width=90,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=10)
        )
        self.relist_unit_menu.pack(side="left", padx=(0, 12))

        # Divider
        ctk.CTkLabel(row1, text="|", font=ctk.CTkFont(size=14), text_color="#334155").pack(side="left", padx=4)

        # Auto-Stop timer setting
        autostop_box = ctk.CTkFrame(row1, fg_color="transparent")
        autostop_box.pack(side="left", padx=(12, 6), pady=6)

        self.auto_stop_enabled_var = ctk.BooleanVar(value=False)
        self.auto_stop_chk = ctk.CTkCheckBox(
            autostop_box,
            text="Auto-Stop Timer:",
            variable=self.auto_stop_enabled_var,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#f59e0b"
        )
        self.auto_stop_chk.pack(side="left", padx=(0, 6))

        self.autostop_entry = ctk.CTkEntry(
            autostop_box,
            width=50,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            justify="center"
        )
        self.autostop_entry.insert(0, "8")
        self.autostop_entry.pack(side="left", padx=(0, 6))

        self.autostop_unit_var = ctk.StringVar(value="Hours")
        self.autostop_unit_menu = ctk.CTkOptionMenu(
            autostop_box,
            values=["Hours", "Minutes"],
            variable=self.autostop_unit_var,
            width=85,
            height=28,
            font=ctk.CTkFont(family="Segoe UI", size=10)
        )
        self.autostop_unit_menu.pack(side="left")

        # Live status summary label
        self.runner_summary_lbl = ctk.CTkLabel(
            row1,
            text="Mode: Non-Stop Auto-Cycle | Delete old ad → Post fresh ad",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        )
        self.runner_summary_lbl.pack(side="right", padx=14)

        # 2. Real-Time Audit Console (Full height)
        log_card = ctk.CTkFrame(
            self.page_runner,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
            corner_radius=12
        )
        log_card.grid(row=1, column=0, sticky="nsew")
        log_card.grid_columnconfigure(0, weight=1)
        log_card.grid_rowconfigure(1, weight=1)

        log_top = ctk.CTkFrame(log_card, fg_color="transparent")
        log_top.grid(row=0, column=0, padx=16, pady=(10, 6), sticky="ew")
        log_top.grid_columnconfigure(0, weight=1)

        console_title = ctk.CTkLabel(
            log_top,
            text="📟 Real-Time Activity & Automation Stream",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#94a3b8"
        )
        console_title.grid(row=0, column=0, sticky="w")

        btn_box = ctk.CTkFrame(log_top, fg_color="transparent")
        btn_box.grid(row=0, column=1, sticky="e")

        clear_btn = ctk.CTkButton(
            btn_box,
            text="Clear Logs",
            height=26,
            width=75,
            corner_radius=6,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#cbd5e1",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._on_clear_logs
        )
        clear_btn.pack(side="left", padx=(0, 6))

        export_btn = ctk.CTkButton(
            btn_box,
            text="Export Results Report",
            height=26,
            corner_radius=6,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._on_export_results
        )
        export_btn.pack(side="left")

        self.log_textbox = ctk.CTkTextbox(
            log_card,
            corner_radius=8,
            fg_color="#0a0e17",
            text_color="#e2e8f0",
            font=ctk.CTkFont(family="Consolas", size=11),
            wrap="word"
        )
        self.log_textbox.grid(row=1, column=0, padx=16, pady=(0, 14), sticky="nsew")

    def _update_runner_summary(self):
        active = [p for p in self.profiles_list if p.get("username", "").strip() and p.get("password", "").strip()]
        total = len(self.profiles_list)
        names = ", ".join([p.get("username", "").strip() for p in active]) if active else "None"
        self.runner_summary_lbl.configure(
            text=f"Active Profiles ({len(active)}/{total}): {names} | ⏱️ 5s delay between accounts"
        )
        self.progress_lbl.configure(text=f"0 / {len(active)} (0%)")

    # ==================================================================
    # PAGE 2: PROFILE & LISTING MANAGEMENT (Dynamic Profiles & Avanture Form)
    # ==================================================================
    def _get_profile_menu_labels(self) -> list:
        labels = []
        for i, p in enumerate(self.profiles_list):
            u = p.get("username", "").strip()
            custom = p.get("profile_name", "").strip()
            if custom:
                labels.append(f"{i + 1}. {custom}")
            elif u:
                labels.append(f"{i + 1}. {u}")
            else:
                labels.append(f"{i + 1}. Profile (Empty)")
        return labels if labels else ["1. Profile 1"]

    def _refresh_profile_dropdown(self):
        labels = self._get_profile_menu_labels()
        self.profile_select_menu.configure(values=labels)
        if 0 <= self.current_profile_index < len(labels):
            self.profile_select_menu.set(labels[self.current_profile_index])
        elif labels:
            self.current_profile_index = 0
            self.profile_select_menu.set(labels[0])
        self.profile_count_lbl.configure(text=f"Total Profiles: {len(self.profiles_list)}")
        self._update_runner_summary()

    def _on_select_profile_dropdown(self, choice: str):
        self._save_current_account_form(silent=True)
        labels = self._get_profile_menu_labels()
        if choice in labels:
            self.current_profile_index = labels.index(choice)
        self._load_account_to_ui()

    def _on_add_new_profile(self):
        self._save_current_account_form(silent=True)
        idx = len(self.profiles_list) + 1
        base_p = self.profiles_list[0] if self.profiles_list else {}
        new_prof = {
            "profile_name": f"Profile {idx}",
            "username": "",
            "password": "",
            "proxy": base_p.get("proxy", ""),
            "proxy_protocol": base_p.get("proxy_protocol", "HTTP"),
            "proxy_host": base_p.get("proxy_host", ""),
            "proxy_port": base_p.get("proxy_port", ""),
            "proxy_login": base_p.get("proxy_login", ""),
            "proxy_password": base_p.get("proxy_password", ""),
            "proxy_name": "",
            "proxy_change_ip_link": "",
            "title": "A relaxed evening for two in Ljubljana",
            "category": AVANTURE_CATEGORY_OPTIONS[0],
            "description": "Looking for a pleasant, mature company for dinner, wine, and casual conversation. Polite and respectful gentleman.",
            "country": "Slovenia",
            "state": "Osrednjeslovenska",
            "city": "Ljubljana",
            "registration_number": "",
            "image_path": ""
        }
        self.profiles_list.append(new_prof)
        self.current_profile_index = len(self.profiles_list) - 1
        AvantureCredentialsStore.save(self.profiles_list)
        self._refresh_profile_dropdown()
        self._load_account_to_ui()
        self.log(f"Created new profile: 'Profile {idx}'. Enter credentials and ad details.", "SUCCESS")
        self.form_user.focus_set()

    def _on_delete_current_profile(self):
        if len(self.profiles_list) <= 1:
            messagebox.showwarning("Cannot Delete", "At least one profile must be kept in the system.")
            return

        cur = self.profiles_list[self.current_profile_index]
        name = cur.get("profile_name") or cur.get("username") or f"Profile {self.current_profile_index + 1}"
        if not messagebox.askyesno("Delete Profile", f"Are you sure you want to delete '{name}'?\nThis action cannot be undone."):
            return

        del self.profiles_list[self.current_profile_index]
        if self.current_profile_index >= len(self.profiles_list):
            self.current_profile_index = len(self.profiles_list) - 1

        AvantureCredentialsStore.save(self.profiles_list)
        self._refresh_profile_dropdown()
        self._load_account_to_ui()
        self.log(f"Profile '{name}' deleted.", "INFO")

    def _on_duplicate_current_profile(self):
        self._save_current_account_form(silent=True)
        src = self.profiles_list[self.current_profile_index]
        clone = dict(src)
        idx = len(self.profiles_list) + 1
        src_tag = src.get("username") or src.get("profile_name") or "Ad"
        clone["profile_name"] = f"Profile {idx} (Copy of {src_tag})"
        clone["username"] = ""
        clone["password"] = ""

        self.profiles_list.append(clone)
        self.current_profile_index = len(self.profiles_list) - 1
        AvantureCredentialsStore.save(self.profiles_list)
        self._refresh_profile_dropdown()
        self._load_account_to_ui()
        self.log(f"Cloned listing into '{clone['profile_name']}'. Enter the account credentials.", "SUCCESS")
        self.form_user.focus_set()

    def _build_profile_page(self):
        self.page_profile.grid_columnconfigure(0, weight=1)
        self.page_profile.grid_rowconfigure(1, weight=1)

        # Top Dynamic Profiles Header & Control Bar
        top_bar = ctk.CTkFrame(
            self.page_profile,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
            corner_radius=12
        )
        top_bar.grid(row=0, column=0, pady=(0, 10), sticky="ew")
        top_bar.grid_columnconfigure(1, weight=1)

        # Left Controls: Selector + Add / Delete / Duplicate Buttons
        left_ctrls = ctk.CTkFrame(top_bar, fg_color="transparent")
        left_ctrls.grid(row=0, column=0, padx=14, pady=10, sticky="w")

        p_lbl = ctk.CTkLabel(
            left_ctrls,
            text="👤 Profile:",
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            text_color="#e2e8f0"
        )
        p_lbl.pack(side="left", padx=(0, 6))

        self.profile_select_menu = ctk.CTkOptionMenu(
            left_ctrls,
            values=self._get_profile_menu_labels(),
            width=210,
            height=32,
            corner_radius=6,
            fg_color="#1e293b",
            button_color="#334155",
            button_hover_color="#475569",
            text_color="#f8fafc",
            dropdown_fg_color="#1e293b",
            dropdown_text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._on_select_profile_dropdown
        )
        self.profile_select_menu.pack(side="left", padx=(0, 6))

        self.btn_add_profile = ctk.CTkButton(
            left_ctrls,
            text="➕ Add Profile",
            height=32,
            width=105,
            corner_radius=6,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._on_add_new_profile
        )
        self.btn_add_profile.pack(side="left", padx=(0, 5))

        self.btn_del_profile = ctk.CTkButton(
            left_ctrls,
            text="🗑️ Delete",
            height=32,
            width=75,
            corner_radius=6,
            fg_color="#dc2626",
            hover_color="#b91c1c",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._on_delete_current_profile
        )
        self.btn_del_profile.pack(side="left", padx=(0, 5))

        self.btn_dup_profile = ctk.CTkButton(
            left_ctrls,
            text="📋 Duplicate",
            height=32,
            width=85,
            corner_radius=6,
            fg_color="#0284c7",
            hover_color="#0369a1",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._on_duplicate_current_profile
        )
        self.btn_dup_profile.pack(side="left")

        # Right Actions: Count & Save Button
        right_ctrls = ctk.CTkFrame(top_bar, fg_color="transparent")
        right_ctrls.grid(row=0, column=2, padx=14, pady=10, sticky="e")

        self.profile_count_lbl = ctk.CTkLabel(
            right_ctrls,
            text=f"Total Profiles: {len(self.profiles_list)}",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8"
        )
        self.profile_count_lbl.pack(side="left", padx=(0, 10))

        save_btn = ctk.CTkButton(
            right_ctrls,
            text="💾 Save Profile Settings",
            height=32,
            corner_radius=6,
            fg_color="#10b981",
            hover_color="#059669",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._save_current_account_form
        )
        save_btn.pack(side="left")

        # Scrollable / Two-Column Form Area
        form_scroll = ctk.CTkScrollableFrame(
            self.page_profile,
            fg_color="transparent",
            corner_radius=0
        )
        form_scroll.grid(row=1, column=0, sticky="nsew")
        form_scroll.grid_columnconfigure(0, weight=1)
        form_scroll.grid_columnconfigure(1, weight=2)

        # -------------------------------------------------------------
        # Left Card 1: Account Credentials
        # -------------------------------------------------------------
        creds_card = ctk.CTkFrame(
            form_scroll,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
            corner_radius=12
        )
        creds_card.grid(row=0, column=0, padx=(0, 6), pady=(0, 10), sticky="new")
        creds_card.grid_columnconfigure(0, weight=1)

        creds_title = ctk.CTkLabel(
            creds_card,
            text="🔐 Avanture Account Credentials",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#e2e8f0"
        )
        creds_title.pack(anchor="w", padx=16, pady=(14, 10))

        # Profile Label / Alias
        lbl_field = ctk.CTkLabel(
            creds_card,
            text="Profile Label / Alias",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        )
        lbl_field.pack(anchor="w", padx=16, pady=(4, 2))

        self.form_label = ctk.CTkEntry(
            creds_card,
            placeholder_text="e.g. Venus Account (Main)",
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.form_label.pack(fill="x", padx=16, pady=(0, 8))
        self.form_label.bind("<KeyRelease>", lambda e: self._on_label_key())

        # Username
        u_lbl = ctk.CTkLabel(
            creds_card,
            text="Username / Email *",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        )
        u_lbl.pack(anchor="w", padx=16, pady=(4, 2))

        self.form_user = ctk.CTkEntry(
            creds_card,
            placeholder_text="e.g. venusxxx",
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.form_user.pack(fill="x", padx=16, pady=(0, 8))
        self.form_user.bind("<KeyRelease>", lambda e: self._on_field_change())

        # Password
        p_lbl = ctk.CTkLabel(
            creds_card,
            text="Password *",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        )
        p_lbl.pack(anchor="w", padx=16, pady=(4, 2))

        self.form_pass = ctk.CTkEntry(
            creds_card,
            placeholder_text="Password",
            show="*",
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.form_pass.pack(fill="x", padx=16, pady=(0, 14))
        self.form_pass.bind("<KeyRelease>", lambda e: self._on_field_change())

        # -------------------------------------------------------------
        # Left Card 2: Dynamic Proxy Configuration (Anti-Detect & Rotation)
        # -------------------------------------------------------------
        proxy_card = ctk.CTkFrame(
            form_scroll,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
            corner_radius=12
        )
        proxy_card.grid(row=1, column=0, padx=(0, 6), pady=(0, 10), sticky="new")
        proxy_card.grid_columnconfigure(0, weight=1)

        p_hdr = ctk.CTkFrame(proxy_card, fg_color="transparent")
        p_hdr.pack(fill="x", padx=16, pady=(14, 8))

        ctk.CTkLabel(
            p_hdr,
            text="🌐 Proxy Configuration",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#e2e8f0"
        ).pack(side="left")

        quick_paste_btn = ctk.CTkButton(
            p_hdr,
            text="📋 Paste Full String",
            width=110,
            height=24,
            corner_radius=6,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#94a3b8",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            command=self._on_quick_paste_proxy
        )
        quick_paste_btn.pack(side="right")

        # 1. Protocol Selector Tabs [HTTP, SOCKS4, SOCKS5, SSH]
        self.form_proxy_protocol = ctk.CTkSegmentedButton(
            proxy_card,
            values=["HTTP", "SOCKS4", "SOCKS5", "SSH"],
            selected_color="#2563eb",
            selected_hover_color="#1d4ed8",
            unselected_color="#1e293b",
            unselected_hover_color="#334155",
            text_color="#f8fafc",
            height=32,
            corner_radius=6,
            command=lambda v: self._on_field_change()
        )
        self.form_proxy_protocol.pack(fill="x", padx=16, pady=(2, 10))
        self.form_proxy_protocol.set("HTTP")

        # 2. Host & Port (2 Columns)
        hp_row = ctk.CTkFrame(proxy_card, fg_color="transparent")
        hp_row.pack(fill="x", padx=16, pady=(0, 8))
        hp_row.grid_columnconfigure(0, weight=3)
        hp_row.grid_columnconfigure(1, weight=2)

        # Host
        h_frame = ctk.CTkFrame(hp_row, fg_color="transparent")
        h_frame.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkLabel(
            h_frame,
            text="Host",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).pack(anchor="w", pady=(0, 2))
        self.form_proxy_host = ctk.CTkEntry(
            h_frame,
            placeholder_text="194.31.182.67",
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.form_proxy_host.pack(fill="x")
        self.form_proxy_host.bind("<KeyRelease>", lambda e: self._on_proxy_host_key(e))

        # Port
        p_frame = ctk.CTkFrame(hp_row, fg_color="transparent")
        p_frame.grid(row=0, column=1, padx=(4, 0), sticky="ew")
        ctk.CTkLabel(
            p_frame,
            text="Port",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).pack(anchor="w", pady=(0, 2))
        self.form_proxy_port = ctk.CTkEntry(
            p_frame,
            placeholder_text="12323",
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.form_proxy_port.pack(fill="x")
        self.form_proxy_port.bind("<KeyRelease>", lambda e: self._on_field_change())

        # 3. Login & Password (2 Columns)
        lp_row = ctk.CTkFrame(proxy_card, fg_color="transparent")
        lp_row.pack(fill="x", padx=16, pady=(0, 8))
        lp_row.grid_columnconfigure(0, weight=1)
        lp_row.grid_columnconfigure(1, weight=1)

        # Login
        l_frame = ctk.CTkFrame(lp_row, fg_color="transparent")
        l_frame.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        ctk.CTkLabel(
            l_frame,
            text="Login",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).pack(anchor="w", pady=(0, 2))
        self.form_proxy_user = ctk.CTkEntry(
            l_frame,
            placeholder_text="14a17d6e203a3",
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.form_proxy_user.pack(fill="x")
        self.form_proxy_user.bind("<KeyRelease>", lambda e: self._on_field_change())

        # Password
        pwd_frame = ctk.CTkFrame(lp_row, fg_color="transparent")
        pwd_frame.grid(row=0, column=1, padx=(4, 0), sticky="ew")
        ctk.CTkLabel(
            pwd_frame,
            text="Password",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).pack(anchor="w", pady=(0, 2))
        self.form_proxy_pass = ctk.CTkEntry(
            pwd_frame,
            placeholder_text="c60c979201",
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.form_proxy_pass.pack(fill="x")
        self.form_proxy_pass.bind("<KeyRelease>", lambda e: self._on_field_change())

        # 4. Proxy Name (Optional)
        pn_frame = ctk.CTkFrame(proxy_card, fg_color="transparent")
        pn_frame.pack(fill="x", padx=16, pady=(0, 8))
        ctk.CTkLabel(
            pn_frame,
            text="Proxy name",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).pack(anchor="w", pady=(0, 2))
        self.form_proxy_name = ctk.CTkEntry(
            pn_frame,
            placeholder_text="Carolina / Venus",
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.form_proxy_name.pack(fill="x")
        self.form_proxy_name.bind("<KeyRelease>", lambda e: self._on_field_change())
        ctk.CTkLabel(
            pn_frame,
            text="Optional",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#64748b"
        ).pack(anchor="w", pady=(2, 0))

        # 5. IP change link (Optional)
        ipc_frame = ctk.CTkFrame(proxy_card, fg_color="transparent")
        ipc_frame.pack(fill="x", padx=16, pady=(0, 10))

        ipc_top = ctk.CTkFrame(ipc_frame, fg_color="transparent")
        ipc_top.pack(fill="x", pady=(0, 2))
        ctk.CTkLabel(
            ipc_top,
            text="🔄 IP change link",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).pack(side="left")

        rotate_btn = ctk.CTkButton(
            ipc_top,
            text="Rotate Now",
            width=70,
            height=20,
            corner_radius=4,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#38bdf8",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            command=self._on_trigger_ip_change
        )
        rotate_btn.pack(side="right")

        self.form_proxy_change_link = ctk.CTkEntry(
            ipc_frame,
            placeholder_text="https://mobileproxy.example/change-ip-url",
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.form_proxy_change_link.pack(fill="x")
        self.form_proxy_change_link.bind("<KeyRelease>", lambda e: self._on_field_change())
        ctk.CTkLabel(
            ipc_frame,
            text="Optional rotation URL for mobile / dynamic proxy endpoints",
            font=ctk.CTkFont(family="Segoe UI", size=9),
            text_color="#64748b"
        ).pack(anchor="w", pady=(2, 0))

        # 6. Bottom Action Bar: CHECK CONNECTION Button & Status Badge
        action_bar = ctk.CTkFrame(proxy_card, fg_color="transparent")
        action_bar.pack(fill="x", padx=16, pady=(4, 16))

        self.btn_check_proxy = ctk.CTkButton(
            action_bar,
            text="⇄ CHECK CONNECTION",
            height=34,
            corner_radius=6,
            fg_color="#1e293b",
            hover_color="#1e3a8a",
            border_width=1,
            border_color="#3b82f6",
            text_color="#60a5fa",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._on_check_proxy_click
        )
        self.btn_check_proxy.pack(side="left", padx=(0, 10))

        self.proxy_status_badge = ctk.CTkLabel(
            action_bar,
            text="ACTIVE",
            height=32,
            corner_radius=6,
            fg_color="#052e16",
            text_color="#22c55e",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            padx=16
        )
        self.proxy_status_badge.pack(side="right")

        # -------------------------------------------------------------
        # Right Card: Listing Form (Matches Avanture Edit Page)
        # -------------------------------------------------------------
        listing_card = ctk.CTkFrame(
            form_scroll,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
            corner_radius=12
        )
        listing_card.grid(row=0, column=1, rowspan=2, padx=(6, 0), sticky="nsew")
        listing_card.grid_columnconfigure(0, weight=1)

        listing_title = ctk.CTkLabel(
            listing_card,
            text="📝 Avanture Listing Form (Matches https://www.avanture.net/classifieds/edit)",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color="#e2e8f0"
        )
        listing_title.pack(anchor="w", padx=16, pady=(14, 10))

        # Title Field
        t_header = ctk.CTkFrame(listing_card, fg_color="transparent")
        t_header.pack(fill="x", padx=16, pady=(2, 2))
        ctk.CTkLabel(
            t_header,
            text="Title *",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).pack(side="left")
        self.title_count_lbl = ctk.CTkLabel(
            t_header,
            text="0 / 50",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#64748b"
        )
        self.title_count_lbl.pack(side="right")

        self.form_title = ctk.CTkEntry(
            listing_card,
            placeholder_text="e.g. A relaxed evening for two",
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.form_title.pack(fill="x", padx=16, pady=(0, 8))
        self.form_title.bind("<KeyRelease>", lambda e: self._on_title_key())

        # Category Dropdown
        cat_lbl = ctk.CTkLabel(
            listing_card,
            text="Category * (Categories allowed for your profile)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        )
        cat_lbl.pack(anchor="w", padx=16, pady=(4, 2))

        self.form_category = ctk.CTkOptionMenu(
            listing_card,
            values=AVANTURE_CATEGORY_OPTIONS,
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            button_color="#334155",
            button_hover_color="#475569",
            text_color="#f8fafc",
            dropdown_fg_color="#1e293b",
            dropdown_text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=lambda v: self._on_field_change()
        )
        self.form_category.pack(fill="x", padx=16, pady=(0, 8))

        # Description Field
        d_header = ctk.CTkFrame(listing_card, fg_color="transparent")
        d_header.pack(fill="x", padx=16, pady=(2, 2))
        ctk.CTkLabel(
            d_header,
            text="Description *",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).pack(side="left")
        self.desc_count_lbl = ctk.CTkLabel(
            d_header,
            text="0 / 1000",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color="#64748b"
        )
        self.desc_count_lbl.pack(side="right")

        self.form_desc = ctk.CTkTextbox(
            listing_card,
            height=90,
            corner_radius=6,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            wrap="word"
        )
        self.form_desc.pack(fill="x", padx=16, pady=(0, 8))
        self.form_desc.bind("<KeyRelease>", lambda e: self._on_desc_key())

        # Location Row (Country, State, City)
        loc_row = ctk.CTkFrame(listing_card, fg_color="transparent")
        loc_row.pack(fill="x", padx=16, pady=(4, 8))
        loc_row.grid_columnconfigure(0, weight=1)
        loc_row.grid_columnconfigure(1, weight=1)
        loc_row.grid_columnconfigure(2, weight=1)

        # Country
        ctk.CTkLabel(
            loc_row,
            text="Country",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).grid(row=0, column=0, padx=(0, 4), sticky="w")

        self.form_country = ctk.CTkOptionMenu(
            loc_row,
            values=AVANTURE_COUNTRY_OPTIONS,
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            button_color="#334155",
            button_hover_color="#475569",
            text_color="#f8fafc",
            dropdown_fg_color="#1e293b",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=lambda v: self._on_field_change()
        )
        self.form_country.grid(row=1, column=0, padx=(0, 4), pady=(2, 0), sticky="ew")

        # State
        ctk.CTkLabel(
            loc_row,
            text="State / Region",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).grid(row=0, column=1, padx=(4, 4), sticky="w")

        self.form_state = ctk.CTkOptionMenu(
            loc_row,
            values=AVANTURE_STATE_OPTIONS,
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            button_color="#334155",
            button_hover_color="#475569",
            text_color="#f8fafc",
            dropdown_fg_color="#1e293b",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=self._on_state_change
        )
        self.form_state.grid(row=1, column=1, padx=(4, 4), pady=(2, 0), sticky="ew")

        # City Dropdown (Scraped from Avanture)
        ctk.CTkLabel(
            loc_row,
            text="City",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).grid(row=0, column=2, padx=(4, 0), sticky="w")

        initial_cities = AVANTURE_SLOVENIA_LOCATIONS.get("Osrednjeslovenska", ["Ljubljana"])
        self.form_city = ctk.CTkOptionMenu(
            loc_row,
            values=initial_cities,
            height=32,
            corner_radius=6,
            fg_color="#0f172a",
            button_color="#334155",
            button_hover_color="#475569",
            text_color="#f8fafc",
            dropdown_fg_color="#1e293b",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            command=lambda v: self._on_field_change()
        )
        self.form_city.grid(row=1, column=2, padx=(4, 0), pady=(2, 0), sticky="ew")

        # Registry number (Erotic massage)
        reg_lbl = ctk.CTkLabel(
            listing_card,
            text="Registry number (Required by law for Erotic massage / Erotične masaže)",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        )
        reg_lbl.pack(anchor="w", padx=16, pady=(4, 2))

        self.form_reg = ctk.CTkEntry(
            listing_card,
            placeholder_text="1234567000",
            height=30,
            corner_radius=6,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=11)
        )
        self.form_reg.pack(fill="x", padx=16, pady=(0, 8))
        self.form_reg.bind("<KeyRelease>", lambda e: self._on_field_change())

        # Picture Upload Row
        pic_box = ctk.CTkFrame(listing_card, fg_color="transparent")
        pic_box.pack(fill="x", padx=16, pady=(6, 16))

        self.btn_pic = ctk.CTkButton(
            pic_box,
            text="📁 Attach Listing Picture",
            height=32,
            corner_radius=6,
            fg_color="#4f46e5",
            hover_color="#4338ca",
            text_color="#ffffff",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            command=self._on_browse_profile_image
        )
        self.btn_pic.pack(side="left", padx=(0, 8))

        self.lbl_pic = ctk.CTkLabel(
            pic_box,
            text="No picture attached (Optional)",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#64748b"
        )
        self.lbl_pic.pack(side="left")

        self.btn_clear_pic = ctk.CTkButton(
            pic_box,
            text="✕",
            width=28,
            height=28,
            corner_radius=6,
            fg_color="#1e293b",
            hover_color="#ef4444",
            text_color="#94a3b8",
            command=self._on_clear_profile_image
        )
        self.btn_clear_pic.pack(side="left", padx=(8, 0))

    # ==================================================================
    # FORM EVENT HANDLERS & PROFILE DATA BINDING
    # ==================================================================
    def _on_label_key(self):
        if 0 <= self.current_profile_index < len(self.profiles_list):
            self.profiles_list[self.current_profile_index]["profile_name"] = self.form_label.get().strip()
            self._save_current_account_form(silent=True)
            labels = self._get_profile_menu_labels()
            self.profile_select_menu.configure(values=labels)
            self.profile_select_menu.set(labels[self.current_profile_index])

    def _load_account_to_ui(self):
        if not (0 <= self.current_profile_index < len(self.profiles_list)):
            return

        acc = self.profiles_list[self.current_profile_index]

        # Profile Label
        if hasattr(self, "form_label"):
            self.form_label.delete(0, "end")
            self.form_label.insert(0, acc.get("profile_name", ""))

        # Credentials
        self.form_user.delete(0, "end")
        self.form_user.insert(0, acc.get("username", ""))

        self.form_pass.delete(0, "end")
        self.form_pass.insert(0, acc.get("password", ""))

        # Proxy settings
        proto = acc.get("proxy_protocol", "HTTP")
        if hasattr(self, "form_proxy_protocol"):
            if proto in ["HTTP", "SOCKS4", "SOCKS5", "SSH"]:
                self.form_proxy_protocol.set(proto)
            else:
                self.form_proxy_protocol.set("HTTP")

        if hasattr(self, "form_proxy_host"):
            self.form_proxy_host.delete(0, "end")
            self.form_proxy_host.insert(0, acc.get("proxy_host", ""))

        if hasattr(self, "form_proxy_port"):
            self.form_proxy_port.delete(0, "end")
            self.form_proxy_port.insert(0, str(acc.get("proxy_port", "")))

        if hasattr(self, "form_proxy_user"):
            self.form_proxy_user.delete(0, "end")
            self.form_proxy_user.insert(0, acc.get("proxy_login", ""))

        if hasattr(self, "form_proxy_pass"):
            self.form_proxy_pass.delete(0, "end")
            self.form_proxy_pass.insert(0, acc.get("proxy_password", ""))

        if hasattr(self, "form_proxy_name"):
            self.form_proxy_name.delete(0, "end")
            self.form_proxy_name.insert(0, acc.get("proxy_name", ""))

        if hasattr(self, "form_proxy_change_link"):
            self.form_proxy_change_link.delete(0, "end")
            self.form_proxy_change_link.insert(0, acc.get("proxy_change_ip_link", ""))

        # Proxy connection badge initial state
        if acc.get("proxy_host"):
            self._set_proxy_badge("READY TO CHECK", color="#94a3b8", bg="#1e293b")
        else:
            self._set_proxy_badge("NO PROXY", color="#64748b", bg="#1e293b")

        # Listing fields
        self.form_title.delete(0, "end")
        self.form_title.insert(0, acc.get("title", ""))

        cat = acc.get("category", "She seeks him (Ona išče njega)")
        if cat in AVANTURE_CATEGORY_OPTIONS:
            self.form_category.set(cat)
        else:
            matched = False
            for opt in AVANTURE_CATEGORY_OPTIONS:
                if cat.lower() in opt.lower() or opt.lower() in cat.lower():
                    self.form_category.set(opt)
                    matched = True
                    break
            if not matched:
                self.form_category.set(AVANTURE_CATEGORY_OPTIONS[0])

        self.form_desc.delete("1.0", "end")
        self.form_desc.insert("1.0", acc.get("description", ""))

        country = acc.get("country", "Slovenia")
        if country in AVANTURE_COUNTRY_OPTIONS:
            self.form_country.set(country)
        else:
            self.form_country.set(AVANTURE_COUNTRY_OPTIONS[0])

        state = acc.get("state", "Osrednjeslovenska")
        if state not in AVANTURE_STATE_OPTIONS:
            state = AVANTURE_STATE_OPTIONS[0]
        self.form_state.set(state)

        # Populate city dropdown for this state
        cities = AVANTURE_SLOVENIA_LOCATIONS.get(state, ["Ljubljana"])
        self.form_city.configure(values=cities)
        saved_city = acc.get("city", "Ljubljana")
        if saved_city in cities:
            self.form_city.set(saved_city)
        else:
            self.form_city.set(cities[0])

        self.form_reg.delete(0, "end")
        self.form_reg.insert(0, acc.get("registration_number", ""))

        img_path = acc.get("image_path", "")
        if img_path and Path(img_path).exists():
            self.lbl_pic.configure(text=f"Attached: {Path(img_path).name}", text_color="#38bdf8")
        else:
            self.lbl_pic.configure(text="No picture attached (Optional)", text_color="#64748b")

        self._on_title_key()
        self._on_desc_key()

    def _set_proxy_badge(self, text: str, color: str = "#22c55e", bg: str = "#052e16"):
        if hasattr(self, "proxy_status_badge"):
            self.proxy_status_badge.configure(text=text, text_color=color, fg_color=bg)

    def _on_proxy_host_key(self, event):
        val = self.form_proxy_host.get().strip()
        if ("://" in val or val.count(":") >= 2) and hasattr(self, "form_proxy_port"):
            parsed = AvantureCredentialsStore.parse_proxy_components(val)
            if parsed.get("host") and parsed.get("port"):
                self.form_proxy_host.delete(0, "end")
                self.form_proxy_host.insert(0, parsed["host"])
                self.form_proxy_port.delete(0, "end")
                self.form_proxy_port.insert(0, parsed["port"])
                if parsed.get("login"):
                    self.form_proxy_user.delete(0, "end")
                    self.form_proxy_user.insert(0, parsed["login"])
                if parsed.get("password"):
                    self.form_proxy_pass.delete(0, "end")
                    self.form_proxy_pass.insert(0, parsed["password"])
                if parsed.get("protocol"):
                    self.form_proxy_protocol.set(parsed["protocol"])
        self._on_field_change()

    def _on_quick_paste_proxy(self):
        prompt = ctk.CTkInputDialog(
            text="Paste proxy string:\n(e.g. 194.31.182.67:12323:user:pass or http://user:pass@host:port)",
            title="Paste Proxy Configuration"
        )
        val = prompt.get_input()
        if not val or not val.strip():
            return

        parsed = AvantureCredentialsStore.parse_proxy_components(val.strip())
        if parsed.get("host"):
            if parsed.get("protocol"):
                self.form_proxy_protocol.set(parsed["protocol"])
            self.form_proxy_host.delete(0, "end")
            self.form_proxy_host.insert(0, parsed["host"])
            self.form_proxy_port.delete(0, "end")
            self.form_proxy_port.insert(0, parsed["port"])
            self.form_proxy_user.delete(0, "end")
            self.form_proxy_user.insert(0, parsed["login"])
            self.form_proxy_pass.delete(0, "end")
            self.form_proxy_pass.insert(0, parsed["password"])
            self._set_proxy_badge("READY TO CHECK", color="#94a3b8", bg="#1e293b")
            self._on_field_change()
            self.log(f"Parsed and applied proxy for {parsed['host']}:{parsed['port']}", "INFO")
            self._on_check_proxy_click()
        else:
            messagebox.showwarning("Invalid Format", "Could not parse host and port from the pasted proxy string.")

    def _on_check_proxy_click(self):
        proto = self.form_proxy_protocol.get() if hasattr(self, "form_proxy_protocol") else "HTTP"
        host = self.form_proxy_host.get().strip() if hasattr(self, "form_proxy_host") else ""
        port = self.form_proxy_port.get().strip() if hasattr(self, "form_proxy_port") else ""
        user = self.form_proxy_user.get().strip() if hasattr(self, "form_proxy_user") else ""
        pwd = self.form_proxy_pass.get().strip() if hasattr(self, "form_proxy_pass") else ""

        if not host:
            self._set_proxy_badge("NO HOST", color="#ef4444", bg="#450a0a")
            self.log("Proxy check notice: Please enter Host and Port before checking.", "WARNING")
            return

        proxy_url = AvantureCredentialsStore.build_proxy_url(proto, host, port, user, pwd)
        self._set_proxy_badge("CHECKING...", color="#f59e0b", bg="#451a03")
        self.btn_check_proxy.configure(state="disabled")
        self.log(f"Testing connection via {proto}://{host}:{port}...", "INFO")

        def test_worker():
            import requests
            import time
            start = time.time()
            try:
                proxies = {
                    "http": proxy_url,
                    "https": proxy_url
                }
                res = requests.get("https://api.ipify.org?format=json", proxies=proxies, timeout=10)
                dur = round(time.time() - start, 2)
                if res.status_code == 200:
                    public_ip = res.json().get("ip", host)
                    def ok():
                        self._set_proxy_badge("ACTIVE", color="#22c55e", bg="#052e16")
                        self.btn_check_proxy.configure(state="normal")
                        self.log(f"Proxy check SUCCESS: Status ACTIVE, Exit IP: {public_ip} ({dur}s)", "SUCCESS")
                    self.after(0, ok)
                else:
                    def fail():
                        self._set_proxy_badge("FAILED", color="#ef4444", bg="#450a0a")
                        self.btn_check_proxy.configure(state="normal")
                        self.log(f"Proxy check returned HTTP {res.status_code}", "ERROR")
                    self.after(0, fail)
            except Exception as e:
                err_msg = str(e)
                def err():
                    self._set_proxy_badge("FAILED", color="#ef4444", bg="#450a0a")
                    self.btn_check_proxy.configure(state="normal")
                    self.log(f"Proxy unreachable: {err_msg[:60]}", "ERROR")
                self.after(0, err)

        threading.Thread(target=test_worker, daemon=True).start()

    def _on_trigger_ip_change(self):
        url = self.form_proxy_change_link.get().strip() if hasattr(self, "form_proxy_change_link") else ""
        if not url:
            self.log("Notice: Enter an IP change rotation URL first.", "WARNING")
            return
        if not (url.startswith("http://") or url.startswith("https://")):
            url = "http://" + url

        self.log(f"Requesting IP rotation: {url}...", "INFO")
        def rot_worker():
            import requests
            try:
                r = requests.get(url, timeout=15)
                def ok():
                    self.log(f"IP rotation executed: HTTP {r.status_code} ({r.text[:50].strip()})", "SUCCESS")
                    self._on_check_proxy_click()
                self.after(0, ok)
            except Exception as e:
                def err():
                    self.log(f"IP rotation error: {e}", "ERROR")
                self.after(0, err)

        threading.Thread(target=rot_worker, daemon=True).start()

    def _on_state_change(self, selected_state: str):
        cities = AVANTURE_SLOVENIA_LOCATIONS.get(selected_state, ["Ljubljana"])
        self.form_city.configure(values=cities)
        self.form_city.set(cities[0])
        self._on_field_change()

    def _on_field_change(self):
        # Auto-save changes into memory and file
        self._save_current_account_form(silent=True)

    def _on_title_key(self):
        txt = self.form_title.get()
        self.title_count_lbl.configure(text=f"{len(txt)} / 50")
        self._on_field_change()

    def _on_desc_key(self):
        txt = self.form_desc.get("1.0", "end-1c").strip()
        length = len(txt)
        if length < 50:
            self.desc_count_lbl.configure(
                text=f"{length} / 1000 (Min 50 required: need {50 - length} more)",
                text_color="#f87171"
            )
        else:
            self.desc_count_lbl.configure(
                text=f"{length} / 1000 (Valid)",
                text_color="#34d399"
            )
        self._on_field_change()

    def _save_current_account_form(self, silent: bool = False):
        if not (0 <= self.current_profile_index < len(self.profiles_list)):
            return

        acc = self.profiles_list[self.current_profile_index]
        if hasattr(self, "form_label"):
            acc["profile_name"] = self.form_label.get().strip()
        acc["username"] = self.form_user.get().strip()
        acc["password"] = self.form_pass.get().strip()

        # Save Proxy Settings dynamically
        proto = self.form_proxy_protocol.get() if hasattr(self, "form_proxy_protocol") else "HTTP"
        p_host = self.form_proxy_host.get().strip() if hasattr(self, "form_proxy_host") else ""
        p_port = self.form_proxy_port.get().strip() if hasattr(self, "form_proxy_port") else ""
        p_user = self.form_proxy_user.get().strip() if hasattr(self, "form_proxy_user") else ""
        p_pass = self.form_proxy_pass.get().strip() if hasattr(self, "form_proxy_pass") else ""
        p_name = self.form_proxy_name.get().strip() if hasattr(self, "form_proxy_name") else ""
        p_change = self.form_proxy_change_link.get().strip() if hasattr(self, "form_proxy_change_link") else ""

        acc["proxy_protocol"] = proto
        acc["proxy_host"] = p_host
        acc["proxy_port"] = p_port
        acc["proxy_login"] = p_user
        acc["proxy_password"] = p_pass
        acc["proxy_name"] = p_name
        acc["proxy_change_ip_link"] = p_change

        if p_host:
            acc["proxy"] = AvantureCredentialsStore.build_proxy_url(proto, p_host, p_port, p_user, p_pass)
        else:
            acc["proxy"] = ""

        acc["title"] = self.form_title.get().strip()
        acc["category"] = self.form_category.get()
        acc["description"] = self.form_desc.get("1.0", "end-1c").strip()
        acc["country"] = self.form_country.get()
        acc["state"] = self.form_state.get()
        acc["city"] = self.form_city.get().strip()
        acc["registration_number"] = self.form_reg.get().strip()

        AvantureCredentialsStore.save(self.profiles_list)

        if not silent:
            u_name = acc.get("profile_name") or acc.get("username") or f"Profile {self.current_profile_index + 1}"
            self.log(f"Profile settings saved for '{u_name}'", "SUCCESS")
            messagebox.showinfo("Saved", f"Profile settings for '{u_name}' saved successfully!")

        if hasattr(self, "profile_select_menu"):
            self._refresh_profile_dropdown()

    def _on_browse_profile_image(self):
        path = filedialog.askopenfilename(
            title="Select Listing Picture",
            filetypes=[
                ("Image Files", "*.jpg *.jpeg *.png *.webp *.bmp *.gif"),
                ("All Files", "*.*")
            ]
        )
        if not path:
            return

        # Ensure image is copied locally to data/images/ for permanent portability
        IMAGES_DIR.mkdir(parents=True, exist_ok=True)
        filename = Path(path).name
        target_file = IMAGES_DIR / filename
        try:
            shutil.copy2(path, target_file)
            saved_path = str(target_file.resolve())
        except Exception:
            saved_path = path

        if 0 <= self.current_profile_index < len(self.profiles_list):
            self.profiles_list[self.current_profile_index]["image_path"] = saved_path
            self.lbl_pic.configure(text=f"Attached: {filename}", text_color="#38bdf8")
            self._save_current_account_form(silent=True)
            AvantureCredentialsStore.save(self.profiles_list)
            self.log(f"Image attached and cached locally: {filename}", "SUCCESS")

    def _on_clear_profile_image(self):
        if 0 <= self.current_profile_index < len(self.profiles_list):
            self.profiles_list[self.current_profile_index]["image_path"] = ""
            self.lbl_pic.configure(text="No picture attached (Optional)", text_color="#64748b")
            self._save_current_account_form(silent=True)
            self.log("Profile image cleared.", "INFO")

    # ==================================================================
    # EXECUTION LIFECYCLE
    # ==================================================================
    def _on_click_start(self):
        if not self.db.is_user_active(self.current_user["username"]):
            messagebox.showerror(
                "Access Revoked",
                "Access Denied: Your privileges have been revoked.\nApplication will exit."
            )
            if self.on_logout:
                self.on_logout()
            return

        # Ensure current form is saved
        self._save_current_account_form(silent=True)

        active_profiles = [p for p in self.profiles_list if p.get("username", "").strip() and p.get("password", "").strip()]
        if not active_profiles:
            messagebox.showwarning(
                "No Active Profiles",
                "Please go to 'Profile Management' and enter username and password for at least one profile."
            )
            self._show_page("profile")
            return

        # Pre-validate description length for active profiles (>= 50 chars)
        for p in active_profiles:
            desc = p.get("description", "").strip()
            pname = p.get("profile_name") or p.get("username") or f"Profile {active_profiles.index(p) + 1}"
            if len(desc) < 50:
                messagebox.showwarning(
                    "Description Too Short",
                    f"The description for profile '{pname}' is only {len(desc)} characters.\n\n"
                    f"Avanture requires at least 50 characters for the description to publish successfully.\n\n"
                    f"Please enter at least 50 characters in Profile Management before running."
                )
                self._show_page("profile")
                return

        # Switch to runner view so operator sees live log stream
        self._show_page("runner")

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress_bar.set(0)
        self.total_count = len(active_profiles)
        self.success_count = 0
        self.fail_count = 0
        self.progress_lbl.configure(text=f"0 / {self.total_count} (0%)")

        # Calculate re-post delay between complete account rounds
        try:
            relist_val = float(self.relist_entry.get().strip())
        except (ValueError, TypeError):
            relist_val = 15.0

        relist_unit = self.relist_unit_var.get().strip()
        if relist_unit == "Hours":
            relist_seconds = max(1.0, relist_val * 3600.0)
            relist_info = f"{relist_val:g} hr(s)"
        elif relist_unit == "Seconds":
            relist_seconds = max(1.0, relist_val * 1.0)
            relist_info = f"{relist_val:g} sec(s)"
        else: # Minutes
            relist_seconds = max(1.0, relist_val * 60.0)
            relist_info = f"{relist_val:g} min(s)"

        # Calculate Auto-Stop timer limit (if enabled)
        auto_stop_enabled = bool(self.auto_stop_enabled_var.get())
        try:
            autostop_val = float(self.autostop_entry.get().strip())
        except (ValueError, TypeError):
            autostop_val = 8.0

        autostop_unit = self.autostop_unit_var.get().strip()
        if autostop_unit == "Minutes":
            auto_stop_seconds = max(60.0, autostop_val * 60.0)
            autostop_info = f"{autostop_val:g} min(s)"
        else: # Hours
            auto_stop_seconds = max(60.0, autostop_val * 3600.0)
            autostop_info = f"{autostop_val:g} hr(s)"

        timer_desc = f"Auto-Stop in {autostop_info}" if auto_stop_enabled else "Non-Stop (Infinite)"
        self.log(
            f"Initiating automation engine for {len(active_profiles)} active profile(s) "
            f"[Cycle Delay: {relist_info} | Schedule: {timer_desc}]...",
            "INFO"
        )
        self.runner_summary_lbl.configure(
            text=f"Active | Round Interval: {relist_info} | {timer_desc}",
            text_color="#34d399"
        )

        self.worker = AutomationWorker(
            target_url=DEFAULT_TARGET_URL,
            data_df=self.current_df,
            accounts=active_profiles,
            proxy=active_profiles[0].get("proxy", "") if active_profiles else DEFAULT_PROXY_URL,
            headless=self.headless_var.get(),
            auto_delete_old=True,
            delay_between_accounts=5.0,
            loop_continuous=True,
            loop_interval_seconds=relist_seconds,
            auto_stop_enabled=auto_stop_enabled,
            auto_stop_seconds=auto_stop_seconds,
            on_log=self.log,
            on_progress=self._on_worker_progress,
            on_row_completed=self._on_worker_row_completed,
            on_finished=self._on_worker_finished,
            on_countdown=self._on_worker_countdown
        )

        self.worker_thread = threading.Thread(target=self.worker.run, daemon=True)
        self.worker_thread.start()

    def _on_click_stop(self):
        if self.worker:
            self.stop_btn.configure(state="disabled")
            self.log("Stop requested by user. Terminating browser and automation immediately...", "WARNING")
            self.worker.stop()
            self.start_btn.configure(state="normal")

    def _on_worker_progress(self, current: int, total: int, pct: float):
        self.after(0, self._update_progress_ui, current, total, pct)

    def _update_progress_ui(self, current: int, total: int, pct: float):
        self.progress_bar.set(pct)
        self.progress_lbl.configure(text=f"{current} / {total} ({int(pct * 100)}%)")

    def _on_worker_row_completed(self, idx: int, success: bool, err_msg: str):
        if success:
            self.success_count += 1
        else:
            self.fail_count += 1

    def _on_worker_countdown(self, text: str):
        self.after(0, self._update_countdown_ui, text)

    def _update_countdown_ui(self, text: str):
        if hasattr(self, "runner_summary_lbl"):
            if text:
                self.runner_summary_lbl.configure(text=f"⏳ {text}", text_color="#38bdf8")
            else:
                self.runner_summary_lbl.configure(
                    text="Mode: Non-Stop Auto-Cycle | Delete old ad → Post fresh ad",
                    text_color="#94a3b8"
                )

    def _on_worker_finished(self, summary: dict):
        self.after(0, self._handle_worker_completion, summary)

    def _handle_worker_completion(self, summary: dict):
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        if hasattr(self, "runner_summary_lbl"):
            self.runner_summary_lbl.configure(
                text="Mode: Non-Stop Auto-Cycle | Delete old ad → Post fresh ad",
                text_color="#94a3b8"
            )
        if self.worker and self.worker.is_stopped:
            messagebox.showinfo("Stopped", "Automation was stopped by user or auto-stop schedule.")
        else:
            msg = f"Automation completed!\nSuccessful: {summary['success']}\nFailed: {summary['failed']}\nTotal Accounts: {summary['total']}"
            messagebox.showinfo("Finished", msg)

    # ==================================================================
    # LOGGING & AUDIT STREAM
    # ==================================================================
    def log(self, message: str, level: str = "INFO"):
        ts = datetime.now().strftime("%H:%M:%S")
        formatted = f"[{ts}] [{level}] {message}\n"
        self.after(0, self._append_log_text, formatted)

    def _append_log_text(self, text: str):
        self.log_textbox.insert("end", text)
        try:
            line_count = int(self.log_textbox.index("end-1c").split(".")[0])
            if line_count > 600:
                self.log_textbox.delete("1.0", f"{line_count - 500}.0")
        except Exception:
            pass
        self.log_textbox.see("end")

    def _on_clear_logs(self):
        self.log_textbox.delete("1.0", "end")

    def _on_export_results(self):
        save_path = filedialog.asksaveasfilename(
            title="Export Automation Audit Report",
            defaultextension=".txt",
            initialfile=f"automation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt",
            filetypes=[("Text File", "*.txt"), ("All Files", "*.*")]
        )
        if save_path:
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(self.log_textbox.get("1.0", "end"))
            messagebox.showinfo("Exported", f"Audit logs saved to:\n{save_path}")

    def _update_auth_status(self):
        if self.auth_manager.has_saved_session():
            self.auth_badge.configure(
                text="● Session Active",
                fg_color="#064e3b",
                text_color="#34d399"
            )
        else:
            self.auth_badge.configure(
                text="○ Ready",
                fg_color="#1e293b",
                text_color="#94a3b8"
            )

    def _check_live_access_status(self):
        """Periodically ensures this admin operator's access has not been revoked by the Super Admin."""
        try:
            username = self.current_user.get("username", "")
            if username and not self.db.is_user_active(username):
                if self.worker:
                    try:
                        self.worker.stop()
                    except Exception:
                        pass
                messagebox.showerror(
                    "Access Revoked",
                    "Your admin account access has been revoked by the Super Administrator.\nYou have been logged out."
                )
                if self.on_logout:
                    self.on_logout()
                return
        except Exception:
            pass
        self.after(4000, self._check_live_access_status)

    def _on_click_manage_admins(self):
        if self.admin_window is None or not self.admin_window.winfo_exists():
            self.admin_window = AdminManagementWindow(self, current_user=self.current_user)
        else:
            self.admin_window.focus()

    def _on_click_logout(self):
        if messagebox.askyesno("Sign Out", "Are you sure you want to sign out?"):
            if self.on_logout:
                self.on_logout()
