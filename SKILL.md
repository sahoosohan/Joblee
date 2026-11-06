---
name: job-tracker-builder
description: Build, extend or debug the "Job Application Tracker" full-stack project (React + Tailwind CSS + Shadcn/UI Kanban board, FastAPI + SQL backend with companies, applications and notes tables, Git). Use this skill whenever the user mentions the job tracker, job application board, Kanban stages (Applied, Interview, Offer, Rejected), follow-up reminders, application notes, company JOINs, drag and drop of applications, or says "continue the project" or "next step", even if they do not name the skill. Always read PRD.md in the project root first.
---

# Job Application Tracker Builder

Guides Claude to build the project in `PRD.md` one verified phase at a time. The goal is a fully working, well-designed app, not a skeleton.

## Ground rules

1. **Read `PRD.md` first.** It is the source of truth for scope, data model, API and acceptance criteria. Do not add features outside it without asking.
2. **Work in phases.** Finish and verify one phase before starting the next. After each phase, report what was built, how to run/test it, and what comes next.
3. **Verify, don't assume.** Run the server, run pytest, hit endpoints with curl, load the UI. Report real results.
4. **Commit after every phase** with conventional commits (`feat:`, `fix:`, `chore:`, `docs:`, `test:`).
5. **Keep code beginner-readable.** Short functions, clear names, comments that explain *why*.
6. **The database is the source of truth.** Stats, joins and follow-up logic are computed in SQL on the server, never recomputed on the client.
7. **Store timestamps in UTC.** Dates are `YYYY-MM-DD` strings over the wire.

## Phase 1: Setup and Git

```bash
mkdir job-tracker && cd job-tracker && git init
mkdir backend frontend
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install fastapi "uvicorn[standard]" sqlalchemy pydantic pytest httpx freezegun
pip freeze > requirements.txt
# Frontend
cd ../frontend && npm create vite@latest . -- --template react-ts && npm install
npm install -D tailwindcss @tailwindcss/vite
npm install react-router-dom @tanstack/react-query react-hook-form zod @hookform/resolvers \
  @dnd-kit/core @dnd-kit/sortable @dnd-kit/utilities date-fns lucide-react sonner
npx shadcn@latest init
npx shadcn@latest add button card input label select dialog alert-dialog sheet badge textarea form \
  popover calendar command dropdown-menu tabs skeleton sonner tooltip separator scroll-area toggle-group avatar
```
Add `.gitignore` (`.venv/`, `node_modules/`, `*.db`, `.env`, `__pycache__/`, `dist/`). Commit: `chore: scaffold backend and frontend`.

**Verify:** `uvicorn app.main:app --reload` serves `/api/v1/health`; `npm run dev` shows the Vite page.

## Phase 2: Database and models

- `config.py`: `DATABASE_URL` (default `sqlite:///./jobs.db`), `FOLLOW_UP_DAYS = 7`, CORS origins.
- `database.py`: engine, `SessionLocal`, `get_db`. For SQLite, enable foreign keys with `PRAGMA foreign_keys=ON` on every connection.
- `models.py`: `Company`, `Application`, `Note`, `StatusHistory` exactly as in the PRD, with relationships (`Company.applications`, `Application.company`, `Application.notes`, `Application.history`) and cascade delete for notes and history.
- Use a Python `Enum` for status and work mode, and keep the DB `CHECK` constraints.
- `seed.py`: ~8 companies and ~25 applications spread across all four stages, some Applied rows with `last_activity_at` 8 to 15 days ago so follow-ups can be seen, plus a few notes. Add a `--reset` flag.

**Verify:** run the seed, then `sqlite3 jobs.db "SELECT a.job_title, c.name FROM applications a JOIN companies c ON c.id=a.company_id LIMIT 5;"`.

## Phase 3: Companies and applications API

