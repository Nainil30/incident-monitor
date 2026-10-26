# Incident Monitor

A small full-stack **incident monitoring dashboard** for software engineering teams. It shows active production incidents, lets on-call engineers dig into logs and event timelines, suggests likely root causes using deterministic rules, and supports the **acknowledge → resolve** workflow.

Built with a **React** frontend and a **Python FastAPI** backend. All data is synthetic and kept in memory, so there are no API keys, no database and no external services. It runs entirely on your machine.

---

## Features

| # | Feature | Where |
|---|---------|-------|
| 1 | **Dashboard**: summary cards (open, acknowledged, resolved, active SEV1) and a table of incidents with severity, affected services, status and age. Filter by status and severity. | `frontend/src/App.jsx` |
| 2 | **Incident details**: description, colour-coded logs and an event timeline. | `GET /api/incidents/{id}` |
| 3 | **Root-cause suggestions ("AI-style")**: a keyword rule engine scans titles and logs and returns ranked causes with confidence, evidence and a recommended action. | `backend/rca.py` |
| 4 | **Acknowledge and resolve**: status changes are validated by the backend and recorded on the timeline. | `POST /api/incidents/{id}/acknowledge`, `/resolve` |
| 5 | **Automated tests**: 16 pytest tests cover the API, the status rules and the root-cause engine. | `backend/tests/test_api.py` |

---

## Architecture

```
┌──────────────────────────┐    /api/*  (Vite proxy)   ┌──────────────────────────────┐
│  React + Vite  (:5173)   │ ────────────────────────▶ │  FastAPI + Uvicorn  (:8000)  │
│                          │                           │                              │
│  SummaryCards            │ ◀──────── JSON ────────── │  main.py    routes + rules   │
│  IncidentTable + filters │                           │  models.py  Pydantic schemas │
│  IncidentDetail          │                           │  data.py    synthetic seed   │
│   ├ Ack / Resolve        │                           │  rca.py     root-cause rules │
│   ├ Root-cause cards     │                           │  store      in-memory dict   │
│   ├ Timeline             │                           │                              │
│   └ Logs                 │                           │                              │
└──────────────────────────┘                           └──────────────────────────────┘
```

**Design decisions (kept deliberately simple):**

- **In-memory store.** At startup the backend builds 8 realistic incidents in a Python `dict`. Restarting the server resets them. This removes any need for a database or migrations.
- **Vite dev proxy instead of CORS.** The browser only talks to `localhost:5173`, and Vite forwards `/api/*` to FastAPI, so no CORS configuration is needed.
- **Pydantic models** define the API contract (`Incident`, `LogEntry`, `TimelineEvent`, `Suggestion`), and FastAPI validates and serialises responses with them.
- **Deterministic "AI".** The root-cause engine is a list of rules, not an LLM. The same input always gives the same output, which makes it explainable and testable.
- **No frontend libraries** beyond React. Plain `fetch`, `useState` and `useEffect`, and hand-written CSS.

### Incident status rules

```
 open ──acknowledge──▶ acknowledged ──resolve──▶ resolved
   └────────────────────resolve─────────────────────┘
```

Any other status change (for example acknowledging a resolved incident, or resolving twice) returns **HTTP 409 Conflict**. Unknown incident IDs return **HTTP 404**. Every successful change adds an event to the incident's timeline.

### How the root-cause engine works (`backend/rca.py`)

1. Builds a list of text from the incident's title, description and every log message.
2. For each rule (for example *"Memory leak"* with keywords `outofmemory`, `oomkilled`, `heap`, `exit code 137`), collects every line that contains a keyword. Those lines become the **evidence**.
3. Confidence is `base_confidence + 0.1 × (extra evidence lines)`, capped at **0.95**, so more supporting evidence means higher confidence.
4. Results are sorted by confidence. If nothing matches, a fallback suggestion tells the engineer to investigate manually.

The current rules cover memory leaks, DB connection pool exhaustion, slow queries, bad deployments, expired TLS certificates, downstream failures, rate limiting, full disks, queue backlogs and cache problems.

---

## API reference

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET`  | `/api/incidents?status=&severity=` | List incidents (active first, then by severity, then newest) |
| `GET`  | `/api/incidents/{id}` | Full incident, including logs and timeline |
| `GET`  | `/api/incidents/{id}/suggestions` | Ranked root-cause suggestions |
| `POST` | `/api/incidents/{id}/acknowledge` | `open` → `acknowledged` |
| `POST` | `/api/incidents/{id}/resolve` | `open` / `acknowledged` → `resolved` |
| `GET`  | `/api/stats` | Counts by status, and active incidents by severity |

Interactive API docs (Swagger UI) are generated automatically at **http://localhost:8000/docs** while the backend is running.

---

## Project structure

```
.
├── backend/
│   ├── main.py            # FastAPI app, routes, status rules, stats
│   ├── models.py          # Pydantic models / API schema
│   ├── data.py            # Synthetic incident seed data
│   ├── rca.py             # Deterministic root-cause rule engine
│   ├── requirements.txt
│   └── tests/
│       └── test_api.py    # 16 pytest tests
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js     # dev server + /api proxy
│   └── src/
│       ├── main.jsx       # React entry point
│       ├── App.jsx        # Dashboard, table, detail panel
│       ├── api.js         # Small fetch wrapper
│       └── styles.css     # Dark theme styling
└── .claude/launch.json    # Dev server config used by Claude Code's preview
```

---

## Getting started

**Prerequisites:** Python 3.10+ and Node.js 18+.

### 1. Backend

```bash
cd backend
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Frontend (in a second terminal)

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:5173**.

### 3. Run the tests

```bash
cd backend
python -m pytest -q
```

Expected output: `16 passed`.

---

## Test coverage

| Area | What is verified |
|------|------------------|
| Listing | All seeded incidents returned; sort order; status and severity filters |
| Details | Logs and timeline are present; unknown ID → 404 |
| Status changes | Acknowledge, resolve from acknowledged, resolve directly from open; timeline events appended |
| Rejected changes | Acknowledge twice, acknowledge resolved, resolve twice → 409 |
| Stats | Counts update after a status change |
| Root-cause engine | Correct top cause for 4 different incidents; repeatable output; fallback when no rule matches |

A pytest fixture resets the in-memory store before every test, so tests are isolated and can run in any order.

---

## Possible next steps

- Store incidents in SQLite or Postgres so they survive restarts
- Live updates via WebSockets or Server-Sent Events
- Users and assignment (who acknowledged or resolved)
- Replace or extend the rule engine with an LLM, keeping the rules as an explainable baseline
- Frontend tests (Vitest + React Testing Library) and CI with GitHub Actions
- Docker Compose for one-command startup
