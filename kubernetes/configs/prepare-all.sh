#!/bin/bash

# create pv
kubectl apply -f deployment/prometheus-config-volume.yaml 
kubectl apply -f deployment/prometheus-tsdb-volume.yaml 
kubectl apply -f deployment/mongodb-volume.yaml 

#create pvc
kubectl apply -f deployment/prometheus-config-volume-claim.yaml 
kubectl apply -f deployment/prometheus-tsdb-volume-claim.yaml 
kubectl apply -f deployment/mongodb-volume-claim.yaml

kubectl create configmap configmap-prometheus --from-file=../../prometheus/prometheus.yml
kubectl create configmap configmap-manager --from-file=../../manager/config.json
kubectl create configmap configmap-qos --from-file=../../qos/config/config.json 
kubectl create configmap configmap-pdp --from-file=../../pdp/config/config.json 