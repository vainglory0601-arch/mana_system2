# config/gunicorn.conf.py
import multiprocessing
import os

# Worker configuration
workers = 2
threads = 4
worker_class = "gthread"

# Timeout settings - INCREASED for image processing
timeout = 120  # ពី 30 មក 120 វិនាទី
graceful_timeout = 120
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