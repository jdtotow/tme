#!/bin/bash
curl -X PUT http://slalite.tme.svc.cluster.local:8090/agreements/a03/stop 
while :
do
	echo "Just a loop.."
	sleep 10
done