# Employer demo packages

Both apps are prepared locally. The demo improvements are prepared for GitHub review. No public deployment, domain purchase, or DNS change is included.

## Open the demos

On this Mac, each app's environment and sample database are already installed. Double-click `Start Demo.command` inside the app folder, or run `python3 demo.py run --open` from that folder. Leave the terminal running. The apps can run simultaneously.

| App | Local address | Sample data |
| --- | --- | --- |
| Smart Habit Tracker | http://127.0.0.1:5051/login | 2 users, 8 habits, 8 categories, 336 logs over 6 weeks |
| SessionIQ | http://127.0.0.1:5052/login | 2 users, 6 activities, 80 sessions over 8 weeks |

Both apps accept `alex@example.com` or `jordan@example.com`, password `Demo-Explore-2026!`. These are fictional demo accounts. Login pages show the credentials in local demo mode.

After initial installation, the apps and their charts work offline. A browser is the interface; Python runs the app, and SQLite stores the records on the laptop. SQLite is free and public domain ([SQLite](https://www.sqlite.org/about.html)).

For another laptop, extract the ZIP, install Python 3.11–3.13, and run `python3 demo.py setup` in each app folder with internet access. Windows uses `py -3` in place of `python3`. Only macOS/Python 3.13 was tested here. The ZIP deliberately excludes machine-specific environments and all database files; setup generates fresh fictional data.

## Five-minute walkthrough

1. Open Smart Habit Tracker and log in as Alex. Explain the sample history, daily charts, and streaks.
2. Add a habit called “Interview preparation.” Log it as complete. Refresh the dashboard to show the saved record.
3. Stop the server with Ctrl+C and restart it. Log in again and find the habit. This demonstrates database persistence, beyond just browser state.
4. Log out and log in as Jordan. Alex's new habit should not appear. Explain how records belong to a user.
5. Open SessionIQ as Alex. Filter the dashboard by activity, then go to Sessions and record 37 minutes at effort 5 with a memorable note. Its calculated load is 185. Refresh, edit the session, and export CSV to show stored information can be retrieved.

Run `python3 demo.py inspect` inside either folder to display the database location and table counts. Data is in `demo-data/demo.sqlite3`, a separate database for each app. Back up that file with the app stopped if you want to preserve your demonstration changes.

Stop the app before `python3 demo.py reset`. Reset saves a timestamped database backup, recreates the fictional accounts/history, and moves the sample dates up to the reset date. Start it again with `python3 demo.py run --open`. Do this before an interview if the sample dates are stale. Local and hosted databases do not automatically sync.

## Domain and subdomains

A local demo is for you or someone sitting at your laptop. Its localhost address cannot be opened remotely by an employer. For application links, use a hosted version; your laptop then does not need to stay on.

A practical address structure is:

- `yourname.com`: portfolio, screenshots, descriptions, and source links.
- `habits.yourname.com`: hosted Smart Habit Tracker.
- `sessioniq.yourname.com`: hosted SessionIQ.

These are examples, not registered domains. The domain is the address; hosting runs the app; database storage keeps the records. DNS connects each subdomain to its hosting destination. The host supplies the exact DNS target and HTTPS setup instructions ([DNS/subdomain documentation](https://developers.cloudflare.com/dns/manage-dns-records/how-to/create-subdomain/)). One registered domain can contain both subdomains; separate domain registrations are unnecessary.

Your existing GitHub Pages repository could serve the portfolio. GitHub Pages serves static files and does not run these Flask backends or their databases ([GitHub Pages documentation](https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages)).

## Next deployment work

The visitor experience described below is now implemented in `public_demo_app.py`; see `PUBLIC_DEMO.md`.

Choose a host that runs Python with persistent storage, then connect the subdomains. No provider or budget has been selected. Open-source app software does not imply that a domain and hosting are free. A provider's default URL can be used before buying a domain.

For each app:

1. Configure a production WSGI server and HTTPS. Flask's development server is unsuitable for public deployment ([Flask deployment documentation](https://flask.palletsprojects.com/en/stable/deploying/)). The local launcher uses Waitress but intentionally binds only to localhost.
2. Store configuration and unique secrets outside source control. Configure HTTPS cookies and authentication protections for a public audience.
3. Use durable database storage and backups. SessionIQ already accepts `DATABASE_URL`; the habit tracker needs production database configuration. SQLite needs a persistent disk for a single-instance deployment; PostgreSQL is another option. An ephemeral deployment filesystem will lose SQLite data.
4. Test database migrations against an empty production database. The local demo initializes a fresh schema from the models and does not validate the migration history.
5. Add a public demo policy: clearly labeled fictional records, separate visitor accounts or isolated demo sessions, and an operator-controlled reset. Shared demo credentials alone do not isolate visitors from one another.
6. Deploy, validate login/create/edit/export and restart persistence on the host, then configure and verify subdomain DNS and HTTPS.

SessionIQ's original README points to a Railway demo but lists Render elsewhere. The live deployment was not verified or modified. Its public repository contains a database with 1 user, 3 activities, and 1 session. The demo package excludes that database. Check whether that original account represents real data before promoting the repository; no remote files/history were changed here.

## Changes and verification

Source snapshots: Smart Habit Tracker `0bf854b100ac1267d4223428ffee4f5eb655946e`; SessionIQ `270fb4c0adea21ea502a4c2ebc7faa341f6899f5`.

Added local launchers, isolated demo databases, deterministic relative-date seeds, backup/reset and inspection commands, demo credentials on login, local Chart.js assets (4.4.8), and Bootstrap assets (5.3.0) for the habit tracker. Vendor licenses are included. Requirements used in testing are recorded in each `requirements-tested.txt`.

Fixed habit tracker startup imports, migration directory, missing dependencies, missing login/register/settings CSRF fields, settings persistence, cross-user habit logging, and unique-day streak counting. Changed dashboard labels to match the stored quantities: habit completion rate and habits per category. Removed placeholder nudge statistics from the visible summary.

Fixed SessionIQ's navigation typo and restricted the post-login redirect to a local path. Its existing seven-day divided by 28-day total calculation is now labeled “7-day share of 28-day load”; the previous ACWR label and low/optimal/high interpretation were removed. Week-over-week comparisons still include the current partial week; this is an existing analytics limitation worth explaining during a demo.

Automated checks use temporary databases and cover seed idempotence, CSRF rejection, login, saved records after app recreation, user isolation, settings saving for the habit tracker, and CSV export for SessionIQ. Reset was exercised on both generated databases. These checks are for local demo readiness, not a comprehensive production or security audit.
