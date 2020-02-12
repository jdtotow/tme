import os

outapi = {'url': os.environ.get("OUTAPIURL")} #http://localhost:55670/v2/api/metrics
rabbitmq = {'host': os.environ.get("RABBITMQHOST"),'port': os.environ.get("RABBITMQPORT"),'queue':os.environ.get("MANAGERQUEUE"),'user':os.environ.get("RABBITMQUSER"),'password':os.environ.get("RABBITMQPASSWORD"),'heartbeat_interval':os.environ.get("INTERVAL")}
exporter = {'url':os.environ.get("EXPORTERURL")} #url = http://localhost:55671:/push?
tester = {'name': os.environ.get("NAME")}
