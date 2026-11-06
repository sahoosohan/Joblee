# Joblee

Joblee is a private job application tracker. Organize applications on a Kanban board, keep company and interview notes together, and see which applications need a follow-up.

## Features

- Track applications in Applied, Interview, Offer, and Rejected stages.
- Add, edit, search, filter, and delete applications and companies.
- Move applications between stages by dragging cards or using the accessible stage menu.
- Keep application notes and a history of status changes.
- See follow-ups after seven days without activity; mark them done or snooze them.
- Review pipeline totals, response rate, and follow-ups due.
- Sign in with Google. This installation is intended for one user: the first Google account to sign in is linked to the tracker.
- Use the responsive interface in light or dark mode.

## Requirements

- Python 3.11 or newer
- Node.js 20 or newer, with npm
- A Google OAuth 2.0 client ID for Google sign-in

## Run the app

From the project root, run the launcher:

```bash
./sh.run
```

The launcher prepares the backend virtual environment, installs missing dependencies, and starts the FastAPI API and Vite frontend together. It reuses a running Joblee frontend when possible. Otherwise it uses port `5173`, or picks an available port from `5174` through `5199` if `5173` is already occupied. The API uses port `8000`.

Open the frontend URL printed by the launcher. The API documentation is at <http://127.0.0.1:8000/docs> and the health check is at <http://127.0.0.1:8000/api/v1/health>. Press **Ctrl+C** in the launcher terminal to stop the servers it started.

## Configure Google sign-in

1. In Google Cloud Console, create an OAuth client with application type **Web application**.
2. Add these **Authorized JavaScript origins**:
   - `http://localhost:5173`
   - `http://127.0.0.1:5173`
3. Copy the root and frontend environment templates:

   ```bash
   cp .env.example .env
   cp frontend/.env.example frontend/.env.local
   ```

4. Set the same Google client ID in `GOOGLE_CLIENT_ID` in `.env` and `VITE_GOOGLE_CLIENT_ID` in `frontend/.env.local`.
5. Restart the launcher after changing environment files.

The Google Identity Services popup flow uses authorized JavaScript origins; no redirect URI is needed for local development. If the launcher selects a port other than `5173`, add both `http://localhost:<port>` and `http://127.0.0.1:<port>` as authorized JavaScript origins in Google Cloud Console, then reload the page. Never put a Google client secret in frontend environment variables; this app only needs the web client ID.

## Environment variables

| File | Variable | Purpose |
| --- | --- | --- |
| `.env` | `GOOGLE_CLIENT_ID` | Google web client ID verified by the API |
| `.env` | `DATABASE_URL` | SQLAlchemy database URL; defaults to local SQLite |
| `frontend/.env.local` | `VITE_GOOGLE_CLIENT_ID` | Client ID used by Google sign-in in the browser; must match the API value |
| `frontend/.env.local` | `VITE_API_URL` | API origin; defaults to `http://127.0.0.1:8000` |

Local environment files are ignored by Git. Keep credentials and local configuration out of commits.

## Sample data

To add sample companies and applications, open another terminal and run:

```bash
cd backend
.venv/bin/python -m app.seed
```

On Windows, use `.venv\Scripts\python.exe -m app.seed` from the `backend` directory. To drop and recreate the database tables before loading the sample data, add `--reset`. **This deletes the existing tracker data in that database.**

## API overview

The API is versioned under `/api/v1`. Application, company, note, stats, and follow-up endpoints require a signed-in session. The health check and Google sign-in setup endpoints are public.

Useful endpoints:

- `GET /api/v1/health` — service health
- `GET /api/v1/auth/status` — whether the tracker needs its first Google account
- `POST /api/v1/auth/google` — exchange a Google credential for a Joblee session
- `GET /api/v1/applications` — list and filter applications
- `GET /api/v1/companies` — list companies
- `GET /api/v1/follow-ups` — list applications due for follow-up
- `GET /api/v1/stats` — pipeline totals and response rate

Interactive API docs are available at <http://127.0.0.1:8000/docs> while the app is running.

## Tech stack

- **Frontend:** React, TypeScript, Vite, Tailwind CSS, dnd-kit, TanStack Query, Sonner
- **Backend:** FastAPI, Pydantic, SQLAlchemy
- **Database:** SQLite by default; other SQLAlchemy-compatible databases can be configured with `DATABASE_URL`
- **Authentication:** Google Identity Services with Google ID token verification by the API

## Project structure

```text
backend/
  app/              API, authentication, database models, queries, and sample data
frontend/
  src/              React application, pages, and UI components
PRD.md              Product requirements and data model
run.py              Cross-platform development launcher
sh.run              Shell launcher (`./sh.run`)
```

## Development commands

Run the frontend production build from `frontend`:

```bash
npm run build
```

Run backend checks from `backend`:

```bash
.venv/bin/python -m pytest
```

On Windows, replace `.venv/bin/python` with `.venv\Scripts\python.exe`.
