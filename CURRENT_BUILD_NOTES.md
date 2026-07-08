# TheForge Admin Current Source Build 0.5.3

This is the current SendForge/TheForge Admin source folder.

## Expected visible version

```text
SendForge Admin v0.5.3
```

Expected tabs:

```text
Products | Entitlements | Referrals | Payouts | Cash App API | Owner Tools | Audit
```

## Included current features

- Products billing-profile panel for new TabForge pricing.
- Entitlements helper text for `tabforge`, `tabforge-subscription`, `tabforge-sync-collections`, and legacy aliases.
- Owner Tools cloud status panel for admin-only cloud saving.
- Owner Tools catalog profile aligned to: `$10` one-time Pro; `$5/month` Sync + Collections; collections subscription-only; skins/icon packs delayed.
- Referral test step actions fixed to backend enum values.
- Mojibake cleanup in Owner Tools labels and logs.

## Cloud staging rule

Cloud saves are live only for `zadockplant@gmail.com` while the cloud provider is being wired in. Non-owner cloud hosting is intentionally stubbed, even when billing/subscription entitlement rows exist.

## Not included

- `.venv`
- `build`
- `dist`
- old EXE output

Those are intentionally excluded to avoid stale-path drift.
