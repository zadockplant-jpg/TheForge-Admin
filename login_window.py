import customtkinter as ctk

from api_client import ApiError, AdminApiClient
from ui_helpers import show_error


class LoginWindow(ctk.CTkFrame):
    def __init__(self, master, client: AdminApiClient, on_authenticated):
        super().__init__(master)
        self.client = client
        self.on_authenticated = on_authenticated
        self.email = ctk.StringVar()
        self.password = ctk.StringVar()
        self.code = ctk.StringVar()
        self.api_base = ctk.StringVar(value=self.client.api_base)
        self.challenge_id = None
        self._build()

    def _build(self):
        self.pack(fill="both", expand=True)
        card = ctk.CTkFrame(self)
        card.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(card, text="SendForge Admin", font=("Arial", 26, "bold")).pack(padx=36, pady=(28, 8))
        ctk.CTkLabel(card, text="Backend admin console · MFA required", text_color="#9ca3af").pack(pady=(0, 20))

        self._labeled_entry(card, "Backend API URL", self.api_base, "https://comms-app-1wo0.onrender.com")
        self._labeled_entry(card, "Admin email", self.email, "zadockplant@gmail.com")
        self._labeled_entry(card, "Password", self.password, "SendForge account password", show="*")
        ctk.CTkButton(card, text="Send MFA Code", command=self.request_code).pack(padx=30, pady=(14, 8), fill="x")

        self._labeled_entry(card, "MFA code", self.code, "6-digit code sent to admin email")
        ctk.CTkButton(card, text="Verify & Open Admin", command=self.verify_code).pack(padx=30, pady=(8, 28), fill="x")

    def _labeled_entry(self, parent, label, variable, placeholder, show=None):
        ctk.CTkLabel(parent, text=label, font=("Arial", 13, "bold")).pack(anchor="w", padx=30, pady=(8, 2))
        ctk.CTkEntry(parent, textvariable=variable, width=360, placeholder_text=placeholder, show=show).pack(padx=30, pady=(0, 4))

    def request_code(self):
        try:
            self.client.set_api_base(self.api_base.get().strip())
            data = self.client.login(self.email.get().strip(), self.password.get())
            self.challenge_id = data.get("challengeId") or data.get("challenge_id")
            if not self.challenge_id:
                raise ApiError("MFA request succeeded but no challenge ID was returned.")
        except ApiError as exc:
            show_error(self, exc)

    def verify_code(self):
        try:
            if not self.challenge_id:
                raise ApiError("Request an MFA code first.")
            self.client.verify_mfa(self.challenge_id, self.code.get().strip())
            self.on_authenticated()
        except ApiError as exc:
            show_error(self, exc)
