#!/bin/bash
sudo docker rmi jdtotow/exporter:latest
sudo docker rmi jdtotow/manager:latest 
sudo docker rmi jdtotow/optimizer:latest
sudo docker rmi jdtotow/prometheusbeat:latest
sudo docker rmi jdtotow/outapi:latest 
sudo docker rmi jdtotow/pdp:latest
sudo docker rmi jdtotow/qos:latest

cd ./exporter
./docker-builder.sh
cd ../manager 
./docker-builder.sh
cd ../optimizer 
./docker-builder.sh
cd ../prometheusbeat
./docker-builder.sh 
cd ../output_api
./docker-builder.sh 
cd ../qos 
./docker-builder.sh 
cd ../pdp 
./docker-builder.sh 