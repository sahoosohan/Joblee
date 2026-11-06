# Joblee

Joblee is a single-user job application tracker. Keep applications organized across a four-stage Kanban board, record notes and status changes, and get a reminder when an application has been quiet for seven days.

## Features

- Create, update, search, filter, and delete job applications
- Move applications by dragging a card or using its stage menu
- Manage companies and see the number of linked applications
- Keep notes and review application status history
- Track follow-ups, mark them complete, or snooze them for three days
- View pipeline totals and response rate from server-side SQL aggregates
- Use the board on mobile and desktop, in light or dark mode

## Run locally

Requirements: Python 3.11 or newer and Node.js 20 or newer (npm is included with Node.js).

Google sign-in requires a Google OAuth **Web application** client ID. In Google Cloud Console, add `http://localhost:5173` and `http://127.0.0.1:5173` as authorized JavaScript origins. Copy [.env.example](./.env.example) to `.env` in the project root, and [frontend/.env.example](./frontend/.env.example) to `frontend/.env.local`. Put the same client ID in `GOOGLE_CLIENT_ID` and `VITE_GOOGLE_CLIENT_ID`.

From the project root, run:

```bash
python run.py
```

The launcher creates the backend virtual environment and installs missing backend or frontend dependencies, then starts both development servers. It uses port `5173` when available and selects the next free port if needed. Open the printed frontend URL; API docs are at `http://127.0.0.1:8000/docs`. Press Ctrl+C once to stop both servers. To load sample data, run `cd backend && .venv/bin/python -m app.seed --reset` (Windows: `.venv\\Scripts\\python.exe -m app.seed --reset` from `backend`). Set `VITE_API_URL` in `frontend/.env.local` to change the API origin. If the frontend uses a port other than `5173`, add that port’s localhost origins to the Google OAuth client settings.

## Stack

- Frontend: React, TypeScript, Vite, Tailwind CSS, dnd-kit, Sonner
- Backend: FastAPI, Pydantic, SQLAlchemy
- Database: SQLite by default; configure another SQLAlchemy `DATABASE_URL` as needed

## Project layout

```text
backend/app/       API, schemas, CRUD, models, seed data
frontend/src/      React application and UI components
PRD.md             Product requirements and data model
```
