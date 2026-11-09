# Development Journey

How LabelFlow was built, one phase at a time, with the problems I hit and how I solved them.

I built it as a set of independent modules. Each phase added one module with a small interface, and later phases import it. I tested every phase on its own before moving on, and committed after each one.

**Working rules I set on day one**
- One phase at a time, always ending with something that runs.
- Git from the first phase. Docker only at the end, once everything worked locally.
- Settings that differ between my laptop and a server live in `.env`, so deploying needs no code change.
- Simple code: one route shows a page, another route does the work (`/register` and `/perform_registration`).

---

## Phase 1: Project setup

**Built:** Flask app factory (`create_app`), `core/config.py` that reads `.env`, `.gitignore`, first commit to GitHub.

**Decision:** I first planned WSL and Docker from the start. I dropped both for now, because Python, Flask and MySQL all run natively on Windows. WSL only became necessary in Phase 10, when I needed Redis.

---

## Phase 2: Database models

**Built:** SQLAlchemy models for users, projects, tasks, assignments, annotations, AI predictions and review decisions.

**Design choices**
- Human labels (`annotations`) and AI labels (`ai_predictions`) are separate tables, so they can be compared later.
- `UNIQUE (task_id, user_id)` on assignments and annotations, so the database itself blocks duplicates even if my code has a bug.

**Problem:** `Access denied for user 'root'@'localhost'` (error 1045) when the app first started.
**Cause:** the password in `.env` was still the placeholder text.
**Fix:** put the real MySQL password in `.env`. I also learned that the traceback proved the code was fine and only the credentials were wrong.

---

## Phase 3: Login and roles

**Built:** register, login, logout, and a `role_required("admin", "reviewer")` decorator. An admin page to change roles.

**Decisions**
- Flask-Login instead of hand-written session code, because role checks then become one line per route.
- The first account created becomes the admin.
- Passwords are stored as hashes (Werkzeug), never as text.

**Problem:** I forgot a password and tried to find it in MySQL.
**Cause:** a hash cannot be turned back into the password, which is the point of hashing.
**Fix:** a small one-off script that sets a new hash for a user.

---

## Phase 4: Projects

**Built:** create a project with a name, guidelines, label options and 2 or 3 annotators per item, plus a project list.

**Problem:** `ValueError: The name 'projects' is already registered for this blueprint`.
**Cause:** the `projects_bp` registration was added twice in `app.py`, once in an earlier step and once in a later rewrite.
**Fix:** keep each `register_blueprint` call exactly once.

---

## Phase 5: CSV ingestion

**Built:** `projects/csv_parser.py`, a standalone function that validates a CSV and returns tasks or an error. Each row becomes a task, and extra columns are saved as JSON metadata.

**Details:** it reads files as `utf-8-sig`, so the hidden marker Excel adds does not break the first column name.

**Also in this phase:** I made the app deployment-ready early. `DATABASE_URL` support, a proxy fix, `gunicorn`, a `/health` route, and connection settings that survive cloud MySQL closing idle connections.

**Lesson:** refreshing the page after an upload re-sends the file. I noted it as a known weakness.

---

## Phase 6: Safe task claiming

**Built:** `tasks/assignment.py`, with `claim_next_task(user_id, project_id)`.

**How it works**
1. If the user already has an unfinished task, return it, so refresh never takes a second task.
2. Otherwise find a task the user has not seen that still has a free slot.
3. Lock that task row with `SELECT ... FOR UPDATE`, count the slots again, and then write the claim.

**Testing:** with two accounts I confirmed both got task 1 (2 annotators per item), and a third got task 2.
**Lesson:** reviewers cannot label, so I needed a third annotator account to test properly.

---

## Phase 7: Labeling screen

**Built:** one item at a time, label buttons, keyboard shortcuts (`1`, `2`, ...), and a timer that saves how long each label took.

---

## Phase 8: Consensus and review queue

**Built:** `tasks/review.py` with `check_task()`. After every label it checks the task: if everyone agrees the label is final, otherwise the task goes to the reviewer, whose decision is final.

**Problem:** my first 10 labels were saved before `check_task` existed, so those tasks never got checked.
**Fix:** a one-time script that ran the checker over all existing tasks, then I deleted it.

