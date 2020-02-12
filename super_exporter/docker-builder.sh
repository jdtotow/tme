#!/bin/bash
sudo docker build -t super_exporter .
sudo docker tag manager jdtotow/super_exporter:latest
sudo docker push jdtotow/super_exporter:latest
