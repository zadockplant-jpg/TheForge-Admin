import customtkinter as ctk

from api_client import ApiError, AdminApiClient
from ui_helpers import show_error, show_info


class EntitlementsTab(ctk.CTkFrame):
    def __init__(self, master, client: AdminApiClient):
        super().__init__(master)
        self.client = client
        self.email = ctk.StringVar()
        self.slug = ctk.StringVar()
        self.output = None
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="Entitlements", font=("Arial", 20, "bold")).pack(anchor="w", padx=12, pady=12)
        form = ctk.CTkFrame(self)
        form.pack(fill="x", padx=12, pady=8)
        ctk.CTkEntry(form, textvariable=self.email, placeholder_text="Customer email", width=280).pack(side="left", padx=8, pady=10)
        ctk.CTkEntry(form, textvariable=self.slug, placeholder_text="product slug / entitlement slug", width=280).pack(side="left", padx=8, pady=10)
        ctk.CTkButton(form, text="Search User", command=self.search_user).pack(side="left", padx=6)
        ctk.CTkButton(form, text="Grant", command=self.grant).pack(side="left", padx=6)
        ctk.CTkButton(form, text="Revoke", command=self.revoke).pack(side="left", padx=6)
        self.output = ctk.CTkTextbox(self)
        self.output.pack(fill="both", expand=True, padx=12, pady=12)

    def _write(self, text):
        self.output.delete("1.0", "end")
        self.output.insert("1.0", text)

    def search_user(self):
        try:
            data = self.client.search_user(self.email.get().strip())
            self._write(str(data))
        except ApiError as exc:
            show_error(self, exc)

    def grant(self):
        try:
            data = self.client.grant_entitlement(self.email.get().strip(), self.slug.get().strip())
            self._write(str(data))
        except ApiError as exc:
            show_error(self, exc)

    def revoke(self):
        try:
            data = self.client.revoke_entitlement(self.email.get().strip(), self.slug.get().strip())
            self._write(str(data))
        except ApiError as exc:
            show_error(self, exc)
