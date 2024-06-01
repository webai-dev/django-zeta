#!/bin/sh

DJANGO_SETTINGS_MODULE=config.settings.backend.test coverage run manage.py test --noinput && coverage report
