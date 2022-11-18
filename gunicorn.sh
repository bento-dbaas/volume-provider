#!/bin/sh
gunicorn --bind 0.0.0.0:5020 --worker-class gevent --workers 2 --log-file - volume_provider.app:app
