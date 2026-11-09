# Run Guide

How to start, use and shut down LabelFlow on Windows. There are two ways to run it. **Use Docker unless you are developing.**

| | Docker (recommended) | Local mode (development) |
|---|---|---|
| What runs | 4 containers: web, worker, MySQL, Redis | Python on Windows, MySQL on Windows, Redis and the worker in WSL |
| Setup effort | Install Docker Desktop, one command | Several one-time steps |
| Good for | Running and demoing the project | Editing code with instant reload |

> **Do not run both at once.** They use the same port (5000) and the same ideas of a database, so pick one.

## Which window runs which command

This is the most common source of mistakes.

| Prompt looks like | It is | Use it for |
|---|---|---|
| `PS C:\...>` | Windows PowerShell | `docker`, `git`, `python app.py`, `wsl --shutdown`, `net start` |
| `amit@amit:...$` | Linux (WSL) | `redis`, the RQ worker, `apt`, `pip` inside WSL |

`wsl --shutdown` and `docker` do **not** work inside WSL. Type `exit` to go back to PowerShell.

---

## Option A: Docker

### One-time setup
1. Install [Docker Desktop](https://www.docker.com/products/docker-desktop/) (it uses WSL2).
2. Clone the repository and open a terminal in its folder.
3. Create a `.env` file (copy `.env.example`) with at least:
```env
SECRET_KEY=change-this-to-a-long-random-text
GROQ_API_KEY=your_groq_key_here
GROQ_MODEL=openai/gpt-oss-20b
```

### Start
1. Open **Docker Desktop** and wait until the bottom left says **Engine running**.
2. In PowerShell:
```powershell
cd path\to\labelflow
docker compose up --build
```
The first build takes a few minutes. Later starts take seconds, and you can drop `--build` unless you changed code.

3. You are ready when the logs show:
   - `web-1 ... Listening at: http://0.0.0.0:5000`
   - `worker-1 ... Listening on default...`
4. Open **http://localhost:5000**.

### Use it
1. Register. **The first account becomes the admin.**
2. Create a project and upload `sample_data/emails.csv`.
3. Click **Run AI pre-labeling**. The `worker-1` lines show the job and then `Job OK`.
4. Click **Start labeling** and press `1` or `2`.
5. For a second annotator, open a private window and register another account. Promote a reviewer on the **Users** page.

### Stop
1. In the terminal running Docker, press **Ctrl + C**.
2. Remove the containers, keeping your data:
```powershell
docker compose down
```
To also delete the database: `docker compose down -v`.

3. Quit Docker Desktop: click the `^` in the taskbar, right-click the whale icon, then **Quit Docker Desktop**.
4. Fully stop WSL:
```powershell
wsl --shutdown
```
5. Check everything is off. Both rows should say `Stopped`:
```powershell
wsl --list --verbose
```

> `wsl --shutdown` also stops Docker's engine, so only run it when you are done with Docker.

### Start again later
Open Docker Desktop, wait for **Engine running**, then `docker compose up`. Your data is still there.

---

## Option B: Local mode (development)

Python and MySQL run on Windows. **Redis and the background worker run in WSL2**, because Redis and RQ do not run on native Windows.

### One-time setup

**1. Install WSL2** (PowerShell as Administrator), restart, then create a Linux user when Ubuntu opens:
```powershell
wsl --install
```
The password prompt shows nothing while you type. That is normal.

**2. Install Redis and Python tools** (in WSL):
```bash
sudo apt update
sudo apt install -y redis-server
sudo apt install -y --no-install-recommends python3-venv python3-pip
```
If you see `Waiting for cache lock`, Ubuntu is updating itself. Wait a few minutes.

**3. Create the worker environment** (in WSL):
```bash
python3 -m venv ~/wsl-venv
source ~/wsl-venv/bin/activate
pip install flask flask-sqlalchemy flask-login pymysql cryptography python-dotenv redis rq groq
```
Do **not** run `pip install -r requirements.txt` here if your file is large.

**4. Let WSL reach MySQL on Windows.** In PowerShell:
```powershell
Set-Content -Path "$env:USERPROFILE\.wslconfig" -Value "[wsl2]`nnetworkingMode=mirrored"
wsl --shutdown
```
Then check inside WSL that `wslinfo --networking-mode` prints `mirrored`.

**5. Windows side** (PowerShell, in the project folder):
```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
Create a MySQL database called `labelflow` and fill `.env` (`DB_USER`, `DB_PASSWORD`, `DB_NAME`, `REDIS_URL=redis://localhost:6379/0`, and the Groq settings).

### Start (3 windows)

**1. MySQL** (PowerShell as Administrator). Skip if it is already running:
```powershell
Get-Service MySQL*
net start MySQL93
```
Use the service name that `Get-Service` shows. Yours may be `MySQL80`.

**2. WSL window 1: Redis**
```powershell
wsl
```
```bash
sudo service redis-server start
redis-cli ping
```
You should see `PONG`. Keep this window open, because it also keeps WSL running.

**3. WSL window 2: the worker.** Open a new PowerShell, then:
```powershell
wsl
```
```bash
cd "/mnt/c/path/to/labelflow"
source ~/wsl-venv/bin/activate
rq worker --url redis://localhost:6379/0 --path .
```
You should see `Listening on default...`. Keep it open. Do not forget the dot at the end of the last line.

**4. The website** (VS Code or PowerShell, in the project folder)
```powershell
venv\Scripts\activate
python app.py
```
Open **http://127.0.0.1:5000**.

### Stop
1. **Ctrl + C** in the Flask window and in the worker window.
2. In the Redis window:
```bash
sudo service redis-server stop
exit
```
3. In PowerShell:
```powershell
wsl --shutdown
```
4. Optional, to stop MySQL (PowerShell as Administrator):
```powershell
net stop MySQL93
```

---

## Troubleshooting

| What you see | Cause | Fix |
|---|---|---|
| `failed to connect to the docker API` | Docker Desktop is not running | Open Docker Desktop and wait for **Engine running** |
| `docker: command not found` in WSL | Wrong window | Type `exit` and use PowerShell |
| `redis.exceptions.ConnectionError` (local mode) | Redis is not running | `sudo service redis-server start` in WSL |
| AI pre-labeling count stays 0 | Worker is not running or Groq failed | Check the worker window, `GROQ_API_KEY` and `GROQ_MODEL` |
| `404 model_not_found` from Groq | The model was retired | Change `GROQ_MODEL` in `.env` to a current model |
| Job stays `QUEUED` | No worker is listening | Start the worker. In Docker, check `worker-1` is up |
| `No module named 'flask'` in the worker | WSL environment is incomplete | Activate `~/wsl-venv` and run the `pip install` line from setup |
| Worker cannot reach MySQL | WSL networking is not mirrored | Redo setup step 4 and check `wslinfo --networking-mode` |
| `Access denied for user 'root'` | Wrong database password | Fix `DB_PASSWORD` in `.env` |
| `TemplateNotFound` | A template file is missing | Check the file exists in `templates/` |
| `Table 'users' already exists` on start (Docker) | Two web workers created tables at once | Make sure the Dockerfile uses `gunicorn --preload` |
| Port 5000 already in use | Local Flask and Docker are both running | Stop one of them |
| Start labeling shows "No tasks left" | Everything is labeled by the required number of people | Upload more rows or use another account |
| Browser shows old styles | Cached CSS | Hard refresh with **Ctrl + F5** |
| Cannot log in after a fresh Docker start | The database is new and empty | Register again. The first account becomes admin |

## Quick reference

```powershell
# Docker
docker compose up --build     # start
docker compose down           # stop, keep data
docker compose down -v        # stop and delete data
docker compose logs -f worker # watch the worker

# WSL
wsl --list --verbose          # is anything running?
wsl --shutdown                # stop WSL completely
```