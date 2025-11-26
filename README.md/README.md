#### HABIT TRACKER 
#### VIDEO DEMO: <URL HERE>
#### DESCRIPTION:

## OVERVIEW
This project is a habit-tracking web application built with Flask and SQLAlchemy. It lets a user create habits, group them into categories, log completions (including a *complete all today* action that avoids duplicates), and see progress through visualizations (weekly totals, streaks, a pie chart of completed vs incomplete items, and a 60-day heatmap). The front end uses Bootstrap for layout and Chart.js for charts, and the backend stores data in an SQLite database managed through Alembic migrations.

## APP STRUCTURE
### 1. __init__.py
The file **smart_habit_tracker/web/__init__.py** implements the Flask *app factory* pattern. The create_app() functions builds and returns a configured Flask instance, kinds core extensions (SQLAlchemy for database access, Migrate for migrations, LoginManager for sessions, and CSRFProtect for form security), registers the main and auth blueprints, exposes csrf_token() to templates, and sets configuration such as the absolute path to the SQLite database inside the package’s instance folder. It also defines the Flask-Login user loader, so the framework fetches a user by ID during a session.

### 2. models.py
The file **smart_habit_tracker/web/models.py** defines the database schema and relationships. There are four models. User stores identity and preferences and relates to Habit, HabitLog, and HabitCategory with cascade deletes so removing a user or habit cleans up dependent rows. HabitCategory is owned by a user and enforces unique names per user with a (user_id, name) constraint. Habit belongs to a user, may belong to a category, and has many HabitLog entries. HabitLog represents one completion record with a UTC timestamp, a boolean completed flag, and foreign keys to the habit and user. These relationships enable simple queries such as “all logs for this user today” and let the app compute streaks and daily counts efficiently.

### 3. routes.py
The file **smart_habit_tracker/web/routes.py** is the main blueprint and contains the core application logic. It renders the dashboard with summaries and charts, groups habits by category for the “log habit” dropdown, and provides POST routes to create habits, log completions, complete all habits for the current day without duplication, create and delete categories (while preventing deletion of categories still in use), rename or delete habits, remove individual log entries, and delete a user account. Routes consistently filter queries by current_user.id to ensure data isolation. The module also does the date math for streaks, uses SQL functions (for example DATE(timestamp)) to compute daily buckets, and prepares JSON-serializable data structures that the dashboard template turns into charts.

### 4. auth.py
The file **smart_habit_tracker/web/auth.py** contains the authentication blueprint. It provides registration, login, and logout, hashes passwords with Werkzeug, and integrates with Flask-Login to protect routes via @login_required.

### 5. TEMPLATES and Static Files
The template **smart_habit_tracker/web/templates/dashboard.html** is the main UI. It uses Bootstrap classes to render forms and layout, includes hidden CSRF tokens in all forms, and displays flash messages for user feedback. It shows a weekly summary and a streak bar, renders the trend, weekly bar, and completed vs. incomplete pie charts with Chart.js, renders a per-category pie chart by mapping server-provided category IDs to counts; shows a 60-day heatmap; and provides forms to add categories, add habits, and log completions, as well as buttons to complete all for today, delete specific logs, delete categories, and delete the account. 

### 6. DATABASE and MIGRATIONS
The **smart_habit_tracker/migrations/** directory contains Alembic migration scripts that track schema changes over time. These scripts are applied through Flask-Migrate commands and are separate from the runtime database file. The smart_habit_tracker/instance/habits.db file is the actual SQLite database created and written by the app; it’s environment-specific and typically excluded from version control. The stylesheet at smart_habit_tracker/web/static/style.css holds small visual tweaks to complement Bootstrap.

## FEATURES AND WORKFLOW ##
In normal usage a new user registers or logs in, creates one or more categories, adds habits (optionally assigning each to a category), and logs completions either one by one from the dropdown or with the *complete all today* action. The dashboard updates immediately, and the charts, streak counter, and heatmap reflect progress.

## LIMITATIONS / FUTURE IMRPOVEMENTS ##
There are a few deliberate limitations and future directions. The original *nudge* idea is preserved only as a simple logging endpoint. The app currently targets SQLite; swapping to Postgres or MySQL would be straightforward for production deployments. Lists are not paginated yet, automated tests are light, and there is room to add reminders or scheduling, richer analytics, and more robust error handling. The log-nudge-event was a feature which I intially wanted to include. The app was meant to send users “nudges” and flash messages when they pivoted to a website that might be a distraction/ There was also a statistic that would keep track of how often users would “ignore” or “close” the nudges or messages. This features proved to be too difficult to implement and they were scrapped, however, you can still see some references to it in the code. There is also a feature that measures of how often users do not complete their tasks per day, but that too has been hard to implement. I’ve keptthese references and seign choices in the hope of including them to give users more insight into their stats.