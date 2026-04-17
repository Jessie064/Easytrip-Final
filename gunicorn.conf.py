# Gunicorn config for Render free tier (512MB RAM)
workers = 1          # only 1 worker to save memory
threads = 2          # use threads instead of multiple workers
worker_class = 'gthread'
timeout = 120        # allow 120 seconds for long AI requests
keepalive = 5
max_requests = 1000
max_requests_jitter = 100