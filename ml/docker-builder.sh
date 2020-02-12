#!/bin/bash
sudo docker build -t ml . 
sudo docker tag ml jdtotow/ml:latest
sudo docker push jdtotow/ml:latest
