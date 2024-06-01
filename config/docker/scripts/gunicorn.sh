#!/bin/sh

/usr/local/bin/gunicorn config.wsgi -w 4 -b 0.0.0.0:8000
