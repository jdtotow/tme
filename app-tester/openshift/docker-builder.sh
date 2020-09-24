#!/bin/bash
sudo docker build -t tester .
sudo docker tag tester jdtotow/tester
sudo docker push jdtotow/tester
