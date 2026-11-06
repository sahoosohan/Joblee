#!/bin/sh
set -eu

python -c 'import json, os; open("/app/static/runtime-config.js", "w").write("window.__JOBLEE_CONFIG__ = " + json.dumps({"googleClientId": os.getenv("GOOGLE_CLIENT_ID", "")}) + ";\n")'
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-10000}"
