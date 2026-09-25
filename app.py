import ctypes
import sys

if sys.platform.startswith("win"):
    # customtkinter turns on per-monitor DPI awareness only after it has created
    # the Tk root, which leaves Tk measuring a 96-DPI desktop while windows are
    # sized in physical pixels.  Switch before Tk starts so both agree.
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (AttributeError, OSError):
        pass

import customtkinter as ctk

from api_client import AdminApiClient
from config import APP_NAME
from login_window import LoginWindow
from dashboard_window import DashboardWindow
from window_fit import place_window


class SendForgeAdminApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title(APP_NAME)
        # Fit the monitor's work area so nothing sits under the Windows taskbar.
        place_window(self, 1180, 760, min_width=980, min_height=640)
        self.client = AdminApiClient()
        self.current = None
        if self.client.token:
            self.show_dashboard()
        else:
            self.show_login()

    def clear(self):
        if self.current:
            self.current.destroy()
            self.current = None

    def show_login(self):
        self.clear()
        self.current = LoginWindow(self, self.client, self.show_dashboard)

    def show_dashboard(self):
        self.clear()
        self.current = DashboardWindow(self, self.client, self.show_login)


if __name__ == "__main__":
    app = SendForgeAdminApp()
    app.mainloop()
