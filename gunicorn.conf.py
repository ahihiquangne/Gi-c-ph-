# gunicorn.conf.py
workers = 1
worker_class = "sync"
timeout = 180          # Cho worker sống tối đa 180 giây (đủ để ScraperAPI render JS)
keepalive = 5
loglevel = "warning"
accesslog = "-"
errorlog = "-"