- `schemas.py` (Pydantic v2): `CompanyCreate/Out`, `ApplicationCreate/Update/Out`, `ApplicationDetail` (company, notes, history). Validate title length, `applied_date` not in the future, `job_url` is a valid http(s) URL, `salary_min <= salary_max`.
- `POST /applications` accepts either `company_id` or a nested `company` (create-or-get by case-insensitive name).
- `GET /applications`: JOIN with companies (use `joinedload`/`selectinload` or an explicit join to avoid N+1), filters `q`, repeatable `status`, `work_mode`, `source`, `needs_follow_up`.
- Companies CRUD; `GET /companies` includes `application_count`; `DELETE` returns 409 when applications exist.
- 404 for missing rows, 409 for duplicates, 422 for bad input. Prefix routes with `/api/v1`; enable CORS for `http://localhost:5173`.

**Verify:** pytest for each validation rule, JOIN output containing company fields, search across title/company/location, duplicate company 409, company-with-applications delete 409.

## Phase 4: Status, notes, follow-ups, stats

- `PATCH /applications/{id}/status`: validates the stage, writes a `status_history` row, and updates `last_activity_at` and `updated_at`. Leaving `applied` clears `snoozed_until`.
- Notes endpoints; creating a note updates the parent's `last_activity_at`.
- Follow-up logic in one reusable query/helper used by `/follow-ups`, the `needs_follow_up` filter and the stats:
  status = `applied` AND `last_activity_at <= now - FOLLOW_UP_DAYS` AND (`snoozed_until` IS NULL OR `snoozed_until <= today`).
- `POST /follow-ups/{id}/done`: adds the note "Followed up" and updates `last_activity_at`. `POST /follow-ups/{id}/snooze`: sets `snoozed_until = today + days`.
- `GET /stats`: one aggregate query with `COUNT(*)` and `FILTER`/`CASE`; also returns `response_rate` and `follow_ups_due`. It accepts the same filters as the list so the numbers match the board.

**Verify:** tests with `freezegun` for the 6/7/8-day boundary, snooze, done, status history rows, and stats matching a manual count.

## Phase 5: Frontend shell

- Tailwind v4 via the Vite plugin; Shadcn theme tokens in `index.css`; Inter font.
- `lib/constants.ts`: stage config (key, label, color, icon) shared everywhere.
- `lib/api.ts`: typed `fetch` wrapper using `VITE_API_URL` with a typed error class.
- `lib/schemas.ts`: Zod schemas mirroring backend rules.
- `hooks/`: TanStack Query hooks (`useApplications(filters)`, `useStats(filters)`, `useFollowUps`, `useMoveApplication`, `useCompanies`, notes hooks). Mutations invalidate `applications`, `stats` and `follow-ups`.
- Layout: top bar with logo, nav (Board, Companies), dark-mode toggle, and a prominent "Add application" button. Mobile uses a compact header.

**Verify:** routes work, dark mode persists, layout holds at 360 px and 1440 px.

## Phase 6: Board UI with drag and drop

- `Board` renders four `Column`s from the stage config; each column header shows color, icon and count.
- `ApplicationCard`: company avatar (initials), job title, company name, location + work mode, applied date ("Applied 5 days ago"), note count, amber "Follow up" badge when due, and a dropdown with Open, Edit, Move to..., Delete.
- dnd-kit: `DndContext` with `PointerSensor` (activation distance 5 px), `TouchSensor` and `KeyboardSensor`; `DragOverlay` for the dragged card; columns are droppable.
- `useMoveApplication` does an **optimistic update** (move the card in the query cache), calls `PATCH /status`, and on error rolls back and shows a toast.
- Skeleton columns while loading, empty state per column, error state with retry.
- On mobile, make columns horizontally scrollable with snap, and rely on the "Move to..." menu.

**Verify:** drag a card between every pair of columns, confirm persistence after reload, simulate a failed request and confirm rollback, and try keyboard moves.

## Phase 7: Forms, company combobox and detail drawer

