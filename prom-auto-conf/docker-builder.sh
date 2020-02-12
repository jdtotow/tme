#!/bin/bash
sudo docker build -t prom-auto-conf . 
sudo docker tag pdp jdtotow/prom-auto-conf:latest
sudo docker push jdtotow/prom-auto-conf:latest