---

## Phase 9: Export

**Built:** download final labels as CSV or JSONL. Only completed tasks are exported, and gold questions are always excluded. The file-building code is separate from the Flask route.

---

## Phase 10: Background jobs (the hardest setup)

**Goal:** a Redis queue with a worker, so slow work never blocks the website.

**Problem 1: Redis does not run on native Windows.**
**Fix:** WSL2. I chose it over a cloud Redis because it matches how a Linux server behaves.

**Problem 2: creating the Linux user.** The password prompt shows nothing while typing. It looked broken, but it was just hidden input.

**Problem 3: `Waiting for cache lock`.** A fresh Ubuntu runs its own updates and holds the package lock.
**Fix:** wait a few minutes, and never kill lock files by force.

**Problem 4: jobs sat in `QUEUED` forever.** The worker was not running, and the Windows side had no `REDIS_URL` setting (`AttributeError: Config has no REDIS_URL`).
**Fix:** add `REDIS_URL` to the config, and start the worker.

**Problem 5: the worker environment would not build.** `python3 -m venv` failed with `404 Not Found` errors.
**Cause:** the package list was out of date.
**Fix:** `sudo apt update`, then install only `python3-venv` and `python3-pip` with `--no-install-recommends`.

**Problem 6: the worker could not read MySQL.** The worker runs in WSL, but MySQL ran on Windows. Connections to `127.0.0.1:3306` were refused.
**Fix:** WSL's **mirrored networking** (`networkingMode=mirrored` in `.wslconfig`), so `localhost` means the same thing on both sides. This kept the code unchanged.

**Problem 7: huge `requirements.txt`.** `pip install -r requirements.txt` in WSL tried to download packages from my other projects.
**Fix:** install only what the worker needs, and clean the file later, in the Docker phase.

**Problem 8: `wsl --shutdown` typed inside Linux** says "command not found". It is a Windows command. I learned to tell the prompts apart: `PS C:\...>` is Windows, `amit@amit:...$` is Linux.

---

## Phase 11: Groq pre-labeling

**Built:** `llm/groq_client.py` with `prelabel(text, labels)`, which asks Groq for JSON (`label` and `confidence`), validates the label against the project's options, and retries with a growing delay. A background job `jobs/prelabel.py` labels every task that has no prediction yet. The labeling screen shows the suggestion, and every human label records `accepted_ai`.

**Problem 1: `404 model_not_found`.** The model I picked (`llama-3.1-8b-instant`) had been retired.
**Fix:** switch to `openai/gpt-oss-20b`. This is exactly why the model name is a setting and not a constant.

**Problem 2: the job failed with `module 'jobs' has no attribute 'prelabel'`.** The real error was hidden. Importing the module by hand showed `No module named 'flask'`, because the WSL environment was missing the web packages.
**Lesson:** when a queue worker shows a vague import error, import the module manually to see the real one.

**Problem 3: `accepted_ai` stayed empty.** My `perform_submit_label` still had the old code.
**Fix:** I replaced the whole file, so no half-edited version remained. A one-off script then showed `True` and `False` values and a 3 of 5 acceptance rate.

---

## Phase 12: Annotator quality

**Built**
- **Hidden gold questions:** a CSV column `gold_label` marks tasks with a known answer. They are mixed in, shown without an AI hint, and excluded from consensus and exports.
- **Speed check:** labels under 1 second are flagged.
- **Annotator weight:** gold accuracy times (1 minus the share of too-fast labels).

**Problem:** gold tasks never appeared, and I kept getting the same 5 normal tasks.
**Cause:** I had uploaded the gold file twice (duplicate gold tasks), and the assignment code was not the new version.
**Fix:** a small test script that called `claim_next_task` directly proved the logic, so I replaced the whole file with a `GOLD_CHANCE` variable I could set to `1.0` for testing, and back to `0.2` afterwards.

---

## Phase 13: Agreement metrics

**Built:** `cohens_kappa(a, b)` as a pure function, and a dashboard with kappa for every pair of annotators, the AI against each annotator, and the most confused label pairs.

