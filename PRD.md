# PRD: Job Application Tracker

**Version:** 1.0  **Status:** Ready to build
**Stack:** React.js (Vite + TypeScript), Tailwind CSS, Shadcn/UI, FastAPI (Python), SQL (SQLite, PostgreSQL ready), Git

---

## 1. Overview

A full-stack web app to track job applications on a Kanban-style board by stage (Applied, Interview, Offer, Rejected). Each application can be moved between stages, linked to a company, annotated with notes, searched and filtered. The app reminds the user to follow up on applications that have had no reply for 7 days and shows quick stats using SQL COUNT queries.

**Goal:** a polished, fully working portfolio project that demonstrates relational database design (JOINs), REST API design, a drag-and-drop UI and clean component architecture.

## 2. Target User

A job seeker managing many applications at once who wants one clear place to see where each stands and what needs attention. Single user, no login in v1.

## 3. Scope

### In scope (v1)
1. Kanban board with 4 columns: Applied, Interview, Offer, Rejected
2. Move applications between stages by drag and drop, and via a menu (for mobile and keyboard users)
3. Application CRUD (create, view, edit, delete)
4. Company data (name, website, location, industry) linked to applications
5. Notes per application (add, edit, delete), shown as a timeline
6. Search and status filters
7. Follow-up reminders for applications with no reply after 7 days
8. Quick stats from SQL COUNT queries: total applications, interviews, offers (plus rejected and response rate)
9. Input validation on server and client
10. Responsive layout and light/dark mode

### Out of scope (v1)
Authentication, multi-user, email integration, resume upload, calendar sync, browser extension, AI features.

## 4. Functional Requirements

### 4.1 Board
| ID | Requirement |
|----|-------------|
| BD1 | Four columns in fixed order: Applied, Interview, Offer, Rejected. Each header shows a count |
| BD2 | Each card shows company, job title, location, applied date, and a "Follow up" badge when due |
| BD3 | Dragging a card to another column updates its status immediately (optimistic update, rolled back with an error toast on failure) |
| BD4 | A card menu offers "Move to..." for keyboard and touch use |
| BD5 | Clicking a card opens a detail drawer |
| BD6 | Cards within a column are ordered by most recently updated |
| BD7 | Empty columns show a friendly empty state |

### 4.2 Applications
| ID | Requirement |
|----|-------------|
| A1 | Add an application: company (pick existing or create new), job title, status (default Applied), applied date, job URL, location, work mode (Onsite / Hybrid / Remote), salary range (optional), source (LinkedIn, Referral, Company site, Other) |
| A2 | Edit any field, delete after confirmation |
| A3 | Job title 1 to 120 chars; applied date not in the future; job URL must be a valid http(s) URL if given; salary min must be <= salary max |
| A4 | Every status change is recorded in a status history with a timestamp |

### 4.3 Companies
| ID | Requirement |
|----|-------------|
| C1 | Create companies inline while adding an application, or from a Companies page |
| C2 | Company names are unique (case-insensitive) |
| C3 | Companies page lists each company with its number of applications |
| C4 | A company with applications cannot be deleted (409 with a clear message) |

### 4.4 Notes
| ID | Requirement |
|----|-------------|
| N1 | Add a note (1 to 2000 chars) to an application from the detail drawer |
| N2 | Notes show newest first with relative timestamps |
| N3 | Edit and delete notes |
| N4 | Adding a note counts as activity on the application (updates `last_activity_at`) |

### 4.5 Search and filters
| ID | Requirement |
|----|-------------|
| S1 | Debounced (300 ms) search across job title, company name and location |
| S2 | Status filter (multi-select chips) |
| S3 | Optional filters: work mode, source, "Needs follow-up only" |
| S4 | Filters apply to the board and update the stats consistently |
| S5 | "Clear filters" button; active filters are visible |

### 4.6 Follow-up reminders
| ID | Requirement |
|----|-------------|
| F1 | An application **needs follow-up** when its status is Applied, it has had no activity (no note, no status change, no edit marked as contact) for 7 or more days, and it has not been dismissed |
| F2 | The 7-day threshold is a backend setting (`FOLLOW_UP_DAYS = 7`) |
| F3 | A reminders panel on the dashboard lists due follow-ups with days waiting, company and title |
| F4 | Actions per reminder: "Mark as followed up" (adds an auto note and resets the 7-day timer), "Snooze 3 days", "Move to Rejected" |
| F5 | Cards show an amber "Follow up" badge when due |

### 4.7 Quick stats (SQL COUNT)
| ID | Requirement |
|----|-------------|
| ST1 | Stat cards: Total applications, Interviews, Offers, Rejected |
| ST2 | Derived: response rate = (Interview + Offer + Rejected) / Total |
| ST3 | Count of follow-ups due |
| ST4 | Stats come from a single aggregate query using `COUNT(*)` with `FILTER`/`CASE`, not computed on the client |

## 5. Non-Functional Requirements

