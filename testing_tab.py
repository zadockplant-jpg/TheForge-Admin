import webbrowser
from datetime import datetime

import customtkinter as ctk

from api_client import ApiError, AdminApiClient
from ui_helpers import clear_frame, show_error, show_info


OWNER_EMAIL = "zadockplant@gmail.com"

LEGACY_SKIN_ENTITLEMENT_ALIASES = {
    "tabforge-skin-terminal": "tabforge-skin-bundle-command-center",
    "tabforge-skin-neon": "tabforge-skin-bundle-creator-money",
    "tabforge-skin-executive": "tabforge-skin-bundle-wild-forge",
    "tabforge-skin-command-center": "tabforge-skin-bundle-command-center",
    "tabforge-skin-creator-money": "tabforge-skin-bundle-creator-money",
    "tabforge-skin-wild-forge": "tabforge-skin-bundle-wild-forge",
}


CANONICAL_SKIN_ENTITLEMENT_LABELS = {
    "tabforge-skin-bundle-command-center": "Star Base",
    "tabforge-skin-bundle-creator-money": "Creator",
    "tabforge-skin-bundle-wild-forge": "Wild Forge",
}


def canonical_entitlement_slug(value):
    slug = str(value or "").strip().lower()
    return LEGACY_SKIN_ENTITLEMENT_ALIASES.get(slug, slug)

def normalized_catalog_item(item):
    if not isinstance(item, dict):
        return None
    normalized = dict(item)
    slug = canonical_entitlement_slug(normalized.get("slug"))
    if slug:
        normalized["slug"] = slug
    if slug in CANONICAL_SKIN_ENTITLEMENT_LABELS:
        normalized["label"] = CANONICAL_SKIN_ENTITLEMENT_LABELS[slug]
    return normalized


def normalized_catalog_section(section):
    if not isinstance(section, dict):
        return None
    normalized = dict(section)
    items = []
    seen = set()
    for item in section.get("items") or []:
        normalized_item = normalized_catalog_item(item)
        if not normalized_item:
            continue
        slug = normalized_item.get("slug")
        if slug and slug in seen:
            continue
        if slug:
            seen.add(slug)
        items.append(normalized_item)
    normalized["items"] = items
    if normalized.get("key") == "skin_packs":
        normalized["key"] = "future_visual_addons"
        normalized["title"] = "Future visual add-ons"
        normalized["description"] = "Skins and icon packs are delayed future one-time add-ons; no active checkout yet."
    return normalized


FALLBACK_CATALOG = [
    {
        "key": "product_features",
        "title": "Product features",
        "description": "Current TabForge billing profile and compatibility aliases.",
        "items": [
            {"slug": "tabforge", "label": "TabForge Pro", "description": "$10 one-time purchase: local notes/images on 1 device."},
            {"slug": "tabforge-subscription", "label": "Sync + Collections", "description": "$5/month: Pro while active, current collections, 20GB profile, up to 5 devices. Cloud provider is admin-only/stubbed until wired."},
            {"slug": "tabforge-sync-collections", "label": "Sync + Collections Alias", "description": "Compatibility alias for the current subscription entitlement."},
            {"slug": "tabforge-collections", "label": "Collections Legacy Alias", "description": "Legacy compatibility entitlement included with Sync + Collections."},
        ],
    },
    {
        "key": "shortcut_packs",
        "title": "Included collection entitlements",
        "description": "Collections are no longer sold individually; these are included while Sync + Collections is active.",
        "items": [
            {"slug": "tabforge-pack-builder", "label": "Builder Collection"},
            {"slug": "tabforge-pack-money", "label": "Money Collection"},
            {"slug": "tabforge-pack-dev", "label": "Developer Collection"},
            {"slug": "tabforge-pack-media", "label": "Media Collection"},
            {"slug": "tabforge-pack-research", "label": "Research Collection"},
        ],
    },
    {
        "key": "future_visual_addons",
        "title": "Future visual add-ons",
        "description": "Skins and icon packs are delayed and will be future one-time add-ons.",
        "items": [
            {"slug": "tabforge-skin-bundle-command-center", "label": "Star Base"},
            {"slug": "tabforge-skin-bundle-creator-money", "label": "Creator"},
            {"slug": "tabforge-skin-bundle-wild-forge", "label": "Wild Forge"},
        ],
    },
]


