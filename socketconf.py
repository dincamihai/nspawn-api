bind="unix:/var/run/gunicorn.sock"
timeout=600
reload=True
loglevel="info"
accesslog = "-"
errorlog="-"
enable_stdio_inheritance=True
