import sys
import ctypes
import customtkinter as ctk

# -------------------------------------------------------------
# 1. CRISP OS-LEVEL DPI AWARENESS (Fixes blurry text on Windows)
# -------------------------------------------------------------
if sys.platform == "win32":
    try:
        # Per-Monitor DPI Awareness v2 for Windows 10/11
        # Eliminates blurry bitmap stretching and renders razor-sharp ClearType text
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

from ui.login_window import LoginView
from ui.main_window import DashboardView
from ui.super_admin_view import SuperAdminView

class Application(ctk.CTk):
    """
    High-performance single-root application.
    Renders razor-sharp native typography with instant view switching.
    """

    def __init__(self):
        super().__init__()

        self.title("Avanture Automation - Sign In")
        self.configure(fg_color="#0a0e17")

        self.current_user = None
        self.current_view = None

        self.show_login_view()

    def _center_window(self, width: int, height: int):
        self.update_idletasks()
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        x = max(0, int((screen_w - width) / 2))
        y = max(0, int((screen_h - height) / 2))
        self.geometry(f"{width}x{height}+{x}+{y}")

    def show_login_view(self):
        if self.current_view:
            self.current_view.destroy()

        self.title("Avanture Automation - Sign In")
        self.resizable(False, False)
        self._center_window(460, 500)

        self.current_view = LoginView(self, on_login_success=self.on_login_success)
        self.current_view.pack(fill="both", expand=True)

    def on_login_success(self, user_data: dict):
        if self.current_view:
            self.current_view.destroy()

        self.current_user = user_data
        role = user_data.get("role")

        self.resizable(True, True)
        self.minsize(880, 680)

        # Role-based separation:
        # SUPER_ADMIN: Dedicated Admin Profiles & Access Control Console (NO automation)
        # ADMIN: Automation Runner & Listing Configuration Dashboard
        if role == "SUPER_ADMIN":
            self.title(f"Avanture Platform Control — Super Admin [{user_data.get('username')}]")
            self._center_window(1060, 780)
            self.current_view = SuperAdminView(
                self,
                current_user=user_data,
                on_logout=self.show_login_view
            )
        else:
            self.title(f"Avanture Automation Engine — {user_data.get('username')} [ADMIN]")
            self._center_window(1060, 860)
            self.current_view = DashboardView(
                self,
                current_user=user_data,
                on_logout=self.show_login_view
            )

        self.current_view.pack(fill="both", expand=True)

def main():
    app = Application()
    app.mainloop()

if __name__ == "__main__":
    main()
