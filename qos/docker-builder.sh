#!/bin/bash
sudo docker build -t qos . 
sudo docker tag qos jdtotow/qos:latest
sudo docker push jdtotow/qos:latest
