-- Support ticketing schema for Lakebase (Postgres)
-- Run once (ensure_schema() in app.py also runs this automatically on startup).

CREATE TABLE IF NOT EXISTS tickets (
    ticket_id   SERIAL PRIMARY KEY,
    title       TEXT NOT NULL,
    status      TEXT NOT NULL DEFAULT 'open'
                CHECK (status IN ('open', 'in_progress', 'resolved', 'closed')),
    created_by  TEXT NOT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS ticket_messages (
    message_id    SERIAL PRIMARY KEY,
    ticket_id     INTEGER NOT NULL REFERENCES tickets(ticket_id) ON DELETE CASCADE,
    message_text  TEXT NOT NULL,
    author        TEXT NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_ticket_messages_ticket_id
    ON ticket_messages (ticket_id);

CREATE INDEX IF NOT EXISTS idx_tickets_status
    ON tickets (status);

-- Optional: enable Lakebase Change Data Feed later with:
-- ALTER TABLE tickets REPLICA IDENTITY FULL;
-- ALTER TABLE ticket_messages REPLICA IDENTITY FULL;
