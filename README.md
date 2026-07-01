# SendForge Admin Desktop v0.4.6

Secure desktop control panel for the SendForge backend admin API.

## Install

```powershell
cd sendforge-admin
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python app.py
```

## Security model

The app does not connect to Postgres, Cash App, or Render secrets directly.

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
- LIVE referral test lab for zadockplant@gmail.com only
- Audit log


## LIVE Referral Test Lab

The Owner Tools tab talks to the deployed backend and changes only the owner test account configured in the backend, currently `zadockplant@gmail.com`. It is for validating the live account page, referral totals, tier thresholds, and test payout status flow. The backend must enforce authorization; the desktop UI is not the security boundary.

Test data is tagged `admin_live_test` and can be reset without deleting real referral events or real rewards. Do not use the normal Rewards tab to process test rewards.

## Payout workflow

```text
Qualified TabForge Pro purchase
-> reward pending
-> admin approves
-> admin sends Cash App payment
-> admin enters Cash App activity/reference
-> reward marked paid and audited
```

The payout screen includes status filters, search, queue totals, batch approval, CSV export, copy buttons, Cash App launch, required payout reference, rejection notes, and confirmation before marking a reward paid.

Paid rewards remain locked by the backend.

## Official Cash App Payout API

The Cash App Payout API is an early-access, server-side partner API. The desktop app includes official onboarding, authentication, and payout documentation links, but it does not store API secrets or send automated payouts itself.

After Cash App approves SendForge, credentials must be stored only in the Render backend environment. Keep `CASHAPP_PAYOUTS_ENABLED=false` until the backend payout-provider integration, webhook verification, idempotency, limits, and sandbox testing are complete.

## Expected backend env vars

```text
ADMIN_JWT_SECRET=...
ADMIN_MFA_EMAIL=zadockplant@gmail.com
ADMIN_WRITES_ENABLED=true
```

Future official Cash App integration will use Render-side variables such as:

```text
CASHAPP_PAYOUTS_ENABLED=false
CASHAPP_API_ENV=sandbox
CASHAPP_CLIENT_ID=...
CASHAPP_CLIENT_SECRET=...
CASHAPP_API_KEY_ID=...
CASHAPP_API_KEY_SECRET=...
CASHAPP_REGION=PDX
CASHAPP_MERCHANT_ID=...
CASHAPP_WEBHOOK_SECRET=...
```

Never commit these secrets or place them in the desktop application.

## v0.4.6 owner tools / payout hold update

- Owner Tools entitlement grant now uses a dropdown of known TabForge products, packs, and skin entitlements, with a custom `tabforge-*` slug override for new packs.
- Entitlement controls still write real owned/admin grants only for `zadockplant@gmail.com`; backend device/license limits remain enforced normally.
- Referrals tab now catalogs referral activity by referrer email and Cash App tag so payout verification is easier.
- Payout rules default to TabForge tiers: 5 qualified Pro purchases = $10, 15 = $20, 50 = $75.
- Payout verification hold is now visible in the admin UI; real payouts should sit in a 7-10 day review window after qualifying Pro purchase before approval/payment.

## Residual files observed in uploaded admin archive

The uploaded `admin.7z` contained build/runtime leftovers. Codex should not preserve, stage, or commit these unless explicitly asked:

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

## Running live tests

The repository includes opt-in live tests for referral-related admin endpoints. They are skipped by default.

To run them locally:

```powershell
$env:RUN_LIVE_TESTS = '1'
$env:SENDFORGE_ADMIN_TEST_API_TOKEN = '<your-admin-token-here>'
pip install -r requirements.txt
python -m pytest tests/test_live_referral.py -q
```

Provide a valid admin token in `SENDFORGE_ADMIN_TEST_API_TOKEN`. Live tests may modify backend state; run them against a test backend or with caution.


## v0.4.4 owner entitlement rule

Owner Tools can grant or revoke real admin-owned entitlements only for `zadockplant@gmail.com`. These are not test-only entitlement rows. Referral flow simulations remain tagged test data. Existing Stripe/manual entitlements are protected, and normal backend device/license limits still apply.


## v0.4.6 Owner Tools UX cleanup

- Owner Tools now separates purchasable entitlement controls into Product features, Shortcut packs, and Skin packs.
- Extra Pages is labeled as a product feature, not a shortcut pack.
- Skin access now shows only the three purchasable skin options instead of every individual internal skin variant.
- Entitlement actions use explicit Enable / Disable buttons and show a confirmation/status message after backend write completion.
- The live account state panel mirrors what the owner account should own in TabForge after refresh.
- Referral test payout cards now show the current status prominently and only offer valid next actions, so Rejected, Approved, Pending, and Paid states are harder to confuse.
- Referral and payout tabs clarify referral code, referrer email, Cash App tag, qualified Pro purchase count, and 7-10 day payout verification hold behavior.
