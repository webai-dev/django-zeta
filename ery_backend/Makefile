DJANGO_SETTINGS_MODULE?=config.settings.backend.local
WHOAMI?=$(shell whoami)
PYTHON?=python
PSQL?=sudo -u postgres psql
MANAGE=$(PYTHON) ../manage.py
PRIMARY_SITE?=localhost
DATABASE_NAME=ery

all: setup-migrations

reset-migrations:
	rm -Rf */migrations
	for app in `ls`; do \
		if [ -f $$app/apps.py ]; then \
			mkdir $$app/migrations; \
			touch $$app/migrations/__init__.py; \
		fi \
	done

reset-postgres:
	echo "\
		DROP DATABASE IF EXISTS $(DATABASE_NAME); \
		DROP DATABASE IF EXISTS test_$(DATABASE_NAME); \
		CREATE DATABASE $(DATABASE_NAME); \
		CREATE DATABASE test_$(DATABASE_NAME); \
		CREATE USER $(WHOAMI); \
		GRANT ALL PRIVILEGES ON DATABASE $(DATABASE_NAME) TO $(WHOAMI); \
		GRANT ALL PRIVILEGES ON DATABASE test_$(DATABASE_NAME) TO $(WHOAMI); \
		ALTER DATABASE $(DATABASE_NAME) OWNER TO $(WHOAMI); \
		ALTER DATABASE test_$(DATABASE_NAME) OWNER TO $(WHOAMI); \
		ALTER USER $(WHOAMI) CREATEDB;" | $(PSQL)


delete-test-postgres:
	echo "\
        	DROP DATABASE IF EXISTS test_$(DATABASE_NAME); \
        	" | $(PSQL)

reset-test-postgres: delete-test-postgres
	echo "\
		CREATE DATABASE test_$(DATABASE_NAME); \
		GRANT ALL PRIVILEGES ON DATABASE test_$(DATABASE_NAME) TO $(WHOAMI);" | $(PSQL)

make-migrations:
	$(MANAGE) makemigrations

setup-migrations:
	$(MANAGE) migrate

setup-site:
	# Changes domain name of first Site object
	echo "from django.contrib.sites.models import Site; Site.objects.update(domain='$(PRIMARY_SITE)')" | $(MANAGE) shell

setup-locales:
	$(MANAGE) loaddata languages_data.json.gz
	$(MANAGE) loaddata countries_data.json.gz

setup-rbac:
	$(MANAGE) loaddata roles_privileges.json

setup-required-backend-fixtures:
	$(MANAGE) runscript import_bxmls --script-args "../fixtures/bxmls"

reset: reset-postgres setup
setup: setup-migrations setup-locales setup-rbac setup-site setup-required-backend-fixtures
setup-test: reset-postgres setup-migrations setup-locales setup-rbac setup-required-backend-fixtures

full-jdorsett: reset-migrations reset-postgres make-migrations setup
