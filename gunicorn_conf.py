import multiprocessing
import os

# 2 * CPU + 1 is a common baseline for async workers.
workers = (multiprocessing.cpu_count() * 2) + 1
worker_class = "uvicorn.workers.UvicornWorker"
bind = f"0.0.0.0:{os.getenv('PORT', '8000')}"
timeout = 60
graceful_timeout = 30
keepalive = 5
accesslog = "-"
errorlog = "-"
loglevel = os.getenv("LOG_LEVEL", "info")
