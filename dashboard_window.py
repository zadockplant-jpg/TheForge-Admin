import customtkinter as ctk

from config import APP_NAME

from api_client import AdminApiClient
from products_tab import ProductsTab
from entitlements_tab import EntitlementsTab
from referrals_tab import ReferralsTab
from rewards_tab import RewardsTab
from payout_setup_tab import CashAppPayoutSetupTab
from testing_tab import TestingTab
from audit_tab import AuditLogTab


class DashboardWindow(ctk.CTkFrame):
    def __init__(self, master, client: AdminApiClient, on_logout):
        super().__init__(master)
        self.client = client
        self.on_logout = on_logout
        self._build()

    def _build(self):
        self.pack(fill="both", expand=True)
        header = ctk.CTkFrame(self, height=52)
        header.pack(fill="x")
        ctk.CTkLabel(header, text=APP_NAME, font=("Arial", 20, "bold")).pack(side="left", padx=16)
        ctk.CTkLabel(header, text=self.client.api_base, text_color="#9ca3af").pack(side="left", padx=16)
        ctk.CTkButton(header, text="Logout", width=90, command=self.logout).pack(side="right", padx=12, pady=8)

        tabs = ctk.CTkTabview(self)
        tabs.pack(fill="both", expand=True, padx=10, pady=10)
        products = tabs.add("Products")
        entitlements = tabs.add("Entitlements")
        referrals = tabs.add("Referrals")
        payouts = tabs.add("Payouts")
        cashapp_api = tabs.add("Cash App API")
        testing = tabs.add("Owner Tools")
        audit = tabs.add("Audit")
        ProductsTab(products, self.client).pack(fill="both", expand=True)
        EntitlementsTab(entitlements, self.client).pack(fill="both", expand=True)
        ReferralsTab(referrals, self.client).pack(fill="both", expand=True)
        RewardsTab(payouts, self.client).pack(fill="both", expand=True)
        CashAppPayoutSetupTab(cashapp_api, self.client).pack(fill="both", expand=True)
        TestingTab(testing, self.client).pack(fill="both", expand=True)
        AuditLogTab(audit, self.client).pack(fill="both", expand=True)

    def logout(self):
        self.client.clear_session()
        self.on_logout()
