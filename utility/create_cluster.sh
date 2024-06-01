 gcloud container clusters create ery \
	 --zone=us-east4-b \
	 --num-nodes=3 \
	 --addons=HttpLoadBalancing,KubernetesDashboard \
	 --enable-autorepair \
	 --enable-autoupgrade \
	 --enable-cloud-logging \
	 --enable-cloud-monitoring \
	 --preemptible \
	 --scopes=gke-default,storage-rw

