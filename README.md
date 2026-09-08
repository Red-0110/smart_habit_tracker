# Smart Habit Tracker — local employer demo

A runnable copy of Red-0110/smart_habit_tracker, with fictional data and offline dashboard assets.

## Start

On this Mac, double-click `Start Demo.command`, or open Terminal in this folder and run:

```sh
python3 demo.py setup
python3 demo.py run --open
```

Setup needs Python 3.11–3.13 and internet access. Tested with Python 3.13 on macOS Apple Silicon. After setup, `run` and the dashboard work offline. Windows launcher: `Start Demo.bat` (not tested on Windows); Windows command equivalent: `py -3 demo.py setup`, then `py -3 demo.py run --open`.

Open http://127.0.0.1:5051/login . Keep the terminal running. Stop with Ctrl+C. If the port is occupied, use `python3 demo.py run --port 5061 --open`.

## Demo accounts

- `alex@example.com`
- `jordan@example.com`
- Password for both: `Demo-Explore-2026!`

Seeded data: 2 users, 8 categories, 8 habits, and 336 logs covering 42 days. Dates are relative to the seed/reset date. Records are synthetic. The accounts have separate records.

## Persistence and reset

Data is stored in `demo-data/demo.sqlite3`. It survives browser refreshes, logout, app restarts, and laptop restarts. Local data does not automatically synchronize to a hosted deployment. The launcher overrides database environment settings so it cannot use your hosted database.

```sh
python3 demo.py inspect
```

This prints the database path and table counts. To restore the fictional records, stop the app and run:

```sh
python3 demo.py reset
python3 demo.py run --open
```

Reset backs up the previous demo database inside `demo-data/` before replacing it. To restore a backup, stop the app, preserve the current file, and copy the chosen backup to `demo-data/demo.sqlite3`. `setup` and `seed` preserve existing records.

## Verify

```sh
.venv/bin/python verify_demo.py
```

Uses a temporary database to test login, CSRF, creation, persistence across app instances, user isolation, and local chart assets. The verification leaves demo records intact. See `DEMO_GUIDE.md` for the interview walkthrough and hosting plan.

## Packaging

`requirements-demo.txt` installs the app plus Waitress. `requirements-tested.txt` records the complete versions used in verification. The ZIP excludes virtual environments, databases, secrets, backups, and Python caches; setup recreates fictional data on the recipient's machine. Do not copy the `.venv` to another machine; recreate it with setup.

This is a local demo, bound only to `127.0.0.1`. Public hosting needs separate deployment configuration and review. See `ORIGINAL_README.md` for the original project description; old setup/deployment claims there are historical.

## Visitor demo experience (prepared, not deployed)

`public_demo_app.py` is a separate, opt-in entry point. Visitors enter at `/demo` without registering; each browser receives its own fictional account and history. Edits persist across refreshes until the two-hour expiry. Reset replaces only that visitor's data, and End demo deletes it. Account registration, normal login, settings, and account deletion routes are unavailable in this mode.

See [PUBLIC_DEMO.md](PUBLIC_DEMO.md) for configuration, local preview, lifecycle, testing, and remaining hosting work. Hosting, database provider, DNS, and deployment are intentionally undecided.
