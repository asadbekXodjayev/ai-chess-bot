# Chess Bot — How to Run & Deploy

A web app to play chess against a custom AI.

- **Backend** — Python / FastAPI. Computes bot moves with a pure-Python chess engine (`ai_engine.py`). Runs on port **8000**.
- **Frontend** — React 18 / Vite / Tailwind. Renders the board, talks to the backend over JSON. Dev server on port **5173**.

The backend is stateless — the board position (FEN) is passed back and forth on every request, so no database or session storage is needed.

---

## 1. Server Requirements (what must be installed)

### Backend server

| Requirement | Version | Notes |
|---|---|---|
| Python | 3.10 or newer | 3.11/3.12 recommended |
| pip + venv | bundled with Python | for the virtual environment |
| fastapi | >= 0.109.0 | installed via `requirements.txt` |
| uvicorn[standard] | >= 0.27.0 | ASGI server, installed via `requirements.txt` |
| python-chess | >= 1.999 | installed via `requirements.txt` |
| pydantic | >= 2.5.0 | installed via `requirements.txt` |

> **No GPU, no torch, no database needed.** The engine is pure Python.
> `torch`/`numpy`/`tqdm` in `requirements.txt` are commented out — they belong to
> legacy training scripts (`train_ai*.py`, `*.pth`) that are NOT used by the app.
> Do not install them on the server.

Hardware: any small VPS works (1 vCPU / 512 MB RAM is enough). A faster CPU = faster/stronger bot moves.

### Frontend build machine (or same server)

| Requirement | Version |
|---|---|
| Node.js | 18 or newer (20 LTS recommended) |
| npm | comes with Node |

Node is only needed to **build** the frontend. The build output (`frontend/dist/`) is static files — serve them with nginx, Apache, or any static host (Vercel/Netlify). Node does not need to run in production.

---

## 2. Run the Backend (do this first)

All commands are run from the `backend/` directory.

### Linux server

```bash
cd backend

# create and activate a virtual environment
python3 -m venv venv
source venv/bin/activate

# install dependencies
pip install -r requirements.txt

# start the API server (listens on all interfaces, port 8000)
uvicorn main:app --host 0.0.0.0 --port 8000
```

### Windows

```powershell
cd backend

python -m venv venv
venv\Scripts\python.exe -m pip install -r requirements.txt

venv\Scripts\python.exe -m uvicorn main:app --host 0.0.0.0 --port 8000
```

### Verify the backend is working

```bash
# list difficulty levels
curl http://127.0.0.1:8000/api/levels

# ask for a bot move from the starting position
curl -X POST http://127.0.0.1:8000/api/bot-move \
  -H "Content-Type: application/json" \
  -d '{"current_fen":"rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1","level":"hard"}'
```

You should get back JSON with the bot's move, the new FEN, and an evaluation.

### Keep it running in production (Linux, systemd)

Create `/etc/systemd/system/chess-backend.service`:

```ini
[Unit]
Description=Chess Bot FastAPI backend
After=network.target

[Service]
User=www-data
WorkingDirectory=/opt/chess-bot/backend
ExecStart=/opt/chess-bot/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now chess-backend
sudo systemctl status chess-backend
```

---

## 3. Run the Frontend

All commands are run from the `frontend/` directory.

### Development (local)

```bash
cd frontend
npm install
npm run dev        # opens Vite dev server on http://localhost:5173
```

### Production build

```bash
cd frontend
npm install
npm run build      # outputs static files to frontend/dist/
```

Serve `dist/` with any static file server, e.g. nginx:

```nginx
server {
    listen 80;
    server_name your-domain.com;

    root /opt/chess-bot/frontend/dist;
    index index.html;

    location / {
        try_files $uri /index.html;
    }
}
```

---

## 4. IMPORTANT — Two things to change before deploying

The app currently assumes everything runs on `localhost`. For a real server you must update both sides:

### a) Frontend → backend URL

`frontend/src/App.jsx` (line ~154) hardcodes the backend address:

```js
const API_URL = 'http://localhost:8000';
```

Change it to your server's public backend URL (e.g. `https://your-domain.com:8000` or `https://api.your-domain.com`) **before** running `npm run build`.

### b) Backend CORS allowlist

`backend/main.py` only allows requests from localhost origins:

```python
allow_origins=[
    "http://localhost:5173", "http://localhost:3000",
    "http://127.0.0.1:5173", "http://127.0.0.1:3000",
],
```

Add your frontend's public origin (e.g. `"https://your-domain.com"`) to this list, otherwise the browser will block the API calls.

---

## 5. Quick Checklist

1. Install Python ≥ 3.10 and Node ≥ 18 on the server.
2. `cd backend` → create venv → `pip install -r requirements.txt`.
3. Edit `backend/main.py` CORS list — add your frontend domain.
4. Start backend: `uvicorn main:app --host 0.0.0.0 --port 8000` (use systemd to keep it alive).
5. Edit `frontend/src/App.jsx` — set `API_URL` to your backend's public URL.
6. `cd frontend` → `npm install` → `npm run build`.
7. Serve `frontend/dist/` with nginx (or deploy to Vercel/Netlify).
8. Open the site, play a move, and confirm the bot replies.

## API Reference (for sanity checks)

| Method | Endpoint | Body | Returns |
|---|---|---|---|
| GET | `/api/levels` | — | available difficulty levels |
| POST | `/api/bot-move` | `{"current_fen": "<FEN>", "level": "beginner\|easy\|intermediate\|hard\|expert\|max"}` | bot move (SAN/UCI), new FEN, eval, game-state flags |
