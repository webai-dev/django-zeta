#!/bin/sh

gcloud config set container/new_scopes_behavior true
gcloud container node-pools create node-pool-1 --cluster=ery --machine-type=n1-standard-1 --num-nodes=3 --preemptible --zone=us-east4-b --scopes=storage-rw,trace,monitoring-write,logging-write,devstorage.read_only,pubsub