- `ApplicationFormDialog` (add and edit): React Hook Form + Zod. Fields: company (combobox), job title, status, applied date (Popover + Calendar), job URL, location, work mode (ToggleGroup), salary min/max, source.
- `CompanyCombobox` using Shadcn `Command`: search existing companies and offer "Create 'X'" inline.
- `ApplicationDrawer` (Sheet): header with title, company, stage selector; details grid; notes timeline (add, edit, delete, relative timestamps); status history list; follow-up actions when due; delete with `AlertDialog`.
- Companies page: list with application counts, add/edit dialog, delete with the 409 error shown clearly.

**Verify:** create with an existing company, create with a new company, edit, add a note and see `last_activity_at` move, and check the form error messages.

## Phase 8: Search, filters, reminders and stats UI

- Stats row of cards: Total, Interviews, Offers, Rejected, Response rate, Follow-ups due. Use skeletons while loading.
- Toolbar: debounced (300 ms) search input, stage toggle chips, work-mode and source selects, "Needs follow-up" switch, "Clear filters". Keep filters in the URL search params so refresh and sharing work.
- Reminders panel/banner (amber): list of due follow-ups with days waiting and actions Mark as followed up, Snooze 3 days, Move to Rejected. Collapsible.
- Board and stats use the same filter object so the numbers always match.

**Verify:** combine search + status filters, confirm stats match the visible cards, run the follow-up flow end to end.

## Phase 9: Polish and tests

- Backend: `pytest` green (CRUD, validation, JOINs, filters, status history, follow-up boundaries, stats).
- Frontend: a few Vitest + Testing Library tests (form validation, card follow-up badge, filter bar) if time allows.
- Accessibility: labels, visible focus, dialog focus trap, keyboard drag and drop, status never by color alone.
- Run `npm run lint` and `npm run build`; check the browser console for errors.
- Visual pass: consistent spacing, hover and focus states, subtle transitions, tabular numerals in stats.

## Phase 10: Docs and ship

- `README.md`: overview, screenshots or GIF of drag and drop, features, stack, setup in under 5 minutes, API docs link (`/docs`), project structure, future ideas.
- Optional deploy: backend on Render/Railway (switch `DATABASE_URL` to PostgreSQL; replace `julianday` with `NOW() - INTERVAL '7 days'`), frontend on Vercel/Netlify with `VITE_API_URL`.
- Tag `v1.0.0`.

## Design standards

- **Look:** clean and spacious; neutral palette with one accent; rounded-xl cards, 1 px borders, soft shadows; 8 px spacing grid.
- **Stage colors:** Applied blue, Interview violet, Offer green, Rejected red/gray, each with an icon and label.
- **Typography:** Inter; page title 24 to 30 px, card title 14 to 16 px, stat numbers large and bold with tabular numerals.
- **Board feel:** columns have a subtle tinted background, cards lift on hover, a dragged card has a shadow and slight rotation, a drop target highlights.
- **Feedback:** every action has loading, success and error feedback. No blank screens.
- **Responsive:** mobile first; drawers become full screen on small devices.

## Definition of done (per phase)

- [ ] It runs without errors
- [ ] It was tested and the real results were reported
- [ ] Code is formatted and linted
- [ ] It is committed with a clear message
- [ ] The user was told what is next

## Common pitfalls

| Problem | Fix |
|---------|-----|
| Foreign keys ignored in SQLite | Run `PRAGMA foreign_keys=ON` on connect |
| N+1 queries on the board | Eager load company and note counts in one query |
| Card snaps back after drop | Update the cache optimistically and invalidate on settle |
| Drag starts on every click | Set a `PointerSensor` activation distance |
| Stats differ from board | Share one filter object and one query helper |
| Follow-up off by one day | Compare timestamps (`<= now - 7 days`) and test 6, 7 and 8 days with frozen time |
| Duplicate companies | Case-insensitive unique name and create-or-get logic |
| CORS blocked | Add the Vite origin to `allow_origins` |
