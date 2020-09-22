#!/bin/bash
curl -k -X POST -d @agreement.json http://slalite.tme.svc.cluster.local:8090/agreements
while :
do
	echo "Just a loop.."
	sleep 10
done