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

4. Set the Google client ID in `GOOGLE_CLIENT_ID` in `.env` and `VITE_GOOGLE_CLIENT_ID` in `frontend/.env.local`.
5. Restart the launcher after changing environment files.

The Google Identity Services popup flow uses authorized JavaScript origins; no redirect URI is needed. If the launcher selects a port other than `5173`, add both `http://localhost:<port>` and `http://127.0.0.1:<port>` as authorized JavaScript origins in Google Cloud Console, then reload the page. Never put a Google client secret in frontend environment variables; this app only needs the web client ID.

## Environment variables

| File | Variable | Purpose |
| --- | --- | --- |
| `.env` | `GOOGLE_CLIENT_ID` | Google web client ID verified by the API |
| `.env` | `DATABASE_URL` | SQLAlchemy database URL; defaults to local SQLite |
| `frontend/.env.local` | `VITE_GOOGLE_CLIENT_ID` | Client ID used by Google sign-in in the browser; must match the API value |
| `frontend/.env.local` | `VITE_API_URL` | Optional API origin; local development proxies `/api` to `http://127.0.0.1:8000`, and production uses the same origin by default |

Local environment files are ignored by Git. Keep credentials and local configuration out of commits.

## Free deployment

The included [render.yaml](./render.yaml) and [Dockerfile](./Dockerfile) deploy the frontend and API together as one free Render web service. Use Supabase Free for PostgreSQL so application data survives Render restarts and deploys.

1. Create a Supabase project on the Free plan and save its database password.
2. In Supabase, open **Connect**, select **Session pooler**, and copy its connection string. Use the session pooler on port `5432`; it supports IPv4 connections from Render. Replace the password placeholder and URL-encode any reserved characters in the password.
3. Push this repository, including the deployment files, to GitHub.
4. In Render, choose **New → Blueprint**, connect the GitHub repository, and deploy the Blueprint. Enter the Supabase connection string for `DATABASE_URL` and your OAuth web client ID for `GOOGLE_CLIENT_ID` when prompted.
5. After Render gives the service its `onrender.com` URL, add that exact HTTPS origin (for example, `https://joblee.onrender.com`) to **Authorized JavaScript origins** for the OAuth client in Google Cloud Console. No redirect URI is needed.
6. Open the Render URL and sign in with the Google account that should own this single-user tracker. The first account to sign in is linked to the database.

The deployment serves the React app and `/api/v1` from the same origin. Its Google client ID is injected when the container starts, so it does not need to be baked into the frontend build. The Render service creates the database tables on startup; it does not copy existing data from `backend/jobs.db`.

Free hosting has sleep and inactivity limits: Render spins down free web services after 15 minutes without traffic, and the next request can take about a minute to wake them. Render's free filesystem is temporary, so the hosted database must be PostgreSQL rather than SQLite. Supabase Free currently includes 500 MB of database storage and may pause projects after a week of low activity. See [Render's free service limits](https://render.com/docs/free), [Supabase Free plan](https://supabase.com/pricing), and [Supabase connection options](https://supabase.com/docs/guides/database/connecting-to-postgres).

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
- **Database:** SQLite locally; PostgreSQL for deployment
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
