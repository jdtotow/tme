#!/bin/bash

# create pv
kubectl apply -f deployment/prometheus-volume.yaml 
kubectl apply -f deployment/mongodb-volume.yaml 
kubectl apply -f deployment/prometheus-config-volume.yaml 
kubectl apply -f deployment/sidecar-volume-prometheus.yaml 
kubectl apply -f deployment/minio-volume.yaml 

#create pvc
kubectl apply -f deployment/prometheus-config-volume-claim.yaml 
kubectl apply -f deployment/prometheus-tsdb-volume-claim.yaml 
kubectl apply -f deployment/mongodb-volume-claim.yaml
kubectl apply -f deployment/sidecar-volume-prometheus-claim.yaml
kubectl apply -f deployment/minio-volume-claim.yaml 

kubectl create configmap configmap-prometheus --from-file=../../prometheus/prometheus.yml
kubectl create configmap configmap-manager --from-file=../../manager/config.json
kubectl create configmap configmap-qos --from-file=../../qos/config/config.json 
kubectl create configmap configmap-pdp --from-file=../../pdp/config/config.json 
kubectl create configmap configmap-bucket --from-file=../../thanos/thanos/bucket_config.yaml 
#sleep 20
#kubectl apply -f deployment/prometheus.yml 
#kubectl apply -f deployment/grafana.yml 
#kubectl apply -f deployment/prometheusbeat.yml 
#kubectl apply -f deployment/manager.yml 
#kubectl apply -f deployment/exporter.yml 
#kubectl apply -f deployment/mongodb.yml 
#kubectl apply -f deployment/qos.yml 
#kubectl apply -f deployment/pdp.yml 