#!/bin/bash
sudo docker build -t exporter .
sudo docker tag exporter jdtotow/exporter:latest
sudo docker push jdtotow/exporter:latest
