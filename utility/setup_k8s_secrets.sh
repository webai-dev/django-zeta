#!/bin/bash

source .env

kubectl --namespace=staging create secret generic cloudsql-db-credentials --from-literal=username=$CLOUD_SQL_USERNAME --from-literal=password=$CLOUD_SQL_PASSWORD
kubectl --namespace=staging create secret generic cloudsql-instance-credentials --from-file=credentials.json=$CLOUD_SQL_CREDENTIALS
kubectl --namespace=staging create secret generic django-secret-key --from-literal=secret_key=$DJANGO_SECRET_KEY
kubectl --namespace=staging create secret generic facebook --from-literal=id=$FACEBOOK_ID --from-literal=secret=$FACEBOOK_SECRET
kubectl --namespace=staging create secret generic linkedin --from-literal=id=$LINKEDIN_ID --from-literal=secret=$LINKEDIN_SECRET
kubectl --namespace=staging create secret generic smsglobal-credentials --from-literal=smsglobal-apikey=$SMSGLOBAL_APIKEY --from-literal=smsglobal-secret=$SMSGLOBAL_SECRET
kubectl --namespace=staging create secret generic ery-smser-credentials --from-file=credentials.json=$ERY_SMSER_CREDENTIALS
kubectl --namespace=staging create secret generic ery-runner-credentials --from-file=credentials.json=$ERY_RUNNER_CREDENTIALS
