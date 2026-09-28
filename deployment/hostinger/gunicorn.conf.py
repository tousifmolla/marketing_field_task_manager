"""Linux production process settings. Keep the proxy upstream private."""
import os
bind = f"{os.environ.get('BIND_HOST', '127.0.0.1')}:{int(os.environ.get('PORT', '8000'))}"
workers = int(os.environ.get("WEB_CONCURRENCY", "1"))
worker_class = "gthread"
threads = 4
timeout = 120
accesslog = "-"
errorlog = "-"
capture_output = True
