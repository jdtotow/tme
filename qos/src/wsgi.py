from flask import Flask, jsonify, request, Response
import json, base64, requests, time, os, psutil, hashlib
from prometheus_client.exposition import CONTENT_TYPE_LATEST, generate_latest
from prom import Collector, MultiCollector

super_metric_dict = {}
super_labels_dict = {}
component_name = os.environ.get("COMPONENTNAME")
_port = int(os.environ.get("EXPORTERPORT","55673"))

def responder(status,message):
    response = {}
    response['status'] = status
    response['message'] = message
    return response

app = Flask(__name__)
#import logging
#log = logging.getLogger('werkzeug')
#log.setLevel(logging.ERROR)

@app.route('/',methods=['GET','POST'])
def home():
    data = request.data
    print("----Data-------------")
    print(data)
    print("----End Data------")
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
    global super_labels_dict, super_metric_dict
    registry = Collector(super_labels_dict,super_metric_dict)
    collected_metric = generate_latest(registry)
    super_labels_dict.clear()
    super_metric_dict.clear()
    return Response(collected_metric,status=200,mimetype=CONTENT_TYPE_LATEST)

if __name__ == '__main__':
    app.run(host='qos',port=_port)
