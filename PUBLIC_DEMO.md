# Public visitor demo — prepared, not deployed

The local named-account demo remains available through `demo.py`. The separate public entry point, `public_demo_app.py`, offers a landing page and a “Try the demo” button. No public deployment or repository visibility change is part of this change.

## Visitor experience

- Each browser receives a unique account with a random, undisclosed password and fictional sample records. No registration or personal email is needed.
- The existing app operates on that account's records; there is no shared demo password.
- Reloading retains edits in the same browser. Separate browsers/incognito sessions receive separate data; tabs in the same browser share a demo.
- The demo expires two hours after entry or reset. A reset replaces only the current visitor's records and restores relative-date sample history. End demo deletes that visitor's data immediately.
- Reset has a ten-second cooldown. The initial capacity is 500 visitor accounts, including expired accounts until cleanup runs.
- Ordinary authentication and account-settings routes are blocked in public mode. Private dynamic responses are marked `no-store`; demo responses request search-engine exclusion.

## Configuration and local preview

Use a **dedicated empty demo database**, separate from real users and the local named-account demo. The public entry point requires `DEMO_DATABASE_URL` and a `SECRET_KEY` of at least 32 characters. Hosting and database selection are deferred. SQLAlchemy models are used for the visitor metadata so the feature is not tied to a hosting provider.

Example local preview on macOS/Linux, from this repository:

```sh
python3 demo.py setup
export SECRET_KEY="$(.venv/bin/python -c 'import secrets; print(secrets.token_hex(32))')"
export DEMO_DATABASE_URL="sqlite:///$(pwd)/demo-data/visitor-preview.sqlite3"
export DEMO_LOCAL_HTTP=1
.venv/bin/flask --app public_demo_app demo-init
.venv/bin/waitress-serve --listen=127.0.0.1:5060 public_demo_app:app
```

Open `http://127.0.0.1:5060/demo`. Use a different port when previewing both apps simultaneously. Initialize only once: `demo-init` refuses any nonempty database rather than overwriting it. It initializes the current models for a fresh sandbox; it does not validate or replace migration history for existing databases.

`DEMO_LOCAL_HTTP=1` is only for localhost preview. Omit it on the eventual HTTPS host, where cookies default to Secure, HttpOnly, and SameSite=Lax. Use a distinct secret for each app and retain it across restarts. The public app never uses the fixed local demo passwords or the inherited `DATABASE_URL` setting.

## Cleanup and storage

Run this command with the same environment as the public service:

```sh
.venv/bin/flask --app public_demo_app demo-cleanup
```

It removes expired visitor accounts and their dependent records, leaving ordinary accounts untouched. Entry opportunistically cleans up at most 20 expired visitors; the chosen host should run full cleanup on a recurring schedule. Access expires after two hours even if cleanup has not run yet; physical deletion occurs on cleanup. Clearing a browser cookie abandons its sandbox until expiry/cleanup.

The table `demo_visitors` records a random identifier, owner ID, creation time, and expiry time. The signed Flask session contains the visitor identifier. Every protected request checks both expiry and authenticated ownership. Reset/end routes use POST and CSRF validation.

## Verification

```sh
.venv/bin/python verify_demo.py
.venv/bin/python verify_public_demo.py
```

Both scripts use temporary databases. Public tests cover anonymous entry, CSRF, separate visitors, repeated entry, cookie persistence across app instances, ownership enforcement, isolated reset, expiry, cleanup preserving ordinary accounts, capacity, End demo, and blocked normal account routes. Local tests retain the existing named-account workflows.

## Before deployment

Select the host, persistent database, backup policy, HTTPS/domain configuration, and cleanup scheduler. Test this configuration on that actual host. The capacity check is a basic guard, not a distributed rate limiter: add host-level request limits and monitor resource usage before opening access broadly. Concurrent start requests can exceed the capacity check, and a visitor can still create many records; choose deployment-level limits as part of hosting work. Review production dependency updates and migration strategy then.

No provider-specific deployment manifest or automatic deployment workflow is included.
