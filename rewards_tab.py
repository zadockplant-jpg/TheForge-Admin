import csv
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from api_client import ApiError, AdminApiClient
from config import CASHAPP_WEB_URL
from ui_helpers import clear_frame, show_error, show_info


STATUS_ORDER = {"pending": 0, "approved": 1, "rejected": 2, "paid": 3}


class RewardsTab(ctk.CTkFrame):
    def __init__(self, master, client: AdminApiClient):
        super().__init__(master)
        self.client = client
        self.items = []
        self.visible_items = []
        self.selection_vars = {}
        self.status_filter = ctk.StringVar(value="All")
        self.search_text = ctk.StringVar()
        self.summary_label = None
        self.list_frame = None
        self._build()

    def _build(self):
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(top, text="Payouts — real Cash App workflow", font=("Arial", 22, "bold")).pack(side="left")
        ctk.CTkButton(top, text="Refresh", command=self.refresh).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Export visible CSV", command=self.export_visible_csv).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Approve selected", command=self.approve_selected).pack(side="right", padx=4)

        filters = ctk.CTkFrame(self)
        filters.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(filters, text="Status", font=("Arial", 13, "bold")).pack(side="left", padx=(10, 4), pady=8)
        ctk.CTkOptionMenu(
            filters,
            variable=self.status_filter,
            values=["All", "Pending", "Approved", "Paid", "Rejected"],
            command=lambda _value: self.render(),
            width=130,
        ).pack(side="left", padx=4)
        ctk.CTkLabel(filters, text="Search", font=("Arial", 13, "bold")).pack(side="left", padx=(18, 4))
        search = ctk.CTkEntry(filters, textvariable=self.search_text, placeholder_text="Email, Cash App tag, product, payout reference")
        search.pack(side="left", fill="x", expand=True, padx=(4, 10), pady=8)
        search.bind("<KeyRelease>", lambda _event: self.render())

        self.summary_label = ctk.CTkLabel(self, text="", text_color="#cbd5e1", anchor="w")
        self.summary_label.pack(fill="x", padx=16, pady=(2, 5))

        helper = ctk.CTkLabel(
            self,
            text="Real payout flow: referred user buys TabForge Pro → reward row waits through the 7-10 day fraud/refund verification hold → approve → manually send Cash App payment → paste Cash App activity/receipt reference → mark paid. Test rows are blocked here and must be changed in Owner Tools.",
            text_color="#9ca3af",
            wraplength=1080,
            justify="left",
        )
        helper.pack(fill="x", padx=16, pady=(0, 6))

        self.list_frame = ctk.CTkScrollableFrame(self)
        self.list_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.refresh()

    def refresh(self):
        try:
            data = self.client.get_rewards()
            items = data.get("items") or data.get("rewards") or []
            self.items = sorted(
                [item for item in items if isinstance(item, dict)],
                key=lambda item: (
                    STATUS_ORDER.get(str(item.get("status", "")).lower(), 99),
                    str(item.get("created_at") or ""),
                ),
            )
        except ApiError as exc:
            show_error(self, exc)
            return
        self.render()

    def render(self):
        clear_frame(self.list_frame)
        self.selection_vars = {}
        status_filter = self.status_filter.get().strip().lower()
        query = self.search_text.get().strip().lower()

        visible = []
        for item in self.items:
            status = str(item.get("status") or "").lower()
            if status_filter != "all" and status != status_filter:
                continue
            haystack = " ".join(
                str(item.get(key) or "")
                for key in (
                    "email",
                    "cashapp_handle",
                    "product_slug",
                    "payout_reference",
                    "account_email",
                    "account_cash_app_tag",
                    "payout_ready_at",
                    "status",
                    "id",
                )
            ).lower()
            if query and query not in haystack:
                continue
            visible.append(item)

        self.visible_items = visible
        self._update_summary()

        if not visible:
            ctk.CTkLabel(self.list_frame, text="No payouts match the current filters.", text_color="#9ca3af").pack(pady=30)
            return

        for item in visible:
            self._reward_card(item)

    def _update_summary(self):
        counts = {"pending": 0, "approved": 0, "paid": 0, "rejected": 0}
        totals = {"pending": 0, "approved": 0, "paid": 0, "rejected": 0}
        for item in self.items:
            status = str(item.get("status") or "").lower()
            cents = self._amount_cents(item)
            if status in counts:
                counts[status] += 1
                totals[status] += cents
        summary = (
            f"Pending {counts['pending']} (${totals['pending']/100:.2f})   |   "
            f"Approved {counts['approved']} (${totals['approved']/100:.2f})   |   "
            f"Paid {counts['paid']} (${totals['paid']/100:.2f})   |   "
            f"Rejected {counts['rejected']}"
        )
        self.summary_label.configure(text=summary)

    def _reward_card(self, item):
        reward_id = str(item.get("id") or "")
        status = str(item.get("status") or "pending").lower()
        email = str(item.get("email") or "")
        cashapp = str(item.get("cashapp_handle") or "")
        product = str(item.get("product_slug") or "")
        payout_reference = str(item.get("payout_reference") or "")
        amount = self._amount_cents(item) / 100
        meta = item.get("metadata") or {}
        tier = meta.get("tier_required_purchases") if isinstance(meta, dict) else None
        is_test = bool(meta.get("admin_live_test")) if isinstance(meta, dict) else False

        card = ctk.CTkFrame(self.list_frame)
        card.pack(fill="x", padx=6, pady=6)

        heading = ctk.CTkFrame(card, fg_color="transparent")
        heading.pack(fill="x", padx=10, pady=(9, 2))
        selected = ctk.IntVar(value=0)
        if not is_test:
            self.selection_vars[reward_id] = selected
        checkbox = ctk.CTkCheckBox(heading, text="", variable=selected, width=26)
        checkbox.pack(side="left")
        if is_test:
            checkbox.configure(state="disabled")
        title_prefix = "[LIVE TEST ONLY] " if is_test else ""
        ctk.CTkLabel(
            heading,
            text=f"{title_prefix}{status.upper()}  ·  ${amount:.2f}  ·  {product or 'unknown product'}",
            font=("Arial", 15, "bold"),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        if tier:
            ctk.CTkLabel(heading, text=f"Tier: {tier} qualified Pro purchases", text_color="#9ca3af").pack(side="right")

        referral_code = str(item.get("referral_code") or item.get("referralCode") or item.get("referral_code_id") or "")
        details = [
            f"Account: {email or 'missing'}",
            f"Cash App: {cashapp or 'MISSING'}",
            f"Referral code: {referral_code or 'not attached'}",
        ]
        if payout_reference:
            details.append(f"Payout reference: {payout_reference}")
        ctk.CTkLabel(card, text="   |   ".join(details), anchor="w", wraplength=1050).pack(fill="x", padx=14, pady=(2, 4))
        hold_label = self._hold_label(item)
        if hold_label:
            ctk.CTkLabel(card, text=hold_label, text_color="#fbbf24", anchor="w", wraplength=1050).pack(fill="x", padx=14, pady=(0, 7))

        actions = ctk.CTkFrame(card, fg_color="transparent")
        actions.pack(fill="x", padx=10, pady=(0, 9))
        ctk.CTkButton(actions, text="Copy $Cashtag", width=110, command=lambda value=cashapp: self.copy_text(value, "Cash App tag")).pack(side="left", padx=3)
        ctk.CTkButton(actions, text="Copy amount", width=100, command=lambda value=f"{amount:.2f}": self.copy_text(value, "Amount")).pack(side="left", padx=3)
        ctk.CTkButton(actions, text="Open Cash App", width=110, command=lambda: webbrowser.open(CASHAPP_WEB_URL)).pack(side="left", padx=3)

        if is_test:
            ctk.CTkLabel(actions, text="Use Owner Tools tab for TEST payout status changes; real payouts stay here.", text_color="#f59e0b").pack(side="right", padx=6)
            return

        if status == "pending":
            approve = ctk.CTkButton(actions, text="Approve", width=90, command=lambda current=item: self.approve_reward(current))
            approve.pack(side="right", padx=3)
            if not cashapp or not self._hold_complete(item):
                approve.configure(state="disabled")
            ctk.CTkButton(actions, text="Reject", width=80, command=lambda current=item: self.reject_reward(current)).pack(side="right", padx=3)
        elif status == "approved":
            paid = ctk.CTkButton(actions, text="Process payout", width=120, command=lambda current=item: self.open_paid_dialog(current))
            paid.pack(side="right", padx=3)
            if not cashapp or not self._hold_complete(item):
                paid.configure(state="disabled")
            ctk.CTkButton(actions, text="Reject", width=80, command=lambda current=item: self.reject_reward(current)).pack(side="right", padx=3)
            ctk.CTkButton(actions, text="Return pending", width=110, command=lambda current=item: self.set_pending(current)).pack(side="right", padx=3)
        elif status == "rejected":
            ctk.CTkButton(actions, text="Restore pending", width=120, command=lambda current=item: self.set_pending(current)).pack(side="right", padx=3)
        elif status == "paid":
            ctk.CTkLabel(actions, text="Paid rewards are locked.", text_color="#86efac").pack(side="right", padx=6)

    def _amount_cents(self, item):
        try:
            return int(item.get("reward_amount_cents") or 0)
        except (TypeError, ValueError):
            return 0

    @staticmethod
    def _hold_complete(item):
        if not isinstance(item, dict):
            return True
        if RewardsTab._is_live_test_reward(item):
            return True
        value = item.get("payout_hold_complete")
        if value is None:
            value = item.get("payoutHoldComplete")
        return bool(value) if value is not None else True

    @staticmethod
    def _hold_label(item):
        if RewardsTab._hold_complete(item):
            return ""
        ready = item.get("payout_ready_at") or item.get("payoutReadyAt")
        days = item.get("payout_hold_days") or item.get("payoutHoldDays")
        if ready:
            return f"PAYOUT HOLD: do not approve/pay until {ready}"
        if days:
            return f"PAYOUT HOLD: {days} day review window still active"
        return "PAYOUT HOLD: 7-10 day fraud/refund verification window still active"

    def copy_text(self, value, label):
        if not value:
            show_error(self, f"{label} is missing.")
            return
        self.clipboard_clear()
        self.clipboard_append(str(value))
        self.update()

    def approve_reward(self, item, quiet=False):
        reward_id = str(item.get("id") or "")
        cashapp = str(item.get("cashapp_handle") or "")
        if not reward_id:
            return False
        if not cashapp:
            if not quiet:
                show_error(self, "This reward has no verified Cash App tag and cannot be approved.")
            return False
        if not self._hold_complete(item):
            if not quiet:
                show_error(self, self._hold_label(item) or "Payout verification hold is still active. Wait for the 7-10 day fraud/refund review window before approving or paying.")
            return False
        try:
            self.client.update_reward(reward_id, "approved", cashapp_handle=cashapp)
            if not quiet:
                self.refresh()
            return True
        except ApiError as exc:
            if not quiet:
                show_error(self, exc)
            return False

    def approve_selected(self):
        selected_ids = {rid for rid, var in self.selection_vars.items() if var.get() == 1}
        selected = [item for item in self.visible_items if str(item.get("id") or "") in selected_ids]
        pending = [item for item in selected if str(item.get("status") or "").lower() == "pending" and not self._is_live_test_reward(item) and self._hold_complete(item)]
        if not pending:
            show_info(self, "Nothing selected", "Select one or more pending payouts first.")
            return
        missing = [item for item in pending if not str(item.get("cashapp_handle") or "").strip()]
        if missing:
            show_error(self, f"{len(missing)} selected payout(s) have no Cash App tag. Nothing was changed.")
            return
        if not self.confirm("Approve selected payouts", f"Approve {len(pending)} selected payout(s) for manual Cash App processing?"):
            return
        completed = 0
        for item in pending:
            if self.approve_reward(item, quiet=True):
                completed += 1
        self.refresh()
        show_info(self, "Batch approval complete", f"Approved {completed} payout(s).")

    @staticmethod
    def _is_live_test_reward(item):
        meta = item.get("metadata") or {} if isinstance(item, dict) else {}
        return bool(meta.get("admin_live_test")) if isinstance(meta, dict) else False

    def reject_reward(self, item):
        reward_id = str(item.get("id") or "")
        dialog = ctk.CTkToplevel(self)
        dialog.title("Reject payout")
        dialog.geometry("520x300")
        dialog.grab_set()
        ctk.CTkLabel(dialog, text="Reject payout", font=("Arial", 19, "bold")).pack(pady=(18, 6))
        ctk.CTkLabel(dialog, text="A rejection note is required and will be recorded in the admin audit log.", wraplength=450).pack(padx=18, pady=6)
        note = ctk.CTkTextbox(dialog, height=100)
        note.pack(fill="x", padx=18, pady=8)

        def submit():
            value = note.get("1.0", "end").strip()
            if not value:
                show_error(dialog, "Enter a rejection reason.")
                return
            try:
                self.client.update_reward(reward_id, "rejected", note=value)
                dialog.destroy()
                self.refresh()
            except ApiError as exc:
                show_error(dialog, exc)

        ctk.CTkButton(dialog, text="Reject payout", command=submit).pack(padx=18, pady=12, fill="x")

    def set_pending(self, item):
        reward_id = str(item.get("id") or "")
        try:
            self.client.update_reward(reward_id, "pending")
            self.refresh()
        except ApiError as exc:
            show_error(self, exc)

    def open_paid_dialog(self, item):
        reward_id = str(item.get("id") or "")
        cashapp = str(item.get("cashapp_handle") or "")
        amount = self._amount_cents(item) / 100
        email = str(item.get("email") or "")
        product = str(item.get("product_slug") or "")
        if not cashapp:
            show_error(self, "Cash App tag is missing.")
            return
        if not self._hold_complete(item):
            show_error(self, self._hold_label(item) or "Payout verification hold is still active. Wait for the 7-10 day fraud/refund review window before approving or paying.")
            return

        dialog = ctk.CTkToplevel(self)
        dialog.title("Process Cash App payout")
        dialog.geometry("600x570")
        dialog.grab_set()

        ctk.CTkLabel(dialog, text="Process Cash App payout", font=("Arial", 21, "bold")).pack(pady=(18, 5))
        ctk.CTkLabel(dialog, text=f"{email}  ·  {product}", text_color="#9ca3af").pack(pady=(0, 12))

        info = ctk.CTkFrame(dialog)
        info.pack(fill="x", padx=18, pady=5)
        ctk.CTkLabel(info, text=f"Recipient: {cashapp}", font=("Arial", 16, "bold")).pack(anchor="w", padx=14, pady=(12, 4))
        ctk.CTkLabel(info, text=f"Amount: ${amount:.2f}", font=("Arial", 16, "bold")).pack(anchor="w", padx=14, pady=(0, 12))

        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=18, pady=6)
        ctk.CTkButton(buttons, text="Copy $Cashtag", command=lambda: self.copy_text(cashapp, "Cash App tag")).pack(side="left", padx=3)
        ctk.CTkButton(buttons, text="Copy amount", command=lambda: self.copy_text(f"{amount:.2f}", "Amount")).pack(side="left", padx=3)
        ctk.CTkButton(buttons, text="Open Cash App", command=lambda: webbrowser.open(CASHAPP_WEB_URL)).pack(side="left", padx=3)

        ctk.CTkLabel(dialog, text="Cash App transaction / activity reference", font=("Arial", 13, "bold")).pack(anchor="w", padx=18, pady=(16, 3))
        ctk.CTkLabel(dialog, text="Required. Paste the reference shown by Cash App after the money is sent.", text_color="#9ca3af").pack(anchor="w", padx=18, pady=(0, 4))
        reference = ctk.CTkEntry(dialog, placeholder_text="Example: Cash App activity ID or receipt reference")
        reference.pack(fill="x", padx=18, pady=4)

        ctk.CTkLabel(dialog, text="Admin note", font=("Arial", 13, "bold")).pack(anchor="w", padx=18, pady=(12, 3))
        note = ctk.CTkTextbox(dialog, height=85)
        note.pack(fill="x", padx=18, pady=4)

        def mark_paid():
            ref_value = reference.get().strip()
            if not ref_value:
                show_error(dialog, "Enter the Cash App transaction/activity reference before marking this payout paid.")
                return
            if not self.confirm("Confirm payout", f"Confirm that ${amount:.2f} was sent to {cashapp}?\n\nReference: {ref_value}", parent=dialog):
                return
            try:
                self.client.update_reward(
                    reward_id,
                    "paid",
                    note=note.get("1.0", "end").strip(),
                    cashapp_handle=cashapp,
                    payout_reference=ref_value,
                )
                dialog.destroy()
                self.refresh()
            except ApiError as exc:
                show_error(dialog, exc)

        ctk.CTkButton(dialog, text="Mark paid", command=mark_paid).pack(fill="x", padx=18, pady=18)

    def export_visible_csv(self):
        if not self.visible_items:
            show_info(self, "Nothing to export", "No payouts match the current filters.")
            return
        default_name = f"sendforge-payouts-{datetime.now().strftime('%Y%m%d-%H%M')}.csv"
        default_dir = Path.home() / "Downloads"
        if not default_dir.exists():
            default_dir = Path.home()
        path = filedialog.asksaveasfilename(
            parent=self,
            title="Export payout queue",
            initialdir=str(default_dir),
            initialfile=default_name,
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")],
        )
        if not path:
            return
        fields = [
            "reward_id",
            "status",
            "email",
            "cashapp_handle",
            "amount_usd",
            "product_slug",
            "tier_required_purchases",
            "payout_reference",
            "payout_ready_at",
            "payout_hold_complete",
            "created_at",
        ]
        with open(path, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields)
            writer.writeheader()
            for item in self.visible_items:
                meta = item.get("metadata") or {}
                writer.writerow(
                    {
                        "reward_id": item.get("id") or "",
                        "status": item.get("status") or "",
                        "email": item.get("email") or "",
                        "cashapp_handle": item.get("cashapp_handle") or "",
                        "amount_usd": f"{self._amount_cents(item)/100:.2f}",
                        "product_slug": item.get("product_slug") or "",
                        "tier_required_purchases": meta.get("tier_required_purchases") if isinstance(meta, dict) else "",
                        "payout_reference": item.get("payout_reference") or "",
                        "payout_ready_at": item.get("payout_ready_at") or item.get("payoutReadyAt") or "",
                        "payout_hold_complete": self._hold_complete(item),
                        "created_at": item.get("created_at") or "",
                    }
                )
        show_info(self, "Export complete", f"Saved {len(self.visible_items)} payout row(s) to:\n{path}")

    def confirm(self, title, message, parent=None):
        owner = parent or self
        result = {"value": False}
        dialog = ctk.CTkToplevel(owner)
        dialog.title(title)
        dialog.geometry("500x250")
        dialog.grab_set()
        ctk.CTkLabel(dialog, text=title, font=("Arial", 18, "bold")).pack(pady=(20, 8))
        ctk.CTkLabel(dialog, text=message, wraplength=440, justify="left").pack(padx=20, pady=10)
        buttons = ctk.CTkFrame(dialog, fg_color="transparent")
        buttons.pack(fill="x", padx=20, pady=16)

        def choose(value):
            result["value"] = value
            dialog.destroy()

        ctk.CTkButton(buttons, text="Cancel", command=lambda: choose(False)).pack(side="left", expand=True, fill="x", padx=(0, 5))
        ctk.CTkButton(buttons, text="Confirm", command=lambda: choose(True)).pack(side="left", expand=True, fill="x", padx=(5, 0))
        dialog.protocol("WM_DELETE_WINDOW", lambda: choose(False))
        owner.wait_window(dialog)
        return result["value"]
