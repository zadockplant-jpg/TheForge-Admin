import json
import os
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

import customtkinter as ctk

from api_client import ApiError, AdminApiClient
from ui_helpers import clear_frame, show_error, show_info


AUDIT_EXPORT_ROOT = Path.home() / "SendForge Admin Audit Logs"


def _safe_text(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback
    text = str(value).strip()
    return text if text else fallback


def _slug(value: Any, fallback: str = "item") -> str:
    text = _safe_text(value, fallback).lower()
    text = re.sub(r"[^a-z0-9._-]+", "-", text).strip("-._")
    return text[:80] or fallback


def _parse_dt(value: Any) -> Optional[datetime]:
    if not value:
        return None
    text = str(value)
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        return datetime.fromisoformat(text)
    except ValueError:
        return None


def _date_key(item: Dict[str, Any]) -> str:
    dt = _parse_dt(item.get("created_at") or item.get("createdAt") or item.get("timestamp"))
    if dt:
        return dt.date().isoformat()
    return "unknown-date"


def _time_label(item: Dict[str, Any]) -> str:
    dt = _parse_dt(item.get("created_at") or item.get("createdAt") or item.get("timestamp"))
    if not dt:
        return "unknown time"
    try:
        if dt.tzinfo is not None:
            dt = dt.astimezone()
    except Exception:
        pass
    return dt.strftime("%I:%M:%S %p").lstrip("0")


def _coerce_dict(value: Any) -> Dict[str, Any]:
    if isinstance(value, dict):
        return value
    if isinstance(value, str):
        try:
            loaded = json.loads(value)
            if isinstance(loaded, dict):
                return loaded
        except Exception:
            return {}
    return {}


def _flatten_interesting_values(value: Any) -> Dict[str, Any]:
    """Pull common diagnostic values out of nested before/after metadata."""
    found: Dict[str, Any] = {}
    wanted = {
        "email",
        "admin_email",
        "owner_email",
        "target_email",
        "referrer_email",
        "recipient_email",
        "purchaser_email",
        "cash_app_tag",
        "cashapp_handle",
        "cashappHandle",
        "referral_code",
        "referralCode",
        "product_slug",
        "productSlug",
        "status",
        "source",
        "payout_reference",
        "payoutReference",
    }

    def walk(obj: Any) -> None:
        if isinstance(obj, dict):
            for key, inner in obj.items():
                if key in wanted and inner not in (None, "") and key not in found:
                    found[key] = inner
                if isinstance(inner, (dict, list)):
                    walk(inner)
        elif isinstance(obj, list):
            for inner in obj[:30]:
                walk(inner)

    walk(value)
    return found


def _item_action(item: Dict[str, Any]) -> str:
    return _safe_text(item.get("action") or item.get("event") or item.get("type"), "unknown.action")


def _item_id(item: Dict[str, Any]) -> str:
    return _safe_text(item.get("id") or item.get("audit_id") or item.get("event_id"), "no-id")


def _item_summary(item: Dict[str, Any]) -> str:
    action = _item_action(item)
    resource = _safe_text(item.get("resource_type") or item.get("resourceType"), "resource")
    resource_id = _safe_text(item.get("resource_id") or item.get("resourceId"), "")
    admin_email = _safe_text(item.get("admin_email") or item.get("adminEmail"), "unknown admin")
    before = _coerce_dict(item.get("before_value") or item.get("beforeValue"))
    after = _coerce_dict(item.get("after_value") or item.get("afterValue"))
    merged = {}
    merged.update(_flatten_interesting_values(before))
    merged.update(_flatten_interesting_values(after))
    bits = [f"{_time_label(item)}", action, f"admin {admin_email}"]
    if resource:
        bits.append(resource if not resource_id else f"{resource}:{resource_id}")
    for key, label in (
        ("owner_email", "owner"),
        ("target_email", "target"),
        ("email", "email"),
        ("referrer_email", "referrer"),
        ("recipient_email", "recipient"),
        ("purchaser_email", "purchaser"),
        ("cash_app_tag", "cash app"),
        ("cashapp_handle", "cash app"),
        ("cashappHandle", "cash app"),
        ("referral_code", "ref code"),
        ("referralCode", "ref code"),
        ("product_slug", "product"),
        ("productSlug", "product"),
        ("status", "status"),
        ("payout_reference", "payout ref"),
        ("payoutReference", "payout ref"),
    ):
        if key in merged:
            bits.append(f"{label} {merged[key]}")
    return " · ".join(str(part) for part in bits if str(part).strip())


def _pretty_item(item: Dict[str, Any]) -> str:
    lines = [
        "SendForge Admin Audit Event",
        "===========================",
        f"Date: {_date_key(item)}",
        f"Time: {_time_label(item)}",
        f"Action: {_item_action(item)}",
        f"ID: {_item_id(item)}",
        f"Admin: {_safe_text(item.get('admin_email') or item.get('adminEmail'), 'unknown admin')}",
        f"Resource: {_safe_text(item.get('resource_type') or item.get('resourceType'), 'unknown')} / {_safe_text(item.get('resource_id') or item.get('resourceId'), 'no resource id')}",
        "",
        "Readable summary",
        "----------------",
        _item_summary(item),
        "",
        "Raw JSON",
        "--------",
        json.dumps(item, indent=2, sort_keys=True, default=str),
        "",
    ]
    return "\n".join(lines)


class AuditLogTab(ctk.CTkFrame):
    """Audit log browser that avoids dumping a giant raw JSON wall into the UI.

    Refresh downloads recent audit events, writes each event to a dated text file, and
    renders a light browse view: Date -> Action/Event -> Event cards. Clicking Open TXT
    opens the saved file in the system text editor.
    """

    def __init__(self, master, client: AdminApiClient):
        super().__init__(master)
        self.client = client
        self.items: List[Dict[str, Any]] = []
        self.files_by_id: Dict[str, Path] = {}
        self.date_var = ctk.StringVar(value="")
        self.action_var = ctk.StringVar(value="All events")
        self.status_label = None
        self.date_frame = None
        self.action_menu = None
        self.event_frame = None
        self.preview_box = None
        self.search_var = ctk.StringVar(value="")
        self.limit_var = ctk.StringVar(value="250")
        self._build()

    def _build(self) -> None:
        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(10, 4))
        ctk.CTkLabel(top, text="Audit Log", font=("Arial", 22, "bold")).pack(side="left")
        ctk.CTkButton(top, text="Refresh + save TXT", command=self.refresh, width=150).pack(side="right", padx=4)
        ctk.CTkButton(top, text="Open log folder", command=self.open_log_folder, width=130).pack(side="right", padx=4)

        controls = ctk.CTkFrame(self)
        controls.pack(fill="x", padx=10, pady=6)
        ctk.CTkLabel(controls, text="Limit", font=("Arial", 13, "bold")).pack(side="left", padx=(10, 4), pady=8)
        ctk.CTkOptionMenu(
            controls,
            variable=self.limit_var,
            values=["100", "250", "500", "1000"],
            width=90,
            command=lambda _value: None,
        ).pack(side="left", padx=4)
        ctk.CTkLabel(controls, text="Search", font=("Arial", 13, "bold")).pack(side="left", padx=(18, 4))
        search = ctk.CTkEntry(
            controls,
            textvariable=self.search_var,
            placeholder_text="Action, email, Cash App tag, referral code, product, admin...",
        )
        search.pack(side="left", fill="x", expand=True, padx=4, pady=8)
        search.bind("<KeyRelease>", lambda _event: self.render_events())

        self.status_label = ctk.CTkLabel(
            self,
            text="Audit events are saved as dated TXT files under your user profile. The UI shows summaries only so it stays fast.",
            text_color="#9ca3af",
            anchor="w",
            wraplength=1150,
        )
        self.status_label.pack(fill="x", padx=16, pady=(0, 6))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.date_frame = ctk.CTkScrollableFrame(body, width=230)
        self.date_frame.pack(side="left", fill="y", padx=(0, 8))

        right = ctk.CTkFrame(body)
        right.pack(side="left", fill="both", expand=True)

        action_bar = ctk.CTkFrame(right)
        action_bar.pack(fill="x", padx=8, pady=8)
        ctk.CTkLabel(action_bar, text="Event submenu", font=("Arial", 13, "bold")).pack(side="left", padx=(8, 6))
        self.action_menu = ctk.CTkOptionMenu(
            action_bar,
            variable=self.action_var,
            values=["All events"],
            command=lambda _value: self.render_events(),
            width=260,
        )
        self.action_menu.pack(side="left", padx=4)
        ctk.CTkButton(action_bar, text="Open date folder", command=self.open_selected_date_folder, width=130).pack(side="right", padx=4)

        self.event_frame = ctk.CTkScrollableFrame(right)
        self.event_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        self.refresh()

    def refresh(self) -> None:
        try:
            limit = int(self.limit_var.get() or "250")
        except ValueError:
            limit = 250
        try:
            data = self.client.get_audit_log(limit=limit)
        except ApiError as exc:
            show_error(self, exc)
            return

        raw_items = data.get("items") or data.get("events") or data.get("audit") or []
        self.items = [item for item in raw_items if isinstance(item, dict)]
        self.files_by_id = self._save_audit_files(self.items)
        self._render_dates()
        self._select_default_date()
        self._render_action_menu()
        self.render_events()
        self.status_label.configure(
            text=f"Loaded {len(self.items)} audit event(s). Saved TXT logs under: {AUDIT_EXPORT_ROOT}"
        )

    def _save_audit_files(self, items: Iterable[Dict[str, Any]]) -> Dict[str, Path]:
        files: Dict[str, Path] = {}
        AUDIT_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
        for item in items:
            date = _date_key(item)
            action = _item_action(item)
            item_id = _item_id(item)
            dt = _parse_dt(item.get("created_at") or item.get("createdAt") or item.get("timestamp"))
            time_slug = dt.strftime("%H%M%S") if dt else "unknown-time"
            folder = AUDIT_EXPORT_ROOT / date / _slug(action, "unknown-action")
            folder.mkdir(parents=True, exist_ok=True)
            path = folder / f"{time_slug}_{_slug(item_id, 'no-id')}.txt"
            try:
                path.write_text(_pretty_item(item), encoding="utf-8")
                files[item_id] = path
            except OSError:
                # If a file cannot be written, keep the UI usable and continue.
                continue
        return files

    def _dates(self) -> List[str]:
        dates = sorted({_date_key(item) for item in self.items}, reverse=True)
        return dates

    def _items_for_date(self, date: str) -> List[Dict[str, Any]]:
        return [item for item in self.items if _date_key(item) == date]

    def _render_dates(self) -> None:
        clear_frame(self.date_frame)
        ctk.CTkLabel(self.date_frame, text="Dates", font=("Arial", 16, "bold")).pack(anchor="w", padx=8, pady=(8, 4))
        dates = self._dates()
        if not dates:
            ctk.CTkLabel(self.date_frame, text="No audit events loaded.", text_color="#9ca3af").pack(anchor="w", padx=8, pady=8)
            return
        for date in dates:
            count = len(self._items_for_date(date))
            button = ctk.CTkButton(
                self.date_frame,
                text=f"{date}  ({count})",
                anchor="w",
                command=lambda value=date: self.select_date(value),
            )
            button.pack(fill="x", padx=6, pady=3)

    def _select_default_date(self) -> None:
        dates = self._dates()
        if dates and (not self.date_var.get() or self.date_var.get() not in dates):
            self.date_var.set(dates[0])

    def select_date(self, date: str) -> None:
        self.date_var.set(date)
        self.action_var.set("All events")
        self._render_action_menu()
        self.render_events()

    def _actions_for_selected_date(self) -> List[str]:
        selected = self.date_var.get()
        actions = sorted({_item_action(item) for item in self._items_for_date(selected)})
        return ["All events"] + actions

    def _render_action_menu(self) -> None:
        actions = self._actions_for_selected_date()
        current = self.action_var.get()
        if current not in actions:
            self.action_var.set("All events")
        if self.action_menu is not None:
            self.action_menu.configure(values=actions if actions else ["All events"])

    def _filtered_items(self) -> List[Dict[str, Any]]:
        selected_date = self.date_var.get()
        selected_action = self.action_var.get()
        query = self.search_var.get().strip().lower()
        items = self._items_for_date(selected_date)
        if selected_action and selected_action != "All events":
            items = [item for item in items if _item_action(item) == selected_action]
        if query:
            filtered = []
            for item in items:
                haystack = (_item_summary(item) + " " + json.dumps(item, default=str)).lower()
                if query in haystack:
                    filtered.append(item)
            items = filtered
        return items

    def render_events(self) -> None:
        clear_frame(self.event_frame)
        items = self._filtered_items()
        selected_date = self.date_var.get() or "no date selected"
        selected_action = self.action_var.get() or "All events"
        title = f"{selected_date} / {selected_action} — {len(items)} event(s)"
        ctk.CTkLabel(self.event_frame, text=title, font=("Arial", 16, "bold")).pack(anchor="w", padx=8, pady=(8, 6))
        if not items:
            ctk.CTkLabel(self.event_frame, text="No events match this date/action/search.", text_color="#9ca3af").pack(anchor="w", padx=8, pady=16)
            return
        for item in items:
            self._event_card(item)

    def _event_card(self, item: Dict[str, Any]) -> None:
        card = ctk.CTkFrame(self.event_frame)
        card.pack(fill="x", padx=6, pady=5)
        action = _item_action(item)
        item_id = _item_id(item)
        path = self.files_by_id.get(item_id)
        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=10, pady=(8, 2))
        ctk.CTkLabel(top, text=f"{_time_label(item)}  ·  {action}", font=("Arial", 14, "bold"), anchor="w").pack(side="left", fill="x", expand=True)
        ctk.CTkButton(top, text="Open TXT", width=90, command=lambda p=path: self.open_file(p)).pack(side="right", padx=3)
        ctk.CTkButton(top, text="Copy ID", width=75, command=lambda value=item_id: self.copy_text(value, "Audit ID")).pack(side="right", padx=3)
        ctk.CTkLabel(card, text=_item_summary(item), anchor="w", justify="left", wraplength=1020).pack(fill="x", padx=12, pady=(2, 8))

    def copy_text(self, value: str, label: str) -> None:
        if not value:
            show_error(self, f"{label} is missing.")
            return
        self.clipboard_clear()
        self.clipboard_append(str(value))
        self.update()
        show_info(self, "Copied", f"Copied {label}.")

    def open_file(self, path: Optional[Path]) -> None:
        if not path or not path.exists():
            show_error(self, "This audit TXT file was not found. Refresh the Audit tab to regenerate it.")
            return
        try:
            os.startfile(str(path))  # type: ignore[attr-defined]
        except AttributeError:
            show_error(self, f"Open this file manually:\n{path}")
        except OSError as exc:
            show_error(self, f"Could not open audit TXT file: {exc}")

    def open_log_folder(self) -> None:
        AUDIT_EXPORT_ROOT.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(AUDIT_EXPORT_ROOT))  # type: ignore[attr-defined]
        except AttributeError:
            show_info(self, "Audit folder", str(AUDIT_EXPORT_ROOT))
        except OSError as exc:
            show_error(self, f"Could not open audit folder: {exc}")

    def open_selected_date_folder(self) -> None:
        date = self.date_var.get()
        if not date:
            self.open_log_folder()
            return
        folder = AUDIT_EXPORT_ROOT / date
        folder.mkdir(parents=True, exist_ok=True)
        try:
            os.startfile(str(folder))  # type: ignore[attr-defined]
        except AttributeError:
            show_info(self, "Audit date folder", str(folder))
        except OSError as exc:
            show_error(self, f"Could not open audit date folder: {exc}")
