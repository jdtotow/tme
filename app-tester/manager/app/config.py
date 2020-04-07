#config
import os
rabbitmq = {'host':os.environ.get("RABBITMQHOST","localhost"),'port':int(os.environ.get("RABBITMQPORT","5672")),'username':os.environ.get("RABBITMQUSER","richardm"),'password':os.environ.get("RABBITMQPASSWORD","bigdatastack")}
exporter = {'url': os.environ.get("URLEXPORTER","http://localhost:55671")}
kafka = {'hosts':os.environ.get("KAFKABROCKERBOOTSTRAP","localhost"),'group-id':os.environ.get("KAFKAGROUPID","group-1"),"topic":os.environ.get("KAFKATOPIC","manager")}
maintainer = 'Jean-Didier Totow, <totow@unipi.gr>'
engine = 'triple_monitoring_engine'
organization = 'UPRC'
manager = {'application':'manager','version':'v1.0','ntry':int(os.environ.get("NTRY","20")),'brocker':os.environ.get("BROCKER","RabbitMQ")}
default_heartbeat = int(os.environ.get("DEFAULTHEARTBEAT","4000"))
configfilepath = os.environ.get("CONFIGFILEPATH","/config")
