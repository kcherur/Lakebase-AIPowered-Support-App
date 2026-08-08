"""
Internal Support Ticket System
--------------------------------
A small Flask app backed by Lakebase (Databricks-managed Postgres) that lets
users:
  - view all support tickets
  - select a ticket and view its messages
  - create a new ticket
  - add a message to an existing ticket
  - update a ticket's status

All operational data (tickets, ticket_messages) lives in Lakebase — see
schema.sql for the DDL. lakebase.py handles the connection (single
LAKEBASE_URL secret, native Postgres role, static password).
"""

import os

from flask import Flask, redirect, render_template, request, url_for

from lakebase import run_query, run_write

app = Flask(__name__)

VALID_STATUSES = ["open", "in_progress", "resolved", "closed"]

SCHEMA_SQL = """
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

CREATE INDEX IF NOT EXISTS idx_ticket_messages_ticket_id ON ticket_messages (ticket_id);
CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets (status);
"""


def ensure_schema() -> None:
    """Create the tickets / ticket_messages tables if they don't exist yet."""
    run_write(SCHEMA_SQL)


@app.route("/")
def list_tickets():
    """View all support tickets, most recent first, with a message count."""
    status_filter = request.args.get("status", "")
    if status_filter and status_filter in VALID_STATUSES:
        tickets = run_query(
            """
            SELECT t.*, COUNT(m.message_id) AS message_count
            FROM tickets t
            LEFT JOIN ticket_messages m ON m.ticket_id = t.ticket_id
            WHERE t.status = %s
            GROUP BY t.ticket_id
            ORDER BY t.created_at DESC
            """,
            (status_filter,),
        )
    else:
        tickets = run_query(
            """
            SELECT t.*, COUNT(m.message_id) AS message_count
            FROM tickets t
            LEFT JOIN ticket_messages m ON m.ticket_id = t.ticket_id
            GROUP BY t.ticket_id
            ORDER BY t.created_at DESC
            """
        )
    return render_template(
        "index.html",
        tickets=tickets,
        statuses=VALID_STATUSES,
        status_filter=status_filter,
    )


@app.route("/tickets", methods=["POST"])
def create_ticket():
    """Create a new ticket."""
    title = request.form.get("title", "").strip()
    created_by = request.form.get("created_by", "").strip()

    if not title or not created_by:
        return redirect(url_for("list_tickets"))

    run_write(
        "INSERT INTO tickets (title, created_by) VALUES (%s, %s)",
        (title, created_by),
    )
    # Redirect back to the main list after creating
    return redirect(url_for("list_tickets"))


@app.route("/tickets/<int:ticket_id>")
def view_ticket(ticket_id):
    """View a single ticket and all of its messages."""
    tickets = run_query("SELECT * FROM tickets WHERE ticket_id = %s", (ticket_id,))
    if not tickets:
        return redirect(url_for("list_tickets"))
    ticket = tickets[0]

    messages = run_query(
        """
        SELECT * FROM ticket_messages
        WHERE ticket_id = %s
        ORDER BY created_at ASC
        """,
        (ticket_id,),
    )
    return render_template(
        "ticket.html", ticket=ticket, messages=messages, statuses=VALID_STATUSES
    )


@app.route("/tickets/<int:ticket_id>/messages", methods=["POST"])
def add_message(ticket_id):
    """Add a message to an existing ticket."""
    message_text = request.form.get("message_text", "").strip()
    author = request.form.get("author", "").strip()

    if message_text and author:
        run_write(
            """
            INSERT INTO ticket_messages (ticket_id, message_text, author)
            VALUES (%s, %s, %s)
            """,
            (ticket_id, message_text, author),
        )
    return redirect(url_for("view_ticket", ticket_id=ticket_id))


@app.route("/tickets/<int:ticket_id>/status", methods=["POST"])
def update_status(ticket_id):
    """Update a ticket's status."""
    new_status = request.form.get("status", "")
    if new_status in VALID_STATUSES:
        run_write(
            "UPDATE tickets SET status = %s WHERE ticket_id = %s",
            (new_status, ticket_id),
        )
    # Redirect back to the main list after updating status
    return redirect(url_for("list_tickets"))


@app.route("/healthz")
def healthz():
    return {"status": "ok"}


if __name__ == "__main__":
    ensure_schema()
    port = int(os.environ.get("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=True)
