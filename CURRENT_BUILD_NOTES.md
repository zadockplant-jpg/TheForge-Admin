# TheForge Admin Current Source Build 0.4.6

This is a clean full source re-output of the current SendForge/TheForge Admin panel.

Use this folder as the single working admin folder. Do not mix it with older Desktop/OneDrive copies.

## Run source

Double-click:

```bat
run_source.bat
```

or run:

```bat
cd /d "C:\TheForge Admin"
run_source.bat
```

## Build EXE

Double-click:

```bat
build_exe.bat
```

The builder recreates `.venv` every time because copied/moved virtual environments store stale absolute paths.

## Expected visible version

The app header should show:

```text
SendForge Admin v0.4.6
```

Expected tabs:

```text
Products | Entitlements | Referrals | Payouts | Cash App API | Owner Tools | Audit
```

## Included current features

- Payout control workflow
- Cash App API setup/documentation tab
- Owner Tools tab for owner-only backend test controls
- Version display fixed to 0.4.6
- EXE builder parser fixes through v0.3.3

## Not included

- `.venv`
- `build`
- `dist`
- old EXE output

Those are intentionally excluded to avoid stale-path drift.


## v0.4.6 owner entitlement rule

Owner Tools can grant or revoke real admin-owned entitlements only for `zadockplant@gmail.com`. These are not test-only entitlement rows. Referral flow simulations remain tagged test data. Existing Stripe/manual entitlements are protected, and normal backend device/license limits still apply.


## v0.4.6 changes

- Owner Tools entitlement grant uses a dropdown list of TabForge products, packs, and skins plus a custom slug override.
- Referrals tab shows a verification catalog grouped by referrer email and Cash App tag.
- Payout UI displays 7-10 day verification hold status and disables approval/payment until hold completion.
- Residual local artifacts observed in the uploaded archive (`.venv/`, `__pycache__/`, `dist/`, `SendForge Admin.spec`, `_patch_bundles/`) are leftovers and should not be committed.


## v0.4.6 Owner Tools UX cleanup

- Owner Tools now separates purchasable entitlement controls into Product features, Shortcut packs, and Skin packs.
- Extra Pages is labeled as a product feature, not a shortcut pack.
- Skin access now shows only the three purchasable skin options instead of every individual internal skin variant.
- Entitlement actions use explicit Enable / Disable buttons and show a confirmation/status message after backend write completion.
- The live account state panel mirrors what the owner account should own in TabForge after refresh.
- Referral test payout cards now show the current status prominently and only offer valid next actions, so Rejected, Approved, Pending, and Paid states are harder to confuse.
- Referral and payout tabs clarify referral code, referrer email, Cash App tag, qualified Pro purchase count, and 7-10 day payout verification hold behavior.
