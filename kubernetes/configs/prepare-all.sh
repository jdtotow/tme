#!/bin/bash

# create pv
kubectl apply -f deployment/prometheus-volume.yaml 
kubectl apply -f deployment/mongodb-volume.yaml 
kubectl apply -f deployment/prometheus-config-volume.yaml 
kubectl apply -f deployment/sidecar-volume-prometheus.yaml 
kubectl apply -f deployment/minio-volume.yaml 
kubectl apply -f deployment/prometheus-ks8-volume.yaml 
kubectl apply -f deployment/volume-manager.yaml 
kubectl apply -f deployment/volume-pdp.yaml 

#create pvc
kubectl apply -f deployment/prometheus-config-volume-claim.yaml 
kubectl apply -f deployment/prometheus-tsdb-volume-claim.yaml 
kubectl apply -f deployment/mongodb-volume-claim.yaml
kubectl apply -f deployment/sidecar-volume-prometheus-claim.yaml
kubectl apply -f deployment/minio-volume-claim.yaml 
kubectl apply -f deployment/prometheus-ks8-volume-claim.yaml 
kubectl apply -f deployment/volume-manager-claim.yaml 
kubectl apply -f deployment/volume-pdp-claim.yaml 

kubectl create configmap configmap-prometheus --from-file=../../prometheus/prometheus-k8s.yml
kubectl create configmap configmap-bucket --from-file=../../thanos/thanos/bucket_config.yaml 
kubectl create configmap prometheus-cluster --from-file=../../cluster/prometheus/prometheus.yml 
kubectl create configmap configmap-logstash --from-file=../../logstash/logstash-2.conf 
#sleep 5
#kubectl apply -f deployment/mongodb.yaml 
#kubectl apply -f deployment/minio.yaml 
#kubectl apply -f deployment/rabbitmq.yaml 
#kubectl apply -f deployment/prometheus.yaml 
#sleep 20
#kubectl apply -f deployment/sidecar.yaml
#sleep 30
#kubectl apply -f deployment/querier.yaml 
#kubectl apply -f deployment/compactor.yaml 
#kubectl apply -f deployment/gateway.yaml 
#sleep 20  
#kubectl apply -f deployment/prometheusbeat.yaml 
#kubectl apply -f deployment/manager.yaml 
#sleep 30
#kubectl apply -f deployment/exporter.yaml 
#kubectl apply -f deployment/qos.yaml 
#kubectl apply -f deployment/pdp.yml 
#kubectl apply -f deployment/grafana.yaml
#kubectl apply -f deployment/ml.yaml 