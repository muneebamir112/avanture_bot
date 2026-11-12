import customtkinter as ctk
from tkinter import messagebox
from typing import Callable, Optional
from core.db import UserManager

class AdminManagementWindow(ctk.CTkToplevel):
    """Modern, high-polish user access control and admin management console."""

    def __init__(self, parent, current_user: dict, on_user_change: Optional[Callable[[], None]] = None):
        super().__init__(parent)

        self.title("Super Admin • Access Control Center")
        self.geometry("920x620")
        self.minsize(840, 540)
        self.current_user = current_user
        self.on_user_change = on_user_change
        self.db = UserManager()

        self.configure(fg_color="#0b0f19")
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self._build_ui()
        self._refresh_users_list()

    def _build_ui(self):
        # 1. HEADER
        header = ctk.CTkFrame(
            self,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
            corner_radius=12
        )
        header.grid(row=0, column=0, padx=20, pady=(16, 10), sticky="ew")
        header.grid_columnconfigure(0, weight=1)

        h_left = ctk.CTkFrame(header, fg_color="transparent")
        h_left.grid(row=0, column=0, padx=16, pady=12, sticky="w")

        title = ctk.CTkLabel(
            h_left,
            text="User Permissions & Access Control",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color="#f8fafc"
        )
        title.pack(anchor="w")

        sub = ctk.CTkLabel(
            h_left,
            text=f"Active Super Administrator: @{self.current_user.get('username')} • Instant Revocation & Granting",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color="#94a3b8"
        )
        sub.pack(anchor="w")

        # 2. MAIN SPLIT (Left: Users, Right: Create Form)
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.grid(row=1, column=0, padx=20, pady=(0, 16), sticky="nsew")
        content_frame.grid_columnconfigure(0, weight=3)
        content_frame.grid_columnconfigure(1, weight=2)
        content_frame.grid_rowconfigure(0, weight=1)

        # LEFT CONTAINER: Accounts Table
        list_container = ctk.CTkFrame(
            content_frame,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
            corner_radius=12
        )
        list_container.grid(row=0, column=0, padx=(0, 10), pady=0, sticky="nsew")
        list_container.grid_columnconfigure(0, weight=1)
        list_container.grid_rowconfigure(1, weight=1)

        list_top = ctk.CTkFrame(list_container, fg_color="transparent")
        list_top.grid(row=0, column=0, padx=16, pady=12, sticky="ew")
        list_top.grid_columnconfigure(0, weight=1)

        table_heading = ctk.CTkLabel(
            list_top,
            text="Team & Operator Accounts",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#e2e8f0"
        )
        table_heading.grid(row=0, column=0, sticky="w")

        refresh_btn = ctk.CTkButton(
            list_top,
            text="↻ Refresh",
            width=80,
            height=28,
            corner_radius=6,
            fg_color="#1e293b",
            hover_color="#334155",
            text_color="#cbd5e1",
            font=ctk.CTkFont(family="Segoe UI", size=12),
            command=self._refresh_users_list
        )
        refresh_btn.grid(row=0, column=1, sticky="e")

        self.scroll_frame = ctk.CTkScrollableFrame(list_container, fg_color="transparent")
        self.scroll_frame.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")
        self.scroll_frame.grid_columnconfigure(0, weight=1)

        # RIGHT CONTAINER: Add New User Form
        form_card = ctk.CTkFrame(
            content_frame,
            fg_color="#111827",
            border_width=1,
            border_color="#1f2937",
            corner_radius=12
        )
        form_card.grid(row=0, column=1, padx=(10, 0), pady=0, sticky="nsew")
        form_card.grid_columnconfigure(0, weight=1)

        form_title = ctk.CTkLabel(
            form_card,
            text="+ Add New Operator / Admin",
            font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
            text_color="#e2e8f0"
        )
        form_title.grid(row=0, column=0, padx=18, pady=(16, 12), sticky="w")

        # Username
        ctk.CTkLabel(
            form_card,
            text="USERNAME",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).grid(row=1, column=0, padx=18, pady=(4, 2), sticky="w")

        self.new_user_entry = ctk.CTkEntry(
            form_card,
            placeholder_text="e.g. operator_alex",
            height=36,
            corner_radius=8,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.new_user_entry.grid(row=2, column=0, padx=18, pady=(0, 10), sticky="ew")

        # Password
        ctk.CTkLabel(
            form_card,
            text="PASSWORD",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).grid(row=3, column=0, padx=18, pady=(4, 2), sticky="w")

        self.new_pass_entry = ctk.CTkEntry(
            form_card,
            placeholder_text="Enter initial password",
            show="*",
            height=36,
            corner_radius=8,
            fg_color="#0f172a",
            border_color="#334155",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.new_pass_entry.grid(row=4, column=0, padx=18, pady=(0, 10), sticky="ew")

        # Role
        ctk.CTkLabel(
            form_card,
            text="PERMISSION ROLE",
            font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
            text_color="#94a3b8"
        ).grid(row=5, column=0, padx=18, pady=(4, 2), sticky="w")

        self.role_var = ctk.StringVar(value="ADMIN")
        self.role_menu = ctk.CTkOptionMenu(
            form_card,
            variable=self.role_var,
            values=["ADMIN", "SUPER_ADMIN"],
            height=36,
            corner_radius=8,
            fg_color="#1e293b",
            button_color="#334155",
            button_hover_color="#475569",
            text_color="#f8fafc",
            font=ctk.CTkFont(family="Segoe UI", size=12)
        )
        self.role_menu.grid(row=6, column=0, padx=18, pady=(0, 18), sticky="ew")

        # Submit Button
        create_btn = ctk.CTkButton(
            form_card,
            text="Create User Account",
            height=38,
            corner_radius=8,
            fg_color="#10b981",       # Emerald green
            hover_color="#059669",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            command=self._on_click_create_user
        )
        create_btn.grid(row=7, column=0, padx=18, pady=(0, 18), sticky="ew")

        # Info Box
        tip_box = ctk.CTkFrame(
            form_card,
            fg_color="#0f172a",
            border_width=1,
            border_color="#1e293b",
            corner_radius=8
        )
        tip_box.grid(row=8, column=0, padx=18, pady=10, sticky="ew")

        tip_lbl = ctk.CTkLabel(
            tip_box,
            text="⚡ Access Revocation Notice:\nRevoking an account halts the user's sessions immediately. They cannot authenticate or launch automated listings.",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color="#94a3b8",
            wraplength=250,
            justify="left"
        )
        tip_lbl.pack(padx=12, pady=10)

    def _refresh_users_list(self):
        for widget in self.scroll_frame.winfo_children():
            widget.destroy()

        users = self.db.get_all_users()

        for idx, u in enumerate(users):
            is_active = (u["status"] == "ACTIVE")
            is_super = (u["role"] == "SUPER_ADMIN")
            is_self = (u["username"] == self.current_user.get("username"))

            card_border = "#1f2937" if is_active else "#5a1e1e"
            card_bg = "#0f172a" if is_active else "#1c1313"

            row_card = ctk.CTkFrame(
                self.scroll_frame,
                corner_radius=10,
                fg_color=card_bg,
                border_width=1,
                border_color=card_border
            )
            row_card.pack(fill="x", padx=4, pady=5)
            row_card.grid_columnconfigure(0, weight=1)

            # Details
            info_frame = ctk.CTkFrame(row_card, fg_color="transparent")
            info_frame.grid(row=0, column=0, padx=14, pady=10, sticky="w")

            title_row = ctk.CTkFrame(info_frame, fg_color="transparent")
            title_row.pack(anchor="w")

            user_badge = ctk.CTkLabel(
                title_row,
                text=f"👤 {u['username']}",
                font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                text_color="#f8fafc"
            )
            user_badge.pack(side="left", padx=(0, 8))

            # Role pill
            role_fg = "#312e81" if is_super else "#0c4a6e"
            role_text_color = "#a5b4fc" if is_super else "#7dd3fc"
            role_pill = ctk.CTkLabel(
                title_row,
                text=u["role"],
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                fg_color=role_fg,
                text_color=role_text_color,
                corner_radius=4,
                padx=6,
                pady=1
            )
            role_pill.pack(side="left", padx=4)

            # Status pill
            status_fg = "#064e3b" if is_active else "#450a0a"
            status_text_color = "#34d399" if is_active else "#f87171"
            status_pill = ctk.CTkLabel(
                title_row,
                text="ACTIVE" if is_active else "REVOKED",
                font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                fg_color=status_fg,
                text_color=status_text_color,
                corner_radius=4,
                padx=6,
                pady=1
            )
            status_pill.pack(side="left", padx=4)

            # Meta line
            meta_lbl = ctk.CTkLabel(
                info_frame,
                text=f"Created: {u['created_at'][:10]}   •   Last Login: {u['last_login'] or 'Never'}",
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color="#64748b"
            )
            meta_lbl.pack(anchor="w", pady=(2, 0))

            # Actions
            btn_frame = ctk.CTkFrame(row_card, fg_color="transparent")
            btn_frame.grid(row=0, column=1, padx=12, pady=10, sticky="e")

            if not is_self and not (u["username"] == "superadmin"):
                if is_active:
                    revoke_btn = ctk.CTkButton(
                        btn_frame,
                        text="🔒 Revoke",
                        width=80,
                        height=28,
                        corner_radius=6,
                        fg_color="#dc2626",
                        hover_color="#b91c1c",
                        font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                        command=lambda uid=u["id"]: self._toggle_status(uid, "REVOKED")
                    )
                    revoke_btn.pack(side="left", padx=3)
                else:
                    restore_btn = ctk.CTkButton(
                        btn_frame,
                        text="🔓 Restore",
                        width=80,
                        height=28,
                        corner_radius=6,
                        fg_color="#059669",
                        hover_color="#047857",
                        font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                        command=lambda uid=u["id"]: self._toggle_status(uid, "ACTIVE")
                    )
                    restore_btn.pack(side="left", padx=3)

                del_btn = ctk.CTkButton(
                    btn_frame,
                    text="✕",
                    width=32,
                    height=28,
                    corner_radius=6,
                    fg_color="#334155",
                    hover_color="#475569",
                    text_color="#f8fafc",
                    font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                    command=lambda uid=u["id"]: self._delete_user(uid)
                )
                del_btn.pack(side="left", padx=3)
            else:
                self_tag = ctk.CTkLabel(
                    btn_frame,
                    text="(Your Account)" if is_self else "(Master)",
                    font=ctk.CTkFont(family="Segoe UI", size=11),
                    text_color="#64748b"
                )
                self_tag.pack(side="right", padx=6)

    def _toggle_status(self, user_id: int, new_status: str):
        ok, msg = self.db.set_user_status(user_id, new_status)
        if ok:
            self._refresh_users_list()
            if self.on_user_change:
                self.on_user_change()
        else:
            messagebox.showerror("Error", msg)

    def _delete_user(self, user_id: int):
        if messagebox.askyesno("Confirm Delete", "Permanently remove this operator account?"):
            ok, msg = self.db.delete_user(user_id)
            if ok:
                self._refresh_users_list()
                if self.on_user_change:
                    self.on_user_change()
            else:
                messagebox.showerror("Error", msg)

    def _on_click_create_user(self):
        user = self.new_user_entry.get().strip()
        pwd = self.new_pass_entry.get().strip()
        role = self.role_var.get()

        if not user or not pwd:
            messagebox.showwarning("Warning", "Please provide both username and password.")
            return

        ok, msg = self.db.create_user(
            username=user,
            password=pwd,
            role=role,
            created_by=self.current_user.get("username", "superadmin")
        )

        if ok:
            messagebox.showinfo("Success", msg)
            self.new_user_entry.delete(0, "end")
            self.new_pass_entry.delete(0, "end")
            self._refresh_users_list()
            if self.on_user_change:
                self.on_user_change()
        else:
            messagebox.showerror("Failed", msg)
