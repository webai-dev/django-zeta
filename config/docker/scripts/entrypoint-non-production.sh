#!/bin/bash
set -e
cmd="$@"

# This entrypoint is used to play nicely with the current cookiecutter configuration.
# Since docker-compose relies heavily on environment variables itself for configuration, we'd have to define multiple
# environment variables just to support cookiecutter out of the box. That makes no sense, so this little entrypoint
# does all this for us.
export REDIS_URL=redis://redis:6379

export CELERY_BROKER_URL=$REDIS_URL/0

function postgres_ready(){
python << END
import sys
import psycopg2
try:
    conn = psycopg2.connect(dbname="$DATABASE_USER", user="$DATABASE_USER", password="$DATABASE_PASSWORD", host="postgres")
except psycopg2.OperationalError:
    sys.exit(-1)
sys.exit(0)
END
}

until postgres_ready; do
  >&2 echo "Postgres is unavailable - sleeping"
  sleep 1
done

>&2 echo "Postgres is up - continuing..."

echo "Setting up credentials"
echo $GOOGLE_APPLICATION_CREDENTIALS_STRING > /tmp/credentials.json

exec $cmd
