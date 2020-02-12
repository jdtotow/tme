#!/bin/bash
sudo docker build -t pdp . 
sudo docker tag pdp jdtotow/pdp:latest
sudo docker push jdtotow/pdp:latest
