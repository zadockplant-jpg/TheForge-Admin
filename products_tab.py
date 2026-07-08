import customtkinter as ctk

from api_client import ApiError, AdminApiClient
from ui_helpers import clear_frame, show_error


class ProductsTab(ctk.CTkFrame):
    def __init__(self, master, client: AdminApiClient):
        super().__init__(master)
        self.client = client
        self.list_frame = None
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=10)
        ctk.CTkLabel(top, text="Product Cards / Catalog", font=("Arial", 20, "bold")).pack(side="left")
        ctk.CTkButton(top, text="Refresh", width=90, command=self.refresh).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Add Product Card", width=150, command=self.open_add_dialog).pack(side="right", padx=4)

        profile = ctk.CTkFrame(self, fg_color="#101827")
        profile.pack(fill="x", padx=10, pady=(0, 10))
        ctk.CTkLabel(profile, text="Current TabForge billing profile", font=("Arial", 15, "bold"), anchor="w").pack(fill="x", padx=12, pady=(10, 3))
        ctk.CTkLabel(
            profile,
            text=(
                "$10 one-time Pro: local notes/images on 1 device.  "
                "$5/month Sync + Collections: current collections, 20GB storage profile, sync across up to 5 devices.  "
                "Cloud hosting is live only for zadockplant@gmail.com until the provider is wired in.  "
                "Skins/icon packs are delayed future one-time add-ons."
            ),
            text_color="#9ca3af",
            wraplength=1120,
            justify="left",
        ).pack(fill="x", padx=12, pady=(0, 10))

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.refresh()

    def refresh(self):
        clear_frame(self.list_frame)
        try:
            data = self.client.get_products()
            products = data.get("items") or data.get("products") or []
        except ApiError as exc:
            show_error(self, exc)
            return
        for product in products:
            self._product_row(product)

    def _product_row(self, product):
        row = ctk.CTkFrame(self.list_frame)
        row.pack(fill="x", padx=6, pady=5)
        title = product.get("name") or product.get("slug") or "Product"
        slug = product.get("slug") or ""
        price_cents = product.get("price_cents") or product.get("priceCents") or 0
        status = product.get("status") or ("active" if product.get("active", True) else "inactive")
        entitlement = product.get("entitlement_slug") or product.get("entitlementSlug") or slug
        billing_type = product.get("billing_type") or product.get("billingType") or product.get("type") or ""
        interval = product.get("interval") or (product.get("metadata") or {}).get("interval") or ""
        ctk.CTkLabel(row, text=title, font=("Arial", 15, "bold"), width=170, anchor="w").pack(side="left", padx=8, pady=8)
        ctk.CTkLabel(row, text=f"slug: {slug}", width=190, anchor="w").pack(side="left", padx=8)
        ctk.CTkLabel(row, text=f"${int(price_cents)/100:.2f}", width=80, anchor="w").pack(side="left", padx=8)
        ctk.CTkLabel(row, text=f"entitlement: {entitlement}", width=220, anchor="w").pack(side="left", padx=8)
        ctk.CTkLabel(row, text=(billing_type + (f"/{interval}" if interval else "")) or status, width=130, anchor="w").pack(side="left", padx=8)
        ctk.CTkLabel(row, text=status, width=90, anchor="w").pack(side="left", padx=8)

    def _labeled_entry(self, parent, label, helper, default=""):
        ctk.CTkLabel(parent, text=label, font=("Arial", 13, "bold")).pack(anchor="w", padx=18, pady=(10, 2))
        if helper:
            ctk.CTkLabel(parent, text=helper, text_color="#9ca3af", wraplength=470, justify="left").pack(anchor="w", padx=18, pady=(0, 4))
        entry = ctk.CTkEntry(parent, width=460)
        entry.insert(0, default)
        entry.pack(padx=18, fill="x")
        return entry

    def open_add_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Add Product Card")
        dialog.geometry("560x680")
        dialog.grab_set()

        fields = {}
        fields["name"] = self._labeled_entry(dialog, "Product name", "Visible display name, for example TabForge Pro or Sync + Collections.", "TabForge Pro")
        fields["slug"] = self._labeled_entry(dialog, "Product slug", "Backend/store ID. Current examples: tabforge, tabforge-subscription, tabforge-sync-collections.", "tabforge")
        fields["description"] = self._labeled_entry(dialog, "Short description", "Use the new billing profile: $10 one-time Pro, or $5/month Sync + Collections with 20GB profile.")
        fields["priceCents"] = self._labeled_entry(dialog, "Price in cents", "Examples: 1000 = $10 one-time Pro; 500 = $5/month subscription.", "1000")
        fields["entitlementSlug"] = self._labeled_entry(dialog, "Entitlement slug", "What the purchase unlocks. Usually same as product slug; subscription aliases are supported.", "tabforge")
        fields["productLine"] = self._labeled_entry(dialog, "Product line", "Use TabForge for the browser extension pricing model.", "TabForge")

        status_var = ctk.StringVar(value="draft")
        ctk.CTkLabel(dialog, text="Status", font=("Arial", 13, "bold")).pack(anchor="w", padx=18, pady=(12, 2))
        ctk.CTkOptionMenu(dialog, variable=status_var, values=["draft", "active", "inactive", "archived"]).pack(fill="x", padx=18)

        def save():
            payload = {key: entry.get().strip() for key, entry in fields.items()}
            payload["status"] = status_var.get()
            if not payload.get("entitlementSlug"):
                payload["entitlementSlug"] = payload.get("slug")
            if not payload.get("productLine"):
                payload["productLine"] = payload.get("slug")
            if payload.get("priceCents"):
                try:
                    payload["priceCents"] = int(payload["priceCents"])
                except ValueError:
                    show_error(dialog, "Price in cents must be a number. Example: 500")
                    return
            try:
                self.client.create_product(payload)
                dialog.destroy()
                self.refresh()
            except ApiError as exc:
                show_error(dialog, exc)

        ctk.CTkButton(dialog, text="Create Product Card", command=save).pack(padx=18, pady=18, fill="x")
