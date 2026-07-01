import json
from pathlib import Path
from typing import Any, Dict, Optional

import requests

from config import DEFAULT_API_BASE, REQUEST_TIMEOUT_SECONDS, SESSION_FILE


class ApiError(Exception):
    pass


class AdminApiClient:
    def __init__(self, api_base: str = DEFAULT_API_BASE):
        self.api_base = api_base.rstrip("/")
        self.token: Optional[str] = None
        self.session_path = Path.home() / SESSION_FILE
        self.load_session()

    def set_api_base(self, api_base: str) -> None:
        self.api_base = api_base.rstrip("/")
        self.save_session()

    def load_session(self) -> None:
        if not self.session_path.exists():
            return
        try:
            data = json.loads(self.session_path.read_text(encoding="utf-8"))
            self.api_base = data.get("api_base", self.api_base).rstrip("/")
            self.token = data.get("token") or None
        except Exception:
            self.token = None

    def save_session(self) -> None:
        data = {"api_base": self.api_base, "token": self.token}
        self.session_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def clear_session(self) -> None:
        self.token = None
        if self.session_path.exists():
            self.session_path.unlink()

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        url = f"{self.api_base}{path}"
        try:
            res = requests.request(
                method,
                url,
                headers=self._headers(),
                timeout=REQUEST_TIMEOUT_SECONDS,
                **kwargs,
            )
        except requests.RequestException as exc:
            raise ApiError(f"Network error: {exc}") from exc

        try:
            data = res.json() if res.text else {}
        except ValueError:
            data = {"raw": res.text}

        if not res.ok:
            message = data.get("message") or data.get("error") or f"HTTP {res.status_code}"
            code = data.get("error") or data.get("code")
            if code and code not in str(message):
                message = f"{message} ({code})"
            raise ApiError(message)
        return data

    def login(self, email: str, password: str) -> Any:
        """Request an MFA challenge using the password entered in the login window."""
        return self._request(
            "POST",
            "/v1/admin/auth/login",
            json={"email": email, "password": password},
        )

    def verify_mfa(self, challenge_id: str, code: str) -> Any:
        """Verify the emailed MFA code and store the returned admin token."""
        data = self._request(
            "POST",
            "/v1/admin/auth/verify",
            json={"challengeId": challenge_id, "code": code},
        )
        token = data.get("token") or data.get("adminToken")
        if not token:
            raise ApiError("MFA succeeded but no admin token was returned.")
        self.token = token
        self.save_session()
        return data

    def get_me(self) -> Any:
        return self._request("GET", "/v1/admin/me")

    def get_live_testing(self) -> Any:
        return self._request("GET", "/v1/admin/testing/live")

    def _live_confirmation(self) -> str:
        return "LIVE TEST zadockplant@gmail.com"

    def apply_live_testing(self, payload: Dict[str, Any]) -> Any:
        data = dict(payload)
        data["confirm"] = self._live_confirmation()
        return self._request("PUT", "/v1/admin/testing/live/state", json=data)

    def step_live_testing(self, action: str, quantity: int = 1) -> Any:
        return self._request(
            "POST",
            "/v1/admin/testing/live/step",
            json={"confirm": self._live_confirmation(), "action": action, "quantity": quantity},
        )

    def update_live_test_reward(self, reward_id: str, status: str, note: str = "") -> Any:
        return self._request(
            "POST",
            f"/v1/admin/testing/live/rewards/{reward_id}/status",
            json={"confirm": self._live_confirmation(), "status": status, "note": note},
        )

    def reset_live_testing(self, restore_cashapp_tag: bool = True) -> Any:
        return self._request(
            "POST",
            "/v1/admin/testing/live/reset",
            json={
                "confirm": self._live_confirmation(),
                "restoreCashAppTag": bool(restore_cashapp_tag),
            },
        )

    def set_owner_entitlement(self, product_slug: str, enabled: bool = True) -> Any:
        return self._request(
            "POST",
            "/v1/admin/testing/live/entitlements",
            json={
                "confirm": self._live_confirmation(),
                "productSlug": product_slug,
                "enabled": bool(enabled),
            },
        )

    def get_products(self) -> Any:
        return self._request("GET", "/v1/admin/products")

    def create_product(self, payload: Dict[str, Any]) -> Any:
        return self._request("POST", "/v1/admin/products", json=payload)

    def update_product(self, product_id: str, payload: Dict[str, Any]) -> Any:
        return self._request("PUT", f"/v1/admin/products/{product_id}", json=payload)

    def search_user(self, email: str) -> Any:
        return self._request("GET", "/v1/admin/users/search", params={"email": email})

    def grant_entitlement(self, email: str, product_slug: str, source: str = "admin") -> Any:
        return self._request(
            "POST",
            "/v1/admin/entitlements/grant",
            json={"email": email, "productSlug": product_slug, "source": source},
        )

    def revoke_entitlement(self, email: str, product_slug: str) -> Any:
        return self._request(
            "POST",
            "/v1/admin/entitlements/revoke",
            json={"email": email, "productSlug": product_slug},
        )

    def get_referrals(self) -> Any:
        return self._request("GET", "/v1/admin/referrals")

    def create_referral_code(self, payload: Dict[str, Any]) -> Any:
        return self._request("POST", "/v1/admin/referrals/codes", json=payload)

    def get_rewards(self) -> Any:
        return self._request("GET", "/v1/admin/rewards")

    def update_reward(
        self,
        reward_id: str,
        status: str,
        note: str = "",
        cashapp_handle: str = "",
        payout_reference: str = "",
    ) -> Any:
        payload: Dict[str, Any] = {"status": status}
        if note.strip():
            payload["adminNote"] = note.strip()
        if cashapp_handle.strip():
            payload["cashappHandle"] = cashapp_handle.strip()
        if payout_reference.strip():
            payload["payoutReference"] = payout_reference.strip()
        return self._request("PUT", f"/v1/admin/rewards/{reward_id}", json=payload)

    def upsert_referral_program(self, payload: Dict[str, Any]) -> Any:
        return self._request("POST", "/v1/admin/referrals/programs", json=payload)

    def get_audit_log(self, limit: int = 100) -> Any:
        return self._request("GET", "/v1/admin/audit-log", params={"limit": limit})
