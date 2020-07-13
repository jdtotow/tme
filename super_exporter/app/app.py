from flask import Flask, jsonify, request, Response
import json, requests, time, os
from prometheus_client.exposition import CONTENT_TYPE_LATEST, generate_latest
from prom import Collector, MultiCollector, CollectorV2
from consumermanager import MultiThreadConsumerManager
from threading import Thread

#////////////////////////////////////////////////////////////////////////////////
n_tries = int(os.environ.get("NTRIES","10"))
username = os.environ.get("RABBITMQUSERNAME","richardm")
password = os.environ.get("RABBITMQPASSWORD","bigdatastack")
host = os.environ.get("RABBITMQHOSTNAME","localhost")
port = int(os.environ.get("RABBITMQPORT","5672"))
queue_name = os.environ.get("RABBITMQQUEUENAME","export_metrics")
n_consumers = int(os.environ.get("NCONSUMERS","3"))
exchange = os.environ.get("EXCHANGE","")
#//////////////////////////////////////////////////////////////////////////////////
super_metric_dict = {}
super_labels_dict = {}
super_list = []

_port = int(os.environ.get("EXPORTERPORT","55684"))

_liveness = False 
_readyness = False 
consumer_manager = None 

def responder(status,message):
    response = {}
    response['status'] = status
    response['message'] = message
    return response

app = Flask(__name__)
#import logging
#log = logging.getLogger('werkzeug')
#log.setLevel(logging.ERROR)

class Manager():
    def __init__(self):
        self.username = None
        self.password = None
        self.host = None
        self.port = None
        self.queue_name = None
    def startConsumerManager(self):
        global _liveness, _readyness, consumer_manager
        consumer_manager = MultiThreadConsumerManager(n_consumers,self.username,self.password,self.host,self.port,n_tries,exchange,self.handler,self.queue_name)
        consumer_manager.start()
        _liveness = True 
        _readyness = True
        thread = Thread(target=self.connectionRoutineCheck,args=())
        thread.start()
    def handler(self,data):
        _json = None
        try:
            _json = json.loads(data)
        except Exception as e:
            print("Cannot decode json")
            print(e)
        if _json == None:
            return None
        if type(_json) == type(""):
            _json = _json[1:-1]
        metrics = None 
        labels = None 
        print(_json)
        try:
            metrics = _json['metrics']
            labels =  _json['labels']
        except Exception as e:
            print(e)
            print("Error getting content")
        if metrics == None or labels == None:
            return None
        global super_metric_dict, super_labels_dict, super_list
        super_list.append({'metrics': metrics,'labels':labels})
        for k,v in metrics.items():
            super_metric_dict[k] = v
        for k,v in labels.items():
            super_labels_dict[k] = v
    def setRabbitMQParameter(self,username,password,host,port,queue_name):
        self.username = username
        self.password = password
        self.host = host
        self.port = port
        self.queue_name = queue_name
    def connectionRoutineCheck(self):
        global _liveness, _readyness
        while True:
            if not consumer_manager.threadsStatus():
                _liveness = False 
                _readyness = False
                consumer_manager.stop()
                print("Restarting all threads")
                time.sleep(5)
                consumer_manager.start()
            else:
                _liveness = True 
                _readyness = True 
            time.sleep(5)


@app.route('/liveness',methods=['GET','POST'])
def liveness():
    global _liveness
    if _liveness:
        return Response('ok',status=200, mimetype="application/json")
    else:
        return Response('Manager does not response',status=500, mimetype="application/json")

@app.route('/readyness',methods=['GET','POST'])
def readyness():
    global _readyness
    if _readyness:
        return Response('ok',status=200, mimetype="application/json") 
    else:
        return Response('Manager not ready', status=500,mimetype="application/json")

@app.route('/',methods=['GET','POST'])
def home():
    data = request.data
    if data != None:
        try:
            _json = json.loads(data)
            fields = ['metrics','labels']
            for field in fields:
                if not field in _json:
                    return Response(responder('error','Missing field'+ field),status=400, mimetype="application/json")
            metrics = _json['metrics']
            labels = _json['labels']
            global super_metric_dict, super_labels_dict
            for k,v in metrics.items():
                super_metric_dict[k] = v
            for k,v in labels.items():
                super_labels_dict[k] = v
            return Response(responder('success','OK'),status=200, mimetype="application/json")
        except Exception as e:
            print(e)
            return Response(responder('error','Error json format'),status=400, mimetype="application/json")

@app.route('/metrics',methods=['GET','POST'])
def getMetrics():
    global super_labels_dict, super_metric_dict, super_list
    #registry = Collector(super_labels_dict,super_metric_dict)
    registry = CollectorV2(super_list)
    collected_metric = generate_latest(registry)
    super_labels_dict.clear()
    super_metric_dict.clear()
    del super_list[:]
    return Response(collected_metric,status=200,mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    manager = Manager()
    manager.setRabbitMQParameter(username,password,host,port,queue_name)
    manager.startConsumerManager()
    app.run(host='0.0.0.0',port=_port)