class TestingTab(ctk.CTkFrame):
    """Owner-only live account controls for referral testing and real owner entitlements."""

    def __init__(self, master, client: AdminApiClient):
        super().__init__(master)
        self.client = client
        self.state = {}
        self.referral_confirmed = ctk.BooleanVar(value=False)
        self.restore_cashapp = ctk.BooleanVar(value=True)
        self.custom_entitlement_slug = ctk.StringVar(value="")
        self.vars = {
            "cashAppTag": ctk.StringVar(value=""),
            "invites": ctk.StringVar(value="0"),
            "verifiedAccounts": ctk.StringVar(value="0"),
            "qualifiedPurchases": ctk.StringVar(value="0"),
            "refundedPurchases": ctk.StringVar(value="0"),
        }
        self.status_label = None
        self.entitlement_controls_frame = None
        self.referral_controls_frame = None
        self.summary_frame = None
        self.entitlement_frame = None
        self.rewards_frame = None
        self.log_frame = None
        self._build()
        self.refresh()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=12, pady=(12, 6))
        ctk.CTkLabel(header, text="Owner Account Tools", font=("Arial", 22, "bold")).pack(side="left")
        ctk.CTkButton(header, text="Open live account", command=lambda: webbrowser.open("https://sendforge.app/account/")).pack(side="right", padx=4)
        ctk.CTkButton(header, text="Refresh", width=90, command=self.refresh).pack(side="right", padx=4)

        warning = ctk.CTkFrame(self, fg_color="#4a2108")
        warning.pack(fill="x", padx=12, pady=(0, 10))
        ctk.CTkLabel(
            warning,
            text=(
                f"OWNER ACCOUNT TOOLS — restricted to {OWNER_EMAIL}. Entitlement controls write REAL owned "
                "backend rows for this one account only. Referral-flow controls create tagged simulation rows only. "
                "No emails, Stripe charges, or Cash App transfers are sent from this tab."
            ),
            text_color="#fbbf24",
            wraplength=1160,
            justify="left",
        ).pack(fill="x", padx=12, pady=10)

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=12, pady=(0, 12))
        body.grid_columnconfigure(0, weight=2)
        body.grid_columnconfigure(1, weight=3)
        body.grid_rowconfigure(0, weight=1)

        left = ctk.CTkScrollableFrame(body, label_text="Owner controls")
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        right = ctk.CTkFrame(body)
        right.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        right.grid_columnconfigure(0, weight=1)
        right.grid_rowconfigure(1, weight=2)
        right.grid_rowconfigure(2, weight=2)
        right.grid_rowconfigure(3, weight=1)
        right.grid_rowconfigure(4, weight=1)

        self.entitlement_controls_frame = ctk.CTkFrame(left, fg_color="#101827")
        self.entitlement_controls_frame.pack(fill="x", padx=10, pady=(8, 10))

        self.referral_controls_frame = ctk.CTkFrame(left, fg_color="#101827")
        self.referral_controls_frame.pack(fill="x", padx=10, pady=(8, 10))
        self._build_referral_controls_static(self.referral_controls_frame)

        self.status_label = ctk.CTkLabel(left, text="", wraplength=430, justify="left", text_color="#9ca3af")
        self.status_label.pack(fill="x", padx=10, pady=10)

        ctk.CTkLabel(right, text="Live backend/account state", font=("Arial", 16, "bold")).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 4))
        self.summary_frame = ctk.CTkScrollableFrame(right)
        self.summary_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.entitlement_frame = ctk.CTkScrollableFrame(right, label_text="Owned on extension / account")
        self.entitlement_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.rewards_frame = ctk.CTkScrollableFrame(right, label_text="Referral payout simulator")
        self.rewards_frame.grid(row=3, column=0, sticky="nsew", padx=10, pady=(0, 8))
        self.log_frame = ctk.CTkScrollableFrame(right, label_text="Owner Tools log")
        self.log_frame.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 10))

    def _build_referral_controls_static(self, box):
        ctk.CTkLabel(box, text="Referral flow simulator — TEST ROWS ONLY", font=("Arial", 16, "bold"), anchor="w").pack(fill="x", padx=10, pady=(10, 3))
        ctk.CTkLabel(
            box,
            text=(
                "Use this section to test referral counts, tier triggers, and payout-status behavior on the live account page. "
                "These rows are tagged and resettable. They do not create real purchases or real Cash App transfers."
            ),
            text_color="#9ca3af",
            wraplength=430,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 8))
        self._entry(box, "Cash App tag", "cashAppTag", "Uses the real account save/uniqueness path. Reset can restore the original tag.")
        self._entry(box, "Fake invites sent", "invites", "Visible in live referral totals, but never paid by itself.")
        self._entry(box, "Fake verified accounts", "verifiedAccounts", "Verified signups only; these do not count toward payout.")
        self._entry(box, "Fake qualified Pro purchases", "qualifiedPurchases", "These count toward the real 5 / 15 / 50 tier display.")
        self._entry(box, "Fake refunded Pro purchases", "refundedPurchases", "Stored as refunded and excluded from qualified totals.")

        ctk.CTkCheckBox(
            box,
            text=f"I understand this changes live referral-test data for {OWNER_EMAIL}",
            variable=self.referral_confirmed,
        ).pack(anchor="w", padx=10, pady=(10, 8))
        ctk.CTkButton(box, text="Apply exact referral test state", command=self.apply_state).pack(fill="x", padx=10, pady=4)

        ctk.CTkLabel(box, text="Quick qualified-purchase thresholds", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(16, 5))
        quick = ctk.CTkFrame(box, fg_color="transparent")
        quick.pack(fill="x", padx=10)
        for value in (0, 4, 5, 14, 15, 24, 25, 49, 50, 74, 75, 100):
            ctk.CTkButton(quick, text=str(value), width=56, command=lambda v=value: self.set_purchase_count(v)).pack(side="left", padx=2, pady=2)

        ctk.CTkLabel(box, text="Increment live flow", font=("Arial", 14, "bold")).pack(anchor="w", padx=10, pady=(16, 5))
        for text, action in [
            ("+1 Invite", "invite"),
            ("+1 Verified account", "verify"),
            ("+1 Qualified Pro purchase", "purchase"),
            ("+1 Refunded Pro purchase", "refund"),
        ]:
            ctk.CTkButton(box, text=text, command=lambda a=action: self.step(a, 1)).pack(fill="x", padx=10, pady=2)

        reset_box = ctk.CTkFrame(box, fg_color="#271313")
        reset_box.pack(fill="x", padx=10, pady=(18, 10))
        ctk.CTkCheckBox(reset_box, text="Restore original Cash App tag", variable=self.restore_cashapp).pack(anchor="w", padx=10, pady=(10, 4))
        ctk.CTkButton(
            reset_box,
            text="RESET REFERRAL TEST DATA",
            fg_color="#991b1b",
            hover_color="#b91c1c",
            command=self.reset,
        ).pack(fill="x", padx=10, pady=(4, 10))

    def _entry(self, parent, label, key, helper):
        ctk.CTkLabel(parent, text=label, font=("Arial", 12, "bold"), anchor="w").pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkEntry(parent, textvariable=self.vars[key]).pack(fill="x", padx=10)
        ctk.CTkLabel(parent, text=helper, text_color="#9ca3af", wraplength=410, justify="left").pack(anchor="w", padx=10, pady=(2, 4))

    @staticmethod
    def _count(value, label):
        try:
            result = int(str(value).strip() or "0")
        except ValueError as exc:
            raise ApiError(f"{label} must be a whole number.") from exc
        if result < 0 or result > 1000000:
            raise ApiError(f"{label} must be between 0 and 1,000,000.")
        return result

    def _require_referral_confirmation(self):
        if not self.referral_confirmed.get():
            raise ApiError("Check the referral-test confirmation box in the Referral flow simulator section first.")

    def _payload(self):
        self._require_referral_confirmation()
        return {
            "invites": self._count(self.vars["invites"].get(), "Invites"),
            "verifiedAccounts": self._count(self.vars["verifiedAccounts"].get(), "Verified accounts"),
            "qualifiedPurchases": self._count(self.vars["qualifiedPurchases"].get(), "Qualified purchases"),
            "refundedPurchases": self._count(self.vars["refundedPurchases"].get(), "Refunded purchases"),
            "cashAppTag": self.vars["cashAppTag"].get().strip() or None,
        }

    def refresh(self):
        try:
            self.state = self.client.get_live_testing()
            self._load_form()
            self._render()
            self._set_status("Live owner state loaded from backend.")
        except ApiError as exc:
            self._render_locked(str(exc))

    def _render_locked(self, message):
        for frame in (self.entitlement_controls_frame, self.summary_frame, self.entitlement_frame, self.rewards_frame, self.log_frame):
            if frame is not None:
                clear_frame(frame)
        if self.summary_frame is not None:
            ctk.CTkLabel(
                self.summary_frame,
                text=(
                    "Owner Tools are locked or the backend endpoints are not deployed. "
                    f"This tab only works when the authenticated admin is {OWNER_EMAIL} and /v1/admin/testing/live is enabled."
                ),
                text_color="#fbbf24",
                wraplength=700,
                justify="left",
            ).pack(anchor="w", padx=10, pady=(12, 6))
            ctk.CTkLabel(self.summary_frame, text=f"Backend response: {message}", text_color="#fca5a5", wraplength=700, justify="left").pack(anchor="w", padx=10, pady=6)
        self._set_status(f"Owner Tools locked/unavailable: {message}")

    def _load_form(self):
        counts = self.state.get("counts") or {}
        account = self.state.get("account") or {}
        self.vars["cashAppTag"].set(account.get("cashAppTag") or "")
        self.vars["invites"].set(str(counts.get("testInvites", 0)))
        self.vars["verifiedAccounts"].set(str(counts.get("testVerifiedAccounts", 0)))
        self.vars["qualifiedPurchases"].set(str(counts.get("testQualifiedPurchases", 0)))
        self.vars["refundedPurchases"].set(str(counts.get("testRefundedPurchases", 0)))

    def _catalog_sections(self):
        catalog = self.state.get("entitlementCatalog") or {}
        sections = catalog.get("sections") if isinstance(catalog, dict) else None
        if isinstance(sections, list) and sections:
            return [section for section in (normalized_catalog_section(section) for section in sections) if section]
        presets = self.state.get("entitlementPresets") or []
        if presets:
            grouped = {"product_features": [], "shortcut_packs": [], "future_visual_addons": []}
            for item in presets:
                if isinstance(item, dict):
                    category = item.get("category") or "shortcut_packs"
                    if category == "skin_packs":
                        category = "future_visual_addons"
                    grouped.setdefault(category, []).append(normalized_catalog_item(item))
            return [
                normalized_catalog_section({"key": "product_features", "title": "Product features", "description": "Current account-level purchases and subscription aliases.", "items": grouped.get("product_features") or []}),
                normalized_catalog_section({"key": "shortcut_packs", "title": "Included collection entitlements", "description": "Collections are included with Sync + Collections only.", "items": grouped.get("shortcut_packs") or []}),
                normalized_catalog_section({"key": "future_visual_addons", "title": "Future visual add-ons", "description": "Skins and icon packs are delayed future one-time add-ons.", "items": grouped.get("future_visual_addons") or []}),
            ]
        return [section for section in (normalized_catalog_section(section) for section in FALLBACK_CATALOG) if section]

    def _catalog_by_slug(self):
        result = {}
        for section in self._catalog_sections():
            for item in section.get("items") or []:
                slug = canonical_entitlement_slug(item.get("slug"))
                if slug:
                    result[slug] = item
        for legacy_slug, canonical_slug in LEGACY_SKIN_ENTITLEMENT_ALIASES.items():
            if canonical_slug in result:
                result[legacy_slug] = result[canonical_slug]
        return result

    def _entitlement_map(self):
        result = {}
        for item in (self.state.get("entitlements") or []):
            if not isinstance(item, dict):
                continue
            slug = canonical_entitlement_slug(item.get("productSlug"))
            if slug:
                result[slug] = item
        return result

    def _render(self):
        for frame in (self.entitlement_controls_frame, self.summary_frame, self.entitlement_frame, self.rewards_frame, self.log_frame):
            clear_frame(frame)
        self._render_entitlement_controls()
        self._render_summary()
        self._render_owned_entitlements()
        self._render_rewards()
        self._render_logs()

    def _render_entitlement_controls(self):
        box = self.entitlement_controls_frame
        ctk.CTkLabel(box, text="Real owner entitlement controls", font=("Arial", 16, "bold"), anchor="w").pack(fill="x", padx=10, pady=(10, 2))
        ctk.CTkLabel(
            box,
            text=(
                "Enable/Disable writes real owned backend entitlements for the owner account only. "
                "Items are grouped as product features, subscription-included collections, and delayed visual add-ons. "
                "Cloud saves currently work only for the owner email until the provider is wired in."
            ),
            text_color="#9ca3af",
            wraplength=430,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 8))
        for section in self._catalog_sections():
            self._entitlement_section(box, section)

        custom = ctk.CTkFrame(box, fg_color="#0f172a")
        custom.pack(fill="x", padx=10, pady=(12, 10))
        ctk.CTkLabel(custom, text="Advanced custom tabforge-* slug", font=("Arial", 13, "bold")).pack(anchor="w", padx=10, pady=(10, 2))
        ctk.CTkLabel(
            custom,
            text="Only use this for compatibility aliases or new tabforge-* slugs that are not listed above.",
            text_color="#9ca3af",
            wraplength=390,
            justify="left",
        ).pack(anchor="w", padx=10, pady=(0, 5))
        ctk.CTkEntry(custom, textvariable=self.custom_entitlement_slug, placeholder_text="example: tabforge-sync-collections").pack(fill="x", padx=10, pady=(0, 6))
        row = ctk.CTkFrame(custom, fg_color="transparent")
        row.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkButton(row, text="Enable custom slug", command=lambda: self.set_custom_entitlement(True)).pack(side="left", fill="x", expand=True, padx=(0, 4))
        ctk.CTkButton(row, text="Disable custom admin grant", fg_color="#6b1f1f", hover_color="#8b2525", command=lambda: self.set_custom_entitlement(False)).pack(side="left", fill="x", expand=True, padx=(4, 0))

    def _entitlement_section(self, parent, section):
        title = section.get("title") or section.get("key") or "Entitlements"
        ctk.CTkLabel(parent, text=title, font=("Arial", 14, "bold"), anchor="w").pack(fill="x", padx=10, pady=(12, 3))
        desc = section.get("description")
        if desc:
            ctk.CTkLabel(parent, text=desc, text_color="#9ca3af", wraplength=410, justify="left").pack(anchor="w", padx=10, pady=(0, 5))
        items = section.get("items") or []
        if not items:
            ctk.CTkLabel(parent, text="No catalog items in this section.", text_color="#9ca3af").pack(anchor="w", padx=10, pady=4)
            return
        for item in items:
            self._entitlement_action_row(parent, item)

    def _entitlement_action_row(self, parent, item):
        slug = canonical_entitlement_slug(item.get("slug"))
        ent = self._entitlement_map().get(slug)
        is_active = str(ent.get("status") or "").lower() == "active" if ent else False
        protected = bool(ent and ent.get("protectedRealEntitlement"))
        can_remove = bool(ent and ent.get("canRemove"))
        status_text, status_color = self._status_for_slug(slug)
        row_color = "#12351f" if is_active else "#1f2937"
        frame = ctk.CTkFrame(parent, fg_color=row_color)
        frame.pack(fill="x", padx=10, pady=4)
        left = ctk.CTkFrame(frame, fg_color="transparent")
        left.pack(side="left", fill="both", expand=True, padx=8, pady=8)
        ctk.CTkLabel(left, text=item.get("label") or slug, font=("Arial", 12, "bold"), anchor="w").pack(fill="x")
        ctk.CTkLabel(left, text=slug, text_color="#93c5fd", anchor="w").pack(fill="x")
        if item.get("description"):
            ctk.CTkLabel(left, text=item.get("description"), text_color="#9ca3af", wraplength=280, justify="left", anchor="w").pack(fill="x", pady=(2, 0))
        ctk.CTkLabel(left, text=status_text, text_color=status_color, wraplength=280, justify="left", anchor="w").pack(fill="x", pady=(4, 0))
        right = ctk.CTkFrame(frame, fg_color="transparent")
        right.pack(side="right", padx=8, pady=8)
        enable = ctk.CTkButton(right, text="Enable", width=82, command=lambda s=slug: self.set_catalog_entitlement(s, True))
        enable.pack(side="left", padx=2)
        disable = ctk.CTkButton(right, text="Disable", width=82, fg_color="#6b1f1f", hover_color="#8b2525", command=lambda s=slug: self.set_catalog_entitlement(s, False))
        disable.pack(side="left", padx=2)
        if is_active:
            enable.configure(state="disabled")
        if protected or not can_remove:
            disable.configure(state="disabled")

    def _status_for_slug(self, slug):
        ent = self._entitlement_map().get(canonical_entitlement_slug(slug))
        if not ent:
            return "Inactive — not currently owned by this account", "#9ca3af"
        status = str(ent.get("status") or "").lower()
        if status == "active" and ent.get("isOwnerGrant"):
            return "ACTIVE — enabled by Owner Tools", "#86efac"
        if status == "active" and ent.get("protectedRealEntitlement"):
            return "ACTIVE — owned from purchase/manual grant; Disable is protected", "#93c5fd"
        if status == "active":
            return f"ACTIVE · {ent.get('source') or 'unknown source'}", "#86efac"
        if status == "revoked":
            return "Inactive — prior Owner Tools grant was disabled", "#fca5a5"
        return f"{status or 'unknown'} · {ent.get('source') or 'unknown source'}", "#facc15"

    def _render_summary(self):
        state = self.state or {}
        account = state.get("account") or {}
        counts = state.get("counts") or {}
        rows = [
            ("Target account", state.get("ownerEmail")),
            ("Referral code", account.get("referralCode") or "Not generated"),
            ("Cash App tag", account.get("cashAppTag") or "Not set"),
            ("Email verified", "Yes" if account.get("emailVerified") else "No"),
            ("Test invites", counts.get("testInvites", 0)),
            ("Test verified accounts", counts.get("testVerifiedAccounts", 0)),
            ("Test qualified Pro purchases", counts.get("testQualifiedPurchases", 0)),
            ("Test refunded purchases", counts.get("testRefundedPurchases", 0)),
            ("Real qualified Pro purchases", counts.get("realVerifiedPurchases", 0)),
            ("Effective live qualified total", counts.get("effectiveVerifiedPurchases", 0)),
        ]
        cloud = state.get("cloud") or {}
        rows.extend([
            ("Cloud save mode", "Admin-only enabled" if cloud.get("enabled") else "Stubbed / disabled"),
            ("Cloud owner account", cloud.get("ownerEmail") or OWNER_EMAIL),
            ("Cloud storage profile", f"{cloud.get('cloudStorageLimitGb') or 20}GB"),
            ("Cloud provider", cloud.get("providerStatus") or "stubbed_until_provider"),
        ])
        for label, value in rows:
            self._summary_row(label, value)
        tiers = state.get("tiers") or []
        ctk.CTkLabel(self.summary_frame, text="Live payout tiers", font=("Arial", 14, "bold")).pack(anchor="w", padx=6, pady=(12, 4))
        for tier in tiers:
            amount = int(tier.get("rewardAmountCents", 0)) / 100
            status = "REACHED" if tier.get("reached") else f"{tier.get('remaining', 0)} remaining"
            hold = tier.get("payoutHoldDays")
            hold_text = f" · {hold} day payout verification hold" if hold is not None else ""
            ctk.CTkLabel(
                self.summary_frame,
                text=f"{tier.get('requiredPurchases')} qualified Pro purchases → ${amount:.2f} · {status}{hold_text}",
                anchor="w",
            ).pack(fill="x", padx=8, pady=2)

    def _summary_row(self, label, value):
        card = ctk.CTkFrame(self.summary_frame)
        card.pack(fill="x", padx=4, pady=3)
        ctk.CTkLabel(card, text=label, font=("Arial", 12, "bold"), width=220, anchor="w").pack(side="left", padx=8, pady=7)
        ctk.CTkLabel(card, text=str(value), anchor="w").pack(side="left", fill="x", expand=True, padx=8, pady=7)

    def _render_owned_entitlements(self):
        ctk.CTkLabel(
            self.entitlement_frame,
            text="This mirrors what TabForge should see after Refresh Purchases. Status is returned by the backend after every Enable/Disable action.",
            text_color="#9ca3af",
            wraplength=720,
            justify="left",
        ).pack(anchor="w", padx=8, pady=(8, 10))
        catalog = self._catalog_by_slug()
        for section in self._catalog_sections():
            ctk.CTkLabel(self.entitlement_frame, text=section.get("title") or section.get("key"), font=("Arial", 14, "bold")).pack(anchor="w", padx=8, pady=(10, 3))
            for item in section.get("items") or []:
                slug = str(item.get("slug") or "").lower()
                status_text, color = self._status_for_slug(slug)
                row = ctk.CTkFrame(self.entitlement_frame)
                row.pack(fill="x", padx=6, pady=3)
                ctk.CTkLabel(row, text=item.get("label") or slug, width=180, font=("Arial", 12, "bold"), anchor="w").pack(side="left", padx=8, pady=7)
                ctk.CTkLabel(row, text=slug, text_color="#93c5fd", width=205, anchor="w").pack(side="left", padx=4, pady=7)
                ctk.CTkLabel(row, text=status_text, text_color=color, anchor="w").pack(side="left", padx=8, pady=7, fill="x", expand=True)
        extra = [item for slug, item in self._entitlement_map().items() if slug not in catalog]
        if extra:
            ctk.CTkLabel(self.entitlement_frame, text="Other active/legacy entitlements returned by backend", font=("Arial", 14, "bold")).pack(anchor="w", padx=8, pady=(14, 3))
            for item in extra:
                line = f"{item.get('productSlug')} · {item.get('status')} · {item.get('source')}"
                ctk.CTkLabel(self.entitlement_frame, text=line, anchor="w", wraplength=700, text_color="#facc15").pack(fill="x", padx=8, pady=2)

    def _render_rewards(self):
        ctk.CTkLabel(
            self.rewards_frame,
            text="TEST payout-status rows only. These use the same status words as the real Payouts tab, but no external Cash App transfer is sent.",
            text_color="#9ca3af",
            wraplength=720,
            justify="left",
        ).pack(anchor="w", padx=8, pady=(8, 10))
        rewards = self.state.get("testRewards") or []
        if not rewards:
            ctk.CTkLabel(self.rewards_frame, text="No test reward tier reached yet.", text_color="#9ca3af").pack(padx=8, pady=12)
        for reward in rewards:
            self._reward_row(reward)

    def _reward_row(self, reward):
        status = str(reward.get("status") or "pending").lower()
        color = {
            "pending": "#1e3a5f",
            "approved": "#3a2305",
            "rejected": "#451a1a",
            "paid": "#12351f",
        }.get(status, "#27272a")
        row = ctk.CTkFrame(self.rewards_frame, fg_color=color)
        row.pack(fill="x", padx=4, pady=4)
        amount = int(reward.get("rewardAmountCents", 0)) / 100
        label = (
            f"TEST payout · tier {reward.get('tierRequiredPurchases')} · ${amount:.2f} · "
            f"STATUS: {status.upper()} · {reward.get('cashAppHandle') or 'Cash App missing'}"
        )
        ctk.CTkLabel(row, text=label, anchor="w", wraplength=700, font=("Arial", 12, "bold")).pack(fill="x", padx=8, pady=(7, 4))
        ctk.CTkLabel(row, text="Click a next action. The card updates only after the backend confirms the new status.", text_color="#d1d5db", wraplength=700, justify="left").pack(fill="x", padx=8, pady=(0, 4))
        actions = ctk.CTkFrame(row, fg_color="transparent")
        actions.pack(fill="x", padx=8, pady=(0, 7))
        if status == "pending":
            self._reward_button(actions, "Approve TEST", reward, "approved")
            self._reward_button(actions, "Reject TEST", reward, "rejected", danger=True)
        elif status == "approved":
            self._reward_button(actions, "Mark TEST paid", reward, "paid")
            self._reward_button(actions, "Return pending", reward, "pending")
            self._reward_button(actions, "Reject TEST", reward, "rejected", danger=True)
        elif status == "rejected":
            self._reward_button(actions, "Restore pending", reward, "pending")
        elif status == "paid":
            ctk.CTkLabel(actions, text="TEST paid is locked for display; reset referral test data to clear it.", text_color="#86efac").pack(side="left", padx=3)
        else:
            self._reward_button(actions, "Reset pending", reward, "pending")

    def _reward_button(self, parent, text, reward, status, danger=False):
        ctk.CTkButton(
            parent,
            text=text,
            width=125,
            fg_color="#6b1f1f" if danger else None,
            hover_color="#8b2525" if danger else None,
            command=lambda r=reward.get("id"), s=status: self.set_reward_status(r, s),
        ).pack(side="left", padx=3)

    def _render_logs(self):
        logs = self.state.get("ownerToolLogs") or []
        if not logs:
            ctk.CTkLabel(self.log_frame, text="No owner-tool log entries returned yet.", text_color="#9ca3af").pack(padx=8, pady=10)
            return
        for entry in logs[:20]:
            if not isinstance(entry, dict):
                continue
            ts = entry.get("at") or ""
            action = entry.get("action") or "event"
            detail = entry.get("detail") or entry.get("slug") or entry.get("status") or ""
            ctk.CTkLabel(self.log_frame, text=f"{ts} · {action} · {detail}", anchor="w", wraplength=700, justify="left").pack(fill="x", padx=8, pady=2)

    def _set_status(self, message):
        if self.status_label is not None:
            self.status_label.configure(text=message)

    def apply_state(self):
        try:
            self.state = self.client.apply_live_testing(self._payload())
            self._load_form()
            self._render()
            self._set_status("Referral test state applied. Refresh the public account page to see counts and tiers.")
        except ApiError as exc:
            show_error(self, exc)

    def set_purchase_count(self, value):
        self.vars["qualifiedPurchases"].set(str(value))
        self.apply_state()

    def step(self, action, quantity):
        try:
            self._require_referral_confirmation()
            self.state = self.client.step_live_testing(action, quantity)
            self._load_form()
            self._render()
            self._set_status(f"Applied referral test step: {action} {quantity:+d}")
        except ApiError as exc:
            show_error(self, exc)

    def set_reward_status(self, reward_id, status):
        try:
            if not reward_id:
                raise ApiError("Reward ID missing.")
            self._set_status(f"Updating TEST payout to {status}...")
            self.state = self.client.update_live_test_reward(reward_id, status)
            self._load_form()
            self._render()
            self._set_status(f"TEST payout status changed to {status}. Real payouts use the Payouts tab and the 7-10 day hold.")
        except ApiError as exc:
            show_error(self, exc)

    def _set_entitlement(self, slug, enabled):
        try:
            slug = str(slug or "").strip().lower()
            if not slug:
                raise ApiError("Choose or enter an entitlement slug first.")
            action = "Enabling" if enabled else "Disabling"
            self._set_status(f"{action} {slug}...")
            self.state = self.client.set_owner_entitlement(slug, enabled)
            self._load_form()
            self._render()
            final_action = "ENABLED" if enabled else "DISABLED"
            self._set_status(f"{final_action}: {slug}. Refresh TabForge extension/account purchases to verify.")
            show_info(self, "Owner entitlement updated", f"{final_action}: {slug}\n\nBackend confirmed the current account state. This only applies to {OWNER_EMAIL}.")
        except ApiError as exc:
            show_error(self, exc)

    def set_catalog_entitlement(self, slug, enabled):
        self._set_entitlement(slug, enabled)

    def set_custom_entitlement(self, enabled):
        self._set_entitlement(self.custom_entitlement_slug.get(), enabled)

    def reset(self):
        try:
            self._require_referral_confirmation()
            self.state = self.client.reset_live_testing(bool(self.restore_cashapp.get()))
            self._load_form()
            self._render()
            self._set_status("Tagged referral test events and test rewards were removed. Admin-owned entitlements were left as-is.")
            show_info(self, "Referral test reset", "Real referral events, real rewards, and admin-owned entitlements were left untouched.")
        except ApiError as exc:
            show_error(self, exc)
