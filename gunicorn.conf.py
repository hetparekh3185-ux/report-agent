import os

# Gunicorn configuration file for Render deployment
# By default Gunicorn kills requests taking > 30 seconds.
# AI report generation (especially 10-20 pages) takes 45-90 seconds,
# so timeout is increased to 180 seconds to avoid 502 WORKER TIMEOUT errors.

timeout = int(os.environ.get("GUNICORN_TIMEOUT", 180))
workers = int(os.environ.get("WEB_CONCURRENCY", 2))
threads = 4
keepalive = 5
capture_output = True
