import customtkinter as ctk

from api_client import ApiError, AdminApiClient
from ui_helpers import clear_frame, show_error


HIDDEN_PROGRAM_SLUGS = {"rentawifey"}


class ReferralsTab(ctk.CTkFrame):
    def __init__(self, master, client: AdminApiClient):
        super().__init__(master)
        self.client = client
        self.data = {}
        self.search_text = ctk.StringVar(value="")
        self.list_frame = None
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text="Referral Verification", font=("Arial", 20, "bold")).pack(side="left")
        ctk.CTkButton(top, text="Refresh", command=self.refresh).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Payout Rule", command=self.open_program_dialog).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Create Code", command=self.open_create).pack(side="right", padx=4)

        filters = ctk.CTkFrame(self)
        filters.pack(fill="x", padx=10, pady=(0, 8))
        ctk.CTkLabel(filters, text="Search", font=("Arial", 13, "bold")).pack(side="left", padx=(10, 4), pady=8)
        search = ctk.CTkEntry(filters, textvariable=self.search_text, placeholder_text="Referrer email, Cash App tag, referral code, recipient email")
        search.pack(side="left", fill="x", expand=True, padx=(4, 10), pady=8)
        search.bind("<KeyRelease>", lambda _event: self.render())

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.refresh()

    def refresh(self):
        try:
            self.data = self.client.get_referrals()
        except ApiError as exc:
            show_error(self, exc)
            return
        self.render()

    def render(self):
        clear_frame(self.list_frame)
        data = self.data or {}
        programs = [p for p in (data.get("programs") or []) if str(p.get("product_slug") or "").lower() not in HIDDEN_PROGRAM_SLUGS]
        events = [e for e in (data.get("events") or data.get("items") or []) if str(e.get("product_slug") or "").lower() not in HIDDEN_PROGRAM_SLUGS]
        rewards = [r for r in (data.get("rewards") or []) if str(r.get("product_slug") or "").lower() not in HIDDEN_PROGRAM_SLUGS]
        catalog = data.get("catalog") or []
        query = self.search_text.get().strip().lower()

        self._section("Referral catalog by user")
        shown = 0
        for item in catalog[:500]:
            haystack = " ".join(str(item.get(k) or "") for k in ("referrerEmail", "cashAppTag", "referralCode", "lastActivityAt")).lower()
            if query and query not in haystack:
                continue
            shown += 1
            self._catalog_card(item)
        if shown == 0:
            self._row("No matching referral catalog rows. Use Refresh after sending invites or creating test rows.")

        self._section("Payout rules")
        for item in programs:
            self._program_card(item)

        self._section("Recent referral activity — email / Cash App / referral code / recipient")
        activity_shown = 0
        for item in events[:200]:
            line = self._event_line(item)
            if query and query not in line.lower():
                continue
            activity_shown += 1
            self._row(line)
        if activity_shown == 0:
            self._row("No matching recent referral activity.")

        self._section("Pending / recent rewards with payout hold")
        reward_shown = 0
        for item in rewards[:200]:
            line = self._reward_line(item)
            if query and query not in line.lower():
                continue
            reward_shown += 1
            self._row(line)
        if reward_shown == 0:
            self._row("No matching reward rows.")

    def _catalog_card(self, item):
        card = ctk.CTkFrame(self.list_frame, fg_color="#111827")
        card.pack(fill="x", padx=6, pady=6)
        email = item.get("referrerEmail") or "unknown email"
        cashapp = item.get("cashAppTag") or "missing Cash App"
        code = item.get("referralCode") or "no code"
        ctk.CTkLabel(card, text=f"{email}", font=("Arial", 14, "bold"), anchor="w").pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(card, text=f"Referral code: {code}     Cash App: {cashapp}", text_color="#93c5fd", anchor="w").pack(fill="x", padx=10, pady=2)
        stats = (
            f"Invites {item.get('invites', 0)}  ·  Verified signups {item.get('verifiedSignups', 0)}  ·  "
            f"Qualified Pro purchases {item.get('qualifiedPurchases', 0)}  ·  Refunds {item.get('refundedPurchases', 0)}"
        )
        ctk.CTkLabel(card, text=stats, anchor="w").pack(fill="x", padx=10, pady=2)
        payouts = (
            f"Pending ${int(item.get('pendingRewardCents') or 0)/100:.2f}  ·  "
            f"Approved ${int(item.get('approvedRewardCents') or 0)/100:.2f}  ·  "
            f"Paid ${int(item.get('paidRewardCents') or 0)/100:.2f}  ·  "
            f"Rejected ${int(item.get('rejectedRewardCents') or 0)/100:.2f}"
        )
        ctk.CTkLabel(card, text=payouts, text_color="#cbd5e1", anchor="w").pack(fill="x", padx=10, pady=(2, 8))

    def _program_card(self, item):
        meta = item.get("metadata") or {}
        tiers = meta.get("tiers") or []
        tier_text = ", ".join([
            f"{t.get('requiredPurchases')} qualified Pro purchases = ${int(t.get('rewardAmountCents', 0))/100:.2f}"
            for t in tiers
        ]) or f"{item.get('required_purchases')} qualified Pro purchases = ${int(item.get('reward_amount_cents', 0))/100:.2f}"
        hold_days = item.get("refund_hold_days")
        hold_text = f" · payout verification hold {hold_days} day(s)" if hold_days is not None else ""
        self._row(f"{item.get('product_slug')} · {tier_text}{hold_text}")

    def _event_line(self, item):
        meta = item.get("metadata") or {}
        prefix = "[LIVE TEST] " if isinstance(meta, dict) and meta.get("admin_live_test") else ""
        referrer = item.get("referrer_email") or item.get("referrerEmail") or item.get("referral_code_email") or item.get("referrer_user_id") or "unknown referrer"
        cashapp = item.get("referrer_cash_app_tag") or item.get("cashAppTag") or item.get("referral_code_cashapp_handle") or "no Cash App"
        referred = item.get("referred_email") or item.get("referredEmail") or (meta.get("recipient_email") if isinstance(meta, dict) else None) or item.get("referred_user_id") or "unknown recipient"
        code = item.get("referral_code") or item.get("referralCode") or item.get("referral_code_id") or "no code"
        return (
            f"{prefix}{item.get('product_slug')} · {item.get('event_type')} · {item.get('status')} · "
            f"referrer {referrer} · Cash App {cashapp} · code {code} · recipient/purchaser {referred} · ref {item.get('purchase_ref') or 'none'}"
        )

    def _reward_line(self, item):
        meta = item.get("metadata") or {}
        prefix = "[LIVE TEST] " if isinstance(meta, dict) and meta.get("admin_live_test") else ""
        ready = item.get("payout_ready_at") or item.get("payoutReadyAt") or (meta.get("payout_ready_at") if isinstance(meta, dict) else None)
        ready_text = f" · hold until {ready}" if ready else ""
        code = item.get("referral_code") or item.get("referralCode") or item.get("referral_code_id") or "no code"
        account = item.get("account_email") or item.get("email") or "unknown account"
        cashapp = item.get("cashapp_handle") or item.get("account_cash_app_tag") or "missing Cash App"
        return (
            f"{prefix}{item.get('product_slug')} · {item.get('status')} · {account} · code {code} · "
            f"${int(item.get('reward_amount_cents', 0))/100:.2f} · {cashapp}{ready_text}"
        )

    def _section(self, title):
        ctk.CTkLabel(self.list_frame, text=title, font=("Arial", 16, "bold")).pack(anchor="w", padx=8, pady=(14, 4))

    def _row(self, text):
        row = ctk.CTkFrame(self.list_frame)
        row.pack(fill="x", padx=6, pady=4)
        ctk.CTkLabel(row, text=text, anchor="w", wraplength=1180, justify="left").pack(fill="x", padx=8, pady=8)

    def _labeled_entry(self, parent, label, helper, default=""):
        ctk.CTkLabel(parent, text=label, font=("Arial", 13, "bold")).pack(anchor="w", padx=18, pady=(10, 2))
        if helper:
            ctk.CTkLabel(parent, text=helper, text_color="#9ca3af", wraplength=430, justify="left").pack(anchor="w", padx=18, pady=(0, 4))
        entry = ctk.CTkEntry(parent)
        entry.insert(0, default)
        entry.pack(fill="x", padx=18)
        return entry

    def open_create(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Create Referral Code")
        dialog.geometry("500x430")
        dialog.grab_set()
        email = self._labeled_entry(dialog, "Owner email", "Optional. Assigns this referral code to an existing user account.")
        code = self._labeled_entry(dialog, "Referral code", "Optional. Leave blank to auto-generate.")
        cashapp = self._labeled_entry(dialog, "Cash App tag", "Optional payout handle for this creator/user. Example: $YourTag")

        def save():
            try:
                self.client.create_referral_code({"email": email.get().strip(), "code": code.get().strip(), "cashappHandle": cashapp.get().strip()})
                dialog.destroy()
                self.refresh()
            except ApiError as exc:
                show_error(dialog, exc)
        ctk.CTkButton(dialog, text="Create Referral Code", command=save).pack(padx=18, pady=18, fill="x")

    def open_program_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Referral Payout Rule")
        dialog.geometry("520x690")
        dialog.grab_set()
        product = self._labeled_entry(dialog, "Product slug", "Product this rule applies to. TabForge is the live product now.", "tabforge")
        tier1_count = self._labeled_entry(dialog, "Tier 1 qualified Pro purchases", "How many completed Pro purchases trigger the first payout.", "5")
        tier1_amount = self._labeled_entry(dialog, "Tier 1 payout cents", "Example: 1000 = $10.00", "1000")
        tier2_count = self._labeled_entry(dialog, "Tier 2 qualified Pro purchases", "Second payout threshold.", "15")
        tier2_amount = self._labeled_entry(dialog, "Tier 2 payout cents", "Example: 2000 = $20.00", "2000")
        tier3_count = self._labeled_entry(dialog, "Tier 3 qualified Pro purchases", "Third payout threshold.", "50")
        tier3_amount = self._labeled_entry(dialog, "Tier 3 payout cents", "Example: 7500 = $75.00", "7500")
        hold_days = self._labeled_entry(dialog, "Payout verification hold days", "Fraud/refund review window after the qualifying Pro purchase. Use 7-10 days; default is 10.", "10")

        def as_int(entry, name):
            try:
                return int(entry.get().strip())
            except ValueError:
                raise ApiError(f"{name} must be a number.")

        def save():
            try:
                tiers = [
                    {"requiredPurchases": as_int(tier1_count, "Tier 1 purchases"), "rewardAmountCents": as_int(tier1_amount, "Tier 1 payout cents")},
                    {"requiredPurchases": as_int(tier2_count, "Tier 2 purchases"), "rewardAmountCents": as_int(tier2_amount, "Tier 2 payout cents")},
                    {"requiredPurchases": as_int(tier3_count, "Tier 3 purchases"), "rewardAmountCents": as_int(tier3_amount, "Tier 3 payout cents")},
                ]
                self.client.upsert_referral_program({
                    "productSlug": product.get().strip(),
                    "tiers": tiers,
                    "refundHoldDays": as_int(hold_days, "Payout verification hold days"),
                    "rewardType": "cashapp_manual",
                    "status": "active",
                    "metadata": {"qualification": "verified_purchase", "payoutVerificationWindow": "7-10 days"},
                })
                dialog.destroy()
                self.refresh()
            except ApiError as exc:
                show_error(dialog, exc)
        ctk.CTkButton(dialog, text="Save Payout Rule", command=save).pack(padx=18, pady=18, fill="x")
