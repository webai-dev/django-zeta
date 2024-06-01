#!/bin/sh -x

GCLOUD_SQL_USER=p744426355021-0c4qtl@gcp-sa-cloud-sql.iam.gserviceaccount.com
GCLOUD_TMP_STORAGE=gs://tmp42

cloudsql_server=ery-production

if [ ! "$1" ]; then
	echo "need file as arg"
	exit
fi

gcloud sql databases delete ery --instance $cloudsql_server
gcloud sql databases create ery --instance $cloudsql_server
gsutil cp $1 $GCLOUD_TMP_STORAGE
gsutil acl ch -u $GCLOUD_SQL_USER:READER $GCLOUD_TMP_STORAGE/$1
gcloud sql import sql $cloudsql_server $GCLOUD_TMP_STORAGE/$1 --database ery --user ery

