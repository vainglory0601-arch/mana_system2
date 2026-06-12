# config/gunicorn.conf.py
import multiprocessing
import os

# Worker configuration
# 4 workers × 4 threads = 16 concurrent requests. With only 2 workers
# (the previous setting), a single slow Cloudinary upload could pin
# both workers and stall the entire site.
workers = 4
threads = 4
worker_class = "gthread"

# Timeout settings — request must finish within 60s. Cloudinary
# itself has a 20s timeout (settings.py), so a hung upload will die
# fast and not eat the whole worker budget.
timeout = 60
graceful_timeout = 30
keep_alive = 5

# Memory optimization
max_requests = 500  # កាត់បន្ថយពី 1000 មក 500
max_requests_jitter = 50
preload_app = True

# File upload limits
limit_request_line = 4096
limit_request_fields = 100
limit_request_field_size = 8190

# Logging
accesslog = "-"
errorlog = "-"
loglevel = "info"

def when_ready(server):
    print("Gunicorn is ready!")