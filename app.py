import customtkinter as ctk

from api_client import AdminApiClient
from config import APP_NAME
from login_window import LoginWindow
from dashboard_window import DashboardWindow


class SendForgeAdminApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")
        self.title(APP_NAME)
        self.geometry("1180x760")
        self.minsize(980, 640)
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
