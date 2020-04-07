#!/bin/bash
sudo docker build -t manager .
sudo docker tag manager jdtotow/manager:latest
sudo docker push jdtotow/manager:latest
