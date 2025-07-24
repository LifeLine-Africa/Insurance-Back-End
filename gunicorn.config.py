"""
Gunicorn configuration for LifeLine Africa Insurance API
Production-ready WSGI server configuration
"""

import os
import multiprocessing

# Server socket
bind = os.getenv('GUNICORN_BIND', '0.0.0.0:5000')
backlog = 2048

# Worker processes
workers = int(os.getenv('GUNICORN_WORKERS', multiprocessing.cpu_count() * 2 + 1))
worker_class = 'gevent'
worker_connections = 1000
max_requests = 1000
max_requests_jitter = 50

# Timeout settings
timeout = int(os.getenv('GUNICORN_TIMEOUT', 30))
keepalive = 2
graceful_timeout = 30

# Security
limit_request_line = 4094
limit_request_fields = 100
limit_request_field_size = 8190

# Logging
accesslog = 'logs/access.log'
errorlog = 'logs/error.log'
loglevel = os.getenv('LOG_LEVEL', 'info').lower()
access_log_format = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(D)s'

# Process naming
proc_name = 'insurance_api'

# Server mechanics
daemon = False
pidfile = '/tmp/insurance_api.pid'
user = None
group = None
tmp_upload_dir = None

# SSL (if using HTTPS termination at application level)
# keyfile = '/path/to/private.key'
# certfile = '/path/to/certificate.crt'

# Preload application for better performance
preload_app = True

# Enable automatic worker restarts
max_requests = 1000
max_requests_jitter = 100

def when_ready(server):
    """Called just after the server is started."""
    server.log.info("LifeLine Africa Insurance API server is ready. Listening on: %s", server.address)

def worker_int(worker):
    """Called just after a worker has been killed by SIGINT or SIGQUIT."""
    worker.log.info("Worker %s killed by signal", worker.pid)

def pre_fork(server, worker):
    """Called just before a worker is forked."""
    server.log.info("Worker %s spawned", worker.pid)

def post_fork(server, worker):
    """Called just after a worker has been forked."""
    server.log.info("Worker %s initialized", worker.pid)

def worker_abort(worker):
    """Called when a worker receives the SIGABRT signal."""
    worker.log.info("Worker %s aborted", worker.pid)