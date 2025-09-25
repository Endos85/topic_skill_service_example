#!/usr/bin/env sh
set -e

# Point Flask CLI to the global app object
export FLASK_APP=${FLASK_APP:-"app:app"}

# Wait for Postgres (unchanged)
python - <<'PY'
import os, time, sys
from urllib.parse import urlparse
import psycopg2
url = os.environ.get("DATABASE_URL", "")
if not url:
    print("DATABASE_URL is not set", file=sys.stderr); sys.exit(1)
u = urlparse(url.replace("+psycopg2",""))
for i in range(60):
    try:
        psycopg2.connect(
            dbname=u.path.lstrip('/'),
            user=u.username,
            password=u.password,
            host=u.hostname,
            port=u.port or 5432,
            connect_timeout=3
        ).close()
        print("Postgres is up.")
        break
    except Exception as e:
        print(f"Waiting for Postgres... ({i+1}/60) {e}")
        time.sleep(2)
else:
    print("Postgres did not become ready in time.", file=sys.stderr)
    sys.exit(1)
PY

# Apply migrations (idempotent)
flask db upgrade || flask db stamp head

# Start Gunicorn with the global app
exec gunicorn --bind 0.0.0.0:${PORT:-5000} --workers ${WORKERS:-2} app:app