**Check:** I verified the formula on a tiny example before trusting the page.

---

## Phase 14: Dataset versioning

**Built:** snapshots of the final labels stored as JSON (v1, v2, ...), each downloadable later and unchanged by new labels.

**Lesson:** a snapshot only contained rows once tasks were `completed`, and that needs two annotators per task. "No versions yet" was correct until a second person labeled.

---

## Phase 15: LLM evaluation tasks

**Built:** project types **pairwise (A or B)** and **rating (1 to 5)**. They reuse the same labels, review queue, export and agreement code, because a pairwise project is just a project whose labels are `A` and `B`. The CSV parser, labeling screen and the AI prompt adapt to the type.

---

## Phase 16: Dashboard and the AI on/off switch

**Built:** a dashboard with progress, AI acceptance, time with AI vs without AI, and quality checks. An admin can switch the AI suggestion on or off per annotator, which makes a fair timing comparison possible.

**Problem:** adding the `see_ai` column. `create_all()` creates missing tables but never changes existing ones.
**Fix:** a one-time `ALTER TABLE`. This is the reason migrations are on my roadmap.

**Honest note:** my early dashboard showed `-267%` time saved from one slow label, and later `0%` because I was pressing keys without reading. Those numbers are not meaningful, and the real comparison needs real annotators.

---

## UI redesign

I redesigned the interface in several rounds, and the design changed three times because I compared it with real products.

1. Plain HTML, then a light CSS layer.
2. A modern layout after comparing sites like OpenTrain and Argilla.
3. A split login page with a gradient panel. I rejected it, because I wanted one white page.
4. Final design: a white and black theme, one violet accent, translucent floating data and LLM icons in the background, a home page with a top bar, and card-based pages.

**Problems**
- `TemplateNotFound: _icons.html`: a template included by `base.html` was never created.
- VS Code showed red errors on lines like `style="width: {{ x }}%"`. They were false alarms, because the CSS checker cannot read Jinja. I moved the number into a `data-w` attribute and set the width with one line of JavaScript.

---

## Phase 17: Docker

**Built:** a `Dockerfile` and a `docker-compose.yml` with four services: `web` (gunicorn), `worker` (RQ), `db` (MySQL 8.4) and `redis`. Containers talk through service names, and the same `DATABASE_URL` and `REDIS_URL` settings the app already supported.

**Problem 1: `failed to connect to the docker API`.** Docker Desktop was not running.

**Problem 2: the web container crashed with `Connection refused` to MySQL.**
**Cause:** MySQL's first start runs a temporary server that already passes a health check, then shuts down and restarts. Flask connected in that gap.
**Fix:** a health check that pings over the network (`-h 127.0.0.1`), plus `restart: on-failure` as a safety net.

**Problem 3: `Table 'users' already exists`.**
**Cause:** two gunicorn workers both ran `create_all()` at the same moment.
**Fix:** `gunicorn --preload`, so the app loads once.

**Problem 4: a 150-line `requirements.txt` from my other projects** (Streamlit, Gradio, spaCy, geopandas, and more).
**Fix:** a clean file with only the 10 packages LabelFlow uses. The image builds in under a minute.

**Problem 5: commands in the wrong terminal.** `docker` is not available inside WSL, and `wsl --shutdown` is not available in Linux. I added a rule to the run guide on which prompt runs which command.

---

## Deployment plan

The app is built to deploy without code changes: `DATABASE_URL` and `REDIS_URL` are read from the environment, and the web server is gunicorn. The plan uses **Render** (web app and worker in one container) and **Aiven** free MySQL and Valkey. Free tiers sleep after idle time, so the README leads with screenshots and a demo video.

---

## What I would do differently

- Write the clean `requirements.txt` on day one.
- Add database migrations from the start instead of `create_all()`.
- Automate a concurrency test for the claiming logic.
- Keep the model name and other external settings in `.env` from the first line of code. This already saved me when Groq retired a model.

## Skills this project gave me

Concurrent database access (row locks and constraints), background job queues, LLM integration with JSON output and retries, inter-annotator agreement statistics, role-based access control, Docker Compose, and debugging across Windows, WSL and containers.