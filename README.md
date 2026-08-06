# Internal Support Ticket App

A minimal Databricks App (Flask + Lakebase) for tracking support tickets and
their message threads.

## What it does

- **View all tickets** — list view with status filter and message counts
- **View a ticket's messages** — full conversation thread for one ticket
- **Create a new ticket**
- **Add a message** to an existing ticket
- **Update a ticket's status** (`open`, `in_progress`, `resolved`, `closed`)

## Files

- `app.py` — Flask app with all routes; also creates the schema on startup
  (`ensure_schema()`) so there's no separate migration step
- `lakebase.py` — Lakebase connection helper (single `LAKEBASE_URL` secret,
  psycopg2 + SQLAlchemy) — unchanged from the reference boilerplate
- `schema.sql` — the same DDL as `ensure_schema()`, for running by hand via
  a SQL editor / `psql` if you'd rather not rely on app startup
- `templates/` — `index.html` (ticket list + create form), `ticket.html`
  (thread + add-message/update-status forms), `base.html` (shared layout)
- `setup_secrets.py` — one-time script to store the Lakebase URL as a
  Databricks secret
- `app.yaml` — Databricks Apps deployment config
- `.env.example` — local dev template

## Schema

```sql
tickets
  ticket_id    SERIAL PRIMARY KEY
  title        TEXT NOT NULL
  status       TEXT NOT NULL DEFAULT 'open'   -- open | in_progress | resolved | closed
  created_by   TEXT NOT NULL
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()

ticket_messages
  message_id     SERIAL PRIMARY KEY
  ticket_id      INTEGER NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE
  message_text   TEXT NOT NULL
  author         TEXT NOT NULL
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
```

`ticket_messages.ticket_id` is a foreign key into `tickets.ticket_id`, with
`ON DELETE CASCADE` so removing a ticket also removes its messages.

## Setup

### 1. Create a Lakebase instance and a native-password role

Same as the reference boilerplate:

1. Databricks workspace → **Catalog** → **Lakebase** tab → **Create Lakebase
   instance**.
2. Open the instance → **Roles & Databases** → enable **native (password)
   authentication** if needed → **Add role** with **Password** auth.
3. Copy the connection URL:
   `postgresql://<role>:<password>@<host>.database.cloud.databricks.com:5432/databricks_postgres?sslmode=require`

### 2. Store the URL as a secret

From a Databricks notebook or authenticated terminal:

```
python setup_secrets.py
```

This stores the URL (base64-encoded) under the `database/lakebase-url`
secret, which `lakebase.py` reads via `WorkspaceClient`.

### 3. Install dependencies

```
pip install -r requirements.txt
```

### 4. Run locally

Requires a Databricks CLI profile authenticated against the same workspace
(`databricks auth login`), since `lakebase.py` fetches the URL through
`WorkspaceClient` rather than an env var:

```
python app.py
```

Then open `http://localhost:8000`.

### 5. Deploy as a Databricks App

1. Create a **Git folder** in your workspace pointing at this repo.
2. **Compute → Apps → Create app → Custom**, point it at the Git folder.
3. Databricks reads `app.yaml` for the run command and env vars.
4. Click **Deploy**. On first request, `app.py` will call `ensure_schema()`
   and create the tables automatically if they don't already exist.

## Routes

| Method | Path                              | Purpose                       |
|--------|-----------------------------------|--------------------------------|
| GET    | `/`                                | List all tickets (optional `?status=` filter) |
| POST   | `/tickets`                         | Create a new ticket           |
| GET    | `/tickets/<ticket_id>`             | View a ticket and its messages|
| POST   | `/tickets/<ticket_id>/messages`    | Add a message to a ticket     |
| POST   | `/tickets/<ticket_id>/status`      | Update a ticket's status      |
| GET    | `/healthz`                         | Health check                  |