- **Performance:** API under 200 ms for typical data; indexes on `status`, `company_id`, `last_activity_at`
- **Validation:** Pydantic on the server, Zod on the client
- **Accessibility:** drag and drop has a keyboard alternative (dnd-kit keyboard sensor + "Move to" menu), labelled inputs, WCAG AA contrast, status never shown by color alone
- **Responsive:** 360 px to desktop; on mobile the board becomes horizontally scrollable columns with snap, or a tabbed view
- **Reliability:** consistent error format, loading, empty and error states everywhere
- **Code quality:** TypeScript and Python type hints, linted, conventional commits

## 6. Data Model (SQL)

```sql
CREATE TABLE companies (
  id         INTEGER PRIMARY KEY,
  name       TEXT NOT NULL UNIQUE COLLATE NOCASE,
  website    TEXT,
  location   TEXT,
  industry   TEXT,
  created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE applications (
  id               INTEGER PRIMARY KEY,
  company_id       INTEGER NOT NULL REFERENCES companies(id),
  job_title        TEXT NOT NULL CHECK (length(job_title) BETWEEN 1 AND 120),
  status           TEXT NOT NULL DEFAULT 'applied'
                   CHECK (status IN ('applied','interview','offer','rejected')),
  applied_date     DATE NOT NULL,
  job_url          TEXT,
  location         TEXT,
  work_mode        TEXT CHECK (work_mode IN ('onsite','hybrid','remote')),
  salary_min       INTEGER,
  salary_max       INTEGER,
  source           TEXT,
  last_activity_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  snoozed_until    DATE,
  created_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CHECK (salary_min IS NULL OR salary_max IS NULL OR salary_min <= salary_max)
);
CREATE INDEX idx_apps_status   ON applications(status);
CREATE INDEX idx_apps_company  ON applications(company_id);
CREATE INDEX idx_apps_activity ON applications(last_activity_at);

CREATE TABLE notes (
  id             INTEGER PRIMARY KEY,
  application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  content        TEXT NOT NULL CHECK (length(content) BETWEEN 1 AND 2000),
  created_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX idx_notes_app ON notes(application_id);

CREATE TABLE status_history (
  id             INTEGER PRIMARY KEY,
  application_id INTEGER NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
  from_status    TEXT,
  to_status      TEXT NOT NULL,
  changed_at     TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
```

### Key queries

**Applications with company details (JOIN):**
```sql
SELECT a.id, a.job_title, a.status, a.applied_date, a.location, a.work_mode,
       a.last_activity_at, c.id AS company_id, c.name AS company_name,
       c.website, c.industry,
       (SELECT COUNT(*) FROM notes n WHERE n.application_id = a.id) AS note_count
FROM applications a
JOIN companies c ON c.id = a.company_id
WHERE (:q IS NULL OR a.job_title LIKE '%' || :q || '%'
                  OR c.name      LIKE '%' || :q || '%'
                  OR a.location  LIKE '%' || :q || '%')
  AND (:status IS NULL OR a.status IN (:statuses))
ORDER BY a.updated_at DESC;
```

**Follow-ups due:**
```sql
SELECT a.id, a.job_title, c.name AS company_name,
       CAST(julianday('now') - julianday(a.last_activity_at) AS INTEGER) AS days_waiting
FROM applications a
JOIN companies c ON c.id = a.company_id
WHERE a.status = 'applied'
  AND a.last_activity_at <= datetime('now', '-7 days')
  AND (a.snoozed_until IS NULL OR a.snoozed_until <= date('now'))
ORDER BY a.last_activity_at ASC;
```

**Quick stats (COUNT):**
```sql
SELECT COUNT(*)                                         AS total,
       COUNT(*) FILTER (WHERE status = 'applied')       AS applied,
       COUNT(*) FILTER (WHERE status = 'interview')     AS interviews,
       COUNT(*) FILTER (WHERE status = 'offer')         AS offers,
       COUNT(*) FILTER (WHERE status = 'rejected')      AS rejected
FROM applications;
```
(SQLite 3.30+ supports `FILTER`; otherwise use `SUM(CASE WHEN ... THEN 1 ELSE 0 END)`.)

## 7. API Specification (FastAPI)

