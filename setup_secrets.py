"""
One-time setup: store the Lakebase connection URL as a Databricks secret.

Run this once from a Databricks notebook (%sh python setup_secrets.py) or a
terminal with the Databricks CLI authenticated. It prompts for the Lakebase
connection URL and stores it base64-encoded under the scope/key that
lakebase.py reads from (default: database/lakebase-url).
"""

import base64
import getpass
import os

from databricks.sdk import WorkspaceClient

SCOPE = os.environ.get("LAKEBASE_SECRET_SCOPE", "database")
KEY = os.environ.get("LAKEBASE_SECRET_KEY", "lakebase-url")


def main():
    w = WorkspaceClient()

    existing_scopes = [s.name for s in w.secrets.list_scopes()]
    if SCOPE not in existing_scopes:
        w.secrets.create_scope(scope=SCOPE)
        print(f"Created secret scope: {SCOPE}")

    lakebase_url = getpass.getpass(
        "Paste your Lakebase connection URL "
        "(postgresql://role:password@host:5432/databricks_postgres?sslmode=require): "
    )
    encoded = base64.b64encode(lakebase_url.encode("utf-8")).decode("utf-8")
    w.secrets.put_secret(scope=SCOPE, key=KEY, string_value=encoded)
    print(f"Stored Lakebase URL as secret {SCOPE}/{KEY}")


if __name__ == "__main__":
    main()
