# SendForge Admin Desktop v0.5.3

Secure desktop control panel for the SendForge backend admin API.

## Install

```powershell
cd "TheForge Admin"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

## Security model

The app does not connect to Postgres, Cash App, Stripe, or Render secrets directly.

```text
Desktop app -> Render backend admin API -> Postgres / payout provider
```

Admin login requires the backend account password plus the MFA code sent by the backend.

## Modules

- Login + MFA
- Products
- Entitlements
- Referrals
- Referral payout control
- Cash App API onboarding/setup links
- Owner Tools for `zadockplant@gmail.com` only
- Audit log

## v0.5.3 billing + cloud staging update

- Products tab now shows the current TabForge billing profile: `$10` one-time Pro and `$5/month` Sync + Collections.
- Entitlements tab defaults to `zadockplant@gmail.com` and documents the current slug profile.
- Owner Tools now shows cloud status: admin-only cloud save account, 20GB cloud-storage profile, notes autosave record, shortcut autosave record, and provider status.
- Owner Tools quick referral steps now send the backend action names expected by `/v1/admin/testing/live/step`.
- Mojibake text in Owner Tools was repaired.
- Collections are labeled as subscription-included only.
- Skins/icon packs are labeled as delayed future one-time add-ons.
- Cloud saves are live only for `zadockplant@gmail.com` until the cloud provider is wired in; non-owner cloud hosting is intentionally stubbed.

## LIVE Referral Test Lab

The Owner Tools tab talks to the deployed backend and changes only the owner test account configured in the backend, currently `zadockplant@gmail.com`. It is for validating the live account page, referral totals, tier thresholds, entitlement visibility, cloud status, and test payout status flow. The backend must enforce authorization; the desktop UI is not the security boundary.

Test data is tagged `admin_live_test` and can be reset without deleting real referral events or real rewards. Do not use the normal Rewards/Payouts tab to process test rewards.

## Expected backend env vars

```text
ADMIN_JWT_SECRET=...
ADMIN_MFA_EMAIL=zadockplant@gmail.com
ADMIN_WRITES_ENABLED=true
ADMIN_LIVE_TESTING_ENABLED=true
ADMIN_LIVE_TEST_OWNER_EMAIL=zadockplant@gmail.com
TABFORGE_CLOUD_OWNER_EMAIL=zadockplant@gmail.com
TABFORGE_CLOUD_PROVIDER_STATUS=stubbed_until_provider
```

Future official Cash App integration will use Render-side variables. Never commit secrets or place them in the desktop application.

## Residual files observed in uploaded admin archive

The uploaded archive contained build/runtime leftovers. Do not preserve, stage, or commit these unless explicitly asked:

```text
.venv/
__pycache__/
dist/SendForge Admin.exe
SendForge Admin.spec
_patch_bundles/
```

These are treated as local artifacts. The source app runs through `run_source.bat`; rebuild artifacts should be recreated locally, not committed.

## Migration rule

Do not run `npm run migrate` locally for the SendForge backend. Commit and push backend migration files; Render applies them during deployment.