Base path: `/api/v1`. JSON only. Errors: `{ "detail": "message" }`.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/applications` | List with `q`, `status` (repeatable), `work_mode`, `source`, `needs_follow_up`, returns joined company data |
| POST | `/applications` | Create (accepts `company_id` or a new `company` object) |
| GET | `/applications/{id}` | Detail with company, notes and status history |
| PUT | `/applications/{id}` | Update fields |
| PATCH | `/applications/{id}/status` | Move stage `{ "status": "interview" }`, writes status history |
| DELETE | `/applications/{id}` | Delete (204) |
| GET | `/applications/{id}/notes` | List notes |
| POST | `/applications/{id}/notes` | Add note |
| PUT | `/notes/{id}` | Edit note |
| DELETE | `/notes/{id}` | Delete note |
| GET | `/companies` | List with application counts, optional `q` |
| POST | `/companies` | Create |
| PUT | `/companies/{id}` | Update |
| DELETE | `/companies/{id}` | Delete (409 if it has applications) |
| GET | `/follow-ups` | Applications needing follow-up |
| POST | `/follow-ups/{id}/done` | Mark followed up (auto note, resets timer) |
| POST | `/follow-ups/{id}/snooze` | Snooze `{ "days": 3 }` |
| GET | `/stats` | COUNT-based stats, accepts the same filters as the list |
| GET | `/health` | Health check |

## 8. UI / UX Design

### Design language
- Shadcn/UI on Tailwind, neutral base with a single accent (violet or blue); Inter font; rounded-xl cards, subtle borders and shadows; 8 px spacing grid
- Stage colors with icons: Applied (blue, Send), Interview (violet, CalendarClock), Offer (green, PartyPopper/Trophy), Rejected (gray-red, XCircle)
- Dark mode toggle, persisted

### Pages
1. **Board** (`/`): stats row, search and filter bar, reminders banner/panel, 4-column Kanban board, "Add application" button
2. **Companies** (`/companies`): table or cards with counts, add/edit/delete
3. **Application drawer** (Shadcn `Sheet`): details, stage selector, edit button, notes timeline, status history, follow-up actions

### Shadcn components
`button, card, input, label, select, dialog, alert-dialog, sheet, badge, textarea, form, popover, calendar, command (company combobox), dropdown-menu, tabs, skeleton, sonner, tooltip, separator, scroll-area, toggle-group, avatar`

### Interaction details
- dnd-kit for drag and drop with pointer + keyboard sensors and a drag overlay
- Optimistic updates with rollback
- Company combobox: search existing, "Create 'X'" option
- Skeletons while loading, empty states with call to action, error states with retry

## 9. Tech Architecture

```
job-tracker/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py          # FOLLOW_UP_DAYS, DATABASE_URL, CORS origins
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── crud.py
│   │   ├── seed.py
│   │   └── routers/ (applications.py, companies.py, notes.py, followups.py, stats.py)
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── components/ (ui/, board/, applications/, companies/, notes/, layout/)
│       ├── pages/
│       ├── hooks/ (TanStack Query hooks)
│       ├── lib/ (api.ts, schemas.ts, utils.ts, constants.ts)
│       └── App.tsx
├── README.md
└── .gitignore
```

**Libraries:** SQLAlchemy 2.x, Pydantic v2, Uvicorn, pytest, httpx | React 18, Vite, TypeScript, React Router, TanStack Query, React Hook Form, Zod, @dnd-kit/core, @dnd-kit/sortable, date-fns, lucide-react, sonner

## 10. Milestones

| # | Milestone | Done when |
|---|-----------|-----------|
| M1 | Setup and repo | Both apps run locally, Git initialised |
| M2 | Database and models | 4 tables with relations and seed data |
| M3 | Companies and applications API | CRUD, JOIN list, search and filters |
| M4 | Status, notes, follow-ups, stats | Stage moves with history, notes, reminders, COUNT stats |
| M5 | Frontend shell | Layout, routing, theme, API client |
| M6 | Board UI | Columns, cards, drag and drop with optimistic updates |
| M7 | Forms and drawer | Add/edit application, company combobox, notes timeline |
| M8 | Search, filters, reminders, stats UI | All wired to the API |
| M9 | Polish and tests | Responsive, accessibility, tests green |
| M10 | Docs and ship | README with screenshots, deployed |

## 11. Acceptance Criteria

- [ ] Applications can be created, edited, deleted and moved between all four stages by drag and drop and via the menu
- [ ] The board shows each application with its company details (from a SQL JOIN)
- [ ] Notes can be added, edited and deleted, and appear on the application
- [ ] Search and status filters work and combine correctly
- [ ] An Applied application with no activity for 7 days appears in follow-ups with an amber badge; marking it followed up or snoozing removes it
- [ ] Stats show correct totals for applications, interviews and offers, matching the board
- [ ] Failed drag updates roll back with an error toast
- [ ] Invalid input is rejected with clear messages on both client and server
- [ ] Works on mobile width and in dark mode
- [ ] Backend tests pass; README lets a new developer run the app in under 5 minutes

## 12. Risks and Mitigations

| Risk | Mitigation |
|------|------------|
| Drag and drop not usable on touch/keyboard | dnd-kit touch + keyboard sensors and a "Move to" menu |
| Stats disagree with board when filtered | One shared filter model used by both endpoints |
| Follow-up logic edge cases (timezones, snooze) | Store UTC timestamps; test with frozen time |
| Duplicate companies ("Google" vs "google") | Case-insensitive unique constraint and combobox that suggests existing matches |
| Scope creep | Keep v1 fixed; log ideas under Future |

## 13. Future Ideas (v2)

Auth, interview scheduling and calendar export, resume versions per application, email reminders, CSV export, analytics charts (applications per week, funnel), custom stages, contacts per company.
