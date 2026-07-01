import webbrowser

import customtkinter as ctk

from api_client import AdminApiClient
from config import (
    CASHAPP_API_KEYS_URL,
    CASHAPP_ONBOARDING_URL,
    CASHAPP_PARTNER_APPLICATION_URL,
    CASHAPP_PARTNER_GUIDE_URL,
    CASHAPP_PAYOUT_API_URL,
)
from ui_helpers import show_info


RENDER_ENV_TEMPLATE = """CASHAPP_PAYOUTS_ENABLED=false
CASHAPP_API_ENV=sandbox
CASHAPP_CLIENT_ID=
CASHAPP_CLIENT_SECRET=
CASHAPP_API_KEY_ID=
CASHAPP_API_KEY_SECRET=
CASHAPP_REGION=PDX
CASHAPP_MERCHANT_ID=
CASHAPP_WEBHOOK_SECRET=
"""


class CashAppPayoutSetupTab(ctk.CTkFrame):
    def __init__(self, master, client: AdminApiClient):
        super().__init__(master)
        self.client = client
        self._build()

    def _build(self):
        scroll = ctk.CTkScrollableFrame(self)
        scroll.pack(fill="both", expand=True, padx=10, pady=10)

        ctk.CTkLabel(scroll, text="Cash App Payout API Setup", font=("Arial", 22, "bold")).pack(anchor="w", padx=8, pady=(4, 4))
        ctk.CTkLabel(
            scroll,
            text="Manual payout controls are active. Official Cash App API sending remains disabled until Cash App approves SendForge and backend credentials are configured in Render.",
            text_color="#cbd5e1",
            wraplength=980,
            justify="left",
        ).pack(anchor="w", padx=8, pady=(0, 12))

        status = ctk.CTkFrame(scroll)
        status.pack(fill="x", padx=8, pady=6)
        ctk.CTkLabel(status, text="Current mode", font=("Arial", 15, "bold")).pack(anchor="w", padx=14, pady=(12, 2))
        ctk.CTkLabel(status, text="Manual Cash App payout workflow", text_color="#fbbf24").pack(anchor="w", padx=14, pady=(0, 12))

        self._section(scroll, "1. Apply for official access")
        self._button(scroll, "Open Cash App partner application", CASHAPP_PARTNER_APPLICATION_URL)
        self._button(scroll, "Read partner approval requirements", CASHAPP_PARTNER_GUIDE_URL)
        self._button(scroll, "Open onboarding requirements", CASHAPP_ONBOARDING_URL)

        self._section(scroll, "2. Review authentication and payouts")
        self._button(scroll, "Open API-key authentication guide", CASHAPP_API_KEYS_URL)
        self._button(scroll, "Open official Create Payout endpoint", CASHAPP_PAYOUT_API_URL)

        ctk.CTkLabel(
            scroll,
            text="Cash App's partner API is server-side. Never place client secrets or API-key secrets in this desktop app. Add them only to the Render backend environment after approval.",
            text_color="#fca5a5",
            wraplength=980,
            justify="left",
        ).pack(anchor="w", padx=8, pady=(10, 8))

        self._section(scroll, "3. Render environment variable template")
        box = ctk.CTkTextbox(scroll, height=220)
        box.insert("1.0", RENDER_ENV_TEMPLATE)
        box.configure(state="disabled")
        box.pack(fill="x", padx=8, pady=6)
        ctk.CTkButton(scroll, text="Copy Render variable names", command=self._copy_env).pack(anchor="w", padx=8, pady=(4, 14))

        self._section(scroll, "Before automatic payouts can be enabled")
        checklist = (
            "• Cash App partner approval and developer account\n"
            "• Client ID and API credentials stored in Render\n"
            "• Merchant ID and region confirmed\n"
            "• Signed backend requests and 30-day API-key rotation\n"
            "• Cash App webhook endpoint and signature verification\n"
            "• Idempotency key per reward so retries cannot double-pay\n"
            "• Daily payout cap, batch cap, fraud hold, and kill switch\n"
            "• Sandbox tests before CASHAPP_PAYOUTS_ENABLED is changed to true"
        )
        ctk.CTkLabel(scroll, text=checklist, wraplength=980, justify="left").pack(anchor="w", padx=8, pady=(2, 14))

    def _section(self, parent, title):
        ctk.CTkLabel(parent, text=title, font=("Arial", 16, "bold")).pack(anchor="w", padx=8, pady=(14, 4))

    def _button(self, parent, label, url):
        ctk.CTkButton(parent, text=label, command=lambda u=url: webbrowser.open(u)).pack(anchor="w", padx=8, pady=4)

    def _copy_env(self):
        self.clipboard_clear()
        self.clipboard_append(RENDER_ENV_TEMPLATE)
        self.update()
        show_info(self, "Copied", "Render environment variable names copied. Leave payout automation disabled until the backend integration is installed and Cash App approves access.")
